"""Binding suggestions: the tables a person brings, matched onto a standard definition instead of becoming new types.

For each standard object type the tables are scored by name (words, labels, aligned vocabulary, romanized Korean,
character pairs) and by how well their columns carry its properties (name, type, allowed values, the key). The best
pairs are kept one to one; each column match keeps its score and the reason. Relations come from the relations the
draft found between the matched tables. A person confirms or changes every match; `binding()` then writes the module
that binds the standard to the tables: columns, joins, and what the standard has that the tables do not.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_data_studio.check import _find_prop, all_props, is_a
from xgen_data_studio.modules import SECTIONS, Module, Requirement

OBJECT_MIN = 0.35
COLUMN_MIN = 0.5
_COMPAT = [{"string", "enum"}, {"integer", "decimal"}, {"date", "datetime"}, {"boolean"}]


def _split(text: str) -> list[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    return [w for w in re.split(r"[^0-9A-Za-z가-힣]+", text.lower()) if w]


def _tokens(text: str) -> set[str]:
    from xgen_data_studio.draft import romanize, singular

    out = set()
    for w in _split(text):
        out.add(singular(w))
        if re.search(r"[가-힣]", w):
            out.add(romanize(w))
    return out


def _pairs(text: str) -> set[str]:
    s = re.sub(r"[^0-9a-z가-힣]", "", (text or "").lower())
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s} if s else set()


def similarity(a: list[str], b: list[str]) -> tuple[float, str]:
    """The best match between any name of one side and any of the other: equal, shared words, shared pairs."""
    best, why = 0.0, ""
    for x in a:
        for y in b:
            if not x or not y:
                continue
            nx, ny = re.sub(r"[^0-9a-z가-힣]", "", x.lower()), re.sub(r"[^0-9a-z가-힣]", "", y.lower())
            if nx and nx == ny:
                return 1.0, f"'{x}' = '{y}'"
            tx, ty = _tokens(x), _tokens(y)
            if tx and ty:
                j = len(tx & ty) / len(tx | ty)
                if j > best:
                    best, why = j, f"'{x}' ~ '{y}' (같은 단어 {', '.join(sorted(tx & ty))})"
            px, py = _pairs(x), _pairs(y)
            if px and py:
                d = 2 * len(px & py) / (len(px) + len(py))
                if d * 0.9 > best:
                    best, why = d * 0.9, f"'{x}' ~ '{y}' (글자 {round(d * 100)}% 겹침)"
    return best, why


def _aligned_names(iris: list[str]) -> list[str]:
    return [re.split(r"[/#]", i.rstrip("/#"))[-1] for i in iris]


@dataclass
class ColumnMatch:
    property: str
    column: str
    score: float
    why: str


@dataclass
class ObjectMatch:
    object: str
    table: str
    score: float
    why: str
    columns: list[ColumnMatch] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # standard properties no column carries
    extra: list[str] = field(default_factory=list)  # columns the standard has no property for


@dataclass
class Suggestion:
    standard: list[str]
    objects: list[ObjectMatch]
    links: dict[str, dict]  # standard link -> {"on": {...}} or {"via": {...}}, with "why"
    unmatched_tables: list[str]
    unbound_objects: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _candidates(onto) -> list[str]:
    parents = {o.parent for o in onto.objects.values() if o.parent}
    return [o.name for o in onto.objects.values() if o.name not in parents and o.name not in onto.identities]


def _names_of(onto, type_name: str) -> list[str]:
    o = onto.objects[type_name]
    return [o.name, o.label, *_aligned_names(o.aligned)]


def _prop_names(onto, type_name: str, prop: str) -> list[str]:
    p = _find_prop(onto, type_name, prop)
    return [prop, p.label, *_aligned_names(p.aligned)] if p else [prop]


def _column_score(onto, type_name: str, prop: str, col, planned, key: str, table_key: str) -> tuple[float, str]:
    p = _find_prop(onto, type_name, prop)
    name, why = similarity(_prop_names(onto, type_name, prop), [col.column, col.name, col.label])
    score, notes = 0.6 * name, [why] if why else []
    ptype = p.type if p else "string"
    if ptype == col.type or any(ptype in g and col.type in g for g in _COMPAT):
        score += 0.2
        notes.append(f"타입 {col.type}")
    if ptype == "enum" and p.values and col.values:
        a, b = set(p.values), set(col.values)
        overlap = len(a & b) / len(a | b)
        score += 0.2 * overlap
        if overlap:
            notes.append(f"허용값 {round(overlap * 100)}% 겹침")
    elif prop == key and col.name == table_key:
        score += 0.2
        notes.append("둘 다 키")
    return min(score, 1.0), ", ".join(notes)


def _match_columns(onto, type_name: str, planned) -> tuple[list[ColumnMatch], list[str], list[str], float]:
    obj = onto.objects[type_name]
    props = [p for p in all_props(onto, type_name) if not _find_prop(onto, type_name, p).expr]
    pairs = []
    for prop in props:
        for col in planned.properties:
            s, why = _column_score(onto, type_name, prop, col, planned, obj.key, planned.key)
            pairs.append((s, prop, col, why))
    pairs.sort(key=lambda x: -x[0])
    used_p, used_c, matches = set(), set(), []
    for s, prop, col, why in pairs:
        if s < COLUMN_MIN or prop in used_p or col.name in used_c:
            continue
        used_p.add(prop)
        used_c.add(col.name)
        matches.append(ColumnMatch(prop, col.column, round(s, 3), why))
    # an inherited property still without a column, of a type exactly one column has, takes it (an agreement's date
    # is the order's date). The type's own properties match by name or stay missing; an ancestor's key is the own key.
    for prop in props:
        if prop in used_p or prop == obj.key or _owner(onto, type_name, prop) == type_name \
                or _inherited_key(onto, type_name, prop):
            continue
        p = _find_prop(onto, type_name, prop)
        same = [c for c in planned.properties if c.type == p.type and c.name != planned.key]
        if len(same) == 1:
            used_p.add(prop)
            matches.append(ColumnMatch(prop, same[0].column, round(COLUMN_MIN, 3),
                                       f"{p.type} 컬럼이 {same[0].column} 하나뿐"))
    key_bound = any(m.property == obj.key for m in matches)
    if not key_bound:
        matches.append(ColumnMatch(obj.key, next(c.column for c in planned.properties if c.name == planned.key),
                                   0.4, "표준 키를 테이블의 키에 연결"))
        used_p.add(obj.key)
    missing = [p for p in props if p not in used_p and not _inherited_key(onto, type_name, p)]
    extra = [c.column for c in planned.properties if c.column not in {m.column for m in matches}]
    coverage = sum(m.score for m in matches) / max(len(props), 1)
    return matches, missing, extra, coverage


def _inherited_key(onto, type_name: str, prop: str) -> bool:
    t = onto.objects[type_name].parent
    while t and t in onto.objects:
        if onto.objects[t].key == prop:
            return True  # an ancestor's key reads the type's own key
        t = onto.objects[t].parent
    return False


def suggest(draft, onto, standard: list[str]) -> Suggestion:
    """Match the draft's tables onto the standard's object types, one to one, best first."""
    scored = []
    for t in _candidates(onto):
        for po in draft.objects:
            name, why = similarity(_names_of(onto, t), [po.table, po.label, po.name])
            cols, missing, extra, cover = _match_columns(onto, t, po)
            score = 0.4 * name + 0.6 * cover
            scored.append((score, t, po, why, cols, missing, extra))
    scored.sort(key=lambda x: -x[0])
    taken_t, taken_o, matches = set(), set(), []
    for score, t, po, why, cols, missing, extra in scored:
        if score < OBJECT_MIN or t in taken_t or po.table in taken_o:
            continue
        taken_t.add(t)
        taken_o.add(po.table)
        reason = "; ".join(x for x in (why, f"컬럼 {len(cols)}개 대응") if x)
        matches.append(ObjectMatch(t, po.table, round(score, 3), reason, cols, missing, extra))
    links = _links(draft, onto, matches)
    unbound = [t for t in _candidates(onto) if t not in taken_t]
    return Suggestion(list(standard), matches, links, [o.table for o in draft.objects if o.table not in taken_o],
                      unbound)


def _links(draft, onto, matches: list[ObjectMatch]) -> dict[str, dict]:
    by_obj = {m.object: m for m in matches}
    # a column two properties share (an inherited date) joins as the first, best matched one
    col_of = {m.object: {c.column: c.property for c in reversed(m.columns)} for m in matches}
    table_obj = {m.table: m.object for m in matches}
    out: dict[str, dict] = {}
    for lk in onto.links.values():
        s, t = by_obj.get(lk.source), by_obj.get(lk.target)
        if s is None or t is None:
            continue
        for dl in draft.links:
            src = next((o for o in draft.objects if o.name == dl.source), None)
            dst = next((o for o in draft.objects if o.name == dl.target), None)
            if src is None or dst is None:
                continue
            a, b = table_obj.get(src.table), table_obj.get(dst.table)
            if dl.via and {a, b} == {lk.source, lk.target}:
                fwd = a == lk.source
                out[lk.name] = {"via": {"table": dl.via[0], "source": dl.via[1] if fwd else dl.via[2],
                                        "target": dl.via[2] if fwd else dl.via[1]},
                                "why": f"{dl.via[0]} 연결 테이블"}
                break
            if not dl.on:
                continue
            fk = next(p.column for p in src.properties if p.name == dl.on[0])
            if a == lk.source and b == lk.target and fk in col_of[lk.source]:
                out[lk.name] = {"on": {col_of[lk.source][fk]: onto.objects[lk.target].key},
                                "why": f"{src.table}.{fk} → {dst.table} 키"}
                break
            if a == lk.target and b == lk.source and fk in col_of[lk.target]:
                out[lk.name] = {"on": {onto.objects[lk.source].key: col_of[lk.target][fk]},
                                "why": f"{src.table}.{fk} → {dst.table} 키"}
                break
    return out


def _reaches_unbound(onto, type_name: str, prop: str, kept: set[str], seen: frozenset = frozenset()) -> bool:
    from xgen_data_studio import expr as ex

    p = _find_prop(onto, type_name, prop)
    if p is None or not p.expr or (type_name, prop) in seen:
        return False
    seen = seen | {(type_name, prop)}
    for node in ex.walk(ex.parse_expr(p.expr)):
        if isinstance(node, ex.Prop) and _reaches_unbound(onto, type_name, node.name, kept, seen):
            return True
        if isinstance(node, ex.Agg):
            try:
                steps, inner = ex.resolve_agg(onto, type_name, node)
            except ex.ExprError:
                return True
            if any(not (st.type in kept or any(is_a(onto, k, st.type) for k in kept)) for st in steps):
                return True
            if inner and _reaches_unbound(onto, steps[-1].type, inner, kept, seen):
                return True
    return False


def _owner(onto, type_name: str, prop: str) -> str:
    t = type_name
    while t and t in onto.objects:
        if prop in onto.objects[t].properties:
            return t
        t = onto.objects[t].parent
    return type_name


def binding(s: Suggestion, onto, *, name: str, label: str = "", edits: dict | None = None,
            base: list[Module] | None = None) -> Module:
    """The binding module for the confirmed matches. edits: {objects: {Type: table|None},
    columns: {"Type.prop": column|None}} change or drop a suggestion before it is written. With `base` (the
    standard's modules), what the removals leave broken (a query on a removed property, a computed property built
    from one) is taken out too, so the standard composes over the tables."""
    m = _binding(s, onto, name=name, label=label, edits=edits)
    if base is None:
        return m
    from xgen_data_studio.modules import compose

    for _ in range(30):
        issues = compose([*base, m]).issues
        if not issues:
            break
        progress = False
        for issue in issues:
            head = issue.split(":", 1)[0]
            kind, _, ident = head.partition(" ")
            section = {"query": "queries", "question": "questions", "decision": "decisions",
                       "action": "actions"}.get(kind)
            if kind == "decision":
                ident = ident.split(".", 1)[0]  # an input's or a rule's issue: the table cannot feed the decision
            if section and ident not in m.remove.get(section, []):
                m.remove.setdefault(section, []).append(ident)
                progress = True
            elif head in onto.objects and "state property" in issue:  # the tables have no state column
                if head not in m.remove.get("states", []):
                    m.remove.setdefault("states", []).append(head)
                    progress = True
            elif "." in head and " " not in head:
                t, prop = head.split(".", 1)
                props = m.remove.setdefault("properties", {}).setdefault(t, [])
                if prop not in props:
                    props.append(prop)
                    progress = True
        if not progress:
            break
    gone = set(m.remove.get("queries", [])) | set(m.remove.get("decisions", []))
    for q in [q.id for q in onto.questions if q.query in gone or q.decision in gone]:
        if q not in m.remove.get("questions", []):
            m.remove.setdefault("questions", []).append(q)
    return m


def _binding(s: Suggestion, onto, *, name: str, label: str = "", edits: dict | None = None) -> Module:
    edits = edits or {}
    objects_edit, columns_edit = edits.get("objects") or {}, edits.get("columns") or {}
    bind_objects, removed_props, kept = {}, [], set()
    missing: dict[tuple[str, str], set[str]] = {}
    for m in s.objects:
        table = objects_edit.get(m.object, m.table)
        if table is None:
            continue
        kept.add(m.object)
        cols = {c.property: c.column for c in m.columns}
        for ref, col in columns_edit.items():
            t, _, p = ref.partition(".")
            if t == m.object:
                if col is None:
                    cols.pop(p, None)
                else:
                    cols[p] = col
        bind_objects[m.object] = {"table": table, "columns": dict(cols)}
        for p in m.missing:
            if p not in cols:
                missing.setdefault((_owner(onto, m.object, p), p), set()).add(m.object)
    # a computed property that follows a relation to a type no table is bound to cannot be computed here
    for t in sorted(kept):
        for p in all_props(onto, t):
            prop = _find_prop(onto, t, p)
            if prop.expr and _reaches_unbound(onto, t, p, kept):
                missing.setdefault((_owner(onto, t, p), p), set()).add(t)
    # a property no bound table carries goes; an inherited one only when no bound subtype carries it
    for (owner, p), lacking in sorted(missing.items()):
        if p == onto.objects[owner].key:
            continue
        carriers = {k for k in kept if is_a(onto, k, owner)}
        if carriers <= lacking:
            removed_props.append(f"{owner}.{p}")
    links = {k: {kk: vv for kk, vv in v.items() if kk != "why"} for k, v in s.links.items()
             if onto.links[k].source in kept and onto.links[k].target in kept}
    def bound(t: str) -> bool:  # bound itself, or a concept one of the bound types specialises
        return t in kept or any(is_a(onto, k, t) for k in kept)

    gone_queries = [q.name for q in onto.queries.values()
                    if any(t in onto.objects and not bound(t) for t in (q.query.get("match") or {}).values())]
    gone_questions = [q.id for q in onto.questions if q.query in gone_queries]
    remove: dict[str, Any] = {}
    if removed_props:
        by_type: dict[str, list[str]] = {}
        for ref in removed_props:
            t, _, prop = ref.partition(".")
            by_type.setdefault(t, []).append(prop)
        remove["properties"] = by_type
    if gone_queries:
        remove["queries"] = gone_queries
    if gone_questions:
        remove["questions"] = gone_questions
    return Module(name=name, version="0.1.0", kind="binding", label=label or name,
                  description="표준 정의를 업로드한 테이블에 연결합니다(바인딩 제안에서 확정).",
                  requires=[Requirement(x) for x in s.standard],
                  body={**{x: {} for x in SECTIONS}, "questions": [], "exclusive": []},
                  extend={"objects": bind_objects, "links": links}, remove=remove)
