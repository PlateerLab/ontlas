"""A decision table in people's words: what an input is called, what a cell asks, what a rule says."""
from __future__ import annotations

import math
from typing import Any

from ontlas.check import _find_prop
from ontlas.decide.cells import Any_, CellError, Compare, IsNull, OneOf, Range, parse_test, resolve
from ontlas.model import DecisionRule, DecisionTable, Ontology

OPS = {"<=": "{} 이하", ">=": "{} 이상", "<": "{} 미만", ">": "{} 초과", "==": "{}", "!=": "{} 제외"}
WORDS = {True: "예", False: "아니요"}
UNIT_WORD = {"KRW": "원"}  # a currency code a property keeps, as people write it after a number


def reads(onto: Ontology, table: DecisionTable, name: str) -> tuple[str, str]:
    """The object type and the property an input reads; either may be empty when it reads neither."""
    src = table.inputs[name].source
    prop = src.get("property") or src.get("days_since") or ""
    here = table.target
    for step in src.get("path") or []:
        lk = onto.links.get(step) or onto.link_by_inverse(step)
        if lk is None:
            return "", ""
        here = lk.target if lk.name == step else lk.source
    return here, prop


def unit_of(onto: Ontology, table: DecisionTable, name: str) -> str:
    src = table.inputs[name].source
    if "days_since" in src:
        return "일"
    if "count" in src:
        return "건"
    here, prop = reads(onto, table, name)
    p = _find_prop(onto, here, prop) if here and prop else None
    if p is None or not p.unit:
        return ""
    return UNIT_WORD.get(p.unit, " " + p.unit)


def input_label(onto: Ontology, table: DecisionTable, name: str) -> str:
    src = table.inputs[name].source
    if src.get("label"):  # a value the caller states reads no property to take a name from, so it is given its own
        return str(src["label"])
    if "count" in src:
        lk = onto.links.get(src["count"][-1]) or onto.link_by_inverse(src["count"][-1])
        return f"{lk.label or name} 수" if lk is not None else name
    here, prop = reads(onto, table, name)
    p = _find_prop(onto, here, prop) if here and prop else None
    if p is None:
        return name
    label = p.label or prop
    return f"{label} 경과일" if "days_since" in src else label


def _value(v: Any, unit: str, labels: dict) -> str:
    if isinstance(v, bool):
        return WORDS[v]
    if v is None:
        return "값 없음"
    if str(v) not in labels and isinstance(v, (int, float)) and unit:
        return f"{v:,}{unit}"  # an amount or a count, with its thousands marked
    return f"{labels.get(str(v), v)}{unit}"


def cell_words(cell: Any, named: dict[str, Any] | None = None, *, unit: str = "", labels: dict | None = None) -> str:
    """What a cell asks. A cell that cannot be read stands as written, so nothing is hidden behind a nicer word."""
    labels = labels or {}
    try:
        t = parse_test(cell, named or {})
    except CellError:
        return str(cell)
    if isinstance(t, Any_):
        return "-"
    if isinstance(t, IsNull):
        return "값 있음" if t.negate else "값 없음"
    if isinstance(t, Compare):
        return OPS.get(t.op, "{}").format(_value(t.value, unit, labels))
    if isinstance(t, Range):
        return f"{_value(t.low, '', labels)}~{_value(t.high, unit, labels)}"
    if isinstance(t, OneOf):
        said = ", ".join(_value(v, unit, labels) for v in t.values)
        return f"{said} 제외" if t.negate else said
    return str(cell)


def cell_parts(cell: Any) -> dict[str, str]:
    """A cell as a form holds it: what is asked and of what. A cell no form can hold stays as written, under `raw`."""
    s = "" if cell is None else str(cell).strip()
    if s in ("", "-"):
        return {"op": "any", "value": ""}
    if s == "null":
        return {"op": "null", "value": ""}
    if s == "not null":
        return {"op": "notnull", "value": ""}

    def bare(x: str) -> str:
        x = x.strip()
        return x[1:-1] if len(x) >= 2 and x[0] == x[-1] and x[0] in "\"'" else x

    low = s.lower()
    for prefix, op in (("not in", "notin"), ("in", "in")):
        if low.startswith(prefix) and s[len(prefix):].strip().startswith("["):
            return {"op": op, "value": ", ".join(bare(x) for x in s[len(prefix):].strip()[1:-1].split(","))}
    for sign, op in (("<=", "lte"), (">=", "gte"), ("!=", "ne"), ("<", "lt"), (">", "gt"), ("==", "eq"), ("=", "eq")):
        if s.startswith(sign):
            return {"op": op, "value": bare(s[len(sign):])}
    if s.startswith(("[", "(")):
        return {"op": "raw", "value": s}
    return {"op": "eq", "value": bare(s)}


def cell_of(op: str, value: Any, kind: str = "string") -> str:
    """The cell a form means. A number and a named value stand bare; text is quoted, because a cell is a test and not a word."""
    v = str(value if value is not None else "").strip()
    if op == "any":
        return "-"
    if op == "null":
        return "null"
    if op == "notnull":
        return "not null"
    if op == "raw":
        return v

    def lit(x: str) -> str:
        x = x.strip()
        if x.startswith("@") or x in ("true", "false") or kind in ("integer", "decimal", "number", "float", "boolean", "date", "datetime"):
            return x
        return '"' + x.replace('"', "") + '"'

    if op in ("in", "notin"):
        items = ", ".join(lit(x) for x in v.split(",") if x.strip())
        return f"in [{items}]" if op == "in" else f"not in [{items}]"
    sign = {"eq": "", "ne": "!= ", "lte": "<= ", "gte": ">= ", "lt": "< ", "gt": "> "}.get(op)
    if sign is None:
        raise ValueError(f"unknown test '{op}'")
    return f"{sign}{lit(v)}"


