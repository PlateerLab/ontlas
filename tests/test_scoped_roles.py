"""A role whose rows come from who is signed in: on reads, in decisions and on writes."""
import pytest

from ontlas import Ontology
from ontlas.actions import Actor
from ontlas.backends.sql import SqliteBackend
from ontlas.modules import Module, compose
from ontlas.roles import AccessDenied, decide_in_scope, in_scope, mask_style
from ontlas.studio import Studio

ALICE = {"seller_id": "S1"}
BOB = {"seller_id": "S2"}


def _definition() -> dict:
    return {
        "ontology": "market", "namespace": "https://example.com/m#",
        "objects": {
            "Product": {"key": "product_id", "source": {"table": "products"}, "properties": {
                "product_id": {"type": "string"}, "seller_id": {"type": "string"}, "name": {"type": "string"}}},
            "Order": {"key": "order_id", "source": {"table": "orders"}, "properties": {
                "order_id": {"type": "string"}, "status": {"type": "string"},
                "total": {"type": "decimal", "expr": "sum(hasLine.amount)"}}},
            "Line": {"key": "line_id", "source": {"table": "lines"}, "properties": {
                "line_id": {"type": "string"}, "order_id": {"type": "string"}, "product_id": {"type": "string"},
                "seller_id": {"type": "string"}, "amount": {"type": "decimal"}, "note": {"type": "string"},
                "replied_by": {"type": "string"}, "buyer_phone": {"type": "string", "mask": "partial"}}}},
        "links": {
            "lineOf": {"from": "Line", "to": "Order", "on": {"order_id": "order_id"}, "cardinality": "many_to_one",
                       "inverse": "hasLine"},
            "lineProduct": {"from": "Line", "to": "Product", "on": {"product_id": "product_id"},
                            "cardinality": "many_to_one"}},
        "queries": {"myLines": {"query": {"match": {"l": "Line"}, "return": ["l.line_id"], "order": ["line_id"]}}},
        "decisions": {"payable": {
            "target": "Line", "outputs": {"pay": "boolean"}, "inputs": {
                "amount": {"type": "decimal", "property": "amount"},
                "phone": {"type": "string", "property": "buyer_phone"}},
            "rules": [{"id": "big", "when": {"amount": ">= 100"}, "then": {"pay": True}},
                      {"id": "small", "when": {"amount": "< 100"}, "then": {"pay": False}}]}},
        "actions": {
            "reply": {"target": "Line", "parameters": {"note": "string"}, "approval": False,
                      "set": {"note": "$note", "replied_by": "$principal.seller_id"}},
            "move": {"target": "Line", "parameters": {"seller_id": "string"}, "set": {"seller_id": "$seller_id"}},
            "flag": {"target": "Line", "set": {"note": "flagged", "seller_id": "S9"}}},
        "roles": {
            "seller": {"read": ["Product", "Order", "Line"], "run": ["myLines", "payable"],
                       "request": ["reply", "move", "flag"], "execute": ["reply", "move", "flag"],
                       "scope": {"attribute": "seller_id", "types": {
                           "Product": "seller_id", "Line": "seller_id",
                           "Order": {"via": ["hasLine"], "property": "seller_id"}}}},
            "admin": {"read": ["*"], "run": ["*"], "request": ["*"], "execute": ["*"]}},
    }


SEED = """
CREATE TABLE products (product_id TEXT, seller_id TEXT, name TEXT);
INSERT INTO products VALUES ('P1', 'S1', 'Mug'), ('P2', 'S2', 'Plate');
CREATE TABLE orders (order_id TEXT, status TEXT);
INSERT INTO orders VALUES ('O1', 'open'), ('O2', 'open'), ('O3', 'open');
CREATE TABLE lines (line_id TEXT, order_id TEXT, product_id TEXT, seller_id TEXT, amount REAL, note TEXT,
                    replied_by TEXT, buyer_phone TEXT);
INSERT INTO lines VALUES ('L1', 'O1', 'P1', 'S1', 100, NULL, NULL, '010-1234-5678'),
                         ('L2', 'O1', 'P2', 'S2', 50, NULL, NULL, '010-1234-5678'),
                         ('L3', 'O2', 'P2', 'S2', 70, NULL, NULL, '010-2222-3333'),
                         ('L4', 'O3', 'P1', 'S1', 10, NULL, NULL, '010-4444-5555');
"""


