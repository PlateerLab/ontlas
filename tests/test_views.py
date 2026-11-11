"""Objects defined by a query: one ledger table read as the kinds of rows it holds."""
import json

import pytest

from ontlas import Ontology
from ontlas.actions import Actor
from ontlas.backends.sql import SqliteBackend
from ontlas.cli import main
from ontlas.decide.views import behind, create_views, in_order, through_view, view_statements
from ontlas.modules import Module, compose
from ontlas.studio import Studio

CLERK = Actor("clerk", "human", ["clerk"])


def _definition() -> dict:
    return {
        "ontology": "accounts", "namespace": "https://example.com/l#",
        "objects": {
            "LedgerEntry": {"key": "entry_id", "source": {"table": "account_ledger"}, "properties": {
                "entry_id": {"type": "string", "column": "ENTRY_ID"}, "account_no": {"type": "string", "column": "ACCOUNT_NO"},
                "kind": {"type": "string", "column": "ENTRY_KIND"}, "batch_no": {"type": "string", "column": "BATCH_NO"},
                "seller_id": {"type": "string", "column": "SELLER_ID"}, "units": {"type": "integer", "column": "UNITS"},
                "amount": {"type": "decimal", "column": "AMOUNT"}, "state": {"type": "string", "column": "STATE"},
                "posted_on": {"type": "date", "column": "POST_YMD", "format": "YYYYMMDD"}}},
            "SaleEntry": {
                "key": "entry_id", "view": {"name": "sale_entries", "query": {
                    "match": {"r": "LedgerEntry"}, "where": {"eq": ["r.kind", "SALE"]},
                    "return": ["r.entry_id", "r.account_no", "r.units", "r.amount", "r.seller_id"]}},
                "properties": {"entry_id": {"type": "string"}, "account_no": {"type": "string"}, "units": {"type": "integer"},
                               "amount": {"type": "decimal"}, "seller_id": {"type": "string"},
                               "worth": {"type": "decimal", "expr": "amount * units"}}},
            "RefundEntry": {
                "key": "entry_ref", "view": {"name": "refund_entries", "query": {
                    "match": {"r": "LedgerEntry"}, "where": {"in": ["r.kind", ["REFUND", "REVERSAL"]]},
                    "return": [{"col": "r.entry_id", "as": "entry_ref"}, "r.batch_no", "r.account_no",
                               {"col": "r.units", "as": "refunded"}, "r.state", "r.posted_on"]}},
                "states": {"property": "state", "states": ["OPEN", "DONE"],
                           "transitions": [{"from": "OPEN", "to": "DONE", "action": "finish"}]},
                "properties": {"entry_ref": {"type": "string"}, "batch_no": {"type": "string"},
                               "account_no": {"type": "string"}, "refunded": {"type": "integer"},
                               "state": {"type": "string"}, "posted_on": {"type": "date"}}},
            "Batch": {
                "key": "batch_no", "view": {"query": {
                    "match": {"r": "RefundEntry"}, "return": ["r.batch_no", {"sum": "r.refunded", "as": "total"},
                                                             {"count": "r", "as": "lines"}]}},
                "properties": {"batch_no": {"type": "string"}, "total": {"type": "integer"}, "lines": {"type": "integer"}}}},
        "links": {"inBatch": {"from": "RefundEntry", "to": "Batch", "on": {"batch_no": "batch_no"},
                              "cardinality": "many_to_one", "inverse": "batchEntries"}},
        "actions": {"finish": {"target": "RefundEntry", "transition_to": "DONE"},
                    "recount": {"target": "RefundEntry", "parameters": {"units": "integer"}, "set": {"refunded": "$units"},
                               "approval": False},
                    "repost": {"target": "RefundEntry", "parameters": {"on": "date"}, "set": {"posted_on": "$on"},
                               "approval": False}},
        "decisions": {"bigBatch": {"target": "Batch", "outputs": {"big": "boolean"},
                                   "inputs": {"total": {"type": "integer", "property": "total"}},
                                   "rules": [{"id": "y", "when": {"total": ">= 3"}, "then": {"big": True}},
                                             {"id": "n", "when": {"total": "< 3"}, "then": {"big": False}}]}},
        "roles": {"clerk": {"read": ["*"], "request": ["*"], "execute": ["*"], "run": ["*"]},
                  "seller": {"read": ["SaleEntry"], "scope": {"attribute": "seller_id", "types": {"SaleEntry": "seller_id"}}}},
    }


