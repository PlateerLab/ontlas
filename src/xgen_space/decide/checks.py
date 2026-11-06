"""What a decision table says twice or not at all: overlapping rules, rules that can never win, inputs no rule answers.

Each input's values are cut into atoms at the values its cells name, so a rule is a box of atoms and two rules meet
where their boxes do. Numbers cut at their bounds; text at the values named, with one atom for anything else unless the
property lists its values. A missing value counts only on an input whose cells speak of null: whether a value can be
missing is the data's business, and every optional column would otherwise read as a gap.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_space.decide.cells import Any_, CellError, Compare, IsNull, OneOf, Range, evaluate, parse_test
from xgen_space.model import DecisionTable, Ontology

MAX_STEPS = 50_000  # cells of a table's input space walked before saying so instead of going on
MAX_SHOWN = 20      # gaps listed per table; the rest are counted
OTHER = "￿"    # sorts after any text a cell names


@dataclass
class Finding:
    kind: str      # gap | overlap | unreachable | tie | unchecked
    severity: str  # warning: for a person to look at; info: how the table is meant to work, shown for the record
    decision: str
    rules: list[str]
    detail: str
    where: dict[str, str] = field(default_factory=dict)  # the inputs it happens at

    def __str__(self) -> str:
        return f"decision {self.decision}: {self.detail}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class _Atom:
    label: str
    sample: Any


class _TooWide(Exception):
    """The table's input space is larger than MAX_STEPS."""


def _literals(test: Any) -> list:
    if isinstance(test, Compare):
        return [test.value]
    if isinstance(test, Range):
        return [test.low, test.high]
    if isinstance(test, OneOf):
        return list(test.values)
    return []


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _span(low: Any, high: Any, whole: bool) -> _Atom | None:
    """What lies strictly between two bounds; between 3 and 4 no whole number does."""
    if not whole:
        return _Atom(f"({low}..{high})", (low + high) / 2)
    first, last = math.floor(low) + 1, math.ceil(high) - 1
    if first > last:
        return None
    return _Atom(str(first) if first == last else f"{first}..{last}", first)


def _numbers(values: list, whole: bool, floor: int | None) -> list[_Atom]:
    bounds = sorted(set(values))
    atoms: list[_Atom] = []
    if floor is None:
        atoms.append(_Atom(f"< {bounds[0]}", bounds[0] - 1))
    else:  # a count or a number of days starts at 0
        bounds = sorted({floor, *(b for b in bounds if b >= floor)})
    for i, b in enumerate(bounds):
        if not whole or float(b).is_integer():
            atoms.append(_Atom(str(b), b))
        if i + 1 < len(bounds):
            span = _span(b, bounds[i + 1], whole)
            if span:
                atoms.append(span)
    atoms.append(_Atom(f"> {bounds[-1]}", bounds[-1] + 1))
    return atoms


def _texts(values: list, ordered: bool) -> list[_Atom]:
    names = sorted(set(values))
    if not ordered:
        return [*(_Atom(f'"{v}"', v) for v in names), _Atom("any other value", OTHER)]
    atoms = [_Atom(f'before "{names[0]}"', "")] if names[0] else []
    for i, v in enumerate(names):
        atoms.append(_Atom(f'"{v}"', v))
        nxt = f' and "{names[i + 1]}"' if i + 1 < len(names) else ""
        atoms.append(_Atom(f'between "{v}"{nxt}' if nxt else f'after "{v}"', v + "\0"))
    return atoms


def _closed_values(onto: Ontology | None, table: DecisionTable, name: str) -> list | None:
    """The values an input can take, where the definition lists them."""
    inp = table.inputs.get(name)
    if onto is None or inp is None or "property" not in inp.source or not table.target:
        return None
    from xgen_space.check import _find_prop

    here = table.target
    for step in inp.source.get("path", []):
        lk = onto.links.get(step) or onto.link_by_inverse(step)
        if lk is None:
            return None
        here = lk.target if lk.name == step else lk.source
    p = _find_prop(onto, here, inp.source["property"])
    return list(p.values) if p is not None and p.type == "enum" and p.values else None


