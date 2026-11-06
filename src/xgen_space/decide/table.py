"""Decision tables: inputs read from the ontology, rules as unary tests, outputs with the evidence behind them.

Hit policies: `first` takes the first rule listed that matches, `collect` every rule that matches, `unique` refuses two
matches, and `priority` takes the matching rule with the lowest `priority` number (1 before 2) and shows what it
overrode.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_space.decide.cells import evaluate, parse_test, resolve
from xgen_space.model import DecisionRule, DecisionTable

_NAMED = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")


class DecisionError(ValueError):
    """The decision cannot be evaluated as defined."""


class Matched(list):
    """The ids of the rules that matched, the winner first, carrying what the others would have said and the
    named parameters they read."""

    def __init__(self, ids=(), overridden=(), parameters=None):
        super().__init__(ids)
        self.overridden = list(overridden)
        self.parameters = dict(parameters or {})


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
    parameters: dict[str, Any] = field(default_factory=dict)  # the named values the matched rules read

    def __post_init__(self):
        self.overridden = self.overridden or getattr(self.matched, "overridden", [])
        self.parameters = self.parameters or getattr(self.matched, "parameters", {})

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence"] = [asdict(e) for e in self.evidence]
        return d


def answer(table: DecisionTable, rule: DecisionRule) -> dict[str, Any]:
    """What a rule gives, with its `@name` outputs read from the parameters."""
    return {k: resolve(v, table.named) for k, v in rule.then.items()}


def _read(table: DecisionTable, hits: list[DecisionRule]) -> dict[str, Any]:
    named = table.named
    if not named:
        return {}
    text = " ".join(str(v) for r in hits for v in (*r.when.values(), *r.then.values()))
    return {n: named[n] for n in _NAMED.findall(text) if n in named}


def _by_priority(table: DecisionTable, hits: list[DecisionRule]) -> tuple[Any, list[str], list[str]]:
    ranked = sorted(hits, key=lambda r: float("inf") if r.priority is None else r.priority)
    top = ranked[0]
    tied = [r.id for r in ranked[1:] if r.priority == top.priority and r.then != top.then]
    if tied:
        raise DecisionError(f"{table.name}: rules {[top.id, *tied]} match at priority {top.priority} and answer "
                            "differently")
    lost = [r for r in ranked[1:] if r.then != top.then]
    overridden = [{"rule": r.id, "priority": r.priority, "by": top.id,
                   "would_give": {k: answer(table, r).get(k) for k in table.outputs}} for r in lost]
    notes = ([top.note] if top.note else []) + [f"{top.id} (priority {top.priority}) overrides {r.id} "
                                                f"(priority {r.priority})" for r in lost]
    matched = Matched([r.id for r in ranked], overridden, _read(table, ranked))
    return {k: answer(table, top).get(k) for k in table.outputs}, matched, notes


def evaluate_table(table: DecisionTable, inputs: dict[str, Any]) -> tuple[Any, list[str], list[str]]:
    """Return (outputs, matched rule ids, rule notes) under the table's hit policy."""
    hits, named = [], table.named
    for rule in table.rules:
        if all(evaluate(parse_test(cell, named), inputs.get(name)) for name, cell in rule.when.items()):
            hits.append(rule)
            if table.hit_policy == "first":
                break
    if table.hit_policy == "unique" and len(hits) > 1:
        raise DecisionError(f"{table.name}: rules {[r.id for r in hits]} all match under hit policy 'unique'")
    if table.hit_policy == "priority" and hits:
        return _by_priority(table, hits)
    ids, notes = Matched([r.id for r in hits], parameters=_read(table, hits)), [r.note for r in hits if r.note]
    if table.hit_policy == "collect":
        return [answer(table, r) for r in hits], ids, notes
    if not hits:
        return {k: None for k in table.outputs}, ids, notes
    return {k: answer(table, hits[0]).get(k) for k in table.outputs}, ids, notes
