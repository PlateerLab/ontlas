"""Two sources that answer one input differently: found, recorded, shown, and settled by a person's pick."""
import json

import pytest

from ontlas import Ontology
from ontlas.cli import main
from ontlas.decide.conflicts import conflict_view, record_pick, source_conflicts
from ontlas.decide.table import DecisionError, DecisionResult, evaluate_table
from ontlas.decide.zen import to_jdm
from ontlas.modules import Module, compose


def _rules() -> list[dict]:
    return [
        {"id": "p1", "when": {"reason": '"changed_mind"'}, "then": {"fee": 3000}, "source": "policy",
         "cite": "Return policy 5.1"},
        {"id": "s1", "when": {"reason": '"changed_mind"', "days": "<= 7"}, "then": {"fee": 0}, "source": "screen",
         "cite": "Refund screen rule 12"},
        {"id": "p2", "when": {"reason": '"damaged"'}, "then": {"fee": 0}, "source": "policy"},
        {"id": "s2", "when": {"reason": '"damaged"'}, "then": {"fee": 0}, "source": "screen"},
        {"id": "rest", "when": {}, "then": {"fee": 500}}]


def _decision(**more) -> dict:
    return {"inputs": {"reason": {"type": "string", "param": "reason"}, "days": {"type": "integer", "param": "days"}},
            "outputs": {"fee": "integer"}, "rules": _rules(), **more}


def _onto(conflicts=None, **decision) -> Ontology:
    return Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {},
                               "decisions": {"return_fee": _decision(**decision)}, "conflicts": conflicts or {}})


FOUND = "return_fee.p1.s1"


def test_rules_of_two_sources_that_disagree_are_found():
    (c,) = _onto().source_conflicts()
    assert c.id == FOUND and c.open and c.decision == "return_fee"
    assert [(a.source, a.says, a.rule, a.cite) for a in c.answers] == [
        ("policy", {"fee": 3000}, "p1", "Return policy 5.1"), ("screen", {"fee": 0}, "s1", "Refund screen rule 12")]
    assert c.input == {"reason": '"changed_mind"', "days": "< 7 | 7"} and c.found


def test_rules_of_one_source_or_none_are_not_a_conflict():
    d = _decision()
    for r in d["rules"]:
        r.pop("source", None)
    o = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "decisions": {"t": d}})
    assert o.source_conflicts() == []
    for r in d["rules"]:
        r["source"] = "policy"
    o = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "decisions": {"t": d}})
    assert o.source_conflicts() == []


def test_a_collected_table_has_no_conflicts_to_find():
    assert _onto(hit_policy="collect").source_conflicts() == []


def test_a_decision_answers_and_carries_the_open_disagreement():
    table = _onto().decisions["return_fee"]
    out, matched, notes = evaluate_table(table, {"reason": "changed_mind", "days": 3})
    assert out == {"fee": 3000} and matched == ["p1"]
    assert matched.conflicts == [{"rules": ["p1", "s1"], "sources": ["policy", "screen"],
                                  "says": [{"fee": 3000}, {"fee": 0}]}]
    assert any("nobody has picked" in n for n in notes)
    res = DecisionResult("return_fee", out, matched, {}).to_dict()
    assert res["conflicts"][0]["sources"] == ["policy", "screen"]
    out, matched, notes = evaluate_table(table, {"reason": "changed_mind", "days": 30})  # only one source speaks here
    assert out == {"fee": 3000} and matched.conflicts == [] and notes == []
    assert evaluate_table(table, {"reason": "damaged", "days": 3})[1].conflicts == []  # they agree


def test_a_pick_sets_the_other_source_aside_where_both_match():
    o = _onto({FOUND: {"decision": "return_fee", "rules": ["p1", "s1"], "picked": "screen", "by": "Quality lead",
                       "at": "2026-11-01", "reason": "The screen is what customers were told"}})
    assert o.validate() == []
    table = o.decisions["return_fee"]
    out, matched, notes = evaluate_table(table, {"reason": "changed_mind", "days": 3})
    assert out == {"fee": 0} and matched == ["s1"] and matched.conflicts == []
    assert notes == [f"policy set aside here by conflict {FOUND}: s1 stands over p1"]
    assert evaluate_table(table, {"reason": "changed_mind", "days": 30})[0] == {"fee": 3000}  # where it stood alone


def test_a_pick_is_shown_as_settled_with_who_and_why():
    o = _onto({FOUND: {"decision": "return_fee", "rules": ["p1", "s1"], "picked": "policy", "by": "Quality lead"}})
    (c,) = o.source_conflicts()
    v = conflict_view(c)
    assert v["status"] == "picked" and v["picked"] == "policy" and v["by"] == "Quality lead" and len(v["answers"]) == 2
    assert evaluate_table(o.decisions["return_fee"], {"reason": "changed_mind", "days": 3})[0] == {"fee": 3000}


