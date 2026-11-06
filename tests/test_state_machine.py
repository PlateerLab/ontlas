"""Transitions with a guard and side effects, transitions on the clock, and an action asked again before it runs."""
import json
from datetime import datetime, timedelta

import pytest

from xgen_space import Ontology
from xgen_space.actions import ActionError, Actor, HttpCaller
from xgen_space.backends.sql import SqliteBackend
from xgen_space.cli import main
from xgen_space.modules import Module, compose
from xgen_space.studio import Studio

NOW = datetime(2026, 3, 15, 12, 0)
AGENT = Actor("agent", "agent", ["clerk"])
CLERK = Actor("clerk", "human", ["clerk"])


def _definition() -> dict:
    return {
        "ontology": "orders", "namespace": "https://example.com/o#",
        "parameters": {"auto_confirm_days": {"type": "integer", "value": 5}},
        "objects": {"Order": {
            "key": "order_id", "source": {"table": "orders"},
            "states": {"property": "status", "initial": "PAID",
                       "states": ["PAID", "SHIPPED", "DELIVERED", "CONFIRMED", "CANCELLED", "ARCHIVED"],
                       "transitions": [
                           {"from": "PAID", "to": "SHIPPED", "action": "ship",
                            "guard": {"decision": "canShip", "expect": {"ok": True}},
                            "set": {"shipped_on": "$today", "carrier": "$carrier"}},
                           {"from": "SHIPPED", "to": "DELIVERED", "action": "deliver", "guard": {"property": "signed"},
                            "set": {"delivered_on": "$today", "handled_at": "$now"}},
                           {"from": "PAID", "to": "CANCELLED", "action": "cancel"},
                           {"from": "SHIPPED", "to": "CANCELLED", "action": "cancel"},
                           {"from": "DELIVERED", "to": "CONFIRMED", "set": {"confirmed_by": "clock"},
                            "after": {"days": "@auto_confirm_days", "since": "delivered_on"}},
                           {"from": "CANCELLED", "to": "ARCHIVED", "after": {"days": 30, "since": "placed_at"},
                            "guard": {"property": "refunded"}}]},
            "properties": {
                "order_id": {"type": "string"}, "status": {"type": "string"}, "carrier": {"type": "string"},
                "weight": {"type": "integer"}, "signed": {"type": "boolean"}, "refunded": {"type": "boolean"},
                "note": {"type": "string"}, "confirmed_by": {"type": "string"}, "handled_at": {"type": "datetime"},
                "placed_at": {"type": "datetime"}, "shipped_on": {"type": "date"},
                "delivered_on": {"type": "date", "column": "DELIVER_YMD", "format": "YYYYMMDD"}}}},
        "decisions": {
            "canShip": {"target": "Order", "outputs": {"ok": "boolean"},
                        "inputs": {"weight": {"type": "integer", "property": "weight"}},
                        "rules": [{"id": "light", "when": {"weight": "<= 30"}, "then": {"ok": True}},
                                  {"id": "heavy", "when": {"weight": "> 30"}, "then": {"ok": False}}]},
            "freshOrder": {"target": "Order", "outputs": {"ok": "boolean"},
                           "inputs": {"age": {"type": "integer", "days_since": "placed_at"}},
                           "rules": [{"id": "new", "when": {"age": "<= 7"}, "then": {"ok": True}},
                                     {"id": "old", "when": {"age": "> 7"}, "then": {"ok": False}}]}},
        "actions": {
            "ship": {"target": "Order", "transition_to": "SHIPPED", "parameters": {"carrier": "string"}},
            "deliver": {"target": "Order", "transition_to": "DELIVERED"},
            "cancel": {"target": "Order", "transition_to": "CANCELLED",
                       "criteria": [{"decision": "freshOrder", "expect": {"ok": True}}]},
            "annotate": {"target": "Order", "parameters": {"note": "string"}, "set": {"note": "$note"},
                         "criteria": [{"states": ["PAID", "SHIPPED"]}]}},
        "roles": {"clerk": {"read": ["*"], "request": ["*"], "execute": ["*"], "run": ["*"]}},
    }


