"""The metric dictionary: a number answered with its formula, denominator, time basis and owner."""
import json

import pytest

from ontlas import Ontology
from ontlas.backends.sql import SqliteBackend
from ontlas.cli import main
from ontlas.decide.metrics import MetricError, answer_metric, dictionary, formula_text, metric_queries
from ontlas.modules import Module, ModuleError, compose, settle
from ontlas.roles import AccessDenied
from ontlas.studio import Studio


def _definition() -> dict:
    return {
        "ontology": "shop", "namespace": "https://example.com/s#",
        "objects": {
            "Line": {"key": "line_id", "source": {"table": "lines"}, "properties": {
                "line_id": {"type": "string"}, "seller_id": {"type": "string"}, "status": {"type": "string"},
                "channel": {"type": "string"}, "amount": {"type": "decimal", "mask": "full"},
                "fee": {"type": "decimal"},
                "delivered_on": {"type": "date", "column": "DELIVER_YMD", "format": "YYYYMMDD"}}},
            "Visit": {"key": "visit_id", "source": {"table": "visits"}, "properties": {
                "visit_id": {"type": "string"}, "seen_on": {"type": "date"}}}},
        "metrics": {
            "late_rate": {
                "label": "Late rate", "description": "Share of delivered lines that came late", "owner": "Merchandising",
                "unit": "%", "scale": 100, "cite": "Metric sheet 3",
                "formula": {"match": {"l": "Line"}, "where": {"eq": ["l.status", "LATE"]}, "value": {"count": "l"}},
                "denominator": {"where": {"in": ["l.status", ["ON_TIME", "LATE"]]}, "value": {"count": "l"},
                                "label": "delivered lines"},
                "time": {"property": "l.delivered_on", "basis": "the day the line was delivered"}},
            "fees": {
                "label": "Fees", "owner": "Finance", "unit": "KRW",
                "formula": {"match": {"l": "Line"}, "value": {"sum": "l.fee"}},
                "time": {"property": "l.delivered_on", "basis": "the day the line was delivered"}},
            "lines_per_visit": {
                "label": "Lines per visit", "owner": "Growth",
                "formula": {"match": {"l": "Line"}, "value": {"count": "l"}},
                "denominator": {"match": {"v": "Visit"}, "value": {"count": "v"}, "time": "v.seen_on", "label": "visits"},
                "time": {"property": "l.delivered_on", "basis": "line delivered, visit seen"}},
            "by_channel": {
                "label": "Lines of a channel", "owner": "Growth", "params": {"channel": "string"},
                "formula": {"match": {"l": "Line"}, "where": {"eq": ["l.channel", {"param": "channel"}]},
                            "value": {"count": "l"}},
                "time": {"basis": "all lines on file"}},
            "secret": {
                "label": "Sales", "owner": "Finance", "formula": {"match": {"l": "Line"}, "value": {"sum": "l.amount"}},
                "time": {"basis": "all lines on file"}}},
        "roles": {
            "seller": {"read": ["Line"], "run": ["late_rate", "secret"],
                       "scope": {"attribute": "seller_id", "types": {"Line": "seller_id"}}},
            "analyst": {"read": ["*"], "run": ["*"], "unmask": ["Line.amount"]},
            "guest": {"read": ["Visit"], "run": ["late_rate"]}},
    }


SEED = """
CREATE TABLE lines (line_id TEXT, seller_id TEXT, status TEXT, channel TEXT, amount REAL, fee REAL, DELIVER_YMD TEXT);
INSERT INTO lines VALUES ('L1', 'S1', 'ON_TIME', 'web', 100, 10, '20260105'),
                         ('L2', 'S1', 'LATE', 'web', 100, 10, '20260110'),
                         ('L3', 'S2', 'ON_TIME', 'app', 100, 10, '20260120'),
                         ('L4', 'S2', 'ON_TIME', 'app', 100, 10, '20260210'),
                         ('L5', 'S2', 'CANCELLED', 'app', 100, 10, NULL);
CREATE TABLE visits (visit_id TEXT, seen_on TEXT);
INSERT INTO visits VALUES ('V1', '2026-01-02'), ('V2', '2026-01-03'), ('V3', '2026-02-01'), ('V4', '2026-02-02');
"""


def _studio(d=None) -> Studio:
    b = SqliteBackend()
    b.script(SEED)
    st = Studio(Ontology.from_dict(d or _definition()).check())
    st.add_backend("source", b)
    return st


@pytest.fixture
def studio() -> Studio:
    return _studio()


