"""Relations a model reads between the concepts a passage names: checked against the passage, kept with its sentence, in the
document ontology, in search, and kept across restarts."""
import json
import re

import pytest

from ontlas.embed import HashEmbedder
from ontlas.relations import BasicReader, Busy, mentions_in, open_reader, parse_rows, units_of
from ontlas.space import Space

DOCS = [{"name": "반품정책", "kind": "md", "text": "", "path": "정책/반품정책.md", "sections": [
            {"title": "반품 기간", "text": "주문상품의 반품은 배송 완료 후 7일 이내에 신청합니다. 반품 승인은 고객센터가 합니다."},
            {"title": "반품 비용", "text": "단순 변심이면 반품 배송비는 고객이 부담합니다."}]},
        {"name": "배송안내", "kind": "md", "text": "", "path": "안내/배송안내.md", "sections": [
            {"title": "배송비", "text": "주문 금액이 5만원 이상이면 배송비 없이 배송합니다. 배송은 하늘택배가 맡습니다."}]}]


class _Field:
    def __init__(self, name, label):
        self.name, self.label, self.labels = name, label, {}


class _Obj:
    def __init__(self, name, label, props=()):
        self.name, self.label, self.properties, self.description = name, label, {p.name: p for p in props}, ""


class _Onto:
    objects = {"OrderItem": _Obj("OrderItem", "주문상품"), "Order": _Obj("Order", "주문")}
    decisions: dict = {}
    actions: dict = {}
    links: dict = {}
    queries: dict = {}


TERMS = [{"term": t, "synonyms": []} for t in ("반품", "고객센터", "고객", "배송비", "배송", "하늘택배", "반품 승인")]


def _space() -> Space:
    s = Space(HashEmbedder(128))
    for d in DOCS:
        s.add(d)
    s.index()
    return s


def answering(rows_for_unit):
    """A model that answers every unit it is shown, from the numbered concepts the prompt gives."""
    calls = []

    def llm(system, user):
        calls.append(user)
        units = re.findall(r"^\[(\d+)\] .*\n  개념: (.+)$", user, re.M)
        rows = []
        for u, names in units:
            rows += rows_for_unit(int(u), numbered(names))
        return "근거를 보고 답합니다.\n```json\n" + json.dumps(rows, ensure_ascii=False) + "\n```"

    llm.calls = calls
    return llm


def numbered(names: str) -> dict[str, int]:
    """'1=반품 승인 2=고객센터' -> {'반품 승인': 1, '고객센터': 2}: a concept may hold a space."""
    return {m.strip(): int(k) for k, m in re.findall(r"(\d+)=(.+?)(?= \d+=|$)", names)}


def approved_by(u, n):
    if "반품 승인" in n and "고객센터" in n:
        return [{"u": u, "s": n["반품 승인"], "p": "approvedBy", "o": n["고객센터"], "label": "승인 주체"}]
    return []


def test_an_ending_on_its_own_is_no_concept():
    from ontlas.space import Chunk, keywords

    chunks = [Chunk(str(i), "d", f"s{i}", i, "검토하는 담당자가 하는 일은 확인하는 것입니다. 하는 일 하는 일") for i in range(3)]
    assert "하는" not in keywords(chunks, {}) and "담당자" in keywords(chunks, {})


def test_names_are_found_longest_first_in_the_order_said():
    assert mentions_in("반품 승인은 고객센터가 합니다. 반품", ["반품", "반품 승인", "고객센터"]) == ["반품 승인", "고객센터", "반품"]
    assert mentions_in("주문상품을 받았다", ["주문", "주문상품"]) == ["주문상품"]


def test_only_sentences_naming_two_concepts_are_units():
    s = _space()
    chunks = list(s.passages.values())
    labels = {c.id: ["반품", "반품 승인", "고객센터", "배송비", "고객"] for c in chunks}
    units = units_of(chunks, labels)
    assert units and all(len(u.mentions) >= 2 for u in units)
    assert any(u.text.startswith("반품 승인은 고객센터가") for u in units)