def test_a_record_can_hold_answers_that_are_not_rules_yet():
    conflicts = {"bulky_fee": {"label": "Who pays to return a bulky item", "decision": "return_fee", "input": {"reason": "bulky"},
                              "answers": [{"source": "Return policy 5.2", "says": {"fee": 3000}, "cite": "5.2"},
                                          {"source": "Refund screen rule 15", "says": {"fee": 0}}]}}
    o = _onto(conflicts)
    assert o.validate() == []
    found = {c.id: c for c in o.source_conflicts()}
    assert set(found) == {"bulky_fee", FOUND}
    assert conflict_view(found["bulky_fee"])["status"] == "open"
    assert found["bulky_fee"].answers[0].cite == "5.2"


def test_a_conflict_needs_no_decision():
    o = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "conflicts": {"x": {"answers": [
        {"source": "a", "says": {"days": 7}}, {"source": "b", "says": {"days": 14}}]}}})
    assert o.validate() == [] and o.source_conflicts()[0].id == "x"


def test_validate_holds_a_conflict_to_two_sources_and_a_real_pick():
    conflicts = {
        "a": {"decision": "nope", "answers": [{"source": "x", "says": {"f": 1}}, {"source": "y", "says": {"f": 2}}]},
        "b": {"answers": [{"source": "x", "says": {"f": 1}}]},
        "c": {"answers": [{"source": "x", "says": {"f": 1}}, {"source": "y", "says": {"f": 1}}]},
        "d": {"answers": [{"source": "x", "says": {"f": 1}}, {"source": "y", "says": {"f": 2}}], "picked": "z", "by": "A"},
        "e": {"answers": [{"source": "x", "says": {"f": 1}}, {"source": "y", "says": {"f": 2}}], "picked": "x"},
        "f": {"decision": "return_fee", "rules": ["p1", "nope"]},
        "g": {"decision": "return_fee", "rules": ["p1", "rest"]},
        "h": {"rules": ["p1", "s1"]},
        "i": {"decision": "return_fee", "answers": [{"source": "x", "says": {"f": 1}, "rule": "nope"},
                                                    {"source": "y", "says": {"f": 2}}]}}
    issues = _onto(conflicts).validate()
    for text in ("conflict a: unknown decision 'nope'", "conflict b: needs answers from two sources",
                 "conflict c: every source says the same, so there is nothing to pick",
                 "conflict d: picked 'z' is not one of its sources ['x', 'y']", "conflict e: a pick says who made it (by)",
                 "conflict f: unknown rule 'nope'", "conflict g: rule rest names no source",
                 "conflict h: rules need a decision", "conflict i: unknown rule 'nope'"):
        assert text in issues, issues


def test_findings_leave_a_conflict_to_the_conflict_list_and_read_a_pick():
    o = _onto()
    assert not [f for f in o.findings() if f.kind == "overlap" and set(f.rules) == {"p1", "s1"}]
    picked = _onto({FOUND: {"decision": "return_fee", "rules": ["p1", "s1"], "picked": "screen", "by": "A"}})
    dead = [f.rules[0] for f in picked.findings() if f.kind == "unreachable"]
    assert dead == ["s2"]  # s1 is below p1, yet p1 yields to it; s2 only repeats p2


def test_a_tie_between_two_sources_is_a_conflict_not_a_refusal():
    d = {"inputs": {"a": {"type": "integer", "param": "a"}}, "outputs": {"fee": "integer"}, "hit_policy": "priority",
         "rules": [{"id": "x", "when": {"a": "> 1"}, "then": {"fee": 1}, "priority": 1, "source": "policy"},
                   {"id": "y", "when": {"a": "> 1"}, "then": {"fee": 2}, "priority": 1, "source": "screen"}]}
    o = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "decisions": {"t": d}})
    assert o.validate() == [] and [c.id for c in o.source_conflicts()] == ["t.x.y"]
    with pytest.raises(DecisionError, match="answer differently"):  # no order to fall back on, so no answer yet
        evaluate_table(o.decisions["t"], {"a": 3})
    d["rules"].append({"id": "z", "when": {"a": "< 1"}, "then": {"fee": 3}, "priority": 1})
    picked = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "decisions": {"t": d},
                                 "conflicts": {"t.x.y": {"decision": "t", "rules": ["x", "y"], "picked": "screen",
                                                         "by": "A"}}})
    assert evaluate_table(picked.decisions["t"], {"a": 3})[0] == {"fee": 2}


def test_the_export_to_zen_honours_a_pick():
    o = _onto({FOUND: {"decision": "return_fee", "rules": ["p1", "s1"], "picked": "screen", "by": "A"}})
    rows = to_jdm(o.decisions["return_fee"])["nodes"][1]["content"]["rules"]
    assert [r["_id"] for r in rows] == ["s1", "p1", "p2", "s2", "rest"]


