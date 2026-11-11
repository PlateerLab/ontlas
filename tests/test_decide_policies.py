"""Hit policy priority, and what a table says twice or leaves open."""
import json

import pytest

from ontlas import Ontology
from ontlas.cli import main
from ontlas.decide import checks
from ontlas.decide.checks import MAX_SHOWN, decision_findings, table_findings
from ontlas.decide.table import DecisionError, DecisionResult, evaluate_table
from ontlas.decide.zen import to_jdm
from ontlas.model import DecisionInput, DecisionRule, DecisionTable
from ontlas.modules import Module, compose

from .conftest import EXAMPLE

LIB = EXAMPLE.parent / "library"


def _table(policy, rules, inputs=None):
    return DecisionTable("shipping", inputs or {}, {"fee": "integer"}, rules, hit_policy=policy)


def _rule(when, fee, rid, priority=None, note=""):
    return DecisionRule(when, {"fee": fee}, rid, note, priority=priority)


def _kinds(findings):
    return sorted((f.kind, f.severity) for f in findings)


def test_the_lowest_priority_number_decides_and_what_it_overrode_shows():
    t = _table("priority", [_rule({"total": ">= 0"}, 3000, "base", 3), _rule({"total": ">= 50000"}, 0, "free", 2),
                            _rule({"member": "true"}, 1000, "member", 1, "members pay a flat fee")])
    out, matched, notes = evaluate_table(t, {"total": 60000, "member": True})
    assert out == {"fee": 1000} and matched == ["member", "free", "base"]
    assert notes == ["members pay a flat fee", "member (priority 1) overrides free (priority 2)",
                     "member (priority 1) overrides base (priority 3)"]
    assert matched.overridden[0] == {"rule": "free", "priority": 2, "by": "member", "would_give": {"fee": 0}}
    res = DecisionResult("shipping", out, matched, {}).to_dict()
    assert [x["rule"] for x in res["overridden"]] == ["free", "base"] and res["matched"][0] == "member"
    assert json.loads(json.dumps(res))["matched"] == ["member", "free", "base"]
    assert evaluate_table(t, {"total": -1, "member": False})[0] == {"fee": None}
    out, matched, _ = evaluate_table(t, {"total": 10, "member": False})
    assert out == {"fee": 3000} and matched == ["base"] and not matched.overridden


def test_a_lower_rule_giving_the_same_answer_overrides_nothing():
    t = _table("priority", [_rule({"a": "> 1"}, 5, "r1", 1), _rule({"a": "> 2"}, 5, "r2", 2)])
    _, matched, notes = evaluate_table(t, {"a": 3})
    assert matched == ["r1", "r2"] and matched.overridden == [] and notes == []


def test_an_equal_priority_tie_is_refused_at_run_time():
    t = _table("priority", [_rule({"a": "> 1"}, 1, "r1", 1), _rule({"a": "> 2"}, 2, "r2", 1)])
    with pytest.raises(DecisionError, match="priority 1 and answer differently"):
        evaluate_table(t, {"a": 3})
    assert evaluate_table(t, {"a": 2})[0] == {"fee": 1}


def _onto(decision, objects=None):
    return Ontology.from_dict({"namespace": "https://example.com/o#", "objects": objects or {},
                               "decisions": {"shipping": decision}})


def test_validate_holds_priority_tables_to_their_rules():
    base = {"outputs": {"fee": "integer"}, "inputs": {"a": {"type": "integer", "param": "a"}}}
    no_number = _onto({**base, "hit_policy": "priority", "rules": [{"id": "r1", "when": {"a": "> 1"}, "then": {"fee": 1}}]})
    assert any("needs a priority on every rule" in i for i in no_number.validate())
    stray = _onto({**base, "rules": [{"id": "r1", "when": {"a": "> 1"}, "then": {"fee": 1}, "priority": 1}]})
    assert any("read only under hit policy priority" in i for i in stray.validate())
    bad = _onto({**base, "hit_policy": "priority",
                 "rules": [{"id": "r1", "when": {"a": "> 1"}, "then": {"fee": 1}, "priority": "high"}]})
    assert any("must be a whole number" in i for i in bad.validate())
    tie = _onto({**base, "hit_policy": "priority", "rules": [
        {"id": "r1", "when": {"a": "[1..5]"}, "then": {"fee": 1}, "priority": 1},
        {"id": "r2", "when": {"a": "[4..9]"}, "then": {"fee": 2}, "priority": 1}]})
    assert any("rules r1 and r2 both match a = 4 | 5" in i and "priority 1" in i for i in tie.validate())
    assert not [f for f in tie.findings() if f.kind == "tie"]  # refused, so not repeated as a finding
    same = _onto({**base, "hit_policy": "priority", "rules": [
        {"id": "r1", "when": {"a": "[1..5]"}, "then": {"fee": 1}, "priority": 1},
        {"id": "r2", "when": {"a": "[4..9]"}, "then": {"fee": 1}, "priority": 1}]})
    assert same.validate() == []
    unknown = _onto({**base, "hit_policy": "best", "rules": []})
    assert any("is not first/collect/unique/priority" in i for i in unknown.validate())


