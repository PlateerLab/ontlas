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

from xgen_space.check import _find_prop, all_props, is_a
from xgen_space.modules import SECTIONS, Module, Requirement

OBJECT_MIN = 0.35
MASTER = re.compile(r"(기본|마스터)\s|_(BASE|MST|MASTER)$", re.I)  # the table of the thing itself, not of its details
MASTER_BONUS = 0.15
COLUMN_MIN = 0.5
_COMPAT = [{"string", "enum"}, {"integer", "decimal"}, {"date", "datetime"}, {"boolean"}]


def _split(text: str) -> list[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text or "")
    return [w for w in re.split(r"[^0-9A-Za-z가-힣]+", text.lower()) if w]


def _tokens(text: str) -> set[str]:
    from xgen_space.draft import romanize, singular

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
            short, long_ = sorted((nx, ny), key=len)
            if len(short) >= 2 and re.search(r"[가-힣]", short) and short in long_:  # 주문 in 주문기본, 카테고리 in 표준카테고리
                c = 0.7 + 0.25 * len(short) / len(long_)
                if c > best:
                    best, why = c, f"'{x}' ~ '{y}' ('{short}' 포함)"
            tx, ty = _tokens(x), _tokens(y)
            if tx and ty:
                j = len(tx & ty) / len(tx | ty)
                if j > best:
                    best, why = j, f"'{x}' ~ '{y}' (같은 단어 {', '.join(sorted(tx & ty))})"
            px, py = _pairs(x), _pairs(y)
            if px and py:
                d = 2 * len(px & py) / (len(px) + len(py))
                if d * 0.9 > best:
                    best, why = d * 0.9, f"'{x}' ~ '{y}' (이름 유사도 {round(d * 100)}%)"
    return best, why


def _aligned_names(iris: list[str]) -> list[str]:
    return [re.split(r"[/#]", i.rstrip("/#"))[-1] for i in iris]


@dataclass
class ColumnMatch:
    property: str
    column: str
    score: float
    why: str
    columns: list[str] = field(default_factory=list)  # a key or reference read from several columns


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


def aliases(terms: list[dict] | None) -> dict[str, list[str]]:
    """Each name of a glossary entry, with the entry's other names: the words a system uses for what a standard names."""
    out: dict[str, list[str]] = {}
    for t in terms or []:
        names = [str(x) for x in [t.get("term"), *(t.get("synonyms") or [])] if x]
        for n in names:
            key = re.sub(r"\s", "", n).lower()
            out.setdefault(key, []).extend(x for x in names if x != n)
    return out


def _widen(names: list[str], words: dict[str, list[str]]) -> list[str]:
    return names + [x for n in names for x in words.get(re.sub(r"\s", "", n or "").lower(), [])]


def _names_of(onto, type_name: str, words: dict | None = None) -> list[str]:
    o = onto.objects[type_name]
    return _widen([o.name, o.label, *_aligned_names(o.aligned)], words or {})


def _prop_names(onto, type_name: str, prop: str, words: dict | None = None) -> list[str]:
    p = _find_prop(onto, type_name, prop)
    return _widen([prop, p.label, *_aligned_names(p.aligned)] if p else [prop], words or {})


def _column_score(onto, type_name: str, prop: str, col, planned, key: str, table_key: str,
                  words: dict | None = None) -> tuple[float, str]:
    p = _find_prop(onto, type_name, prop)
    name, why = similarity(_prop_names(onto, type_name, prop, words), [col.column, col.name, col.label])
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
            notes.append(f"허용값 일치율 {round(overlap * 100)}%")
    elif prop == key and col.name == table_key:
        score += 0.2
        notes.append("키 일치")
    return min(score, 1.0), ", ".join(notes)


