"""The lexicon: terms tied to the definitions they name, with their labels and the words they must not be taken for;
plugged in and out with their modules, edited from the management screens, brought in from a glossary, read in a
question; and the owners, tiers, question types, held-out set and gradings beside it."""
import json
from pathlib import Path

import pytest

from ontlas.lexicon import (
    collect,
    concept_of,
    conflicts,
    entry,
    labels,
    link,
    merge,
    read,
    read_glossary,
    term_id,
    view,
)
from ontlas.model import Ontology
from ontlas.modules import Module, compose

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "examples" / "library"
SHOP = ["core", "commerce", "commerce-bindings", "commerce-operations", "commerce-operations-bindings", "fashion",
        "acme-overlay"]
KW = {"namespace": "https://example.org/studio#", "name": "studio"}
NS = "https://example.org/t#"
PAIRS = ("구분,용어 A,용어 B,관계,설명,근거,확인 필요\n"
         "주문,주문금액,주문 합계,동의어,,용어집 3장,\n"
         "결제,결제금액,주문금액,혼동주의,할인 전후가 다릅니다,,Y\n"
         "결제,환불금액,결제금액,관련어,,,\n"
         "배송,배송완료,출고완료,동의어,,,\n"
         "결제,PG,결제대행,약어,,,\n"
         "주문,주문,오더,동의어,,,\n"
         "주문,주문상품,주문,상위어,,,\n"
         "주문,주문,,동의어,,,\n"
         "주문,주문,상품,모름,,,\n")


def _mod(name, **kw):
    return Module.from_dict({"module": name, **kw})


def _base():
    return _mod("base", namespace=NS, areas={"Order": {"label": "주문"}},
                objects={"Order": {"key": "id", "label": "주문", "area": "Order", "properties": {
                    "id": {"type": "string", "label": "주문 번호"},
                    "status": {"type": "enum", "values": {"PAID": "결제 완료", "DONE": "배송 완료"}, "label": "주문 상태"},
                    "total": {"type": "decimal", "label": "주문 금액"}}}})


@pytest.fixture
def shop():
    pytest.importorskip("yaml")
    from ontlas.library import Library

    return Library(LIB).resolve(SHOP)


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(load_studio(LIB / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))


# ---- the entry and where it is kept --------------------------------------------------------------------------------

def test_an_entry_from_before_keeps_working_and_the_new_shape_reads_in_full():
    old = {"term": "주문내역", "synonyms": ["주문상세"], "avoid": ["오더"], "definition": "주문 한 건의 상품", "english": "Order Detail",
           "abbreviation": "ORD_DTL", "column": "ORD_DTL_NO"}
    e = entry(old)
    assert e["id"] == "주문내역" and e["abbreviations"] == ["ORD_DTL"] and e["avoid"] == ["오더"] and e["status"] == "active"
    assert labels(e) == [("주문내역", "preferred"), ("Order Detail", "english"), ("주문상세", "alternative"),
                         ("ORD_DTL", "abbreviation")]
    new = entry({"term": "결제금액", "concept": "property:Payment.amount", "synonyms": "실결제금액, 결제액",
                 "channels": {"백오피스": "승인금액", "쇼핑몰": " "}, "hidden": ["결재금액", "결재 금액"],
                 "confusable": [{"term": "주문금액", "note": "할인 전"}, "주문금액", "할인금액"], "status": "review"})
    assert new["id"] == "결제금액@property:Payment.amount" and new["synonyms"] == ["실결제금액", "결제액"]
    assert new["channels"] == {"백오피스": "승인금액"} and new["confusable"] == [{"term": "주문금액", "note": "할인 전"},
                                                                              {"term": "할인금액", "note": ""}]
    assert ("결재 금액", "hidden") not in labels(new)  # one label, however it is spaced
    assert term_id({"id": "pay", "term": "결제금액"}) == "pay"
    m = _mod("words", kind="dictionary", terms=[old, new])
    assert Module.from_dict(m.to_dict()).terms == [old, new] and m.counts()["terms"] == 2


def test_a_later_module_writes_a_term_over_takes_one_out_and_one_module_may_say_a_word_twice():
    words = _mod("words", kind="dictionary", requires=["base"], terms=[
        {"term": "주문", "concept": "object:Order", "synonyms": ["오더"]}, {"term": "금액"}, {"term": "금액"}])
    later = _mod("later", requires=["words"], terms=[{"id": "주문@object:Order", "term": "주문", "concept": "object:Order",
                                                       "synonyms": ["구매"]}], remove={"terms": ["금액"]})
    comp = compose([_base(), words], name="t")
    assert [term_id(t) for t in comp.terms] == ["주문@object:Order", "금액", "금액#2"]
    assert comp.term_origin == {"주문@object:Order": "words", "금액": "words", "금액#2": "words"}
    comp = compose([_base(), words, later], name="t")
    assert [(term_id(t), t.get("synonyms")) for t in comp.terms] == [("주문@object:Order", ["구매"]), ("금액#2", None)]
    assert comp.term_origin["주문@object:Order"] == "later" and comp.issues == []
    assert collect([words])[0] == comp.terms[:0] + [words.terms[0], words.terms[1], {"id": "금액#2", "term": "금액"}]