def test_a_priority_of_zero_survives_the_round_trip():
    d = {"outputs": {"fee": "integer"}, "inputs": {"a": {"type": "integer", "param": "a"}}, "hit_policy": "priority",
         "rules": [{"id": "r1", "when": {"a": "> 1"}, "then": {"fee": 1}, "priority": 0}]}
    again = Ontology.from_dict(_onto(d).to_dict())
    assert again.decisions["shipping"].rules[0].priority == 0 and again.validate() == []


def test_zen_export_lists_rules_in_priority_order():
    t = _table("priority", [_rule({"a": "> 1"}, 1, "low", 5), _rule({"a": "> 2"}, 2, "high", 1)])
    content = to_jdm(t)["nodes"][1]["content"]
    assert content["hitPolicy"] == "first" and [r["_id"] for r in content["rules"]] == ["high", "low"]


def test_zen_gives_the_priority_answer():
    pytest.importorskip("zen")
    from ontlas.decide.zen import evaluate_zen

    t = _table("priority", [_rule({"a": "> 1"}, 1, "low", 5), _rule({"a": "> 2"}, 2, "high", 1)])
    t.inputs = {"a": DecisionInput("a", "integer", {"param": "a"})}
    for a in (2, 3):
        assert evaluate_zen(t, {"a": a}) == evaluate_table(t, {"a": a})[0]


def test_numeric_gaps_are_cut_at_the_bounds():
    t = _table("first", [_rule({"days": "<= 7"}, 1, "soon"), _rule({"days": "> 14"}, 2, "late")],
               {"days": DecisionInput("days", "integer", {"param": "days"})})
    gaps = [f for f in table_findings(t) if f.kind == "gap"]
    assert [g.where for g in gaps] == [{"days": "8..13 | 14"}]
    assert "no rule answers days = 8..13 | 14" in gaps[0].detail
    whole = _table("first", [_rule({"days": "< 3"}, 1, "a"), _rule({"days": ">= 3"}, 2, "b")],
                   {"days": DecisionInput("days", "integer", {"param": "days"})})
    assert table_findings(whole) == []


def test_whole_numbers_leave_no_gap_between_neighbours_but_decimals_do():
    rules = [_rule({"n": "[1..3]"}, 1, "a"), _rule({"n": "[4..6]"}, 2, "b"), _rule({"n": "< 1"}, 3, "c"),
             _rule({"n": "> 6"}, 4, "d")]
    whole = _table("first", rules, {"n": DecisionInput("n", "integer", {"param": "n"})})
    assert table_findings(whole) == []
    real = _table("first", rules, {"n": DecisionInput("n", "decimal", {"param": "n"})})
    assert [f.where for f in table_findings(real)] == [{"n": "(3..4)"}]


def test_a_number_of_days_or_a_count_starts_at_zero():
    days = _table("first", [_rule({"d": "[0..7]"}, 1, "a"), _rule({"d": "> 7"}, 2, "b")],
                  {"d": DecisionInput("d", "integer", {"days_since": "at"})})
    assert table_findings(days) == []
    count = _table("first", [_rule({"d": "> 2"}, 1, "a")], {"d": DecisionInput("d", "integer", {"count": ["x"]})})
    assert [f.where for f in table_findings(count)] == [{"d": "0 | 1 | 2"}]


