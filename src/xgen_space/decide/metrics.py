"""Metrics: a number with what it means, kept as module content and answered with its meaning attached.

    metrics:
      late_rate:
        label: Late rate
        owner: Merchandising
        unit: "%"
        scale: 100
        formula: {match: {l: Line}, where: {eq: [l.status, LATE]}, value: {count: l}}
        denominator: {where: {in: [l.status, [ON_TIME, LATE]]}, value: {count: l}, label: delivered lines}
        time: {property: l.delivered_on, basis: the day the line was delivered}

`formula` and `denominator` are queries that return one value; a denominator takes the formula's match and edges unless
it gives its own, and its own time property with `time`. A window bounds both: `from` inclusive, `to` exclusive.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_space.ir import AGGS, IRError, Query
from xgen_space.model import Metric
from xgen_space.roles import AccessDenied


class MetricError(ValueError):
    """The metric cannot be answered as asked."""


@dataclass
class MetricAnswer:
    metric: str
    value: Any
    label: str = ""
    description: str = ""
    unit: str = ""
    owner: str = ""
    formula: str = ""        # how the number is made, in one line
    numerator: Any = None
    denominator: Any = None
    denominator_label: str = ""
    time_basis: str = ""
    period: dict[str, Any] = field(default_factory=dict)  # the window asked for: from inclusive, to exclusive
    queries: dict[str, str] = field(default_factory=dict)  # the query each part ran, with its values shown
    version: str = ""
    cite: str = ""
    backend: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _aggregate(part: dict) -> str:
    fn = next((f for f in AGGS if f in (part.get("value") or {})), "")
    return f"{fn}({part['value'][fn]})" if fn else ""


def formula_text(m: Metric) -> str:
    text = _aggregate(m.formula)
    if m.denominator:
        text += f" / {_aggregate(m.denominator)}"
    return text + (f" x {m.scale:g}" if m.scale != 1 else "")


def _query(part: dict, base: dict, time_ref: str, since: bool, until: bool) -> Query:
    where = [part["where"]] if part.get("where") else []
    if time_ref and since:
        where.append({"gte": [time_ref, {"param": "from"}]})
    if time_ref and until:
        where.append({"lt": [time_ref, {"param": "to"}]})
    d = {"match": part.get("match") or base.get("match"), "edges": part.get("edges") or base.get("edges") or [],
         "return": [{**part.get("value", {}), "as": "value"}]}
    if where:
        d["where"] = where[0] if len(where) == 1 else {"and": where}
    return Query.from_dict(d)


def metric_queries(m: Metric, *, since: bool = False, until: bool = False) -> dict[str, Query]:
    """What the metric compiles to: {formula: query, denominator: query}. `since` and `until` add the window, whose
    values are the parameters `from` and `to`."""
    time_ref = str(m.time.get("property", ""))
    out = {"formula": _query(m.formula, m.formula, time_ref, since, until)}
    if m.denominator:
        out["denominator"] = _query(m.denominator, m.formula, str(m.denominator.get("time") or time_ref), since, until)
    return out


def metric_issues(o, m: Metric) -> list[str]:
    from xgen_space.check import check

    out = []
    if not m.owner:
        out.append("needs an owner: who answers for what it means")
    if not m.time.get("basis"):
        out.append("needs time: {basis, property}: what time the number counts by, in words")
    if not m.formula:
        return [*out, "needs a formula"]
    unread = [name for part, name in ((m.formula, "formula"), (m.denominator, "denominator"))
              if part and not _aggregate(part)]
    if unread:
        return [*out, *(f"{name}: value takes one of {', '.join(AGGS)}" for name in unread)]
    try:
        queries = metric_queries(m, since=bool(m.time.get("property")))
    except (IRError, KeyError, TypeError) as e:
        return [*out, f"cannot read it as a query: {e}"]
    for name, q in queries.items():
        res = check(q, o)
        out += [f"{name}: {i}" for i in res.issues]
        out += [f"{name}: parameter '{p}' is not declared" for p in res.param_types if p not in (*m.params, "from", "to")]
        if m.time.get("property") and res.ok and res.param_types.get("from") not in ("date", "datetime"):
            out.append(f"{name}: time property is {res.param_types.get('from')}, not a date or datetime")
    return out


def _value(res) -> Any:
    if res.masked:
        raise AccessDenied("this role sees the value masked, so the metric cannot be answered for it")
    return res.rows[0][0] if res.rows else None


def answer_metric(studio, name: str, params: dict | None = None, *, since: Any = None, until: Any = None,
                  backend: str | None = None, role: str | None = None, principal: dict | None = None) -> MetricAnswer:
    """Run a metric and return the number with its meaning: a reader of the answer needs nothing else to read it."""
    m = studio.onto.metrics.get(name)
    if m is None:
        raise KeyError(f"unknown metric '{name}'")
    if role and not studio.onto.roles[role].can("run", name):
        raise AccessDenied(f"role {role} may not run metric '{name}'")
    if (since or until) and not m.time.get("property"):
        raise MetricError(f"{name} has no time property, so it takes no window")
    values = {**(params or {}), **({"from": since} if since else {}), **({"to": until} if until else {})}
    parts: dict[str, Any] = {}
    shown: dict[str, str] = {}
    used = ""
    for part, q in metric_queries(m, since=bool(since), until=bool(until)).items():
        res = studio.run(q, values, backend=backend, role=role, principal=principal)
        parts[part] = _value(res)
        shown[part] = res.compiled.preview({**values, **_principal(role, principal)})
        used = res.backend
    numerator, denominator = parts["formula"], parts.get("denominator")
    notes = []
    if m.denominator and not denominator:
        notes.append("the denominator is 0 or empty, so there is no value")
    if m.time.get("property") and not (since or until):
        notes.append("no window was given, so this counts all time")
    value = None
    if numerator is not None and (denominator or not m.denominator):
        value = float(numerator) / (float(denominator) if m.denominator else 1) * m.scale
    period = {k: v for k, v in (("from", since), ("to", until)) if v}
    return MetricAnswer(name, value, m.label, m.description, m.unit, m.owner, formula_text(m), numerator, denominator,
                        str(m.denominator.get("label", "")), str(m.time.get("basis", "")), period, shown,
                        studio.version_of(f"metric:{name}"), m.cite, used, notes)


def _principal(role: str | None, principal: dict | None) -> dict:
    return {f"principal__{k}": v for k, v in (principal or {}).items()} if role else {}


def dictionary(onto) -> list[dict]:
    """Every metric as a person reads it, without running one."""
    return [{"metric": m.name, "label": m.label, "description": m.description, "unit": m.unit, "owner": m.owner,
             "formula": formula_text(m), "denominator": str(m.denominator.get("label", "")),
             "time_basis": str(m.time.get("basis", "")), "cite": m.cite} for m in onto.metrics.values()]
