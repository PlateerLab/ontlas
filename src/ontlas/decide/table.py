"""Decision tables: inputs read from the ontology, rules as unary tests, outputs with the evidence behind them.

Hit policies: `first` takes the first rule listed that matches, `collect` every rule that matches, `unique` refuses two
matches, and `priority` takes the matching rule with the lowest `priority` number (1 before 2) and shows what it
overrode.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any

from ontlas.decide.cells import evaluate, parse_test, resolve
from ontlas.model import DecisionRule, DecisionTable

_NAMED = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")


class DecisionError(ValueError):
    """The decision cannot be evaluated as defined."""


class MissingValues(DecisionError):
    """Decided on given values, some of its inputs were not given, or were given a value the property they read does
    not allow. Not given is not known: a value it was given as null (no delivery date yet) decides, one it was not
    given at all is asked for rather than read as null. A code that is not one of the allowed ones (배송완료 for
    배송완료(27)) is asked for again with the allowed ones, never decided on: it would match no rule and answer wrongly."""

    def __init__(self, decision: str, missing: list[dict], invalid: list[dict] | None = None):
        self.decision, self.missing, self.invalid = decision, missing, list(invalid or [])
        said = []
        if self.invalid:
            said.append("was given a value that is not allowed for " + ", ".join(m["input"] for m in self.invalid))
        if missing:  # last: the page reads the names after `needs`
            said.append("needs " + ", ".join(m["input"] for m in missing))
        super().__init__(f"decision '{decision}' " + "; ".join(said))


class Matched(list):
    """The ids of the rules that matched, the winner first, carrying what the others would have said, the named
    parameters they read, and where their sources disagree."""

    def __init__(self, ids=(), overridden=(), parameters=None):
        super().__init__(ids)
        self.overridden = list(overridden)
        self.parameters = dict(parameters or {})
        self.conflicts: list[dict] = []


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
    conflicts: list[dict] = field(default_factory=list)  # {rules, sources, says}: nobody has picked between them yet
    also: list[str] = field(default_factory=list)  # rules that held too, which the hit policy did not use
    path: dict = field(default_factory=dict)  # layer by layer, AXIOM first: what fired, and where it came from (semantic)

    def __post_init__(self):
        self.overridden = self.overridden or getattr(self.matched, "overridden", [])
        self.parameters = self.parameters or getattr(self.matched, "parameters", {})
        self.conflicts = self.conflicts or getattr(self.matched, "conflicts", [])

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
    # an AXIOM rule is checked before any number a lower layer gives its own rules
    ranked = sorted(hits, key=lambda r: (r.layer != "axiom", float("inf") if r.priority is None else r.priority))
    top = ranked[0]
    tied = [r.id for r in ranked[1:] if r.priority == top.priority and r.then != top.then
            and (r.layer == "axiom") == (top.layer == "axiom")]
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


def _disagreements(table: DecisionTable, hits: list[DecisionRule]) -> list[dict]:
    if table.hit_policy == "collect":
        return []
    return [{"rules": [a.id, b.id], "sources": [a.source, b.source], "says": [answer(table, a), answer(table, b)]}
            for a, b in combinations(hits, 2) if a.source and b.source and a.source != b.source and a.then != b.then]


def holding(table: DecisionTable, inputs: dict[str, Any]) -> list[DecisionRule]:
    """Every rule whose conditions the inputs meet, in table order, before the hit policy picks."""
    named = table.named
    return [r for r in table.rules
            if all(evaluate(parse_test(cell, named), inputs.get(name)) for name, cell in r.when.items())]


def evaluate_table(table: DecisionTable, inputs: dict[str, Any]) -> tuple[Any, list[str], list[str]]:
    """Return (outputs, matched rule ids, rule notes) under the table's hit policy."""
    matching = holding(table, inputs)
    ids = {r.id for r in matching}
    # a person picked the other source here; an AXIOM rule is never set aside by a pick
    picked = [bool(ids & set(r.overruled_by)) and r.layer != "axiom" for r in matching]
    aside = [r for r, out in zip(matching, picked) if out]
    hits = [r for r, out in zip(matching, picked) if not out]
    disagree = _disagreements(table, hits)
    said = [f"{r.source or r.id} set aside here by conflict {r.overruled_by[k]}: {k} stands over {r.id}"
            for r in aside for k in r.overruled_by if k in ids]
    said += [f"sources disagree and nobody has picked: {d['sources'][0]} says {d['says'][0]}, "
             f"{d['sources'][1]} says {d['says'][1]}" for d in disagree]
    outputs, matched, notes = _outcome(table, hits)
    matched.conflicts = disagree
    return outputs, matched, notes + said


def _outcome(table: DecisionTable, hits: list[DecisionRule]) -> tuple[Any, Matched, list[str]]:
    if table.hit_policy == "first":
        hits = hits[:1]
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
