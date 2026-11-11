"""Dates kept as text, and the row of a period table that is valid now."""
import json
from datetime import datetime

import pytest

from ontlas import Ontology
from ontlas.actions import Actor
from ontlas.backends.sql import SqliteBackend
from ontlas.cli import main
from ontlas.compile.base import CompileError, compiler_for
from ontlas.decide.periods import overlapping_periods
from ontlas.expr import ExprError, check_computed, date_format, dependencies, encode_text_date, parse_expr
from ontlas.modules import Module, ModuleError, compose
from ontlas.roles import mask_style
from ontlas.studio import Studio

NOW = datetime(2026, 3, 15, 9, 30)


def _definition() -> dict:
    return {
        "ontology": "shop", "namespace": "https://example.com/o#",
        "objects": {
            "Order": {"key": "order_id", "source": {"table": "orders"}, "properties": {
                "order_id": {"type": "string"},
                "placed_on": {"type": "date", "column": "PLACED_YMD", "format": "YYYYMMDD", "label": "Placed on"},
                "shipped_at": {"type": "datetime", "column": "SHIPPED_STAMP", "format": "YYYYMMDDHH24MISS"},
                "closed_at": {"type": "datetime", "columns": ["CLOSED_YMD", "CLOSED_HMS"], "format": "YYYYMMDD|HHMISS"},
                "slashed": {"type": "date", "column": "SLASHED", "format": "DD/MM/YYYY"},
                "status": {"type": "string"},
                "age_days": {"type": "integer", "expr": "days_between(placed_on, today())"},
                "placed_year": {"type": "integer", "expr": "year(placed_on)"},
                "placed_month": {"type": "integer", "expr": "month(placed_on)"},
                "is_recent": {"type": "boolean", "expr": "placed_on >= '2026-03-01'"}}},
            "Product": {"key": "product_id", "source": {"table": "products"}, "properties": {
                "product_id": {"type": "string"}, "name": {"type": "string"},
                "price_now": {"type": "decimal", "expr": "current(prices.amount)", "label": "Current price"},
                "sale_now": {"type": "string", "expr": "current(sales.label)"},
                "price_or_zero": {"type": "decimal", "expr": "coalesce(current(prices.amount), 0)"}}},
            "Price": {"key": "price_id", "source": {"table": "prices"},
                      "period": {"start": "valid_from", "end": "valid_to", "of": "priceOf"}, "properties": {
                "price_id": {"type": "string"}, "product_id": {"type": "string"}, "amount": {"type": "decimal"},
                "valid_from": {"type": "date", "column": "START_YMD", "format": "YYYYMMDD"},
                "valid_to": {"type": "date", "column": "END_YMD", "format": "YYYYMMDD"}}},
            "Sale": {"key": "sale_id", "source": {"table": "sales"},
                     "period": {"start": "starts_at", "end": "ends_at", "end_exclusive": True}, "properties": {
                "sale_id": {"type": "string"}, "product_id": {"type": "string"}, "label": {"type": "string"},
                "starts_at": {"type": "datetime"}, "ends_at": {"type": "datetime"}}},
            "Change": {"key": "change_id", "source": {"table": "changes"}, "series": {"time": "changed_on", "of": "changeOf"},
                       "properties": {
                "change_id": {"type": "string"}, "order_id": {"type": "string"}, "note": {"type": "string"},
                "changed_on": {"type": "date", "column": "CHANGE_YMD", "format": "YYYYMMDD"}}}},
        "links": {
            "priceOf": {"from": "Price", "to": "Product", "on": {"product_id": "product_id"},
                        "cardinality": "many_to_one", "inverse": "prices"},
            "saleOf": {"from": "Sale", "to": "Product", "on": {"product_id": "product_id"},
                       "cardinality": "many_to_one", "inverse": "sales"},
            "changeOf": {"from": "Change", "to": "Order", "on": {"order_id": "order_id"}, "cardinality": "many_to_one",
                         "inverse": "changes"}},
        "actions": {"reschedule": {"target": "Order", "parameters": {"on": "date"}, "set": {"placed_on": "$on"},
                                   "approval": False}},
        "roles": {"clerk": {"read": ["*"], "execute": ["reschedule"], "request": ["reschedule"]},
                  "guest": {"read": ["Order"], "mask": {"Order.placed_on": "full"}}},
        "decisions": {"stale": {
            "target": "Order", "outputs": {"stale": "boolean"},
            "inputs": {"age": {"type": "integer", "days_since": "placed_on"},
                       "shipped": {"type": "integer", "days_since": "shipped_at"}},
            "rules": [{"id": "old", "when": {"age": "> 30"}, "then": {"stale": True}},
                      {"id": "new", "when": {"age": "<= 30"}, "then": {"stale": False}}]}},
    }


