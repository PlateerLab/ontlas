"""A decision table drafted from past outcomes: a shallow decision tree over the columns a person picks.

The result column (an allowed-value or true/false column) is what was decided; the inputs are columns of the same
table or of a table one relation away. Each leaf of the tree becomes a rule with how many past cases it covers and
how many it gets right, and a five-fold cross-validation says how well the table decides cases it was not drawn
from. A person reads, edits and approves the table like any other; nothing here decides on its own.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

NUMBER = ("integer", "decimal")


class InduceError(ValueError):
    """The table cannot be drawn: the message says what is missing."""


@dataclass
class Feature:
    name: str  # decision input name
    type: str  # enum | boolean | integer | decimal | string
    column: str  # in the query that reads the cases
    property: str
    path: list[str] = field(default_factory=list)


@dataclass
class _Node:
    rows: list[int]
    test: tuple | None = None  # (feature index, kind, value): kind eq | le | true
    yes: _Node | None = None
    no: _Node | None = None


def _gini(labels: list[Any]) -> float:
    n = len(labels)
    if not n:
        return 0.0
    counts: dict[Any, int] = {}
    for x in labels:
        counts[x] = counts.get(x, 0) + 1
    return 1.0 - sum((c / n) ** 2 for c in counts.values())


def _majority(labels: list[Any]) -> tuple[Any, int]:
    counts: dict[Any, int] = {}
    for x in labels:
        counts[x] = counts.get(x, 0) + 1
    best = max(counts.items(), key=lambda kv: (kv[1], str(kv[0])))
    return best


def _splits(feature: Feature, values: list[Any]) -> list[tuple]:
    present = sorted({v for v in values if v is not None}, key=lambda v: (str(type(v)), v))
    if feature.type in NUMBER:
        nums = sorted({float(v) for v in present})
        return [("le", (a + b) / 2) for a, b in zip(nums, nums[1:])]
    if feature.type == "boolean":
        return [("true", True)] if len(present) > 1 else []
    return [("eq", v) for v in present] if len(present) > 1 else []


def _passes(kind: str, value: Any, v: Any) -> bool | None:
    if v is None:
        return None
    if kind == "le":
        return float(v) <= value
    if kind == "true":
        return bool(v) is True
    return v == value


def _grow(rows: list[int], X: list[list[Any]], y: list[Any], features: list[Feature], used: frozenset, depth: int,
          max_depth: int, min_leaf: int) -> _Node:
    node = _Node(rows)
    labels = [y[i] for i in rows]
    if depth >= max_depth or len(set(labels)) <= 1 or len(rows) < 2 * min_leaf:
        return node
    base, best = _gini(labels), None
    for fi, f in enumerate(features):
        if fi in used:
            continue
        for kind, value in _splits(f, [X[i][fi] for i in rows]):
            yes = [i for i in rows if _passes(kind, value, X[i][fi]) is True]
            no = [i for i in rows if _passes(kind, value, X[i][fi]) is False]
            if len(yes) < min_leaf or len(no) < min_leaf:
                continue
            gain = base - (len(yes) * _gini([y[i] for i in yes]) + len(no) * _gini([y[i] for i in no])) / len(rows)
            if gain > 1e-9 and (best is None or gain > best[0]):
                best = (gain, fi, kind, value, yes, no)
    if best is None:
        return node
    _, fi, kind, value, yes, no = best
    node.test = (fi, kind, value)
    node.yes = _grow(yes, X, y, features, used | {fi}, depth + 1, max_depth, min_leaf)
    node.no = _grow(no, X, y, features, used | {fi}, depth + 1, max_depth, min_leaf)
    return node


def _number(v: float, t: str) -> str:
    if t == "integer":
        return str(math.floor(v))  # x <= 7.5 for whole numbers is x <= 7
    return f"{v:.6g}"


def _cell(f: Feature, kind: str, value: Any, yes: bool) -> str:
    if kind == "le":
        n = _number(value, f.type)
        return f"<= {n}" if yes else f"> {n}"
    if kind == "true":
        return "true" if yes else "false"
    lit = '"' + str(value).replace('"', '\\"') + '"'
    return lit if yes else f"!= {lit}"


def _leaves(node: _Node, path: list[tuple[int, str, Any, bool]]):
    if node.test is None:
        yield node, path
        return
    fi, kind, value = node.test
    yield from _leaves(node.yes, path + [(fi, kind, value, True)])
    yield from _leaves(node.no, path + [(fi, kind, value, False)])


def _predict(node: _Node, x: list[Any], y: list[Any], default: Any) -> Any:
    while node.test is not None:
        fi, kind, value = node.test
        hit = _passes(kind, value, x[fi])
        if hit is None:
            return default
        node = node.yes if hit else node.no
    return _majority([y[i] for i in node.rows])[0] if node.rows else default


def tree(X: list[list[Any]], y: list[Any], features: list[Feature], *, max_depth: int = 3,
         min_leaf: int = 2) -> _Node:
    return _grow(list(range(len(y))), X, y, features, frozenset(), 0, max_depth, min_leaf)


def cross_validate(X, y, features, *, folds: int = 5, **kw) -> float | None:
    n = len(y)
    if n < 2 * folds:
        return None
    hits = 0
    for k in range(folds):
        test = [i for i in range(n) if i % folds == k]
        train = [i for i in range(n) if i % folds != k]
        t = tree([X[i] for i in train], [y[i] for i in train], features, **kw)
        default = _majority([y[i] for i in train])[0]
        hits += sum(_predict(t, X[i], [y[j] for j in train], default) == y[i] for i in test)
    return hits / n


def rules_of(root: _Node, X, y, features: list[Feature], output: str, lang: str = "ko") -> list[dict]:
    out = []
    for i, (leaf, path) in enumerate(_leaves(root, [])):
        labels = [y[r] for r in leaf.rows]
        value, right = _majority(labels)
        when = {features[fi].name: _cell(features[fi], kind, v, yes) for fi, kind, v, yes in path}
        note = (f"지난 {len(labels)}건 중 {right}건 일치" if lang == "ko" else f"{right} of {len(labels)} past cases")
        out.append({"id": f"learned-{i + 1}", "when": when, "then": {output: value}, "note": note,
                    "cases": len(labels), "right": right})
    value, _ = _majority(y)
    out.append({"id": "otherwise", "when": {}, "then": {output: value},
                "note": "어느 규칙에도 맞지 않는 값(빈 값 포함)" if lang == "ko" else "values no rule covers (empty too)",
                "cases": 0, "right": 0})
    return out


def _plain(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    return v


def induce(backend, onto, target: str, inputs: list[str], *, name: str = "", label: str = "", max_depth: int = 3,
           min_leaf: int = 2, lang: str = "ko") -> dict[str, Any]:
    """Draw a decision table for `target` ("Type.prop") from the inputs ("prop" of the type, or "link.prop").

    Returns {"decision": the table as a module would hold it, "report": cases, accuracy, cross-validated accuracy}.
    """
    from ontlas.check import find_prop
    from ontlas.expr import ExprError, follow
    from ontlas.ir import Column, Edge, Query, Ref

    type_name, _, out_prop = target.partition(".")
    if type_name not in onto.objects or not out_prop:
        raise InduceError(f"'{target}' is not Type.property")
    out = find_prop(onto, type_name, out_prop)
    if out.type not in ("enum", "boolean", "string"):
        raise InduceError(f"{target} is {out.type}; the result has to be an allowed-value or true/false property")
    if not inputs:
        raise InduceError("pick at least one input")
    nodes, edges, cols = {"x": type_name}, [], [Column(Ref("x", out_prop), "__result")]
    features: list[Feature] = []
    aliases: dict[str, str] = {}
    for spec in inputs:
        path, _, prop = spec.rpartition(".")
        alias = "x"
        steps = []
        if path:
            try:
                steps = follow(onto, type_name, tuple(path.split(".")))
            except ExprError as e:
                raise InduceError(str(e)) from None
            if len(steps) != 1:
                raise InduceError(f"{spec}: inputs reach one relation away at most")
            lk = onto.links[steps[0].link]
            if lk.cardinality not in ("many_to_one", "one_to_one") or not steps[0].forward:
                raise InduceError(f"{spec}: '{path}' reaches many {steps[0].type}; pick a relation to one")
            alias = aliases.setdefault(path, f"r{len(aliases) + 1}")
            if alias not in nodes:
                nodes[alias] = steps[0].type
                edges.append(Edge("x", steps[0].link, alias, optional=True))
        p = find_prop(onto, nodes[alias], prop)
        if p.type not in ("enum", "boolean", "integer", "decimal", "string"):
            raise InduceError(f"{spec} is {p.type}; inputs are allowed values, true/false or numbers")
        fname = prop if not path else f"{path.replace('.', '_')}_{prop}"
        if spec == target or (not path and prop == out_prop):
            raise InduceError(f"{spec} is the result itself")
        col = f"f{len(features)}"
        cols.append(Column(Ref(alias, prop), col))
        features.append(Feature(fname, p.type, col, prop, path.split(".") if path else []))
    q = Query(nodes=nodes, edges=edges, columns=cols)
    compiled = backend.compiler(onto).compile(q)
    rows = backend.execute(compiled).rows
    from ontlas.values import from_source

    X, y = [], []
    for r in rows:
        if r[0] is None:
            continue
        y.append(from_source(r[0], "boolean" if out.type == "boolean" else "string"))
        X.append([None if v is None else _plain(from_source(v, f.type if f.type != "enum" else "string"))
                  for v, f in zip(r[1:], features)])
    if len(y) < 2 * min_leaf:
        raise InduceError(f"{len(y)} past cases with a result; at least {2 * min_leaf} are needed")
    root = tree(X, y, features, max_depth=max_depth, min_leaf=min_leaf)
    output = out_prop
    rules = rules_of(root, X, y, features, output, lang)
    default = _majority(y)[0]
    fitted = sum(_predict(root, x, y, default) == t for x, t in zip(X, y)) / len(y)
    cv = cross_validate(X, y, features, max_depth=max_depth, min_leaf=min_leaf)
    decision = {
        "label": label or (f"{onto.objects[type_name].label or type_name} {out.label or out_prop} 판정" if lang == "ko"
                           else f"{out.label or out_prop} of {type_name}"),
        "target": type_name, "hit_policy": "first",
        "inputs": {f.name: {"type": "string" if f.type == "enum" else f.type, "property": f.property,
                            **({"path": f.path} if f.path else {})} for f in features},
        "outputs": {output: "boolean" if out.type == "boolean" else "string"},
        "rules": [{k: v for k, v in r.items() if k not in ("cases", "right")} for r in rules],
    }
    report = {"cases": len(y), "accuracy": fitted, "cross_validated": cv, "rules": len(rules),
              "depth": max_depth, "result": target, "inputs": list(inputs),
              "leaves": [{"id": r["id"], "cases": r["cases"], "right": r["right"]} for r in rules],
              "values": sorted({str(v) for v in y})}
    return {"name": name or f"{type_name[:1].lower()}{type_name[1:]}{out_prop.title().replace('_', '')}",
            "decision": decision, "report": report}