def _studio(d=None) -> Studio:
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d or _definition()).check())
    st.add_backend("source", b)
    return st


@pytest.fixture
def studio() -> Studio:
    return _studio()


def _seller(name="alice", who=ALICE) -> Actor:
    return Actor(name, "human", ["seller"], dict(who))


def _ids(res):
    return [r[0] for r in res.rows]


def test_a_read_returns_only_the_signed_in_sellers_rows(studio):
    q = {"match": {"p": "Product"}, "return": ["p.product_id"]}
    assert _ids(studio.run(q, role="seller", principal=ALICE)) == ["P1"]
    assert _ids(studio.run(q, role="seller", principal=BOB)) == ["P2"]
    assert _ids(studio.run("myLines", role="seller", principal=ALICE)) == ["L1", "L4"]
    assert len(studio.run(q, role="admin").rows) == 2


def test_a_type_scoped_over_a_link_keeps_the_rows_that_reach_the_seller(studio):
    q = {"match": {"o": "Order"}, "return": ["o.order_id"], "order": ["order_id"]}
    assert _ids(studio.run(q, role="seller", principal=ALICE)) == ["O1", "O3"]
    assert _ids(studio.run(q, role="seller", principal=BOB)) == ["O1", "O2"]


def test_a_read_without_the_attribute_is_refused(studio):
    with pytest.raises(AccessDenied, match=r"needs principal attributes \['seller_id'\]"):
        studio.run({"match": {"p": "Product"}, "return": ["p.product_id"]}, role="seller")


def test_the_scope_reaches_joins_exists_and_aggregates(studio):
    q = {"match": {"l": "Line", "o": "Order"}, "edges": [["l", "lineOf", "o"]], "return": ["l.line_id", "o.order_id"],
         "order": ["line_id"]}
    assert studio.run(q, role="seller", principal=ALICE).rows == [("L1", "O1"), ("L4", "O3")]
    q = {"match": {"o": "Order"}, "return": ["o.order_id"], "order": ["order_id"],
         "where": {"exists": {"match": {"l": "Line"}, "edges": [["l", "lineOf", "o"]],
                              "where": {"gte": ["l.amount", 60]}}}}
    assert _ids(studio.run(q, role="seller", principal=BOB)) == ["O2"]  # O1's line of 100 is another seller's
    q = {"match": {"l": "Line"}, "return": [{"sum": "l.amount", "as": "total"}]}
    assert studio.run(q, role="seller", principal=BOB).rows == [(120.0,)]


def test_row_filters_still_apply_on_top(studio):
    d = _definition()
    d["roles"]["seller"]["row_filters"] = {"Line": {"gte": ["$self.amount", 50]}}
    q = {"match": {"l": "Line"}, "return": ["l.line_id"]}
    assert _ids(_studio(d).run(q, role="seller", principal=ALICE)) == ["L1"]


def test_a_total_over_rows_outside_the_scope_is_hidden(studio):
    q = {"match": {"o": "Order"}, "return": ["o.order_id", "o.total"], "order": ["order_id"]}
    res = studio.run(q, role="seller", principal=ALICE)
    assert res.rows == [("O1", "***"), ("O3", "***")] and res.masked == {"total": "full"}
    with pytest.raises(AccessDenied, match="masked and may not filter"):
        studio.run({"match": {"o": "Order"}, "where": {"gt": ["o.total", 100]}, "return": ["o.order_id"]},
                   role="seller", principal=ALICE)
    assert studio.run(q, role="admin").rows[0] == ("O1", 150.0)
    d = _definition()
    d["roles"]["seller"]["unmask"] = ["Order.total"]
    assert _studio(d).run(q, role="seller", principal=ALICE).rows[0] == ("O1", 150.0)