SEED = """
CREATE TABLE orders (order_id TEXT, PLACED_YMD TEXT, SHIPPED_STAMP TEXT, CLOSED_YMD TEXT, CLOSED_HMS TEXT, SLASHED TEXT,
                     status TEXT);
INSERT INTO orders VALUES ('O1', '20260110', '20260112143005', '20260120', '180000', '10/01/2026', 'open'),
                          ('O2', '20260310', '20260311080000', NULL, NULL, '10/03/2026', 'open'),
                          ('O3', '', NULL, NULL, NULL, NULL, 'open'),
                          ('O4', '00000000', 'bad', NULL, NULL, 'x', 'open');
CREATE TABLE products (product_id TEXT, name TEXT);
INSERT INTO products VALUES ('P1', 'Mug'), ('P2', 'Plate'), ('P3', 'Bowl'), ('P4', 'Fork');
CREATE TABLE prices (price_id TEXT, product_id TEXT, amount REAL, START_YMD TEXT, END_YMD TEXT);
INSERT INTO prices VALUES ('A1', 'P1', 900, '20250101', '20251231'), ('A2', 'P1', 1000, '20260101', '20261231'),
                          ('A3', 'P1', 1100, '20270101', '99991231'), ('A4', 'P2', 500, '20260101', NULL),
                          ('A5', 'P3', 700, '20270101', '20271231');
CREATE TABLE sales (sale_id TEXT, product_id TEXT, label TEXT, starts_at TEXT, ends_at TEXT);
INSERT INTO sales VALUES ('S1', 'P1', 'spring', '2026-03-15T09:00:00', '2026-03-15T10:00:00'),
                         ('S2', 'P2', 'gone', '2026-03-15T08:00:00', '2026-03-15T09:30:00');
CREATE TABLE changes (change_id TEXT, order_id TEXT, note TEXT, CHANGE_YMD TEXT);
INSERT INTO changes VALUES ('C1', 'O1', 'first', '20260105'), ('C2', 'O1', 'second', '20260107');
"""


@pytest.fixture
def onto() -> Ontology:
    o = Ontology.from_dict(_definition())
    o.clock = lambda: NOW
    return o


@pytest.fixture
def source() -> SqliteBackend:
    b = SqliteBackend()
    b.script(SEED)
    return b


@pytest.fixture
def studio(onto, source) -> Studio:
    st = Studio(onto, now=lambda: NOW)
    st.add_backend("source", source)
    return st


def test_a_layout_says_where_each_part_stands():
    assert date_format("YYYYMMDD") == {"YYYY": (0, 4), "MM": (4, 2), "DD": (6, 2)}
    assert date_format("DD/MM/YYYY") == {"DD": (0, 2), "MM": (3, 2), "YYYY": (6, 4)}
    assert date_format("YYYYMMDDHH24MISS")["SS"] == (12, 2)
    assert date_format("YYYY-MM-DD HH:MI")["MI"] == (14, 2)
    for bad, why in (("YYYYMM", "gives no DD"), ("YYYYMMDDYYYY", "twice"), ("yyyymmdd", "cannot read")):
        with pytest.raises(ExprError, match=why):
            date_format(bad)


