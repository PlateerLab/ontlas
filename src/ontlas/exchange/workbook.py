"""A definition draft kept as a workbook: a sheet is a section, its header row names the columns, a row is an item.

What comes out is the mapping of sections a YAML file of the same draft is, so `definitions.from_definitions` reads
both alike. A sheet and a column are known by the key the YAML uses or by the Korean name a sheet gives it. A sheet or a
column that is neither is not read, and the draft says so (`meta.not_read`) for the import to report: nothing is
dropped in silence. Reading .xlsx needs openpyxl, as reading a data file does (`draft.read_xlsx`).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from ontlas.draft import ReadError, Table, read_xlsx

WORKBOOKS = (".xlsx",)
HEADER_SCAN = 10  # rows a title or a note may take above the header
ROWS_MAX = 20_000  # rows of one sheet a draft is read to
DASH = ("—", "–", "-")  # a cell that says there is nothing
YES = ("y", "yes", "true", "예", "o", "필수")  # a check column, as a sheet marks it
# a vocabulary a sheet names with no IRI, and the IRI it is known by
VOCABULARIES = {"schema.org": "https://schema.org/"}

# a section as a sheet may be named. `relations` is whichever of the three its columns say
SHEETS = {
    "meta": ("meta", "notes", "readme", "안내", "개요"),
    "objects": ("objects", "object", "오브젝트"),
    "entities": ("entities", "entity", "엔티티"),
    "properties": ("properties", "property", "프로퍼티", "속성"),
    "enumerations": ("enumerations", "enumeration", "enums", "enum", "열거형"),
    "relations": ("relations", "relation", "관계"),
    "object_relations": ("object_relations", "object 관계", "오브젝트 관계"),
    "entity_relations": ("entity_relations", "entity 관계", "엔티티 관계"),
    "term_relations": ("term_relations", "표현 관계", "용어 관계"),
    "rule_links": ("rule_links", "규칙 연결"),
    "rules": ("rules", "rule", "규칙"),
    "parameters": ("parameters", "parameter", "기준값"),
    "banned_expressions": ("banned_expressions", "금지 표현"),
    "terms": ("terms", "term", "glossary", "용어", "용어 사전"),
    "customer_labels": ("customer_labels", "고객 표기"),
}
SHEET_TAILS = ("초안", "draft", "목록", "list")  # what a sheet's name may say after the section

# the keys the import reads of each section, each with the names a column may go by: the nearer the front, the closer.
# A name that starts with … is one a header ends with (whose it is may be written before it)
COLUMNS = {
    "objects": {
        "id": ("id", "초안 id"),
        "notation": ("notation", "표기", "object 표기"),
        "label_ko": ("label_ko", "label", "한글 이름", "한글명", "이름"),
        "class": ("class", "클래스"),
        "name": ("name", "영문 이름", "영문명"),
        "vocabulary": ("vocabulary", "어휘"),
        "group": ("group", "묶음"),
        "definition": ("definition", "description", "정의", "설명"),
        "includes": ("includes", "포함하는 것", "포함"),
        "excludes": ("excludes", "포함하지 않는 것", "제외"),
        "identifier": ("identifier", "식별자"),
        "lifecycle": ("lifecycle", "상태 흐름"),
        "entities": ("entities", "entity", "주요 entity"),
        "scope_without_data": ("scope_without_data", "연결 없이"),
        "scope_with_data": ("scope_with_data", "연결 후"),
        "owner": ("owner", "담당", "담당자", "담당 영역"),
    },
    "entities": {
        "id": ("id", "초안 id"),
        "notation": ("notation", "표기", "entity 표기"),
        "label_ko": ("label_ko", "label", "한글 이름", "한글명", "entity", "이름"),
        "class": ("class", "클래스"),
        "name": ("name", "영문 이름", "영문명"),
        "object": ("object", "오브젝트"),
        "vocabulary": ("vocabulary", "어휘"),
        "subClassOf": ("subclassof", "상위 클래스", "상위"),
        "definition": ("definition", "description", "정의", "설명"),
        "rule_requirements": ("rule_requirements", "규칙이 요구하는 것", "규칙이 요구하는 property"),
    },
    "properties": {  # a sheet of its own in a workbook: each row is a property of the Entity it names
        "entity": ("entity class", "entity 클래스", "클래스", "class", "entity"),
        "name": ("name", "property", "속성", "영문 이름"),
        "label_ko": ("label_ko", "label", "한글 이름", "한글명"),
        "kind": ("kind", "종류", "구분"),
        "vocabulary": ("vocabulary", "어휘"),
        "range": ("range", "값 유형", "자료형", "타입"),
        "cardinality": ("cardinality", "개수", "기수", "카디널리티"),
        "required": ("required", "필수"),
    },
    "enumerations": {
        "name": ("name", "enumeration", "열거형", "이름"),
        "values": ("values", "값", "값 목록", "허용값"),
    },
    "object_relations": {
        "subject": ("subject", "주어 object", "주어"),
        "predicate": ("predicate", "관계 유형", "관계"),
        "object": ("object", "대상 object", "대상"),
    },
    "entity_relations": {
        "subject": ("subject", "주어 클래스", "주어"),
        "property": ("property", "속성", "관계"),
        "object": ("object", "대상 클래스", "대상"),
        "cardinality": ("cardinality", "개수", "기수", "카디널리티"),
        "label_ko": ("label_ko", "label", "뜻", "한글 이름"),
    },
    "rule_links": {
        "rule": ("rule", "규칙 id", "규칙 초안 id", "초안 id", "id"),
        "object": ("object", "주 object", "적용 object"),
        "entities": ("entities", "관련 entity", "entity"),
    },
    "rules": {
        "id": ("id", "초안 id", "규칙 id"),
        "tier": ("tier", "layer", "계층", "계층 제안"),
        "area": ("area", "category", "영역", "분류"),
        "name": ("name", "title", "규칙 이름", "이름"),
        "type": ("type", "유형"),
        "condition": ("condition", "조건"),
        "result": ("result", "결과"),
        "exception": ("exception", "예외"),
        "object": ("object", "적용 object", "주 object"),
        "related": ("related", "관련 대상", "관련 object"),
        "basis": ("basis", "source", "근거"),
        "law": ("law", "대표 법령", "법령"),
        "basis_kind": ("basis_kind", "source_kind", "근거 종류"),
        "risk": ("risk", "위반 시", "위험"),
        "verification": ("verification", "확인 수준", "근거 확인"),
        "policy_check": ("policy_check", "정책서 대조", "…정책서 대조"),
        "owner": ("owner", "담당", "담당자"),
    },
    "parameters": {
        "key": ("key", "name", "키", "이름"),
        "value": ("value", "값"),
        "label": ("label", "표시 이름"),
        "kind": ("kind", "cite", "종류"),
        "rules": ("rules", "쓰는 규칙", "규칙"),
    },
    "banned_expressions": {
        "scope": ("scope", "품목", "상황", "대상"),
        "examples": ("examples", "표현 예", "표현"),
        "kind": ("kind", "구분", "종류"),
        "reason": ("reason", "이유", "사유"),
        "basis": ("basis", "근거"),
        "allowed_when": ("allowed_when", "쓸 수 있는 조건", "허용 조건"),
        "verification": ("verification", "확인 수준"),
    },
    "terms": {
        "id": ("id",),
        "term": ("term", "name", "용어", "표준 용어", "표준어"),
        "english": ("english", "영문 표기", "영문", "영문 이름"),
        "kind": ("kind", "구분", "종류"),
        "concept": ("concept", "연결 개념", "개념"),
        "definition": ("definition", "description", "정의", "설명"),
        "synonyms": ("synonyms", "동의어"),
        "source": ("source", "출처"),
    },
    "term_relations": {
        "relation": ("relation", "관계", "관계 종류"),
        "standard": ("standard", "표준 용어", "표준어", "용어"),
        "expressions": ("expressions", "다른 표현", "표현"),
        "note": ("note", "설명", "비고"),
        "basis": ("basis", "cite", "근거"),
        "needs_check": ("needs_check", "check", "확인 필요"),
    },
    "customer_labels": {
        "area": ("area", "영역"),
        "admin_labels": ("admin_labels", "관리자 표기"),
        "customer_label": ("customer_label", "고객 표기"),
        "standard_value": ("standard_value", "표준 값"),
        "needs_check": ("needs_check", "check", "확인 필요"),
    },
}
# a row is an item when it gives these, one of each group: a total under the rows, or a note between them, does not
NAMED = {"objects": (("class", "name", "notation"),), "entities": (("class", "name", "notation"),),
         "properties": (("name",), ("entity",)), "enumerations": (("name",),),
         "object_relations": (("subject",), ("object",)), "entity_relations": (("subject",), ("property",), ("object",)),
         "rule_links": (("rule",),), "rules": (("id",),), "parameters": (("key",),),
         "banned_expressions": (("scope", "examples", "reason"),), "terms": (("term",),),
         "term_relations": (("standard",),), "customer_labels": (("customer_label", "standard_value"),)}
# the columns that hold several values in a cell, as a YAML draft's lists, and whether a middle dot parts them where no
# comma does: not in a synonym, a phrase that may hold one itself (the import parts a text of synonyms at commas too)
LISTS = {("objects", "entities"): True, ("rule_links", "entities"): True, ("parameters", "rules"): True,
         ("terms", "synonyms"): False, ("term_relations", "expressions"): True, ("customer_labels", "admin_labels"): True}


def _norm(s: Any) -> str:
    """A name as it is compared: one form of each letter, no case, nothing between its words."""
    return re.sub(r"[\s_\-·./]+", "", unicodedata.normalize("NFC", str(s or "")).lower())


_SHEETS = {section: tuple(_norm(n) for n in names) for section, names in SHEETS.items()}
_COLUMNS = {section: {key: tuple(("…" if n.startswith("…") else "") + _norm(n.lstrip("…")) for n in names)
                      for key, names in keys.items()} for section, keys in COLUMNS.items()}


def _forms(header: str) -> list[str]:
    """A header as it may be read: whole, then without what it says in brackets, then by the first of two names it
    joins (`예외 · 비고`)."""
    bare = re.sub(r"\s*[(（][^)）]*[)）]\s*", " ", str(header)).strip()
    first = re.split(r"\s+[·/]\s+", bare)[0]
    return list(dict.fromkeys(_norm(x) for x in (header, bare, first)))


def _columns(section: str, headers: list[str]) -> dict[str, int]:
    """Where each key of a section is among a sheet's columns. A key is one column: where two could be it, the one
    read more nearly whole, then the one whose name stands nearer the front."""
    found: dict[str, tuple[int, int, int]] = {}  # key → (how far the header was cut, the name's place, the column)
    for i, header in enumerate(headers):
        for cut, form in enumerate(_forms(header)):
            hit = next(((key, at) for key, names in _COLUMNS[section].items() for at, n in enumerate(names)
                        if (form.endswith(n[1:]) if n.startswith("…") else form == n)), None)
            if hit is not None:
                if hit[0] not in found or (cut, hit[1]) < found[hit[0]][:2]:
                    found[hit[0]] = (cut, hit[1], i)
                break
    return {key: place[2] for key, place in found.items()}


def _section(name: str, headers: list[str]) -> str:
    """The section a sheet of this name is, or '' when it is none."""
    n = _norm(name)
    n = next((n[:-len(t)] for t in SHEET_TAILS if n.endswith(t) and len(n) > len(t)), n)
    section = next((s for s, names in _SHEETS.items() if n in names), "")
    if section == "relations":
        section = max(("object_relations", "entity_relations", "term_relations"), key=lambda s: len(_columns(s, headers)))
    return section


def header_row(raw: list[list]) -> int:
    """Where a sheet's header is: the first row two of whose cells are names a column goes by. 0 for a sheet of notes."""
    known = {n for keys in _COLUMNS.values() for names in keys.values() for n in names}
    for i, row in enumerate(raw[:HEADER_SCAN]):
        if sum(any(f in known for f in _forms(c)) for c in row if isinstance(c, str)) >= 2:
            return i
    return 0