def test_a_term_names_a_definition_by_its_element():
    o = compose([_base()], name="t").ontology
    assert concept_of(o, "area:Order")["kind_label"] == "Object"
    assert concept_of(o, "property:Order.total") == {"concept": "property:Order.total", "kind": "property",
                                                      "kind_label": "속성", "label": "주문 금액", "of": "주문"}
    assert concept_of(o, "value:Order.status=DONE")["label"] == "배송 완료"
    assert concept_of(o, "value:Order.status=GONE") is None and concept_of(o, "object:Nope") is None
    assert concept_of(o, "nonsense") is None and concept_of(o, "decision:x") is None
    assert link(entry({"term": "주문"}), o) == ("object:Order", [])  # the type before the area of the same name
    assert link(entry({"term": "배송완료"}), o) == ("value:Order.status=DONE", [])  # spaces aside
    assert link(entry({"term": "주문번호"}), o) == ("property:Order.id", [])
    assert link(entry({"term": "환불", "synonyms": ["주문 금액"]}), o) == ("property:Order.total", [])
    assert link(entry({"term": "없는 말"}), o) == ("", [])


def test_the_shop_keys_a_property_label_to_the_type_whose_key_it_is_and_leaves_a_shared_one_open(shop):
    o = compose(shop, **KW).ontology
    assert link(entry({"term": "주문 번호"}), o) == ("property:Order.order_id", [])
    assert link(entry({"term": "결제 금액"}), o) == ("", ["property:OrderItem.line_total", "property:Payment.amount"])


# ---- conflicts, reading a sentence, the view --------------------------------------------------------------------

def test_conflicts_are_one_label_for_two_definitions_a_pair_both_same_and_confusable_and_a_missing_definition():
    o = compose([_base()], name="t").ontology
    terms = [{"term": "주문금액", "concept": "property:Order.total", "synonyms": ["금액"]},
             {"term": "결제금액", "concept": "property:Payment.amount", "hidden": ["금 액"]},
             {"term": "주문", "concept": "object:Order", "synonyms": ["오더"]},
             {"term": "오더", "concept": "object:Order"},  # the same definition: no conflict
             {"term": "배송완료", "synonyms": ["출고완료"], "confusable": ["출고완료"]}]
    found = conflicts(terms, o)
    assert [(c["kind"], c["label"]) for c in found] == [("label", "금액"), ("synonym_confusable", "출고완료"),
                                                         ("missing_concept", "결제금액")]
    assert found[0]["terms"] == ["주문금액@property:Order.total", "결제금액@property:Payment.amount"]
    assert found[0]["concepts"] == ["property:Order.total", "property:Payment.amount"]
    assert "서로 다른 용어 주문금액, 결제금액" in found[0]["text"]
    assert conflicts(terms[2:4], o) == []


def test_a_sentence_is_read_by_every_label_longest_first_and_names_what_not_to_take_it_for():
    terms = [{"term": "결제금액", "concept": "property:Payment.amount", "hidden": ["결재금액"], "channels": {"쇼핑몰": "최종 결제금액"},
              "confusable": [{"term": "주문금액", "note": "할인 전 금액입니다"}], "definition": "승인된 금액"},
             {"term": "주문금액", "synonyms": ["주문 총액"], "confusable": [{"term": "결제금액", "note": "승인된 금액입니다"}]},
             {"term": "결제", "abbreviations": ["PG"]}, {"term": "주문"}]
    said = read("최종결제금액이랑 주문 총액 차이, PGA 말고 PG사 기준으로", terms)
    assert said["text"] == "결제금액이랑 주문금액 차이, PGA 말고 결제사 기준으로"  # a Latin word whole, a particle after it
    assert [(m["label"], m["as"], m["term"]) for m in said["matched"]] == [
        ("최종 결제금액", "channel", "결제금액"), ("주문 총액", "alternative", "주문금액"), ("PG", "abbreviation", "결제")]
    assert said["confusables"] == [
        {"term": "결제금액", "id": "결제금액@property:Payment.amount", "confusable": "주문금액", "note": "할인 전 금액입니다"},
        {"term": "주문금액", "id": "주문금액", "confusable": "결제금액", "note": "승인된 금액입니다"}]  # each its own note
    said = read("결재 금액은요", terms)
    assert said["text"] == "결제금액은요" and said["matched"][0]["as_label"] == "숨은 표기"
    assert read("주문 내역", terms)["matched"][0]["term"] == "주문" and read("배송", terms)["matched"] == []


