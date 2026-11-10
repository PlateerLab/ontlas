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


def test_a_record_search_that_finds_nothing_names_the_types_that_hold_the_words(session):
    r = session.record_list("OrderItem", "C001")
    assert r["rows"] == [] and r["q"] == "C001"
    assert {"type": "Customer", "label": "고객", "count": 1, "more": False} in r["elsewhere"]
    assert all(x["type"] != "OrderItem" and x["count"] for x in r["elsewhere"])
    assert session.record_list("Customer", "C001")["elsewhere"] == []  # found here: nothing to switch to
    assert session.record_list("OrderItem")["elsewhere"] == []  # no words, no search elsewhere
    json.dumps(r)


def test_a_decision_the_engine_refuses_is_said_in_the_pages_words(session):
    with pytest.raises(ValueError) as e:
        session.simulate("returnEligibility", "I9999")
    assert str(e.value) == "주문상품 I9999 레코드가 없어 판정하지 못했습니다. 레코드를 다시 골라 주세요."
    with pytest.raises(ValueError, match="주문상품 I9999 레코드가 없어"):
        session.decide("returnEligibility", "I9999")
    with pytest.raises(ValueError, match="^결정표를 찾지 못해 판정하지 못했습니다"):
        session.simulate("nope", "I1001")
    with pytest.raises(ValueError, match="자료형에 맞지 않아 판정하지 못했습니다") as e:
        session.simulate("returnEligibility", "I1001", {"days_since_delivery": "abc"})
    assert "invalid literal" not in str(e.value)
    assert session.simulate("returnEligibility", "I1001")["key"] == "I1001"  # a record that is there still decides


def _in_window(session, days: int) -> dict:
    """The rule as the rules screen sends it after a cell is edited: its other cells as they stand."""
    d = next(x for x in session.manage_state()["decisions"] if x["name"] == "returnEligibility")
    r = next(x for x in d["rules"] if x["id"] == "in-window")
    return {"decision": d["name"], "id": r["id"], "when": {**r["when"], "days_since_delivery": {"op": "lte", "value": str(days)}},
            "then": r["then"], "cite": r["cite"] or ""}


def test_a_rule_edited_in_the_workspace_is_compared_field_by_field_after_it_is_applied(session):
    assert session.studio.changes.self_approve  # one visitor: filing tries the edit on a copy and applies it
    session.manage_edit("update_rule", _in_window(session, 10))
    first = session.manage_propose()
    assert first["change"]["status"] == "approved" and first["change"]["base_version"] == ""
    d = session.change_detail(first["change"]["id"])
    rule = next(x for x in d["items"] if x["element"] == "rule:returnEligibility.in-window")
    cell = next(f for f in rule["fields"] if f["field"] == "when.days_since_delivery")
    assert (cell["before"], cell["after"], cell["said"]) == ("<= 7", "<= 10", ["7일 이하", "10일 이하"])
    assert cell["label"] == "조건 · 배송 완료 일시 경과일" and rule["change"] == "changed"
    assert {t for t, _ in d["yaml"]} == {"+"}  # the module's first version: every line is new
    # the next change is written over the first one and compared with it, the file too
    session.manage_edit("update_rule", _in_window(session, 12))
    second = session.manage_propose()
    assert (second["change"]["base_version"], second["change"]["version"]) == ("0.1.0", "0.1.1")
    d = session.change_detail(second["change"]["id"])
    cell = next(f for x in d["items"] for f in x["fields"] if f["field"] == "when.days_since_delivery")
    assert cell["said"] == ["10일 이하", "12일 이하"]
    assert any(t == "-" and "<= 10" in line for t, line in d["yaml"]) and any(t == "+" and "<= 12" in line for t, line in d["yaml"])
    # the first change still reads as it was filed, though the studio has moved on twice
    again = session.change_detail(first["change"]["id"])
    cell = next(f for x in again["items"] for f in x["fields"] if f["field"] == "when.days_since_delivery")
    assert cell["said"] == ["7일 이하", "10일 이하"]
    json.dumps(again)


def test_a_change_waiting_for_an_approver_is_compared_the_same_way(session):
    session.studio.changes.self_approve = False  # a team: someone else approves it
    session.manage_edit("update_rule", _in_window(session, 9))
    cid = session.manage_propose()["change"]["id"]
    cell = next(f for x in session.change_detail(cid)["items"] for f in x["fields"] if f["field"] == "when.days_since_delivery")
    assert cell["said"] == ["7일 이하", "9일 이하"]


def test_a_display_name_gives_the_english_name_the_way_drafts_name_tables(session):
    assert session.name_for("쿠폰") == {"label": "쿠폰", "name": "Coupon", "parts": [["쿠폰", "Coupon"]], "roman": False}
    got = session.name_for("주문 금액", "property")
    assert got["name"] == "order_amount" and got["parts"] == [["주문", "Order"], ["금액", "Amount"]] and not got["roman"]
    got = session.name_for("별명", "property")
    assert got["roman"] and got["name"] == "byeolmyeong"  # a word nobody named: spelled in Latin letters, to be checked
    assert session.name_for("Gift card", "object")["name"] == "GiftCard" and not session.name_for("Gift card")["roman"]
