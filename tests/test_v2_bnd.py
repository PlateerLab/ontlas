"""What the Data Binding screens ask: a registered query as its screen shows it and its change or removal as an edit,
a query read into every store's language without being run, the SQL an Entity's binding makes, and an action tried
without a request being made."""
import json
from pathlib import Path

import pytest

from ontlas.config import load_studio
from ontlas.web import routes
from ontlas.web.api import StudioSession
from ontlas.web.team import NEEDS

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
ITEMS = {"match": {"x": "OrderItem"}, "return": ["x.item_id", "x.item_status"], "limit": 5}
BY_STATUS = {**ITEMS, "where": {"eq": ["x.item_status", {"param": "status"}]}}


@pytest.fixture()
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    routes.load()
    return StudioSession(load_studio(SHOP))


def get(s, route, **a):
    return routes.find("GET", route)(s, a, None)


def post(s, route, **a):
    return routes.find("POST", route)(s, a, None)


def listed(s, name):
    return next((q for q in get(s, "bnd/queries")["queries"] if q["name"] == name), None)


def test_the_routes_are_registered_and_reading_needs_no_more_than_a_viewer():
    routes.load()
    assert routes.find("GET", "bnd/queries") and routes.find("GET", "bnd/binding")
    assert NEEDS["bnd/query/check"] == "viewer" and NEEDS["bnd/action/try"] == "viewer"


def test_a_registered_query_says_where_it_starts_what_it_follows_and_who_uses_it(session):
    out = get(session, "bnd/queries")
    json.dumps(out)
    assert len(out["queries"]) == len(session.studio.onto.queries) and not out["pending"] and out["removed"] == []
    q = listed(session, "ordersOfCustomer")
    assert q["start"] == "Customer" and q["start_label"] == "고객" and q["params"] == {"customer": "string"}
    assert [(h["link"], h["to"]) for h in q["hops"]] == [("placed", "Order")]
    assert q["returns"][0] == {"text": "o.order_id", "label": "주문 · 주문 번호"}
    assert q["module"] == "commerce" and q["version"] and not q["new"] and q["editable"]
    assert "Q1" in q["questions"] and any(r["name"] == "operator" for r in q["roles"])


def test_a_query_is_added_with_the_values_it_takes_then_changed_then_taken_out(session):
    session.manage_edit("new_query", {"name": "itemsByStatus", "label": "상태별 주문상품", "description": "상태를 받아 조회", "query": BY_STATUS})
    q = listed(session, "itemsByStatus")
    assert q["new"] and q["editable"] and q["params"] == {"status": "string"} and q["description"] == "상태를 받아 조회"
    assert get(session, "bnd/queries")["pending"]
    session.manage_edit("update_query", {"name": "itemsByStatus", "label": "주문상품 다섯 건", "description": "", "query": ITEMS})
    q = listed(session, "itemsByStatus")
    assert q["label"] == "주문상품 다섯 건" and q["params"] == {} and q["description"] == ""  # what it no longer takes is gone
    session.manage_edit("delete_query", {"name": "itemsByStatus"})
    assert listed(session, "itemsByStatus") is None
    assert session.manage_undo()["ok"] and listed(session, "itemsByStatus") is not None  # an edit like any other: it is taken back


def test_a_query_a_module_defines_is_changed_by_extending_it_and_taken_out_with_what_asks_it(session):
    session.manage_edit("update_query", {"name": "ordersOfCustomer", "label": "다른 이름"})
    assert listed(session, "ordersOfCustomer")["label"] == "다른 이름"
    assert session.manage_undo()["ok"]
    with pytest.raises(ValueError, match="찾지 못해"):
        session.manage_edit("update_query", {"name": "nope", "label": "x"})
    out = session.manage_edit("delete_query", {"name": "ordersOfCustomer"})
    assert "question:Q1" in out["edit"]["took_out"]  # the question that asked it goes with it, and the edit says so
    assert get(session, "bnd/queries")["removed"] == ["ordersOfCustomer"]


