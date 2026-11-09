"""The ways in and out: a platform's query service as a source, the REST API, the reasoner port, the space on the page."""
import json
import os
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from xgen_space.backends.gateway import GatewayBackend, GatewayError, inline, literal
from xgen_space.rest import ROUTES, Rest, openapi, tool_list

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "examples" / "library" / "studio.yaml"


@pytest.mark.parametrize("value,dialect,text", [
    (None, "postgres", "NULL"), (True, "postgres", "TRUE"), (True, "sqlite", "1"), (3, "postgres", "3"), (1.5, "postgres", "1.5"),
    ("O'Brien", "postgres", "'O''Brien'"), ("a\\b", "postgres", "'a\\b'"), ("a\\b", "mysql", "'a\\\\b'"),
    ("'; DROP TABLE x; --", "postgres", "'''; DROP TABLE x; --'")])
def test_a_value_becomes_sql_text_it_cannot_break_out_of(value, dialect, text):
    assert literal(value, dialect) == text


def test_placeholders_inside_quotes_stay_and_a_missing_value_is_refused():
    assert inline("SELECT '?' , a FROM t WHERE b = ? AND c = ?", (1, "x"), "postgres") == "SELECT '?' , a FROM t WHERE b = 1 AND c = 'x'"
    with pytest.raises(ValueError):
        inline("a = ? AND b = ?", (1,), "postgres")
    with pytest.raises(ValueError):
        literal("a\x00b", "postgres")


class _Service(BaseHTTPRequestHandler):
    """A platform lending a connection: its shape, its read-only guard, its row limit. It runs on SQLite for the test."""

    db: sqlite3.Connection
    limit = 500

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("Authorization") != "Bearer good":
            return self._answer(401, {"detail": "no"})
        if body["connection_id"] != 7:
            return self._answer(404, {"detail": "DB 연결을 찾을 수 없습니다."})
        sql = body["query"]
        if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
            return self._answer(200, {"success": False, "columns": [], "rows": [], "row_count": 0, "error": "read only"})
        cur = self.db.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r)) for r in cur.fetchmany(min(body["max_rows"], self.limit))]
        self._answer(200, {"success": True, "columns": columns, "rows": rows, "row_count": len(rows), "error": None})

    def _answer(self, code, body):
        out = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture
def service():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.executescript("CREATE TABLE t (id TEXT PRIMARY KEY, name TEXT); INSERT INTO t VALUES ('a', 'O''Brien'), ('b', 'K');")
    _Service.db = db
    srv = HTTPServer(("127.0.0.1", 0), _Service)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/query"
    srv.shutdown()
    srv.server_close()


def test_a_platforms_connection_reads_like_any_source(service):
    g = GatewayBackend(service, connection=7, dialect="sqlite", token="good")
    assert g.fetch("SELECT name FROM t WHERE id = ?", ("a",)) == [("O'Brien",)]
    assert g.capabilities.write is False


def test_the_gateway_never_writes_and_says_what_went_wrong(service):
    g = GatewayBackend(service, connection=7, dialect="sqlite", token="good")
    with pytest.raises(PermissionError):
        g.run("DELETE FROM t")
    with pytest.raises(PermissionError):
        g.run_many([("DELETE FROM t", ())])
    with pytest.raises(GatewayError, match="read only"):
        g.fetch("DELETE FROM t")
    with pytest.raises(GatewayError, match="토큰"):
        GatewayBackend(service, connection=7, token="bad").fetch("SELECT 1")
    with pytest.raises(GatewayError, match="공유되지"):
        GatewayBackend(service, connection=8, token="good").fetch("SELECT 1")
    with pytest.raises(GatewayError, match="응답하지"):
        GatewayBackend("http://127.0.0.1:9/q", connection=1, timeout=1).fetch("SELECT 1")


def test_a_full_answer_is_marked_as_possibly_cut(service, monkeypatch):
    monkeypatch.setattr(_Service, "limit", 1)
    g = GatewayBackend(service, connection=7, dialect="sqlite", token="good", max_rows=1)
    assert len(g.fetch("SELECT id FROM t")) == 1 and g.truncated == 1


