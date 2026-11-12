"""What a platform calls first: what a question's words mean, where a definition sits, whether values keep to the rules,
and which definitions answered. No source is needed for any of them."""
from __future__ import annotations

from pathlib import Path

import pytest

from ontlas.config import load_studio
from ontlas.rest import ROUTES, Rest, definition, openapi
from ontlas.semantic import CardError, card_spec
from ontlas.tools import StudioTools

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

SHOP = Path(__file__).resolve().parent.parent / "examples" / "library" / "studio.yaml"


@pytest.fixture(scope="module")
def rest():
    return Rest([("t", StudioTools(load_studio(SHOP), actor_id="flow", audit=True))])


def _call(rest, path, body, method="POST"):
    return rest.answer(method, path, body, rest.caller("Bearer t"))


def test_terms_say_what_each_word_stands_for_and_what_to_search_by(rest):
    code, out = _call(rest, "/v1/terms", {"text": "배달완료된 주문의 주문 총액과 결제 단가"})
    assert code == 200
    by = {m["term"]: m for m in out["matched"]}
    assert by["배송완료"]["meaning"] == "주문 · 주문 상태 = DELIVERED" and by["배송완료"]["concept_kind"] == "코드값"
    assert by["주문금액"]["meaning"] == "주문 · 주문 금액"
    labels = {x["term"]: x["labels"] for x in out["expansions"]}
    assert "주문 총액" in labels["주문금액"] and "배달완료" not in labels["배송완료"]  # a hidden label is for reading only
    named = {x["label"]: [c["concept"] for c in x["concepts"]] for x in out["defined"]}
    assert named["결제 단가"] == ["property:OrderItem.unit_price"]  # named by its own label, no term needed
    assert "주문 총액" not in named and "배달완료" not in named  # what a term read is not read again


def test_an_object_says_where_it_sits(rest):
    _, out = _call(rest, "/v1/object", {"name": "Order"})
    assert out["area"] == {"name": "Order", "label": "주문"} and out["parent"]["name"] == "Agreement"
    _, party = _call(rest, "/v1/object", {"name": "Party"})
    assert {"name": "Customer", "label": "고객"} in party["children"]


def test_values_are_checked_against_the_definition_and_the_cards_that_bound_them(rest):
    code, out = _call(rest, "/v1/validate", {"object": "OrderItem", "values": {
        "unit_price": -100, "quantity": "two", "item_status": "DONE", "color": "red"}})
    assert code == 200 and out["valid"] is False and out["rules"] == ["unit-price-not-negative"]
    by = {v["property"]: v for v in out["violations"]}
    assert {p: v["kind"] for p, v in by.items()} == {"unit_price": "rule", "quantity": "type", "item_status": "code",
                                                     "color": "unknown"}
    rule = by["unit_price"]
    assert (rule["rule"], rule["layer"], rule["module"], rule["version"], rule["min"]) == \
        ("unit-price-not-negative", "standard", "commerce", "1.0.0", 0)
    assert [a["code"] for a in by["item_status"]["allowed"]] == ["NORMAL", "RETURN_REQUESTED", "RETURNED"]
    _, ok = _call(rest, "/v1/validate", {"object": "OrderItem", "values": {"unit_price": 12000, "quantity": 2}})
    assert ok["valid"] is True and ok["violations"] == []
    _, whole = _call(rest, "/v1/validate", {"object": "OrderItem", "values": {"unit_price": 12000}, "complete": True})
    assert [(v["property"], v["kind"]) for v in whole["violations"]] == [("item_id", "missing")]
    assert _call(rest, "/v1/validate", {"object": "Nothing", "values": {}})[0] == 400


def test_a_card_bounds_a_named_value_or_a_property():
    spec = card_spec({"id": "c", "type": "compute", "statement": "s", "check": {"property": "OrderItem.unit_price", "min": 0}})
    assert spec["check"] == {"property": "OrderItem.unit_price", "min": 0}
    for bad in ({"property": "unit_price", "min": 0}, {"parameter": "days", "property": "A.b", "min": 0},
                {"property": "A.b"}):
        with pytest.raises(CardError):
            card_spec({"id": "c", "type": "compute", "statement": "s", "check": bad})


def test_every_answer_says_which_definitions_answered(rest):
    _, a = _call(rest, "/v1/rules", {"k": 1})
    _, b = _call(rest, "/v1/ontology", {}, method="GET")
    assert a["definition"] == b["definition"] == definition(rest.tools)
    mods = {m["module"]: m["version"] for m in a["definition"]["modules"]}
    assert mods["commerce"] == "1.0.0" and len(a["definition"]["version"]) == 12


def test_an_agent_over_mcp_gets_the_same_calls():
    pytest.importorskip("mcp")
    import asyncio
    import json

    from ontlas.mcp_server import build_server

    srv = build_server(load_studio(SHOP), read_only=True)
    assert {"decide", "find_rules", "read_terms", "validate_values", "run_questions"} <= \
        {t.name for t in asyncio.run(srv.list_tools())}

    def call(name, args):
        res = asyncio.run(srv.call_tool(name, args))
        blocks = getattr(res, "content", None) or (res[0] if isinstance(res, tuple) else res)  # by mcp version
        return json.loads(blocks[0].text)

    asked = call("decide", {"decision": "returnEligibility", "values": {"days_since_delivery": 3}})
    assert asked["needs_values"] is True and {m["input"] for m in asked["missing"]} >= {"item_status", "customer_grade"}
    got = call("decide", {"decision": "returnEligibility", "values": {
        "days_since_delivery": 4, "item_status": "NORMAL", "category_returnable": True, "customer_grade": "VIP"}})
    assert got["mode"] == "values" and got["decided_by"]["rule"]
    assert call("validate_values", {"object": "OrderItem", "values": {"unit_price": -1}})["valid"] is False
    assert call("read_terms", {"text": "배달완료"})["matched"][0]["term"] == "배송완료"


def test_the_openapi_document_offers_validate():
    paths = openapi("0")["paths"]
    assert "/v1/validate" in paths and set(paths["/v1/validate"]["post"]["requestBody"]["content"]["application/json"]
                                           ["schema"]["required"]) == {"object", "values"}
    assert len(paths) == len(ROUTES) + 1  # and /v1/libraries
