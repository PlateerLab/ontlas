"""A studio with no source: definitions, rules, decisions on given values, documents and changes work, and what reads
rows answers "no source" in its own shape instead of failing."""
import json
import shutil
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from ontlas import Ontology
from ontlas.backends.base import NoSource
from ontlas.cli import main

from .conftest import EXAMPLE, NOW

pytest.importorskip("yaml")

MODULES = "[core, commerce, commerce-operations]"  # the definitions without the modules that bind them to tables
IN_WINDOW = {"days_since_delivery": 3, "item_status": "NORMAL", "category_returnable": True}


def _no_backend(tmp_path: Path, tail: str = "") -> Path:
    """The example studio file without its backends, over a copy of the examples, so nothing writes to the repo."""
    root = tmp_path / "examples"
    shutil.copytree(EXAMPLE.parent, root)
    text = (root / "library" / "studio.yaml").read_text(encoding="utf-8")
    text = text[:text.index("backends:")].replace(text[text.index("modules: ["):].split("\n", 1)[0], f"modules: {MODULES}")
    cfg = root / "library" / "nodb.yaml"
    cfg.write_text(text + tail, encoding="utf-8")
    return cfg


@pytest.fixture
def cfg(tmp_path) -> Path:
    return _no_backend(tmp_path)


@pytest.fixture
def session(cfg):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    return StudioSession(load_studio(cfg))


@pytest.mark.parametrize("tail", ["", "backends: {}\n"])
def test_a_studio_with_no_backend_loads_and_says_so(tmp_path, tail):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    st = load_studio(_no_backend(tmp_path, tail))
    assert st.backends == {} and st.source == "" and len(st.onto.objects) == 18
    state = StudioSession(st).state()
    assert state["source"] == {"connected": False, "name": "", "kind": ""} and state["stats"]["decisions"] == 2
    with pytest.raises(NoSource):
        st.run("ordersOfCustomer", {"customer": "C001"})
    with pytest.raises(NoSource):
        st.decide("returnEligibility", "I1001")


def test_a_studio_with_a_source_says_which():
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    pytest.importorskip("rdflib")
    st = load_studio(EXAMPLE.parent / "library" / "studio.yaml")
    assert StudioSession(st).state()["source"] == {"connected": True, "name": "source", "kind": "sqlite"}
    assert not any(g.get("unmeasured") for g in st.gates()["gates"])  # with a source every condition is measured


def test_what_reads_only_the_definition_works(session):
    st = session.studio
    got = st.decide("returnEligibility", inputs=dict(IN_WINDOW))
    assert got.outputs["eligible"] is True and got.matched == ["in-window"]
    sim = session.simulate("returnEligibility", "", {"days_since_delivery": 12, "item_status": "NORMAL",
                                                     "category_returnable": True})
    assert sim["matched"] == ["expired"] and sim["yes"] is False and sim["other"]  # a nearer value would answer otherwise
    assert all(q["passed"] is None and q["unmeasured"] == "no_source" for q in sim["questions"])
    assert "MATCH" in st.translate("ordersOfCustomer", "cypher").text
    q = session.run_query("ordersOfCustomer", {"customer": "C001"})
    assert q["ok"] and q["results"] == [] and q["no_source"] and any(t["ok"] for t in q["translations"])
    assert all("원천" in t["error"] for t in q["translations"] if not t["ok"])  # said in the page's words
    assert session.object("Customer")["properties"] and "Customer" in session.export_owl()
    assert session.space_search("반품", 3)["hits"]
    assert session.manage_state()["objects"]