def test_a_query_being_written_is_read_into_every_language_and_nothing_is_run(session):
    out = post(session, "bnd/query/check", query=BY_STATUS)
    assert out["ok"] and out["params"] == ["status"] and out["masked"] == []
    assert all(t["ok"] and t["text"] for t in out["translations"]) and len(out["translations"]) >= 9
    assert "order_items" in next(t["text"] for t in out["translations"] if t["target"] == "sql:postgres")
    phone = post(session, "bnd/query/check", query={"match": {"c": "Customer"}, "return": ["c.customer_id", "c.phone"]})
    assert phone["masked"] == ["고객 · 연락처"]  # what an access policy would hide is said before it is saved
    bad = post(session, "bnd/query/check", query={"match": {"x": "Nope"}, "return": ["x.a"]})
    assert not bad["ok"] and not any(t["ok"] for t in bad["translations"]) and bad["translations"][0]["error"] == "Entity 없음 · Nope"
    lost = post(session, "bnd/query/check", query={"match": {"c": "Customer"}, "return": ["c.nope"]})
    assert {t["error"] for t in lost["translations"]} == {"Property 없음 · Customer.nope"}  # the compiler's own words are not shown
    wrong = post(session, "bnd/query/check", query="not a query")
    assert not wrong["ok"] and wrong["error"] == "질의 정의 형식 오류"


def test_a_value_a_compiler_lifts_out_of_the_query_is_not_an_input(session):
    # Order.total is computed; one store's language carries a number of its formula as a value of its own
    out = post(session, "bnd/query/check", query={"match": {"x": "OrderItem", "y": "Order"}, "edges": [["y", "hasItem", "x"]],
                                                  "where": {"eq": ["x.item_status", {"param": "status"}]}, "return": ["x.item_id", "y.total"]})
    assert out["ok"] and out["params"] == ["status"]


def test_a_query_not_yet_deployed_runs_on_the_values_given(session):
    assert NEEDS["bnd/query/run"] == "viewer"
    session.manage_edit("new_query", {"name": "itemsByStatus", "label": "상태별 주문상품", "query": BY_STATUS})
    out = post(session, "bnd/query/run", query=BY_STATUS, params={"status": "RETURNED"})
    assert out["ok"] and out["params"] == {"status": "RETURNED"} and out["results"]
    res = out["results"][0]
    assert res["ok"] and res["rows"] and all(r[res["columns"].index("item_status")] == "RETURNED" for r in res["rows"])
    empty = post(session, "bnd/query/run", query=BY_STATUS, params={"status": ""})  # an input left empty is not given
    assert empty["params"] == {} and not all(r["ok"] for r in empty["results"])
    with pytest.raises(ValueError, match="질의 정의가 없어"):
        post(session, "bnd/query/run", query="nope")


def test_the_check_is_of_the_definition_as_the_edits_leave_it(session):
    assert NEEDS["bnd/check"] == "viewer"
    clean = post(session, "bnd/check")
    assert clean["ok"] is not None and not clean["pending"] and clean["checked"]["columns"] > 0
    assert not any(f["element"] == "property:Customer.phone" for f in clean["findings"])
    session.manage_edit("update_property", {"object": "Customer", "name": "phone", "column": "phone_no"})
    out = post(session, "bnd/check")
    assert out["pending"] and any(f["element"] == "property:Customer.phone" and f["kind"] == "column" for f in out["findings"])


def test_the_check_reads_the_properties_taken_from_the_parent_and_says_each_in_words(session):
    # Customer takes name and phone from Party and reads them from its own table: a table without them misses all three
    session.manage_edit("update_object", {"name": "Customer", "table": "wishlists"})
    out = post(session, "bnd/check")
    lost = sorted(f["element"] for f in out["findings"] if f["kind"] == "column" and f["element"].startswith("property:Customer."))
    assert lost == ["property:Customer.grade", "property:Customer.name", "property:Customer.phone"] and not out["ok"]
    said = {f["element"]: f["detail"] for f in out["findings"]}
    assert said["property:Customer.name"] == "wishlists.name 컬럼 없음"
    assert not any("does not exist" in f["detail"] for f in out["findings"])


