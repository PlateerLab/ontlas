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


def test_edits_made_again_on_an_approved_version_hold_aside_what_it_also_changed(ws):
    """After an approval the edits still being written are made again on it; one on an item the approval changed waits
    aside with why, until a person makes it over the approval or lets it go. Each keeps who made it."""
    from ontlas.manage import changed_elements
    from ontlas.modules import Module

    ws.apply("update_object", {"name": "Customer", "label": "회원"})
    approved = Module.from_dict(ws.module.to_dict())  # the workspace module as the first approval left it
    later = type(ws)(ws.base, approved, compose_kw=ws.kw)
    later.who = "Choi"
    product = later.apply("update_object", {"name": "Product", "label": "상품 마스터"})
    later.apply("update_object", {"name": "Customer", "label": "고객 마스터"})
    later.apply("add_property", {"object": "Customer", "name": "memo", "type": "string"})
    second = approved.to_dict()
    second["version"], second["extend"]["objects"]["Customer"]["label"] = "0.1.1", "고객"  # approved meanwhile
    after = type(ws)(ws.base, Module.from_dict(second), compose_kw=ws.kw)
    changed = changed_elements(later.started(), after.started())
    assert changed == {"object:Customer"}
    moved = later.rebase(ws.base, after.current, changed=changed, change="C2")
    assert [(e.target, e.by) for e in moved.edits] == [("object:Product", "Choi"), ("property:Customer.memo", "Choi")]
    assert moved.edits[0].id == product.id
    assert [(e.target, e.conflict["why"], e.conflict["change"]) for e in moved.held] == [("object:Customer", "changed", "C2")]
    assert moved.composed().ontology.objects["Customer"].label == "고객"  # what was approved is not written back
    kept = later.rebase(ws.base, after.current, changed=changed, change="C2")
    kept.drop_held(kept.held[0].id)
    assert kept.held == [] and kept.composed().ontology.objects["Customer"].label == "고객"
    made = moved.make_held(moved.held[0].id)
    assert made.by == "Choi" and moved.held == [] and moved.composed().ontology.objects["Customer"].label == "고객 마스터"


def test_a_property_names_the_standard_vocabulary_it_stands_for_and_lets_it_go(ws):
    ws.apply("add_property", {"object": "Customer", "name": "nickname", "type": "string",
                              "aligned": ["https://schema.org/alternateName"]})
    assert ws.composed().ontology.objects["Customer"].properties["nickname"].aligned == ["https://schema.org/alternateName"]
    ws.apply("update_property", {"object": "Customer", "name": "nickname", "aligned": []})  # the definition's own name again
    assert ws.composed().ontology.objects["Customer"].properties["nickname"].aligned == []
    ws.apply("update_property", {"object": "Customer", "name": "grade", "aligned": ["https://schema.org/category"]})  # a standard's
    assert ws.composed().ontology.objects["Customer"].properties["grade"].aligned == ["https://schema.org/category"]
    assert ws.module.extend["objects"]["Customer"]["properties"]["grade"] == {"aligned": ["https://schema.org/category"]}



@pytest.fixture
def shop():
    """The example shop library as people get it: the decision tables and named values the rules screens edit."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio projects a graph
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    from .conftest import EXAMPLE

    return StudioSession(load_studio(EXAMPLE.parent / "library" / "studio.yaml"))


def _table_rows(s, name):
    return {c["rule"]: c for c in s.semantic_state()["cards"] if c["kind"] == "executable" and c["decision"] == name}


def test_a_table_taken_to_priority_numbers_its_rules_and_answers_as_before(shop):
    before = {k: shop.simulate("shippingFee", k)["verdict"] for k in ("O1", "O2", "O3", "O4")}
    shop.manage_edit("update_decision", {"decision": "shippingFee", "hit_policy": "priority"})
    got = _table_rows(shop, "shippingFee")
    assert [(k, got[k]["priority"]) for k in ("cancelled", "free", "basic")] == [("cancelled", 1), ("free", 2), ("basic", 3)]
    assert {k: shop.simulate("shippingFee", k)["verdict"] for k in before} == before
    # a row's number is kept when it is edited without one, and a new one is given its own
    shop.manage_edit("update_rule", {"decision": "shippingFee", "id": "basic", "when": {}, "then": {"fee": 2500, "reason": "기본"}})
    assert _table_rows(shop, "shippingFee")["basic"]["priority"] == 3
    shop.manage_edit("add_rule", {"decision": "shippingFee", "id": "promo", "when": {}, "then": {"fee": 0, "reason": "행사"},
                                     "priority": 0})
    assert _table_rows(shop, "shippingFee")["promo"]["priority"] == 0
    assert shop.simulate("shippingFee", "O1")["matched"][0] == "promo"
    with pytest.raises(ValueError):
        shop.manage_edit("update_rule", {"decision": "shippingFee", "id": "basic", "when": {}, "then": {"fee": 1, "reason": "x"},
                                            "priority": "high"})
    # and back: in the order of the numbers, without them
    shop.manage_edit("update_rule", {"decision": "shippingFee", "id": "free", "when": {"order_total": ">= @free_shipping_amount"},
                                        "then": {"fee": 0, "reason": "무료"}, "priority": 9})
    shop.manage_edit("update_decision", {"decision": "shippingFee", "hit_policy": "first"})
    got = _table_rows(shop, "shippingFee")
    assert sorted(got, key=lambda k: got[k]["position"]) == ["promo", "cancelled", "basic", "free"]
    assert all(c["priority"] is None for c in got.values())


def test_a_table_with_an_unnumbered_axiom_row_is_not_taken_to_priority(shop):
    with pytest.raises(ValueError) as e:
        shop.manage_edit("update_decision", {"decision": "returnEligibility", "hit_policy": "priority"})
    assert str(e.value) == "AXIOM 규칙 'not-delivered'는 여기서 바꾸거나 옮기거나 지울 수 없습니다."


def test_a_named_value_takes_an_owner(shop):
    from ontlas.web import routes

    routes.load()
    shop.manage_edit("update_parameter", {"name": "return_window_days", "value": 7, "owner": "운영팀"})
    p = next(x for x in shop.semantic_state()["parameters"] if x["name"] == "return_window_days")
    assert p["owner"] == "운영팀"
    hist = routes.find("GET", "sem/history")(shop, {"kind": "parameter", "name": "return_window_days"}, None)
    assert {f["label"]: f["after"] for f in hist["entries"][0]["fields"]}["담당자"] == "운영팀"
    item = routes.find("GET", "item/history")(shop, {"element": "parameter:return_window_days"}, None)
    assert any(f["label"] == "담당" and f["after"] == "운영팀" for f in item["entries"][0]["fields"])
