import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from xgen_data_studio import Ontology
from xgen_data_studio.actions import ActionError, Actor, HttpCaller, check_parameters, render
from xgen_data_studio.compile.base import CompileError, compiler_for
from xgen_data_studio.expr import ExprError, check_computed, dependencies, parse_expr
from xgen_data_studio.roles import AccessDenied, mask_value

from .conftest import EXAMPLE

AGENT = Actor("agent-1", "agent", ["customer_agent"])
OPERATOR = Actor("op", "human", ["operator"])


def test_computed_properties_answer_the_same_from_sql_and_the_graph(graph_studio):
    st = graph_studio
    assert st.run("orderTotals").rows == [("O1", "DELIVERED", 2, 97000.0), ("O2", "SHIPPED", 1, 59000.0),
                                          ("O3", "DELIVERED", 2, 74000.0), ("O4", "CANCELLED", 1, 19000.0)]
    assert st.run("skuPrices").rows == [("S1", 69000.0, 59000.0, 59000.0), ("S2", 69000.0, 59000.0, 59000.0),
                                        ("S3", 19000.0, 19000.0, 19000.0), ("S4", None, None, 15000.0)]
    rep = st.conformance()
    assert rep.passed, rep.summary()
    # a computed property is a definition, not a copy: the graph holds no triple for it
    assert not any(":total>" in t[1] or "#total>" in t[1] for t in st.projection.triples(st.onto))


def test_expressions_follow_one_null_rule_in_every_language(graph_studio):
    st = graph_studio
    d = st.onto.to_dict()
    item = d["objects"]["OrderItem"]["properties"]
    item["per_unit"] = {"type": "decimal", "expr": "line_total / (quantity - quantity)"}  # always / 0
    item["wrapped"] = {"type": "string", "expr": "if(delivered_at > '2026-10-20', 'late', 'early')"}
    item["days"] = {"type": "integer", "expr": "days_between(delivered_at, '2026-10-30')"}
    item["shown"] = {"type": "string", "expr": "concat(lower(item_status), '/', upper(item_id))"}
    d["objects"]["Order"]["properties"]["lines"] = {"type": "integer", "expr": "count(hasItem.delivered_at)"}
    st.onto = Ontology.from_dict(d).check()
    st.project()
    q = {"match": {"i": "OrderItem"}, "return": ["i.item_id", "i.per_unit", "i.wrapped", "i.days", "i.shown"],
         "order": ["item_id"]}
    rows = st.run(q).rows
    assert rows[0] == ("I1001", None, "late", 5, "normal/I1001")
    assert rows[4] == ("I1005", None, None, None, "normal/I1005")  # not delivered: if and days are null
    assert st.conformance(queries={"q": (st.query(q), {}),
                                   "n": (st.query({"match": {"o": "Order"}, "return": ["o.order_id", "o.lines"],
                                                   "order": ["order_id"]}), {})}).passed


def test_expressions_are_checked_against_the_definition(onto):
    with pytest.raises(ExprError, match="link.property"):
        parse_expr("sum(quantity)")
    with pytest.raises(ExprError, match="unknown function"):
        parse_expr("median(quantity)")
    d = onto.to_dict()
    props = d["objects"]["OrderItem"]["properties"]
    props["bad"] = {"type": "decimal", "expr": "quantity + item_status"}
    props["loop_a"] = {"type": "integer", "expr": "loop_b + 1"}
    props["loop_b"] = {"type": "integer", "expr": "loop_a + 1"}
    props["wrong"] = {"type": "boolean", "expr": "quantity * 2"}
    props["nolink"] = {"type": "integer", "expr": "count(nowhere)"}
    issues = Ontology.from_dict(d).validate()
    assert any("'+' takes numbers, not enum" in i for i in issues)
    assert any("loop" in i for i in issues)
    assert any("gives integer, the property is declared boolean" in i for i in issues)
    assert any("has no link 'nowhere'" in i for i in issues)
    assert check_computed(onto, "Customer", "spent").type == "decimal"
    assert dependencies(onto, "Customer", "spent") == {("OrderItem", "unit_price"), ("OrderItem", "quantity"),
                                                   ("Order", "status")}