def test_an_answer_is_read_leniently_and_checked_row_by_row():
    assert parse_rows('설명 ```json\n[{"u": 1}]\n```') == [{"u": 1}]
    assert parse_rows('{"relations": [{"u": 2}]}') == [{"u": 2}]
    assert parse_rows("모르겠습니다") is None
    s = _space()
    chunks = [c for c in s.passages.values() if c.section == "반품 기간"]
    labels = {c.id: ["반품 승인", "고객센터", "주문상품", "반품"] for c in chunks}

    def llm(system, user):
        return json.dumps([
            {"u": 2, "s": 1, "p": "approvedBy", "o": 2, "label": "승인 주체이며 아주 길게 늘어진 이름은 잘립니다 정말로 길게"},
            {"u": 2, "s": 1, "p": "approvedBy", "o": 2},  # the same pair and name once
            {"u": 2, "s": 1, "p": "approvedBy", "o": 1},  # a concept with itself
            {"u": 9, "s": 1, "p": "approvedBy", "o": 2},  # no such unit
            {"u": 2, "s": 1, "p": "승인", "o": 2},  # not an English identifier
            {"u": 2, "s": 1, "p": "mentions", "o": 2},  # the document ontology's own link
            {"u": 2, "s": 1, "p": "approvedBy", "o": 7},  # no such concept
            "엉뚱한 줄"], ensure_ascii=False)

    out = BasicReader(llm).read(chunks, labels, {})
    assert [(r.source, r.predicate, r.target) for r in out["relations"]] == [("반품 승인", "approvedBy", "고객센터")]
    r = out["relations"][0]
    assert r.evidence == "반품 승인은 고객센터가 합니다." and len(r.label) == 30 and r.document == "반품정책"
    assert out["answered"] == {c.id for c in chunks} and out["calls"] == 1


def test_a_failed_call_leaves_its_passages_and_a_busy_site_keeps_what_was_read():
    s = _space()
    chunks = list(s.passages.values())
    labels = {c.id: ["반품 승인", "고객센터", "배송비", "고객", "배송", "하늘택배"] for c in chunks}
    out = BasicReader(lambda a, b: "모르겠습니다", batch_chars=10).read(chunks, labels, {})
    unread = {c.id for c in chunks if len(units_of([c], labels)) > 0}
    assert unread and not unread & out["answered"] and out["relations"] == []
    n = []

    def busy(system, user):
        n.append(1)
        if len(n) > 1:
            raise Busy("limit")
        return "[]"

    out = BasicReader(busy, batch_chars=10).read(chunks, labels, {})
    assert out["busy"] and len(n) == 2 and len(out["answered"] & unread) == 1


def test_the_vocabulary_so_far_goes_into_the_next_prompt():
    s = _space()
    llm = answering(approved_by)
    s.vocabulary["appliesTo"] = "규정이 적용되는 대상"
    s.read_relations(BasicReader(llm), _Onto, TERMS)
    assert any("appliesTo: 규정이 적용되는 대상" in c for c in llm.calls)


def test_relations_enter_the_document_ontology_with_their_sentence():
    s = _space()
    out = s.read_relations(BasicReader(answering(approved_by)), _Onto, TERMS)
    assert out["found"] == 1 and out["left"] == 0 and out["reader"] == "basic"
    st = s.studio(_Onto, TERMS)
    rows = st.run("relationsOf", {"concept": "고객센터"}).rows
    assert rows == [("반품 승인", "승인 주체", "approvedBy", "고객센터", "반품정책", "반품 기간")]
    assert st.run("relationNames").rows == [("approvedBy", 1)]
    if len(st.backends) > 1:
        assert st.conformance().summary()["agree"] == len(st.onto.queries)
    g = s.graph(_Onto, TERMS)
    edge = next(e for e in g["edges"] if e.get("relation") == "approvedBy")
    assert edge["label"] == "승인 주체" and edge["evidence"] == "반품 승인은 고객센터가 합니다." and g["relations"] == 1
    ends = {edge["source"], edge["target"]}
    assert not any(e["label"] == "함께 언급" and {e["source"], e["target"]} == ends for e in g["edges"])  # a named relation says more
    assert s.read_relations(BasicReader(answering(approved_by)), _Onto, TERMS)["read"] == 0  # nothing left to read


def test_a_changed_passage_is_read_again_and_a_folder_reads_alone():
    s = _space()
    llm = answering(approved_by)
    out = s.read_relations(BasicReader(llm), _Onto, TERMS, folder="안내")
    assert s.reading("안내")["read"] == s.reading("안내")["passages"] and s.reading("정책")["read"] == 0 and out["found"] == 0
    s.read_relations(BasicReader(llm), _Onto, TERMS, folder="정책")
    assert len(s.live_relations("정책")) == 1 and s.live_relations("안내") == []
    changed = json.loads(json.dumps(DOCS[0]))
    changed["sections"][0]["text"] = changed["sections"][0]["text"].replace("고객센터가", "고객센터 팀장이")
    s.add(changed)
    assert s.live_relations() == [] and s.reading("정책")["read"] < s.reading("정책")["passages"]
    assert s.forget_relations("안내") > 0 and s.reading("안내")["read"] == 0


