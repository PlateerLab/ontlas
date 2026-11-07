"""Role scoping: refuse unreadable types and AND each alias's row filter into the query."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from xgen_space.ir import Agg, And, Cmp, Column, Exists, Not, Or, Query, Ref, filter_refs, parse_filter
from xgen_space.model import RAW_SUFFIX, TEXT_SUFFIX, Ontology, Role


class AccessDenied(PermissionError):
    """The role may not read or run this."""


def _rewrite(node: Any, alias: str, renames: dict[str, str], principal_attrs: set[str]) -> Any:
    if isinstance(node, dict):
        if set(node) == {"principal"}:
            principal_attrs.add(node["principal"])
            return {"param": f"principal__{node['principal']}"}
        out = {}
        for k, v in node.items():
            if k in ("exists", "not_exists") and isinstance(v, dict):
                inner = {**renames, **{a: f"{alias}__{a}" for a in v.get("match", {})}}
                v = {**v, "match": {inner[a]: t for a, t in v.get("match", {}).items()}}
                out[k] = _rewrite(v, alias, inner, principal_attrs)
            else:
                out[k] = _rewrite(v, alias, renames, principal_attrs)
        return out
    if isinstance(node, list):
        return [_rewrite(x, alias, renames, principal_attrs) for x in node]
    if isinstance(node, str):
        if node == "$self":
            return alias
        if "." in node and node.count(".") == 1:
            a, p = node.split(".")
            if a == "$self":
                return f"{alias}.{p}"
            if a in renames:
                return f"{renames[a]}.{p}"
        return renames.get(node, node)
    return node


def row_filter(role: Role, type_name: str, alias: str) -> tuple[Any, set[str]]:
    specs = [s for s in (role.row_filters.get(type_name), role.scoped.get(type_name)) if s]
    if not specs:
        return None, set()
    attrs: set[str] = set()
    spec = specs[0] if len(specs) == 1 else {"and": specs}
    return parse_filter(_rewrite(spec, alias, {}, attrs)), attrs


def _scope_filter(f: Any, role: Role, attrs: set[str], check) -> Any:
    if isinstance(f, (And, Or)):
        return type(f)([_scope_filter(x, role, attrs, check) for x in f.items])
    if isinstance(f, Not):
        return Not(_scope_filter(f.item, role, attrs, check))
    if isinstance(f, Exists):
        extra = []
        for a, t in f.nodes.items():
            check(t)
            rf, used = row_filter(role, t, a)
            attrs |= used
            if rf is not None:
                extra.append(rf)
        where = _scope_filter(f.where, role, attrs, check)
        parts = ([where] if where is not None else []) + extra
        return replace(f, where=And(parts) if len(parts) > 1 else (parts[0] if parts else None))
    return f


def _lineage(onto: Ontology, type_name: str) -> list[str]:
    out, t = [], type_name
    while t and t in onto.objects and t not in out:
        out.append(t)
        t = onto.objects[t].parent
    return out


def mask_style(onto: Ontology, role: Role, type_name: str, prop: str, _seen: frozenset = frozenset()) -> str:
    """How a role sees one property: '' in clear, or partial / full. A computed property built from a hidden one is
    hidden too."""
    from xgen_space.check import _find_prop

    prop = prop.removesuffix(TEXT_SUFFIX).removesuffix(RAW_SUFFIX)  # what is stored shows what its property shows
    if type_name in onto.interfaces and type_name not in onto.objects:  # the strictest of those that implement it
        from xgen_space.check import concrete_subtypes

        styles = {mask_style(onto, role, t, prop, _seen) for t in concrete_subtypes(onto, type_name)}
        return "full" if "full" in styles else next(iter(styles - {""}), "")
    names = _lineage(onto, type_name)
    if "*" in role.unmask or any(f"{t}.{prop}" in role.unmask or f"{t}.*" in role.unmask for t in names):
        return ""
    for t in names:
        style = role.mask.get(f"{t}.{prop}") or role.mask.get(f"{t}.*")
        if style:
            return style
    p = _find_prop(onto, type_name, prop)
    if p is None:
        return ""
    if p.mask:
        return p.mask
    if p.expr and (type_name, prop) not in _seen:
        from xgen_space.expr import ExprError, dependencies

        try:
            deps = dependencies(onto, type_name, prop)
        except ExprError:
            return ""
        seen = _seen | {(type_name, prop)}
        if any(mask_style(onto, role, t, n, seen) for t, n in deps if (t, n) != (type_name, prop)):
            return "full"
        # an aggregate over a scoped type counts every row of it, also those outside this role's scope
        if any(t != type_name and t in role.scoped for t, _ in deps):
            return "full"
    return ""


def masking(onto: Ontology, q: Query, role_name: str) -> dict[str, str]:
    """The returned columns this role sees masked, by column name. Filtering or ordering on a masked property is
    refused, since the answer would give the value away."""
    from xgen_space.check import aliases_of

    role = onto.roles.get(role_name)
    if role is None:
        raise AccessDenied(f"unknown role '{role_name}'")
    types = aliases_of(q)

    def style(ref: Ref) -> str:
        t = types.get(ref.alias)
        return mask_style(onto, role, t, ref.prop) if t else ""

    for ref in filter_refs(q.where):
        if style(ref):
            raise AccessDenied(f"role {role.name} sees {types.get(ref.alias)}.{ref.prop} masked and may not "
                               "filter on it")
    plan: dict[str, str] = {}
    for c in q.columns:
        e = c.expr
        ref = e if isinstance(e, Ref) else (e.ref if isinstance(e, Agg) and e.func not in ("count", "count_distinct") else None)
        if ref is not None and style(ref):
            plan[c.name] = style(ref)
    for o in q.order:
        if o.name in plan:
            raise AccessDenied(f"role {role.name} sees '{o.name}' masked and may not order by it")
    return plan


def mask_value(value: Any, style: str) -> Any:
    """Partial keeps what identifies the kind of value (an email's domain, a phone's last four digits, a name's
    first letter); full keeps nothing."""
    if value is None or not style:
        return value
    if style == "full":
        return "***"
    s = str(value)
    if "@" in s:
        local, _, domain = s.partition("@")
        return f"{local[:1]}***@{domain}"
    digits = sum(ch.isdigit() for ch in s)
    if digits >= 6 and digits >= len(s) * 0.6:
        keep, out = 4, []
        for ch in reversed(s):
            if ch.isdigit():
                out.append(ch if keep > 0 else "*")
                keep -= 1
            else:
                out.append(ch)
        return "".join(reversed(out))
    if len(s) <= 2:
        return s[:1] + "*" * (len(s) - 1)
    return s[:1] + "*" * (len(s) - 2) + s[-1:]


def mask_rows(columns: list[str], rows: list[tuple], plan: dict[str, str]) -> list[tuple]:
    if not plan:
        return rows
    idx = {i: plan[c] for i, c in enumerate(columns) if c in plan}
    return [tuple(mask_value(v, idx[i]) if i in idx else v for i, v in enumerate(r)) for r in rows]


def in_scope(studio, role: Role, type_name: str, key: Any, principal: dict | None) -> bool:
    """Whether one object is within a role's rows, asked the way a read asks."""
    obj = studio.onto.obj(type_name)
    spec, attrs = row_filter(role, type_name, "x")
    principal = principal or {}
    missing = sorted(a for a in attrs if a not in principal)
    if missing:
        raise AccessDenied(f"role {role.name} needs principal attributes {missing}")
    q = Query(nodes={"x": type_name}, where=Cmp(Ref("x", obj.key), "eq", str(key)),
              columns=[Column(Ref("x", obj.key), "k")]).with_where(spec)
    return bool(studio.run(q, {f"principal__{a}": principal[a] for a in attrs}).rows)


