"""Draft an ontology from data: tables become objects, columns properties, and the values decide keys and relations.

The mapping follows the W3C Direct Mapping of relational data (table -> class, column -> property, foreign key ->
link). Files declare no keys, so a key is a column whose values are all present and distinct, and a relation is a
column named after another table's key whose values are all found among that key's values. Every choice is kept
with the reason for it, so the draft can be reviewed before it is plugged into a studio.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from xgen_data_studio.compile.sql import qi
from xgen_data_studio.model import CARDINALITIES, TYPES
from xgen_data_studio.modules import SECTIONS, Module, Requirement

ENUM_MAX = 20  # past this many distinct values an allowed-value list stops being a useful check
TEXT_MAX = 40  # values longer than this are free text, not a category
XLSX_UNPACKED_MAX = 64 * 1024 * 1024
ROW_KEY = "row_no"
TITLE_HINTS = ("name", "title", "nm", "이름", "명", "제목")
PARENT_HINTS = ("parent", "upper", "upr", "super", "broader", "상위")
KEY_SUFFIXES = ("_id", "_no", "_cd", "_code", "_key", "_sn", "id", "no", "번호", "코드", "아이디")
GENERIC_KEYS = ("id", "no", "seq", "sn", "code", "key", ROW_KEY)  # shared by many tables, so a name alone says nothing
QUERY_KINDS = ("list", "count_by", "values")
STATE_HINTS = ("status", "state", "stat", "상태")
PERSON_HINTS = ("member", "customer", "user", "client", "person", "회원", "고객", "사용자")

LABELS = {
    "en": {"list": "{o} list", "count_by": "{s} per {t}", "values": "{o} by {p}", "action": "Set {o} to {s}",
           "viewer": "Viewer", "operator": "Operator", "self": "Own records ({o})",
           "question": "How many rows does '{q}' give?"},
    "ko": {"list": "{o} 목록", "count_by": "{t}별 {s} 수", "values": "{o} {p}별 수", "action": "{o} {s}(으)로 변경",
           "viewer": "조회 담당", "operator": "운영자", "self": "본인 조회 ({o})",
           "question": "'{q}' 결과는 몇 행인가요?"},
}


class ReadError(ValueError):
    """A file could not be read as a table; `reason` is format, encoding, empty, workbook, workbook_size, openpyxl
    or convert (a value that does not fit the type asked for; `info` holds table, column, value and type)."""

    def __init__(self, message: str, reason: str = "", **info: Any):
        super().__init__(message)
        self.reason = reason
        self.info = info


@dataclass
class DraftRules:
    """What the draft decides by. The defaults are the ones above; a person can change any of them."""

    enum_max: int = ENUM_MAX  # most distinct values a text column may have and still get an allowed-value list
    enum_repeat: float = 2.0  # how often each of those values must repeat on average
    text_max: int = TEXT_MAX  # longest value still taken as a category
    infer_links: bool = True  # relations from names and values where no foreign key is declared
    link_tables: bool = True  # a table of two relation columns becomes a many-to-many link
    row_keys: bool = True  # files only: number the rows of a table no column can key
    title_hints: list[str] = field(default_factory=lambda: list(TITLE_HINTS))
    parent_hints: list[str] = field(default_factory=lambda: list(PARENT_HINTS))
    key_suffixes: list[str] = field(default_factory=lambda: list(KEY_SUFFIXES))
    generic_keys: list[str] = field(default_factory=lambda: list(GENERIC_KEYS))
    queries: list[str] = field(default_factory=lambda: list(QUERY_KINDS))
    states: bool = True  # a status column becomes a state machine; a history table gives its transitions
    roles: bool = True  # a viewer, an operator and, for a person-like table, a role scoped to one person's rows
    questions: bool = True  # each generated query with the answer it gives now, to check later changes against
    state_hints: list[str] = field(default_factory=lambda: list(STATE_HINTS))
    person_hints: list[str] = field(default_factory=lambda: list(PERSON_HINTS))
    table_prefixes: list[str] = field(default_factory=lambda: ["tb_", "tbl_"])  # left out of an object's name

    @classmethod
    def from_dict(cls, d: dict | None) -> DraftRules:
        r, d = cls(), d or {}
        for k in ("enum_max", "text_max"):
            if k in d:
                setattr(r, k, max(0, int(d[k])))
        if "enum_repeat" in d:
            r.enum_repeat = max(1.0, float(d["enum_repeat"]))
        for k in ("infer_links", "link_tables", "row_keys", "states", "roles", "questions"):
            if k in d:
                setattr(r, k, bool(d[k]))
        for k in ("title_hints", "parent_hints", "key_suffixes", "generic_keys", "state_hints", "person_hints",
                  "table_prefixes"):
            if k in d:
                items = d[k].split(",") if isinstance(d[k], str) else d[k]
                setattr(r, k, [str(x).strip().lower() for x in items if str(x).strip()])
        if "queries" in d:
            r.queries = [q for q in d["queries"] if q in QUERY_KINDS]
        return r

    def to_dict(self) -> dict:
        return asdict(self)


# ---- files ---------------------------------------------------------------------------------------------------


@dataclass
class Table:
    """Rows read from a file, before they are loaded into a database."""

    name: str
    columns: list[str]
    rows: list[list[str | None]]
    source: str = ""
    truncated: bool = False


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp949"):  # spreadsheet exports in Korea are often cp949
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ReadError("the file is neither UTF-8 nor CP949 text", "encoding")


def _header(cells: list[Any]) -> list[str]:
    out: list[str] = []
    for i, c in enumerate(cells):
        name = str(c).strip() if c is not None else ""
        name = name or f"column{i + 1}"
        base, n = name, 2
        while name in out:
            name, n = f"{base}_{n}", n + 1
        out.append(name)
    return out


def _table(name: str, source: str, raw: list[list[Any]], max_rows: int) -> Table:
    raw = [r for r in raw if any(c not in (None, "") for c in r)]
    if not raw:
        raise ReadError(f"{source}: no rows", "empty")
    cols = _header(raw[0])
    body = raw[1:]
    truncated = bool(max_rows) and len(body) > max_rows
    if truncated:
        body = body[:max_rows]
    rows = []
    for r in body:
        cells = [(_cell(c) if c not in (None, "") else None) for c in r[:len(cols)]]
        rows.append(cells + [None] * (len(cols) - len(cells)))
    return Table(name, cols, rows, source, truncated)


def _cell(v: Any) -> str | None:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime):
        return v.replace(microsecond=0).isoformat() if (v.hour, v.minute, v.second) != (0, 0, 0) else v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    return s or None


def read_csv(data: bytes, source: str, *, max_rows: int = 0) -> Table:
    text = _decode(data)
    if source.lower().endswith(".tsv"):
        delim = "\t"
    else:
        try:
            delim = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delim = ","
    raw = list(csv.reader(io.StringIO(text), delimiter=delim))
    return _table(Path(source).stem, source, raw, max_rows)


def read_xlsx(data: bytes, source: str, *, max_rows: int = 0) -> list[Table]:
    """Every sheet with rows; a workbook of one sheet is named after the file, otherwise after the sheets."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > XLSX_UNPACKED_MAX:
                raise ReadError(f"{source}: the workbook unpacks to more than {XLSX_UNPACKED_MAX >> 20}MB",
                                "workbook_size")
    except zipfile.BadZipFile:
        raise ReadError(f"{source}: not an .xlsx workbook", "workbook") from None
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ReadError("reading .xlsx needs openpyxl (pip install 'xgen-data-studio[xlsx]')", "openpyxl") from None
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    out = []
    try:
        sheets = wb.worksheets
        for ws in sheets:
            raw = []
            for r in ws.iter_rows(values_only=True):
                raw.append(list(r))
                if max_rows and len(raw) > max_rows + 1:
                    break
            try:
                t = _table(Path(source).stem if len(sheets) == 1 else ws.title, f"{source} · {ws.title}", raw,
                           max_rows)
            except ReadError:
                continue
            out.append(t)
    finally:
        wb.close()
    if not out:
        raise ReadError(f"{source}: no sheet has rows", "empty")
    return out


