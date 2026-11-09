import json

import pytest

from .conftest import LIB

CFG = LIB / "studio.yaml"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    return StudioSession(load_studio(CFG))


def test_a_record_page_gathers_what_a_person_needs_about_one_record(session):
    r = session.record_page("OrderItem", "I1001")
    values = {p["name"]: p for p in r["props"]}
    assert values["item_status"]["value"] == "NORMAL" and values["delivered_at"]["column"] == "delivered_at"
    assert values["line_total"]["expr"] and values["line_total"]["value"] == 59000  # computed, never a column
    assert r["state"]["now"] == "NORMAL" and r["state"]["next"][0] == {
        "to": "RETURN_REQUESTED", "action": "requestReturn", "action_label": "반품 신청", "after": {}, "guarded": False}
    order = next(x for x in r["links"] if x["type"] == "Order")
    assert not order["forward"] and order["items"] == [{"key": "O1", "title": None}]
    assert next(x for x in r["links"] if x["type"] == "Sku")["items"][0]["key"] == "S1"
    d = r["decisions"][0]
    assert (d["name"], d["verdict"], d["matched"], d["cite"]) == ("returnEligibility", "가능", ["vip-window"], "ACME 운영 정책 4.1")
    assert r["actions"][0]["name"] == "requestReturn" and r["actions"][0]["ready"]
    assert not session.studio.function_log  # functions are listed to run, never run by opening a page
    assert r["documents"] == [] and r["key_documents"] == []  # this studio file names no documents
    json.dumps(r)


def test_a_record_page_tells_its_history_and_what_can_happen_next(session):
    session.request("requestReturn", "I1001", {"reason": "size"}, "customer_agent", {"customer_id": "C001"})
    r = session.record_page("OrderItem", "I1001")
    assert r["history"][0]["pending"] and r["history"][0]["action"] == "requestReturn"
    p = next(iter(session.studio.actions.proposals.values()))
    assert session.approve(p.id, True)["ok"]
    r = session.record_page("OrderItem", "I1001")
    assert r["state"]["now"] == "RETURN_REQUESTED"
    assert not r["actions"][0]["ready"]  # the request it would make is already made
    assert not any(h.get("pending") for h in r["history"]) and {h["event"] for h in r["history"]} >= {"요청", "승인", "원천 반영"}
    with pytest.raises(LookupError):
        session.record_page("OrderItem", "I9999")


def test_records_are_listed_by_their_key_and_found_by_the_name_they_carry(session):
    found = session.record_list("Customer", "김")
    assert found["title"] == "name" and found["columns"][:2] == ["customer_id", "name"]
    assert found["total"] == len(found["rows"]) and all("김" in r["fields"]["name"] for r in found["rows"])
    assert session.record_list("Customer", "C001")["rows"][0]["key"] == "C001"
    first = session.record_list("Order", limit=2)
    assert [r["key"] for r in first["rows"]] == ["O1", "O2"] and first["total"] > 2


def test_the_inbox_holds_what_waits_on_a_person_and_says_who_asked(session):
    assert session.inbox()["counts"]["all"] == len([c for c in session.studio.onto.source_conflicts() if c.open])
    session.request("requestReturn", "I1001", {"reason": "size"}, "customer_agent", {"customer_id": "C001"})
    session.manage_edit("update_property", {"object": "Customer", "name": "grade", "label": "회원 등급"})
    box = session.inbox()
    kinds = [x["kind"] for x in box["items"]]
    assert "action" in kinds and "workspace" in kinds
    action = next(x for x in box["items"] if x["kind"] == "action")
    assert action["title"] == "반품 신청 · 주문상품 I1001" and action["by_kind"] == "agent" and not action["mine"]
    assert "RETURN_REQUESTED" in action["change"]
    assert box["alone"] and box["counts"]["assigned"] == box["counts"]["all"]  # one visitor settles what they asked for
    session.studio.changes.self_approve = False  # a team studio: someone else approves the change
    assert session.manage_propose()["pending"]
    box = session.inbox()
    change = next(x for x in box["items"] if x["kind"] == "change")
    assert change["mine"] and change["gates"][1] >= 1 and box["counts"]["assigned"] == box["counts"]["all"] - box["counts"]["mine"]
    json.dumps(session.inbox())


