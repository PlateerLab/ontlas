"""Check the definition against the actual database: tables, columns, types, keys, enum values, orphan links."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from xgen_space.check import _find_prop, all_props, columns_of
from xgen_space.compile.sql import qi
from xgen_space.model import KEY_SEP, Ontology

_TYPES = {
    "integer": ("INT",),
    "decimal": ("REAL", "NUM", "DEC", "DOUBLE", "FLOAT", "INT", "MONEY"),
    "boolean": ("BOOL", "BIT", "INT", "TINYINT"),
    "date": ("DATE", "TEXT", "CHAR", "TIME"),
    "datetime": ("DATE", "TIME", "TEXT", "CHAR"),
    "string": ("CHAR", "TEXT", "CLOB", "STRING", "UUID", ""),
    "enum": ("CHAR", "TEXT", "CLOB", "STRING", "ENUM", ""),
}


@dataclass
class Finding:
    severity: str
    kind: str
    element: str
    detail: str
    data: dict = field(default_factory=dict)  # the table, columns and rows it is about, for whoever goes on to fix it


@dataclass
class BindingReport:
    findings: list[Finding]
    checked: dict[str, int]

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checked": self.checked, "findings": [asdict(f) for f in self.findings]}


def entity_level(onto: Ontology, name: str, *, columns: set[str] | None = None, found: set[str] | None = None) -> int:
    """How far an object type has come, 0 to 3.

    0  a definition only: a label or a description, no property past its key and no relation.
    1  logical: a property past its key, or a relation it takes part in.
    2  bound: a source table, and a column for every stored property (a computed one has none).
    3  bound, and the last database check found nothing against it.

    `columns` is what the source holds for the type's table, in lower case, where that was read: every stored
    property's column has to be among them. Where it was not (None), a stored property reads the column it names, or
    the one called as it is, so the table is enough. `found` is the elements the last database check found something
    against: on the type, on one of its properties, or on a relation from it. None says nothing was measured for the
    type as it is now, which leaves a bound type at 2; this never measures."""
    t = onto.objects[name]
    keys, seen, at = set(), set(), t
    while at is not None and at.name not in seen:  # an ancestor's key is the type's own key
        seen.add(at.name)
        keys.add(at.key)
        at = onto.objects.get(at.parent)
    props = [_find_prop(onto, name, p) for p in all_props(onto, name)]
    stored = [p for p in props if not p.expr and (p.name == t.key or p.name not in keys)]
    if not t.table or (columns is not None and any(c.lower() not in columns for p in stored for c in p.cols)):
        related = any(name in (lk.source, lk.target) for lk in onto.links.values())
        return 1 if related or any(p.name not in keys and not p.internal for p in props) else 0
    if found is None:
        return 2
    mine = {f"object:{name}", *(f"link:{lk.name}" for lk in onto.links.values() if lk.source == name)}
    return 2 if any(e in mine or e.startswith(f"property:{name}.") for e in found) else 3


def _fits(prop_type: str, sql_type: str) -> bool:
    s = (sql_type or "").upper()
    return any(k in s for k in _TYPES.get(prop_type, ("",)))


def check_bindings(onto: Ontology, backend, *, data: bool = True, limit: int = 5) -> BindingReport:
    """Every bound table and column must exist with a fitting type; with `data`, the rows are checked too."""
    out: list[Finding] = []
    checked = {"tables": 0, "columns": 0, "data_checks": 0}
    cols: dict[str, dict[str, str] | None] = {}

    def table(name: str) -> dict[str, str] | None:
        if name not in cols:
            cols[name] = backend.columns(name)
            checked["tables"] += 1
        return cols[name]

    absent = {t for t in onto.crosswalks() if table(t) is None}
    for o in onto.objects.values():
        if not o.table:
            continue
        have = table(o.table)
        if o.table in absent:
            out.append(Finding("warning", "table", f"object:{o.name}", f"identity not resolved yet: '{o.table}' is written then"))
            continue
        if have is None:
            out.append(Finding("error", "table", f"object:{o.name}", f"table '{o.table}' does not exist", {"table": o.table}))
            continue
        for p in sorted(set(o.properties) | {o.key}):
            prop = o.properties.get(p)
            if prop is not None and prop.expr:
                continue
            parts = columns_of(onto, o.name, p)
            for col in parts:
                checked["columns"] += 1
                if col.lower() not in have:
                    out.append(Finding("error", "column", f"property:{o.name}.{p}",
                                       f"column '{o.table}.{col}' does not exist", {"table": o.table, "column": col}))
                elif prop is not None and len(parts) == 1 and not _fits(prop.type, have[col.lower()]):
                    out.append(Finding("warning", "type", f"property:{o.name}.{p}",
                                       f"{prop.type} is read from {o.table}.{col} declared {have[col.lower()] or '?'}",
                                       {"table": o.table, "column": col, "type": prop.type, "sql_type": have[col.lower()] or ""}))
    for lk in onto.links.values():
        if lk.via and lk.via.table in absent:
            continue
        if lk.via:
            have = table(lk.via.table)
            if have is None:
                out.append(Finding("error", "table", f"link:{lk.name}", f"link table '{lk.via.table}' does not exist", {"table": lk.via.table}))
                continue
            for c in (lk.via.source_column, lk.via.target_column):
                checked["columns"] += 1
                if c.lower() not in have:
                    out.append(Finding("error", "column", f"link:{lk.name}", f"column '{lk.via.table}.{c}' does not exist",
                                       {"table": lk.via.table, "column": c}))
    if data and not any(f.severity == "error" for f in out):
        out += _data_checks(onto, backend, limit, checked, absent)
    return BindingReport(out, checked)


def _data_checks(onto: Ontology, backend, limit: int, checked: dict[str, int], absent: set[str]) -> list[Finding]:
    out: list[Finding] = []
    for o in onto.objects.values():
        if not o.table or o.table in absent:
            continue
        t, key = qi(o.table), ", ".join(qi(c) for c in o.key_prop.cols)
        dialect = backend.capabilities.dialect
        top = f"TOP {limit} " if dialect == "tsql" else ""
        first = {"oracle": f" FETCH FIRST {limit} ROWS ONLY", "tsql": ""}.get(dialect, f" LIMIT {limit}")
        dup = backend.fetch(f"SELECT {top}{key}, COUNT(*) FROM {t} GROUP BY {key} HAVING COUNT(*) > 1{first}")
        checked["data_checks"] += 1
        if dup:
            shown = [KEY_SEP.join(str(v) for v in r[:-1]) for r in dup]
            out.append(Finding("error", "key", f"object:{o.name}", f"key {o.key} repeats: {shown}",
                               {"table": o.table, "columns": list(o.key_prop.cols), "keys": shown}))
        for p in o.properties.values():
            if p.expr:
                continue
            c = qi(p.cols[0])
            if p.required or p.name == o.key:
                empty = " OR ".join(f"{qi(x)} IS NULL" for x in p.cols)
                n = backend.fetch(f"SELECT COUNT(*) FROM {t} WHERE {empty}")[0][0]
                checked["data_checks"] += 1
                if n:
                    rows = backend.fetch(f"SELECT {top}{key} FROM {t} WHERE {empty}{first}")
                    out.append(Finding("error", "required", f"property:{o.name}.{p.name}", f"{n} rows have no value",
                                       {"table": o.table, "columns": list(p.cols), "count": n,
                                        "keys": [KEY_SEP.join(str(v) for v in r) for r in rows]}))
            if p.type == "enum" and p.values:
                seen = {str(r[0]): r[1] for r in backend.fetch(f"SELECT {c}, COUNT(*) FROM {t} WHERE {c} IS NOT NULL GROUP BY {c}")}
                checked["data_checks"] += 1
                extra = sorted(v for v in seen if v not in p.values)
                if extra:
                    out.append(Finding("warning", "enum", f"property:{o.name}.{p.name}",
                                       f"values not in the definition: {extra[:limit]}",
                                       {"table": o.table, "column": p.cols[0], "extra": extra[:20], "counts": {v: seen[v] for v in extra[:20]}}))
    for lk in onto.links.values():
        src, dst = onto.objects[lk.source], onto.objects[lk.target]
        if not (lk.on and src.table and dst.table):
            continue
        sp, tp = columns_of(onto, src.name, lk.on[0]), columns_of(onto, dst.name, lk.on[1])
        if lk.on[1] != dst.key or len(sp) != len(tp):
            continue
        join = " AND ".join(f"s.{qi(a)} = d.{qi(b)}" for a, b in zip(sp, tp))
        n = backend.fetch(f"SELECT COUNT(*) FROM {qi(src.table)} s LEFT JOIN {qi(dst.table)} d ON {join} "
                          f"WHERE s.{qi(sp[0])} IS NOT NULL AND d.{qi(tp[0])} IS NULL")[0][0]
        checked["data_checks"] += 1
        if n:
            dialect = backend.capabilities.dialect
            top = f"TOP {limit} " if dialect == "tsql" else ""
            first = {"oracle": f" FETCH FIRST {limit} ROWS ONLY", "tsql": ""}.get(dialect, f" LIMIT {limit}")
            rows = backend.fetch(f"SELECT {top}s.{qi(sp[0])} FROM {qi(src.table)} s LEFT JOIN {qi(dst.table)} d ON {join} "
                                 f"WHERE s.{qi(sp[0])} IS NOT NULL AND d.{qi(tp[0])} IS NULL{first}")
            out.append(Finding("warning", "orphan", f"link:{lk.name}",
                               f"{n} {src.name} rows point at a {dst.name} that does not exist",
                               {"table": src.table, "column": sp[0], "count": n, "target": dst.table, "values": [str(r[0]) for r in rows]}))
    return out
