"""Check the definition against the actual database: tables, columns, types, keys, enum values, orphan links."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from xgen_space.check import columns_of
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


@dataclass
class BindingReport:
    findings: list[Finding]
    checked: dict[str, int]

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "checked": self.checked, "findings": [asdict(f) for f in self.findings]}


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

    for o in onto.objects.values():
        if not o.table:
            continue
        have = table(o.table)
        if have is None:
            out.append(Finding("error", "table", f"object:{o.name}", f"table '{o.table}' does not exist"))
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
                                       f"column '{o.table}.{col}' does not exist"))
                elif prop is not None and len(parts) == 1 and not _fits(prop.type, have[col.lower()]):
                    out.append(Finding("warning", "type", f"property:{o.name}.{p}",
                                       f"{prop.type} is read from {o.table}.{col} declared {have[col.lower()] or '?'}"))
    for lk in onto.links.values():
        if lk.via:
            have = table(lk.via.table)
            if have is None:
                out.append(Finding("error", "table", f"link:{lk.name}", f"link table '{lk.via.table}' does not exist"))
                continue
            for c in (lk.via.source_column, lk.via.target_column):
                checked["columns"] += 1
                if c.lower() not in have:
                    out.append(Finding("error", "column", f"link:{lk.name}", f"column '{lk.via.table}.{c}' does not exist"))
    if data and not any(f.severity == "error" for f in out):
        out += _data_checks(onto, backend, limit, checked)
    return BindingReport(out, checked)


def _data_checks(onto: Ontology, backend, limit: int, checked: dict[str, int]) -> list[Finding]:
    out: list[Finding] = []
    for o in onto.objects.values():
        if not o.table:
            continue
        t, key = qi(o.table), ", ".join(qi(c) for c in o.key_prop.cols)
        dialect = backend.capabilities.dialect
        top = f"TOP {limit} " if dialect == "tsql" else ""
        first = {"oracle": f" FETCH FIRST {limit} ROWS ONLY", "tsql": ""}.get(dialect, f" LIMIT {limit}")
        dup = backend.fetch(f"SELECT {top}{key}, COUNT(*) FROM {t} GROUP BY {key} HAVING COUNT(*) > 1{first}")
        checked["data_checks"] += 1
        if dup:
            shown = [KEY_SEP.join(str(v) for v in r[:-1]) for r in dup]
            out.append(Finding("error", "key", f"object:{o.name}", f"key {o.key} repeats: {shown}"))
        for p in o.properties.values():
            if p.expr:
                continue
            c = qi(p.cols[0])
            if p.required or p.name == o.key:
                empty = " OR ".join(f"{qi(x)} IS NULL" for x in p.cols)
                n = backend.fetch(f"SELECT COUNT(*) FROM {t} WHERE {empty}")[0][0]
                checked["data_checks"] += 1
                if n:
                    out.append(Finding("error", "required", f"property:{o.name}.{p.name}", f"{n} rows have no value"))
            if p.type == "enum" and p.values:
                seen = [r[0] for r in backend.fetch(f"SELECT DISTINCT {c} FROM {t} WHERE {c} IS NOT NULL")]
                checked["data_checks"] += 1
                extra = sorted(str(v) for v in seen if str(v) not in p.values)
                if extra:
                    out.append(Finding("warning", "enum", f"property:{o.name}.{p.name}",
                                       f"values not in the definition: {extra[:limit]}"))
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
            out.append(Finding("warning", "orphan", f"link:{lk.name}",
                               f"{n} {src.name} rows point at a {dst.name} that does not exist"))
    return out