SEED = """
CREATE TABLE orders (order_id TEXT, status TEXT, carrier TEXT, weight INTEGER, signed INTEGER, refunded INTEGER,
                     note TEXT, confirmed_by TEXT, handled_at TEXT, placed_at TEXT, shipped_on TEXT, DELIVER_YMD TEXT);
INSERT INTO orders VALUES
 ('A', 'PAID', NULL, 10, 0, 0, NULL, NULL, NULL, '2026-03-14T09:00:00', NULL, NULL),
 ('B', 'PAID', NULL, 99, 0, 0, NULL, NULL, NULL, '2026-03-14T09:00:00', NULL, NULL),
 ('C', 'SHIPPED', 'K', 10, 1, 0, NULL, NULL, NULL, '2026-03-14T09:00:00', '2026-03-14', NULL),
 ('D', 'SHIPPED', 'K', 10, 0, 0, NULL, NULL, NULL, '2026-03-14T09:00:00', '2026-03-14', NULL),
 ('E', 'DELIVERED', 'K', 10, 1, 0, NULL, NULL, NULL, '2026-03-01T09:00:00', '2026-03-05', '20260310'),
 ('F', 'DELIVERED', 'K', 10, 1, 0, NULL, NULL, NULL, '2026-03-01T09:00:00', '2026-03-05', '20260311'),
 ('G', 'CANCELLED', NULL, 10, 0, 1, NULL, NULL, NULL, '2026-01-01T09:00:00', NULL, NULL),
 ('H', 'CANCELLED', NULL, 10, 0, 0, NULL, NULL, NULL, '2026-01-01T09:00:00', NULL, NULL);
"""


class _Clock:
    def __init__(self):
        self.now = NOW

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return _Clock()


def _studio(clock, d=None) -> Studio:
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d or _definition()).check(), now=clock)
    st.add_backend("source", b)
    return st


@pytest.fixture
def studio(clock) -> Studio:
    return _studio(clock)


def _failed(p):
    return {c.name for c in p.checks if not c.passed}


def test_a_transition_writes_its_side_effects(studio):
    p = studio.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    assert p.status == "pending", p.checks
    assert p.changes == {"shipped_on": "2026-03-15", "carrier": "K", "status": "SHIPPED"}
    studio.actions.approve(p.id, approver=CLERK)
    row = studio.fetch("Order", "A")
    assert (row["status"], row["shipped_on"], row["carrier"]) == ("SHIPPED", "2026-03-15", "K")


def test_a_guard_on_a_decision_stops_the_transition(studio):
    p = studio.actions.request("ship", "B", {"carrier": "K"}, actor=AGENT)
    assert p.status == "rejected" and _failed(p) == {"guard:canShip"}
    assert next(c.detail for c in p.checks if c.name == "guard:canShip") == "{'ok': False}"


def test_a_guard_on_a_property_stops_the_transition(studio):
    assert _failed(studio.actions.request("deliver", "D", actor=AGENT)) == {"guard:signed"}
    p = studio.actions.request("deliver", "C", actor=AGENT)
    studio.actions.approve(p.id, approver=CLERK)
    row = studio.fetch("Order", "C")
    assert row["delivered_on"] == "2026-03-15" and row["handled_at"] == "2026-03-15T12:00:00"
    assert studio.backend().fetch("SELECT DELIVER_YMD FROM orders WHERE order_id = 'C'")[0][0] == "20260315"


def test_a_wrong_state_still_says_state(studio):
    assert _failed(studio.actions.request("deliver", "A", actor=AGENT)) == {"state"}


def test_each_transition_of_an_action_is_its_own(studio):
    sm = studio.onto.obj("Order").states
    assert sm.find("PAID", "CANCELLED", "cancel").source == "PAID"
    assert sm.find("SHIPPED", "CANCELLED", "cancel").source == "SHIPPED"
    assert sm.find("PAID", "SHIPPED", "other").action == "ship"  # one that names another action is still the way there
    assert sm.find("PAID", "CONFIRMED") is None


def test_a_transition_can_call_out_after_the_write(clock):
    d = _definition()
    trans = d["objects"]["Order"]["states"]["transitions"]
    trans[0]["call"] = {"url": "https://carrier.example.com/pickup/$key", "body": {"carrier": "$carrier"}}
    d["actions"]["ship"]["undo"] = {"url": "https://carrier.example.com/pickup/$key/cancel"}
    st = _studio(clock, d)
    sent = []

    class Resp:
        status = 200

        def read(self, n):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def opener(req, timeout=None):
        sent.append((req.full_url, req.data))
        return Resp()

    p = st.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    assert _failed(p) == {"call"}  # no allowed host yet
    st.actions.caller = HttpCaller(["carrier.example.com"], opener=opener)
    p = st.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    st.actions.approve(p.id, approver=CLERK)
    assert p.status == "executed" and sent[0] == ("https://carrier.example.com/pickup/A", b'{"carrier": "K"}')
    st.actions.rollback(p.id, actor=CLERK)
    assert sent[1][0].endswith("/pickup/A/cancel") and st.fetch("Order", "A")["status"] == "PAID"


