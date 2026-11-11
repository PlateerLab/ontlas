"""The vector port: every store the same answers, the embedder swapped, and the space built on them."""
import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from ontlas.embed import (
    CachedEmbedder,
    Embedder,
    EmbedError,
    HashEmbedder,
    OpenAIEmbedder,
    open_embedder,
    register_embedder,
)
from ontlas.space import Space, dictionary, keywords, open_space, split
from ontlas.vectors import (
    MemoryStore,
    Point,
    QdrantStore,
    VectorError,
    conformance,
    known_kinds,
    open_vector_store,
    register_vector_store,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = [{"name": "반품", "kind": "md", "text": "", "sections": [
            {"title": "반품 기간", "text": "배송 완료 후 7일 이내의 주문상품은 반품할 수 있습니다. 포장을 뜯은 속옷은 반품할 수 없습니다."},
            {"title": "반품 비용", "text": "단순 변심이면 왕복 배송비 6천원을 고객이 부담합니다."}]},
        {"name": "배송", "kind": "md", "text": "", "sections": [
            {"title": "배송비", "text": "주문 금액이 5만원 이상이면 무료로 배송합니다."},
            {"title": "택배사", "text": "하늘택배와 바람로지스가 배송합니다. 운송장 번호는 문자로 보냅니다."}]}]


def _space(**kw) -> Space:
    s = Space(HashEmbedder(256), **kw)
    for d in DOCS:
        s.add(d)
    return s


def _points(n: int = 40, dim: int = 16) -> list[Point]:
    e = HashEmbedder(dim)
    return [Point(f"p{i}", e.embed([f"문서 {i} 내용 {i % 7}"])[0], {"group": "a" if i % 2 else "b", "n": i}) for i in range(n)]


def test_hash_embedder_repeats_and_says_what_it_is():
    e = HashEmbedder(64)
    a, b = e.embed(["주문상품 반품"])[0], e.embed(["주문상품 반품"])[0]
    assert a == b and len(a) == 64 and abs(sum(x * x for x in a) - 1) < 1e-9
    assert e.semantic is False and e.describe()["kind"] == "hash"
    with pytest.raises(ValueError):
        HashEmbedder(4)


def test_a_cache_embeds_each_text_once():
    calls = []

    class Counting(HashEmbedder):
        def embed(self, texts):
            calls.append(list(texts))
            return super().embed(texts)

    c = CachedEmbedder(Counting(32), limit=3)
    first = c.embed(["가", "나"])
    assert c.embed(["나", "가"]) == [first[1], first[0]] and calls == [["가", "나"]]
    assert len(c.embed(["다", "라", "마", "바"])) == 4  # past the limit it still answers


def test_an_embedder_joins_by_name():
    class Fixed(Embedder):
        kind, name, dim = "fixed", "fixed", 2

        def embed(self, texts):
            return [[1.0, 0.0] for _ in texts]

    register_embedder("fixed", lambda s: Fixed())
    assert open_embedder({"kind": "fixed"}).embed(["x"]) == [[1.0, 0.0]]
    with pytest.raises(ValueError):
        open_embedder({"kind": "nothing"})


class _Embeddings(BaseHTTPRequestHandler):
    seen: list = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Embeddings.seen.append((self.path, self.headers.get("Authorization"), body["model"]))
        if body["model"] == "broken":
            self.send_response(500)
            self.end_headers()
            return
        data = [{"index": i, "embedding": [float(len(t)), 1.0]} for i, t in enumerate(body["input"])]
        out = json.dumps({"data": list(reversed(data))}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


def test_any_openai_shaped_service_embeds():
    srv = HTTPServer(("127.0.0.1", 0), _Embeddings)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/v1"
    try:
        e = OpenAIEmbedder(url, "m", key="k", batch=2)
        out = e.embed(["a", "bb", "ccc"])
        assert len(out) == 3 and e.dim == 2 and out[2][0] > out[0][0]  # back in order, whatever order the service answered in
        assert _Embeddings.seen[0] == ("/v1/embeddings", "Bearer k", "m")
        with pytest.raises(EmbedError):
            OpenAIEmbedder(url, "broken").embed(["x"])
    finally:
        srv.shutdown()
        srv.server_close()
    with pytest.raises(EmbedError):
        OpenAIEmbedder(url, "m", timeout=1).embed(["x"])


def test_memory_store_is_exact_and_filters():
    m = MemoryStore()
    m.ensure("c", 16)
    pts = _points()
    m.upsert("c", pts)
    assert m.count("c") == 40 and m.collections() == ["c"]
    hits = m.search("c", pts[3].vector, 3)
    assert hits[0].id == "p3" and hits[0].score == pytest.approx(1.0)
    assert all(h.payload["group"] == "a" for h in m.search("c", pts[3].vector, 5, {"group": "a"}))
    assert {h.payload["group"] for h in m.search("c", pts[3].vector, 40, {"group": ["a", "b"]})} == {"a", "b"}
    assert m.delete("c", ["p3", "nope"]) == 1 and m.count("c") == 39
    with pytest.raises(VectorError):
        m.ensure("c", 8)
    m.drop("c")
    assert m.count("c") == 0


def test_a_store_joins_by_name_and_is_held_to_exact_search():
    class Wrong(MemoryStore):
        kind = "wrong"

        def search(self, collection, vector, k=5, where=None):
            return list(reversed(super().search(collection, vector, 40, where)))[:k]

    register_vector_store("wrong", lambda s: Wrong())
    assert "wrong" in known_kinds()
    pts = _points()
    rep = conformance({"good": MemoryStore(), "bad": open_vector_store({"kind": "wrong"})}, pts,
                      [("q", pts[0].vector), ("r", pts[9].vector)], k=5)
    assert rep.stores["good"]["agree"] and not rep.stores["bad"]["agree"]
    with pytest.raises(ValueError):
        open_vector_store({"kind": "nothing"})


def test_a_store_that_fails_is_reported_not_raised():
    down = QdrantStore("http://127.0.0.1:9", timeout=1)
    rep = conformance({"down": down}, _points(5), [("q", _points(1)[0].vector)])
    assert rep.stores["down"]["agree"] is False and "Qdrant" in rep.stores["down"]["error"]


def test_documents_split_by_section_and_keep_what_is_short_whole():
    chunks = split(DOCS[0])
    assert [c.section for c in chunks] == ["반품 기간", "반품 비용"] and chunks[0].document == "반품"
    long = {"name": "긴", "sections": [{"title": "t", "text": "가나다라. " * 400}]}
    parts = split(long, size=200, overlap=20)
    assert len(parts) > 5 and all(len(c.text) <= 240 for c in parts)
    assert split({"name": "본문만", "text": "제목 없는 본문입니다."})[0].section == "본문만"
    assert split({"name": "빈 문서", "text": "  "}) == []


def test_a_space_indexes_only_what_changed_and_follows_the_catalog():
    s = _space()
    assert s.index()["added"] == 4 and s.index()["added"] == 0
    s.add({"name": "쿠폰", "kind": "md", "text": "쿠폰은 주문 한 건에 하나만 씁니다."})
    assert s.index() == {"added": 1, "removed": 0, "chunks": 5, "errors": {}}
    s.set_uploaded([DOCS[0]])
    r = s.index()
    assert r["removed"] == 3 and r["chunks"] == 2
    assert s.stores["memory"].count(s.collection) == 2


def test_search_lands_on_the_section_and_every_store_holds_the_same():
    s = _space(stores={"a": MemoryStore(), "b": MemoryStore()})
    hit = s.search("운송장 번호", 1)[0]
    assert (hit["document"], hit["section"]) == ("배송", "택배사") and hit["store"] == "a"
    assert s.search("운송장 번호", 1, store="b")[0]["id"] == hit["id"]
    assert s.compare("무료 배송", 3)["same"] is True
    with pytest.raises(LookupError):
        s.search("x", store="없음")


def test_a_store_that_fails_falls_behind_and_catches_up():
    class Flaky(MemoryStore):
        broken = True

        def upsert(self, collection, points):
            if self.broken:
                raise VectorError("down")
            return super().upsert(collection, points)

    flaky = Flaky()
    s = _space(stores={"good": MemoryStore(), "flaky": flaky})
    assert s.index()["errors"] == {"flaky": "down"} and s.primary() == "good"
    assert s.search("배송비", 1)[0]["store"] == "good"
    flaky.broken = False
    s.index()
    assert s.errors == {} and flaky.count(s.collection) == 4


def test_a_store_added_later_is_filled():
    s = _space()
    s.index()
    r = s.add_store("second", {"kind": "memory"})
    assert r["errors"] == {} and s.stores["second"].count(s.collection) == 4
    s.remove_store("second")
    with pytest.raises(ValueError):
        s.remove_store("memory")


def test_a_check_says_which_questions_found_their_document():
    s = _space(checks=[{"text": "운송장 번호", "document": "배송"}, {"text": "운송장 번호", "document": "없는 문서"}])
    r = s.check()
    assert r["found"] == 1 and r["questions"] == 2 and r["results"][0]["rank"] >= 1 and r["results"][1]["rank"] == 0
    assert _space().check() is None


class _Field:
    def __init__(self, name, label, labels=None):
        self.name, self.label, self.labels = name, label, labels or {}


class _Obj:
    def __init__(self, name, label, props=()):
        self.name, self.label, self.properties = name, label, {p.name: p for p in props}


class _Onto:
    objects = {"Order": _Obj("Order", "주문"), "OrderItem": _Obj("OrderItem", "주문상품", [_Field("status", "주문상품 상태", {"R": "반품 요청"})])}
    decisions: dict = {}
    actions: dict = {}


def test_names_are_matched_longest_first_and_keywords_skip_verbs():
    names = dictionary(_Onto, [{"term": "운송장", "synonyms": ["송장"]}])
    assert list(names)[0] == "주문상품 상태" and {"주문", "주문상품", "반품 요청", "운송장", "송장"} <= set(names)
    s = _space()
    s.index()
    made = s.concepts(_Onto)
    labels = {c.label: c for c in made["concepts"].values()}
    assert labels["주문상품"].element == "object:OrderItem" and "주문" in labels
    assert "있습니다" not in keywords(list(s.chunks.values()), {})


def test_the_document_ontology_is_an_ontology():
    s = _space()
    st = s.studio(_Onto)
    assert {"Document", "Section", "Concept", "Relation"} <= set(st.onto.objects)
    assert st.run("allDocuments").rows[0][0] == "반품"
    rows = st.run("sectionsAbout", {"concept": "주문상품"}).rows
    assert ("반품", "반품 기간") in rows
    assert "SELECT" in st.translate("allDocuments", "sql:postgres").text and "MATCH" in st.translate("allDocuments", "cypher").text
    if len(st.backends) > 1:
        assert st.conformance().summary()["agree"] == len(st.onto.queries) == 5


def test_a_definition_finds_its_documents_and_a_question_its_definition():
    s = _space()
    assert s.mentions_of("object:OrderItem", _Onto)[0]["section"] == "반품 기간"
    assert [c["element"] for c in s.concepts_in("주문상품 반품 기간", _Onto)] == ["object:OrderItem"]
    g = s.graph(_Onto)
    assert {c["id"] for c in g["clusters"]} >= {"document", "section", "ontology"}
    assert all(e["source"] in {n["id"] for n in g["nodes"]} for e in g["edges"])


def test_a_space_comes_from_the_studio_file():
    s = open_space({"documents": ["../documents/*.md"], "embedder": {"kind": "hash", "dim": 128},
                    "vectors": {"one": {"kind": "memory"}, "two": {"kind": "memory"}}, "collection": "docs",
                    "checks": [{"text": "x", "document": "y"}]}, ROOT / "examples" / "library")
    assert len(s.fixed) == 6 and list(s.stores) == ["one", "two"] and s.collection == "docs" and s.embedder.dim == 128
    assert s.state()["chunks"] > 10 and open_space(None).state()["documents"] == 0


LIVE = [("ONTLAS_LIVE_QDRANT", lambda v: {"kind": "qdrant", "url": v, "prefix": "ontlas_test_"}),
        ("ONTLAS_LIVE_PGVECTOR", lambda v: {"kind": "pgvector", "dsn": v, "prefix": "ontlas_test_"})]


@pytest.mark.parametrize("env,spec", LIVE, ids=["qdrant", "pgvector"])
def test_live_store_agrees_with_exact_search(env, spec):
    value = os.environ.get(env)
    if not value:
        pytest.skip(f"{env} not set")
    store = open_vector_store(spec(value))
    pts = _points(300, 64)
    rep = conformance({"live": store}, pts, [(p.id, p.vector) for p in pts[:30]], k=10)
    assert rep.stores["live"]["agree"], rep.stores
    filtered = conformance({"live": store}, pts, [(p.id, p.vector) for p in pts[:10]], k=5, where={"group": "a"})
    assert filtered.stores["live"]["agree"], filtered.stores
    many = conformance({"live": store}, pts, [(p.id, p.vector) for p in pts[:10]], k=5, where={"group": ["a", "b"]})
    assert many.stores["live"]["agree"], many.stores
    store.ensure("reused", 64)
    store.upsert("reused", pts[:5])
    store.upsert("reused", pts[:5])  # the same ids twice stay five points
    assert store.count("reused") == 5 and "reused" in store.collections()
    assert store.search("reused", pts[0].vector, 1)[0].id == pts[0].id
    assert store.search("reused", pts[0].vector, 1)[0].payload["n"] == 0
    assert store.delete("reused", ["p0"]) >= 1 and store.count("reused") == 4
    with pytest.raises(VectorError):
        store.ensure("reused", 8)
    store.drop("reused")
    assert store.count("reused") == 0


def test_live_space_on_a_real_store():
    value = os.environ.get("ONTLAS_LIVE_QDRANT")
    if not value:
        pytest.skip("ONTLAS_LIVE_QDRANT not set")
    s = _space(stores={"memory": MemoryStore(), "qdrant": open_vector_store({"kind": "qdrant", "url": value, "prefix": "ontlas_space_"})})
    assert s.index()["errors"] == {}
    assert s.compare("운송장 번호", 3)["same"]
    s.stores["qdrant"].drop(s.collection)
    assert urllib.request.urlopen(value + "/collections", timeout=5).status == 200


def test_the_question_s_own_words_settle_what_a_model_found_close():
    class Near(HashEmbedder):
        semantic = True  # says it reads meaning, and puts the wrong passage first

        def embed(self, texts):
            return [[1.0, 0.0] if "숨김" in t or "돌려" in t else [0.9, 0.44] for t in texts]

    near = Near(256)
    near.dim = 2
    s = Space(near)
    s.add({"id": "a", "name": "상품평", "text": "욕설이 들어간 상품평은 숨김 처리합니다."})
    s.add({"id": "b", "name": "반품", "text": "포장을 뜯은 속옷은 반품할 수 없습니다."})
    hits = s.search("포장을 뜯은 속옷도 돌려보낼 수 있나요", k=2)
    assert [h["document"] for h in hits] == ["반품", "상품평"]
    assert hits[0]["score"] > hits[1]["score"] and all(0 <= h["score"] <= 1 for h in hits)
    assert s.compare("포장을 뜯은 속옷도 돌려보낼 수 있나요", k=2)["same"]  # the stores are still compared on the model alone


def test_a_search_returns_what_it_was_asked_for_however_far_it_looked():
    s = Space(HashEmbedder(256))
    for i in range(8):
        s.add({"id": f"d{i}", "name": f"문서{i}", "text": f"반품 기간 {i}일 안내입니다."})
    assert len(s.search("반품 기간", k=3)) == 3