def _vip_window(days: int) -> dict:
    return {"decision": "returnEligibility", "id": "vip-window", "cite": "ACME 운영 정책 4.2",
            "when": {"days_since_delivery": f"<= {days}", "item_status": '"NORMAL"', "category_returnable": "true",
                     "customer_grade": '"VIP"'},
            "then": {"eligible": True, "reason": f"VIP 고객은 배송 완료 후 {days}일까지 반품할 수 있습니다"}}


def test_a_change_is_reviewed_element_by_element_against_how_the_studio_stands_now(session):
    session.studio.changes.self_approve = False  # someone other than its author approves it
    session.manage_edit("update_rule", _vip_window(21))
    cid = session.manage_propose()["change"]["id"]
    d = session.change_detail(cid)
    rule = next(x for x in d["items"] if x["element"] == "rule:returnEligibility.vip-window")
    cells = {f["field"]: (f["before"], f["after"]) for f in rule["fields"]}
    assert cells["when.days_since_delivery"] == ("<= 14", "<= 21") and cells["cite"][1] == "ACME 운영 정책 4.2"
    assert rule["fields"][0]["label"].startswith("조건 · ") and rule["change"] == "changed"
    assert "액션 반품 신청" in rule["readers"]  # what the rule reaches
    assert d["before"]["decide.min_agreement"] >= next(g["value"] for g in d["gates"] if g["stage"] == "decide")
    assert not d["can_decide"] and d["can_mark"]  # its author cannot approve it
    d = session.change_mark(cid, rule["element"], "fix")
    d = session.change_comment(cid, rule["element"], "개정 문서를 올려 주세요")
    assert d["marks"] == {rule["element"]: "fix"} and d["items"][0]["comments"][0]["text"] == "개정 문서를 올려 주세요"
    session.who = "이도윤"  # another person
    out = session.decide_change(cid, True)
    assert not out["ok"] and "수정을 요청한 항목" in out["error"]
    session.change_mark(cid, rule["element"], "ok")
    out = session.decide_change(cid, True)  # the mark no longer holds it back; a validation question that now fails does
    assert not out["ok"] and "수정을 요청한 항목" not in out["error"] and "검증 질문 정답률" in out["error"]
    assert session.decide_change(cid, False)["ok"]
    with pytest.raises(ValueError):
        session.change_mark(cid, rule["element"], "ok")  # decided: no more marks


def test_a_decision_is_tried_on_a_record_and_says_what_would_turn_it(session):
    sim = session.simulate("returnEligibility", "I1001")
    assert (sim["verdict"], sim["matched"]) == ("가능", ["vip-window"])
    days = next(i for i in sim["inputs"] if i["name"] == "days_since_delivery")
    assert days["value"] == 4 and days["type"] == "integer"
    turn = next(o for o in sim["other"] if o["input"] == "days_since_delivery")
    assert turn["value"] == 15 and turn["verdict"] == "불가"  # the first day past the VIP window
    assert {(e["value"], e["verdict"]) for e in sim["edges"] if e["input"] == "days_since_delivery"} >= {(14, "가능"), (15, "불가")}
    assert session.simulate("returnEligibility", "I1001", {"days_since_delivery": "20"})["verdict"] == "불가"
    assert session.simulate("returnEligibility", "", {"days_since_delivery": "3", "item_status": "NORMAL",
                                                      "category_returnable": "true", "customer_grade": "BASIC"})["matched"] == ["in-window"]
    assert not session.studio.function_log and not session.studio.actions.audit  # trying writes nothing