def test_what_reads_rows_gives_the_typed_empty_answer(session):
    assert session.keys("Order") == []
    rec = session.record_list("Order")
    assert rec["rows"] == [] and rec["total"] == 0 and rec["no_source"] and rec["columns"]
    assert session.record_find("O1")["no_source"]
    for out in (session.object_rows("Order"), session.object_profile("OrderItem"), session.value_state(),
                session.agreement(), session.bindings(), session.function_run("refundEstimate", "I1001", {})):
        assert out["ok"] is False and out["no_source"] is True and "원천" in out["error"]
    q = session.questions()
    assert q["accuracy"] is None and q["measured"] == 0 and q["unmeasured"] == len(q["results"]) > 0 and q["no_source"]
    assert all(r["passed"] is None and r["note"] == "측정 대상 아님 (원천 미연결)" for r in q["results"])
    assert session.identities()["no_source"]
    for call in (lambda: session.record_page("Order", "O1"), lambda: session.decide("returnEligibility", "I1001"),
                 lambda: session.sync(), lambda: session.transitions_advance(),
                 lambda: session.request("requestReturn", "I1001", {}, "")):
        with pytest.raises(NoSource):
            call()
    links = session.connections()
    assert links["stores"] == [] and links["source"]["connected"] is False


def test_the_flow_does_not_fail_on_stages_that_need_rows(session):
    flow = session.flow()
    assert flow["passed"] is True and flow["gates"]["unmeasured"] > 0
    steps = {s["id"]: s for s in flow["steps"]}
    for stage in ("bind", "project", "query", "decide", "check"):
        assert steps[stage]["note"] == "측정 대상 아님 (원천 미연결)"
    gates = [g for s in flow["steps"] for g in s["gates"]]
    assert all(g["passed"] for g in gates) and {g["stage"] for g in gates if g["unmeasured"]} == {"bind", "query", "decide",
                                                                                                    "check"}
    assert next(g for g in gates if g["stage"] == "index")["unmeasured"] == ""  # documents are measured without a source
    assert session.studio.gates()["passed"] is True
    assert session.monitor()["status"] == "ok"
    # a change that touches only the definition is reviewed and applied
    session.manage_edit("add_property", {"object": "Customer", "name": "memo", "type": "string", "label": "메모"})
    trial = session.manage_trial()
    assert trial["passed"] and all(g["note"] for g in trial["gates"] if g["unmeasured"])
    out = session.manage_propose()
    assert out["ok"] and out["change"]["status"] == "approved"
    assert "memo" in [p["name"] for p in session.object("Customer")["properties"]]


