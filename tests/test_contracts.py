"""Interfaces in queries, functions under a contract, approval limits, transforms and transaction values."""
import io
import json

import pytest

from ontlas import ModelError, Ontology
from ontlas.actions import Actor, HttpCaller
from ontlas.backends.sql import SqliteBackend
from ontlas.functions import FunctionError, reads
from ontlas.review import FlowSettings, gates, measure, value_accuracy
from ontlas.roles import AccessDenied
from ontlas.studio import Studio
from ontlas.tools import StudioTools

SEED = """
CREATE TABLE shops (shop_id TEXT PRIMARY KEY, name TEXT, region TEXT);
CREATE TABLE goods (goods_id TEXT PRIMARY KEY, name TEXT, price_cents INTEGER, on_sale TEXT, shop_id TEXT, stock INTEGER);
CREATE TABLE sales (sale_id TEXT PRIMARY KEY, goods_id TEXT, charged REAL, sold_out INTEGER);
INSERT INTO shops VALUES ('H1', '북쪽 상점', 'N'), ('H2', '남쪽 상점', 'S');
INSERT INTO goods VALUES ('G1', '연필', 1250, 'Y', 'H1', 3), ('G2', '공책', 3000, 'N', 'H2', 0);
INSERT INTO sales VALUES ('A1', 'G1', 12.5, 0), ('A2', 'G2', 30, 1);
"""


def spec(**over) -> dict:
    d = {
        "ontology": "shop", "namespace": "https://example.org/shop#",
        "parameters": {"step": {"type": "integer", "value": 10, "label": "허용 폭"}},
        "interfaces": {"Named": {"properties": ["name"], "label": "이름 있음"}},
        "objects": {
            "Shop": {"key": "shop_id", "source": {"table": "shops"}, "implements": ["Named"],
                     "properties": {"shop_id": {"type": "string"}, "name": {"type": "string"}, "region": {"type": "string"}}},
            "Goods": {"key": "goods_id", "source": {"table": "goods"}, "implements": ["Named"],
                      "properties": {
                          "goods_id": {"type": "string"}, "name": {"type": "string"}, "shop_id": {"type": "string"},
                          "price": {"type": "decimal", "column": "price_cents", "transform": "value / 100", "source_type": "integer"},
                          "on_sale": {"type": "boolean", "column": "on_sale", "transform": "value = 'Y'", "source_type": "string"},
                          "stock": {"type": "integer"}, "list_price": {"type": "integer", "column": "price_cents"}}},
            "Sale": {"key": "sale_id", "source": {"table": "sales"},
                     "properties": {"sale_id": {"type": "string"}, "goods_id": {"type": "string"}, "charged": {"type": "decimal"},
                                    "sold_out": {"type": "boolean"}}}},
        "links": {"goodsOf": {"from": "Goods", "to": "Shop", "cardinality": "many_to_one", "on": {"shop_id": "shop_id"}}},
        "decisions": {"canSell": {"target": "Goods", "inputs": {"stock": {"type": "integer", "property": "stock"}},
                                  "outputs": {"ok": "boolean"},
                                  "rules": [{"id": "none", "when": {"stock": "<= 0"}, "then": {"ok": False}},
                                            {"id": "some", "when": {}, "then": {"ok": True}}]}},
        "queries": {"sales": {"query": {"match": {"s": "Sale"}, "return": ["s.sale_id", "s.goods_id", "s.charged", "s.sold_out"],
                                        "order": ["sale_id"]}}},
        "actions": {"setPrice": {"target": "Goods", "parameters": {"to": {"type": "integer"}}, "set": {"list_price": "$to"},
                                 "approval": {"auto_within": [{"property": "list_price", "percent": "@step"}]}}},
        "functions": {
            "withTax": {"target": "Goods", "version": "1.2.0", "owner": "정산팀", "inputs": {"rate": {"type": "decimal", "required": False, "default": 0.1}},
                        "outputs": {"amount": "decimal"}, "expr": "price * (1 + @rate)"},
            "sellable": {"runtime": "decision", "target": "Goods", "decision": "canSell", "outputs": {"ok": "boolean"}},
            "allSales": {"runtime": "query", "query": "sales"},
            "score": {"runtime": "python", "target": "Goods", "entry": "scorer", "outputs": {"score": "integer"}},
            "forecast": {"runtime": "http", "target": "Goods", "outputs": {"demand": "integer"},
                         "call": {"url": "https://model.example/forecast/$key", "method": "GET", "path": "data"}}},
        "roles": {"clerk": {"read": ["Goods", "Shop"], "run": ["withTax"], "request": ["setPrice"], "execute": ["setPrice"]},
                  "north": {"read": ["Goods", "Shop"], "row_filters": {"Goods": {"eq": ["$self.shop_id", "H1"]}}},
                  "viewer": {"read": ["Goods", "Shop"]}},
    }
    d.update(over)
    return d