def test_the_view_counts_the_lexicon_and_marks_rows_new_or_changed_against_what_runs():
    o = compose([_base()], name="t").ontology
    o.questions = [type("Q", (), {"id": "Q1", "text": "주문 총액 알려줘"})()]
    applied = [{"term": "주문금액", "concept": "property:Order.total"}, {"term": "가버린 말"}]
    terms = [{"term": "주문금액", "concept": "property:Order.total", "synonyms": ["주문 총액"],
              "confusable": [{"term": "결제금액"}]},
             {"term": "결제금액", "hidden": ["결재금액"], "confusable": [{"term": "주문금액"}], "status": "review"}]
    v = view(terms, o, origin={"주문금액@property:Order.total": "words"}, applied=applied, module_label=str.upper,
             readers=lambda el: [f"읽는 곳 {el}"])
    assert v["stats"] == {"terms": 2, "labels": 4, "by_label": {"preferred": 2, "english": 0, "alternative": 1,
                                                                 "abbreviation": 0, "channel": 0, "hidden": 1},
                          "linked": 1, "concepts": 1, "unlinked": 1, "confusables": 1, "conflicts": 0, "review": 1}
    a, b = v["rows"]
    assert (a["concept_label"], a["concept_kind"], a["concept_of"], a["concept_found"]) == ("주문 금액", "속성", "주문", True)
    assert a["labels"]["alternative"] == ["주문 총액"] and a["module"] == "words" and a["module_label"] == "WORDS"
    assert a["used_by"] == ["검증 질문 Q1", "읽는 곳 property:Order.total"]
    assert (a["new"], a["pending"], b["new"], b["pending"]) == (False, True, True, False)
    assert b["concept_found"] is None and v["removed"] == ["가버린 말"]
    assert [k["label"] for k in v["label_kinds"]] == ["대표어", "영문", "동의어", "약어", "채널 표기", "숨은 표기"]


def test_the_document_dictionary_finds_a_definition_by_any_label_of_its_term():
    from ontlas.space import dictionary

    o = compose([_base()], name="t").ontology
    names = dictionary(o, [{"term": "주문금액", "concept": "property:Order.total", "synonyms": ["주문 총액"], "hidden": ["주문금엑"]},
                           {"term": "주문", "concept": "object:Order", "synonyms": ["오더"]},
                           {"term": "완료", "concept": "value:Order.status=DONE"},
                           {"term": "운송장", "synonyms": ["송장"], "hidden": ["운송짱"]}])
    assert names["주문 총액"].element == names["주문금엑"].element == "property:Order.total"
    assert names["주문 총액"] is names["주문금액"] and names["주문금액"].kind == "term"
    assert names["오더"] is names["주문"] and names["주문"].kind == "object"  # the type's own name, met by another word
    assert names["완료"].element == "property:Order.status"  # a value is found as its property, as a value label is
    assert names["송장"].element == "" and names["운송짱"] is names["운송장"]


# ---- the management screens' edits ----------------------------------------------------------------------------------

@pytest.fixture
def ws(shop):
    from ontlas.manage import Workspace

    return Workspace(shop, compose_kw=KW)


def test_terms_are_added_changed_and_deleted_into_the_workspace_module(ws):
    from ontlas.manage import EditError

    e = ws.apply("add_term", {"term": "반품", "concept": "object:Claim", "synonyms": ["리턴"], "owner": "고객센터",
                              "confusable": [{"term": "교환", "note": "상품을 바꿔 받는 것입니다"}]})
    assert e.target == "term:반품@object:Claim"
    assert ws.module.terms == [{"term": "반품", "concept": "object:Claim", "synonyms": ["리턴"],
                                "confusable": [{"term": "교환", "note": "상품을 바꿔 받는 것입니다"}], "owner": "고객센터"}]
    for bad, msg in (({"term": "반품", "concept": "object:Claim"}, "already exists"),
                     ({"term": "x", "concept": "object:Nope"}, "concept 'object:Nope' is unknown"),
                     ({"term": ""}, "a term needs its word"), ({"term": "x", "status": "gone"}, "term status 'gone'"),
                     ({"term": "x", "confusable": ["x"]}, "cannot be confused with itself")):
        with pytest.raises(EditError, match=msg):
            ws.apply("add_term", bad)
    ws.apply("update_term", {"id": "반품@object:Claim", "term": "반품 접수", "status": "draft"})
    assert ws.module.terms[0]["id"] == "반품@object:Claim" and ws.module.terms[0]["term"] == "반품 접수"
    assert len(ws.module.terms) == 1  # the workspace's own term changes in place, under the id it had
    ws.apply("update_term", {"id": "결제금액@property:Payment.amount", "hidden": ["결재금액", "결제액수"], "owner": "재무팀"})
    over = ws.module.terms[1]
    assert over["id"] == "결제금액@property:Payment.amount" and over["hidden"] == ["결재금액", "결제액수"]
    assert over["channels"] == {"백오피스": "승인금액", "쇼핑몰": "최종 결제금액"}  # the rest as the module had it
    assert "commerce-operations" in [r.name for r in ws.module.requires]  # it composes after what it writes over
    comp = ws.composed()
    assert comp.term_origin["결제금액@property:Payment.amount"] == "workspace" and len(comp.terms) == 7
    e = ws.apply("delete_term", {"id": "결제금액@property:Payment.amount"})
    assert e.took_out == [] and ws.module.remove["terms"] == ["결제금액@property:Payment.amount"]
    assert len(ws.module.terms) == 1 and "결제금액@property:Payment.amount" not in [term_id(t) for t in ws.composed().terms]
    with pytest.raises(EditError, match="term '결제금액@property:Payment.amount' is unknown"):
        ws.apply("delete_term", {"id": "결제금액@property:Payment.amount"})
    ws.apply("delete_term", {"id": "반품@object:Claim"})
    assert ws.module.terms == []
    ws.undo()
    ws.undo()
    assert "결제금액@property:Payment.amount" in [term_id(t) for t in ws.composed().terms]
    ws.redo()
    assert "결제금액@property:Payment.amount" not in [term_id(t) for t in ws.composed().terms]


