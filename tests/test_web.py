import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from .conftest import EXAMPLE

CFG = EXAMPLE.parent / "library" / "studio.yaml"
ALL = {"core", "commerce", "commerce-bindings", "fashion", "acme-overlay", "finance", "finance-bindings",
       "party-identity"}


def _build():
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    return StudioSession(load_studio(CFG))


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    return _build()


def test_state_lists_the_library_and_the_schema_graph(session):
    st = session.state()
    assert {r["name"] for r in st["library"] if r["on"]} == ALL
    assert next(r for r in st["library"] if r["name"] == "food")["on"] is False
    assert any(n["abstract"] for n in st["graph"]["nodes"]) and any(e["subtype"] for e in st["graph"]["edges"])
    assert {c["id"] for c in st["graph"]["clusters"]} == {"core", "commerce", "finance", "party-identity", "acme-overlay"}
    json.dumps(st)


def test_unplug_shows_the_impact_and_plugs_back(session):
    imp = session.impact("commerce")
    assert not imp["ok"] and set(imp["dependents"]) == {"acme-overlay", "commerce-bindings", "fashion", "party-identity"}
    assert session.impact("commerce", True)["ok"]
    assert session.detach("commerce")["ok"] is False
    r = session.detach("acme-overlay")
    assert r["ok"] and not r["warning"]
    assert session.decide("returnEligibility", "I1001")["reason"] == "배송 완료 후 반품기간 7일 이내입니다"
    assert session.attach("acme-overlay")["ok"]
    assert session.decide("returnEligibility", "I1001")["matched"] == ["vip-window"]
    r = session.attach("food")
    assert r["ok"] and r["warning"]  # the example database has no food columns
    assert {f["element"] for f in session.bindings()["findings"]} == {"property:Sku.expires_on",
                                                                      "property:Sku.storage"}
    assert session.log[0]["kind"] == "attach"


def test_one_query_in_every_language_and_under_a_role(session):
    r = session.run_query("allParties")
    assert r["agree"] and all(t["ok"] for t in r["translations"])
    r = session.run_query("myOrders", role="customer_agent", principal={"customer_id": "C001"})
    assert all(len(b["rows"]) == 3 for b in r["results"])
    assert "'C001'" in next(t for t in r["translations"] if t["target"] == "sql:postgres")["text"]
    assert "C001" not in r["source"]["sparql"]  # the box for writing it yourself starts before the role filter
    assert not session.run_query("allParties", role="customer_agent", principal={"customer_id": "C001"})["ok"]
    sparql = session.run_query("agreementsSince", {"since": "2026-10-01T00:00:00"})["source"]["sparql"]
    back = session.run_text("sparql", sparql)
    assert back["ok"] and back["agree"] and [len(b["rows"]) for b in back["results"]] == [5, 5]
    assert session.run_text("cypher", session.run_query("revenueByCategory")["source"]["cypher"])["agree"]
    assert not session.run_text("cypher", "MATCH (")["ok"]
    assert not session.ask("anything")["ok"]


def test_request_approve_and_the_decision_follows(session):
    d = session.decide("returnEligibility", "I1001")
    assert d["yes"] and d["evidence"][0]["source"] == "order_items.delivered_at"
    p = session.request("requestReturn", "I1001", {"reason": "사이즈"}, "customer_agent")["proposal"]
    assert p["status"] == "pending" and all(c["passed"] for c in p["checks"])
    assert next(c for c in p["checks"] if c["name"] == "role")["detail"] == "고객 응대 Agent"
    done = session.approve(p["id"], True)
    assert done["proposal"]["status"] == "executed" and "graph" in done["projection"]
    assert next(c for c in done["proposal"]["checks"] if c["name"].startswith("decision:"))["detail"].startswith(
        "eligible true")
    assert session.decide("returnEligibility", "I1001")["yes"] is False
    assert session.audit()[0]["event"] == "원천 반영"
    assert session.request("requestReturn", "I1001", {"reason": "x"}, "customer_agent")["proposal"]["status"] == \
        "rejected"


def test_checks_and_owl_export(session):
    qa = session.questions()
    assert qa["accuracy"] == 1.0 and qa["conformance"]["passed"]
    assert "skos:exactMatch" in session.export_owl()