def test_a_whole_ontology_runs_through_a_gateway(service):
    pytest.importorskip("yaml")
    from xgen_space.config import open_backend
    from xgen_space.modules import Module
    from xgen_space.studio import Studio

    m = Module.from_dict({"module": "m", "version": "1.0.0", "kind": "domain", "namespace": "urn:m#", "objects": {
        "Thing": {"key": "id", "table": "t", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}}},
        "queries": {"named": {"params": {"who": "string"}, "query": {"match": {"x": "Thing"}, "where": {"eq": ["x.name", {"param": "who"}]},
                                                                      "return": ["x.id"]}}}})
    st = Studio.from_modules([m], name="m")
    st.add_backend("source", open_backend({"kind": "gateway", "url": service, "connection": 7, "dialect": "sqlite", "token": "good"}, Path(".")), source=True)
    assert st.run("named", {"who": "O'Brien"}).rows == [("a",)]


def test_the_api_is_described_for_whoever_imports_it():
    spec = openapi("1.2.3", "https://space.example")
    assert spec["openapi"].startswith("3.1") and spec["servers"][0]["url"] == "https://space.example"
    assert {r[0] for r in ROUTES} == set(spec["paths"])
    assert spec["paths"]["/v1/search"]["post"]["requestBody"]["content"]["application/json"]["schema"]["required"] == ["text"]
    assert {t["name"] for t in tool_list()} >= {"search_documents", "run_query", "decide", "describe_space"}


@pytest.fixture
def tools():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.tools import StudioTools

    return StudioTools(load_studio(CFG), read_only=True)


def test_rest_answers_with_a_token_and_only_then(tools):
    r = Rest(tools, "secret")
    assert r.allowed("Bearer secret") and not r.allowed("Bearer wrong") and not r.allowed("")
    assert not Rest(tools, "").allowed("Bearer ")
    code, out = r.answer("POST", "/v1/search", {"text": "주문상품 반품 기간", "k": 2})
    assert code == 200 and len(out["hits"]) == 2 and out["ontology"][0]["element"] == "object:OrderItem"
    assert r.answer("POST", "/v1/search", {})[0] == 400
    assert r.answer("GET", "/v1/search", {})[0] == 405
    assert r.answer("GET", "/v1/none", {})[0] == 404
    code, out = r.answer("GET", "/v1/space", {})
    assert code == 200 and out["ontology"]["objects"] == 19 and out["space"]["documents"] == 7
    assert r.answer("POST", "/v1/query", {"query": "revenueByCategory"})[1]["columns"] == ["category", "revenue", "items"]
    assert "SELECT" in r.answer("POST", "/v1/translate", {"query": "orderTotals", "to": "sql:postgres"})[1]["text"]
    assert r.answer("POST", "/v1/decide", {"decision": "shippingFee", "key": "O1"})[1]["outputs"]["fee"] == 0
    assert r.answer("POST", "/v1/query", {"query": "noSuchQuery"})[0] == 400


def test_a_read_only_token_cannot_request_and_a_role_holds(tools):
    from xgen_space.tools import StudioTools

    assert Rest(tools, "s").answer("POST", "/v1/actions", {"action": "requestReturn", "key": "I1001"})[0] == 403
    agent = StudioTools(tools.studio, role="customer_agent", principal={"customer_id": "C001"})
    r = Rest(agent, "s")
    rows = r.answer("POST", "/v1/query", {"query": "myOrders"})[1]["rows"]
    assert rows and {x["order_id"] for x in rows} <= {"O1", "O2"}


