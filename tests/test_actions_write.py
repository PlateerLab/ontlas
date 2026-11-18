"""Writing to the data source is off unless the server is told otherwise (ontlas serve --action-write): an action that
would change the source runs its checks, is approved as usual and ends recorded, with what it would change and the
source left as it was."""
from pathlib import Path

import pytest

from ontlas.actions import ActionError, ActionService, Actor, HttpCaller, Settled
from ontlas.backends.sql import SqliteBackend
from ontlas.config import load_studio
from ontlas.modules import Module, compose
from ontlas.studio import Studio

from .conftest import NOW

SHOP = Path(__file__).resolve().parent.parent / "examples" / "library" / "studio.yaml"  # the example shop, l1

AGENT = Actor("agent-1", "agent", ["customer_agent"])
OPERATOR = Actor("op", "human", ["operator"])
OTHER = Actor("op-2", "human", ["operator"])


@pytest.fixture
def plain(onto, source):
    """The example studio as a library user, or a server started without --action-write, gets it."""
    st = Studio(onto, now=lambda: NOW)
    st.add_backend("source", source)
    return st


def test_off_by_default_an_approved_action_is_recorded_and_the_source_kept(plain):
    assert ActionService.write is False and plain.actions.write is False
    p = plain.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    assert p.status == "pending"
    plain.actions.approve(p.id, approver=OPERATOR)
    assert p.status == "recorded"
    assert p.before == {"item_status": "NORMAL"} and p.changes == {"item_status": "RETURN_REQUESTED"}
    assert plain.fetch("OrderItem", "I1001")["item_status"] == "NORMAL"
    assert [e.event for e in plain.actions.audit] == ["requested", "approved", "recorded"]
    assert plain.actions.audit[-1].detail == {"before": {"item_status": "NORMAL"}, "after": {"item_status": "RETURN_REQUESTED"}}


def test_turned_on_the_source_is_written_as_before(plain):
    plain.actions.write = True
    p = plain.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    plain.actions.approve(p.id, approver=OPERATOR)
    assert p.status == "executed"
    assert plain.fetch("OrderItem", "I1001")["item_status"] == "RETURN_REQUESTED"
    assert plain.actions.audit[-1].event == "executed" and plain.actions.audit[-1].detail["rows"] == 1


def test_a_server_turns_it_on_for_every_studio_it_makes_and_one_studio_may_keep_it_off(monkeypatch, onto):
    monkeypatch.setattr(ActionService, "write", True)
    a, b = Studio(onto), Studio(onto)
    b.actions.write = False
    assert a.actions.write is True and b.actions.write is False


