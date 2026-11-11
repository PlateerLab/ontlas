"""What the forms write into the workspace module, and an API description read as definitions and actions."""
import json

import pytest

from ontlas.ingest import IngestError, ingest

from .conftest import EXAMPLE, LIB

MODULES = ["core", "commerce", "commerce-bindings", "commerce-operations", "commerce-operations-bindings", "fashion", "acme-overlay"]


@pytest.fixture
def ws():
    pytest.importorskip("yaml")
    from ontlas.library import Library
    from ontlas.manage import Workspace

    return Workspace(Library(LIB).resolve(MODULES), compose_kw={"namespace": "https://example.org/studio#", "name": "studio"})


def onto(ws):
    return ws.composed().ontology


def test_a_named_value_is_added_changed_and_taken_out(ws):
    from ontlas.manage import EditError

    ws.apply("add_parameter", {"name": "gift_limit", "type": "integer", "value": "3", "label": "선물 포장 한도", "unit": "개", "min": 0, "max": 9})
    p = onto(ws).parameters["gift_limit"]
    assert (p.value, p.unit, p.max) == (3, "개", 9)
    ws.apply("update_parameter", {"name": "gift_limit", "value": 5, "label": "포장 한도"})
    assert onto(ws).parameters["gift_limit"].value == 5 and onto(ws).parameters["gift_limit"].label == "포장 한도"
    with pytest.raises(EditError, match="at most"):
        ws.apply("update_parameter", {"name": "gift_limit", "value": 10})
    with pytest.raises(EditError, match="already exists"):
        ws.apply("add_parameter", {"name": "gift_limit", "value": 1})
    ws.apply("delete_parameter", {"name": "gift_limit"})
    assert "gift_limit" not in onto(ws).parameters


def test_a_named_value_a_rule_reads_stays(ws):
    from ontlas.manage import EditError

    with pytest.raises(EditError, match="read by rules"):
        ws.apply("delete_parameter", {"name": "free_shipping_amount"})
    ws.apply("update_parameter", {"name": "free_shipping_amount", "value": 70000, "cite": "배송비 정책서 v2.0"})
    assert onto(ws).parameters["free_shipping_amount"].value == 70000
    assert ws.module.extend["parameters"]["free_shipping_amount"]["cite"] == "배송비 정책서 v2.0"


def test_a_metric_is_defined_on_the_form_and_answered(ws):
    from ontlas.manage import EditError

    args = {"name": "cancelRate", "label": "취소율", "owner": "운영팀", "unit": "%", "scale": 100,
            "formula": {"match": {"x": "Order"}, "where": {"eq": ["x.status", "CANCELLED"]}, "value": {"count": "x"}},
            "denominator": {"value": {"count": "x"}}, "time": {"basis": "주문 일시", "property": "x.ordered_at"}}
    ws.apply("add_metric", args)
    assert onto(ws).metrics["cancelRate"].owner == "운영팀"
    ws.apply("update_metric", {"name": "cancelRate", "owner": "고객팀"})
    assert onto(ws).metrics["cancelRate"].owner == "고객팀"
    ws.apply("update_metric", {"name": "returnRate", "owner": "품질팀"})  # a standard's: extended, not edited
    assert ws.module.extend["metrics"]["returnRate"] == {"owner": "품질팀"}
    with pytest.raises(EditError):
        ws.apply("add_metric", {"name": "broken", "label": "깨짐", "owner": "x", "formula": {"match": {"x": "Nope"}, "value": {"count": "x"}}, "time": {"basis": "b"}})
    ws.apply("delete_metric", {"name": "cancelRate"})
    assert "cancelRate" not in onto(ws).metrics


def test_an_identity_is_defined_on_the_form_and_a_copy_passes_before_its_crosswalk_exists(ws, tmp_path):
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.review import review

    ws.apply("add_identity", {"name": "Partner", "label": "거래 상대", "members": {"Customer": {"phone": "phone"}, "Seller": {"phone": "phone"}},
                              "rules": [{"id": "same-phone", "match": ["phone"], "normalize": {"phone": "digits"}}]})
    assert "Partner" in onto(ws).objects and onto(ws).identities["Partner"].table == "partner_identity"
    st = load_studio(EXAMPLE.parent / "library" / "studio.yaml")
    rep = review(st, ws.module, attach=True)
    assert not rep["issues"]
    assert not [f for f in rep["measured"]["bind"]["findings"] if f["severity"] == "error"]
    ws.apply("update_identity", {"name": "Partner", "label": "거래처"})
    assert onto(ws).identities["Partner"].label == "거래처"
    ws.apply("delete_identity", {"name": "Partner"})
    assert "Partner" not in onto(ws).identities