def _items(cell: str, dotted: bool) -> list[str]:
    """The values of a cell that holds several: a line each, else parted by commas, else (`dotted`) by middle dots."""
    for mark in (r"\n", r"[,;]", *([r"\s·\s"] if dotted else [])):
        if re.search(mark, cell):
            return [x for x in (p.strip() for p in re.split(mark, cell)) if x and x not in DASH]
    return [cell]


def _codes(cell: str) -> list[dict]:
    """An enumeration's codes, a line each (or parted by commas where none has a name): the code, then its name after a
    middle dot."""
    lines = cell.splitlines() if "\n" in cell or "·" in cell else re.split(r"[,;]", cell)
    pairs = (re.split(r"\s*·\s*", line.strip(), maxsplit=1) for line in lines)
    return [{"value": p[0], "label_ko": p[1] if len(p) > 1 else ""} for p in pairs if p[0]]


def _named(row: dict) -> dict:
    """A name written `한글@Class` gives the label and the class the row does not give by themselves."""
    ko, at, cls = str(row.get("notation") or "").partition("@")
    if at and cls.strip():
        row.pop("notation")
        row.setdefault("class", cls.strip())
        if ko.strip():
            row.setdefault("label_ko", ko.strip())
    return row


def _rows(section: str, t: Table, keys: dict[str, int]) -> tuple[list[dict], int]:
    """A sheet's rows as the section's items, and how many of its rows name nothing."""
    out, unnamed = [], 0
    for cells in t.rows:
        row: dict[str, Any] = {}
        for key, i in keys.items():
            cell = cells[i]
            if cell is None or cell in DASH:
                continue
            if (section, key) in LISTS:
                cell = _items(cell, LISTS[section, key])
            elif (section, key) == ("enumerations", "values"):
                cell = _codes(cell)
            elif (section, key) == ("properties", "required"):
                cell = cell.lower() in YES
            row[key] = cell
        if section in ("objects", "entities"):
            row = _named(row)
        if section == "objects" and "entities" in row:
            row["entities"] = [_named({"notation": x}) if "@" in x else x for x in row["entities"]]
        if all(any(row.get(k) for k in group) for group in NAMED[section]):
            out.append(row)
        else:
            unnamed += 1
    return out, unnamed


