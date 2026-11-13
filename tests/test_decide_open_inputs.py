"""Which inputs a decision still needs when only some were given (decide.table.open_inputs)."""
from ontlas.decide.table import open_inputs
from ontlas.model import DecisionInput, DecisionRule, DecisionTable


def _table(policy: str, rules: list[DecisionRule]) -> DecisionTable:
    ins = {n: DecisionInput(n, "integer", {}) for n in ("a", "b", "c")}
    return DecisionTable("t", ins, {"x": "string"}, rules, hit_policy=policy)


def _rules() -> list[DecisionRule]:
    return [DecisionRule({"a": "> 5", "b": "1"}, {"x": "p"}, id="r1"),
            DecisionRule({"a": "<= 5"}, {"x": "q"}, id="r2"),
            DecisionRule({"c": "1"}, {"x": "r"}, id="r3")]


def test_first_reads_nothing_after_the_first_rule_that_stands():
    t = _table("first", _rules())
    assert open_inputs(t, {"a": 3}, {"b", "c"}) == []  # r1 is out by a, r2 stands
    assert open_inputs(t, {"a": 9}, {"b", "c"}) == ["b", "c"]  # r1 turns on b, and r3 on c should r1 fail
    assert open_inputs(t, {"a": 9, "b": 1}, {"c"}) == []  # r1 stands
    assert open_inputs(t, {}, {"a", "b", "c"}) == ["a", "b", "c"]


def test_the_other_hit_policies_read_every_rule_not_ruled_out():
    for policy in ("collect", "unique", "priority"):
        t = _table(policy, _rules())
        assert open_inputs(t, {"a": 3}, {"b", "c"}) == ["c"], policy  # r2 stands, and r3 may as well
        assert open_inputs(t, {"a": 3, "c": 2}, {"b"}) == [], policy  # r1 and r3 are out by what was given


def test_a_rule_a_pick_sets_aside_waits_on_the_rule_picked_over_it():
    r1 = DecisionRule({"a": "<= 5"}, {"x": "p"}, id="r1", overruled_by={"r2": "c1"})
    r2 = DecisionRule({"b": "1"}, {"x": "q"}, id="r2")
    t = _table("first", [r1, r2])
    assert open_inputs(t, {"a": 3}, {"b"}) == ["b"]  # r1 stands unless r2 holds too
    assert open_inputs(t, {"a": 3, "b": 2}, set()) == []
    axiom = DecisionRule({"a": "<= 5"}, {"x": "p"}, id="r1", overruled_by={"r2": "c1"}, layer="axiom")
    assert open_inputs(_table("first", [axiom, r2]), {"a": 3}, {"b"}) == []  # a pick never sets an AXIOM rule aside