SEED = """
CREATE TABLE account_ledger (ENTRY_ID TEXT, ACCOUNT_NO TEXT, ENTRY_KIND TEXT, BATCH_NO TEXT, SELLER_ID TEXT, UNITS INTEGER,
                           AMOUNT REAL, STATE TEXT, POST_YMD TEXT);
INSERT INTO account_ledger VALUES
 ('R1', 'A1', 'SALE', NULL, 'S1', 2, 100, 'OPEN', '20260101'),
 ('R2', 'A1', 'SALE', NULL, 'S2', 1, 50, 'OPEN', '20260101'),
 ('R3', 'A1', 'REFUND', 'C1', 'S1', 1, 100, 'OPEN', '20260105'),
 ('R4', 'A1', 'REVERSAL', 'C1', 'S1', 1, 100, 'OPEN', '20260106'),
 ('R5', 'A1', 'TRANSFER', 'C1', 'S1', 1, 100, 'OPEN', '20260107'),
 ('R6', 'A2', 'REFUND', 'C2', 'S2', 1, 40, 'OPEN', '20260108');
"""


def _source() -> SqliteBackend:
    b = SqliteBackend()
    b.script(SEED)
    return b


def _studio(d=None) -> Studio:
    st = Studio(Ontology.from_dict(d or _definition()).check())
    st.add_backend("source", _source())
    create_views(st)
    return st


@pytest.fixture
def studio() -> Studio:
    return _studio()


def _ids(res):
    return [r[0] for r in res.rows]


def test_one_table_reads_as_the_kinds_of_rows_it_holds(studio):
    q = {"match": {"l": "SaleEntry"}, "return": ["l.entry_id"], "order": ["entry_id"]}
    assert _ids(studio.run(q)) == ["R1", "R2"]
    q = {"match": {"l": "RefundEntry"}, "return": ["l.entry_ref", "l.refunded"], "order": ["entry_ref"]}
    assert studio.run(q).rows == [("R3", 1), ("R4", 1), ("R6", 1)]


def test_units_no_longer_count_refund_rows_twice(studio):
    assert studio.run({"match": {"l": "SaleEntry"}, "return": [{"sum": "l.units", "as": "q"}]}).rows == [(3,)]
    assert studio.run({"match": {"r": "LedgerEntry"}, "return": [{"sum": "r.units", "as": "q"}]}).rows == [(7,)]


def test_rows_grouped_into_one_object(studio):
    q = {"match": {"c": "Batch"}, "return": ["c.batch_no", "c.total", "c.lines"], "order": ["batch_no"]}
    assert studio.run(q).rows == [("C1", 2, 2), ("C2", 1, 1)]


def test_a_view_is_an_object_like_any_other(studio):
    q = {"match": {"l": "RefundEntry", "c": "Batch"}, "edges": [["l", "inBatch", "c"]],
         "return": ["l.entry_ref", "c.total"], "order": ["entry_ref"]}
    assert studio.run(q).rows == [("R3", 2), ("R4", 2), ("R6", 1)]
    assert studio.fetch("SaleEntry", "R1")["worth"] == 200  # a computed property over a view
    assert studio.decide("bigBatch", "C1").outputs == {"big": False}
    assert studio.fetch("RefundEntry", "R3")["posted_on"] == "2026-01-05"  # the text date reads through


def test_a_scoped_role_reads_a_view(studio):
    q = {"match": {"l": "SaleEntry"}, "return": ["l.entry_id"]}
    assert _ids(studio.run(q, role="seller", principal={"seller_id": "S2"})) == ["R2"]


def test_the_graph_answers_the_same(studio):
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    studio.add_backend("graph", RdflibBackend())
    studio.project()
    assert ("Batch", "C1") in studio.projection.nodes and ("SaleEntry", "R5") not in studio.projection.nodes
    queries = {
        "lines": {"match": {"l": "RefundEntry"}, "return": ["l.entry_ref", "l.refunded"], "order": ["entry_ref"]},
        "batches": {"match": {"l": "RefundEntry", "c": "Batch"}, "edges": [["l", "inBatch", "c"]],
                   "return": ["l.entry_ref", "c.total"], "order": ["entry_ref"]}}
    rep = studio.conformance(queries={k: (studio.query(v), {}) for k, v in queries.items()})
    assert rep.passed, rep.summary()


def test_the_bindings_check_treats_a_view_as_a_table(studio):
    rep = studio.check_bindings()
    assert rep.ok, rep.findings


def test_a_view_not_made_yet_is_named_by_the_bindings_check():
    st = Studio(Ontology.from_dict(_definition()))
    st.add_backend("source", _source())
    rep = st.check_bindings(data=False)
    assert {f.detail for f in rep.findings if f.kind == "table"} == {
        "table 'sale_entries' does not exist", "table 'refund_entries' does not exist", "table 'batch_view' does not exist"}


