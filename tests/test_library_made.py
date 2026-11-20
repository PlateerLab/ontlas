"""A library made on the page: from definition files, on the library that is open, or with nothing in it."""
import io
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"

ENTITIES = {
    "meta": {"title": "가게 표준 초안"},
    "objects": [{"label_ko": "주문", "class": "shop:Order", "definition": "손님이 물건을 사려고 만든 거래",
                 "entities": [{"class": "shop:Order"}, {"class": "shop:OrderLine"}]}],
    "entities": [
        {"name": "Order", "class": "shop:Order", "label_ko": "주문", "properties": [
            {"name": "shop:orderNumber", "label_ko": "주문번호", "kind": "값", "range": "Text", "cardinality": "1", "required": True},
            {"name": "shop:orderedItem", "label_ko": "주문 줄", "kind": "관계", "range": "shop:OrderLine", "cardinality": "1..n"}]},
        {"name": "OrderLine", "class": "shop:OrderLine", "label_ko": "주문 줄", "properties": [
            {"name": "shop:quantity", "label_ko": "수량", "kind": "값", "range": "Integer", "cardinality": "1", "required": True}]},
    ],
}
RULES = {
    "rules": [{"id": "D-AX-01", "tier": "AXIOM 후보", "type": "제한", "name": "무르기 기간 하한", "condition": "무르기 기간을 정할 때",
               "result": "받은 날부터 7일 이내에는 무를 수 있어야 한다", "basis": "가게법 제3조"}],
    "parameters": [{"key": "@undo_days_min", "value": "7", "kind": "법정 기준", "rules": ["D-AX-01"]}],
    "terms": [{"term": "무르기", "definition": "산 것을 되돌리는 일", "synonyms": ["반품"]}],
    "appendix": [{"note": "모듈에 자리가 없는 구역"}],
}
TURTLE = """@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <https://example.org/farm#> .
ex:Crop a owl:Class ; rdfs:label "작물"@ko . ex:Field a owl:Class ; rdfs:label "밭"@ko .
ex:grownIn a owl:ObjectProperty ; rdfs:domain ex:Crop ; rdfs:range ex:Field ; rdfs:label "자라는 밭"@ko ."""