def test_a_term_changed_where_it_was_defined_keeps_its_id_through_a_new_definition(ws):
    ws.apply("update_term", {"id": "고객@object:Customer", "concept": "area:Customer"})
    comp = ws.composed()
    row = next(t for t in comp.terms if t.get("term") == "고객")
    assert term_id(row) == "고객@object:Customer" and row["concept"] == "area:Customer"
    assert sum(1 for t in comp.terms if t.get("term") == "고객") == 1


# ---- a glossary brought in -----------------------------------------------------------------------------------------

def test_a_pair_table_becomes_synonyms_related_confusable_terms_and_says_what_conflicts(shop):
    comp = compose(shop, **KW)
    g = read_glossary(PAIRS.encode("utf-8"), "용어집.csv")
    assert len(g["pairs"]) == 9 and g["terms"] == []
    entries, rep = merge(g, comp.terms, comp.ontology, source="용어집.csv")
    by = {e["term"]: e for e in entries}
    assert rep["added"] == ["환불금액", "결제대행", "주문", "주문상품"] and rep["updated"] == ["주문금액", "결제금액", "배송완료"]
    assert by["주문금액"]["synonyms"] == ["주문 총액", "주문 합계"] and by["주문금액"]["cite"] == "용어집 3장"
    assert by["주문금액"]["id"] == "주문금액@property:Order.total"  # written over, under the id it has
    assert by["결제금액"]["status"] == "review" and rep["review"] == ["결제금액"]
    assert by["결제금액"]["related"] == ["환불금액"] and by["환불금액"]["related"] == ["결제금액"]
    assert by["결제대행"]["abbreviations"] == ["PG"]  # the shorter word is the abbreviation
    assert by["주문상품"]["broader"] == ["주문"] and by["주문"]["narrower"] == ["주문상품"]
    assert [(x["term"], x["with"]) for x in rep["synonym"]] == [("주문금액", "주문 합계"), ("배송완료", "출고완료"),
                                                                ("주문", "오더")]
    assert rep["confusable"] == [{"term": "결제금액", "with": "주문금액", "note": "할인 전후가 다릅니다", "row": 3}]
    assert {x["term"]: x["concept"] for x in rep["linked"]} == {"주문상품": "object:OrderItem",
                                                               "환불금액": "property:Refund.amount", "주문": "object:Order"}
    assert "id" not in by["주문"] and "id" not in by["환불금액"]  # a new entry goes by its word and definition
    assert rep["unlinked"] == [{"term": "결제대행", "candidates": []}]
    assert [s["row"] for s in rep["skipped"]] == [9, 10] and "관계 '모름'" in rep["skipped"][1]["reason"]
    assert [(c["kind"], c["label"]) for c in rep["conflicts"]] == [("label", "출고완료"), ("synonym_confusable", "배송완료")]


def test_a_term_list_and_a_seed_file_are_read_too():
    g = read_glossary("용어,영문,정의,유의어\n적립금,Reward Point,돌려주는 포인트,마일리지; 포인트\n,빈 줄,,\n".encode("utf-8"),
                      "terms.csv")
    assert g["pairs"] == [] and g["terms"] == [{"term": "적립금", "english": "Reward Point", "definition": "돌려주는 포인트",
                                                "synonyms": "마일리지; 포인트"}]
    entries, rep = merge(g, [], None, source="terms.csv")
    assert entries == [{"term": "적립금", "source": "terms.csv", "english": "Reward Point", "definition": "돌려주는 포인트",
                        "synonyms": ["마일리지", "포인트"]}]
    assert rep["added"] == ["적립금"] and rep["unlinked"] == [{"term": "적립금", "candidates": []}]
    pytest.importorskip("yaml")
    seed = read_glossary("terms:\n  - {term: 쿠폰, confusable: [적립금]}\n  - {nothing: 1}\n".encode("utf-8"), "seed.yaml")
    assert seed == {"terms": [{"term": "쿠폰", "confusable": ["적립금"]}], "pairs": []}
    entries, _ = merge(seed, [], None)
    assert entries[0]["confusable"] == [{"term": "적립금", "note": ""}]
    for data, name, msg in ((b"a,b\n1,2\n", "x.csv", "머리글을 확인"), (b"[1, 2]", "x.json", "terms 목록"),
                            (b"{broken", "x.yaml", "YAML 또는 JSON")):
        with pytest.raises(ValueError, match=msg):
            read_glossary(data, name)