def test_what_was_read_outlives_the_space():
    s = _space()
    s.read_relations(BasicReader(answering(approved_by)), _Onto, TERMS)
    saved = json.loads(json.dumps(s.relations_dump(), ensure_ascii=False))
    again = _space()
    again.relations_load(saved)
    assert [(r.source, r.target, r.evidence) for r in again.live_relations()] == \
        [(r.source, r.target, r.evidence) for r in s.live_relations()]
    assert again.read_relations(BasicReader(answering(approved_by)), _Onto, TERMS)["read"] == 0


def test_a_relation_is_said_beside_the_passage_that_states_it():
    from ontlas.knowledge import WordsRetriever, build

    s = _space()
    s.read_relations(BasicReader(answering(approved_by)), _Onto, TERMS)
    know = build(_Onto, s, TERMS, "words")
    assert isinstance(know.retriever, WordsRetriever)
    stated = next(e for e in know.items if e.kind == "document" and "고객센터가" in e.text)
    other = next(e for e in know.items if e.kind == "document" and e.id != stated.id)
    said = "반품 승인 → 승인 주체 → 고객센터"
    assert said in know.relations("반품 승인은 누가 하나요", [stated.id])
    assert said not in know.relations("반품 승인은 누가 하나요", [other.id])  # a relation no found passage states explains nothing
    assert "concept:고객센터" in stated.mentions and ("concept:반품 승인", "승인 주체", "concept:고객센터") in know.links
    hidden = know.only(lambda doc: doc != "반품정책")  # a reader who may not read the sentence does not get its relation
    assert said not in hidden.relations("반품 승인은 누가 하나요", [stated.id])


def test_a_relation_says_a_property_by_its_name():
    from ontlas.knowledge import build

    class Onto(_Onto):
        objects = {**_Onto.objects, "Desk": _Obj("Desk", "창구", [_Field("team", "고객센터")])}

    s = _space()
    s.read_relations(BasicReader(answering(approved_by)), Onto, TERMS)
    (sub, label, obj, chunk), = s.relation_triples(Onto, TERMS)
    assert obj == "concept:고객센터" and "반품 승인 → 승인 주체 → 고객센터" in build(Onto, s, TERMS, "words").relations("반품 승인", [chunk])


def test_a_document_out_of_the_stores_is_still_read():
    s = Space(HashEmbedder(128))
    for d in DOCS:
        s.add({**d, "embed": False} if d["name"] == "반품정책" else d)
    s.index()
    assert all(c.document != "반품정책" for c in s.chunks.values())
    s.read_relations(BasicReader(answering(approved_by)), _Onto, TERMS)
    assert len(s.live_relations()) == 1


def test_readers_are_a_port():
    with pytest.raises(ValueError):
        open_reader("nothing", lambda a, b: "")
    assert open_reader("basic", lambda a, b: "").kind == "basic"


def test_ontology_build_reads_the_same_shape():
    pytest.importorskip("xgen_ontology_build")
    s = _space()

    def llm(system, user):
        if "units_with_relations" not in system:
            return json.dumps({"predicates": [{"name": "approvedBy", "definition": "승인하는 쪽"}]})
        units = re.findall(r"^\[(\d+)\] (.+)\n  개체: (.+)$", user, re.M)
        rows = []
        for u, text, names in units:
            n = numbered(names)
            if "반품 승인" in n and "고객센터" in n:
                rows.append({"u": int(u), "s": n["반품 승인"], "p": "approvedBy", "o": n["고객센터"]})
        return json.dumps({"units_with_relations": [r["u"] for r in rows], "relations": rows}, ensure_ascii=False)

    out = s.read_relations(open_reader("ontology-build", llm), _Onto, TERMS)
    assert out["reader"] == "ontology-build" and out["left"] == 0
    r = s.live_relations()
    assert [(x.source, x.predicate, x.target) for x in r] == [("반품 승인", "approvedBy", "고객센터")]
    assert r[0].evidence == "반품 승인은 고객센터가 합니다."
