"""Named parameters: one value in a module, read by rules and computed properties, changed by a customer module."""
import pytest

from xgen_space import Ontology
from xgen_space.backends.sql import SqliteBackend
from xgen_space.compile.base import compiler_for
from xgen_space.decide.cells import CellError, Compare, OneOf, Range, parse_test
from xgen_space.decide.table import evaluate_table
from xgen_space.decide.zen import to_jdm
from xgen_space.expr import ExprError, check_computed, parse_expr
from xgen_space.modules import Module, ModuleError, compose, removal_impact, settle
from xgen_space.studio import Studio


def _shop(**more) -> dict:
    return {"module": "shop", "namespace": "https://example.com/o#",
            "parameters": {"return_window_days": {"type": "integer", "value": 14, "unit": "days", "label": "Return window",
                                                  "min": 1, "max": 90, "cite": "Terms 4.1"},
                           "bulk_quantity": 10, "tax_rate": 0.1},
            "objects": {"Line": {"key": "line_id", "source": {"table": "lines"}, "properties": {
                "line_id": {"type": "string"}, "age_days": {"type": "integer"}, "quantity": {"type": "integer"},
                "price": {"type": "decimal"},
                "bulk": {"type": "boolean", "expr": "quantity >= @bulk_quantity"},
                "tax": {"type": "decimal", "expr": "price * @tax_rate"},
                "twice": {"type": "decimal", "expr": "tax * 2"}}}},
            "decisions": {"returnable": {
                "target": "Line", "outputs": {"ok": "boolean", "window": "integer"}, "hit_policy": "first",
                "inputs": {"age": {"type": "integer", "property": "age_days"}},
                "rules": [{"id": "in", "when": {"age": "<= @return_window_days"},
                           "then": {"ok": True, "window": "@return_window_days"}},
                          {"id": "out", "when": {"age": "> @return_window_days"}, "then": {"ok": False}}]}},
            **more}


def _overlay(value=30) -> Module:
    return Module.from_dict({"module": "acme", "kind": "customer", "requires": ["shop"],
                             "extend": {"parameters": {"return_window_days": value}}})


@pytest.fixture
def source() -> SqliteBackend:
    b = SqliteBackend()
    b.script("CREATE TABLE lines (line_id TEXT, age_days INTEGER, quantity INTEGER, price REAL);"
             "INSERT INTO lines VALUES ('L1', 20, 12, 1000.0), ('L2', 5, 3, 500.0);")
    return b


def _studio(modules, source) -> Studio:
    st = Studio.from_modules(modules)
    st.add_backend("source", source)
    return st


def test_a_cell_reads_a_parameter_wherever_it_takes_a_literal():
    named = {"low": 3, "high": 7, "kind": "sample"}
    assert parse_test("<= @high", named) == Compare("<=", 7)
    assert parse_test("[@low..@high]", named) == Range(3, 7)
    assert parse_test("in [@low, 9]", named) == OneOf((3, 9))
    assert parse_test("@low, @high", named) == OneOf((3, 7))
    assert parse_test("@kind", named) == Compare("==", "sample")
    with pytest.raises(CellError, match="unknown parameter '@nope'"):
        parse_test("< @nope", named)
    with pytest.raises(CellError, match="unknown parameter"):
        parse_test("< @low")


def test_one_value_serves_rules_and_outputs(source):
    st = _studio([Module.from_dict(_shop())], source)
    res = st.decide("returnable", "L1")
    assert res.outputs == {"ok": False, "window": None} and res.matched == ["out"]
    res = st.decide("returnable", "L2")
    assert res.outputs == {"ok": True, "window": 14}
    assert res.parameters == {"return_window_days": 14} and res.to_dict()["parameters"] == {"return_window_days": 14}


def test_a_customer_module_changes_one_value_and_every_reader_follows(source):
    base, overlay = Module.from_dict(_shop()), _overlay()
    st = _studio([base, overlay], source)
    res = st.decide("returnable", "L1")
    assert res.outputs == {"ok": True, "window": 30} and res.parameters == {"return_window_days": 30}
    comp = st.composition
    assert comp.owner("parameter:return_window_days") == "shop"
    assert comp.touched["parameter:return_window_days"] == ["acme"]
    p = comp.ontology.parameters["return_window_days"]
    assert (p.value, p.label, p.unit, p.cite) == (30, "Return window", "days", "Terms 4.1")  # the rest stays
    assert "parameter:return_window_days" in overlay.elements()
    assert base.counts()["parameters"] == 3


def test_a_full_patch_can_cite_the_customers_own_terms():
    overlay = _overlay({"value": 21, "cite": "Acme terms 2"})
    p = compose([Module.from_dict(_shop()), overlay]).ontology.parameters["return_window_days"]
    assert (p.value, p.cite, p.max) == (21, "Acme terms 2", 90)


def test_a_customer_value_of_zero_is_a_value():
    d = _shop()
    d["parameters"]["free_sample"] = {"value": 5}
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["shop"],
                                "extend": {"parameters": {"free_sample": 0}}})
    assert compose([Module.from_dict(d), overlay]).ontology.parameters["free_sample"].value == 0


def test_computed_properties_read_the_value_in_every_language(source):
    st = _studio([Module.from_dict(_shop()), _overlay()], source)
    q = {"match": {"l": "Line"}, "return": ["l.line_id", "l.bulk", "l.tax", "l.twice"], "order": ["line_id"]}
    rows = st.run(q).rows
    assert rows[0][0] == "L1" and bool(rows[0][1]) is True and rows[0][2:] == (100.0, 200.0)
    assert not rows[1][1]
    assert ">= 10" in st.translate(q, "sql").text and "0.1" in st.translate(q, "sql").text
    assert ">= 10" in compiler_for(st.onto, "cypher").compile(q).text
    assert ">= 10" in compiler_for(st.onto, "sparql").compile(q).text