def test_the_server_serves_the_api_beside_the_page():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import socket

    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession
    from xgen_space.web.server import serve

    data = DataOptions(rest=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    threading.Thread(target=serve, args=(lambda: StudioSession(load_studio(CFG), data=data),),
                     kwargs={"port": port, "data": data, "quiet": True, "api": {"token": "tok"}}, daemon=True).start()
    base = f"http://127.0.0.1:{port}"

    def call(path, body=None, token=""):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    import time
    for _ in range(100):
        try:
            if call("/v1/openapi.json")[0] == 200:
                break
        except OSError:
            time.sleep(0.1)
    assert call("/v1/tools")[0] == 200
    assert call("/v1/space")[0] == 401 and call("/v1/space", token="bad")[0] == 401
    code, out = call("/v1/search", {"text": "운송장 번호", "k": 1}, "tok")
    assert code == 200 and out["hits"][0]["document"] == "배송안내"


def test_reasoners_swap_and_two_engines_of_one_logic_are_compared(tools):
    pytest.importorskip("owlrl")
    from xgen_space.reason.port import (
        HttpReasoner,
        Reasoner,
        agreement,
        open_reasoner,
        open_reasoners,
        register_reasoner,
    )

    st = tools.studio
    engines = open_reasoners(None)
    assert set(engines) == {"rules", "owlrl", "shacl"}
    assert len(engines["rules"].run(st.onto, st.projection).derived) == len(engines["owlrl"].run(st.onto, st.projection).derived) > 0

    class Half(Reasoner):
        kind, name, logic = "half", "half", "owl2rl"

        def infer(self, onto, projection):
            return open_reasoner({"kind": "owlrl"}).infer(onto, projection)[0][:3], []

    register_reasoner("half", lambda s: Half())
    rep = agreement({"owlrl": engines["owlrl"], "half": open_reasoner({"kind": "half"})}, st.onto, st.projection)
    assert rep["owl2rl"]["same"] is False and rep["owl2rl"]["only"]["owlrl"]
    assert agreement({"owlrl": engines["owlrl"]}, st.onto, st.projection)["owl2rl"]["same"] is True
    assert HttpReasoner("http://127.0.0.1:9/r", timeout=1).run(st.onto, st.projection).error
    with pytest.raises(ValueError):
        open_reasoner({"kind": "nothing"})


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    return StudioSession(load_studio(CFG), data=DataOptions(samples=ROOT / "examples" / "files"))


def test_the_page_reads_one_space_across_pipelines(session):
    st = session.space_state()
    assert st["documents"] == 7 and st["check"]["questions"] == 6 and st["stores"][0]["kind"] == "memory"
    found = session.space_search("주문상품 반품 기간", 3)
    assert found["hits"] and found["named"][0]["element"] == "object:OrderItem"
    with pytest.raises(ValueError):
        session.space_search("  ")
    session.upload("안내.md", "# 안내\n\n## 포인트\n\n포인트는 주문 금액의 1%를 적립합니다.\n".encode())
    assert session.space_state()["documents"] == 8
    assert session.space_search("포인트 적립", 1)["hits"][0]["document"] == "안내"
    session.use_samples()
    session.make_draft("가상 쇼핑몰")
    session.apply_draft()
    assert session.space_state()["documents"] == 8  # documents stay when the pipeline changes
    session.catalog_remove(["안내.md"])
    assert session.space_state()["documents"] == 7


def test_the_page_shows_ports_map_and_document_ontology(session):
    a = session.adapters()
    assert {b["name"] for b in a["backends"]} == {"source", "graph"} and "qdrant" in a["vector_kinds"]
    langs = {x["id"]: x for x in a["languages"]}  # every registered query compiled for every language, measured now
    assert langs["sparql"]["backends"] == ["graph"] and langs["sql:sqlite"]["backends"] == ["source"]
    assert all(x["compiled"] + len(x["refused"]) == a["queries"] for x in a["languages"]) and "sql:tsql" in langs
    rep = session.adapters_check()
    assert rep["vectors"]["memory"]["agree"] and rep["graph"]["agree"] == rep["graph"]["queries"]
    assert rep["runs"]["rules"]["count"] > 0 and set(rep["runs"]) == {r["name"] for r in a["reasoners"] if not r["missing"]}
    assert session.reasoner_run("rules")["count"] > 0
    with pytest.raises(LookupError):
        session.reasoner_run("nothing")
    m = session.space_map()
    ids = {n["id"] for n in m["nodes"]}
    assert {"object:Order", "table:orders", "document:배송안내", "vector:memory", "graph:graph", "reasoner:rules", "embedder"} <= ids
    assert all(e["source"] in ids and e["target"] in ids for e in m["edges"])
    words = {n["id"]: n["label"] for n in m["nodes"]}  # stores read as what they are, not as the keys in studio.yaml
    assert words["reasoner:rules"] == "추론기 · 규칙" and words["vector:memory"] == "벡터 저장소 · 메모리"
    assert words["graph:graph"].startswith("그래프 저장소") and next(n["label"] for n in m["nodes"] if n["table"] == "database") == "원천 DB"
    assert session.space_map_node("reasoner:rules")["label"] == "추론기 · 규칙"
    node = session.space_map_node("document:배송안내")
    assert any(x["kind"] == "vector_store" for x in node["impact"])
    q = session.space_queries()
    assert q["conformance"]["agree"] == q["conformance"]["queries"] == 5 and q["queries"][0]["rows"]
    assert session.object("Order")["documents"]
    g = session.space_graph()
    sec = next(n for n in g["nodes"] if n["module"] == "section")
    doc = next(e["source"] for e in g["edges"] if e["target"] == sec["id"])
    title = next(n["label"] for n in g["nodes"] if n["id"] == doc)
    assert session.space_section(title, sec["label"])["text"]


def test_a_store_needs_an_install_that_allows_connections(session):
    with pytest.raises(PermissionError):
        session.space_store("add", kind="qdrant", url="http://127.0.0.1:9")
    session.data.allow_connect = True
    with pytest.raises(ValueError, match="연결하지 못했습니다|쓰지 못했습니다"):
        session.space_store("add", kind="qdrant", url="http://127.0.0.1:9")
    assert list(session.space.stores) == ["memory"]
    assert len(session.space_store("add", "second", "memory")["stores"]) == 2
    assert len(session.space_store("remove", "second")["stores"]) == 1


def test_the_flow_and_the_board_hold_the_space(session):
    flow = session.flow()
    step = next(s for s in flow["steps"] if s["id"] == "index")
    assert step["documents"] == 7 and step["found"] == step["questions"] - 1 or step["found"] == step["questions"]
    assert any(g["condition"] == "min_found" for g in step["gates"]) and flow["passed"]
    b = session.monitor()
    floor = next(f for f in b["floors"] if f["id"] == "store")
    assert {t["key"] for t in floor["tags"]} == {"store.nodes", "store.chunks", "store.found", "store.reasoners"}
    assert b["parts"]["store"]["vectors"] == ["memory"] and b["parts"]["store"]["graphs"] == ["graph"]


def test_pipelines_outlive_the_server_where_repositories_do(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.repository import Repositories
    from xgen_space.web import DataOptions, StudioSession

    data = DataOptions(samples=ROOT / "examples" / "files", repositories=tmp_path)

    def start():
        return StudioSession(load_studio(CFG), data=data, repositories=Repositories(tmp_path))

    s = start()
    s.use_samples()
    s.make_draft("가상 쇼핑몰")
    s.apply_draft()
    assert (tmp_path / "pipelines" / "index.json").is_file()
    rows = s.studio.backends[s.studio.source].fetch('SELECT COUNT(*) FROM "주문"')[0][0]
    pid = s.pipeline

    again = start()
    assert [p["label"] for p in again.pipelines] == ["기본 파이프라인", "가상 쇼핑몰"]
    again.pipeline_use(pid)
    assert again.studio.backends[again.studio.source].fetch('SELECT COUNT(*) FROM "주문"')[0][0] == rows
    assert again.flow()["steps"][0]["tables"] and again.space_state()["documents"] >= 7
    again.pipeline_delete(pid)
    assert [p["label"] for p in start().pipelines] == ["기본 파이프라인"]
    assert not (tmp_path / "pipelines" / pid).exists()


def test_a_connected_pipeline_keeps_its_modules_and_no_secret(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.modules import Module
    from xgen_space.repository import Repositories
    from xgen_space.studio import Studio
    from xgen_space.web import DataOptions, StudioSession

    data = DataOptions(repositories=tmp_path)
    s = StudioSession(load_studio(CFG), data=data, repositories=Repositories(tmp_path))
    m = Module.from_dict({"module": "m", "version": "1.0.0", "kind": "domain", "namespace": "urn:m#", "objects": {
        "Thing": {"key": "id", "table": "t", "properties": {"id": {"type": "string"}}}}})
    st = Studio.from_modules([m], name="m")
    st.add_backend("source", GatewayBackend("http://platform.example/q", connection=7, token="s3cret-token"), source=True)
    s.pipelines.append({"id": "p2", "label": "연결 DB", "studio": st, "origin": {"kind": "database", "detail": "PostgreSQL db"}, "rows": [], "log": []})
    s.save_pipelines()
    written = "".join(f.read_text(encoding="utf-8") for f in (tmp_path / "pipelines").rglob("*") if f.is_file())
    assert "s3cret-token" not in written and "platform.example" not in written
    assert not (tmp_path / "pipelines" / "p2" / "data.sql").exists()
    again = StudioSession(load_studio(CFG), data=data, repositories=Repositories(tmp_path))
    assert [p["id"] for p in again.pipelines] == ["p1"]  # it asks to be connected again rather than opening with nothing
    assert any("다시 연결" in e["text"] for e in again.events)


def test_the_page_asks_for_what_a_platform_connection_needs(session):
    with pytest.raises(PermissionError):
        session.connect_gateway("http://x/q", 1, "t")
    session.data.allow_connect = True
    with pytest.raises(ValueError, match="주소와 연결 번호"):
        session.connect_gateway("", "", "t")
    with pytest.raises(ValueError) as e:
        session.connect_gateway("http://127.0.0.1:9/q", 3, "s3cret-token")
    assert "응답하지" in str(e.value) and "s3cret-token" not in str(e.value)


def test_live_draft_through_a_query_service_over_postgres():
    """A real PostgreSQL behind a service of the platform's shape: the whole way from the catalog queries to a compiled query."""
    dsn = os.environ.get("XSPACE_LIVE_PG")
    if not dsn:
        pytest.skip("XSPACE_LIVE_PG not set")
    psycopg = pytest.importorskip("psycopg")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    conn = psycopg.connect(dsn, autocommit=True)
    conn.execute("DROP TABLE IF EXISTS gw_items, gw_orders")
    conn.execute("CREATE TABLE gw_orders (order_id text PRIMARY KEY, status text, placed_at timestamp)")
    conn.execute("CREATE TABLE gw_items (item_id text PRIMARY KEY, order_id text REFERENCES gw_orders, qty integer, price numeric(10,2))")
    conn.execute("INSERT INTO gw_orders VALUES ('O1', 'PAID', '2026-10-01 10:00'), ('O''2', 'NEW', '2026-10-02 11:00')")
    conn.execute("INSERT INTO gw_items VALUES ('I1', 'O1', 2, 1500.50), ('I2', 'O''2', 1, 300)")

    class Service(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if not body["query"].lstrip().upper().startswith(("SELECT", "WITH")):
                out = {"success": False, "error": "read only", "rows": [], "columns": []}
            else:
                cur = conn.execute(body["query"])
                columns = [d[0] for d in cur.description]
                rows = [dict(zip(columns, [str(v) if v is not None and not isinstance(v, (int, float, str, bool)) else v for v in r]))
                        for r in cur.fetchmany(body["max_rows"])]
                out = {"success": True, "columns": columns, "rows": rows, "row_count": len(rows), "error": None}
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), Service)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        s = StudioSession(load_studio(CFG), data=DataOptions(allow_connect=True))
        s.connect_gateway(f"http://127.0.0.1:{srv.server_port}/query", 7, "t", "postgres", "플랫폼 주문")
        d = s.pending[0]
        assert {o.table for o in d.objects} >= {"gw_orders", "gw_items"} and d.links
        s.apply_draft()
        assert s.origin["detail"].startswith("쿼리 서비스 127.0.0.1")
        name = next(n for n, q in s.studio.onto.queries.items() if "gw_orders" in s.studio.translate(n, "sql:postgres").text.lower())
        assert s.studio.run(name).rows
        assert s.flow()["steps"][0]["rows"] == 4
    finally:
        srv.shutdown()
        srv.server_close()
        conn.execute("DROP TABLE IF EXISTS gw_items, gw_orders")
        conn.close()


def test_the_rules_screen_reads_what_the_modules_say(session):
    r = session.rules_state()
    assert {p["name"] for p in r["parameters"]} == {"free_shipping_amount", "base_shipping_fee", "price_auto_percent"}
    assert r["metrics"][0]["metric"] == "returnRate" and r["conflicts"][0]["status"] == "open"
    assert any(f["decision"] == "returnEligibility" for f in r["findings"])
    m = session.metric_run("returnRate")
    assert m["denominator"] > m["numerator"] > 0 and m["value"] == pytest.approx(100 * m["numerator"] / m["denominator"])
    assert m["notes"] == ["기간을 지정하지 않아 전체 기간 기준입니다."]
    d = session.decide("shippingFee", "O16")
    assert d["result"]["fee"] == 3000 and d["parameters"] == {"base_shipping_fee": 3000}


def test_a_pick_between_sources_waits_for_review_like_any_change(session):
    assert session.conflict_pick("vipExchangeWindow", "교환 정책서 2조", "정책서가 우선")["pending"]
    assert session.workspace.dirty
    assert next(c for c in session.studio.onto.source_conflicts() if c.id == "vipExchangeWindow").open  # not yet applied
    with pytest.raises(ValueError):
        session.conflict_pick("vipExchangeWindow", "없는 출처")
    with pytest.raises(LookupError):
        session.conflict_pick("없음", "x")


def test_a_view_rides_along_with_the_query_where_the_source_cannot_hold_one():
    from xgen_space.backends.sql import SqliteBackend
    from xgen_space.modules import Module
    from xgen_space.studio import Studio

    m = Module.from_dict({"module": "m", "version": "1.0.0", "kind": "domain", "namespace": "urn:m#", "objects": {
        "Entry": {"key": "id", "table": "ledger", "properties": {"id": {"type": "string"}, "kind": {"type": "string"}, "units": {"type": "integer"}}},
        "Refund": {"key": "id", "view": {"name": "refunds_v", "inline": True, "query": {
            "match": {"e": "Entry"}, "where": {"eq": ["e.kind", "REFUND"]}, "return": ["e.id", {"col": "e.units", "as": "refunded"}]}},
            "properties": {"id": {"type": "string"}, "refunded": {"type": "integer"}}}},
        "queries": {"refunds": {"query": {"match": {"r": "Refund"}, "return": ["r.id", "r.refunded"], "order": ["id"]}}}})
    st = Studio.from_modules([m], name="m")
    src = SqliteBackend()
    src.script("CREATE TABLE ledger (id TEXT PRIMARY KEY, kind TEXT, units INTEGER);"
               "INSERT INTO ledger VALUES ('a', 'SALE', 2), ('b', 'REFUND', 1);")
    st.add_backend("source", src, source=True)
    assert st.run("refunds").rows == [("b", 1)]  # no view was created in the source


def test_an_agent_carries_its_scope_and_the_studio_its_clock():
    from datetime import datetime

    from xgen_space.backends.sql import SqliteBackend
    from xgen_space.modules import Module
    from xgen_space.studio import Studio
    from xgen_space.tools import StudioTools

    m = Module.from_dict({"module": "m", "version": "1.0.0", "kind": "domain", "namespace": "urn:m#", "objects": {
        "T": {"key": "id", "table": "t", "properties": {"id": {"type": "string"}, "d": {"type": "integer", "expr": "days_between(today(), today())"}}}}})
    st = Studio.from_modules([m], name="m", now=lambda: datetime(2020, 1, 2))
    assert st.onto.clock().year == 2020
    src = SqliteBackend()
    src.script("CREATE TABLE t (id TEXT PRIMARY KEY);")
    st.add_backend("source", src, source=True)
    assert StudioTools(st, principal={"seller_id": "S1"}).actor.principal == {"seller_id": "S1"}
