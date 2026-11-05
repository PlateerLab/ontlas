"""Decision tables held in a code definition: a code group whose reference columns name other code groups.

Two shapes, told apart by where the group's own code is stored:

- a column holds the code (a claim reason): the code decides what its references say (who is at fault, who pays),
  one rule per code;
- no column holds it (a list of what may be done): the references say which values of other columns allow each code,
  and every code that applies is collected (the actions open to an order line in this state).

A reference that names no code group (a number of days, a yes or no) is an output of the first shape and is left out of
the second. Codes not in use are left out.
"""
from __future__ import annotations

import re
from typing import Any

GROUP = re.compile(r"\s*([A-Za-z]{1,6}\d{1,6})")


def _groups_in(defs, o) -> dict[str, str]:
    """code group -> the property of a planned object that holds it."""
    td = defs.table(o.table)
    out: dict[str, str] = {}
    if td is None:
        return out
    for p in o.properties:
        col = td.column(p.column)
        g = defs.code_of(col) if col is not None else None
        if g is not None:
            out.setdefault(g.name, p.name)
    return out


def _cell(values: list[str]) -> str:
    return ", ".join(f'"{v}"' for v in values) if len(values) > 1 else f'"{values[0]}"'


def _split(text: Any) -> list[str]:
    return [x.strip() for x in str(text or "").split(",") if x.strip()]


def _named(ref: str, label: str, used: set[str]) -> str:
    m = GROUP.match(label or "")
    name = m.group(1).lower() if m else ref.lower()
    while name in used:
        name += "_"
    used.add(name)
    return name


def code_tables(objects: list, links: list, defs) -> dict[str, dict]:
    """The decision tables a draft's objects can carry, by name."""
    holds = {o.name: _groups_in(defs, o) for o in objects}
    out: dict[str, dict] = {}
    for g in defs.codes.values():
        refs = getattr(g, "refs", None) or {}
        coded = {k: m.group(1) for k, v in refs.items() if (m := GROUP.match(str(v))) and m.group(1) in defs.codes}
        used = [v for v in g.values if v.get("use", True)]
        if not refs or not used:
            continue
        home = next((o for o in objects if g.name in holds[o.name]), None)
        table = _by_code(g, refs, used, home, holds) if home else _by_state(g, coded, used, objects, links, holds)
        if table:
            out[f"codes_{g.name.lower()}"] = table
    return out


def _by_code(g, refs: dict, used: list[dict], home, holds: dict) -> dict:
    prop, taken = holds[home.name][g.name], set()
    names = {k: _named(k, str(v), taken) for k, v in refs.items()}
    rules = []
    for v in used:
        then = {names[k]: str(x) for k, x in (v.get("refs") or {}).items() if k in names and str(x).strip()}
        if then:
            rules.append({"id": f"c{v['code']}", "when": {prop: f'"{v["code"]}"'}, "then": then,
                          "cite": f"{g.name} {v['code']} {v.get('name', '')}".strip()})
    if not rules:
        return {}
    return {"label": g.label or g.name, "target": home.name, "hit_policy": "first", "cite": g.name,
            "inputs": {prop: {"type": "string", "property": prop}},
            "outputs": {n: "string" for n in names.values()}, "rules": rules, "report": {"from": "codes"}}


def _by_state(g, coded: dict, used: list[dict], objects: list, links: list, holds: dict) -> dict:
    wanted = set(coded.values())
    if not wanted:
        return {}
    by_name = {o.name: o for o in objects}

    def reach(o) -> tuple[int, int]:
        """What the object reads, itself or one relation away, then how central it is: a copy of a status in a report
        table holds as much as the table where the status lives, but little points at it."""
        far = {g for lk in links if lk.source == o.name and lk.on and lk.target in by_name for g in holds[lk.target]}
        return len(wanted & (set(holds[o.name]) | far)), sum(o.name in (lk.source, lk.target) for lk in links)

    home = max(objects, key=reach, default=None)
    if home is None or not wanted & set(holds[home.name]):
        return {}
    inputs: dict[str, dict] = {}
    read: dict[str, str] = {}  # code group -> the input that reads it
    for grp in sorted(wanted):
        if grp in holds[home.name]:
            p = holds[home.name][grp]
            inputs[p] = {"type": "string", "property": p}
            read[grp] = p
            continue
        for lk in links:  # a value one relation away (the product type of an order line)
            if lk.source == home.name and lk.on and lk.target in by_name and grp in holds[lk.target]:
                p = holds[lk.target][grp]
                inputs[p] = {"type": "string", "path": [lk.name], "property": p}
                read[grp] = p
                break
    rules = []
    for v in used:
        allowed: dict[str, list[str]] = {}
        for k, grp in coded.items():  # two references to one group (two stages of one status) allow either
            if grp in read and _split((v.get("refs") or {}).get(k)):
                allowed.setdefault(read[grp], []).extend(_split((v.get("refs") or {}).get(k)))
        if allowed:
            rules.append({"id": f"c{v['code']}", "when": {p: _cell(list(dict.fromkeys(x))) for p, x in allowed.items()},
                          "then": {"code": v["code"], "name": v.get("name", "")},
                          "cite": f"{g.name} {v['code']} {v.get('name', '')}".strip()})
    if not rules:
        return {}
    return {"label": g.label or g.name, "target": home.name, "hit_policy": "collect", "cite": g.name,
            "inputs": inputs, "outputs": {"code": "string", "name": "string"}, "rules": rules,
            "report": {"from": "codes"}}

