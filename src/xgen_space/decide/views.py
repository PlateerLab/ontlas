"""Views as objects: an object defined by a query over other objects, for a ledger whose table holds several kinds of row.

    RefundEntry:
      key: entry_id
      view:
        name: refund_entries
        query: {match: {e: LedgerEntry}, where: {eq: [e.kind, REFUND]}, return: [e.entry_id, {col: e.units, as: refunded}]}
      properties: {entry_id: {type: string}, refunded: {type: integer}}

The query is written over objects, so it reads through their bindings and can group rows into one object. It compiles
to the source's SQL and lives there as a database view (`xspace views`, or the statements handed to whoever may create
one), and the object is bound to that view as to a table: queries, graphs, decisions and checks need nothing else.
Writing goes through to the object behind it where each view row is one row there.
"""
from __future__ import annotations

from typing import Any

from xgen_space.check import _comparable, _find_prop, aliases_of, check, column_refs
from xgen_space.compile.sql import qi
from xgen_space.ir import IRError, Query, Ref, filter_refs
from xgen_space.model import ModelError, ObjectType, Ontology


def view_query(t: ObjectType) -> Query:
    return Query.from_dict(t.view.get("query") or {})


def behind(onto: Ontology, t: ObjectType) -> tuple[str, dict[str, str]] | None:
    """The one type whose rows this view's rows are, and which property each column is; None if rows are not one to
    one: a join, a grouping, or a key that is not the key behind."""
    q = view_query(t)
    if len(q.nodes) != 1 or q.edges or q.aggregated or q.distinct:
        return None
    base = next(iter(q.nodes.values()))
    columns = {c.name: c.expr.prop for c in q.columns if isinstance(c.expr, Ref)}
    if columns.get(t.key_prop.col) != onto.obj(base).key:
        return None
    return base, columns


def through_view(onto: Ontology, type_name: str, changes: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Where a write to this type lands: the type behind a view, and its properties."""
    t = onto.obj(type_name)
    if not t.view:
        return type_name, changes
    found = behind(onto, t)
    if found is None:
        raise ValueError(f"{type_name} is a view with no single row behind each of its rows, so it cannot be written")
    base, columns = found
    missing = [p for p in changes if t.prop(p).col not in columns]
    if missing:
        raise ValueError(f"{type_name}.{missing[0]} comes from no property of {base}, so it cannot be written")
    return through_view(onto, base, {columns[t.prop(p).col]: v for p, v in changes.items()})


def _reads_clock(onto: Ontology, type_name: str, name: str, seen: set | None = None) -> bool:
    """A view is stored, so a value that moves with today would stay at the day it was made."""
    from xgen_space.expr import Agg, Call, ExprError, Prop, parse_expr, resolve_agg, walk

    seen = set() if seen is None else seen
    p = _find_prop(onto, type_name, name)
    if p is None or not p.expr or (type_name, name) in seen:
        return False
    seen.add((type_name, name))
    try:
        for n in walk(parse_expr(p.expr)):
            if (isinstance(n, Call) and n.fn in ("today", "now")) or (isinstance(n, Agg) and n.fn == "current"):
                return True
            if isinstance(n, Prop) and _reads_clock(onto, type_name, n.name, seen):
                return True
            if isinstance(n, Agg):
                steps, prop = resolve_agg(onto, type_name, n)
                if prop and _reads_clock(onto, steps[-1].type, prop, seen):
                    return True
    except ExprError:
        return False  # the property's own check names it
    return False


def in_order(onto: Ontology) -> list[ObjectType]:
    """The views, each after the views it reads."""
    out: list[ObjectType] = []
    state: dict[str, str] = {}

    def visit(t: ObjectType, path: list[str]) -> None:
        if state.get(t.name) == "done":
            return
        if state.get(t.name) == "open":
            raise ValueError(f"views read each other in a loop: {' -> '.join([*path, t.name])}")
        state[t.name] = "open"
        for name in aliases_of(view_query(t)).values():
            read = onto.objects.get(name)
            if read is not None and read.view:
                visit(read, [*path, t.name])
        state[t.name] = "done"
        out.append(t)

    for t in onto.objects.values():
        if t.view:
            visit(t, [])
    return out


def view_issues(onto: Ontology, t: ObjectType) -> list[str]:
    out = [f"unknown key '{k}'" for k in t.view if k not in ("name", "query", "inline")]
    if t.table != t.view_name:
        out.append("give a view or a source table, not both")
    try:
        q = view_query(t)
    except (IRError, KeyError, TypeError, AttributeError) as e:
        return [*out, f"cannot read its query: {e}"]
    res = check(q, onto)
    if not res.ok:
        return [*out, *res.issues]
    if res.param_types:
        out.append(f"a view is stored, so it takes no parameters: {sorted(res.param_types)}")
    if q.order or q.limit is not None:
        out.append("a view gives rows, not an order or a limit")
    types = aliases_of(q)
    for ref in [*column_refs(q), *filter_refs(q.where)]:
        if _reads_clock(onto, types[ref.alias], ref.prop):
            out.append(f"{ref} moves with the clock, and a view is stored")
    for p in t.properties.values():
        if p.expr:
            continue
        for col in p.cols:
            got = res.column_types.get(col)
            if got is None:
                out.append(f"{p.name}: the query returns no column '{col}'")
            elif not _comparable(p.type, got):
                out.append(f"{p.name} is {p.type}, the column '{col}' is {got}")
    try:
        in_order(onto)
    except ValueError as e:
        out.append(str(e))
    except (IRError, KeyError, TypeError, AttributeError):
        pass  # the other view's own check names it
    return out


def write_issue(onto: Ontology, t: ObjectType, props: list[str]) -> str:
    """Why an action cannot write these properties of a view, if it cannot."""
    try:
        through_view(onto, t.name, {p: None for p in props})
    except (ValueError, ModelError, IRError, KeyError) as e:
        return str(e)
    return ""


def view_statements(onto: Ontology, backend) -> list[str]:
    """What makes the views in a source: every old one out, last read first, then each one after what it reads."""
    ordered = in_order(onto)
    made = [f"CREATE VIEW {qi(t.table)} AS\n{backend.compiler(onto).compile(view_query(t)).preview()}" for t in ordered]
    return [*(f"DROP VIEW IF EXISTS {qi(t.table)}" for t in reversed(ordered)), *made]


def create_views(studio, backend: str | None = None) -> list[str]:
    b = studio.backend(backend)
    if b.capabilities.language != "sql":
        raise ValueError(f"backend {b.name} is not a SQL source; views live in the source")
    done = view_statements(studio.onto, b)
    for text in done:
        b.run(text)
    return done