def decide_in_scope(studio, name: str, key: Any, role_name: str, principal: dict | None, params: dict | None = None):
    """A decision for a scoped role: refused for a row outside its scope, and shown through its masks."""
    role = studio.onto.roles.get(role_name)
    table = studio.onto.decisions.get(name)
    if role is None or table is None or not ("*" in role.run or name in role.run):
        raise AccessDenied(f"role {role_name} may not run decision '{name}'")
    if table.target in role.scoped and not in_scope(studio, role, table.target, key, principal):
        raise AccessDenied(f"{table.target} {key} is outside the scope of role {role.name}")
    res = studio.decide(name, key, params)
    for ev in res.evidence:
        style = mask_style(studio.onto, role, ev.object_type, ev.property) if ev.object_type else ""
        if style:
            ev.value = res.inputs[ev.input] = mask_value(ev.value, style)
    return res


def apply_role(onto: Ontology, q: Query, role_name: str, principal: dict | None) -> tuple[Query, dict]:
    role = onto.roles.get(role_name)
    if role is None:
        raise AccessDenied(f"unknown role '{role_name}'")

    def check(t: str) -> None:
        if t in onto.interfaces and t not in onto.objects:  # no row filter sits on an interface, so none may be passed
            from xgen_space.check import concrete_subtypes

            for m in concrete_subtypes(onto, t):
                check(m)
                if row_filter(role, m, "x")[0] is not None:
                    raise AccessDenied(f"role {role.name} reads {m} row by row, so not through interface {t}")
            return
        if not role.can_read(t):
            raise AccessDenied(f"role {role.name} may not read {t}")

    attrs: set[str] = set()
    filters = []
    for a, t in q.nodes.items():
        check(t)
        rf, used = row_filter(role, t, a)
        attrs |= used
        if rf is not None:
            filters.append(rf)
    q = replace(q, where=_scope_filter(q.where, role, attrs, check))
    if filters:
        q = q.with_where(filters[0] if len(filters) == 1 else And(filters))
    principal = principal or {}
    missing = sorted(a for a in attrs if a not in principal)
    if missing:
        raise AccessDenied(f"role {role.name} needs principal attributes {missing}")
    return q, {f"principal__{a}": principal[a] for a in attrs}