def test_a_call_with_no_way_back_cannot_be_rolled_back(clock):
    d = _definition()
    d["objects"]["Order"]["states"]["transitions"][0]["call"] = {"url": "https://carrier.example.com/pickup/$key"}
    st = _studio(clock, d)

    class Resp:
        status = 200

        def read(self, n):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    st.actions.caller = HttpCaller(["carrier.example.com"], opener=lambda req, timeout=None: Resp())
    p = st.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    st.actions.approve(p.id, approver=CLERK)
    with pytest.raises(ActionError, match="declares no undo"):
        st.actions.rollback(p.id, actor=CLERK)


def test_what_is_due_comes_from_the_clock_and_the_parameter(studio, clock):
    assert [(d.key, d.target) for d in studio.actions.due()] == [("E", "CONFIRMED"), ("G", "ARCHIVED"), ("H", "ARCHIVED")]
    clock.now = NOW + timedelta(days=1)
    assert "F" in [d.key for d in studio.actions.due()]
    clock.now = NOW - timedelta(days=1)
    assert "E" not in [d.key for d in studio.actions.due()]


def test_a_customer_value_moves_the_clock(clock):
    d = _definition()
    d["parameters"]["auto_confirm_days"]["value"] = 2
    assert [x.key for x in _studio(clock, d).actions.due() if x.target == "CONFIRMED"] == ["E", "F"]


def test_advancing_takes_what_is_due_with_its_side_effects_and_says_so(studio):
    done = studio.actions.advance()
    assert [(p.key, p.status) for p in done] == [("E", "executed"), ("G", "executed"), ("H", "rejected")]
    row = studio.fetch("Order", "E")
    assert row["status"] == "CONFIRMED" and row["confirmed_by"] == "clock"
    assert studio.fetch("Order", "G")["status"] == "ARCHIVED"
    assert studio.fetch("Order", "H")["status"] == "CANCELLED"  # its guard does not hold: left for the next round
    assert _failed(done[2]) == {"guard:refunded"}
    audit = studio.actions.audit
    assert audit[0].event == "executed" and audit[0].actor == "clock" and audit[0].actor_kind == "system"
    assert audit[0].action == "Order:DELIVERED->CONFIRMED" and audit[0].detail["before"]["status"] == "DELIVERED"
    assert [p.key for p in studio.actions.advance()] == ["H"]  # taken once


def test_the_clock_takes_its_own_transition_where_an_action_shares_the_states(clock):
    d = _definition()
    trans = d["objects"]["Order"]["states"]["transitions"]
    trans.insert(0, {"from": "DELIVERED", "to": "CONFIRMED", "action": "confirm", "set": {"confirmed_by": "person"}})
    d["actions"]["confirm"] = {"target": "Order", "transition_to": "CONFIRMED"}
    st = _studio(clock, d)
    st.actions.advance()
    assert st.fetch("Order", "E")["confirmed_by"] == "clock"


def test_a_call_on_the_clock_needs_an_allowed_host(clock):
    d = _definition()
    d["objects"]["Order"]["states"]["transitions"][4]["call"] = {"url": "https://notify.example.com/$key"}
    st = _studio(clock, d)
    p = st.actions.advance()[0]
    assert p.status == "rejected" and _failed(p) == {"call"}
    assert st.fetch("Order", "E")["status"] == "DELIVERED"


def test_a_transition_on_the_clock_is_not_rolled_back_as_an_action(studio):
    p = studio.actions.advance()[0]
    with pytest.raises(ActionError, match="taken on the clock"):
        studio.actions.rollback(p.id, actor=CLERK)


def test_a_request_goes_stale_when_the_state_moved_before_it_ran(studio):
    p = studio.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    studio.backend().run("UPDATE orders SET status = 'CANCELLED' WHERE order_id = 'A'")
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "stale" and p.approved_by == "clerk"
    assert {c.name: c.passed for c in p.revalidated} == {"target": True, "state": False}
    row = studio.fetch("Order", "A")
    assert row["status"] == "CANCELLED" and row["carrier"] is None  # nothing was written
    assert [e.event for e in studio.actions.audit] == ["requested", "approved", "stale"]
    assert studio.actions.audit[-1].detail == {"failed": ["state"]}
    with pytest.raises(ValueError, match="is stale"):
        studio.actions.approve(p.id, approver=CLERK)