@pytest.fixture
def shop() -> Studio:
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(spec()).check())
    st.add_backend("source", b)
    return st


def graph(st: Studio) -> Studio:
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    st.add_backend("graph", RdflibBackend())
    st.project(into=["graph"])
    return st


# ---- an interface reads like a parent

def test_a_query_names_an_interface_and_gets_every_type_that_implements_it(shop):
    q = {"match": {"x": "Named"}, "return": ["x.name"], "order": ["name"]}
    want = [("공책",), ("남쪽 상점",), ("북쪽 상점",), ("연필",)]
    assert sorted(shop.run(q).rows) == sorted(want)
    assert sorted(graph(shop).run(q, backend="graph").rows) == sorted(want)
    assert "Named" not in shop.onto.objects  # only a query sees the type
    for language in ("sql", "sparql", "cypher", "gremlin"):
        assert shop.translate(q, language).text


def test_an_interface_passes_no_row_limit_of_a_type_behind_it(shop):
    q = {"match": {"x": "Named"}, "return": ["x.name"]}
    assert len(shop.run(q, role="viewer").rows) == 4
    with pytest.raises(AccessDenied, match="row by row"):
        shop.run(q, role="north")


def test_through_an_interface_a_role_sees_the_strictest_mask():
    d = spec()
    d["objects"]["Shop"]["properties"]["name"]["mask"] = "full"
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    res = st.run({"match": {"x": "Named"}, "return": ["x.name"]}, role="viewer")
    assert {r[0] for r in res.rows} == {"***"}
    with pytest.raises(AccessDenied, match="masked"):
        st.run({"match": {"x": "Named"}, "where": {"eq": ["x.name", "연필"]}, "return": ["x.name"]}, role="viewer")


def test_an_interface_reads_stored_properties():
    d = spec()
    d["objects"]["Shop"]["properties"]["name"] = {"type": "string", "expr": "upper(region)"}
    assert any("computed" in i for i in Ontology.from_dict(d).validate())


# ---- a transform changes a column on its way in

def test_a_transform_reads_the_same_on_every_store_and_is_written_back_as_declared(shop):
    q = {"match": {"g": "Goods"}, "return": ["g.goods_id", "g.price", "g.on_sale"], "order": ["goods_id"]}
    rows = [(k, float(p), bool(s)) for k, p, s in shop.run(q).rows]
    assert rows == [("G1", 12.5, True), ("G2", 30.0, False)]
    got = [(k, float(p), bool(s)) for k, p, s in graph(shop).run(q, backend="graph").rows]
    assert got == rows
    assert shop.run({"match": {"g": "Goods"}, "where": {"gt": ["g.price", 20]}, "return": ["g.goods_id"]}).rows == [("G2",)]
    back = shop.onto.to_dict()["objects"]["Goods"]["properties"]["price"]
    assert back["transform"] == "value / 100" and "expr" not in back and back["column"] == "price_cents"
    assert Ontology.from_dict(shop.onto.to_dict()).check().objects["Goods"].properties["price__raw"].internal


@pytest.mark.parametrize("change, why", [
    ({"goods_id": {"type": "string", "transform": "upper(value)"}}, "key"),
    ({"price": {"type": "decimal", "columns": ["a", "b"], "transform": "value"}}, "one column"),
    ({"stock": {"type": "integer", "source_type": "integer"}}, "goes with a transform"),
    ({"stock": {"type": "integer", "transform": "value", "source_type": "money"}}, "source_type"),
])
def test_what_a_transform_may_not_do(change, why):
    d = spec()
    d["objects"]["Goods"]["properties"].update(change)
    assert any(why in i for i in Ontology.from_dict(d).validate())


def test_an_action_does_not_write_a_transformed_property():
    d = spec()
    d["actions"]["setPrice"]["set"] = {"price": "$to"}
    d["actions"]["setPrice"]["approval"] = True
    assert any("computed and cannot be set" in i for i in Ontology.from_dict(d).validate())


# ---- functions