def test_http_keeps_each_visitor_apart():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.web.server import RateLimit, Sessions, make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(_build, spare=0), ask_limit=RateLimit(5),
                                                               quiet=True))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None, cookie=""):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **({"Cookie": cookie} if cookie
                                                                                      else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read().decode("utf-8"), r.headers.get("Set-Cookie", "")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), ""

    try:
        code, html, set_cookie = call("/")
        assert code == 200 and "XGEN Space" in html and "/*JS*/" not in html and "/*CSS*/" not in html
        first = set_cookie.split(";", 1)[0]
        assert first.startswith("xspace_session=")
        code, body, _ = call("/api/detach", {"name": "acme-overlay"}, first)
        assert code == 200 and json.loads(body)["ok"]
        on = {r["name"] for r in json.loads(call("/api/state", cookie=first)[1])["library"] if r["on"]}
        assert "acme-overlay" not in on
        code, body, other = call("/api/state")
        assert other and {r["name"] for r in json.loads(body)["library"] if r["on"]} == ALL
        assert call("/api/nothing", cookie=first)[0] == 404
        assert call("/api/decide", {"name": "noSuchDecision", "key": "x"}, first)[0] == 400
        assert call("/healthz")[1] == "ok"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_a_visitor_brings_files_reviews_the_draft_and_plugs_it_in(session):
    from xgen_space.web.api import DataOptions

    session.data = DataOptions(samples=EXAMPLE.parent / "files")
    assert len(session.use_samples()["files"]) == 6
    view = session.make_draft("도서관")["pending"]
    assert [s["id"] for s in view["steps"]][:2] == ["read", "objects"] and len(view["graph"]["nodes"]) == 5
    assert view["modules"][0]["yaml"].startswith("module: my-data")
    session.apply_draft({"drop": ["object:Jeoja"], "labels": {"object:Daechul": "대출 기록"}})
    st = session.state()
    assert st["origin"]["kind"] == "files" and st["title"] == "도서관"
    assert {r["name"] for r in st["library"] if r["on"]} == {"my-data", "my-data-bindings"}
    steps = {s["id"]: s for s in session.flow()["steps"]}
    assert steps["bind"]["ok"] and steps["query"]["conformance"] == {"agree": 11, "queries": 11}
    assert steps["source"]["rows"] == 155 and steps["decide"]["decisions"] == 0 and steps["decide"]["actions"] == 2
    assert steps["check"]["questions"] == 11 and steps["check"]["accuracy"] == 1
    assert session.run_query("daechulPerHoewon")["agree"]
    assert session.attach("commerce")["ok"]  # the library stays there to plug in
    session.data = DataOptions(file_bytes=10)
    with pytest.raises(ValueError):
        session.upload("big.csv", b"a,b\n1,2\n3,4\n")
    with pytest.raises(PermissionError):
        session.connect("sqlite:///x.db")