def test_the_page_routes_answer_without_a_source(cfg):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession
    from ontlas.web.server import RateLimit, Sessions, make_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(lambda: StudioSession(load_studio(cfg)), spare=0),
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
        code, state = call("/api/state")
        assert code == 200 and state["source"]["connected"] is False
        for path in ("manage", "files", "inbox", "build/steps", "flow", "issues", "monitor", "connections", "adapters",
                     "explorer", "rules", "values", "agreement", "identities", "space", "space/map", "keys?type=Order",
                     "records?type=Order", "records/find?q=O1", "object/rows?name=Order", "integrations"):
            code, body = call(f"/api/{path}")
            assert code == 200, (path, body)
            assert "KeyError" not in json.dumps(body) and "unknown backend" not in json.dumps(body), path
        assert call("/api/records?type=Order")[1]["no_source"] is True
        for path, body in (("/api/record?type=Order&key=O1", None), ("/api/decide", {"name": "returnEligibility", "key": "I1001"}),
                           ("/api/sync", {}), ("/api/transitions/advance", {}),
                           ("/api/request", {"action": "requestReturn", "key": "I1001", "kind": "human"})):
            code, out = call(path, body)
            assert code == 409 and out["no_source"] is True and out["error"].startswith("원천 데이터가 연결되어 있지 않아"), path
        code, out = call("/api/decide/simulate", {"name": "returnEligibility", "inputs": IN_WINDOW})
        assert code == 200 and out["outputs"]["eligible"] is True
        code, out = call("/api/questions", {})
        assert code == 200 and out["accuracy"] is None and out["no_source"]
        code, out = call("/api/flow")
        assert code == 200 and out["passed"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_api_for_platforms_says_no_source():
    from ontlas.rest import Rest
    from ontlas.studio import Studio
    from ontlas.tools import StudioTools

    st = Studio(Ontology.load(EXAMPLE / "ontology.yaml").check(), now=lambda: NOW)
    rest = Rest(StudioTools(st))
    code, out = rest.answer("POST", "/v1/query", {"query": "ordersOfCustomer", "params": {"customer": "C001"}})
    assert code == 409 and out["no_source"] is True
    code, out = rest.answer("POST", "/v1/translate", {"query": "ordersOfCustomer", "to": "sparql"})
    assert code == 200 and "SELECT" in out["text"]


def test_cli_without_a_source(cfg, capsys):
    code = main(["decide", str(cfg), "returnEligibility", *sum((["--input", f"{k}={json.dumps(v)}"] for k, v in IN_WINDOW.items()), [])])
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["outputs"]["eligible"] is True and out["evidence"] == []
    assert main(["decide", str(cfg), "returnEligibility", "I1001"]) == 2
    assert "no source is connected" in capsys.readouterr().err
    assert main(["run", str(cfg), "ordersOfCustomer", "--param", "customer=C001"]) == 2
    capsys.readouterr()
    assert main(["questions", str(cfg)]) == 0 and json.loads(capsys.readouterr().out)["unmeasured"] > 0
    assert main(["gates", str(cfg)]) == 0 and json.loads(capsys.readouterr().out)["passed"] is True
    assert main(["modules", str(cfg)]) == 0


def test_ontlas_new_starts_from_nothing_and_takes_hand_made_definitions(tmp_path, capsys):
    from ontlas.config import load_studio
    from ontlas.library import Library
    from ontlas.web.api import StudioSession

    folder = tmp_path / "support"
    assert main(["new", str(folder), "--label", "고객 지원"]) == 0
    assert "ontlas serve" in json.loads(capsys.readouterr().out)["next"]
    assert "backends" not in (folder / "studio.yaml").read_text(encoding="utf-8") and (folder / "library").is_dir()
    with pytest.raises(SystemExit):
        main(["new", str(folder)])  # an existing studio is never written over

    st = load_studio(folder / "studio.yaml")
    assert st.onto.objects == {} and list(st.composition.modules) == []
    s = StudioSession(st)
    s.store = Library(folder / "library")  # as `ontlas serve --library-write` does
    s._adopt(s.studio)
    assert s.state()["title"] == "고객 지원" and s.state()["source"]["connected"] is False
    s.manage_edit("add_object", {"name": "Ticket", "label": "문의", "key": "ticket_id",
                                 "properties": {"ticket_id": {"type": "string", "label": "문의 번호", "required": True}}})
    s.manage_edit("add_property", {"object": "Ticket", "name": "grade", "type": "enum", "label": "고객 등급",
                                   "values": ["VIP", "BASIC"]})
    s.manage_edit("add_property", {"object": "Ticket", "name": "waited_hours", "type": "integer", "label": "대기 시간"})
    out = s.manage_propose()
    assert out["ok"] and out["change"]["status"] == "approved"
    assert sorted(p["name"] for p in s.object("Ticket")["properties"]) == ["grade", "ticket_id", "waited_hours"]
    s.manage_edit("add_decision", {"name": "escalate", "label": "상위 담당 이관", "target": "Ticket",
                                   "inputs": {"grade": {"type": "string", "property": "grade"},
                                              "waited_hours": {"type": "integer", "property": "waited_hours"}}})
    s.manage_edit("add_rule", {"decision": "escalate", "id": "vip-wait", "first": True,
                               "when": {"grade": {"op": "eq", "value": "VIP"}, "waited_hours": {"op": "gte", "value": "24"}},
                               "then": {"result": True, "reason": "VIP 고객이 오래 기다렸습니다"}})
    assert s.manage_propose()["ok"]
    assert s.simulate("escalate", "", {"grade": "VIP", "waited_hours": 30})["outputs"]["result"] is True
    assert s.simulate("escalate", "", {"grade": "BASIC", "waited_hours": 30})["outputs"]["result"] is False

    again = load_studio(folder / "studio.yaml")  # what was approved is the studio's on its next start
    assert "Ticket" in again.onto.objects and "escalate" in again.onto.decisions
    assert again.decide("escalate", inputs={"grade": "VIP", "waited_hours": 25}).outputs["result"] is True