def test_a_request_goes_stale_when_a_criterion_no_longer_holds(studio, clock):
    p = studio.actions.request("cancel", "A", actor=AGENT)
    assert p.status == "pending"
    clock.now = NOW + timedelta(days=10)  # the approver comes back too late
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "stale" and [c.name for c in p.revalidated if not c.passed] == ["decision:freshOrder"]
    assert studio.fetch("Order", "A")["status"] == "PAID"


def test_a_request_goes_stale_when_a_guard_no_longer_holds(studio):
    p = studio.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    studio.backend().run("UPDATE orders SET weight = 99 WHERE order_id = 'A'")
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "stale" and [c.name for c in p.revalidated if not c.passed] == ["guard:canShip"]


def test_a_request_goes_stale_when_a_state_criterion_or_the_row_is_gone(studio):
    p = studio.actions.request("annotate", "A", {"note": "x"}, actor=AGENT)
    studio.backend().run("UPDATE orders SET status = 'CONFIRMED' WHERE order_id = 'A'")
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "stale" and [c.name for c in p.revalidated if not c.passed] == ["states"]
    p = studio.actions.request("annotate", "C", {"note": "x"}, actor=AGENT)
    studio.backend().run("DELETE FROM orders WHERE order_id = 'C'")
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "stale" and [c.name for c in p.revalidated if not c.passed] == ["target"]


def test_a_request_goes_stale_when_the_row_leaves_the_requesters_scope(clock):
    d = _definition()
    d["objects"]["Order"]["properties"]["seller_id"] = {"type": "string"}
    d["actions"]["annotate"].pop("criteria")
    d["roles"]["seller"] = {"read": ["Order"], "request": ["annotate"],
                            "scope": {"attribute": "seller_id", "types": {"Order": "seller_id"}}}
    b = SqliteBackend()
    b.script(SEED + "ALTER TABLE orders ADD COLUMN seller_id TEXT; UPDATE orders SET seller_id = 'S1';")
    st = Studio(Ontology.from_dict(d).check(), now=clock)
    st.add_backend("source", b)
    p = st.actions.request("annotate", "A", {"note": "x"},
                           actor=Actor("alice", "agent", ["seller"], {"seller_id": "S1"}))
    assert p.status == "pending"
    b.run("UPDATE orders SET seller_id = 'S2' WHERE order_id = 'A'")
    st.actions.approve(p.id, approver=CLERK)
    assert p.status == "stale" and [c.name for c in p.revalidated if not c.passed] == ["scope"]


def test_a_request_that_still_holds_runs_as_before_and_says_it_was_asked(studio):
    p = studio.actions.request("ship", "A", {"carrier": "K"}, actor=AGENT)
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "executed" and [c.name for c in p.revalidated] == ["target", "state", "guard:canShip"]
    assert [e.event for e in studio.actions.audit] == ["requested", "approved", "executed"]
    assert json.loads(json.dumps(p.to_dict(), default=str))["revalidated"][0]["passed"] is True


def test_validate_holds_transitions_to_the_definition():
    d = _definition()
    trans = d["objects"]["Order"]["states"]["transitions"]
    trans += [
        {"from": "PAID", "to": "SHIPPED", "guard": {}, "set": {"nope": 1, "shipped_on": "$who"}},
        {"from": "PAID", "to": "DELIVERED", "guard": {"decision": "nope"}},
        {"from": "PAID", "to": "DELIVERED", "guard": {"decision": "canShip", "property": "signed", "when": "x"}},
        {"from": "PAID", "to": "DELIVERED", "guard": {"property": "nope"}},
        {"from": "PAID", "to": "DELIVERED", "guard": {"property": "weight"}},
        {"from": "PAID", "to": "ARCHIVED", "after": {"days": -1, "since": "note", "x": 1}},
        {"from": "PAID", "to": "ARCHIVED", "after": {"days": "@nope", "since": "nope"}},
        {"from": "PAID", "to": "ARCHIVED", "after": {"days": 1, "since": "placed_at"}, "action": "ship"},
        {"from": "PAID", "to": "ARCHIVED", "set": {"weight": "$now"}, "call": {"url": "ftp://x"}}]
    d["parameters"]["word"] = "x"
    trans.append({"from": "PAID", "to": "ARCHIVED", "after": {"days": "@word", "since": "placed_at"}})
    d["objects"]["Order"]["properties"]["doubled"] = {"type": "integer", "expr": "weight * 2"}
    trans.append({"from": "PAID", "to": "ARCHIVED", "set": {"doubled": 1}})
    issues = Ontology.from_dict(d).validate()
    head = "Order: transition "
    for text in ("PAID -> SHIPPED: sets unknown property 'nope'", "PAID -> SHIPPED: '$who' is not a parameter of any action",
                 "PAID -> DELIVERED: guard: unknown decision 'nope'", "PAID -> DELIVERED: guard: unknown keys ['when']",
                 "PAID -> DELIVERED: guard: give a decision or a property",
                 "PAID -> DELIVERED: guard: Order has no property 'nope'",
                 "PAID -> DELIVERED: guard: property 'weight' is integer, not a true/false value",
                 "PAID -> ARCHIVED: after: unknown keys ['x']", "PAID -> ARCHIVED: after: days takes a whole number or @parameter",
                 "PAID -> ARCHIVED: after: since 'note' is string, not a date or datetime",
                 "PAID -> ARCHIVED: after: unknown parameter '@nope'",
                 "PAID -> ARCHIVED: after: since takes a date or datetime property",
                 "PAID -> ARCHIVED: after: a transition on the clock is taken by no action",
                 "PAID -> ARCHIVED: call: url must start with http:// or https://",
                 "PAID -> ARCHIVED: after: parameter '@word' is string, not a whole number",
                 "PAID -> ARCHIVED: 'doubled' is computed and cannot be set"):
        assert head + text in issues, (text, issues)