def test_the_graph_answers_the_same(source):
    pytest.importorskip("rdflib")
    from xgen_space.backends.rdf import RdflibBackend

    st = _studio([Module.from_dict(_shop())], source)
    st.add_backend("graph", RdflibBackend())
    st.project()
    q = st.query({"match": {"l": "Line"}, "return": ["l.line_id", "l.bulk", "l.tax"], "order": ["line_id"]})
    assert st.conformance(queries={"q": (q, {})}).passed


def test_a_customer_cannot_retype_a_parameter_or_extend_one_nobody_defined():
    with pytest.raises(ModuleError, match="changes the type of parameter"):
        compose([Module.from_dict(_shop()), _overlay({"value": "x", "type": "string"})])
    stray = Module.from_dict({"module": "acme", "requires": ["shop"], "extend": {"parameters": {"nope": 1}}})
    with pytest.raises(ModuleError, match="no attached module defines"):
        compose([Module.from_dict(_shop()), stray])


def test_validate_catches_wrong_values_and_unknown_names():
    assert any("is above 90" in i for i in compose([Module.from_dict(_shop()), _overlay(120)]).issues)
    assert any("is below 1" in i for i in compose([Module.from_dict(_shop()), _overlay(0)]).issues)
    assert any("'soon' is not integer" in i for i in compose([Module.from_dict(_shop()), _overlay("soon")]).issues)
    d = _shop()
    d["parameters"]["bad name"] = 1
    d["parameters"]["kind"] = {"type": "enum", "value": "a"}
    d["parameters"]["empty"] = {"type": "integer"}
    d["decisions"]["returnable"]["rules"][0]["when"]["age"] = "<= @return_window"
    d["decisions"]["returnable"]["rules"][1]["then"]["window"] = "@retrun_window_days"
    d["objects"]["Line"]["properties"]["bulk"]["expr"] = "quantity >= @bulk"
    issues = compose([Module.from_dict(d)]).issues
    assert "parameter bad name: the name is not an identifier" in issues
    assert any("parameter kind: type 'enum'" in i for i in issues)
    assert "parameter empty: needs a value" in issues
    assert "decision returnable rule in: age: unknown parameter '@return_window'" in issues
    assert "decision returnable rule out: window: unknown parameter '@retrun_window_days'" in issues
    assert "Line.bulk: unknown parameter '@bulk'" in issues


def test_expressions_type_the_parameter_they_read():
    onto = compose([Module.from_dict(_shop())]).ontology
    assert check_computed(onto, "Line", "bulk").type == "boolean"
    d = onto.to_dict()
    d["parameters"]["word"] = "x"
    d["objects"]["Line"]["properties"]["sum"] = {"type": "integer", "expr": "quantity + @word"}
    assert any("'+' takes numbers, not string" in i for i in Ontology.from_dict(d).validate())
    with pytest.raises(ExprError):
        parse_expr("quantity >= @")


def test_text_starting_with_at_stays_text_where_no_parameters_are_in_use():
    d = _shop()
    del d["parameters"]
    for name in ("bulk", "tax", "twice"):
        del d["objects"]["Line"]["properties"][name]
    d["decisions"]["returnable"] = {"target": "Line", "outputs": {"to": "string"},
                                    "inputs": {"age": {"type": "integer", "property": "age_days"}},
                                    "rules": [{"id": "r", "when": {}, "then": {"to": "@support"}}]}
    onto = compose([Module.from_dict(d)]).ontology
    assert onto.validate() == []
    assert evaluate_table(onto.decisions["returnable"], {"age": 1})[0] == {"to": "@support"}


def test_the_definition_round_trips():
    onto = compose([Module.from_dict(_shop())]).ontology
    d = onto.to_dict()
    assert d["parameters"]["return_window_days"]["value"] == 14 and d["parameters"]["return_window_days"]["min"] == 1
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.parameters == onto.parameters
    assert again.decisions["returnable"].named["bulk_quantity"] == 10
    zero = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "parameters": {"z": {"value": 0}}})
    assert zero.to_dict()["parameters"]["z"]["value"] == 0


def test_a_bare_value_says_its_own_type():
    onto = compose([Module.from_dict(_shop())]).ontology
    assert (onto.parameters["bulk_quantity"].type, onto.parameters["tax_rate"].type) == ("integer", "decimal")


def test_zen_export_writes_the_value_in():
    onto = compose([Module.from_dict(_shop()), ]).ontology
    rule = to_jdm(onto.decisions["returnable"])["nodes"][1]["content"]["rules"][0]
    assert rule["in_age"] == "$ <= 14" and rule["out_window"] == "14"


def test_findings_read_the_value():
    d = _shop()
    d["decisions"]["returnable"]["rules"][1]["when"]["age"] = "> @bulk_quantity"  # 11..14 now answered twice
    found = compose([Module.from_dict(d)]).findings
    assert [f.kind for f in found] == ["overlap"] and found[0].where == {"age": "11..13 | 14"}


def test_removing_a_parameter_something_reads_is_refused_or_settled():
    base = Module.from_dict(_shop())
    gone = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["shop"],
                             "remove": {"parameters": ["bulk_quantity"]}})
    comp = compose([base, gone])
    assert "Line.bulk: unknown parameter '@bulk_quantity'" in comp.issues and "parameter:bulk_quantity" in comp.removed
    assert removal_impact([base, _overlay()], "acme").changed == ["parameter:return_window_days"]
    taken = settle(gone, [base])
    assert "property:Line.bulk" in taken and compose([base, gone]).issues == []