def test_a_date_goes_back_into_its_layout():
    assert encode_text_date("2026-03-15", "YYYYMMDD") == "20260315"
    assert encode_text_date("2026-03-15T14:30:05", "YYYYMMDDHH24MISS") == "20260315143005"
    assert encode_text_date("2026-03-15", "DD/MM/YYYY HH:MI") == "15/03/2026 00:00"


def test_a_text_date_reads_as_a_date_in_every_answer(studio):
    assert studio.fetch("Order", "O1")["placed_on"] == "2026-01-10"
    assert studio.fetch("Order", "O1")["shipped_at"] == "2026-01-12T14:30:05"
    assert studio.fetch("Order", "O1")["closed_at"] == "2026-01-20T18:00:00"
    assert studio.fetch("Order", "O1")["slashed"] == "2026-01-10"
    assert studio.fetch("Order", "O1")["placed_on__text"] == "20260110"
    assert studio.fetch("Order", "O2")["closed_at"] is None


def test_blank_and_broken_text_reads_as_no_date(studio):
    for key in ("O3", "O4"):
        row = studio.fetch("Order", key)
        assert row["placed_on"] is None and row["age_days"] is None and row["shipped_at"] is None
    assert studio.fetch("Order", "O4")["slashed"] is None


def test_days_since_and_date_functions_work_on_them(studio):
    assert studio.decide("stale", "O1").inputs == {"age": 64, "shipped": 61}
    assert studio.decide("stale", "O1").outputs == {"stale": True}
    assert studio.decide("stale", "O2").outputs == {"stale": False}
    assert studio.decide("stale", "O3").inputs == {"age": None, "shipped": None}
    row = studio.fetch("Order", "O2")
    assert (row["age_days"], row["placed_year"], row["placed_month"], row["is_recent"]) == (5, 2026, 3, True)


def test_filters_and_ordering_take_a_date_not_the_stored_text(studio):
    q = {"match": {"o": "Order"}, "where": {"gte": ["o.placed_on", {"param": "since"}]}, "return": ["o.order_id"],
         "order": ["-o.placed_on"]}
    assert studio.run(q, {"since": "2026-01-01"}).rows == [("O2",), ("O1",)]
    q["where"] = {"lt": ["o.shipped_at", "2026-03-01T00:00:00"]}
    assert studio.run(q).rows == [("O1",)]


def test_a_string_property_can_be_read_as_a_date_by_hand(onto, source):
    d = _definition()
    d["objects"]["Order"]["properties"]["raw"] = {"type": "string", "column": "PLACED_YMD"}
    d["objects"]["Order"]["properties"]["raw_age"] = {"type": "integer",
                                                      "expr": "days_between(text_date(raw, 'YYYYMMDD'), '2026-01-20')"}
    o = Ontology.from_dict(d)
    assert o.validate() == []
    st = Studio(o)
    st.add_backend("source", source)
    assert st.fetch("Order", "O1")["raw_age"] == 10


def test_the_definition_says_format_once_and_round_trips(onto):
    d = onto.to_dict()
    p = d["objects"]["Order"]["properties"]
    assert p["placed_on"] == {"type": "date", "column": "PLACED_YMD", "format": "YYYYMMDD", "label": "Placed on"}
    assert "placed_on__text" not in p and "amount__current" not in d["objects"]["Price"]["properties"]
    assert d["objects"]["Change"]["series"] == {"time": "changed_on", "of": "changeOf"}
    assert d["objects"]["Sale"]["period"]["end_exclusive"] is True
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.to_dict() == d