def test_an_expression_function_runs_on_the_store_with_its_inputs_and_says_which_version_ran(shop):
    out = shop.function("withTax", "G1", {"rate": 0.2})
    assert out["outputs"]["amount"] == pytest.approx(15.0) and out["version"] == "1.2.0" and out["owner"] == "정산팀"
    assert shop.function("withTax", "G1")["outputs"]["amount"] == pytest.approx(13.75)  # its default
    assert "property:Goods.price__raw" in reads(shop.onto, shop.onto.functions["withTax"])
    assert shop.function_log[-1]["function"] == "withTax"


def test_a_function_over_a_decision_a_query_and_registered_code(shop):
    assert shop.function("sellable", "G2")["outputs"] == {"ok": False}
    assert [r["sale_id"] for r in shop.function("allSales")["outputs"]["rows"]] == ["A1", "A2"]
    with pytest.raises(FunctionError, match="registered no callable"):
        shop.function("score", "G1")
    shop.entries["scorer"] = lambda row, inputs: {"score": row["stock"] * 2}
    assert shop.function("score", "G1")["outputs"] == {"score": 6}
    shop.entries["scorer"] = lambda row, inputs: {"score": "high"}
    with pytest.raises(FunctionError, match="not integer"):  # what comes back is held to the contract
        shop.function("score", "G1")
    shop.entries["scorer"] = lambda row, inputs: {}
    with pytest.raises(FunctionError, match="gave no output"):
        shop.function("score", "G1")


