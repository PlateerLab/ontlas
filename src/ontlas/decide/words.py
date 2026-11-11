"""A decision table in people's words: what an input is called, what a cell asks, what a rule says."""
from __future__ import annotations

from typing import Any

from ontlas.check import _find_prop
from ontlas.decide.cells import Any_, CellError, Compare, IsNull, OneOf, Range, parse_test
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
    outcome = " ".join(str(v) for v in rule.then.values() if isinstance(v, str)) or \
        ", ".join(f"{k} {_value(v, '', {})}" for k, v in rule.then.items())
    head = table.label or table.name
    return f"{head}: {', '.join(conditions)}인 경우 {outcome}" if conditions else f"{head}: {outcome}"


def verdict(table: DecisionTable, outputs: Any) -> tuple[str, bool]:
    """What a decision gave, in a word, and whether it reads as a yes. An amount is an amount, never a refusal."""
    outs = outputs if isinstance(outputs, dict) else {"result": outputs}
    value = outs.get(next(iter(table.outputs), ""))
    if isinstance(value, bool) or value is None:
        return ("가능", True) if value else ("불가", False)
    return (f"{value:,}" if isinstance(value, (int, float)) else str(value)), True


__all__ = ["cell_of", "cell_parts", "cell_words", "input_label", "labels_of", "reads", "rule_sentence", "unit_of", "verdict"]