def test_statements_are_written_in_the_order_views_read_each_other(studio):
    assert [t.name for t in in_order(studio.onto)] == ["SaleEntry", "RefundEntry", "Batch"]
    text = view_statements(studio.onto, studio.backend())
    assert text[:3] == ['DROP VIEW IF EXISTS "batch_view"', 'DROP VIEW IF EXISTS "refund_entries"',
                        'DROP VIEW IF EXISTS "sale_entries"']
    assert text[3].startswith('CREATE VIEW "sale_entries" AS\nSELECT') and "'SALE'" in text[3]
    assert "GROUP BY" in text[5] and '"refund_entries"' in text[5]


def test_views_can_be_made_again(studio):
    create_views(studio)
    assert len(studio.run({"match": {"l": "SaleEntry"}, "return": ["l.entry_id"]}).rows) == 2


def test_a_write_goes_through_to_the_row_behind_the_view(studio):
    p = studio.actions.request("finish", "R3", actor=Actor("agent", "agent", ["clerk"]))
    assert all(c.passed for c in p.checks), p.checks
    studio.actions.approve(p.id, approver=CLERK)
    assert p.status == "executed" and studio.fetch("RefundEntry", "R3")["state"] == "DONE"
    assert studio.backend().fetch("SELECT STATE FROM account_ledger WHERE ENTRY_ID = 'R3'") == [("DONE",)]
    studio.actions.rollback(p.id, actor=CLERK)
    assert studio.backend().fetch("SELECT STATE FROM account_ledger WHERE ENTRY_ID = 'R3'") == [("OPEN",)]


def test_a_write_under_another_name_lands_on_the_right_column(studio):
    p = studio.actions.request("recount", "R3", {"units": 5}, actor=CLERK)
    assert p.status == "executed", p.checks
    assert studio.backend().fetch("SELECT UNITS FROM account_ledger WHERE ENTRY_ID = 'R3'") == [(5,)]


def test_a_text_date_behind_a_view_is_written_in_its_layout(studio):
    p = studio.actions.request("repost", "R3", {"on": "2026-02-01"}, actor=CLERK)
    assert p.status == "executed", p.checks
    assert studio.backend().fetch("SELECT POST_YMD FROM account_ledger WHERE ENTRY_ID = 'R3'") == [("20260201",)]


def test_where_a_write_lands(studio):
    onto = studio.onto
    assert behind(onto, onto.obj("RefundEntry"))[0] == "LedgerEntry" and behind(onto, onto.obj("Batch")) is None
    assert through_view(onto, "RefundEntry", {"refunded": 3}) == ("LedgerEntry", {"units": 3})
    assert through_view(onto, "LedgerEntry", {"units": 3}) == ("LedgerEntry", {"units": 3})
    with pytest.raises(ValueError, match="no single row behind"):
        through_view(onto, "Batch", {"total": 1})


def test_validate_refuses_writing_a_grouped_view():
    d = _definition()
    d["actions"]["bad"] = {"target": "Batch", "set": {"total": 1}}
    assert "action bad: Batch is a view with no single row behind each of its rows, so it cannot be written" in \
        Ontology.from_dict(d).validate()


def test_a_key_that_is_not_the_key_behind_cannot_be_written():
    d = _definition()
    q = d["objects"]["RefundEntry"]
    q["key"] = "batch_no"
    assert any("no single row behind" in i for i in Ontology.from_dict(d).validate())


def test_validate_holds_a_view_to_its_query():
    d = _definition()
    views = d["objects"]
    views["A"] = {"key": "k", "view": {"query": {"match": {"r": "Nope"}, "return": ["r.x"]}},
                  "properties": {"k": {"type": "string"}}}
    views["B"] = {"key": "k", "view": {"query": {"nothing": 1}}, "properties": {"k": {"type": "string"}}}
    views["C"] = {"key": "k", "view": {"extra": 1, "query": {"match": {"r": "LedgerEntry"}, "return": [
        {"col": "r.entry_id", "as": "k"}, {"col": "r.units", "as": "n"}]}},
        "properties": {"k": {"type": "string"}, "n": {"type": "string"}, "missing": {"type": "string"}}}
    views["D"] = {"key": "k", "source": {"table": "x"}, "view": {"query": {
        "match": {"r": "LedgerEntry"}, "where": {"eq": ["r.kind", {"param": "kind"}]}, "order": ["k"], "limit": 3,
        "return": [{"col": "r.entry_id", "as": "k"}]}}, "properties": {"k": {"type": "string"}}}
    issues = Ontology.from_dict(d).validate()
    assert any(i.startswith("A: view: alias 'r': unknown object type 'Nope'") for i in issues)
    assert any(i.startswith("B: view: cannot read its query") for i in issues)
    assert "C: view: unknown key 'extra'" in issues
    assert "C: view: n is string, the column 'n' is integer" in issues
    assert "C: view: missing: the query returns no column 'missing'" in issues
    assert "D: view: give a view or a source table, not both" in issues
    assert "D: view: a view is stored, so it takes no parameters: ['kind']" in issues
    assert "D: view: a view gives rows, not an order or a limit" in issues