def _atoms(onto: Ontology | None, table: DecisionTable, name: str, tests: list) -> list[_Atom]:
    inp = table.inputs.get(name)
    kind = inp.type if inp else ""
    values = [v for t in tests for v in _literals(t) if v is not None]
    numbers = [v for v in values if _is_number(v)]
    texts = [v for v in values if isinstance(v, str)]
    out: list[_Atom] = []
    closed = _closed_values(onto, table, name)
    if closed is not None:
        out += [_Atom(f'"{v}"', v) for v in closed]
    elif texts:
        ordered = any((isinstance(t, Compare) and t.op not in ("==", "!=")) or isinstance(t, Range) for t in tests)
        out += _texts(texts, ordered)
    if numbers:
        whole = kind == "integer" or (inp is not None and ("count" in inp.source or "days_since" in inp.source))
        floor = 0 if inp is not None and ("count" in inp.source or "days_since" in inp.source) else None
        out += _numbers(numbers, whole, floor)
    if kind == "boolean" or any(isinstance(v, bool) for v in values):
        out += [_Atom("true", True), _Atom("false", False)]
    if not out:
        out = [_Atom("any value", OTHER)]
    if any(isinstance(t, IsNull) for t in tests):
        out.append(_Atom("null", None))
    return out


@dataclass
class _Space:
    """A table's rules as boxes of atoms, one set of atom numbers per input."""

    columns: list[str]
    atoms: list[list[_Atom]]
    boxes: list[list[set[int]]]

    @property
    def whole(self) -> list[set[int]]:
        return [set(range(len(a))) for a in self.atoms]

    def where(self, box: list[set[int]]) -> dict[str, str]:
        out = {}
        for c, name in enumerate(self.columns):
            if len(box[c]) < len(self.atoms[c]):
                out[name] = " | ".join(self.atoms[c][i].label for i in sorted(box[c]))
        return out


def _space(onto: Ontology | None, table: DecisionTable) -> _Space:
    tests = [{k: parse_test(v, table.named) for k, v in r.when.items()} for r in table.rules]
    columns = [c for c in dict.fromkeys([*table.inputs, *(k for t in tests for k in t)])
               if any(not isinstance(t.get(c, Any_()), Any_) for t in tests)]
    atoms = [_atoms(onto, table, c, [t[c] for t in tests if c in t]) for c in columns]
    boxes = [[{i for i, a in enumerate(atoms[c]) if evaluate(t.get(name, Any_()), a.sample)}
              for c, name in enumerate(columns)] for t in tests]
    return _Space(columns, atoms, boxes)


def _uncovered(box: list[set[int]], rules: list[list[set[int]]], budget: list[int]) -> list[list[set[int]]]:
    """The parts of `box` no rule reaches, walking one input at a time and grouping the atoms the same rules take."""
    out: list[list[set[int]]] = []

    def walk(col: int, here: list[set[int]], alive: list[list[set[int]]]) -> None:
        budget[0] -= 1
        if budget[0] < 0:
            raise _TooWide
        if not alive:
            out.append(here)
            return
        if any(all(here[c] <= r[c] for c in range(col, len(here))) for r in alive):
            return
        groups: dict[tuple, set[int]] = {}
        for atom in here[col]:
            groups.setdefault(tuple(i for i, r in enumerate(alive) if atom in r[col]), set()).add(atom)
        for taken, atoms in groups.items():
            walk(col + 1, [*here[:col], atoms, *here[col + 1:]], [alive[i] for i in taken])

    walk(0, box, rules)
    return out


def _meet(a: list[set[int]], b: list[set[int]]) -> list[set[int]] | None:
    both = [x & y for x, y in zip(a, b)]
    return both if all(both) else None