def test_a_function_is_registered_and_a_standard_one_extended(ws):
    ws.apply("add_function", {"name": "lineValue", "label": "금액", "target": "OrderItem", "owner": "정산팀", "outputs": {"v": "decimal"}, "expr": "line_total * 2", "status": "draft"})
    assert onto(ws).functions["lineValue"].status == "draft"
    ws.apply("update_function", {"name": "lineValue", "status": "active", "version": "1.1.0"})
    assert onto(ws).functions["lineValue"].version == "1.1.0"
    ws.apply("update_function", {"name": "soldOut", "owner": "재고팀"})
    assert ws.module.extend["functions"]["soldOut"] == {"owner": "재고팀"}
    ws.apply("delete_function", {"name": "lineValue"})
    assert "lineValue" not in onto(ws).functions


def test_row_rules_are_written_as_filters_and_read_back(ws):
    from ontlas.manage import EditError, row_rule

    ws.apply("add_role", {"name": "region_desk", "label": "지역 담당", "read": ["Order", "OrderItem"],
                          "rows": [{"type": "Order", "property": "customer_id", "principal": "customer_id"},
                                   {"type": "OrderItem", "via": ["itemOf"], "property": "status", "value": "PAID"}]})
    r = onto(ws).roles["region_desk"]
    assert r.row_filters["Order"] == {"eq": ["$self.customer_id", {"principal": "customer_id"}]}
    assert row_rule("OrderItem", r.row_filters["OrderItem"]) == {"type": "OrderItem", "via": ["itemOf"], "property": "status", "value": "PAID"}
    with pytest.raises(EditError, match="has no property"):
        ws.apply("update_role", {"name": "region_desk", "rows": [{"type": "Order", "property": "nope", "value": "x"}]})
    with pytest.raises(EditError, match="compared with"):
        ws.apply("update_role", {"name": "region_desk", "rows": [{"type": "Order", "property": "status"}]})
    ws.apply("update_role", {"name": "region_desk", "rows": []})
    assert onto(ws).roles["region_desk"].row_filters == {}


def test_a_standard_roles_rows_change_over_it_and_one_the_form_cannot_say_is_kept(ws):
    from ontlas.manage import row_rule

    r = onto(ws).roles["customer_agent"]
    rules = [row_rule(t, s) for t, s in r.row_filters.items()]
    assert {"type": "Order", "via": [], "property": "customer_id", "principal": "customer_id"} in rules
    assert {"type": "OrderItem", "via": ["itemOf"], "property": "customer_id", "principal": "customer_id"} in rules
    odd = {"or": [{"eq": ["$self.status", "PAID"]}, {"eq": ["$self.status", "SHIPPED"]}]}
    assert row_rule("Order", odd) == {"type": "Order", "raw": odd}
    ws.apply("update_role", {"name": "customer_agent", "rows": [rules[0]]})
    assert list(onto(ws).roles["customer_agent"].row_filters) == ["Order"]
    assert ws.module.extend["roles"]["customer_agent"]["row_filters_drop"] == ["OrderItem"]
    ws.apply("update_role", {"name": "customer_agent", "rows": [{"type": "Order", "raw": odd}]})
    assert onto(ws).roles["customer_agent"].row_filters["Order"] == odd


def test_an_organisations_scope_is_set_and_cleared_on_the_form(ws):
    scope = {"attribute": "seller_id", "types": [{"type": "Seller", "property": "seller_id"}]}
    ws.apply("add_role", {"name": "seller_desk", "read": ["Seller"], "scope": scope})
    assert onto(ws).roles["seller_desk"].scope == {"attribute": "seller_id", "types": {"Seller": "seller_id"}}
    ws.apply("update_role", {"name": "seller_desk", "scope": {}})
    assert onto(ws).roles["seller_desk"].scope == {}
    ws.apply("update_role", {"name": "support_agent", "scope": {"attribute": "customer_id", "types": [{"type": "Customer", "property": "customer_id"}]}})
    assert "scope_set" in ws.module.extend["roles"]["support_agent"]


def test_an_action_takes_its_limits_and_its_outside_call_from_the_form(ws):
    ws.apply("add_action", {"name": "restock", "label": "재입고", "target": "Sku", "parameters": {"qty": {"type": "integer"}},
                            "set": {"stock": "$qty"}, "approval": {"auto_within": [{"parameter": "qty", "max": 50}], "agents": True},
                            "call": {"url": "https://wms.example/stock/$key", "method": "POST", "body": {"qty": "$qty"}},
                            "undo": {"url": "https://wms.example/stock/$key/undo", "method": "POST"}})
    a = onto(ws).actions["restock"]
    assert a.auto_within == [{"parameter": "qty", "max": 50}] and a.auto_agents and a.call["url"].startswith("https://wms")
    ws.apply("update_action", {"name": "requestReturn", "call": {"url": "https://oms.example/return/$key", "method": "POST"}})
    assert onto(ws).actions["requestReturn"].call["method"] == "POST"


def test_a_property_takes_a_transform_from_the_form(ws):
    ws.apply("add_property", {"object": "Coupon", "name": "rate_percent", "type": "decimal", "column": "discount_rate", "transform": "value * 100"})
    p = onto(ws).objects["Coupon"].properties["rate_percent"]
    assert p.transform == "value * 100" and "rate_percent__raw" in onto(ws).objects["Coupon"].properties
    ws.apply("update_property", {"object": "Coupon", "name": "rate_percent", "transform": "value * 10"})
    assert onto(ws).objects["Coupon"].properties["rate_percent"].transform == "value * 10"


