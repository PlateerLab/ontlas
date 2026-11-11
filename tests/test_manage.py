"""The management screens' edits: one overlay module over the standards, cascading what it leaves broken."""
import json

import pytest

from .conftest import LIB

MODULES = ["core", "commerce", "commerce-bindings", "fashion", "acme-overlay", "finance", "finance-bindings",
           "party-identity"]


@pytest.fixture
def ws():
    pytest.importorskip("yaml")
    from ontlas.library import Library
    from ontlas.manage import Workspace

    lib = Library(LIB)
    return Workspace(lib.resolve(MODULES), compose_kw={"namespace": "https://example.org/studio#", "name": "studio"})


def test_an_edit_on_a_standard_extends_it_and_leaves_the_standard_alone(ws):
    from ontlas.manage import EditError

    e = ws.apply("update_property", {"object": "Customer", "name": "grade", "label": "회원 등급"})
    assert e.target == "property:Customer.grade" and e.took_out == []
    assert ws.module.extend["objects"]["Customer"]["properties"]["grade"] == {"label": "회원 등급"}
    assert ws.composed().ontology.objects["Customer"].properties["grade"].label == "회원 등급"
    assert ws.module.requires and ws.dirty
    with pytest.raises(EditError, match="comes from its standard"):  # the standard's type stays
        ws.apply("update_property", {"object": "Customer", "name": "grade", "type": "integer"})
    with pytest.raises(EditError, match="specialises"):  # an inherited property goes on its owner
        ws.apply("delete_property", {"object": "Customer", "name": "name"})
    with pytest.raises(EditError, match="is the key"):
        ws.apply("delete_property", {"object": "Customer", "name": "customer_id"})
    with pytest.raises(EditError, match="set where it is defined"):
        ws.apply("update_object", {"name": "Customer", "key": "grade"})
    assert len(ws.edits) == 1  # refused edits change nothing


def test_a_removal_takes_out_what_it_leaves_broken_and_says_so(ws):
    e = ws.apply("delete_link", {"name": "placed"})
    assert {"query:ordersOfCustomer", "query:customerValue", "decision:returnEligibility", "question:Q1",
            "property:Customer.order_count"} <= set(e.took_out)
    comp = ws.composed()
    assert comp.issues == [] and "placed" not in comp.ontology.links
    assert "ordersOfCustomer" not in comp.ontology.queries and "returnEligibility" not in comp.ontology.decisions
    e = ws.apply("delete_object", {"name": "Claim"})
    assert e.took_out == ["link:hasClaim"] and "Claim" not in ws.composed().ontology.objects


def test_new_objects_links_and_questions_are_the_modules_own(ws):
    from ontlas.manage import EditError

    ws.apply("add_object", {"name": "Coupon", "label": "쿠폰", "table": "coupons", "key": "coupon_id",
                            "properties": {"coupon_id": {"type": "string", "label": "쿠폰 번호"}}})
    ws.apply("add_property", {"object": "Order", "name": "coupon_id", "type": "string", "label": "쿠폰 번호"})
    ws.apply("add_link", {"name": "usedCoupon", "source": "Order", "target": "Coupon", "on": ["coupon_id", "coupon_id"],
                          "label": "사용 쿠폰"})
    ws.apply("update_link", {"name": "usedCoupon", "cardinality": "one_to_one"})
    assert ws.module.body["links"]["usedCoupon"]["cardinality"] == "one_to_one"
    with pytest.raises(EditError, match="already exists"):
        ws.apply("add_object", {"name": "Coupon", "key": "x", "properties": {"x": "string"}})
    with pytest.raises(EditError, match="unknown query"):  # an edit that leaves its own element broken is refused
        ws.apply("add_question", {"id": "G1", "text": "?", "query": "nope"})
    ws.apply("add_question", {"id": "G1", "text": "연체 대출은?", "query": "overdueLoans", "expect": {"rows": 1}})
    assert [q["id"] for q in ws.module.body["questions"]] == ["G1"]
    e = ws.apply("delete_object", {"name": "Coupon"})  # its own: deleted outright, its links with it
    assert "Coupon" not in ws.module.body["objects"] and "usedCoupon" not in ws.module.body["links"]
    assert e.took_out == []
    ws.apply("delete_question", {"id": "Q1"})  # a standard's question is removed, not deleted
    assert "Q1" in ws.module.remove["questions"]