def _match_columns(onto, type_name: str, planned,
                   words: dict | None = None) -> tuple[list[ColumnMatch], list[str], list[str], float]:
    obj = onto.objects[type_name]
    props = [p for p in all_props(onto, type_name) if not _find_prop(onto, type_name, p).expr]
    pairs = []
    for prop in props:
        for col in planned.properties:
            s, why = _column_score(onto, type_name, prop, col, planned, obj.key, planned.key, words)
            pairs.append((s, prop, col, why))
    pairs.sort(key=lambda x: -x[0])
    used_p, used_c, matches = set(), set(), []
    wide = next((c for c in planned.properties if c.name == planned.key and c.columns), None)
    if wide is not None:  # a table keyed by several columns: no one of them identifies a row
        used_p.add(obj.key)
        used_c.add(wide.name)
        matches.append(ColumnMatch(obj.key, wide.column, 0.6, "키 일치", list(wide.columns)))
    for s, prop, col, why in pairs:
        if s < COLUMN_MIN or prop in used_p or col.name in used_c:
            continue
        used_p.add(prop)
        used_c.add(col.name)
        matches.append(ColumnMatch(prop, col.column, round(s, 3), why, list(col.columns)))
    title = _title_of(onto, type_name)
    if title and title not in used_p and planned.title and planned.title not in used_c:
        c = next(x for x in planned.properties if x.name == planned.title)
        used_p.add(title)
        used_c.add(c.name)
        matches.append(ColumnMatch(title, c.column, COLUMN_MIN, "표시 이름 일치"))
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
                                       f"{p.type} 컬럼 후보 {same[0].column} 1개"))
    key_bound = any(m.property == obj.key for m in matches)
    if not key_bound:
        k = next(c for c in planned.properties if c.name == planned.key)
        matches.append(ColumnMatch(obj.key, k.column, 0.4, "표준 키를 테이블의 키에 연결", list(k.columns)))
        used_p.add(obj.key)
    missing = [p for p in props if p not in used_p and not _inherited_key(onto, type_name, p)]
    extra = [", ".join(c.columns) or c.column for c in planned.properties if c.column not in {m.column for m in matches}]
    coverage = sum(m.score for m in matches) / max(len(props), 1)
    return matches, missing, extra, coverage


def _title_of(onto, type_name: str) -> str:
    t = type_name
    while t and t in onto.objects:
        if onto.objects[t].title:
            return onto.objects[t].title
        t = onto.objects[t].parent
    return ""


def _inherited_key(onto, type_name: str, prop: str) -> bool:
    t = onto.objects[type_name].parent
    while t and t in onto.objects:
        if onto.objects[t].key == prop:
            return True  # an ancestor's key reads the type's own key
        t = onto.objects[t].parent
    return False


def suggest(draft, onto, standard: list[str], terms: list[dict] | None = None) -> Suggestion:
    """Match the draft's tables onto the standard's object types, one to one, best first. `terms` (a glossary) says
    which words of the system mean what a standard names."""
    scored = []
    words = aliases(terms)
    for t in _candidates(onto):
        for po in draft.objects:
            name, why = similarity(_names_of(onto, t, words), [po.table, po.label, po.name])
            cols, missing, extra, cover = _match_columns(onto, t, po, words)
            score = 0.4 * name + 0.6 * cover + (MASTER_BONUS if MASTER.search(f"{po.label} {po.table}") else 0)
            scored.append((score, t, po, why, cols, missing, extra))
    scored.sort(key=lambda x: -x[0])
    taken_t, taken_o, matches = set(), set(), []
    for score, t, po, why, cols, missing, extra in scored:
        if score < OBJECT_MIN or t in taken_t or po.table in taken_o:
            continue
        taken_t.add(t)
        taken_o.add(po.table)
        reason = "; ".join(x for x in (why, f"컬럼 {len(cols)}개 연결") if x)
        matches.append(ObjectMatch(t, po.table, round(score, 3), reason, cols, missing, extra))
    links = _links(draft, onto, matches)
    unbound = [t for t in _candidates(onto) if t not in taken_t]
    return Suggestion(list(standard), matches, links, [o.table for o in draft.objects if o.table not in taken_o],
                      unbound)