def test_languages_without_a_form_say_so(onto):
    q = {"match": {"o": "Order"}, "return": ["o.order_id", "o.total"]}
    with pytest.raises(CompileError, match="GQL"):
        compiler_for(onto, "gql").compile(q)
    with pytest.raises(CompileError, match="SQL/PGQ"):
        compiler_for(onto, "sqlpgq").compile(q)
    simple = {"match": {"i": "OrderItem"}, "return": ["i.item_id", "i.line_total"]}
    assert "unit_price" in compiler_for(onto, "gql").compile(simple).text
    assert "unit_price" in compiler_for(onto, "sqlpgq").compile(simple).text
    assert "unit_price" in compiler_for(onto, "sql:oracle").compile(q).text


def test_masked_properties_and_what_a_role_may_ask(studio):
    q = {"match": {"c": "Customer"}, "return": ["c.customer_id", "c.phone", "c.name"], "order": ["customer_id"]}
    res = studio.run(q, role="support_agent")
    assert res.rows[0] == ("C001", "***-****-0101", "김하늘") and res.masked == {"phone": "partial"}
    assert studio.run(q, role="operator").rows[0][1] == "010-5550-0101"
    assert studio.run(q).rows[0][1] == "010-5550-0101"  # no role: the studio's own reads are in clear
    with pytest.raises(AccessDenied, match="filter"):
        studio.run({"match": {"c": "Customer"}, "where": {"eq": ["c.phone", "010-5550-0101"]},
                    "return": ["c.customer_id"]}, role="support_agent")
    with pytest.raises(AccessDenied, match="order"):
        studio.run({"match": {"c": "Customer"}, "return": ["c.phone"], "order": ["phone"]}, role="support_agent")
    assert mask_value("kim@example.org", "partial") == "k***@example.org"
    assert mask_value("김하늘", "partial") == "김*늘" and mask_value(12, "full") == "***"


def test_a_computed_property_built_from_a_masked_one_is_masked(studio):
    d = studio.onto.to_dict()
    d["objects"]["Customer"]["properties"]["tail"] = {"type": "string", "expr": "concat(phone, '')"}
    studio.onto = Ontology.from_dict(d).check()
    res = studio.run({"match": {"c": "Customer"}, "return": ["c.customer_id", "c.tail"], "order": ["customer_id"]},
                     role="support_agent")
    assert res.rows[0] == ("C001", "***") and res.masked == {"tail": "full"}


def test_parameters_are_checked_by_type_range_and_pattern():
    spec = {"qty": {"type": "integer", "min": 1, "max": 5}, "code": {"type": "string", "pattern": "[A-Z]{2}\\d+"},
            "kind": {"type": "enum", "values": ["A", "B"]}, "note": {"type": "string", "required": False,
                                                                    "max_length": 3}}
    values, problems = check_parameters(spec, {"qty": "3", "code": "AB12", "kind": "A"})
    assert values["qty"] == 3 and not problems
    _, problems = check_parameters(spec, {"qty": 9, "code": "x", "kind": "C", "note": "long"})
    assert len(problems) == 4
    with pytest.raises(ActionError, match="only filled into headers"):
        render("${SECRET}", {})


def test_reason_too_long_is_rejected(studio):
    p = studio.actions.request("requestReturn", "I1001", {"reason": "x" * 201}, actor=AGENT)
    assert p.status == "rejected" and "longer than 200" in next(c.detail for c in p.checks if c.name == "parameters")


