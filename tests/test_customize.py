from pathlib import Path

import pytest

from xgen_space.manage import EditError, Workspace
from xgen_space.modules import compose

SHOP = Path(__file__).resolve().parents[1] / "examples" / "library" / "studio.yaml"


@pytest.fixture
def shop():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio

    return load_studio(SHOP)


@pytest.fixture
def ws(shop):
    return Workspace(list(shop.composition.modules))


def onto(ws):
    return compose([*ws.base, ws.module]).ontology


def test_a_new_rule_goes_before_the_standard_and_leaves_it_alone(ws):
    ws.apply("add_rule", {"decision": "returnEligibility", "id": "gold-window", "cite": "운영 정책 7.1",
                          "when": {"customer_grade": {"op": "eq", "value": "GOLD"}, "days_since_delivery": {"op": "lte", "value": "10"}},
                          "then": {"eligible": True, "reason": "GOLD 고객은 10일까지 반품할 수 있습니다"}})
    rules = onto(ws).decisions["returnEligibility"].rules
    assert rules[0].id == "gold-window" and rules[0].when == {"customer_grade": '"GOLD"', "days_since_delivery": "10".join(["<= ", ""])}
    assert rules[0].cite == "운영 정책 7.1"
    assert all(m.name != "workspace" for m in ws.base)
    assert "decisions" in ws.module.extend  # an overlay: no standard module was edited


def test_a_rule_of_a_standard_is_changed_by_replacing_it_over_the_standard(ws):
    ws.apply("update_rule", {"decision": "returnEligibility", "id": "in-window", "when": {"days_since_delivery": {"op": "lte", "value": "10"}},
                             "then": {"eligible": True, "reason": "배송 완료 후 10일 이내입니다"}})
    rule = next(r for r in onto(ws).decisions["returnEligibility"].rules if r.id == "in-window")
    assert rule.when["days_since_delivery"] == "<= 10" and "10일" in rule.then["reason"]
    assert [r.id for r in onto(ws).decisions["returnEligibility"].rules].index("in-window") > 0  # it keeps its place


def test_a_rule_is_taken_out_and_the_last_one_stays(ws):
    ws.apply("delete_rule", {"decision": "shippingFee", "id": "free"})
    assert "free" not in [r.id for r in onto(ws).decisions["shippingFee"].rules]
    ws.apply("delete_rule", {"decision": "shippingFee", "id": "basic"})
    with pytest.raises(EditError):
        ws.apply("delete_rule", {"decision": "shippingFee", "id": "cancelled"})


def test_a_rule_that_cannot_be_read_is_refused_and_nothing_changes(ws):
    before = ws.module.to_dict()
    with pytest.raises(EditError):
        ws.apply("add_rule", {"decision": "returnEligibility", "id": "bad", "when": {"days_since_delivery": "<= soon"}, "then": {"eligible": True}})
    with pytest.raises(EditError):
        ws.apply("add_rule", {"decision": "returnEligibility", "id": "in-window", "when": {}, "then": {"eligible": True}})
    with pytest.raises(EditError):
        ws.apply("add_rule", {"decision": "returnEligibility", "id": "x", "when": {"nope": "1"}, "then": {"eligible": True}})
    with pytest.raises(EditError):
        ws.apply("add_rule", {"decision": "returnEligibility", "id": "bad id", "when": {}, "then": {"eligible": True}})
    assert ws.module.to_dict() == before


def test_a_new_decision_table_starts_from_one_rule(ws):
    ws.apply("add_decision", {"name": "exchangeEligibility", "label": "교환 가능 여부", "target": "OrderItem",
                              "inputs": {"item_status": {"type": "string", "property": "item_status"}}})
    ws.apply("add_rule", {"decision": "exchangeEligibility", "id": "normal", "when": {"item_status": {"op": "eq", "value": "NORMAL"}},
                          "then": {"result": True, "reason": "교환할 수 있습니다"}})
    t = onto(ws).decisions["exchangeEligibility"]
    assert [r.id for r in t.rules] == ["normal", "default"] and t.target == "OrderItem"


def test_an_action_is_changed_and_a_new_one_added(ws):
    ws.apply("update_action", {"name": "requestReturn", "label": "반품 접수", "approval": False,
                               "parameters": {"reason": {"type": "string", "label": "사유"}, "memo": {"type": "string", "label": "메모"}}})
    a = onto(ws).actions["requestReturn"]
    assert a.label == "반품 접수" and a.approval is False and "memo" in a.parameters
    ws.apply("add_action", {"name": "holdItem", "label": "보류", "target": "OrderItem", "parameters": {}, "criteria": [], "transition_to": ""})
    assert onto(ws).actions["holdItem"].target == "OrderItem" and onto(ws).actions["holdItem"].approval is True
    ws.apply("delete_action", {"name": "holdItem"})
    assert "holdItem" not in onto(ws).actions


def test_a_role_gains_and_loses_what_it_may_do(ws):
    ws.apply("update_role", {"name": "support_agent", "label": "상담 담당", "read": ["Customer", "Order"], "run": ["customerValue", "returnEligibility"],
                             "request": ["requestReturn"], "mask": {"Customer.phone": "full"}})
    r = onto(ws).roles["support_agent"]
    assert r.label == "상담 담당" and "OrderItem" not in r.read and "returnEligibility" in r.run and "orderTotals" not in r.run
    assert r.request == ["requestReturn"] and r.mask["Customer.phone"] == "full"
    ws.apply("add_role", {"name": "cs_lead", "label": "상담 리더", "read": ["*"], "run": ["*"]})
    assert onto(ws).roles["cs_lead"].can_read("Order")


def test_a_state_machine_is_replaced_whole(ws):
    ws.apply("update_states", {"object": "OrderItem", "property": "item_status", "initial": "NORMAL", "states": ["NORMAL", "RETURN_REQUESTED", "RETURNED", "HELD"],
                               "transitions": [{"from": "NORMAL", "to": "RETURN_REQUESTED", "action": "requestReturn"}, {"from": "NORMAL", "to": "HELD", "action": ""}]})
    sm = onto(ws).objects["OrderItem"].states
    assert "HELD" in sm.states and sm.allows("NORMAL", "HELD") and not sm.allows("RETURN_REQUESTED", "RETURNED")
    with pytest.raises(EditError):
        ws.apply("update_states", {"object": "OrderItem", "property": "item_status", "states": ["ONLY"], "transitions": []})
    with pytest.raises(EditError):
        ws.apply("update_states", {"object": "OrderItem", "property": "item_status", "states": ["A", "B"], "transitions": [{"from": "A", "to": "C"}]})


def test_a_module_that_extends_a_standard_says_so(ws):
    ws.apply("update_rule", {"decision": "returnEligibility", "id": "in-window", "when": {"days_since_delivery": {"op": "lte", "value": "10"}},
                             "then": {"eligible": True, "reason": "10일"}})
    assert any(r.name == "commerce" for r in ws.module.requires) or ws.module.requires  # it composes after what it changes