def retarget(s: Suggestion, draft, onto, tables: dict, terms: list[dict] | None = None) -> Suggestion:
    """The suggestion after a person chose another table for a type: its columns and relations are matched again."""
    words = aliases(terms)
    objects, taken = [], set()
    for m in s.objects:
        table = tables.get(m.object, m.table)
        po = next((o for o in draft.objects if o.table == table), None)
        if table != m.table and po is not None:
            cols, missing, extra, _ = _match_columns(onto, m.object, po, words)
            m = ObjectMatch(m.object, table, m.score, "직접 지정", cols, missing, extra)
        objects.append(m)
        taken.add(m.object)
    for t, table in tables.items():  # a type no table was suggested for, given one by hand
        po = next((o for o in draft.objects if o.table == table), None)
        if t not in taken and po is not None and t in onto.objects:
            cols, missing, extra, _ = _match_columns(onto, t, po, words)
            objects.append(ObjectMatch(t, table, 0.0, "직접 지정", cols, missing, extra))
    used = {m.table for m in objects if tables.get(m.object, m.table)}
    return Suggestion(s.standard, objects, _links(draft, onto, objects),
                      [o.table for o in draft.objects if o.table not in used],
                      [t for t in _candidates(onto) if t not in {m.object for m in objects}])


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
            own = next(p for p in src.properties if p.name == dl.on[0])
            fk, shown = own.column, ", ".join(own.columns) or own.column
            if a == lk.source and b == lk.target and fk in col_of[lk.source]:
                out[lk.name] = {"on": {col_of[lk.source][fk]: onto.objects[lk.target].key},
                                "why": f"{src.table}.{shown} → {dst.table} 키"}
                break
            if a == lk.target and b == lk.source and fk in col_of[lk.target]:
                out[lk.name] = {"on": {onto.objects[lk.source].key: col_of[lk.target][fk]},
                                "why": f"{src.table}.{shown} → {dst.table} 키"}
                break
    return out


def _reaches_unbound(onto, type_name: str, prop: str, kept: set[str], seen: frozenset = frozenset()) -> bool:
    from xgen_space import expr as ex

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
            base: list[Module] | None = None, draft=None, terms: list[dict] | None = None) -> Module:
    """The binding module for the confirmed matches. edits: {objects: {Type: table|None},
    columns: {"Type.prop": column|None}} change or drop a suggestion before it is written. With `base` (the
    standard's modules), what the removals leave broken (a query on a removed property, a computed property built
    from one) is taken out too, so the standard composes over the tables. With `draft`, a table chosen by hand is
    matched column by column again."""
    if draft is not None and (edits or {}).get("objects"):
        s = retarget(s, draft, onto, {k: v for k, v in edits["objects"].items() if v}, terms)
    m = _binding(s, onto, name=name, label=label, edits=edits, draft=draft)
    if base is None:
        return m
    from xgen_space.modules import settle

    settle(m, base)
    return m


def _binding(s: Suggestion, onto, *, name: str, label: str = "", edits: dict | None = None, draft=None) -> Module:
    edits = edits or {}
    objects_edit, columns_edit = edits.get("objects") or {}, edits.get("columns") or {}
    bind_objects, removed_props, kept = {}, [], set()
    missing: dict[tuple[str, str], set[str]] = {}
    for m in s.objects:
        table = objects_edit.get(m.object, m.table)
        if table is None:
            continue
        kept.add(m.object)
        cols = {c.property: list(c.columns) or c.column for c in m.columns}
        for ref, col in columns_edit.items():
            t, _, p = ref.partition(".")
            if t == m.object:
                if col is None:
                    cols.pop(p, None)
                else:  # the page names a key of several columns by its stand-in
                    planned = next((o for o in (draft.objects if draft else []) if o.table == table), None)
                    wide = next((x for x in (planned.properties if planned else []) if x.column == col and x.columns), None)
                    cols[p] = list(wide.columns) if wide else col
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
    unjoined = [k for k, lk in onto.links.items() if k not in links and not lk.bound and lk.source in kept
                and lk.target in kept]  # both ends are here and no table joins them
    if unjoined:
        remove["links"] = unjoined
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
                  description="표준 정의를 업로드한 테이블에 연결합니다(Binding 제안에서 확정).",
                  requires=[Requirement(x) for x in s.standard],
                  body={**{x: {} for x in SECTIONS}, "questions": [], "exclusive": []},
                  extend={"objects": bind_objects, "links": links}, remove=remove)