def test_http_takes_a_file_as_the_body_and_keeps_to_the_limit():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.web.server import RateLimit, Sessions, make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(_build, spare=0), ask_limit=RateLimit(5),
                                                               quiet=True, upload_max=64))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def post(path, data, cookie=""):
        req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/octet-stream",
                                                                      **({"Cookie": cookie} if cookie else {})})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, json.loads(r.read().decode("utf-8")), r.headers.get("Set-Cookie", "")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8")), ""

    try:
        code, body, cookie = post("/api/upload?path=" + urllib.parse.quote("회원/회원.csv"),
                                  "회원번호,이름\nM1,가\nM2,나\n".encode("utf-8"))
        cookie = cookie.split(";", 1)[0]
        assert code == 200 and body == {"ok": True, "skipped": False}
        assert post("/api/upload?path=big.csv", b"x" * 65, cookie)[0] == 400
        assert post("/api/upload?path=" + urllib.parse.quote("../up.csv"), b"a\n1\n", cookie)[0] == 400
        assert post("/api/upload?path=x.pdf", b"%PDF", cookie)[0] == 200  # raw material, kept with the reason
        with urllib.request.urlopen(urllib.request.Request(base + "/api/catalog?folder=", headers={"Cookie": cookie})) as r:
            top = json.loads(r.read().decode("utf-8"))
        assert [f["name"] for f in top["folders"]] == ["회원"] and top["files"][0]["error"] and top["unread"] == 1
        url = base + "/api/catalog/download?path=" + urllib.parse.quote("회원/회원.csv")
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Cookie": cookie})) as r:
            assert r.read().startswith("회원번호".encode()) and "UTF-8''" in r.headers["Content-Disposition"]
        code, body, _ = post("/api/draft", b"{}", cookie)
        assert code == 200 and body["pending"]["steps"][1]["items"][0]["key"] == "hoewonbeonho"
        assert post("/api/connect", json.dumps({"dsn": "sqlite:///x.db"}).encode(), cookie)[0] == 403
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_guide_offers_one_video_in_byte_ranges(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.web.server import RateLimit, Sessions, guide, make_handler

    assert guide(None) == {"video": "", "chapters": []}
    video = tmp_path / "demo.mp4"
    video.write_bytes(bytes(range(256)) * 4)
    (tmp_path / "demo.chapters.json").write_text(json.dumps([{"t": 3.4, "chapter": "01", "tab": "flow"}]),
                                                 encoding="utf-8")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(_build, spare=0), ask_limit=RateLimit(5),
                                                               quiet=True, video=video))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def get(path, rng=""):
        req = urllib.request.Request(base + path, headers={"Range": rng} if rng else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    try:
        code, body, _ = get("/api/guide")
        g = json.loads(body)
        assert code == 200 and g["video"].startswith("/media/demo.mp4?v=") and g["chapters"][0]["tab"] == "flow"
        code, body, h = get("/media/demo.mp4", "bytes=10-19")
        assert code == 206 and body == bytes(range(10, 20)) and h["Content-Range"] == "bytes 10-19/1024"
        assert get("/media/demo.mp4", "bytes=-4")[1] == bytes(range(252, 256))
        assert get("/media/demo.mp4", "bytes=5000-")[0] == 416
        assert len(get("/media/demo.mp4")[1]) == 1024
        assert get("/media/demo.chapters.json")[0] == 404
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_a_visitor_sets_the_rules_edits_each_step_and_any_module(session):
    from xgen_space.web.api import DataOptions

    session.data = DataOptions(samples=EXAMPLE.parent / "files")
    session.use_samples()
    view = session.make_draft("도서관", rules={"queries": ["list"]}, tables=["회원", "대출"])["pending"]
    assert view["counts"] == {"objects": 2, "links": 1, "properties": 10, "queries": 2, "states": 1, "actions": 0,
                              "roles": 2, "questions": 2, "decisions": 0}
    bad = session.preview_draft({"types": {"Hoewon.ireum": "enum"}})
    assert bad["ok"] and bad["issues"] and bad["graph"] is None  # an enum with no values does not pass the check
    good = session.preview_draft({"types": {"Hoewon.ireum": "enum"}, "values": {"Hoewon.ireum": "한지우, 오세린"}})
    assert good["ok"] and not good["issues"]
    with pytest.raises(ValueError):
        session.apply_draft({"types": {"Hoewon.hoewonbeonho": "integer"}})  # M001 is not a number
    session.apply_draft({"types": {"Daechul.daechulilsi": "string"}, "labels": {"object:Daechul": "대출 기록"}})
    assert session.studio.onto.objects["Daechul"].properties["daechulilsi"].type == "string"
    assert session.bindings()["ok"] and session.run_query("listDaechul")["agree"]

    src = session.module_source("my-data")
    assert src["applied"] and src["yaml"].startswith("module: my-data")
    edited = src["yaml"].replace("label: 대출 기록", "label: 대출 이력", 1)
    assert session.check_module(edited)["ok"]
    assert session.save_module(edited)["applied"]
    assert session.studio.onto.objects["Daechul"].label == "대출 이력"
    assert not session.check_module(edited.replace("key: daechulbeonho", "key: nothing", 1))["ok"]
    with pytest.raises(ValueError):
        session.save_module("module: [")
    new = "module: notes\nversion: 0.1.0\nkind: industry\nlabel: 메모\nrequires: [my-data]\nextend:\n  objects:\n" \
          "    Hoewon:\n      properties:\n        memo: {type: string, label: 메모}\n"
    assert session.save_module(new, apply=False)["applied"] is False
    assert "notes" in {r["name"] for r in session.state()["library"]}
    assert session.attach("notes")["ok"] and "memo" in session.studio.onto.objects["Hoewon"].properties
    assert "module: notes" in session.export_module("notes")


def test_a_customers_decision_rule_is_edited_on_the_page(session):
    assert session.decide("returnEligibility", "I1001")["matched"] == ["vip-window"]
    src = session.module_source("acme-overlay")["yaml"]
    assert "<= 14" in src
    narrower = src.replace("<= 14", "<= 3")  # the item was delivered four days ago
    with pytest.raises(ValueError, match="정답률"):  # question A1 still expects the VIP rule: the flow refuses it
        session.save_module(narrower)
    assert session.decide("returnEligibility", "I1001")["matched"] == ["vip-window"]
    import yaml

    d = yaml.safe_load(narrower)
    next(q for q in d["questions"] if q["id"] == "A1")["expect"]["reason"] = "배송 완료 후 반품기간 7일 이내입니다"
    out = session.save_module(yaml.safe_dump(d, allow_unicode=True, sort_keys=False))
    assert out["change"]["version"] == "1.0.1" and out["change"]["status"] == "approved"
    assert session.decide("returnEligibility", "I1001")["matched"] != ["vip-window"]
    assert session.log[0]["kind"] == "change"
    assert [c["status"] for c in session.changes_state()["changes"]] == ["approved", "pending"]