def test_the_number_comes_back_with_what_it_means(studio):
    a = answer_metric(studio, "late_rate", since="2026-01-01", until="2026-02-01")
    assert a.value == pytest.approx(100 / 3)
    assert (a.numerator, a.denominator) == (1, 3)
    assert (a.label, a.owner, a.unit, a.cite) == ("Late rate", "Merchandising", "%", "Metric sheet 3")
    assert a.description == "Share of delivered lines that came late"
    assert a.formula == "count(l) / count(l) x 100" and a.denominator_label == "delivered lines"
    assert a.time_basis == "the day the line was delivered"
    assert a.period == {"from": "2026-01-01", "to": "2026-02-01"}
    assert a.backend == "source" and a.notes == []
    assert "LATE" in a.queries["formula"] and "2026-02-01" in a.queries["denominator"]
    assert json.loads(json.dumps(a.to_dict()))["owner"] == "Merchandising"


def test_a_window_counts_from_inclusive_to_exclusive(studio):
    assert answer_metric(studio, "fees", since="2026-01-05", until="2026-01-20").value == 20
    assert answer_metric(studio, "fees", since="2026-01-20").value == 20
    assert answer_metric(studio, "fees", until="2026-01-06").value == 10


def test_no_window_says_so(studio):
    a = answer_metric(studio, "fees")
    assert a.value == 50 and a.notes == ["no window was given, so this counts all time"] and a.period == {}


def test_a_metric_without_a_denominator_is_a_plain_total(studio):
    a = answer_metric(studio, "fees", since="2026-01-01", until="2026-02-01")
    assert a.value == 30 and a.denominator is None and a.formula == "sum(l.fee)" and set(a.queries) == {"formula"}


def test_the_denominator_can_be_another_table_with_its_own_time(studio):
    a = answer_metric(studio, "lines_per_visit", since="2026-01-01", until="2026-02-01")
    assert (a.numerator, a.denominator, a.value) == (3, 2, 1.5)
    assert "seen_on" in a.queries["denominator"]


def test_a_zero_denominator_gives_no_value_and_says_why(studio):
    a = answer_metric(studio, "late_rate", since="2030-01-01")
    assert a.value is None and a.numerator == 0 and a.denominator == 0
    assert a.notes == ["the denominator is 0 or empty, so there is no value"]


def test_declared_parameters_are_asked_for(studio):
    assert answer_metric(studio, "by_channel", {"channel": "app"}).value == 3
    with pytest.raises(ValueError, match="missing parameters"):
        answer_metric(studio, "by_channel")


def test_a_metric_without_a_time_property_takes_no_window(studio):
    with pytest.raises(MetricError, match="takes no window"):
        answer_metric(studio, "by_channel", {"channel": "app"}, since="2026-01-01")
    assert answer_metric(studio, "by_channel", {"channel": "app"}).notes == []


def test_a_scoped_role_gets_the_number_of_its_own_rows(studio):
    a = answer_metric(studio, "late_rate", role="seller", principal={"seller_id": "S1"})
    assert (a.numerator, a.denominator, a.value) == (1, 2, 50)
    assert answer_metric(studio, "late_rate", role="seller", principal={"seller_id": "S2"}).value == 0
    assert "S1" in answer_metric(studio, "late_rate", role="seller", principal={"seller_id": "S1"}).queries["formula"]


def test_a_role_needs_the_right_to_run_it_and_to_read_it(studio):
    with pytest.raises(AccessDenied, match="may not run metric 'fees'"):
        answer_metric(studio, "fees", role="seller", principal={"seller_id": "S1"})
    with pytest.raises(AccessDenied, match="may not read Line"):
        answer_metric(studio, "late_rate", role="guest")
    with pytest.raises(AccessDenied, match="masked"):
        answer_metric(studio, "secret", role="seller", principal={"seller_id": "S1"})
    assert answer_metric(studio, "secret", role="analyst").value == 500
    with pytest.raises(KeyError):
        answer_metric(studio, "nothing")


def test_the_graph_gives_the_same_number(studio):
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    studio.add_backend("graph", RdflibBackend())
    studio.project()
    for name, kw in (("late_rate", {"since": "2026-01-01", "until": "2026-02-01"}), ("fees", {})):
        a = answer_metric(studio, name, **kw)
        b = answer_metric(studio, name, backend="graph", **kw)
        assert a.value == pytest.approx(b.value) and b.backend == "graph"


def test_a_metric_compiles_to_every_query_language(studio):
    q = metric_queries(studio.onto.metrics["late_rate"], since=True)
    assert set(q) == {"formula", "denominator"}
    for language in ("sql", "sparql", "cypher"):
        compiled = studio.translate(q["formula"], language)
        assert "count" in compiled.text.lower() and "from" in compiled.params


def test_the_dictionary_reads_without_running(studio):
    rows = {r["metric"]: r for r in dictionary(studio.onto)}
    assert rows["late_rate"]["owner"] == "Merchandising" and rows["late_rate"]["denominator"] == "delivered lines"
    assert rows["late_rate"]["time_basis"] == "the day the line was delivered"
    assert formula_text(studio.onto.metrics["fees"]) == "sum(l.fee)"