def test_validate_holds_format_to_a_date_property():
    d = _definition()
    props = d["objects"]["Order"]["properties"]
    props["a"] = {"type": "string", "format": "YYYYMMDD"}
    props["b"] = {"type": "date", "format": "YYYYMM"}
    props["c"] = {"type": "date", "format": "YYYYMMDDHHMI"}
    props["d"] = {"type": "date", "format": "YYYYMMDD", "expr": "today()"}
    d["objects"]["Change"]["properties"]["changed_on"]["format"] = "DD/MM/YYYY"
    d["actions"]["bad"] = {"target": "Order", "set": {"closed_at": "2026-01-01T00:00:00"}}
    issues = Ontology.from_dict(d).validate()
    assert "Order.a: format reads text as a date; declare it date or datetime, not string" in issues
    assert "Order.b: date format 'YYYYMM' gives no DD" in issues
    assert "Order.c: format YYYYMMDDHHMI carries a time; declare it datetime" in issues
    assert "Order.d: format reads a stored column and takes no expr" in issues
    assert any("does not sort by time" in i for i in issues)
    assert "action bad: 'closed_at' is read from several columns and cannot be set" in issues


def test_an_action_writes_the_date_back_in_its_layout(studio, source):
    op = Actor("op", "human", ["clerk"])
    p = studio.actions.request("reschedule", "O1", {"on": "2026-04-01"}, actor=op)
    assert p.status == "executed", p.checks
    assert source.fetch("SELECT PLACED_YMD FROM orders WHERE order_id = 'O1'")[0][0] == "20260401"
    assert studio.fetch("Order", "O1")["placed_on"] == "2026-04-01"
    studio.actions.rollback(p.id, actor=op)
    assert source.fetch("SELECT PLACED_YMD FROM orders WHERE order_id = 'O1'")[0][0] == "20260110"


def test_a_masked_date_masks_its_stored_text(onto):
    assert mask_style(onto, onto.roles["guest"], "Order", "placed_on__text") == "full"
    assert mask_style(onto, onto.roles["guest"], "Order", "age_days") == "full"
    d = _definition()
    d["objects"]["Order"]["properties"]["placed_on"]["mask"] = "partial"
    assert Ontology.from_dict(d).obj("Order").prop("placed_on__text").mask == "partial"


def test_a_binding_module_can_say_a_column_holds_text():
    std = Module.from_dict({"module": "std", "namespace": "https://example.com/o#", "objects": {"Doc": {
        "key": "doc_id", "properties": {"doc_id": {"type": "string"}, "issued_on": {"type": "date"},
                                        "signed_on": {"type": "string"}}}}})
    binding = Module.from_dict({"module": "bind", "kind": "binding", "requires": ["std"], "extend": {"objects": {"Doc": {
        "table": "DOCS", "columns": {"issued_on": "ISSUE_YMD"},
        "properties": {"issued_on": {"format": "YYYYMMDD"},
                       "signed_on": {"type": "date", "format": "YYYYMMDD"}}}}}})
    comp = compose([std, binding])
    assert comp.issues == []
    p = comp.ontology.obj("Doc").prop("issued_on__text")
    assert p.column == "ISSUE_YMD" and comp.ontology.obj("Doc").prop("issued_on").type == "date"
    assert comp.ontology.obj("Doc").prop("signed_on").type == "date"
    wrong = Module.from_dict({"module": "bad", "kind": "binding", "requires": ["std"], "extend": {"objects": {"Doc": {
        "properties": {"signed_on": {"type": "integer"}}}}}})
    with pytest.raises(ModuleError, match="changes the type"):
        compose([std, wrong])


def test_the_row_valid_now_answers_as_a_computed_property(studio):
    rows = studio.run({"match": {"p": "Product"}, "return": ["p.product_id", "p.price_now", "p.price_or_zero"],
                       "order": ["product_id"]}).rows
    assert rows == [("P1", 1000.0, 1000.0), ("P2", 500.0, 500.0), ("P3", None, 0), ("P4", None, 0)]
    assert studio.fetch("Product", "P2")["price_now"] == 500  # an empty end stays open