def test_the_definition_round_trips():
    conflicts = {FOUND: {"decision": "return_fee", "rules": ["p1", "s1"], "picked": "screen", "by": "A", "at": "2026-11-01",
                         "reason": "r"},
                 "bulky_fee": {"label": "x", "answers": [{"source": "a", "says": {"f": 1}, "cite": "5.2"},
                                                        {"source": "b", "says": {"f": 2}}]}}
    o = _onto(conflicts)
    d = o.to_dict()
    assert d["conflicts"][FOUND] == {"decision": "return_fee", "rules": ["p1", "s1"], "picked": "screen", "by": "A",
                                     "at": "2026-11-01", "reason": "r"}
    assert d["conflicts"]["bulky_fee"]["answers"][0]["cite"] == "5.2"
    assert d["decisions"]["return_fee"]["rules"][0]["source"] == "policy"
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.conflicts == o.conflicts and again.to_dict() == d
    assert evaluate_table(again.decisions["return_fee"], {"reason": "changed_mind", "days": 1})[0] == {"fee": 0}


def _module(**more) -> Module:
    return Module.from_dict({"module": "returns", "namespace": "https://example.com/o#",
                             "decisions": {"return_fee": _decision()}, **more})


def test_composition_shows_conflicts_and_a_customer_can_pick():
    base = _module(conflicts={"bulky_fee": {"decision": "return_fee", "input": {"reason": "bulky"},
                                           "answers": [{"source": "a", "says": {"fee": 1}},
                                                       {"source": "b", "says": {"fee": 2}}]}})
    comp = compose([base])
    assert {c.id for c in comp.conflicts} == {"bulky_fee", FOUND} and comp.issues == []
    assert base.counts()["conflicts"] == 1 and "conflict:bulky_fee" in base.elements()
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["returns"], "extend": {"conflicts": {
        "bulky_fee": {"picked": "b", "by": "Quality lead"}}}})
    comp = compose([base, overlay])
    assert comp.touched["conflict:bulky_fee"] == ["acme"]
    assert {c.id: c.picked for c in comp.conflicts} == {"bulky_fee": "b", FOUND: ""}


def test_record_pick_writes_the_pick_into_a_module():
    base = _module(conflicts={"bulky_fee": {"decision": "return_fee", "answers": [{"source": "a", "says": {"fee": 1}},
                                                                                 {"source": "b", "says": {"fee": 2}}]}})
    overlay = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["returns"]})
    found = {c.id: c for c in compose([base, overlay]).conflicts}
    record_pick(overlay, found[FOUND], "screen", by="Quality lead", reason="told to customers", at="2026-11-01")
    record_pick(overlay, found["bulky_fee"], "a", by="Quality lead")
    with pytest.raises(ValueError, match="is not a source"):
        record_pick(overlay, found[FOUND], "memo", by="Quality lead")
    comp = compose([base, overlay])
    assert comp.issues == [] and {c.id: c.picked for c in comp.conflicts} == {"bulky_fee": "a", FOUND: "screen"}
    assert evaluate_table(comp.ontology.decisions["return_fee"], {"reason": "changed_mind", "days": 1})[0] == {"fee": 0}
    assert overlay.to_dict()["conflicts"][FOUND]["reason"] == "told to customers"  # survives the module's file


def test_a_conflict_that_loses_its_rule_goes_when_settled():
    from ontlas.modules import settle

    base = _module(conflicts={FOUND: {"decision": "return_fee", "rules": ["p1", "s1"]}})
    gone = Module.from_dict({"module": "acme", "kind": "customer", "requires": ["returns"],
                             "remove": {"decisions": ["return_fee"]}})
    assert any(i.startswith("conflict return_fee.p1.s1:") for i in compose([base, gone]).issues)
    assert "conflict:return_fee.p1.s1" in settle(gone, [base]) and compose([base, gone]).issues == []


def test_named_parameters_in_answers_read_their_value():
    d = _decision()
    d["rules"][0]["then"]["fee"] = "@standard_fee"
    o = Ontology.from_dict({"namespace": "https://example.com/o#", "objects": {}, "decisions": {"t": d},
                            "parameters": {"standard_fee": 3000},
                            "conflicts": {"c": {"decision": "t", "rules": ["p1", "s1"]}}})
    assert o.conflicts["c"].answers[0].says == {"fee": 3000}
    assert source_conflicts(o)[0].id == "c"


def test_validate_shows_them_on_the_command_line(tmp_path, capsys):
    path = tmp_path / "o.json"
    path.write_text(json.dumps(_onto().to_dict()), encoding="utf-8")
    assert main(["validate", str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["conflicts"][0]["id"] == FOUND and out["conflicts"][0]["status"] == "open"
    assert [a["source"] for a in out["conflicts"][0]["answers"]] == ["policy", "screen"]