def test_a_glossary_workbook_is_read_by_its_sheets(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.active.title = "용어"
    for row in (["용어", "영문", "정의"], ["적립금", "Reward Point", "돌려주는 포인트"]):
        wb.active.append(row)
    pairs = wb.create_sheet("관계")
    for row in (["구분", "용어 A", "용어 B", "관계"], ["혜택", "적립금", "쿠폰", "혼동주의"]):
        pairs.append(row)
    wb.save(tmp_path / "g.xlsx")
    g = read_glossary((tmp_path / "g.xlsx").read_bytes(), "g.xlsx")
    assert [t["term"] for t in g["terms"]] == ["적립금"] and [(p["a"], p["b"], p["sheet"]) for p in g["pairs"]] == [
        ("적립금", "쿠폰", "g.xlsx · 관계")]


def test_the_cli_shows_the_lexicon_and_brings_a_glossary_in_as_a_dictionary_module(tmp_path, capsys):
    from ontlas.cli import main

    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio projects into a graph
    (tmp_path / "용어집.csv").write_text(PAIRS, encoding="utf-8")
    out = tmp_path / "shop-words.yaml"
    assert main(["lexicon", "import", str(tmp_path / "용어집.csv"), "--config", str(LIB / "studio.yaml"),
                 "-o", str(out), "--name", "shop-words"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["written"] == str(out) and rep["terms"] == 7 and len(rep["conflicts"]) == 2
    m = Module.load(out)
    assert (m.name, m.kind) == ("shop-words", "dictionary")
    assert [r.name for r in m.requires] == ["commerce", "commerce-operations"]  # it writes over their terms
    assert main(["lexicon", "import", str(tmp_path / "용어집.csv"), "-o", str(out)]) == 0  # again: the same terms
    assert len(Module.load(out).terms) == 7
    capsys.readouterr()
    assert main(["lexicon", "import", str(tmp_path / "용어집.csv")]) == 0
    assert "kind: dictionary" in capsys.readouterr().out
    assert main(["lexicon", "show", str(LIB / "studio.yaml")]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["stats"]["terms"] == 6 and shown["stats"]["confusables"] == 2 and shown["conflicts"] == []


# ---- the page --------------------------------------------------------------------------------------------------------

def test_the_shop_lexicon_is_shown_with_its_labels_owners_and_confusable_pairs(session):
    st = session.lexicon_state()
    json.dumps(st)
    assert st["stats"] == {"terms": 6, "labels": 24, "by_label": {"preferred": 6, "english": 6, "alternative": 5,
                                                                   "abbreviation": 1, "channel": 4, "hidden": 2},
                           "linked": 6, "concepts": 6, "unlinked": 0, "confusables": 2, "conflicts": 0, "review": 0}
    rows = {r["term"]: r for r in st["rows"]}
    pay = rows["결제금액"]
    assert (pay["id"], pay["concept"], pay["concept_label"], pay["concept_kind"], pay["concept_of"]) == (
        "결제금액@property:Payment.amount", "property:Payment.amount", "결제 금액", "속성", "결제")
    assert pay["labels"]["channel"] == ["승인금액", "최종 결제금액"] and pay["labels"]["hidden"] == ["결재금액"]
    assert pay["confusable"] == [{"term": "주문금액", "note": "주문금액은 할인 전 주문상품 금액의 합입니다"}]
    assert (pay["module"], pay["module_label"], pay["owner"]) == ("commerce-operations", "이커머스 운영 온톨로지", "결제팀")
    assert "검증 질문 OP7" in pay["used_by"] and "질의 결제 수단별 금액" in pay["used_by"]
    assert rows["출고완료"]["concept_label"] == "SHIPPED" and rows["출고완료"]["concept_of"] == "주문 · 주문 상태"
    assert {c["concept"] for c in st["concepts"]} >= {"area:Order", "object:Order", "property:Order.total",
                                                      "value:Order.status=SHIPPED", "decision:returnEligibility"}
    assert st["workspace"] == {"dirty": False, "module": "workspace", "label": "관리 변경", "issues": [], "edits": [],
                               "redo": 0}


def test_terms_are_edited_and_imported_from_the_page_and_filed_as_one_change(session):
    with pytest.raises(ValueError, match="용어 편집\\(add_area\\)이 아니어서"):
        session.lexicon_edit("add_area", {"name": "X"})
    with pytest.raises(ValueError, match="용어 '고객@object:Customer'이\\(가\\) 이미 있어"):
        session.lexicon_edit("add_term", {"term": "고객", "concept": "object:Customer"})
    with pytest.raises(ValueError, match="연결한 정의 'object:Nope'을\\(를\\) 찾지 못해"):
        session.lexicon_edit("add_term", {"term": "x", "concept": "object:Nope"})
    r = session.lexicon_edit("add_term", {"term": "반품", "concept": "object:Claim", "synonyms": ["리턴"]})
    assert r["edit"] == {"op": "add_term", "target": "term:반품@object:Claim", "took_out": []}
    row = next(x for x in r["rows"] if x["term"] == "반품")
    assert row["new"] and (row["module"], row["module_label"]) == ("workspace", "관리 변경") and r["workspace"]["dirty"]
    r = session.lexicon_edit("update_term", {"id": "고객@object:Customer", "hidden": ["고갱님"]})
    assert next(x for x in r["rows"] if x["term"] == "고객")["pending"]
    r = session.lexicon_import(PAIRS, "용어집.csv")
    assert r["edit"]["target"] == "terms:용어집.csv" and r["report"]["review"] == ["결제금액"]
    assert [c["kind"] for c in r["conflicts"]] == ["label", "synonym_confusable"] and r["stats"]["conflicts"] == 2
    assert [e["op"] for e in r["workspace"]["edits"]] == ["add_term", "update_term", "import_terms"]
    session.catalog_upload("용어/목록.csv", "용어,영문,정의\n적립금,Reward Point,돌려주는 포인트\n".encode("utf-8"))
    r = session.lexicon_import(path="용어/목록.csv")
    assert r["report"]["source"] == "목록.csv" and r["report"]["added"] == ["적립금"]
    with pytest.raises(ValueError, match="용어 파일이 없어"):
        session.lexicon_import()
    assert session.manage_state()["workspace"]["edits"][-1]["op"] == "import_terms"  # the same pending edits
    session.manage_undo()
    assert "적립금" not in [x["term"] for x in session.lexicon_state()["rows"]]
    out = session.manage_propose()
    assert out["ok"] and not out["pending"]
    comp = session.studio.composition
    assert "반품@object:Claim" in [term_id(t) for t in comp.terms] and comp.term_origin["반품@object:Claim"] == "workspace"
    st = session.lexicon_state()
    assert not st["workspace"]["dirty"] and not any(x["new"] or x["pending"] for x in st["rows"])


def test_the_lexicon_routes_answer_over_http(session):
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from ontlas.web.server import RateLimit, Sessions, make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(lambda: session, spare=0),
                                                               ask_limit=RateLimit(5), quiet=True))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base, cookie = f"http://127.0.0.1:{httpd.server_address[1]}", {}

    def call(path, body=None):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **cookie})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.headers.get("Set-Cookie"):
                    cookie["Cookie"] = r.headers["Set-Cookie"].split(";", 1)[0]
                return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    try:
        code, body = call("/api/lexicon")
        assert code == 200 and body["stats"]["terms"] == 6
        code, body = call("/api/lexicon/edit", {"op": "add_term", "args": {"term": "반품", "concept": "object:Claim"}})
        assert code == 200 and body["stats"]["terms"] == 7
        code, body = call("/api/lexicon/edit", {"op": "delete_term", "args": {"id": "없는 말"}})
        assert code == 400 and body["error"] == "용어 '없는 말'을(를) 찾지 못했습니다. 화면을 새로고침해 주세요."
        code, body = call("/api/lexicon/import", {"text": PAIRS, "name": "용어집.csv"})
        assert code == 200 and len(body["report"]["conflicts"]) == 2
        code, body = call("/api/manage/edit", {"op": "update_term", "args": {"id": "반품@object:Claim", "owner": "고객센터"}})
        assert code == 200 and body["edit"]["target"] == "term:반품@object:Claim"
    finally:
        httpd.shutdown()
    from ontlas.web.team import NEEDS

    assert NEEDS["lexicon/edit"] == NEEDS["lexicon/import"] == "editor"


