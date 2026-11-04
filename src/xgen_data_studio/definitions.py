"""Table and code definitions: the names, types, keys, references and code values of a schema, without its rows.

Projects keep these as a table definition sheet (a row per column: table, column, their names, type, key, code
group) and a code definition sheet (a row per code: group, code, name, in use), or export them from a modelling
tool. `read_definitions` reads either sheet from CSV or Excel, or a JSON file in the shape of `Definitions.to_dict`.

They do two things for a draft (draft.py): `schema_backend` builds an empty database with the declared keys and
references, so a studio can be drafted from the schema alone, and the draft takes its object and property names,
and the allowed values of coded columns with their names, from them (`draft(..., definitions=)`).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_data_studio.compile.sql import qi

TRUE = {"y", "yes", "true", "1", "o", "pk", "●", "○", "v", "✓"}
# header names a sheet may use, lower case without spaces; the first match wins
TABLE_HEADERS = {
    "table": ["테이블명", "테이블id", "물리테이블명", "테이블물리명", "table", "tablename", "table_name", "tableid"],
    "table_label": ["테이블한글명", "논리테이블명", "테이블논리명", "엔터티명", "엔티티명", "테이블설명", "tablelabel",
                    "table_label", "entity", "entityname"],
    "column": ["컬럼명", "컬럼id", "물리컬럼명", "컬럼물리명", "column", "columnname", "column_name", "columnid"],
    "label": ["컬럼한글명", "논리컬럼명", "컬럼논리명", "속성명", "논리명", "attribute", "attributename", "columnlabel",
              "column_label"],
    "type": ["데이터타입", "자료형", "타입", "datatype", "data_type", "type"],
    "length": ["길이", "length", "size"],
    "pk": ["pk", "pk여부", "기본키", "primarykey", "primary_key", "키"],
    "not_null": ["notnull", "not_null", "필수", "필수여부", "required", "mandatory"],
    "nullable": ["null", "null여부", "nullable", "널여부", "null허용"],
    "code": ["코드그룹", "코드그룹id", "공통코드", "공통코드그룹", "codegroup", "code_group", "code"],
    "ref_table": ["참조테이블", "fk테이블", "referencetable", "ref_table", "references"],
    "ref_column": ["참조컬럼", "fk컬럼", "referencecolumn", "ref_column"],
    "description": ["설명", "비고", "컬럼설명", "description", "comment", "remarks"],
}
CODE_HEADERS = {
    "group": ["코드그룹", "그룹코드", "코드그룹id", "공통코드그룹", "대분류코드", "group", "codegroup", "code_group"],
    "group_label": ["코드그룹명", "그룹코드명", "대분류코드명", "공통코드그룹명", "groupname", "group_name", "group_label"],
    "code": ["코드", "코드값", "상세코드", "소분류코드", "code", "value", "codevalue"],
    "name": ["코드명", "코드값명", "상세코드명", "소분류코드명", "name", "label", "codename"],
    "use": ["사용여부", "사용", "use", "use_yn", "useyn", "active"],
}
_GROUP_IN_LABEL = re.compile(r"\(([A-Za-z]{1,6}\d{1,6})\)")  # a label that names its code group: 주문상태(OD01)


@dataclass
class ColumnDef:
    name: str
    label: str = ""
    type: str = ""
    length: int = 0
    pk: bool = False
    required: bool = False
    code: str = ""  # the code group whose values the column holds
    description: str = ""


@dataclass
class TableDef:
    name: str
    label: str = ""
    description: str = ""
    columns: list[ColumnDef] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)  # {columns: [...], table: ..., ref_columns: [...]}

    def column(self, name: str) -> ColumnDef | None:
        low = name.lower()
        return next((c for c in self.columns if c.name.lower() == low), None)


@dataclass
class CodeGroup:
    name: str
    label: str = ""
    values: list[dict] = field(default_factory=list)  # {code, name, use}

    def used(self) -> list[dict]:
        return [v for v in self.values if v.get("use", True)]


@dataclass
class Definitions:
    tables: dict[str, TableDef] = field(default_factory=dict)
    codes: dict[str, CodeGroup] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def table(self, name: str) -> TableDef | None:
        low = name.lower()
        return self.tables.get(name) or next((t for k, t in self.tables.items() if k.lower() == low), None)

    def code_of(self, col: ColumnDef) -> CodeGroup | None:
        """The code group a column names, or the one its label names in brackets."""
        for g in [col.code, *_GROUP_IN_LABEL.findall(col.label or ""), *_GROUP_IN_LABEL.findall(col.description or "")]:
            if g and g in self.codes:
                return self.codes[g]
        return None

    def merge(self, other: Definitions) -> Definitions:
        out = Definitions(dict(self.tables), dict(self.codes), [*self.sources, *other.sources])
        out.tables.update(other.tables)
        out.codes.update(other.codes)
        return out

    def counts(self) -> dict:
        return {"tables": len(self.tables), "columns": sum(len(t.columns) for t in self.tables.values()),
                "references": sum(len(t.references) for t in self.tables.values()), "codes": len(self.codes),
                "code_values": sum(len(g.values) for g in self.codes.values())}

    def to_dict(self) -> dict:
        return {"tables": [_clean(asdict(t)) for t in self.tables.values()],
                "codes": {k: {**({"label": g.label} if g.label else {}), "values": g.values}
                          for k, g in self.codes.items()}}

    @classmethod
    def from_dict(cls, d: dict, source: str = "") -> Definitions:
        """The shape to_dict writes, and the usual synonyms: table/name, logical/label, not_null/required,
        code_group/code, fks/references with ref_table/table."""
        tables: dict[str, TableDef] = {}
        items = d.get("tables") or []
        if isinstance(items, dict):
            items = [{"name": k, **(v or {})} for k, v in items.items()]
        for t in items:
            name = str(t.get("name") or t.get("table") or "")
            if not name:
                continue
            cols = []
            for c in t.get("columns") or []:
                code = c.get("code") or c.get("code_group") or ""
                cols.append(ColumnDef(name=str(c.get("name") or c.get("column") or ""),
                                      label=str(c.get("label") or c.get("logical") or ""),
                                      type=str(c.get("type") or ""), length=_int(c.get("length")),
                                      pk=bool(c.get("pk")), required=bool(c.get("required") or c.get("not_null")),
                                      code=str(code[0] if isinstance(code, list) and code else code or ""),
                                      description=str(c.get("description") or c.get("comment") or "")))
            pk = list(t.get("primary_key") or [c.name for c in cols if c.pk])
            refs = []
            for r in t.get("references") or t.get("fks") or []:
                src = r.get("columns") or ([r["column"]] if r.get("column") else [])
                dst = r.get("ref_columns") or ([r["ref_column"]] if r.get("ref_column") else [])
                target = r.get("table") or r.get("ref_table") or ""
                if src and target:
                    refs.append({"columns": list(src), "table": str(target), "ref_columns": list(dst)})
            tables[name] = TableDef(name, str(t.get("label") or t.get("logical") or ""),
                                    str(t.get("description") or t.get("definition") or ""), cols, pk, refs)
        codes: dict[str, CodeGroup] = {}
        for k, g in (d.get("codes") or {}).items():
            vals = [{"code": str(v.get("code")), "name": str(v.get("name") or ""),
                     "use": str(v.get("use", True)).lower() not in ("n", "false", "0", "no")}
                    for v in (g.get("values") or []) if v.get("code") not in (None, "")]
            codes[str(k)] = CodeGroup(str(k), str(g.get("label") or g.get("name") or ""), vals)
        return cls(tables, codes, [source] if source else [])


def read_definitions(data: bytes, source: str) -> Definitions | None:
    """A JSON definitions file, or the definition sheets of a CSV or Excel file; None when it holds neither."""
    if source.lower().endswith(".json"):
        try:
            d = json.loads(data.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return Definitions.from_dict(d, source) if isinstance(d, dict) and ("tables" in d or "codes" in d) else None
    from xgen_data_studio.draft import ReadError, read_file

    try:
        sheets = read_file(data, source)
    except ReadError:
        return None
    return from_sheets(sheets, source)


def from_sheets(sheets, source: str = "") -> Definitions | None:
    """Table and code definition sheets among tables read from files (draft.Table); None when there are none."""
    out = Definitions(sources=[source] if source else [])
    found = False
    for sh in sheets:
        cols = _match(sh.columns, TABLE_HEADERS)
        if "table" in cols and "column" in cols:
            found = True
            _table_rows(out, sh, cols)
            continue
        cols = _match(sh.columns, CODE_HEADERS)
        if "group" in cols and "code" in cols and "name" in cols:
            found = True
            for row in sh.rows:
                g, code = _cell(row, cols, "group"), _cell(row, cols, "code")
                if not g or not code:
                    continue
                grp = out.codes.setdefault(g, CodeGroup(g, _cell(row, cols, "group_label")))
                if not grp.label:
                    grp.label = _cell(row, cols, "group_label")
                use = _cell(row, cols, "use").lower()
                grp.values.append({"code": code, "name": _cell(row, cols, "name"),
                                   "use": use not in ("n", "no", "false", "0", "미사용")})
    return out if found else None


def _table_rows(out: Definitions, sh, cols: dict[str, int]) -> None:
    for row in sh.rows:
        tname, cname = _cell(row, cols, "table"), _cell(row, cols, "column")
        if not tname or not cname:
            continue
        t = out.tables.setdefault(tname, TableDef(tname))
        if not t.label:
            t.label = _cell(row, cols, "table_label")
        if "not_null" in cols:
            required = _cell(row, cols, "not_null").lower() in TRUE
        else:  # a nullable flag: N (or "NOT NULL") means required
            v = _cell(row, cols, "nullable").lower()
            required = v in ("n", "no", "false", "notnull", "not null")
        pk = _cell(row, cols, "pk").lower() in TRUE or _cell(row, cols, "pk").isdigit()
        ty, length = _cell(row, cols, "type"), _int(_cell(row, cols, "length"))
        m = re.fullmatch(r"\s*([A-Za-z ]+?)\s*\(\s*(\d+)(?:\s*,\s*\d+)?\s*\)\s*", ty)
        if m and not length:
            ty, length = m.group(1), int(m.group(2))
        t.columns.append(ColumnDef(cname, _cell(row, cols, "label"), ty, length, pk, required or pk,
                                   _cell(row, cols, "code"), _cell(row, cols, "description")))
        if pk:
            t.primary_key.append(cname)
        rt = _cell(row, cols, "ref_table")
        if rt:
            t.references.append({"columns": [cname], "table": rt,
                                 "ref_columns": [_cell(row, cols, "ref_column")] if _cell(row, cols, "ref_column")
                                 else []})


def schema_backend(defs: Definitions, tables: list[str] | None = None, *, conn=None):
    """An empty SQLite database with the definitions' tables, primary keys and single-column references
    (in memory, or on `conn`, a sqlite3 connection)."""
    from xgen_data_studio.backends.sql import SqliteBackend

    wanted = {t.lower() for t in tables} if tables else None
    chosen = [t for t in defs.tables.values() if wanted is None or t.name.lower() in wanted]
    names = {t.name.lower(): t for t in chosen}
    ddl = []
    for t in chosen:
        if not t.columns:
            continue
        parts = [f"{qi(c.name)} {_sql_type(c)}" for c in t.columns]
        if t.primary_key:
            parts.append(f"PRIMARY KEY ({', '.join(qi(c) for c in t.primary_key)})")
        for r in t.references:
            target = names.get(str(r["table"]).lower())
            if target is None or len(r["columns"]) != 1:
                continue  # a reference to a table left out, or over several columns, is not drafted
            ref = (r.get("ref_columns") or target.primary_key or [""])[0]
            if len(target.primary_key) == 1 and ref.lower() == target.primary_key[0].lower():
                parts.append(f"FOREIGN KEY ({qi(r['columns'][0])}) REFERENCES {qi(target.name)} ({qi(ref)})")
        ddl.append(f"CREATE TABLE {qi(t.name)} ({', '.join(parts)})")
    b = SqliteBackend(conn=conn) if conn is not None else SqliteBackend()
    b.script(";\n".join(ddl) + (";" if ddl else ""))
    return b


def _sql_type(c: ColumnDef) -> str:
    u = (c.type or "").upper()
    if any(k in u for k in ("INT", "SERIAL")):
        return "INTEGER"
    if any(k in u for k in ("NUMERIC", "DECIMAL", "NUMBER", "REAL", "FLOA", "DOUB", "MONEY")):
        return "NUMERIC"
    if "TIMESTAMP" in u or "DATETIME" in u:
        return "TIMESTAMP"
    if u == "DATE":
        return "DATE"
    if "BOOL" in u:
        return "BOOLEAN"
    return "TEXT"


def _match(headers: list[str], spec: dict[str, list[str]]) -> dict[str, int]:
    norm = [re.sub(r"[\s()_\-./]", "", str(h or "")).lower() for h in headers]
    out: dict[str, int] = {}
    for key, names in spec.items():
        for n in names:
            n = re.sub(r"[\s()_\-./]", "", n).lower()
            i = next((i for i, h in enumerate(norm) if h == n and i not in out.values()), None)
            if i is not None:
                out[key] = i
                break
    return out


def _cell(row: list, cols: dict[str, int], key: str) -> str:
    i = cols.get(key)
    if i is None or i >= len(row) or row[i] is None:
        return ""
    return str(row[i]).strip()


def _int(v: Any) -> int:
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return 0


def _clean(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: _clean(v) for k, v in d.items() if v not in ("", [], {}, None, False, 0)}
    if isinstance(d, list):
        return [_clean(x) for x in d]
    return d