def test_a_call_in_two_places_is_refused():
    d = _definition()
    d["actions"]["ship"]["call"] = {"url": "https://a.example.com"}
    d["objects"]["Order"]["states"]["transitions"][0]["call"] = {"url": "https://b.example.com"}
    assert "Order: transition PAID -> SHIPPED: action ship makes its own call; give one of them" in \
        Ontology.from_dict(d).validate()


def test_a_decision_about_another_type_cannot_guard():
    d = _definition()
    d["objects"]["Note"] = {"key": "k", "properties": {"k": {"type": "string"}}}
    d["decisions"]["canShip"]["target"] = "Note"
    d["decisions"]["canShip"]["inputs"] = {}
    d["decisions"]["canShip"]["rules"] = []
    assert "Order: transition PAID -> SHIPPED: guard: decision 'canShip' is not about Order" in \
        Ontology.from_dict(d).validate()


def test_the_definition_round_trips():
    onto = Ontology.from_dict(_definition())
    d = onto.to_dict()
    t = d["objects"]["Order"]["states"]["transitions"]
    assert t[0]["guard"] == {"decision": "canShip", "expect": {"ok": True}} and t[0]["set"]["carrier"] == "$carrier"
    assert t[4]["after"] == {"days": "@auto_confirm_days", "since": "delivered_on"}
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.to_dict() == d


def test_a_module_can_add_a_guarded_transition():
    d = _definition()
    d["module"] = "orders"
    del d["ontology"]
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["orders"], "extend": {"objects": {
        "Order": {"transitions_add": [{"from": "CONFIRMED", "to": "ARCHIVED", "guard": {"property": "refunded"},
                                       "after": {"days": 90, "since": "placed_at"}}]}}}})
    comp = compose([Module.from_dict(d), overlay])
    assert comp.issues == [] and comp.ontology.obj("Order").states.find("CONFIRMED", "ARCHIVED").after["days"] == 90


def test_a_definition_without_any_of_this_runs_as_it_did(studio):
    plain = studio.onto.obj("Order").states.find("PAID", "CANCELLED")
    assert plain.guard == {} and plain.set == {} and plain.after == {} and plain.call == {}


def test_the_command_line(tmp_path, capsys):
    yaml = pytest.importorskip("yaml")
    import sqlite3

    conn = sqlite3.connect(tmp_path / "shop.sqlite")
    conn.executescript(SEED)
    conn.close()
    (tmp_path / "ontology.json").write_text(json.dumps(_definition()), encoding="utf-8")
    (tmp_path / "studio.yaml").write_text(yaml.safe_dump({
        "ontology": "ontology.json", "backends": {"source": {"kind": "sqlite", "path": "shop.sqlite", "source": True}}}),
        encoding="utf-8")
    assert main(["transitions", str(tmp_path / "studio.yaml")]) == 0
    due = json.loads(capsys.readouterr().out)
    assert {"type": "Order", "key": "E", "source": "DELIVERED", "target": "CONFIRMED", "since": "delivered_on",
            "days": 5} in due
    assert main(["transitions", str(tmp_path / "studio.yaml"), "--apply"]) == 0
    assert {p["key"]: p["status"] for p in json.loads(capsys.readouterr().out)}["E"] == "executed"
    assert "E" not in [d["key"] for d in (main(["transitions", str(tmp_path / "studio.yaml")]),
                                          json.loads(capsys.readouterr().out))[1]]