def test_text_inputs_are_open_unless_the_property_lists_its_values():
    objects = {"Ticket": {"key": "ticket_id", "source": {"table": "tickets"}, "properties": {
        "ticket_id": {"type": "string"}, "reason": {"type": "enum", "values": ["damaged", "wrong_item", "changed_mind"]},
        "note": {"type": "string"}}}}
    decision = {"target": "Ticket", "outputs": {"fee": "integer"}, "rules": [
        {"id": "a", "when": {"reason": '"damaged"'}, "then": {"fee": 0}},
        {"id": "b", "when": {"reason": '"wrong_item"'}, "then": {"fee": 0}}]}
    closed = _onto({**decision, "inputs": {"reason": {"type": "string", "property": "reason"}}}, objects)
    assert [f.where for f in closed.findings()] == [{"reason": '"changed_mind"'}]
    opened = _onto({**decision, "inputs": {"reason": {"type": "string", "property": "note"}}}, objects)
    assert [f.where for f in opened.findings()] == [{"reason": "any other value"}]
    assert table_findings(opened.decisions["shipping"]) == table_findings(closed.decisions["shipping"])


def test_gaps_across_two_inputs_name_the_combination():
    t = _table("first", [_rule({"member": "true", "total": ">= 100"}, 0, "free"), _rule({"member": "false"}, 5, "paid")],
               {"member": DecisionInput("member", "boolean", {"param": "m"}),
                "total": DecisionInput("total", "integer", {"param": "t"})})
    assert [f.where for f in table_findings(t) if f.kind == "gap"] == [{"member": "true", "total": "< 100"}]


def test_a_catch_all_closes_every_gap():
    t = _table("first", [_rule({"a": "> 1", "b": '"x"'}, 1, "r1"), _rule({}, 2, "rest")])
    assert _kinds(table_findings(t)) == [("overlap", "info")]


def test_a_missing_value_counts_only_where_a_cell_speaks_of_null():
    quiet = _table("first", [_rule({"a": "> 1"}, 1, "r1"), _rule({"a": "<= 1"}, 2, "r2")])
    assert table_findings(quiet) == []
    spoken = _table("first", [_rule({"a": "not null"}, 1, "r1")])
    assert [f.where for f in table_findings(spoken)] == [{"a": "null"}]


def test_overlaps_read_by_hit_policy():
    rules = [_rule({"a": "[1..5]"}, 1, "r1"), _rule({"a": "[4..9]"}, 2, "r2"), _rule({"a": "> 9"}, 3, "r3"),
             _rule({"a": "< 1"}, 3, "r4")]
    first = table_findings(_table("first", rules))
    assert _kinds(first) == [("overlap", "info")] and "r1 is listed first" in first[0].detail
    assert first[0].rules == ["r1", "r2"] and first[0].where == {"a": "4 | (4..5) | 5"}
    assert _kinds(table_findings(_table("unique", rules))) == [("overlap", "warning")]
    assert table_findings(_table("collect", rules)) == []
    ranked = [_rule({"a": "[1..5]"}, 1, "r1", 2), _rule({"a": "[4..9]"}, 2, "r2", 1), _rule({"a": "> 9"}, 3, "r3", 3),
              _rule({"a": "< 1"}, 3, "r4", 3)]
    found = table_findings(_table("priority", ranked))
    assert _kinds(found) == [("overlap", "info")] and "r2 (priority 1) overrides r1 (priority 2)" in found[0].detail


def test_rules_with_one_answer_do_not_overlap_except_under_unique():
    rules = [_rule({"a": "> 1"}, 1, "r1"), _rule({"a": "> 2"}, 1, "r2"), _rule({"a": "<= 1"}, 1, "r3")]
    assert not [f for f in table_findings(_table("first", rules)) if f.kind == "overlap"]
    assert [f.rules for f in table_findings(_table("unique", rules))] == [["r1", "r2"]]