def test_a_view_cannot_store_what_moves_with_the_clock():
    d = _definition()
    d["objects"]["LedgerEntry"]["properties"]["age"] = {"type": "integer", "expr": "days_between(posted_on, today())"}
    d["objects"]["LedgerEntry"]["properties"]["aged"] = {"type": "integer", "expr": "age + 1"}
    d["objects"]["SaleEntry"]["view"]["query"]["where"] = {"gt": ["r.aged", 3]}
    assert "SaleEntry: view: r.aged moves with the clock, and a view is stored" in Ontology.from_dict(d).validate()


def test_views_that_read_each_other_are_refused():
    d = _definition()
    d["objects"]["A"] = {"key": "k", "view": {"query": {"match": {"b": "B"}, "return": ["b.k"]}},
                         "properties": {"k": {"type": "string"}}}
    d["objects"]["B"] = {"key": "k", "view": {"query": {"match": {"a": "A"}, "return": ["a.k"]}},
                         "properties": {"k": {"type": "string"}}}
    assert "A: view: views read each other in a loop: A -> B -> A" in Ontology.from_dict(d).validate()


def test_the_definition_round_trips():
    onto = Ontology.from_dict(_definition())
    d = onto.to_dict()
    assert "source" not in d["objects"]["RefundEntry"] and d["objects"]["RefundEntry"]["view"]["name"] == "refund_entries"
    assert d["objects"]["LedgerEntry"]["source"] == {"table": "account_ledger"}
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.obj("Batch").table == "batch_view" and again.to_dict() == d


def test_a_module_can_define_a_view_and_a_customer_can_redraw_it():
    d = _definition()
    d["module"] = "ledger"
    del d["ontology"], d["roles"]
    query = dict(d["objects"]["RefundEntry"]["view"]["query"])
    query["where"] = {"eq": ["r.kind", "REFUND"]}
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["ledger"], "extend": {"objects": {
        "RefundEntry": {"view": {"name": "acme_returns", "query": query}}}}})
    comp = compose([Module.from_dict(d), overlay])
    assert comp.issues == [] and comp.ontology.obj("RefundEntry").table == "acme_returns"
    st = Studio.from_modules([Module.from_dict(d), overlay])
    st.add_backend("source", _source())
    create_views(st)
    assert _ids(st.run({"match": {"l": "RefundEntry"}, "return": ["l.entry_ref"], "order": ["entry_ref"]})) == ["R3", "R6"]


def test_removing_what_a_view_reads_is_named():
    d = _definition()
    d["module"] = "ledger"
    del d["ontology"], d["roles"]
    gone = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["ledger"],
                             "remove": {"properties": {"LedgerEntry": ["kind"]}}})
    assert any(i.startswith("SaleEntry: view: LedgerEntry ('r') has no property 'kind'")
               for i in compose([Module.from_dict(d), gone]).issues)


def test_a_graph_backend_makes_no_views(studio):
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    studio.add_backend("graph", RdflibBackend())
    with pytest.raises(ValueError, match="is not a SQL source"):
        create_views(studio, "graph")


def test_the_command_line(tmp_path, capsys):
    yaml = pytest.importorskip("yaml")
    import sqlite3

    conn = sqlite3.connect(tmp_path / "ledger.sqlite")
    conn.executescript(SEED)
    conn.close()
    (tmp_path / "ontology.json").write_text(json.dumps(_definition()), encoding="utf-8")
    (tmp_path / "studio.yaml").write_text(yaml.safe_dump({
        "ontology": "ontology.json", "backends": {"source": {"kind": "sqlite", "path": "ledger.sqlite", "source": True}}}),
        encoding="utf-8")
    config = str(tmp_path / "studio.yaml")
    assert main(["views", config]) == 0
    out = capsys.readouterr().out
    assert 'CREATE VIEW "batch_view" AS' in out and out.rstrip().endswith(";")
    assert main(["views", config, "--apply"]) == 0
    assert len(json.loads(capsys.readouterr().out)["ran"]) == 6
    assert main(["run", config, json.dumps({"match": {"c": "Batch"}, "return": ["c.batch_no"]})]) == 0
    assert len(json.loads(capsys.readouterr().out)["rows"]) == 2