def test_a_question_is_read_by_the_lexicon_and_names_the_term_it_must_not_be_taken_for(session):
    out = session.space_ask("결재 금액이랑 주문 총액은 어떻게 달라요?")
    lx = out["lexicon"]
    assert lx["text"] == "결제금액이랑 주문금액은 어떻게 달라요?" and out["question"] == "결재 금액이랑 주문 총액은 어떻게 달라요?"
    assert [(m["label"], m["as"], m["term"], m["concept_label"]) for m in lx["matched"]] == [
        ("주문 총액", "alternative", "주문금액", "주문 금액"), ("결재금액", "hidden", "결제금액", "결제 금액")]
    assert {(c["term"], c["confusable"]) for c in lx["confusables"]} == {("주문금액", "결제금액"), ("결제금액", "주문금액")}
    out = session.space_ask("출고완료면 반품 기간이 시작되나요?")
    assert out["lexicon"]["confusables"] == [{"term": "출고완료", "id": "출고완료@value:Order.status=SHIPPED",
                                              "confusable": "배송완료",
                                              "note": "배송완료는 고객이 상품을 받은 상태이고 반품 기간은 배송완료부터 셉니다"}]
    plain = session.space_ask("주문상품 I1004 반품 되나요?")  # a question that uses no term answers as it always did
    assert "lexicon" not in plain and plain["route"] == "decision"
    named = session.space_ask("최종 결제금액 I1004 반품 되나요?")
    assert named["route"] == "decision" and named["lexicon"]["matched"][0]["as"] == "channel"


def test_a_label_the_lexicon_knows_finds_the_definition_the_question_did_not_name(studio):
    from ontlas.tools import StudioTools

    tools = StudioTools(studio)
    before = tools.answer_question("주문 결제액수 알려줘")
    tools.terms = [{"term": "주문 금액", "concept": "property:Order.total", "hidden": ["결제액수"]}]
    after = tools.answer_question("주문 결제액수 알려줘")
    assert "lexicon" not in before and after["lexicon"]["text"] == "주문 주문 금액 알려줘"
    titles = [d["title"] for d in after["definitions"]]
    assert "주문" in titles


# ---- owners, tiers, question types, the held-out set and the gradings --------------------------------------------

