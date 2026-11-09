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