def read_file(data: bytes, source: str, *, max_rows: int = 0) -> list[Table]:
    ext = Path(source).suffix.lower()
    if ext in (".csv", ".tsv", ".txt"):
        return [read_csv(data, source, max_rows=max_rows)]
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(data, source, max_rows=max_rows)
    raise ReadError(f"{source}: give a .csv, .tsv or .xlsx file", "format")


# ---- types ---------------------------------------------------------------------------------------------------

_INT = re.compile(r"[-+]?(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)")  # no leading zeros: '00123' is a code
_DEC = re.compile(r"[-+]?(?:\d+|\d{1,3}(?:,\d{3})+)?\.\d+|[-+]?(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)")
_DATE = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\.?")
_DATETIME = re.compile(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?")
SQL_TYPE = {"integer": "INTEGER", "decimal": "REAL", "boolean": "BOOLEAN", "date": "DATE", "datetime": "TIMESTAMP",
            "string": "TEXT"}


def _as_date(v: str) -> str | None:
    m = _DATE.fullmatch(v)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def _as_datetime(v: str) -> str | None:
    m = _DATETIME.fullmatch(v)
    if not m:
        return _as_date(v)
    try:
        return datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6] or 0)).isoformat()
    except ValueError:
        return None


def infer_type(values: list[str]) -> str:
    """The narrowest type every value fits; text that only some values fit stays text."""
    vs = [v for v in values if v is not None]
    if not vs:
        return "string"
    if all(v.lower() in ("true", "false") for v in vs):
        return "boolean"
    if all(_INT.fullmatch(v) for v in vs):
        return "integer"
    if all(_DEC.fullmatch(v) for v in vs):
        return "decimal"
    if all(_as_date(v) for v in vs):
        return "date"
    if all(_as_datetime(v) for v in vs):
        return "datetime"
    return "string"


def convert(v: str | None, type_: str) -> Any:
    if v is None:
        return None
    if type_ == "integer":
        return int(v.replace(",", ""))
    if type_ == "decimal":
        return float(v.replace(",", ""))
    if type_ == "boolean":
        low = v.strip().lower()
        if low in ("true", "1", "y", "yes"):
            return 1
        if low in ("false", "0", "n", "no"):
            return 0
        raise ValueError(f"{v!r} is not a boolean")
    if type_ == "date":
        return _as_date(v)
    if type_ == "datetime":
        return _as_datetime(v)
    return v


def declared_type(sql_type: str) -> str:
    u = (sql_type or "").upper()
    if "INT" in u:
        return "integer"
    if "BOOL" in u:
        return "boolean"
    if any(k in u for k in ("NUMERIC", "DECIMAL", "REAL", "FLOA", "DOUB", "MONEY")):
        return "decimal"
    if "TIMESTAMP" in u or "DATETIME" in u:
        return "datetime"
    if u == "DATE":
        return "date"
    return "string"


@dataclass
class Loaded:
    table: str
    source: str
    rows: int
    columns: int
    truncated: bool = False
    row_key: str = ""


