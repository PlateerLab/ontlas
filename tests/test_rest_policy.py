"""A /v1 caller with no access policy is refused: it would read every row unmasked. A server that means to let such a
caller read everything says so (ontlas serve --api-open)."""
import pytest

from ontlas.config import load_studio
from ontlas.rest import Rest
from ontlas.tools import StudioTools

from .conftest import LIB

VALUES = {"days_since_delivery": 3, "item_status": "NORMAL", "category_returnable": True, "customer_grade": "VIP"}
DECIDE = {"decision": "returnEligibility", "values": VALUES}


@pytest.fixture(scope="module")
def studio():
    pytest.importorskip("yaml")
    return load_studio(LIB / "studio.yaml")


def test_a_caller_with_no_policy_is_refused_with_why_and_what_to_do(studio):
    tools = StudioTools(studio, actor_id="xgen-workflow", audit=True)
    rest = Rest([("t", tools)])
    for method, path, body in [("POST", "/v1/decide", DECIDE), ("POST", "/v1/query", {"query": "myOrders"}),
                               ("GET", "/v1/ontology", {}), ("GET", "/v1/libraries", {})]:
        code, out = rest.answer(method, path, body, tools)
        assert code == 403 and out["no_policy"] is True, path
        assert "xgen-workflow" in out["error"] and "--api-role" in out["error"] and "--api-open" in out["error"]
    assert not [e for e in studio.actions.audit if e.actor == "xgen-workflow"]  # nothing was decided for it


def test_opened_by_the_server_it_reads_as_before(studio, monkeypatch):
    tools = StudioTools(studio, actor_id="xgen-workflow")
    assert Rest([("t", tools)], unscoped=True).answer("POST", "/v1/decide", DECIDE, tools)[0] == 200
    monkeypatch.setattr(Rest, "unscoped", True)  # ontlas serve --api-open
    code, out = Rest([("t", tools)]).answer("POST", "/v1/decide", DECIDE, tools)
    assert code == 200 and out["outputs"]["eligible"] is True


def test_a_caller_with_a_policy_is_answered_under_it(studio):
    tools = StudioTools(studio, role="operator", actor_id="ops-agent")
    code, out = Rest([("t", tools)]).answer("POST", "/v1/decide", DECIDE, tools)
    assert code == 200 and out["outputs"]["eligible"] is True


def test_the_page_tries_a_call_with_no_policy_as_the_server_would_answer_it(monkeypatch):
    pytest.importorskip("rdflib")
    from ontlas.web import routes
    from ontlas.web.api import StudioSession
    from ontlas.web.areas import ops

    routes.load()
    s = StudioSession(load_studio(LIB / "studio.yaml"))
    out = ops.try_call(s, {"path": "/v1/decide", "policy": "", "body": DECIDE}, None)
    assert out["status"] == 403 and out["body"]["no_policy"] is True
    assert ops.try_call(s, {"path": "/v1/decide", "policy": "operator", "body": DECIDE}, None)["status"] == 200
    monkeypatch.setattr(Rest, "unscoped", True)
    assert ops.try_call(s, {"path": "/v1/decide", "policy": "", "body": DECIDE}, None)["status"] == 200


def test_the_screen_is_told_how_a_caller_with_no_policy_is_answered(monkeypatch):
    pytest.importorskip("rdflib")
    from ontlas.web.api import StudioSession
    from ontlas.web.areas import ops

    s = StudioSession(load_studio(LIB / "studio.yaml"))
    monkeypatch.setitem(ops._REST, "rest", Rest([("t", StudioTools(s.studio, actor_id="xgen-workflow"))]))
    out = ops.targets(s, {}, None)
    assert out["unscoped"] is False and out["action_write"] is False
    assert [(t["name"], t["policy"]) for t in out["targets"]] == [("xgen-workflow", "")]
    monkeypatch.setitem(ops._REST, "rest", Rest([("t", StudioTools(s.studio, actor_id="xgen-workflow"))], unscoped=True))
    assert ops.targets(s, {}, None)["unscoped"] is True
