"""Decision tables: inputs read from the ontology, rules as unary tests, outputs with the evidence behind them.

Hit policies: `first` takes the first rule listed that matches, `collect` every rule that matches, `unique` refuses two
matches, and `priority` takes the matching rule with the lowest `priority` number (1 before 2) and shows what it
overrode.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_space.decide.cells import evaluate, parse_test
from xgen_space.model import DecisionRule, DecisionTable


class DecisionError(ValueError):
    """The decision cannot be evaluated as defined."""


class Matched(list):
    """The ids of the rules that matched, the winner first, carrying what the others would have said."""

    def __init__(self, ids=(), overridden=()):
        super().__init__(ids)
        self.overridden = list(overridden)


@dataclass
class Evidence:
    input: str
    value: Any
    object_type: str = ""
    key: str = ""
    property: str = ""
    source: str = ""


@dataclass
class DecisionResult:
    decision: str
    outputs: Any
    matched: list[str]
    inputs: dict[str, Any]
    evidence: list[Evidence] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    engine: str = "native"
    target: str = ""
    key: str = ""
    overridden: list[dict] = field(default_factory=list)  # {rule, priority, by, would_give}, under hit policy priority

    def __post_init__(self):
        self.overridden = self.overridden or getattr(self.matched, "overridden", [])

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence"] = [asdict(e) for e in self.evidence]
        return d


def _by_priority(table: DecisionTable, hits: list[DecisionRule]) -> tuple[Any, list[str], list[str]]:
    ranked = sorted(hits, key=lambda r: float("inf") if r.priority is None else r.priority)
    top = ranked[0]
    tied = [r.id for r in ranked[1:] if r.priority == top.priority and r.then != top.then]
    if tied:
        raise DecisionError(f"{table.name}: rules {[top.id, *tied]} match at priority {top.priority} and answer "
                            "differently")
    lost = [r for r in ranked[1:] if r.then != top.then]
    overridden = [{"rule": r.id, "priority": r.priority, "by": top.id,
                   "would_give": {k: r.then.get(k) for k in table.outputs}} for r in lost]
    notes = ([top.note] if top.note else []) + [f"{top.id} (priority {top.priority}) overrides {r.id} "
                                                f"(priority {r.priority})" for r in lost]
    return {k: top.then.get(k) for k in table.outputs}, Matched([r.id for r in ranked], overridden), notes


def evaluate_table(table: DecisionTable, inputs: dict[str, Any]) -> tuple[Any, list[str], list[str]]:
    """Return (outputs, matched rule ids, rule notes) under the table's hit policy."""
    hits = []
    for rule in table.rules:
        if all(evaluate(parse_test(cell), inputs.get(name)) for name, cell in rule.when.items()):
            hits.append(rule)
            if table.hit_policy == "first":
                break
    if table.hit_policy == "unique" and len(hits) > 1:
        raise DecisionError(f"{table.name}: rules {[r.id for r in hits]} all match under hit policy 'unique'")
    if table.hit_policy == "priority" and hits:
        return _by_priority(table, hits)
    ids, notes = [r.id for r in hits], [r.note for r in hits if r.note]
    if table.hit_policy == "collect":
        return [dict(r.then) for r in hits], ids, notes
    if not hits:
        return {k: None for k in table.outputs}, ids, notes
    return {k: hits[0].then.get(k) for k in table.outputs}, ids, notes