def load_sqlite(tables: list[Table], backend, *, row_keys: bool = True,
                types: dict[str, dict[str, str]] | None = None) -> list[Loaded]:
    """One typed table per file; a table with no column of present, distinct values gets a row number to key it.

    `types` sets the type of some columns ({table: {column: type}}) instead of reading it from the values; a value
    that does not fit raises ReadError(reason="convert").
    """
    out = []
    types = types or {}
    taken = {r[0].lower() for r in backend.fetch("SELECT name FROM sqlite_master WHERE type = 'table'")}
    for t in tables:
        name, n = t.name, 2
        while name.lower() in taken:
            name, n = f"{t.name}_{n}", n + 1
        taken.add(name.lower())
        asked = types.get(t.name, {})
        kinds = [asked.get(c) or infer_type([r[i] for r in t.rows]) for i, c in enumerate(t.columns)]
        kinds = ["string" if k == "enum" else k for k in kinds]
        cols = list(t.columns)
        rows = []
        for r in t.rows:
            row = []
            for i in range(len(cols)):
                try:
                    v = convert(r[i], kinds[i])
                except ValueError:
                    v = None
                if v is None and r[i] is not None:
                    raise ReadError(f"{t.name}.{cols[i]}: {r[i]!r} is not {kinds[i]}", "convert", table=t.name,
                                    column=cols[i], value=r[i], type=kinds[i])
                row.append(v)
            rows.append(row)
        keyed = any(all(r[i] is not None for r in rows) and len({r[i] for r in rows}) == len(rows)
                    for i in range(len(cols))) and bool(rows)
        row_key = ""
        if not keyed and row_keys:
            row_key, n = ROW_KEY, 2
            while row_key in cols:
                row_key, n = f"{ROW_KEY}_{n}", n + 1
            cols.append(row_key)
            kinds.append("integer")
            rows = [r + [i + 1] for i, r in enumerate(rows)]
        ddl = ", ".join(f"{qi(c)} {SQL_TYPE[ty]}" for c, ty in zip(cols, kinds))
        backend.conn.execute(f"CREATE TABLE {qi(name)} ({ddl})")
        backend.conn.executemany(f"INSERT INTO {qi(name)} VALUES ({', '.join('?' * len(cols))})", rows)
        backend.conn.commit()
        out.append(Loaded(name, t.source, len(rows), len(t.columns), t.truncated, row_key))
    return out


# ---- what the database holds ---------------------------------------------------------------------------------


@dataclass
class ColumnProfile:
    name: str
    declared: str
    type: str
    nulls: int
    distinct: int
    max_len: int
    values: list[Any] = field(default_factory=list)


@dataclass
class TableProfile:
    name: str
    rows: int
    columns: list[ColumnProfile]
    primary_key: list[str]
    foreign_keys: list[tuple[str, str, str]]

    def col(self, name: str) -> ColumnProfile:
        return next(c for c in self.columns if c.name == name)


def _catalog(backend) -> list[tuple[str, list[tuple[str, str]], list[str], list[tuple[str, str, str]]]]:
    dialect = backend.capabilities.dialect
    out = []
    if dialect == "sqlite":
        names = [r[0] for r in backend.fetch(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for t in names:
            info = backend.fetch(f"PRAGMA table_info({qi(t)})")
            pk = [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]
            fk = backend.fetch(f"PRAGMA foreign_key_list({qi(t)})")  # id, seq, table, from, to, ...
            single = {r[0] for r in fk if sum(x[0] == r[0] for x in fk) == 1}
            out.append((t, [(r[1], r[2] or "") for r in info], pk, [(r[3], r[2], r[4] or "") for r in fk
                                                                    if r[0] in single]))
        return out
    if dialect != "postgres":
        raise ValueError(f"drafting reads the catalog of SQLite or PostgreSQL, not {dialect}")
    names = [r[0] for r in backend.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema() "
        "AND table_type = 'BASE TABLE' ORDER BY table_name")]
    for t in names:
        cols = backend.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = "
                             "current_schema() AND table_name = ? ORDER BY ordinal_position", (t,))
        join = ("FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu "
                "ON kcu.constraint_name = tc.constraint_name AND kcu.table_schema = tc.table_schema ")
        pk = [r[0] for r in backend.fetch(
            f"SELECT kcu.column_name {join}WHERE tc.table_schema = current_schema() AND tc.table_name = ? "
            "AND tc.constraint_type = 'PRIMARY KEY' ORDER BY kcu.ordinal_position", (t,))]
        rows = backend.fetch(
            f"SELECT tc.constraint_name, kcu.column_name, ccu.table_name, ccu.column_name {join}"
            "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name "
            "AND ccu.table_schema = tc.table_schema WHERE tc.table_schema = current_schema() AND tc.table_name = ? "
            "AND tc.constraint_type = 'FOREIGN KEY'", (t,))
        single = {c for c in {r[0] for r in rows} if sum(r[0] == c for r in rows) == 1}
        out.append((t, [(str(c), str(d)) for c, d in cols], pk, [(r[1], r[2], r[3]) for r in rows if r[0] in single]))
    return out


def profile(backend, tables: list[str] | None = None, rules: DraftRules | None = None) -> list[TableProfile]:
    """Row counts, empty and distinct values per column, and the values of columns that look like categories."""
    rules = rules or DraftRules()
    sqlite = backend.capabilities.dialect == "sqlite"
    out = []
    for name, cols, pk, fks in _catalog(backend):
        if tables is not None and name not in tables:
            continue
        t = qi(name)
        parts = ["COUNT(*)"]
        for c, _ in cols:
            parts += [f"COUNT({qi(c)})", f"COUNT(DISTINCT {qi(c)})", f"MAX(LENGTH(CAST({qi(c)} AS TEXT)))"]
        stats = backend.fetch(f"SELECT {', '.join(parts)} FROM {t}")[0]
        rows = int(stats[0])
        profs = []
        for i, (c, declared) in enumerate(cols):
            nonnull, distinct, max_len = int(stats[1 + 3 * i]), int(stats[2 + 3 * i]), int(stats[3 + 3 * i] or 0)
            ty = declared_type(declared)
            if sqlite and ty == "string" and nonnull:  # SQLite has no date type; ISO text is the convention
                vals = [str(r[0]) for r in backend.fetch(f"SELECT DISTINCT {qi(c)} FROM {t} WHERE {qi(c)} IS NOT NULL")]
                guess = infer_type(vals)
                if guess in ("date", "datetime") and all(v == convert(v, guess) for v in vals):
                    ty = guess
            p = ColumnProfile(c, declared, ty, rows - nonnull, distinct, max_len)
            if ty == "string" and 0 < distinct <= rules.enum_max and max_len <= rules.text_max \
                    and distinct * rules.enum_repeat <= nonnull:
                p.values = [r[0] for r in backend.fetch(
                    f"SELECT DISTINCT {qi(c)} FROM {t} WHERE {qi(c)} IS NOT NULL ORDER BY {qi(c)}")]
            profs.append(p)
        out.append(TableProfile(name, rows, profs, pk, fks))
    return out


# ---- names ---------------------------------------------------------------------------------------------------

_INITIAL = "g kk n d tt r m b pp s ss _ j jj ch k t p h".split()
_MEDIAL = "a ae ya yae eo e yeo ye o wa wae oe yo u wo we wi yu eu ui i".split()
_FINAL = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t",
          "ng", "t", "t", "k", "t", "p", "t"]