def test_owners_tiers_and_question_metadata_are_read_and_written_back():
    d = {"ontology": "t", "namespace": NS, "version": "0.1.0",
         "areas": {"Order": {"label": "주문", "owner": "주문팀", "tier": 1}, "Cart": {"tier": "2"}},
         "objects": {"Order": {"label": "주문", "area": "Order", "owner": "주문팀", "key": "id",
                               "properties": {"id": {"type": "string"}}}},
         "queries": {"all": {"label": "전체", "query": {"match": {"o": "Order"}, "return": ["o.id"]}}},
         "decisions": {"d": {"label": "판정", "target": "Order", "owner": "고객센터", "inputs": {"x": {"type": "string",
                                                                                                    "property": "id"}},
                             "outputs": {"ok": "boolean"}, "rules": [{"id": "r", "when": {}, "then": {"ok": True}}]}},
         "questions": [{"id": "A", "text": "몇 건?", "query": "all", "type": "value", "grading": "keywords",
                        "keywords": ["1"], "holdout": True, "owner": "주문팀", "expect": {"rows": 1}},
                       {"id": "B", "text": "주문이 뭔가요?", "keywords": ["주문"], "expect": {}},
                       {"id": "C", "text": "?", "decision": "d", "key": "1", "expect": {"ok": True}}]}
    o = Ontology.from_dict(d)
    assert o.validate() == []
    assert (o.areas["Order"].owner, o.areas["Order"].tier, o.areas["Cart"].tier) == ("주문팀", 1, 2)
    assert o.objects["Order"].owner == "주문팀" and o.decisions["d"].owner == "고객센터"
    a, b, c = o.questions
    assert (a.kind, a.graded_by, a.holdout, a.keywords, a.owner) == ("value", "keywords", True, ["1"], "주문팀")
    assert (b.kind, b.graded_by, c.kind, c.graded_by) == ("definition", "keywords", "decision", "match")
    back = o.to_dict()
    assert back["areas"] == {"Order": {"label": "주문", "owner": "주문팀", "tier": 1}, "Cart": {"tier": 2}}
    assert back["objects"]["Order"]["owner"] == "주문팀" and back["decisions"]["d"]["owner"] == "고객센터"
    assert back["questions"][0] == {"id": "A", "text": "몇 건?", "query": "all", "type": "value", "holdout": True,
                                    "grading": "keywords", "keywords": ["1"], "owner": "주문팀", "expect": {"rows": 1}}
    assert back["questions"][2] == {"id": "C", "text": "?", "decision": "d", "key": "1", "expect": {"ok": True}}
    assert Ontology.from_dict(back).to_dict() == back


def test_bad_metadata_is_said():
    d = {"ontology": "t", "namespace": NS, "areas": {"Order": {"tier": 0}, "Cart": {"tier": "first"}},
         "objects": {"Order": {"key": "id", "properties": {"id": {"type": "string"}}}},
         "questions": [{"id": "A", "text": "?", "type": "guess", "grading": "vibes", "query": "q"},
                       {"id": "B", "text": "?", "grading": "keywords", "decision": "d"},
                       {"id": "C", "text": "뭔가요?"}, {"id": "D", "text": "?", "type": "decision"}]}
    issues = Ontology.from_dict(d).validate()
    for said in ("area Order: tier '0' is not a whole number from 1", "area Cart: tier 'first' is not a whole number from 1",
                 "question A: type 'guess' is not one of", "question A: grading 'vibes' is not one of",
                 "question B: grading by keywords needs keywords", "question C: give the words a right answer has",
                 "question D: give either a query or a decision"):
        assert any(i.startswith(said) for i in issues), said


def test_owners_tiers_and_question_metadata_go_through_the_management_screens(ws):
    from ontlas.manage import EditError

    ws.apply("update_area", {"name": "Order", "owner": "주문운영팀", "tier": 2})
    ws.apply("add_area", {"name": "Member", "label": "회원", "owner": "고객팀", "tier": 3})
    ws.apply("update_object", {"name": "Customer", "owner": "고객팀"})
    ws.apply("update_decision", {"decision": "shippingFee", "owner": "물류팀"})
    ws.apply("add_question", {"id": "N1", "text": "결제금액이 뭔가요?", "type": "definition", "grading": "keywords",
                              "keywords": "결제 수단, 승인", "holdout": True, "owner": "결제팀"})
    ws.apply("update_question", {"id": "Q2", "holdout": True, "grading": "evidence", "keywords": ["3.2조"]})
    with pytest.raises(EditError, match="tier '0' is not a whole number"):
        ws.apply("update_area", {"name": "Order", "tier": 0})
    o = ws.composed().ontology
    assert (o.areas["Order"].owner, o.areas["Order"].tier, o.areas["Member"].tier) == ("주문운영팀", 2, 3)
    assert o.objects["Customer"].owner == "고객팀" and o.decisions["shippingFee"].owner == "물류팀"
    n1 = next(q for q in o.questions if q.id == "N1")
    assert (n1.kind, n1.graded_by, n1.keywords, n1.holdout, n1.query, n1.decision) == (
        "definition", "keywords", ["결제 수단", "승인"], True, "", "")
    q2 = next(q for q in o.questions if q.id == "Q2")
    assert (q2.holdout, q2.graded_by, q2.keywords, q2.expect) == (True, "evidence", ["3.2조"], {"eligible": True})
    ws.apply("update_question", {"id": "Q2", "holdout": False, "expect": {"eligible": True}})
    q2 = next(q for q in ws.composed().ontology.questions if q.id == "Q2")
    assert not q2.holdout and q2.graded_by == "evidence"
    ws.apply("update_area", {"name": "Order", "tier": ""})
    assert ws.composed().ontology.areas["Order"].tier is None