def test_a_function_calls_only_a_host_the_deployment_allows(shop):
    with pytest.raises(FunctionError, match="no allowed host"):
        shop.function("forecast", "G1")

    class Reply(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    seen = []

    def opener(req, timeout=0):
        seen.append(req.full_url)
        return Reply(json.dumps({"data": {"demand": 7}}).encode())

    shop.actions.caller = HttpCaller(["model.example"], opener=opener)
    assert shop.function("forecast", "G1")["outputs"] == {"demand": 7}
    assert seen == ["https://model.example/forecast/G1"]
    shop.actions.caller = HttpCaller(["other.example"], opener=opener)
    with pytest.raises(ValueError, match="not an allowed host"):
        shop.function("forecast", "G1")


def test_a_role_is_given_a_function_by_name_and_a_status_decides_who_runs_it(shop):
    tools = StudioTools(shop, role="clerk")
    assert [f["name"] for f in tools.list_functions()["functions"]] == ["withTax"]
    assert tools.run_function("withTax", "G1")["outputs"]["amount"] == pytest.approx(13.75)
    with pytest.raises(PermissionError, match="may not run"):
        tools.run_function("sellable", "G1")
    shop.onto.functions["withTax"].status = "draft"
    with pytest.raises(FunctionError, match="draft"):
        tools.run_function("withTax", "G1")
    with pytest.raises(FunctionError, match="draft"):  # no role is no exemption: an API without one is still not a person
        shop.function("withTax", "G1")
    assert shop.function("withTax", "G1", trial=True)["outputs"]  # a person trying it out
    shop.onto.functions["withTax"].status = "retired"
    with pytest.raises(FunctionError, match="retired"):
        shop.function("withTax", "G1")


def test_an_expression_needs_a_value_for_each_input():
    d = spec()
    d["functions"]["withTax"]["inputs"]["rate"] = {"type": "decimal", "required": False}
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    with pytest.raises(FunctionError, match="no value"):
        st.function("withTax", "G1")


def test_a_function_keeps_to_the_rows_of_the_role(shop):
    d = shop.onto.roles["north"]
    d.run = ["withTax"]
    assert shop.function("withTax", "G1", role="north")["outputs"]
    with pytest.raises(PermissionError, match="outside"):
        shop.function("withTax", "G2", role="north")


def test_a_function_on_a_masked_value_gives_it_masked():
    d = spec()
    d["objects"]["Goods"]["properties"]["stock"]["mask"] = "full"
    d["functions"]["double"] = {"target": "Goods", "outputs": {"n": "integer"}, "expr": "stock * 2"}
    d["roles"]["clerk"]["run"].append("double")
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    assert st.function("double", "G1", role="clerk")["outputs"] == {"n": "***"}
    assert st.function("double", "G1")["outputs"] == {"n": 6}


@pytest.mark.parametrize("change, why", [
    ({"runtime": "shell"}, "runtime"), ({"status": "old"}, "status"), ({"version": "new"}, "version"),
    ({"target": "Nope"}, "unknown"), ({"outputs": {"a": "money"}}, "output 'a'"), ({"expr": "nope + 1"}, "nope"),
    ({"outputs": {"a": "integer", "b": "integer"}}, "one output"),
])
def test_a_function_that_does_not_hold_is_refused(change, why):
    d = spec()
    d["functions"]["withTax"].update(change)
    assert any(why in i for i in Ontology.from_dict(d).validate() if i.startswith("function"))


def test_a_definition_names_a_callable_and_brings_no_code():
    d = spec()
    d["functions"]["score"]["entry"] = "os:system"
    st = Studio(Ontology.from_dict(d).check())
    b = SqliteBackend()
    b.script(SEED)
    st.add_backend("source", b)
    with pytest.raises(FunctionError, match="registered no callable"):
        st.function("score", "G1")


def test_a_condition_of_an_action_can_be_a_function(shop):
    d = spec()
    d["actions"]["setPrice"]["criteria"] = [{"function": "sellable", "expect": {"ok": True}}]
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    who = Actor("kim", "human", ["clerk"])
    assert st.actions.request("setPrice", "G1", {"to": 1300}, actor=who).status == "executed"
    assert st.actions.request("setPrice", "G2", {"to": 3100}, actor=who).status == "rejected"


# ---- approval limits

def test_inside_its_limit_an_action_runs_and_past_it_a_person_approves(shop):
    who = Actor("kim", "human", ["clerk"])
    p = shop.actions.request("setPrice", "G1", {"to": 1300}, actor=who)  # 4% of 1250
    assert p.status == "executed" and p.approved_by == "auto" and p.limits[0]["within"]
    assert any(e.event == "auto_approved" for e in shop.actions.audit)
    q = shop.actions.request("setPrice", "G2", {"to": 4000}, actor=who)  # 33% of 3000
    assert q.status == "pending" and not q.limits[0]["within"] and q.limits[0]["limit"] == 10
    assert shop.fetch("Goods", "G2")["list_price"] == 3000
    assert shop.actions.approve(q.id, approver=Actor("lee", "human", ["clerk"])).status == "executed"


def test_an_agent_goes_to_a_person_unless_the_action_says_otherwise():
    d = spec()
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    bot = Actor("bot", "agent", ["clerk"])
    assert st.actions.request("setPrice", "G1", {"to": 1300}, actor=bot).status == "pending"
    d["actions"]["setPrice"]["approval"]["agents"] = True
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    assert st.actions.request("setPrice", "G1", {"to": 1300}, actor=bot).status == "executed"
    assert st.actions.request("setPrice", "G2", {"to": 4000}, actor=bot).status == "pending"  # past it, still a person


def test_inside_the_limit_without_the_right_to_execute_it_waits():
    d = spec()
    d["roles"]["clerk"]["execute"] = []
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    assert st.actions.request("setPrice", "G1", {"to": 1300}, actor=Actor("kim", "human", ["clerk"])).status == "pending"


def test_a_limit_by_delta_and_by_a_requested_amount():
    d = spec()
    d["actions"]["setPrice"]["approval"] = {"auto_within": [{"property": "list_price", "delta": 100}, {"parameter": "to", "max": 2000}]}
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d).check())
    st.add_backend("source", b)
    who = Actor("kim", "human", ["clerk"])
    assert st.actions.request("setPrice", "G1", {"to": 1340}, actor=who).status == "executed"
    assert st.actions.request("setPrice", "G1", {"to": 1500}, actor=who).status == "pending"  # past the delta
    assert st.actions.request("setPrice", "G2", {"to": 2950}, actor=who).status == "pending"  # past the amount
    assert Ontology.from_dict(st.onto.to_dict()).actions["setPrice"].auto_within == st.onto.actions["setPrice"].auto_within


@pytest.mark.parametrize("limit, why", [
    ({"delta": 1}, "names a property or a parameter"), ({"property": "list_price"}, "give delta"),
    ({"property": "name", "delta": 1}, "reads a number"), ({"property": "stock", "delta": 1}, "does not set"),
    ({"parameter": "to", "delta": 1}, "has no before"), ({"parameter": "x", "max": 1}, "not a parameter"),
    ({"property": "list_price", "percent": "@nope"}, "unknown named value"), ({"property": "list_price", "percent": "ten"}, "number or @name"),
])
def test_a_limit_that_does_not_hold_is_refused(limit, why):
    d = spec()
    d["actions"]["setPrice"]["approval"] = {"auto_within": [limit]}
    assert any(why in i for i in Ontology.from_dict(d).validate())