def test_the_clock_moves_the_answer(studio):
    q = {"match": {"p": "Product"}, "where": {"eq": ["p.product_id", "P1"]}, "return": ["p.price_now"]}
    assert studio.run(q).rows == [(1000.0,)]
    studio.onto.clock = lambda: datetime(2025, 6, 1)
    assert studio.run(q).rows == [(900.0,)]
    studio.onto.clock = lambda: datetime(2027, 6, 1)
    assert studio.run(q).rows == [(1100.0,)]
    studio.onto.clock = lambda: datetime(2026, 12, 31)  # the last day of a closed period still counts
    assert studio.run(q).rows == [(1000.0,)]


def test_a_period_in_datetimes_reads_the_time_and_an_end_can_be_exclusive(studio):
    assert studio.fetch("Product", "P1")["sale_now"] == "spring"
    assert studio.fetch("Product", "P2")["sale_now"] is None  # it ended at 09:30, and the end is exclusive


def test_decisions_read_the_current_value(onto, source):
    d = _definition()
    d["decisions"]["cheap"] = {"target": "Product", "outputs": {"cheap": "boolean"},
                               "inputs": {"price": {"type": "decimal", "property": "price_now"}},
                               "rules": [{"id": "y", "when": {"price": "< 600"}, "then": {"cheap": True}},
                                         {"id": "n", "when": {"price": ">= 600"}, "then": {"cheap": False}}]}
    o = Ontology.from_dict(d)
    o.clock = lambda: NOW
    st = Studio(o)
    st.add_backend("source", source)
    assert st.decide("cheap", "P2").outputs == {"cheap": True} and st.decide("cheap", "P1").outputs == {"cheap": False}


def test_the_graph_answers_the_same(studio):
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    studio.add_backend("graph", RdflibBackend())
    studio.project()
    queries = {
        "dates": {"match": {"o": "Order"}, "return": ["o.order_id", "o.placed_on", "o.shipped_at", "o.age_days",
                                                      "o.placed_year"], "order": ["order_id"]},
        "since": {"match": {"o": "Order"}, "where": {"gte": ["o.placed_on", "2026-03-01"]}, "return": ["o.order_id"]},
        "prices": {"match": {"p": "Product"}, "return": ["p.product_id", "p.price_now", "p.sale_now"],
                   "order": ["product_id"]},
    }
    rep = studio.conformance(queries={k: (studio.query(v), {}) for k, v in queries.items()})
    assert rep.passed, rep.summary()


def test_a_series_on_a_text_date_keeps_working_in_every_language(onto, source):
    d = _definition()
    d["objects"]["Order"]["properties"]["last_note"] = {"type": "string", "expr": "latest(changes.note)"}
    o = Ontology.from_dict(d)
    assert o.validate() == []
    st = Studio(o)
    st.add_backend("source", source)
    q = {"match": {"o": "Order"}, "where": {"eq": ["o.order_id", "O1"]}, "return": ["o.last_note"]}
    assert st.run(q).rows == [("second",)]
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    st.add_backend("graph", RdflibBackend())
    st.project()
    assert st.run(q, backend="graph").rows == [("second",)]


def test_each_language_writes_the_decoding(onto):
    q = {"match": {"o": "Order"}, "return": ["o.placed_on"]}
    sql = compiler_for(onto, "sql").compile(q).text
    assert "SUBSTR(CAST(t_o.\"PLACED_YMD\" AS VARCHAR), 1, 4)" in sql and "BETWEEN '01' AND '12'" in sql
    assert "STRDT(CONCAT(" in compiler_for(onto, "sparql").compile(q).text
    assert "substring(toString(o.`placed_on__text`), 0, 4)" in compiler_for(onto, "cypher").compile(q).text
    with pytest.raises(CompileError, match="GQL"):
        compiler_for(onto, "gql").compile(q)
    current = {"match": {"p": "Product"}, "return": ["p.price_now"]}
    assert "MAX((CASE WHEN" in compiler_for(onto, "sql").compile(current).text
    assert "2026-03-15" in compiler_for(onto, "cypher").compile(current).text