def test_the_management_state_shows_owners_tiers_and_question_metadata(session):
    st = session.manage_state()
    areas = {a["name"]: a for a in st["areas"]}
    assert (areas["Order"]["owner"], areas["Order"]["tier"]) == ("주문팀", 1)
    assert (areas["Product"]["owner"], areas["Product"]["tier"]) == ("", None)
    assert {d["name"]: d["owner"] for d in st["decisions"]}["returnEligibility"] == "고객센터"
    qs = {q["id"]: q for q in st["questions"]}
    assert (qs["Q3"]["type"], qs["Q3"]["holdout"], qs["Q3"]["grading"]) == ("decision", True, "match")
    assert (qs["Q4"]["grading"], qs["Q4"]["keywords"], qs["Q4"]["owner"]) == ("evidence", ["2.1조"], "고객센터")
    assert (qs["OP7"]["type"], qs["OP7"]["query"], qs["OP7"]["decision"]) == ("definition", "", "")
    assert next(o for o in st["objects"] if o["name"] == "Order")["owner"] == ""
    with pytest.raises(ValueError, match="Object Order의 단계 'x'은\\(는\\) 1 이상의 정수여야"):
        session.manage_edit("update_area", {"name": "Order", "tier": "x"})
    with pytest.raises(ValueError, match="키워드로 채점하므로 키워드를"):
        session.manage_edit("add_question", {"id": "N2", "text": "?", "query": "shipmentsInTransit", "grading": "keywords"})


# ---- the check -------------------------------------------------------------------------------------------------------

def test_the_shop_check_grades_by_words_and_grounds_and_reports_the_held_out_set_apart(session):
    rep = session.studio.questions()
    by = {r.id: r for r in rep.results}
    assert rep.accuracy == 1.0 and all(r.passed for r in rep.results)
    assert (by["Q3"].holdout, by["Q4"].grading, by["OP6"].grading, by["OP7"].type) == (True, "evidence", "keywords", "definition")
    assert "결제 수단에서 실제로 승인된 금액" in by["OP7"].got and by["OP7"].grounded
    sets = rep.split()
    assert sets["holdout"] == {"questions": 1, "measured": 1, "passed": 1, "accuracy": 1.0, "grounded": 1.0}
    assert sets["dev"]["questions"] == len(rep.results) - 1
    assert set(rep.split("type")) == {"value", "decision", "definition"}
    page = session.questions()
    assert page["sets"]["holdout"]["accuracy"] == 1 and page["types"]["definition"]["questions"] == 1
    row = next(r for r in page["results"] if r["id"] == "Q3")
    assert (row["holdout"], row["type"], row["grading"]) == (True, "decision", "match")
    d = rep.to_dict()
    assert d["sets"] == sets and "types" in d


def test_a_grading_holds_an_answer_right_by_its_words_its_grounds_or_leaves_it_to_a_model(studio):
    from ontlas.model import Question

    base = {"text": "?", "decision": "returnEligibility", "key": "I1004"}
    studio.onto.questions = [
        Question(id="match", expect={"eligible": False}, **base),
        Question(id="words", expect={"eligible": True}, grading="keywords", keywords=["불가", "카테고리"], **base),
        Question(id="missing", expect={}, grading="keywords", keywords=["가능"], **base),
        Question(id="grounds", expect={"eligible": False}, grading="evidence", keywords=["2.1조"], **base),
        Question(id="clause", expect={"eligible": False}, grading="evidence", keywords=["9조"], **base),
        Question(id="wrong", expect={"eligible": True}, grading="evidence", keywords=["2.1조"], **base),
        Question(id="model", expect={"eligible": False}, grading="llm", holdout=True, **base),
        Question(id="rows", text="?", query="ordersOfCustomer", params={"customer": "C001"}, expect={},
                 grading="keywords", keywords=["o2", "shipped"], type="value")]
    rep = studio.questions()
    by = {r.id: r for r in rep.results}
    assert by["match"].passed and by["words"].passed and not by["missing"].passed  # 불가 · 카테고리 are said, 가능 is not
    assert by["grounds"].passed and not by["clause"].passed and not by["wrong"].passed  # the clause, and the verdict too
    assert by["model"].unmeasured == "needs_model" and by["model"].holdout and by["model"].grading == "llm"
    assert rep.split()["holdout"] == {"questions": 1, "measured": 0, "passed": 0, "accuracy": None, "grounded": None}
    assert by["rows"].passed and (by["rows"].type, by["rows"].grading) == ("value", "keywords")
    assert rep.split()["dev"]["measured"] == 7 and rep.split("type") == {
        "decision": {"questions": 7, "measured": 6, "passed": 3, "accuracy": 0.5, "grounded": 1.0},
        "value": {"questions": 1, "measured": 1, "passed": 1, "accuracy": 1.0, "grounded": 1.0}}


def test_the_review_reports_the_held_out_set_apart(session):
    from ontlas.review import measure

    check = measure(session.studio, session.studio.flow)["check"]
    assert check["sets"]["holdout"] == {"questions": 1, "measured": 1, "passed": 1, "accuracy": 1.0, "grounded": 1.0}
    assert check["sets"]["dev"]["passed"] == check["sets"]["dev"]["measured"]