def _nest(doc: dict) -> None:
    """Put each row of a Property sheet under the Entity it names: by class, by name, then by label. An Entity no sheet
    of this workbook lists is listed by its properties alone (another file of the draft may say the rest)."""
    entities = doc.setdefault("entities", [])
    by: dict[str, dict] = {}
    for field in ("class", "name", "label_ko"):
        for e in entities:
            if e.get(field):
                by.setdefault(e[field], e)
    for p in doc.pop("properties"):
        of = p.pop("entity")
        if of not in by:
            by[of] = {"class": of}
            entities.append(by[of])
        by[of].setdefault("properties", []).append(p)


def draft_of(tables: list[Table], source: str = "") -> dict:
    """The draft the sheets of a workbook hold (`draft.read_xlsx` gives them), as the mapping of sections a YAML file
    is. What was not read is listed under `meta.not_read`."""
    doc: dict[str, Any] = {}
    meta: dict[str, Any] = {}
    not_read: list[str] = []
    for t in tables:
        lead = f"{source} · "
        sheet = t.source[len(lead):] if source and t.source.startswith(lead) else t.name
        section = _section(sheet, t.columns) or _section(t.name, t.columns)  # a workbook of one sheet, by its file's name
        at = f"sheet '{sheet}'" + (f" of {source}" if source else "")  # a draft of several workbooks has sheets of one name
        if section == "meta":  # notes about the draft: a line above them is its title
            said = [c for i, c in enumerate(t.columns) if c != f"column{i + 1}"]
            titled = len(said) == 1 and "title" not in meta
            if titled:
                meta["title"] = said[0]
            not_read.append(f"{at}: notes, not a table of rows; " +
                            ("only its first line was read, as the draft's title" if titled else "not read"))
            continue
        if not section:
            not_read.append(f"{at} ({len(t.rows)} rows): not a section of a draft, not read")
            continue
        keys = _columns(section, t.columns)
        rows, unnamed = _rows(section, t, keys)
        if not rows:
            not_read.append(f"{at} ({len(t.rows)} rows): no row of it names an item of '{section}', not read")
            continue
        left = [h for i, h in enumerate(t.columns) if i not in keys.values() and any(r[i] is not None for r in t.rows)]
        if left:
            not_read.append(f"{at}: columns not read: {', '.join(left)}")
        if unnamed:
            not_read.append(f"{at}: {unnamed} of its rows name no item (a total, a note), not read")
        if t.truncated:
            not_read.append(f"{at}: rows past {ROWS_MAX} not read")
        doc.setdefault(section, []).extend(rows)
    if "properties" in doc:
        _nest(doc)
    listed = [*doc.get("objects", []), *doc.get("entities", [])]
    said = {str(r.get("vocabulary") or "").strip().lower() for e in listed for r in (e, *(e.get("properties") or []))}
    known = {v: VOCABULARIES[v] for v in sorted(said) if v in VOCABULARIES}
    if known:  # as a YAML draft says how its names are written
        meta["notation"] = known
    if not_read:
        meta["not_read"] = not_read
    return {**({"meta": meta} if meta else {}), **doc}


def read_workbook(data: bytes, source: str) -> dict:
    """The draft a workbook holds. `draft.ReadError` says why a file could not be read as one: `reason` is workbook,
    workbook_size, openpyxl, or empty where no sheet of it is a section with rows."""
    try:
        tables = read_xlsx(data, source, max_rows=ROWS_MAX, header=header_row)
    except ReadError:
        raise
    except Exception:  # a zip that is no workbook: whatever a malformed upload trips over ends in an answer
        raise ReadError(f"{source}: not an .xlsx workbook", "workbook") from None
    doc = draft_of(tables, source)
    if not any(isinstance(v, list) and v for k, v in doc.items() if k != "meta"):
        sheets = ", ".join(t.source[len(source) + 3:] for t in tables)
        raise ReadError(f"{source}: no sheet is a section of a draft with rows (its sheets: {sheets}); a sheet is named "
                        "objects, entities, properties, rules, parameters, terms ... or by the Korean name of one", "empty")
    return doc