def test_a_decision_is_closed_to_the_role_until_it_is_asked_in_scope(studio):
    with pytest.raises(AccessDenied, match="may not run decision 'payable'"):
        studio.decide("payable", "L2", role="seller")
    res = decide_in_scope(studio, "payable", "L1", "seller", ALICE)
    assert res.outputs == {"pay": True}
    assert res.inputs["phone"] == "***-****-5678" and res.evidence[1].value == "***-****-5678"
    with pytest.raises(AccessDenied, match="outside the scope of role seller"):
        decide_in_scope(studio, "payable", "L2", "seller", ALICE)
    with pytest.raises(AccessDenied, match="needs principal"):
        decide_in_scope(studio, "payable", "L1", "seller", {})
    with pytest.raises(AccessDenied, match="may not run"):
        decide_in_scope(studio, "nothing", "L1", "seller", ALICE)
    assert studio.decide("payable", "L2", role="admin").outputs == {"pay": False}


def test_a_seller_acts_on_their_own_row(studio):
    p = studio.actions.request("reply", "L1", {"note": "shipped today"}, actor=_seller())
    assert p.status == "executed", p.checks
    row = studio.fetch("Line", "L1")
    assert row["note"] == "shipped today" and row["replied_by"] == "S1"  # filled in from who is signed in


def test_another_sellers_row_is_refused_and_nothing_of_it_comes_back(studio):
    p = studio.actions.request("reply", "L2", {"note": "x"}, actor=_seller())
    assert p.status == "rejected" and p.changes == {} and p.before == {}
    assert {c.name for c in p.checks if not c.passed} == {"scope"}
    assert [c.name for c in p.checks] == ["role", "parameters", "scope"]  # no check that would read the row
    assert studio.fetch("Line", "L2")["note"] is None
    assert [e.event for e in studio.actions.audit] == ["rejected"]


def test_a_write_without_the_attribute_is_refused(studio):
    p = studio.actions.request("reply", "L1", {"note": "x"}, actor=Actor("x", "human", ["seller"]))
    assert p.status == "rejected" and "needs principal attributes" in p.checks[-1].detail


def test_the_scope_attribute_is_filled_in_and_cannot_be_chosen(studio):
    p = studio.actions.request("move", "L1", {}, actor=_seller())
    assert all(c.passed for c in p.checks) and p.params["seller_id"] == "S1" and p.changes == {"seller_id": "S1"}
    p = studio.actions.request("move", "L1", {"seller_id": "S1"}, actor=_seller())
    assert all(c.passed for c in p.checks)
    p = studio.actions.request("move", "L1", {"seller_id": "S2"}, actor=_seller())
    assert p.status == "rejected" and "'S2' is not alice's own" in p.checks[1].detail


def test_a_fixed_value_cannot_move_a_row_out_of_the_scope(studio):
    p = studio.actions.request("flag", "L1", {}, actor=_seller())
    assert p.changes == {"note": "flagged", "seller_id": "S1"}


def test_an_unscoped_role_writes_as_before(studio):
    admin = Actor("root", "human", ["admin"])
    p = studio.actions.request("move", "L1", {"seller_id": "S2"}, actor=admin)
    assert p.status == "pending" and p.changes == {"seller_id": "S2"}
    both = Actor("both", "human", ["seller", "admin"], dict(ALICE))
    assert studio.actions.request("move", "L2", {"seller_id": "S1"}, actor=both).status == "pending"


def test_an_approver_in_another_scope_cannot_approve(studio):
    p = studio.actions.request("move", "L1", {}, actor=Actor("agent", "agent", ["seller"], dict(ALICE)))
    assert p.status == "pending"
    with pytest.raises(PermissionError, match="outside the scope of bob"):
        studio.actions.approve(p.id, approver=_seller("bob", BOB))
    assert p.status == "pending"
    studio.actions.approve(p.id, approver=_seller())
    assert p.status == "executed"


def test_a_rollback_stays_in_the_scope(studio):
    p = studio.actions.request("reply", "L1", {"note": "x"}, actor=_seller())
    with pytest.raises(PermissionError, match="outside the scope of bob"):
        studio.actions.rollback(p.id, actor=_seller("bob", BOB))
    studio.actions.rollback(p.id, actor=_seller())
    assert studio.fetch("Line", "L1")["note"] is None