def romanize(text: str) -> str:
    """Hangul syllables in the Revised Romanization letters (without the sound-change rules)."""
    out = []
    for ch in text:
        n = ord(ch) - 0xAC00
        if 0 <= n < 11172:
            ini = _INITIAL[n // 588]
            out.append(("" if ini == "_" else ini) + _MEDIAL[(n % 588) // 28] + _FINAL[n % 28])
        else:
            out.append(ch)
    return "".join(out)


def _words(text: str) -> list[str]:
    s = romanize(text)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return [w.lower() for w in re.split(r"[^A-Za-z0-9]+", s) if w]


def singular(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def _snake(text: str, fallback: str) -> str:
    s = "_".join(_words(text))
    if not s:
        return fallback
    return s if not s[0].isdigit() else f"n{s}"


def _pascal(text: str, fallback: str) -> str:
    w = _words(text)
    if not w:
        return fallback
    w[-1] = singular(w[-1])
    s = "".join(x[:1].upper() + x[1:] for x in w)
    return s if not s[0].isdigit() else f"N{s}"


def _camel(text: str, fallback: str) -> str:
    s = _pascal(text, "")
    return s[:1].lower() + s[1:] if s else fallback


def _stem(col: str, suffixes=KEY_SUFFIXES) -> str:
    low = col.lower()
    for suf in suffixes:
        if low.endswith(suf) and len(low) > len(suf):
            return col[:-len(suf)].rstrip("_")
    return col


# ---- the draft -----------------------------------------------------------------------------------------------


@dataclass
class PlannedProperty:
    name: str
    column: str
    type: str
    label: str
    values: list[str] = field(default_factory=list)
    nulls: int = 0
    distinct: int = 0
    declared: str = ""
    labels: dict[str, str] = field(default_factory=dict)  # an allowed value's name (from a code definition)


@dataclass
class PlannedObject:
    name: str
    table: str
    label: str
    key: str
    key_why: str
    rows: int
    properties: list[PlannedProperty]
    title: str = ""
    series: dict[str, str] = field(default_factory=dict)  # a table of past states: {time: property, of: link}

    def prop_of(self, column: str) -> PlannedProperty:
        return next(p for p in self.properties if p.column == column)


@dataclass
class PlannedLink:
    name: str
    source: str
    target: str
    label: str
    why: str
    cardinality: str = "many_to_one"
    on: tuple[str, str] | None = None
    via: tuple[str, str, str] | None = None
    column: str = ""
    values: int = 0


@dataclass
class PlannedStates:
    object: str
    property: str
    states: list[str]
    initial: str = ""
    transitions: list[tuple[str, str, int]] = field(default_factory=list)  # from, to, times seen
    why: str = "values"  # values: the allowed values only; history: read from a table of past states
    history: str = ""


@dataclass
class Draft:
    """The plan drawn from the data, which the review can trim and relabel before it becomes modules."""

    name: str
    label: str
    objects: list[PlannedObject]
    links: list[PlannedLink]
    tables: list[TableProfile]
    skipped: list[dict] = field(default_factory=list)
    loaded: list[Loaded] = field(default_factory=list)
    origin: dict[str, Any] = field(default_factory=dict)
    lang: str = "en"
    rules: DraftRules = field(default_factory=DraftRules)
    no_queries: list[str] = field(default_factory=list)
    states: list[PlannedStates] = field(default_factory=list)
    answers: dict[str, int] = field(default_factory=dict)  # generated query -> rows it gives now
    decisions: dict[str, dict] = field(default_factory=dict)  # drawn from past outcomes (induce.py), then edited

    def revise(self, *, drop: list[str] = (), labels: dict[str, str] | None = None, keys: dict[str, str] | None = None,
               types: dict[str, str] | None = None, values: dict[str, list[str]] | None = None,
               cardinality: dict[str, str] | None = None, add_links: list[dict] = ()) -> Draft:
        """A person's edits on top of the draft; the draft itself stays as it was.

        drop: object:X, link:y, property:X.p, query:q. labels: object:X, property:X.p, link:y -> label.
        keys: X -> property. types and values: X.p -> type, X.p -> allowed values. cardinality: y -> cardinality.
        add_links: {source, property, target, label?, cardinality?}, joined on the target's key.
        """
        labels, keys, types, values = labels or {}, keys or {}, types or {}, values or {}
        cardinality = cardinality or {}
        gone = {e.split(":", 1)[1] for e in drop if e.startswith("object:")}
        cut = {e.split(":", 1)[1] for e in drop if e.startswith("link:")}
        props_gone = {e.split(":", 1)[1] for e in drop if e.startswith("property:")}
        for k, t in types.items():
            if t not in TYPES:
                raise ValueError(f"{k}: type '{t}' is not one of {TYPES}")
        for k, c in cardinality.items():
            if c not in CARDINALITIES:
                raise ValueError(f"{k}: cardinality '{c}' is not one of {CARDINALITIES}")
        objs = []
        for o in self.objects:
            if o.name in gone:
                continue
            key = keys.get(o.name, o.key)
            if key not in {p.name for p in o.properties}:
                raise ValueError(f"{o.name} has no property '{key}' to key it")
            props = []
            for p in o.properties:
                ref = f"{o.name}.{p.name}"
                if ref in props_gone and p.name != key:
                    continue
                ptype = types.get(ref, p.type)
                vals = [str(v) for v in values[ref]] if ref in values else (p.values if ptype == "enum" else [])
                props.append(PlannedProperty(**{**asdict(p), "type": ptype, "values": vals if ptype == "enum" else [],
                                                "label": labels.get(f"property:{ref}", p.label),
                                                "labels": {k: v for k, v in p.labels.items() if k in vals}}))
            kept = {p.name for p in props}
            objs.append(PlannedObject(**{**asdict(o), "properties": props, "key": key,
                                         "title": o.title if o.title in kept else "",
                                         "label": labels.get(f"object:{o.name}", o.label)}))
        by_name = {o.name: o for o in objs}

        def bound(lk: PlannedLink) -> bool:  # a relation goes with the property it is joined on
            if lk.source not in by_name or lk.target not in by_name:
                return False
            if not lk.on:
                return True
            return lk.on[0] in {p.name for p in by_name[lk.source].properties} and \
                lk.on[1] in {p.name for p in by_name[lk.target].properties}

        links = [PlannedLink(**{**asdict(lk), "label": labels.get(f"link:{lk.name}", lk.label),
                                "cardinality": cardinality.get(lk.name, lk.cardinality)})
                 for lk in self.links if lk.name not in cut and bound(lk)]
        names = set(by_name) | {p.name for o in objs for p in o.properties} | {lk.name for lk in links}
        for a in add_links:
            src, dst = by_name.get(str(a.get("source", ""))), by_name.get(str(a.get("target", "")))
            prop = str(a.get("property", ""))
            if src is None or dst is None or prop not in {p.name for p in src.properties}:
                raise ValueError(f"cannot link {a.get('source')}.{prop} to {a.get('target')}")
            n0 = _camel(f"{prop}_{dst.name}" if _stem(prop, self.rules.key_suffixes) == prop
                        else _stem(prop, self.rules.key_suffixes), "related")
            nm, n = n0, 2
            while nm in names:
                nm, n = f"{n0}{n}", n + 1
            names.add(nm)
            card = str(a.get("cardinality") or "many_to_one")
            if card not in CARDINALITIES:
                raise ValueError(f"cardinality '{card}' is not one of {CARDINALITIES}")
            links.append(PlannedLink(nm, src.name, dst.name, str(a.get("label") or dst.label), "manual", card,
                                     on=(prop, dst.key), column=next(p.column for p in src.properties
                                                                      if p.name == prop)))
        no_queries = sorted(set(self.no_queries) | {e.split(":", 1)[1] for e in drop if e.startswith("query:")})
        no_states = {e.split(":", 1)[1] for e in drop if e.startswith("states:")}
        states = [s for s in self.states if s.object in by_name and s.object not in no_states
                  and any(p.name == s.property and p.type == "enum" for p in by_name[s.object].properties)]
        decisions = {k: v for k, v in self.decisions.items() if f"decision:{k}" not in drop
                     and v.get("target") in by_name}
        return Draft(self.name, self.label, objs, links, self.tables, self.skipped, self.loaded, self.origin,
                     self.lang, self.rules, no_queries, states, dict(self.answers), decisions)

    # ---- rules, actions, roles, questions ----

    def actions(self) -> dict[str, dict]:
        """One action per state a history shows things moving into; the state machine checks the move."""
        words = LABELS.get(self.lang, LABELS["en"])
        by_name = {o.name: o for o in self.objects}
        out: dict[str, dict] = {}
        for s in self.states:
            o = by_name[s.object]
            for target in dict.fromkeys(t for _, t, _ in s.transitions):
                name = f"set{o.name}{_pascal(target, 'State')}"
                out[name] = {"label": words["action"].format(o=o.label, s=target), "target": o.name,
                             "transition_to": target, "approval": True}
        return out

    def person(self) -> PlannedObject | None:
        """The table of people whose own rows a scoped role reads, by the person name hints."""
        hints = [h.lower() for h in self.rules.person_hints]
        for o in self.objects:
            words = {o.table.lower(), o.label.lower(), o.name.lower()}
            if any(h and any(h in w for w in words) for h in hints):
                return o
        return None

    def roles(self) -> dict[str, dict]:
        if not self.rules.roles:
            return {}
        words = LABELS.get(self.lang, LABELS["en"])
        own = f"{self.name}-"  # named after the module, so a library's own roles stay apart
        out: dict[str, dict] = {f"{own}viewer": {"label": words["viewer"], "read": ["*"], "run": ["*"]}}
        if self.actions():
            out[f"{own}operator"] = {"label": words["operator"], "read": ["*"], "run": ["*"], "request": ["*"],
                               "execute": ["*"]}
        p = self.person()
        if p is not None:
            filters = {p.name: {"eq": [f"$self.{p.key}", {"principal": p.key}]}}
            for lk in self.links:
                if lk.target == p.name and lk.on and lk.cardinality in ("many_to_one", "one_to_one"):
                    filters.setdefault(lk.source, {"eq": [f"$self.{lk.on[0]}", {"principal": p.key}]})
            queries = [q for q, v in self.queries().items() if set(v["query"]["match"].values()) <= set(filters)]
            out[f"{own}self"] = {"label": words["self"].format(o=p.label), "read": sorted(filters),
                                   "row_filters": filters, "run": queries}
        return out

    def questions(self) -> list[dict]:
        if not self.rules.questions:
            return []
        words = LABELS.get(self.lang, LABELS["en"])
        out = []
        for i, (name, q) in enumerate(self.queries().items()):
            if name in self.answers and not q.get("params"):
                out.append({"id": f"{self.name}-q{i + 1}", "text": words["question"].format(q=q["label"]), "query": name,
                            "expect": {"rows": self.answers[name]}})
        return out

    # ---- as modules ----

    def queries(self, *, dropped: bool = False) -> dict[str, dict]:
        """The generated queries of the kinds the rules ask for; with `dropped`, also those the review left out."""
        words = LABELS.get(self.lang, LABELS["en"])
        by_name = {o.name: o for o in self.objects}
        kinds = self.rules.queries
        out: dict[str, dict] = {}
        for o in self.objects if "list" in kinds else ():
            shown = [o.key] + ([o.title] if o.title and o.title != o.key else [])
            shown += [p.name for p in o.properties if p.name not in shown][:6 - len(shown)]
            out[f"list{o.name}"] = {"label": words["list"].format(o=o.label), "query": {
                "match": {"x": o.name}, "return": [f"x.{p}" for p in shown], "order": [o.key], "limit": 100}}
        for lk in self.links if "count_by" in kinds else ():
            if lk.via or lk.source == lk.target:
                continue
            s, t = by_name[lk.source], by_name[lk.target]
            shown = [t.key] + ([t.title] if t.title and t.title != t.key else [])  # grouped by the key, not a name
            out[f"{_camel(s.name, 'count')}Per{t.name}"] = {
                "label": words["count_by"].format(s=s.label, t=t.label), "query": {
                    "match": {"s": s.name, "t": t.name}, "edges": [["s", lk.name, "t"]],
                    "return": [f"t.{c}" for c in shown] + [{"count": "s", "as": "n"}], "order": ["-n", t.key]}}
        for o in self.objects if "values" in kinds else ():
            for p in o.properties:
                if p.type == "enum":
                    out[f"{_camel(o.name, 'x')}By{_pascal(p.name, 'Value')}"] = {
                        "label": words["values"].format(o=o.label, p=p.label), "query": {
                            "match": {"x": o.name}, "return": [f"x.{p.name}", {"count": "x", "as": "n"}],
                            "order": [p.name]}}
        return out if dropped else {k: v for k, v in out.items() if k not in self.no_queries}

    def modules(self) -> list[Module]:
        objects, bind_objects = {}, {}
        for o in self.objects:
            props = {}
            for p in o.properties:
                d: dict[str, Any] = {"type": p.type, "label": p.label}
                if p.values:
                    d["values"] = list(p.values)
                if p.labels:
                    d["labels"] = dict(p.labels)
                if p.name == o.key:
                    d["required"] = True
                props[p.name] = d
            objects[o.name] = {"label": o.label, "key": o.key, **({"title": o.title} if o.title else {}),
                               **({"series": dict(o.series)} if o.series else {}), "properties": props}
            sm = next((s for s in self.states if s.object == o.name), None)
            if sm is not None:
                objects[o.name]["states"] = {"property": sm.property, "states": list(sm.states),
                                             **({"initial": sm.initial} if sm.initial else {}),
                                             "transitions": [{"from": a, "to": b} for a, b, _ in sm.transitions]}
            cols = {p.name: p.column for p in o.properties if p.name != p.column}
            bind_objects[o.name] = {"table": o.table, **({"columns": cols} if cols else {})}
        links, bind_links = {}, {}
        for lk in self.links:
            links[lk.name] = {"from": lk.source, "to": lk.target, "cardinality": lk.cardinality, "label": lk.label}
            bind_links[lk.name] = {"on": {lk.on[0]: lk.on[1]}} if lk.on else \
                {"via": {"table": lk.via[0], "source": lk.via[1], "target": lk.via[2]}}
        body = {s: {} for s in SECTIONS}
        body.update({"objects": objects, "links": links, "queries": self.queries(), "questions": self.questions(),
                     "exclusive": [], "actions": self.actions(), "roles": self.roles(),
                     "decisions": {k: {kk: vv for kk, vv in v.items() if kk != "report"}
                                   for k, v in self.decisions.items()}})
        where = self.origin.get("detail", "")
        domain = Module(name=self.name, version="0.1.0", kind="domain", label=self.label, body=body,
                        description=where, namespace=f"https://example.org/{self.name}#")
        binding = Module(name=f"{self.name}-bindings", version="0.1.0", kind="binding",
                         label=f"{self.label} · binding" if self.lang == "en" else f"{self.label} 바인딩",
                         description=where, requires=[Requirement(self.name)],
                         body={**{s: {} for s in SECTIONS}, "questions": [], "exclusive": []},
                         extend={"objects": bind_objects, "links": bind_links})
        return [domain, binding]

    def steps(self) -> list[dict]:
        """What was read and decided, in the order it was decided, with the reason for each."""
        by_table = {lo.table: lo for lo in self.loaded}
        read = [{"table": t.name, "rows": t.rows, "columns": len(t.columns),
                 "source": by_table[t.name].source if t.name in by_table else "",
                 "truncated": by_table[t.name].truncated if t.name in by_table else False,
                 "row_key": by_table[t.name].row_key if t.name in by_table else ""} for t in self.tables]
        objects = [{"element": f"object:{o.name}", "label": o.label, "table": o.table, "key": o.key,
                    "why": o.key_why, "rows": o.rows} for o in self.objects]
        props = []
        for o in self.objects:
            for p in o.properties:
                props.append({"element": f"property:{o.name}.{p.name}", "object": o.name, "label": p.label,
                              "column": p.column, "type": p.type, "values": p.values, "nulls": p.nulls,
                              "distinct": p.distinct, "rows": o.rows, "key": p.name == o.key, "declared": p.declared,
                              "title": p.name == o.title})
        links = [{"element": f"link:{lk.name}", "label": lk.label, "from": lk.source, "to": lk.target,
                  "why": lk.why, "column": lk.column, "via": lk.via[0] if lk.via else "", "values": lk.values,
                  "cardinality": lk.cardinality} for lk in self.links]
        queries = [{"element": f"query:{k}", "label": v["label"], "on": k not in self.no_queries}
                   for k, v in self.queries(dropped=True).items()]
        rules = [{"element": f"states:{s.object}", "kind": "states", "object": s.object, "property": s.property,
                  "states": s.states, "initial": s.initial, "why": s.why, "history": s.history,
                  "transitions": [{"from": a, "to": b, "seen": n} for a, b, n in s.transitions]} for s in self.states]
        rules += [{"element": f"action:{k}", "kind": "action", "label": v["label"], "object": v["target"],
                   "to": v["transition_to"]} for k, v in self.actions().items()]
        rules += [{"element": f"role:{k}", "kind": "role", "label": v["label"], "read": v["read"],
                   "filters": sorted(v.get("row_filters", {}))} for k, v in self.roles().items()]
        rules += [{"element": f"question:{q['id']}", "kind": "question", "text": q["text"], "query": q["query"],
                   "expect": q["expect"]} for q in self.questions()]
        rules += [{"element": f"decision:{k}", "kind": "decision", "label": v.get("label", k),
                   "object": v.get("target"), "rules": len(v.get("rules") or []), "report": v.get("report", {})}
                  for k, v in self.decisions.items()]
        binds = [{"element": f"object:{o.name}", "table": o.table, "columns": len(o.properties)} for o in self.objects]
        binds += [{"element": f"link:{lk.name}", "table": lk.via[0] if lk.via else "", "column": lk.column}
                  for lk in self.links]
        return [{"id": "read", "items": read}, {"id": "objects", "items": objects, "skipped": self.skipped},
                {"id": "properties", "items": props}, {"id": "links", "items": links},
                {"id": "queries", "items": queries}, {"id": "rules", "items": rules},
                {"id": "bindings", "items": binds}]


def _names_target(col: str, own: TableProfile, other: TableProfile, key: str, rules: DraftRules) -> bool:
    """Does a column's name point at another table's key: the same name, or <table>_<key>, or <table>_id."""
    c, k = col.lower(), key.lower()
    if other.name == own.name:
        return c != k and c.startswith(tuple(rules.parent_hints)) and _stem(c, rules.key_suffixes) != c
    base = "_".join(_words(other.name))
    one = "_".join(_words(other.name)[:-1] + [singular(_words(other.name)[-1])]) if _words(other.name) else base
    return (c == k and k not in rules.generic_keys) or c in (f"{one}_{k}", f"{base}_{k}", f"{one}_id", f"{base}_id")


def draft(backend, *, name: str = "my-data", label: str = "", tables: list[str] | None = None,
          loaded: list[Loaded] | None = None, origin: dict | None = None, lang: str = "en",
          rules: DraftRules | None = None, definitions=None) -> Draft:
    """Read the catalog and the values, then decide objects, keys, properties, relations and their bindings.

    `definitions` (definitions.Definitions) names the objects and properties and gives coded columns their allowed
    values with their names; with `definitions.schema_backend` it drafts from the schema alone."""
    rules = rules or DraftRules()
    profs = profile(backend, tables, rules)
    loaded = loaded or []
    row_keys = {lo.table: lo.row_key for lo in loaded if lo.row_key}

    # keys: a declared primary key, else a column of present, distinct values (the most key-like name first)
    keys: dict[str, tuple[str, str]] = {}
    for t in profs:
        if len(t.primary_key) == 1:
            keys[t.name] = (t.primary_key[0], "primary_key")
            continue
        unique = [c for c in t.columns if t.rows and not c.nulls and c.distinct == t.rows and c.name != row_keys.get(
            t.name)]

        def rank(c: ColumnProfile, t: TableProfile = t) -> tuple:
            low = c.name.lower()
            return (low not in ("id", f"{singular(t.name.lower())}_id", f"{t.name.lower()}_id"),
                    not low.endswith(tuple(rules.key_suffixes)), t.columns.index(c))

        if unique:
            keys[t.name] = (min(unique, key=rank).name, "unique")
        elif t.name in row_keys:
            keys[t.name] = (row_keys[t.name], "row_number")

    # relations: declared foreign keys, else a column named after a key whose values all appear in that key
    refs: dict[str, list[tuple[str, str, str, int]]] = {t.name: [] for t in profs}
    for t in profs:
        for col, rt, rc in t.foreign_keys:
            if rt in keys and (not rc or rc == keys[rt][0]):
                refs[t.name].append((col, rt, "foreign_key", t.rows - t.col(col).nulls))
        declared = {r[0] for r in refs[t.name]}
        for c in t.columns if rules.infer_links else ():
            if c.name in declared or c.name in t.primary_key or c.name == row_keys.get(t.name) \
                    or not (t.rows - c.nulls):
                continue
            for other in profs:
                if other.name not in keys:
                    continue
                k = keys[other.name][0]
                if other.col(k).type != c.type or not _names_target(c.name, t, other, k, rules):
                    continue
                missing = backend.fetch(
                    f"SELECT COUNT(*) FROM {qi(t.name)} s WHERE s.{qi(c.name)} IS NOT NULL AND NOT EXISTS "
                    f"(SELECT 1 FROM {qi(other.name)} o WHERE o.{qi(k)} = s.{qi(c.name)})")[0][0]
                if not missing:
                    refs[t.name].append((c.name, other.name, "values_included", t.rows - c.nulls))
                    break

    # a table of two relation columns and nothing else is a many-to-many relation, not an object
    joins = {t.name for t in profs if rules.link_tables and not t.primary_key and len(refs[t.name]) == 2 and
             {c.name for c in t.columns} - {row_keys.get(t.name, "")} == {r[0] for r in refs[t.name]}}
    skipped = [{"table": t.name, "why": "composite_key" if len(t.primary_key) > 1 else "no_key"}
               for t in profs if t.name not in keys and t.name not in joins]

    objects: dict[str, PlannedObject] = {}
    seen_types: dict[str, str] = {}
    taken: set[str] = set()
    for i, t in enumerate(profs):
        if t.name in joins or t.name not in keys:
            continue
        bare = next((t.name[len(x):] for x in rules.table_prefixes
                     if t.name.lower().startswith(x) and len(t.name) > len(x)), t.name)
        oname, n = _pascal(bare, f"Object{i + 1}"), 2
        while oname in taken:
            oname, n = f"{_pascal(bare, f'Object{i + 1}')}{n}", n + 1
        taken.add(oname)
        fk_cols = {r[0] for r in refs[t.name]}
        props, used = [], set()
        for j, c in enumerate(t.columns):
            ptype = "enum" if c.values and c.name not in fk_cols and c.name != keys[t.name][0] else c.type
            pname = _snake(c.name, f"col{j + 1}")
            if pname in used or (pname in seen_types and seen_types[pname] != ptype):
                pname = f"{_snake(oname, 'x')}_{pname}"
            base, n = pname, 2
            while pname in used or (pname in seen_types and seen_types[pname] != ptype):
                pname, n = f"{base}_{n}", n + 1
            used.add(pname)
            seen_types.setdefault(pname, ptype)
            props.append(PlannedProperty(pname, c.name, ptype, c.name, [str(v) for v in c.values] if ptype == "enum"
                                         else [], c.nulls, c.distinct, c.declared))
        o = PlannedObject(oname, t.name, t.name, "", keys[t.name][1], t.rows, props)
        o.key = o.prop_of(keys[t.name][0]).name
        o.title = next((p.name for p in props if p.type == "string" and p.name != o.key and p.column not in fk_cols
                        and any(p.column.lower() == h or p.column.lower().endswith(("_" + h, h))
                                for h in rules.title_hints)),
                       "")
        objects[t.name] = o

    if definitions is not None:
        _annotate(objects, definitions)
    names = set(taken) | {p.name for o in objects.values() for p in o.properties}
    links: list[PlannedLink] = []

    def link_name(text: str, fallback: str) -> str:
        n0 = _camel(text, fallback)
        nm, n = n0, 2
        while nm in names:
            nm, n = f"{n0}{'Link' if n == 2 else n}", n + 1
        names.add(nm)
        return nm

    for t in profs:
        if t.name in joins:
            (ca, ta, wa, va), (cb, tb, _, _) = refs[t.name]
            if ta in objects and tb in objects:
                links.append(PlannedLink(link_name(t.name, "related"), objects[ta].name, objects[tb].name, t.name, wa,
                                         "many_to_many", via=(t.name, ca, cb), column=f"{ca}, {cb}", values=va))
            continue
        if t.name not in objects:
            continue
        src = objects[t.name]
        for col, rt, why, nvals in refs[t.name]:
            if rt not in objects:
                continue
            dst = objects[rt]
            one = col == keys[t.name][0]  # a snapshot of values cannot show a relation is one-to-one; a key can
            stem = _stem(col, rules.key_suffixes)
            links.append(PlannedLink(link_name(stem if stem != col else f"{col}_ref", dst.name),
                                     src.name, dst.name, dst.label, why, "one_to_one" if one else "many_to_one",
                                     on=(src.prop_of(col).name, dst.key), column=col, values=nvals))
    origin = origin or {}
    d = Draft(name, label or name, list(objects.values()), links, profs, skipped, loaded, origin, lang, rules)
    if rules.states:
        d.states = _states(backend, d, refs, rules)
    if rules.questions:
        d.answers = _answers(backend, d)
    return d


def _annotate(objects: dict[str, PlannedObject], defs) -> None:
    """Names from the definitions, and the code values (with their names) of the columns that hold a code group."""
    strip = re.compile(r"\s*\([A-Za-z]{1,6}\d{1,6}\)\s*")
    for table, o in objects.items():
        td = defs.table(table)
        if td is None:
            continue
        if td.label:
            o.label = td.label
        for p in o.properties:
            cd = td.column(p.column)
            if cd is None:
                continue
            if cd.label:
                p.label = strip.sub(" ", cd.label).strip() or p.label
            g = defs.code_of(cd)
            if g is not None and g.values and p.name != o.key and p.type in ("string", "enum"):
                p.type, p.values = "enum", [v["code"] for v in g.values]
                p.labels = {v["code"]: v["name"] for v in g.values if v.get("name")}


def _states(backend, d: Draft, refs: dict, rules: DraftRules) -> list[PlannedStates]:
    """A status column, named by the state hints, with allowed values; a table that keeps past states of the same
    rows (a relation to it, the same values, a time column) gives the transitions in the order they happened."""
    out = []
    by_table = {o.table: o for o in d.objects}
    profs = {t.name: t for t in d.tables}
    hints = [h.lower() for h in rules.state_hints]
    candidates = []
    for o in d.objects:
        prop = next((p for p in o.properties if p.type == "enum" and p.name != o.key and p.values
                     and any(h in p.column.lower() for h in hints)), None)
        if prop is not None:
            candidates.append((o, prop))
    histories: set[str] = set()
    for o, prop in candidates:
        sm = PlannedStates(o.name, prop.name, list(prop.values))
        for t, rs in refs.items():
            if t == o.table or t not in profs:
                continue
            fk = next((c for c, rt, _, _ in rs if rt == o.table), None)
            if fk is None:
                continue
            tp = profs[t]
            status = next((c for c in tp.columns if c.name != fk and c.values and len(c.values) > 1
                           and {str(v) for v in c.values} <= set(prop.values)), None)
            when = next((c for c in tp.columns if c.type in ("date", "datetime")), None)
            if status is None or when is None:
                continue
            rows = backend.fetch(f"SELECT {qi(fk)}, {qi(status.name)} FROM {qi(t)} WHERE {qi(fk)} IS NOT NULL "
                                 f"AND {qi(status.name)} IS NOT NULL ORDER BY {qi(fk)}, {qi(when.name)}")
            seen: dict[tuple[str, str], int] = {}
            first: dict[str, int] = {}
            last_key, last = None, None
            for k, s in rows:
                s = str(s)
                if k != last_key:
                    first[s] = first.get(s, 0) + 1
                elif s != last:
                    seen[(last, s)] = seen.get((last, s), 0) + 1
                last_key, last = k, s
            if seen:
                sm.transitions = [(a, b, n) for (a, b), n in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))]
                sm.initial = max(first.items(), key=lambda kv: (kv[1], kv[0]))[0] if first else ""
                sm.why, sm.history = "history", t
                h = by_table.get(t)
                lk = next((x for x in d.links if h is not None and x.source == h.name and x.target == o.name), None)
                if h is not None and lk is not None:  # the history is a series of the object's past states
                    h.series = {"time": h.prop_of(when.name).name, "of": lk.name}
                    histories.add(h.name)
                break
        out.append(sm)
    return [sm for sm in out if sm.object not in histories]


def _answers(backend, d: Draft) -> dict[str, int]:
    """How many rows each generated query gives on the data it was drawn from."""
    from xgen_data_studio.ir import Query
    from xgen_data_studio.modules import compose

    try:
        onto = compose(d.modules()).ontology
    except Exception:  # a draft that does not compose has no answers yet; the check shows why
        return {}
    out = {}
    for name, q in d.queries().items():
        try:
            compiled = backend.compiler(onto).compile(Query.from_dict(q["query"]))
            out[name] = len(backend.execute(compiled).rows)
        except Exception:
            continue
    return out


def studio_from(d: Draft, source, *, library=None, graph: bool = True, **kw):
    """A studio over the draft's modules that reads `source`, projected into an in-process RDF store."""
    from xgen_data_studio.library import OverlayLibrary
    from xgen_data_studio.studio import Studio

    modules = d.modules()
    st = Studio.from_modules(modules, library=OverlayLibrary(library, modules), name=d.name, **kw)
    st.add_backend("source", source, source=True)
    if graph:
        from xgen_data_studio.backends.rdf import RdflibBackend

        st.add_backend("graph", RdflibBackend())
        st.project(into=["graph"])
    return st