# ---- an API description

SPEC = {"openapi": "3.0.3", "info": {"title": "주문 API"}, "servers": [{"url": "https://api.example/v1"}],
        "paths": {"/orders/{orderId}/cancel": {"post": {"operationId": "cancelOrder", "summary": "주문 취소", "requestBody": {"content": {"application/json": {
                      "schema": {"type": "object", "required": ["reason"], "properties": {"reason": {"type": "string", "title": "사유"}}}}}}}},
                  "/orders/{orderId}": {"get": {"summary": "주문 조회"}},
                  "/customers": {"post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Customer"}}}}}}},
        "components": {"schemas": {
            "Customer": {"title": "고객", "type": "object", "required": ["id", "name"],
                         "properties": {"id": {"type": "string"}, "name": {"type": "string", "title": "이름"},
                                        "grade": {"type": "string", "enum": ["BASIC", "VIP"], "x-enum-varnames": ["일반", "우수"]}}},
            "Base": {"type": "object", "properties": {"createdAt": {"type": "string", "format": "date-time"}}},
            "Order": {"allOf": [{"$ref": "#/components/schemas/Base"}, {"type": "object", "required": ["id"], "properties": {
                "id": {"type": "string"}, "customer": {"$ref": "#/components/schemas/Customer"}, "amount": {"type": "number"},
                "items": {"type": "array", "items": {"$ref": "#/components/schemas/Item"}}}}]},
            "Item": {"type": "object", "properties": {"id": {"type": "integer"}, "quantity": {"type": "integer", "maxLength": 3}}}}}}


def test_an_api_description_becomes_tables_codes_and_operations():
    d = ingest(json.dumps(SPEC).encode(), "orders.json")
    assert sorted(d.tables) == ["Base", "Customer", "Item", "Order"]
    o = d.tables["Order"]
    assert o.primary_key == ["id"] and {c.name for c in o.columns} >= {"id", "customer_key", "amount", "createdAt"}
    assert o.column("amount").type == "decimal" and o.column("createdAt").type == "datetime"
    assert {"columns": ["customer_key"], "table": "Customer", "ref_columns": ["id"]} in o.references
    assert any(r["table"] == "Order" for r in d.tables["Item"].references)  # a list points back at its owner
    assert [v["name"] for v in d.codes["Customer.grade"].values] == ["일반", "우수"]
    cancel = next(a for a in d.apis if a["name"] == "cancelOrder")
    assert cancel["table"] == "Order" and cancel["parameters"]["reason"]["required"] and cancel["method"] == "POST"
    assert d.documents[0]["kind"] == "api" and any(s["title"] == "GET /orders/{orderId}" for s in d.documents[0]["sections"])


def test_a_yaml_description_and_swagger_two_read_the_same_way():
    yaml = pytest.importorskip("yaml")
    assert sorted(ingest(yaml.safe_dump(SPEC, allow_unicode=True).encode(), "orders.yaml").tables) == sorted(ingest(json.dumps(SPEC).encode(), "o.json").tables)
    old = {"swagger": "2.0", "host": "api.example", "basePath": "/v1", "definitions": {"Thing": {"type": "object", "properties": {"id": {"type": "string"}}}},
           "paths": {"/things/{id}": {"delete": {"operationId": "dropThing"}}}}
    d = ingest(json.dumps(old).encode(), "old.json")
    assert d.apis[0]["url"] == "https://api.example/v1/things/{id}" and d.apis[0]["table"] == "Thing"


def test_a_file_that_is_not_an_api_description_is_refused():
    pytest.importorskip("yaml")
    with pytest.raises(IngestError, match="OpenAPI"):
        ingest(b"name: value\n", "settings.yaml")
    with pytest.raises(IngestError, match="no schemas"):
        ingest(json.dumps({"openapi": "3.0.0", "info": {}}).encode(), "empty.json")


def test_a_draft_turns_writing_operations_into_actions_behind_a_person():
    pytest.importorskip("yaml")
    from ontlas.definitions import schema_backend
    from ontlas.draft import draft
    from ontlas.modules import compose

    d = ingest(json.dumps(SPEC).encode(), "orders.json")
    plan = draft(schema_backend(d), name="orders", definitions=d)
    comp = compose(plan.modules(), namespace="https://example.org/o#")
    assert not comp.issues
    a = comp.ontology.actions["cancelOrder"]
    assert a.target == "Order" and a.approval and a.call["url"] == "https://api.example/v1/orders/$key/cancel"
    assert a.call["body"] == {"reason": "$reason"}
    again = ingest(json.dumps(d.to_dict()).encode(), "bundle.json")  # the one JSON carries the operations too
    assert [x["name"] for x in again.apis] == [x["name"] for x in d.apis]