def test_settle_prunes_what_removals_break_but_not_what_the_module_defines():
    pytest.importorskip("yaml")
    from ontlas.library import Library
    from ontlas.modules import Module, compose, settle

    base = Library(LIB).resolve(["core", "commerce", "commerce-bindings"])
    m = Module.from_dict({"module": "cut", "version": "0.1.0", "kind": "customer", "requires": ["commerce"],
                          "remove": {"links": ["placed"]},
                          "queries": {"mine": {"label": "내 질의", "query": {
                              "match": {"c": "Customer", "o": "Order"}, "edges": [["c", "placed", "o"]],
                              "return": ["o.order_id"]}}}})
    out = settle(m, base)
    assert "query:ordersOfCustomer" in out and "mine" in m.body["queries"]  # its own query is left to a person
    assert any("mine" in i for i in compose([*base, m]).issues)


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    return StudioSession(load_studio(LIB / "studio.yaml"))


def test_the_state_shows_objects_properties_links_and_the_source(session):
    st = session.manage_state()
    json.dumps(st)
    names = {o["name"]: o for o in st["objects"]}
    assert names["Party"]["concept"] and names["Customer"]["table"] == "customers" and names["Customer"]["rows"] == 3
    grade = next(p for p in st["properties"] if (p["object"], p["name"]) == ("Customer", "grade"))
    assert grade["module"] == "commerce" and grade["values"] == ["BASIC", "SILVER", "VIP"]
    inherited = next(p for p in st["properties"] if (p["object"], p["name"]) == ("Customer", "name"))
    assert inherited["inherited"] == "Party" and inherited["module"] == "core"
    tables = {t["table"]: t for t in st["sources"]["source"]["tables"]}
    assert tables["orders"]["objects"] == ["Order"] and tables["wishlists"]["links"] == ["wishes"]
    assert "wishlists" not in st["sources"]["source"]["unbound"]  # a relation's junction table is read
    assert st["unlinked"] == ["ReturnCase"] and not st["workspace"]["dirty"]
    assert {q["id"] for q in st["questions"]} >= {"Q1", "A1", "L1"}


def test_edits_are_said_in_korean_and_filed_as_one_change(session):
    with pytest.raises(ValueError, match="표준 모듈에서 정해져"):
        session.manage_edit("update_property", {"object": "Customer", "name": "grade", "type": "integer"})
    with pytest.raises(ValueError, match="상위 Entity Party"):
        session.manage_edit("delete_property", {"object": "Customer", "name": "name"})
    r = session.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    assert r["workspace"]["dirty"] and r["workspace"]["diff"]["changed"] == ["object:Customer"]
    assert next(o for o in r["objects"] if o["name"] == "Customer")["pending"]
    r = session.manage_edit("delete_object", {"name": "Claim"})
    assert r["edit"]["took_out"] == ["link:hasClaim"]
    r = session.manage_import_questions('- {id: G1, text: "연체 대출은?", query: overdueLoans, expect: {rows: 1}}\n'
                                        "- {id: G2, text: 없는 질의, query: nope}\n")
    assert r["added"] == ["G1"] and r["failed"][0].startswith("G2: 정의 검사를 통과하지 못해")
    assert session.studio.onto.objects["Customer"].label != "회원"  # nothing reaches the studio before approval
    r = session.manage_propose()
    assert r["ok"] and r["change"]["status"] == "approved" and not r["workspace"]["dirty"]
    onto = session.studio.onto
    assert onto.objects["Customer"].label == "회원" and "Claim" not in onto.objects
    assert any(q.id == "G1" for q in onto.questions)
    assert [m.name for m in session.studio.composition.modules][-1] == "workspace"
    assert not next(o for o in session.manage_state()["objects"] if o["name"] == "Customer")["pending"]
    # the next edits start from the approved module and file its next version
    session.manage_edit("update_object", {"name": "Customer", "description": "회원 설명"})
    r = session.manage_propose()
    assert r["change"]["version"] == "0.1.1" and session.studio.onto.objects["Customer"].description == "회원 설명"
    with pytest.raises(ValueError, match="바뀐 내용이 없어"):
        session.manage_propose()


def test_a_change_the_trial_stops_comes_back_with_its_review(session):
    # wishlists has no primary key and customer_id repeats there: the trial's DB check finds it
    session.manage_edit("add_object", {"name": "Wish", "table": "wishlists", "key": "customer_id",
                                       "properties": {"customer_id": {"type": "string", "required": True}}})
    r = session.manage_propose()
    assert not r["ok"] and "DB 대조" in r["error"]
    assert r["change"]["status"] == "rejected" and any(f["kind"] == "key" for f in r["change"]["measured"]["findings"])
    assert r["workspace"]["dirty"] and "Wish" not in session.studio.onto.objects  # kept to be fixed
    r = session.manage_discard()
    assert not r["workspace"]["dirty"]


def test_management_routes_need_an_editor():
    from ontlas.web.team import NEEDS

    assert {NEEDS[r] for r in ("manage/edit", "manage/questions", "manage/discard", "manage/propose")} == {"editor"}