def test_today_is_read_when_the_query_is_compiled(onto):
    assert "'2026-03-15'" in compiler_for(onto, "sql").compile({"match": {"o": "Order"}, "return": ["o.age_days"]}).text
    assert check_computed(onto, "Order", "age_days").type == "integer"


def test_expressions_are_checked():
    with pytest.raises(ExprError, match="takes the layout as text"):
        parse_expr("text_date(x, y)")
    with pytest.raises(ExprError, match="gives no DD"):
        parse_expr("text_date(x, 'YYYYMM')")
    with pytest.raises(ExprError, match=r"today\(\) takes 0"):
        parse_expr("today(1)")
    d = _definition()
    props = d["objects"]["Product"]["properties"]
    props["no_period"] = {"type": "integer", "expr": "current(prices.nope)"}
    props["number"] = {"type": "date", "expr": "text_date(1, 'YYYYMMDD')"}
    d["objects"]["Order"]["properties"]["no_series"] = {"type": "string", "expr": "current(changes.note)"}
    issues = Ontology.from_dict(d).validate()
    assert "Product.no_period: Price has no property 'nope'" in issues
    assert "Product.number: text_date() takes text, not integer" in issues
    assert "Order.no_series: current() needs Change to give its period (period: {start: ..., end: ...})" in issues


def test_validate_holds_period_to_dates():
    d = _definition()
    d["objects"]["Price"]["period"] = {"end": "amount", "of": "saleOf", "until": "x"}
    issues = Ontology.from_dict(d).validate()
    assert "Price: period: unknown key 'until'" in issues
    assert "Price: period: needs start: a date or datetime property" in issues
    assert "Price: period: end 'amount' is decimal, not a date or datetime" in issues
    assert "Price: period: of 'saleOf' is not a link from Price" in issues
    d["objects"]["Price"]["period"] = {"start": "nothing"}
    assert "Price: period: start 'nothing' is not a property" in Ontology.from_dict(d).validate()


def test_a_masked_price_masks_the_current_price(onto):
    assert dependencies(onto, "Product", "price_now") == {("Price", "amount"), ("Price", "valid_from__text"),
                                                          ("Price", "valid_to__text")}


def test_overlapping_periods_are_listed_for_a_person(studio, source):
    assert overlapping_periods(studio) == []
    source.script("INSERT INTO prices VALUES ('A6', 'P1', 1200, '20260601', '20260630'),"
                  " ('A7', 'P2', 400, '20260301', NULL);")
    found = overlapping_periods(studio)
    assert found == [{"type": "Price", "of": "P1", "rows": ["A2", "A6"], "from": "2026-06-01", "until": "2026-12-31"},
                     {"type": "Price", "of": "P2", "rows": ["A4", "A7"], "from": "2026-03-01", "until": None}]
    assert studio.fetch("Product", "P2")["price_now"] == 500  # the highest, until a person settles it


def test_periods_on_the_command_line(tmp_path, capsys):
    yaml = pytest.importorskip("yaml")
    db = tmp_path / "shop.sqlite"
    import sqlite3

    conn = sqlite3.connect(db)
    conn.executescript(SEED + "INSERT INTO prices VALUES ('A6', 'P1', 1200, '20260601', '20260630');")
    conn.close()
    (tmp_path / "ontology.json").write_text(json.dumps(_definition()), encoding="utf-8")
    (tmp_path / "studio.yaml").write_text(yaml.safe_dump({
        "ontology": "ontology.json", "backends": {"source": {"kind": "sqlite", "path": "shop.sqlite", "source": True}}}),
        encoding="utf-8")
    assert main(["periods", str(tmp_path / "studio.yaml")]) == 1
    assert json.loads(capsys.readouterr().out)[0]["rows"] == ["A2", "A6"]