def test_each_property_is_listed_with_the_column_it_is_read_from(session):
    cols = get(session, "bnd/columns")["columns"]
    assert cols["OrderItem.quantity"] == ["quantity"] and "OrderItem.line_total" not in cols  # a computed one reads none
    assert cols["Customer.party_id"] == ["customer_id"]  # the key taken from the parent reads the Entity's own key column
    session.manage_edit("update_property", {"object": "OrderItem", "name": "quantity", "column": "qty"})
    out = get(session, "bnd/columns")
    assert out["pending"] and out["columns"]["OrderItem.quantity"] == ["qty"]


def test_the_sql_of_a_binding_reads_the_bound_properties_from_the_table(session):
    out = get(session, "bnd/binding", entity="OrderItem")
    assert out["table"] == "order_items" and out["target"] == "sql:sqlite" and not out["error"]
    assert out["sql"].startswith("SELECT") and '"order_items"' in out["sql"] and '"item_status"' in out["sql"]
    assert "line_total" not in out["sql"]  # a computed property reads no column
    concept = get(session, "bnd/binding", entity="Party")
    assert concept["sql"] == "" and "테이블이 지정되지 않은" in concept["error"]
    with pytest.raises(LookupError):
        get(session, "bnd/binding", entity="Nope")


def test_the_sql_follows_the_edits_not_yet_sent(session):
    session.manage_edit("update_property", {"object": "OrderItem", "name": "quantity", "column": "qty"})
    out = get(session, "bnd/binding", entity="OrderItem")
    assert out["pending"] and '"qty"' in out["sql"]


def test_an_action_is_tried_on_a_record_and_no_request_is_left(session):
    before = len(session.studio.actions.proposals)
    out = post(session, "bnd/action/try", action="requestReturn", role="customer_agent", key="I1001", params={"reason": "단순 변심"})
    assert out["ok"] and out["on_record"] and out["approval"] is True and out["call"] is None
    by = {c["name"]: c for c in out["checks"]}
    assert by["role"]["passed"] and by["parameters"]["passed"] and by["target"]["passed"] and by["state"]["detail"] == "NORMAL → RETURN_REQUESTED"
    assert by["decision:returnEligibility"]["passed"] and "가능" in by["decision:returnEligibility"]["detail"]
    assert out["state"] == {"property": "item_status", "from": "NORMAL", "to": "RETURN_REQUESTED"}
    assert len(session.studio.actions.proposals) == before and session.pending_actions()["pending"] == []
    assert session.studio.fetch("OrderItem", "I1001")["item_status"] == "NORMAL"  # nothing was changed


def test_an_action_is_tried_on_given_values_when_no_record_is_named(session):
    late = post(session, "bnd/action/try", action="requestReturn", role="operator", params={"reason": "변심"},
                inputs={"returnEligibility": {"days_since_delivery": 30, "item_status": "NORMAL", "grade": "BASIC"}})
    assert not late["on_record"] and not late["ok"]
    assert not next(c for c in late["checks"] if c["name"] == "decision:returnEligibility")["passed"]
    soon = post(session, "bnd/action/try", action="requestReturn", role="operator", params={"reason": "변심"},
                inputs={"returnEligibility": {"days_since_delivery": 3, "item_status": "NORMAL"}})
    assert next(c for c in soon["checks"] if c["name"] == "decision:returnEligibility")["passed"]


def test_a_try_says_what_is_missing_and_who_may_not_ask(session):
    out = post(session, "bnd/action/try", action="requestReturn", role="support_agent", key="I1001", params={})
    by = {c["name"]: c for c in out["checks"]}
    assert not out["ok"] and not by["parameters"]["passed"] and by["parameters"]["detail"] == "reason 값 없음"
    assert by["role"]["passed"] == session.studio.onto.roles["support_agent"].can("request", "requestReturn")
    with pytest.raises(ValueError, match="배포되지 않은 Action"):
        post(session, "bnd/action/try", action="notThere", role="operator")
