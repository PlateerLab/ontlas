"""Source conflicts: the same input answered differently by two sources, kept for a person to pick.

A rule says where it came from with `source`. Two rules of different sources that meet and answer differently are found
on their own. The `conflicts` section records one by hand, for answers that are not rules yet, and holds the pick:

    conflicts:
      bulky_return_fee:
        label: Who pays to return a bulky item
        decision: return_fee
        input: {reason: bulky}
        answers:
          - {source: Return policy 5.1, says: {fee: 3000}, cite: section 5.1}
          - {source: Refund screen rule 12, says: {fee: 0}}
      return_fee.p1.s1: {decision: return_fee, rules: [p1, s1], picked: screen, by: Quality lead, at: 2026-11-01, reason: ...}

A pick sets the other source's rules aside wherever the picked one also matches; until then a decision answers as its
hit policy says and carries the disagreement with it.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ontlas.decide.checks import _meet, _space
from ontlas.decide.table import answer
from ontlas.model import ConflictAnswer, DecisionRule, DecisionTable, Ontology, SourceConflict
from ontlas.modules import Module


def _pair(table: DecisionTable, a: DecisionRule, b: DecisionRule, where: dict[str, str]) -> SourceConflict:
    return SourceConflict(f"{table.name}.{a.id}.{b.id}", table.name, dict(where),
                          [ConflictAnswer(r.source, answer(table, r), r.id, r.cite) for r in (a, b)], found=True)


def _found(onto: Ontology, table: DecisionTable) -> list[SourceConflict]:
    if table.hit_policy == "collect" or len({r.source for r in table.rules if r.source}) < 2:
        return []
    space = _space(onto, table)
    out = []
    for i, a in enumerate(table.rules):
        for j in range(i + 1, len(table.rules)):
            b = table.rules[j]
            if a.source and b.source and a.source != b.source and a.then != b.then:
                both = _meet(space.boxes[i], space.boxes[j])
                if both is not None:
                    out.append(_pair(table, a, b, space.where(both)))
    return out


def source_conflicts(onto: Ontology) -> list[SourceConflict]:
    """What is recorded, then what the rules say with no record yet."""
    from ontlas.decide.cells import CellError

    out = list(onto.conflicts.values())
    known = {(c.decision, frozenset(a.rule for a in c.answers)) for c in out}
    for table in onto.decisions.values():
        try:
            found = _found(onto, table)
        except CellError:
            continue  # validate names the cell
        out += [c for c in found if (c.decision, frozenset(a.rule for a in c.answers)) not in known]
    return out


def conflict_view(c: SourceConflict) -> dict[str, Any]:
    return {"id": c.id, "label": c.label, "decision": c.decision, "input": c.input,
            "answers": [asdict(a) for a in c.answers], "status": "open" if c.open else "picked", "picked": c.picked,
            "by": c.by, "at": c.at, "reason": c.reason}


def conflict_issues(onto: Ontology, c: SourceConflict) -> list[str]:
    out = []
    table = onto.decisions.get(c.decision) if c.decision else None
    if c.decision and table is None:
        out.append(f"unknown decision '{c.decision}'")
    ids = {r.id: r for r in table.rules} if table else {}
    for name in c.rules:
        if table is None:
            out.append("rules need a decision")
            break
        if name not in ids:
            out.append(f"unknown rule '{name}'")
        elif not ids[name].source:
            out.append(f"rule {name} names no source")
    for a in c.answers:
        if table is not None and a.rule and a.rule not in ids:
            out.append(f"unknown rule '{a.rule}'")
    sources = {a.source for a in c.answers}
    if len(sources) < 2:
        out.append("needs answers from two sources")
    elif len({str(sorted(a.says.items(), key=str)) for a in c.answers}) < 2:
        out.append("every source says the same, so there is nothing to pick")
    if c.picked and c.picked not in sources:
        out.append(f"picked '{c.picked}' is not one of its sources {sorted(sources)}")
    if c.picked and not c.by:
        out.append("a pick says who made it (by)")
    return out


def record_pick(module: Module, c: SourceConflict, source: str, *, by: str, reason: str = "", at: str = "") -> None:
    """Write a person's pick into a module: over the record if there is one, as a new record if the rules found it."""
    if source not in {a.source for a in c.answers}:
        raise ValueError(f"'{source}' is not a source of {c.id}")
    pick = {"picked": source, "by": by, **({"reason": reason} if reason else {}), **({"at": at} if at else {})}
    if c.found:
        rules = [a.rule for a in c.answers]
        module.body.setdefault("conflicts", {})[c.id] = {"decision": c.decision, "rules": rules, "input": c.input, **pick}
    else:
        module.extend.setdefault("conflicts", {})[c.id] = pick