def test_rollback_puts_back_what_the_action_replaced(studio):
    p = studio.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    studio.actions.approve(p.id, approver=OPERATOR)
    with pytest.raises(PermissionError):
        studio.actions.rollback(p.id, actor=Actor("bot", "agent", ["operator"]))
    studio.actions.rollback(p.id, actor=OPERATOR, reason="잘못 승인")
    assert p.status == "rolled_back" and studio.fetch("OrderItem", "I1001")["item_status"] == "NORMAL"
    assert studio.actions.audit[-1].event == "rolled_back"
    with pytest.raises(ActionError, match="only an executed action"):
        studio.actions.rollback(p.id, actor=OPERATOR)
    q = studio.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    studio.actions.approve(q.id, approver=OPERATOR)
    studio.backend().run("UPDATE order_items SET item_status = 'RETURNED' WHERE item_id = 'I1001'")
    with pytest.raises(ActionError, match="has changed since"):
        studio.actions.rollback(q.id, actor=OPERATOR)


class _Hook(BaseHTTPRequestHandler):
    seen: list = []
    fail = False

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Hook.seen.append((self.path, self.headers.get("Authorization"), body))
        self.send_response(500 if _Hook.fail else 200)
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, *a):
        pass


@pytest.fixture
def hook():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Hook)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    _Hook.seen, _Hook.fail = [], False
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _with_call(studio, url: str, undo: bool):
    d = studio.onto.to_dict()
    a = d["actions"]["requestReturn"]
    a["call"] = {"url": f"{url}/returns/$key", "headers": {"Authorization": "Bearer ${XDS_TEST_TOKEN}"},
                 "body": {"item": "$key", "reason": "$reason", "status": "$after.item_status"}}
    if undo:
        a["undo"] = {"url": f"{url}/returns/$key/cancel", "body": {"item": "$key"}}
    studio.onto = Ontology.from_dict(d).check()


def test_an_external_call_is_sent_after_the_change_and_undone_with_it(studio, hook, monkeypatch):
    monkeypatch.setenv("XDS_TEST_TOKEN", "t0ken")
    _with_call(studio, hook, undo=True)
    p = studio.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    assert next(c for c in p.checks if c.name == "call").passed is False  # no allowed host yet
    studio.actions.caller = HttpCaller(["127.0.0.1"])
    p = studio.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    studio.actions.approve(p.id, approver=OPERATOR)
    assert p.status == "executed" and p.call["status"] == 200
    assert _Hook.seen[0] == ("/returns/I1001", "Bearer t0ken",
                             {"item": "I1001", "reason": "사이즈", "status": "RETURN_REQUESTED"})
    studio.actions.rollback(p.id, actor=OPERATOR)
    assert _Hook.seen[-1][0] == "/returns/I1001/cancel" and p.status == "rolled_back"


def test_a_failed_call_reverts_the_change(studio, hook, monkeypatch):
    monkeypatch.setenv("XDS_TEST_TOKEN", "t0ken")
    _with_call(studio, hook, undo=False)
    studio.actions.caller = HttpCaller(["127.0.0.1"])
    _Hook.fail = True
    p = studio.actions.request("requestReturn", "I1001", {"reason": "사이즈"}, actor=AGENT)
    studio.actions.approve(p.id, approver=OPERATOR)
    assert p.status == "failed" and "500" in p.call["error"]
    assert studio.fetch("OrderItem", "I1001")["item_status"] == "NORMAL"
    assert [e.event for e in studio.actions.audit][-2:] == ["written", "call_failed"]


def test_identity_joins_customers_and_borrowers_across_systems():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_data_studio.config import load_studio

    st = load_studio(EXAMPLE.parent / "library" / "studio.yaml")
    rep = st.resolve_identity("Person")
    assert rep.summary() == {"identity": "Person", "records": 6, "identities": 5, "joined": 1, "findings": 0,
                             "written": True}
    joined = rep.joined[0]
    assert joined.members == ["Borrower:B03", "Customer:C003"] and joined.rules == ["same-phone-name"]
    assert joined.evidence[0].value == "01055500103 / 박서연"
    assert st.run("customersWhoBorrow").rows == [("Borrower:B03", "C003", "B03", "박서연")]
    assert st.run("customersWhoBorrow", backend="graph").rows == st.run("customersWhoBorrow").rows
    assert st.check_bindings().ok and st.conformance().passed