def test_validate_holds_a_metric_to_its_meaning():
    d = _definition()
    d["metrics"] = {
        "a": {"formula": {"match": {"l": "Line"}, "value": {"count": "l"}}},
        "b": {"owner": "x", "time": {"basis": "y"}},
        "c": {"owner": "x", "time": {"basis": "y"}, "formula": {"match": {"l": "Line"}, "value": {"median": "l.fee"}}},
        "d": {"owner": "x", "time": {"basis": "y", "property": "l.status"},
              "formula": {"match": {"l": "Line"}, "value": {"count": "l"}}},
        "e": {"owner": "x", "time": {"basis": "y"}, "formula": {"match": {"l": "Nope"}, "value": {"count": "l"}}},
        "f": {"owner": "x", "time": {"basis": "y"}, "formula": {"match": {"l": "Line"}, "value": {"sum": "l.nope"}}},
        "g": {"owner": "x", "time": {"basis": "y"}, "formula": {
            "match": {"l": "Line"}, "where": {"eq": ["l.status", {"param": "s"}]}, "value": {"count": "l"}}},
        "h": {"owner": "x", "time": {"basis": "y"}, "formula": {"value": {"count": "l"}}},
    }
    issues = Ontology.from_dict(d).validate()
    assert "metric a: needs an owner: who answers for what it means" in issues
    assert "metric a: needs time: {basis, property}: what time the number counts by, in words" in issues
    assert "metric b: needs a formula" in issues
    assert any(i.startswith("metric c: formula: value takes one of count") for i in issues)
    assert "metric d: formula: time property is string, not a date or datetime" in issues
    assert any(i.startswith("metric e: formula: alias 'l': unknown object type 'Nope'") for i in issues)
    assert any(i.startswith("metric f: formula: Line ('l') has no property 'nope'") for i in issues)
    assert "metric g: formula: parameter 's' is not declared" in issues
    assert any(i.startswith("metric h: cannot read it as a query") for i in issues)


def test_the_definition_round_trips():
    onto = Ontology.from_dict(_definition())
    d = onto.to_dict()
    assert d["metrics"]["late_rate"]["scale"] == 100 and "scale" not in d["metrics"]["fees"]
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.metrics == onto.metrics


def _module(extra=None) -> Module:
    d = _definition()
    d["module"] = "shop"
    del d["ontology"], d["roles"]
    return Module.from_dict({**d, **(extra or {})})


def test_a_metric_is_module_content_a_customer_can_redefine():
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["shop"], "version": "2.1.0",
                                "extend": {"metrics": {"late_rate": {
                                    "owner": "Acme quality",
                                    "denominator": {"where": {"eq": ["l.status", "ON_TIME"]}, "value": {"count": "l"},
                                                    "label": "lines on time"}}}}})
    base = _module()
    comp = compose([base, overlay])
    assert comp.issues == [] and comp.owner("metric:late_rate") == "shop"
    assert comp.touched["metric:late_rate"] == ["acme"]
    assert "metric:late_rate" in base.elements() and base.counts()["metrics"] == 5
    b = SqliteBackend()
    b.script(SEED)
    st = Studio.from_modules([base, overlay])
    st.add_backend("source", b)
    a = answer_metric(st, "late_rate")
    assert a.owner == "Acme quality" and a.denominator_label == "lines on time" and a.denominator == 3
    assert a.version == base.version
    stray = Module.from_dict({"module": "x", "requires": ["shop"], "extend": {"metrics": {"nope": {"owner": "a"}}}})
    with pytest.raises(ModuleError, match="no attached module defines"):
        compose([base, stray])


def test_unplugging_what_a_metric_reads_takes_the_metric_with_it():
    base = _module()
    gone = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["shop"],
                             "remove": {"properties": {"Line": ["fee"]}}})
    assert any(i.startswith("metric fees:") for i in compose([base, gone]).issues)
    assert "metric:fees" in settle(gone, [base]) and compose([base, gone]).issues == []


def test_the_command_line(tmp_path, capsys):
    yaml = pytest.importorskip("yaml")
    import sqlite3

    conn = sqlite3.connect(tmp_path / "shop.sqlite")
    conn.executescript(SEED)
    conn.close()
    (tmp_path / "ontology.json").write_text(json.dumps(_definition()), encoding="utf-8")
    (tmp_path / "studio.yaml").write_text(yaml.safe_dump({
        "ontology": "ontology.json", "backends": {"source": {"kind": "sqlite", "path": "shop.sqlite", "source": True}}}),
        encoding="utf-8")
    assert main(["metric", str(tmp_path / "studio.yaml"), "late_rate", "--from", "2026-01-01", "--to", "2026-02-01"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["numerator"] == 1 and out["owner"] == "Merchandising" and out["period"]["to"] == "2026-02-01"
    assert main(["metric", str(tmp_path / "studio.yaml"), "late_rate", "--role", "seller", "--principal",
                 "seller_id=S1"]) == 0
    assert json.loads(capsys.readouterr().out)["value"] == 50
    assert main(["metric", str(tmp_path / "studio.yaml")]) == 0
    assert [r["metric"] for r in json.loads(capsys.readouterr().out)][0] == "late_rate"