def test_the_price_change_on_the_example_shop_leaves_the_price_alone():
    """The case that was found: a price changed from 59,000 to 12,345 was written to the source once approved."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio projects a graph
    st = load_studio(SHOP)
    before = st.fetch("Sku", "S1")["price"]
    p = st.actions.request("changePrice", "S1", {"price": 12345}, actor=OPERATOR)
    assert p.status == "pending"  # past the automatic limit, a person approves it
    st.actions.approve(p.id, approver=OTHER)
    assert p.status == "recorded" and p.changes == {"price": 12345} and p.before == {"price": before}
    assert st.fetch("Sku", "S1")["price"] == before
    inside = st.actions.request("changePrice", "S1", {"price": before + 1000}, actor=OPERATOR)
    assert inside.approved_by == "auto" and inside.status == "recorded"  # inside the limit it ran at once, recorded
    assert st.fetch("Sku", "S1")["price"] == before


def test_a_recorded_request_is_settled_and_has_nothing_to_roll_back(plain):
    p = plain.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    plain.actions.approve(p.id, approver=OPERATOR)
    with pytest.raises(Settled) as e:
        plain.actions.reject(p.id, approver=OPERATOR)
    assert e.value.code == "recorded"
    with pytest.raises(ActionError, match="only an executed action"):
        plain.actions.rollback(p.id, actor=OPERATOR)


def test_with_writing_off_an_executed_action_is_not_rolled_back_in_the_source(plain):
    plain.actions.write = True
    p = plain.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    plain.actions.approve(p.id, approver=OPERATOR)
    plain.actions.write = False
    with pytest.raises(ActionError, match="writing to the data source is off"):
        plain.actions.rollback(p.id, actor=OPERATOR)
    assert p.status == "executed" and plain.fetch("OrderItem", "I1001")["item_status"] == "RETURN_REQUESTED"


def _calling_studio(sent: list) -> Studio:
    """One order an action marks as shipped and tells a carrier about, and one that only tells the carrier."""
    m = Module.from_dict({"module": "calls", "version": "1.0.0", "kind": "domain", "namespace": "https://example.com/c#",
                          "objects": {"Order": {"key": "order_id", "source": {"table": "orders"},
                                                "properties": {"order_id": {"type": "string"}, "status": {"type": "string"}}}},
                          "actions": {
                              "ship": {"target": "Order", "approval": False, "set": {"status": "SHIPPED"},
                                       "call": {"url": "https://carrier.example.com/ship/$key"}},
                              "notify": {"target": "Order", "approval": False,
                                         "call": {"url": "https://carrier.example.com/notify/$key"}}},
                          "roles": {"clerk": {"read": ["*"], "request": ["*"], "execute": ["*"]}}})
    comp = compose([m])
    assert not comp.issues, comp.issues
    st = Studio(comp.ontology, now=lambda: NOW)
    b = SqliteBackend()
    b.script("CREATE TABLE orders (order_id TEXT PRIMARY KEY, status TEXT); INSERT INTO orders VALUES ('O1', 'PAID');")
    st.add_backend("source", b)

    class Reply:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            return b"{}"

    def opener(req, timeout=None):
        sent.append(req.full_url)
        return Reply()

    st.actions.caller = HttpCaller(["carrier.example.com"], opener=opener)
    return st


def test_an_action_that_writes_is_recorded_with_the_request_it_would_send_and_sends_none():
    sent: list = []
    st = _calling_studio(sent)
    p = st.actions.request("ship", "O1", {}, actor=Actor("kim", "human", ["clerk"]))
    assert p.status == "recorded" and sent == []
    assert p.call == {"method": "POST", "url": "https://carrier.example.com/ship/$key", "sent": False}
    assert st.fetch("Order", "O1")["status"] == "PAID"


def test_an_action_that_only_calls_out_is_not_a_write_and_still_runs():
    sent: list = []
    st = _calling_studio(sent)
    p = st.actions.request("notify", "O1", {}, actor=Actor("kim", "human", ["clerk"]))
    assert p.status == "executed" and sent == ["https://carrier.example.com/notify/O1"]


# ---- where it is turned on: the server's option, and the MCP server's ------------------------------------------------

def test_serve_turns_writing_on_only_when_told(monkeypatch):
    from ontlas import web
    from ontlas.cli import main
    from ontlas.rest import Rest

    monkeypatch.setattr(ActionService, "write", False)
    monkeypatch.setattr(Rest, "unscoped", False)
    monkeypatch.setattr(web, "serve_config", lambda *a, **kw: None)
    main(["serve", str(SHOP)])
    assert ActionService.write is False and Rest.unscoped is False
    main(["serve", str(SHOP), "--action-write"])
    assert ActionService.write is True and Rest.unscoped is False
    main(["serve", str(SHOP), "--api-open"])
    assert Rest.unscoped is True


def test_mcp_hands_the_option_on_and_turns_writing_on(monkeypatch):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio projects a graph
    from ontlas import mcp_server
    from ontlas.cli import main

    got = {}
    monkeypatch.setattr(mcp_server, "main", lambda argv: got.setdefault("argv", argv))
    main(["mcp", "studio.yaml", "--action-write"])
    assert got["argv"] == ["studio.yaml", "--transport", "stdio", "--action-write"]
    monkeypatch.undo()

    class Quiet:
        def run(self, transport):
            got["ran"] = transport

    def built(studio, **kw):
        return Quiet()

    monkeypatch.setattr(ActionService, "write", False)
    monkeypatch.setattr(mcp_server, "build_server", built)
    mcp_server.main([str(SHOP)])
    assert ActionService.write is False and got["ran"] == "stdio"
    mcp_server.main([str(SHOP), "--action-write"])
    assert ActionService.write is True


# ---- what the screens and a platform are told -------------------------------------------------------------------------

def test_the_screens_and_the_api_say_whether_a_run_writes(monkeypatch):
    pytest.importorskip("rdflib")
    from ontlas.tools import StudioTools
    from ontlas.web import routes
    from ontlas.web.api import StudioSession

    routes.load()
    s = StudioSession(load_studio(SHOP))
    state = routes.find("GET", "bnd/action/write")
    assert state(s, {}, None) == {"write": False, "writable": True}
    tried = routes.find("POST", "bnd/action/try")(s, {"action": "changePrice", "role": "operator", "key": "S1",
                                                       "params": {"price": 60000}}, None)
    assert tried["write"] is False and tried["writes"] is True
    assert StudioTools(s.studio, role="operator").describe_space()["action_write"] is False
    monkeypatch.setattr(ActionService, "write", True)
    s = StudioSession(load_studio(SHOP))
    assert state(s, {}, None)["write"] is True
    assert StudioTools(s.studio, role="operator").describe_space()["action_write"] is True