def test_a_rule_the_ones_above_answer_for_can_never_win():
    t = _table("first", [_rule({"a": "<= 5"}, 1, "low"), _rule({"a": "> 5"}, 2, "high"), _rule({"a": "[3..8]"}, 3, "mid")],
               {"a": DecisionInput("a", "integer", {"param": "a"})})
    dead = [f for f in table_findings(t) if f.kind == "unreachable"]
    assert [f.rules for f in dead] == [["mid", "low", "high"]] and dead[0].severity == "warning"
    ranked = _table("priority", [_rule({"a": "> 1"}, 1, "wide", 1), _rule({"a": "> 2"}, 2, "narrow", 2),
                                 _rule({"a": "<= 1"}, 3, "rest", 3)])
    assert [f.rules[0] for f in table_findings(ranked) if f.kind == "unreachable"] == ["narrow"]


def test_a_cell_outside_the_listed_values_can_never_match():
    objects = {"Ticket": {"key": "ticket_id", "source": {"table": "tickets"}, "properties": {
        "ticket_id": {"type": "string"}, "reason": {"type": "enum", "values": ["damaged"]}}}}
    o = _onto({"target": "Ticket", "outputs": {"fee": "integer"},
               "inputs": {"reason": {"type": "string", "property": "reason"}},
               "rules": [{"id": "a", "when": {"reason": '"damaged"'}, "then": {"fee": 0}},
                         {"id": "typo", "when": {"reason": '"damagde"'}, "then": {"fee": 1}}]}, objects)
    assert [f.detail for f in o.findings()] == ["rule typo names only values its input cannot take"]


def test_many_gaps_are_counted_and_a_huge_table_says_it_was_not_checked(monkeypatch):
    cases = [f'"{c}"' for c in "abcdefghijklmnopqrstuvwxyz"]
    rules = [_rule({"a": c, "b": c}, 1, f"r{i}") for i, c in enumerate(cases)]
    found = [f for f in table_findings(_table("first", rules)) if f.kind == "gap"]
    assert len(found) == MAX_SHOWN + 1 and "more input gaps are not listed" in found[-1].detail
    monkeypatch.setattr(checks, "MAX_STEPS", 3)
    assert _kinds(table_findings(_table("first", rules))) == [("unchecked", "info")]


def test_a_broken_cell_is_validates_to_name_not_the_checks():
    t = _table("first", [_rule({"a": "<= seven"}, 1, "r1")])
    assert table_findings(t) == []


def test_the_example_tables_read_clean_enough_to_trust(onto):
    assert not [f for f in decision_findings(onto) if f.severity == "warning"]


def test_validate_and_the_module_check_show_findings(tmp_path, capsys):
    path = tmp_path / "o.json"
    path.write_text(json.dumps(_onto({"inputs": {"a": {"type": "integer", "param": "a"}}, "outputs": {"fee": "integer"},
                                      "rules": [{"id": "r1", "when": {"a": "> 1"}, "then": {"fee": 1}}]}).to_dict()),
                    encoding="utf-8")
    assert main(["validate", str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and [f["where"] for f in out["findings"]] == [{"a": "< 1 | 1"}]
    assert out["findings"][0]["kind"] == "gap" and out["findings"][0]["decision"] == "shipping"


def test_composition_carries_findings_and_a_customer_can_close_a_gap():
    core = Module.from_dict({"module": "shop", "namespace": "https://example.com/o#", "decisions": {"shipping": {
        "inputs": {"a": {"type": "integer", "param": "a"}}, "outputs": {"fee": "integer"}, "hit_policy": "priority",
        "rules": [{"id": "r1", "when": {"a": "> 1"}, "then": {"fee": 1}, "priority": 2}]}}})
    assert [f.kind for f in compose([core]).findings] == ["gap"]
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["shop"], "extend": {"decisions": {
        "shipping": {"rules_append": [{"id": "rest", "when": {}, "then": {"fee": 0}, "priority": 9},
                                      {"id": "promo", "when": {"a": "> 5"}, "then": {"fee": 0}, "priority": 1}]}}}})
    comp = compose([core, overlay])
    assert comp.issues == [] and _kinds(comp.findings) == [("overlap", "info")] * 2
    assert evaluate_table(comp.ontology.decisions["shipping"], {"a": 9})[1] == ["promo", "r1", "rest"]


def test_the_module_check_on_a_studio(tmp_path, capsys):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio has a graph
    assert main(["modules", str(LIB / "studio.yaml"), "--check"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["issues"] == [] and isinstance(out["findings"], list)
