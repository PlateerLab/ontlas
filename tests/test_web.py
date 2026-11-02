import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from .conftest import EXAMPLE

CFG = EXAMPLE.parent / "library" / "studio.yaml"
ALL = {"core", "commerce", "commerce-bindings", "fashion", "acme-overlay", "finance", "finance-bindings"}


def _build():
    from xgen_data_studio.config import load_studio
    from xgen_data_studio.web.api import StudioSession

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
    assert {c["id"] for c in st["graph"]["clusters"]} == {"core", "commerce", "finance"}
    json.dumps(st)


def test_unplug_shows_the_impact_and_plugs_back(session):
    imp = session.impact("commerce")
    assert not imp["ok"] and set(imp["dependents"]) == {"acme-overlay", "commerce-bindings", "fashion"}
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
    assert next(c for c in p["checks"] if c["name"] == "role")["detail"] == "고객 응대 에이전트"
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
    from xgen_data_studio.web.server import RateLimit, Sessions, make_handler

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
        assert code == 200 and "XGEN 데이터 스튜디오" in html and "/*JS*/" not in html and "/*CSS*/" not in html
        first = set_cookie.split(";", 1)[0]
        assert first.startswith("xds_session=")
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