def test_in_scope_asks_like_a_read(studio):
    role = studio.onto.roles["seller"]
    assert in_scope(studio, role, "Order", "O1", BOB) and not in_scope(studio, role, "Order", "O3", BOB)
    assert not in_scope(studio, role, "Order", "nope", BOB)


def test_a_subtype_of_a_scoped_type_is_scoped_too():
    d = _definition()
    d["objects"]["BonusLine"] = {"key": "line_id", "parent": "Line", "source": {"table": "lines"}, "properties": {
        "line_id": {"type": "string"}, "seller_id": {"type": "string"}}}
    d["roles"]["seller"]["read"].append("BonusLine")
    st = _studio(d)
    assert _ids(st.run({"match": {"g": "BonusLine"}, "return": ["g.line_id"], "order": ["line_id"]}, role="seller",
                       principal=ALICE)) == ["L1", "L4"]


def test_validate_refuses_a_scope_that_says_nothing_or_leaks():
    d = _definition()
    d["roles"]["a"] = {"scope": {"types": {"Nope": "x", "Line": "nope", "Order": {"via": ["nowhere"], "property": "p"},
                                           "Product": {"via": ["lineProduct"]}}, "extra": 1}}
    d["roles"]["b"] = {"scope": {"attribute": "seller_id"}}
    issues = Ontology.from_dict(d).validate()
    for text in ("role a: scope: needs attribute: what the principal says it belongs to",
                 "role a: scope: unknown key 'extra'", "role a: scope: unknown type 'Nope'",
                 "role a: scope: Line: Line has no property 'nope'", "role a: scope: Order: unknown link 'nowhere' in via",
                 "role a: scope: Product: give a property, or {via: [links], property}",
                 "role b: scope: needs types: the property that holds it on each type"):
        assert text in issues, issues


def test_validate_refuses_reading_a_parent_in_full():
    d = _definition()
    d["objects"]["Item"] = {"key": "line_id", "properties": {"line_id": {"type": "string"}}}
    d["objects"]["Line"]["parent"] = "Item"
    d["roles"]["seller"]["read"].append("Item")
    assert "role seller: scope: it reads Item in full, whose subtypes are scoped; scope Item or do not read it" in \
        Ontology.from_dict(d).validate()


def test_the_definition_round_trips():
    onto = Ontology.from_dict(_definition())
    d = onto.to_dict()
    assert d["roles"]["seller"]["scope"]["types"]["Line"] == "seller_id"
    assert "scoped" not in d["roles"]["seller"] and "closed" not in d["roles"]["seller"]
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.roles["seller"].scoped == onto.roles["seller"].scoped


def _module(d) -> Module:
    d = dict(d)
    d["module"] = "market"
    del d["ontology"]
    return Module.from_dict(d)


def test_a_customer_module_can_widen_what_a_scope_covers():
    d = _definition()
    del d["roles"]["seller"]["scope"]["types"]["Product"]
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["market"], "extend": {"roles": {
        "seller": {"scope": {"types": {"Product": "seller_id"}}}}}})
    comp = compose([_module(d), overlay])
    assert comp.issues == [] and set(comp.ontology.roles["seller"].scoped) == {"Product", "Line", "Order"}
    assert comp.ontology.roles["seller"].scope["attribute"] == "seller_id"


def test_taking_the_property_away_fails_closed():
    gone = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["market"],
                             "remove": {"properties": {"Product": ["seller_id"]}}})
    assert "role seller: scope: Product: Product has no property 'seller_id'" in compose([_module(_definition()), gone]).issues


def test_taking_a_type_away_takes_its_entry():
    d = _definition()
    d["objects"]["Extra"] = {"key": "k", "properties": {"k": {"type": "string"}}}
    d["roles"]["seller"]["scope"]["types"]["Extra"] = "k"
    gone = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["market"], "remove": {"objects": ["Extra"]}})
    comp = compose([_module(d), gone])
    assert comp.issues == [] and "Extra" not in comp.ontology.roles["seller"].scope["types"]


def test_mask_style_reads_the_scope_for_a_computed_property(studio):
    onto = studio.onto
    assert mask_style(onto, onto.roles["seller"], "Order", "total") == "full"
    assert mask_style(onto, onto.roles["admin"], "Order", "total") == ""