def test_an_action_with_only_an_outside_call_writes_nothing(shop):
    from ontlas.actions import SqlWriteback

    assert SqlWriteback(shop.backend()).apply(shop.onto, "Goods", "G1", {}) == 0


# ---- transaction values

VALUES = [{"name": "charged", "label": "판매가", "query": "sales", "key": "goods_id", "truth": "charged",
           "answer": {"type": "Goods", "property": "price"}},
          {"name": "soldOut", "label": "품절", "query": "sales", "key": "goods_id", "truth": "sold_out",
           "answer": {"decision": "canSell", "output": "ok"}}]


def test_values_are_held_case_by_case_against_what_the_system_recorded(shop):
    rep = value_accuracy(shop, VALUES[:1])
    assert (rep["cases"], rep["errors"]) == (2, 0)
    shop.backend().run("UPDATE sales SET charged = 11 WHERE sale_id = 'A1'", ())
    rep = value_accuracy(shop, VALUES[:1])
    assert rep["errors"] == 1 and rep["items"][0]["mismatches"] == [{"key": "G1", "answer": 12.5, "truth": 11}]
    assert value_accuracy(shop, [{**VALUES[0], "tolerance": 2}])["errors"] == 0


def test_a_flag_and_a_stored_number_are_one_answer(shop):
    rep = value_accuracy(shop, VALUES[1:])  # canSell is the opposite of sold_out, so every case differs
    assert rep["errors"] == 2


def test_the_flow_holds_a_change_to_no_wrong_value(shop):
    settings = FlowSettings.from_dict({"gates": {"check": {"max_value_errors": 0}}, "values": VALUES[:1]})
    assert all(g.passed for g in gates(measure(shop, settings), settings))
    shop.backend().run("UPDATE sales SET charged = 11 WHERE sale_id = 'A1'", ())
    measured = measure(shop, settings)
    assert measured["check"]["value_errors"] == 1
    assert not all(g.passed for g in gates(measured, settings))
    assert FlowSettings.from_dict(settings.to_dict()).values == settings.values


def test_a_value_can_be_read_from_the_system_api(shop):
    class Reply(io.BytesIO):
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    shop.actions.caller = HttpCaller(["shop.example"], opener=lambda req, timeout=0: Reply(b'{"data": {"price": 12.5}}'))
    spec_ = {**VALUES[0], "query": "sales", "truth": {"url": "https://shop.example/price/$key", "method": "GET", "path": "data.price"}}
    assert value_accuracy(shop, [spec_])["items"][0]["mismatches"] == [{"key": "G2", "answer": 30, "truth": 12.5}]


@pytest.mark.parametrize("value, why", [({"query": "q"}, "needs 'key'"), ({"query": "q", "key": "k", "truth": "t", "answer": {"x": 1}}, "answers by")])
def test_a_value_that_does_not_hold_is_refused(value, why):
    with pytest.raises(ValueError, match=why):
        FlowSettings.from_dict({"values": [value]})


def test_a_model_error_names_the_function():
    d = spec()
    d["functions"]["sellable"]["decision"] = "gone"
    with pytest.raises(ModelError, match="function sellable"):
        Ontology.from_dict(d).check()


# ---- what a platform calls

def test_a_platform_runs_a_function_reads_context_and_requests_an_action_in_plain_json(shop):
    from ontlas.rest import Rest, openapi, tool_list

    rest = Rest(StudioTools(shop, role="clerk", actor_id="api"), "t")
    code, out = rest.answer("POST", "/v1/function", {"name": "withTax", "key": "G1"})
    assert code == 200 and out["version"] == "1.2.0"
    code, out = rest.answer("POST", "/v1/actions", {"action": "setPrice", "key": "G1", "params": {"to": 1300}})
    assert code == 200 and json.dumps(out)  # a decimal in the row before does not stop the answer
    code, out = rest.answer("GET", "/v1/functions", {})
    assert [f["name"] for f in out["functions"]] == ["withTax"]
    code, out = rest.answer("POST", "/v1/context", {"text": "연필"})
    assert code == 200 and isinstance(out["text"], str)
    names = [t["name"] for t in tool_list()]
    assert {"run_function", "list_functions", "agent_context"} <= set(names)
    spec = openapi("1", "https://space.example")
    assert spec["servers"] == [{"url": "https://space.example"}]
    body = spec["paths"]["/v1/query"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert body["properties"]["query"]["type"] == "string"  # a parser that wants a type reads the name of a query