def labels_of(onto: Ontology, table: DecisionTable, name: str) -> dict:
    here, prop = reads(onto, table, name)
    p = _find_prop(onto, here, prop) if here and prop else None
    return dict(p.labels or {}) if p is not None else {}


def _stretch(atom: str) -> tuple[float, bool, float, bool] | None:
    """A stretch of numbers as the table checks name it (decide.checks): 7, 1..6, (0.5..1), > 14, < 0; with whether
    each end is in it. None for one that is not numbers."""
    def num(s: str) -> float | None:
        try:
            return float(s)
        except ValueError:
            return None

    if atom.startswith(("> ", "< ")):
        n = num(atom[2:])
        return None if n is None else (n, False, math.inf, False) if atom[0] == ">" else (-math.inf, False, n, False)
    low, dots, high = atom.strip("()").partition("..")
    a, b = num(low), num(high) if dots else num(low)
    if a is None or b is None:
        return None
    shut = not atom.startswith("(")
    return a, shut, b, shut


def _said_stretch(s: tuple[float, bool, float, bool], unit: str) -> str:
    lo, lo_in, hi, hi_in = s
    n = lambda v: f"{int(v):,}" if float(v).is_integer() else f"{v:,}"  # noqa: E731
    if lo == -math.inf:
        return "모든 값" if hi == math.inf else f"{n(hi)}{unit} {'이하' if hi_in else '미만'}"
    if hi == math.inf:
        return f"{n(lo)}{unit} {'이상' if lo_in else '초과'}"
    return f"{n(lo)}{unit}" if lo == hi else f"{n(lo)}~{n(hi)}{unit}"


def _atoms_words(atoms: list[str], unit: str, labels: dict, whole: bool) -> list[str]:
    """The stretches of an input's values in words; numbers that run on into each other read as one (0, 1..6, 7 is
    0~7, 50000 and > 50000 is 50,000 이상)."""
    said = {"null": "값 없음", "true": WORDS[True], "false": WORDS[False], "any value": "모든 값", "any other value": "그 밖의 값"}
    out: list[Any] = []
    for atom in atoms:
        s = _stretch(atom)
        last = out[-1] if out and isinstance(out[-1], tuple) else None
        if s is not None and last is not None and (last[2] == s[0] and (last[3] or s[1])
                                                   or whole and last[3] and s[1] and s[0] == last[2] + 1):
            out[-1] = (last[0], last[1], s[2], s[3])
        elif s is not None:
            out.append(s)
        elif atom in said:
            out.append(said[atom])
        elif len(atom) >= 2 and atom[0] == atom[-1] == '"':
            out.append(str(labels.get(atom[1:-1], atom[1:-1])))
        else:
            out.append(atom)
    return [_said_stretch(x, unit) if isinstance(x, tuple) else x for x in out]


def where_words(onto: Ontology, table: DecisionTable, where: dict[str, str]) -> str:
    """Where a table check found something (an input and the stretches of its values), in people's words."""
    out = []
    for name, atoms in where.items():
        if name not in table.inputs:
            out.append(f"{name} {atoms}")
            continue
        src = table.inputs[name].source
        whole = table.inputs[name].type == "integer" or "count" in src or "days_since" in src
        said = _atoms_words(atoms.split(" | "), unit_of(onto, table, name).strip(), labels_of(onto, table, name), whole)
        out.append(f"{input_label(onto, table, name)} {', '.join(said)}")
    return " · ".join(out) or "모든 경우"


def rule_sentence(onto: Ontology, table: DecisionTable, rule: DecisionRule) -> str:
    """One rule as a sentence: it is how a rule is found by a question, and what a person reads."""
    named = table.named
    conditions = []
    for name, cell in rule.when.items():
        if name not in table.inputs:
            continue
        said = cell_words(cell, named, unit=unit_of(onto, table, name), labels=labels_of(onto, table, name))
        if said != "-":
            conditions.append(f"{input_label(onto, table, name)} {said}")
    gives = {k: resolve(v, named) for k, v in rule.then.items()}  # a reason says the value in force (`{@name}`)
    outcome = " ".join(str(v) for v in gives.values() if isinstance(v, str)) or \
        ", ".join(f"{k} {_value(v, '', {})}" for k, v in gives.items())
    head = table.label or table.name
    return f"{head}: {', '.join(conditions)}인 경우 {outcome}" if conditions else f"{head}: {outcome}"


def verdict(table: DecisionTable, outputs: Any) -> tuple[str, bool]:
    """What a decision gave, in a word, and whether it reads as a yes. An amount is an amount, never a refusal."""
    outs = outputs if isinstance(outputs, dict) else {"result": outputs}
    value = outs.get(next(iter(table.outputs), ""))
    if isinstance(value, bool) or value is None:
        return ("가능", True) if value else ("불가", False)
    return (f"{value:,}" if isinstance(value, (int, float)) else str(value)), True


__all__ = ["cell_of", "cell_parts", "cell_words", "input_label", "labels_of", "reads", "rule_sentence", "unit_of", "verdict",
           "where_words"]