def raw(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def _build():
    from ontlas.config import load_studio
    from ontlas.web import library_entry
    from ontlas.web.api import StudioSession

    first = load_studio(SHOP)
    s = StudioSession(first)
    s.libraries = [library_entry("l1", SHOP, first)]
    return s


@pytest.fixture()
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    return _build()


def test_files_of_a_draft_are_read_together_into_a_library_of_their_own(session):
    first = session.studio
    session.library_file("entities.json", raw(ENTITIES))
    held = session.library_file("C:\\초안\\rules.json", raw(RULES))  # only the file's name is kept
    assert [f["name"] for f in held["files"]] == ["entities.json", "rules.json"]
    assert held["files"][0]["sections"] == {"objects": 1, "entities": 2} and held["files"][1]["sections"]["rules"] == 1
    out = session.library_new("가게 표준", "files", key="Shop Standard")
    assert out["id"] == "s1" and session.library_id == "s1" and session.studio is not first
    assert out["made"]["objects"] == 2 and out["made"]["links"] == 1 and out["made"]["cards"] == 1 and out["made"]["terms"] == 1
    assert out["report"]["preserved"] > 0
    assert {"label": "모듈에 자리가 없는 구역", "count": 1} in out["report"]["unsupported"]["kinds"]
    st = session.state()
    assert st["title"] == "가게 표준" and st["libraries"][-1] == {"id": "s1", "label": "가게 표준", "modules": out["made"]["modules"],
                                                              "source": "", "made": True}
    assert {r["name"] for r in st["library"]} == {"shop-standard", "shop-standard-axiom"}  # nothing of the library left
    assert session.library_files()["files"] == []  # the files went into the library
    session.library_use("l1")
    assert session.studio is first
    session.library_use("s1")
    assert "Order" in session.studio.onto.objects and session.studio.onto.namespace == "https://example.org/shop-standard#"


def test_a_file_that_is_no_draft_is_refused_where_it_is_added(session):
    for name, data in (("notes.txt", b"x"), ("broken.json", b"{"), ("list.json", b"[1, 2]"), ("bare.json", b'{"meta": {"title": "x"}}'),
                       ("latin.json", "{\"terms\": [\"\xe9\"]}".encode("latin-1"))):
        with pytest.raises(ValueError):
            session.library_file(name, data)
    assert session.library_files()["files"] == []
    with pytest.raises(ValueError, match="파일이 없어"):
        session.library_new("가게 표준", "files")
    session.library_file("odd.json", raw({"appendix": [{"note": "x"}]}))  # rows, but none a module has a place for
    with pytest.raises(ValueError, match="읽은 정의가 없어"):
        session.library_new("가게 표준", "files")
    assert [x["id"] for x in session.libraries] == ["l1"] and session.library_id == "l1"
    assert session.library_file_drop("odd.json")["files"] == []


def test_an_owl_vocabulary_comes_in_as_the_library_s_module(session):
    session.library_file("farm.ttl", TURTLE.encode("utf-8"))
    out = session.library_new("농장", "files", key="farm")
    assert out["made"]["objects"] == 2 and out["made"]["links"] == 1 and out["made"]["modules"] == 1
    assert session.state()["library"][0]["name"] == "farm"
    assert any(k["label"] == "식별자 추가" for k in out["report"]["adjusted"]["kinds"])


def test_an_empty_library_holds_nothing_and_still_answers(session):
    out = session.library_new("새 도메인", "empty")
    assert out["made"]["objects"] == 0 and out["made"]["modules"] == 0 and out["report"] is None
    st = session.state()
    assert st["title"] == "새 도메인" and st["library"] == [] and st["stats"]["objects"] == 0


def test_a_library_on_the_one_that_is_open_keeps_its_own_copy(session):
    offered = len(session.state()["library"])
    out = session.library_new("우리 가게", "base", modules=["commerce"])
    on = {m.name for m in session.studio.composition.modules}
    assert on == {"core", "commerce"} and out["made"]["modules"] == 2  # what a chosen module requires comes with it
    assert len(session.state()["library"]) == offered  # the rest of the library is there to switch on
    extra = session.studio.library.create("ours", label="우리 규칙")
    assert "ours" in session.studio.library.names() and extra.name == "ours"
    session.library_use("l1")
    assert "ours" not in session.studio.library.names() and len(session.studio.composition.modules) == 8
    with pytest.raises(ValueError, match="모듈 구성"):
        session.library_new("없는 모듈", "base", modules=["nowhere"])
    assert [x["id"] for x in session.libraries] == ["l1", "s1"]


def test_names_and_counts_are_kept_within_limits_and_only_a_made_one_is_dropped(session):
    from ontlas.web.api import LIBRARIES_MADE_MAX

    for bad in ("", "   "):
        with pytest.raises(ValueError, match="이름"):
            session.library_new(bad, "empty")
    with pytest.raises(ValueError, match="시작 방법"):
        session.library_new("가", "elsewhere")
    for i in range(LIBRARIES_MADE_MAX):
        session.library_new(f"도메인 {i}", "empty")
    with pytest.raises(ValueError, match="같은 이름"):
        session.library_new("도메인 0", "empty")
    with pytest.raises(ValueError, match="한도"):
        session.library_new("하나 더", "empty")
    with pytest.raises(ValueError, match="삭제하지 못했습니다"):
        session.library_drop("l1")
    with pytest.raises(LookupError):
        session.library_drop("s9")
    assert session.library_id == f"s{LIBRARIES_MADE_MAX}"
    session.library_drop(session.library_id)  # the one on screen: the first library takes its place
    assert session.library_id == "l1" and len(session.libraries) == LIBRARIES_MADE_MAX
    assert session.library_new("하나 더", "empty")["id"] == f"s{LIBRARIES_MADE_MAX}"


def test_a_library_is_taken_out_as_a_studio_folder_that_serves(session, tmp_path):
    from ontlas.config import load_studio

    session.library_file("entities.json", raw(ENTITIES))
    session.library_file("rules.json", raw(RULES))
    session.library_new("가게 표준", "files", key="shop")
    data, name = session.export_library()
    assert name == "shop.zip"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert sorted(z.namelist()) == ["shop/library/shop-axiom/0.1.0.yaml", "shop/library/shop/0.1.0.yaml", "shop/studio.yaml"]
        z.extractall(tmp_path)
    again = load_studio(tmp_path / "shop" / "studio.yaml")
    assert set(again.onto.objects) == set(session.studio.onto.objects) and again.onto.label == "가게 표준"
    assert len(again.composition.cards) == 1 and again.onto.parameters["undo_days_min"].value == 7


def test_in_a_team_studio_an_admin_makes_and_drops_libraries():
    from ontlas.web.team import NEEDS

    assert {NEEDS[r] for r in ("library/file", "library/file/drop", "library/new", "library/drop")} == {"admin"}
    assert "library" not in NEEDS  # which one a person looks at is their own: anyone signed in opens one


def test_over_http_a_file_is_the_body_and_the_zip_comes_back():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.web.server import RateLimit, Sessions, make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(_build, spare=0), ask_limit=RateLimit(5), quiet=True,
                                                               upload_max=2048))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, data=None, cookie="", kind="application/json"):
        req = urllib.request.Request(base + path, data=data, headers={"Content-Type": kind, **({"Cookie": cookie} if cookie else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    try:
        code, body, headers = call("/api/library/file?path=" + urllib.parse.quote("가게.json"), raw(ENTITIES), kind="application/octet-stream")
        cookie = headers.get("Set-Cookie", "").split(";", 1)[0]
        assert code == 200 and json.loads(body)["files"][0]["name"] == "가게.json"
        assert call("/api/library/file?path=big.json", b" " * 4096, cookie, "application/octet-stream")[0] == 400
        assert json.loads(call("/api/library/files", cookie=cookie)[1])["files"][0]["sections"] == {"objects": 1, "entities": 2}
        code, body, _ = call("/api/library/new", json.dumps({"label": "가게 표준", "start": "files", "key": "shop"}).encode(), cookie)
        assert code == 200 and json.loads(body)["id"] == "s1"
        st = json.loads(call("/api/state", cookie=cookie)[1])
        assert st["library_id"] == "s1" and st["libraries"][-1]["made"] is True
        code, body, headers = call("/api/export/library", cookie=cookie)
        assert code == 200 and "shop.zip" in headers["Content-Disposition"] and zipfile.ZipFile(io.BytesIO(body)).namelist()
        assert json.loads(call("/api/library/drop", json.dumps({"id": "s1"}).encode(), cookie)[1]) == {"ok": True}
        assert json.loads(call("/api/state", cookie=cookie)[1])["library_id"] == "l1"
        assert call("/api/library/new", json.dumps({"label": "", "start": "empty"}).encode(), cookie)[0] == 400
    finally:
        httpd.shutdown()
        httpd.server_close()