def _gaps(table: DecisionTable, space: _Space, budget: list[int]) -> list[Finding]:
    boxes = _uncovered(space.whole, space.boxes, budget)
    out = [Finding("gap", "warning", table.name, [], "no rule answers " + _say(space.where(b)), space.where(b))
           for b in boxes[:MAX_SHOWN]]
    if len(boxes) > MAX_SHOWN:
        out.append(Finding("gap", "warning", table.name, [], f"{len(boxes) - MAX_SHOWN} more input gaps are not listed"))
    return out


def _say(where: dict[str, str]) -> str:
    return ", ".join(f"{k} = {v}" for k, v in where.items()) or "any input"


def _ahead(table: DecisionTable, i: int) -> list[int]:
    """The rules that decide before rule i does."""
    if table.hit_policy == "priority":
        mine = table.rules[i].priority
        return [j for j, r in enumerate(table.rules) if mine is not None and r.priority is not None and r.priority < mine]
    return list(range(i))


def _unreachable(table: DecisionTable, space: _Space, budget: list[int]) -> list[Finding]:
    out = []
    for i, r in enumerate(table.rules):
        box = space.boxes[i]
        if not all(box):
            out.append(Finding("unreachable", "warning", table.name, [r.id],
                               f"rule {r.id} names only values its input cannot take"))
        elif not _uncovered(box, [space.boxes[j] for j in _ahead(table, i)], budget):
            before = [table.rules[j].id for j in _ahead(table, i)]
            out.append(Finding("unreachable", "warning", table.name, [r.id, *before],
                               f"rule {r.id} can never win: {', '.join(before)} answer everything it does"))
    return out


def _overlaps(table: DecisionTable, space: _Space) -> list[Finding]:
    out = []
    policy = table.hit_policy
    for i, a in enumerate(table.rules):
        for j in range(i + 1, len(table.rules)):
            b = table.rules[j]
            both = _meet(space.boxes[i], space.boxes[j])
            if both is None or (policy != "unique" and a.then == b.then):
                continue
            where, ids = space.where(both), [a.id, b.id]
            at = _say(where)
            if policy == "unique":
                out.append(Finding("overlap", "warning", table.name, ids,
                                   f"rules {a.id} and {b.id} both match {at}, which hit policy unique refuses", where))
            elif policy == "first":
                out.append(Finding("overlap", "info", table.name, ids,
                                   f"rules {a.id} and {b.id} both match {at}; {a.id} is listed first", where))
            elif a.priority == b.priority:
                out.append(Finding("tie", "warning", table.name, ids,
                                   f"rules {a.id} and {b.id} both match {at} at priority {a.priority} and answer "
                                   "differently", where))
            else:
                top, low = (a, b) if (a.priority or 0) < (b.priority or 0) else (b, a)
                out.append(Finding("overlap", "info", table.name, ids,
                                   f"rule {top.id} (priority {top.priority}) overrides {low.id} "
                                   f"(priority {low.priority}) at {at}", where))
    return out


def table_findings(table: DecisionTable, onto: Ontology | None = None) -> list[Finding]:
    """A collected table is left out: every rule that applies is the answer, and none applying is an answer too."""
    if table.hit_policy not in ("first", "unique", "priority") or not table.rules:
        return []
    try:
        space = _space(onto, table)
    except CellError:
        return []  # validate names the cell
    budget = [MAX_STEPS]
    try:
        out = _overlaps(table, space)
        if table.hit_policy != "unique":
            out += _unreachable(table, space, budget)
        return out + _gaps(table, space, budget)
    except _TooWide:
        return [Finding("unchecked", "info", table.name, [],
                        f"more than {MAX_STEPS} input combinations; gaps and unreachable rules were not checked")]


def decision_findings(onto: Ontology) -> list[Finding]:
    """Every table's findings but ties, which validate refuses."""
    return [f for d in onto.decisions.values() for f in table_findings(d, onto) if f.kind != "tie"]
