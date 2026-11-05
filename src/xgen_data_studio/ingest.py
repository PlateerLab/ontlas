"""Anything in, one JSON out: read a file of any kind into the canonical definitions object.

A file is read by its extension, then by what its content looks like, and comes out as `definitions.Definitions`:
tables, codes, terms, messages and documents, the shape of `Definitions.to_dict`. From there one path makes modules.
A format of your own is a python file that calls `register`, loaded with `load_adapters`.

Uploads are untrusted. A zip is read only up to UNPACKED_MAX, whatever it declares, and its entries stay in memory;
XML that declares a document type is refused, so no entity is ever defined or fetched; nothing in a file is run.
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable, Iterable, Iterator
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path
from typing import NamedTuple
from xml.parsers import expat

from xgen_data_studio.definitions import CodeGroup, ColumnDef, Definitions, TableDef, from_sheets, read_definitions
from xgen_data_studio.draft import XLSX_UNPACKED_MAX, ReadError, read_file

UNPACKED_MAX = XLSX_UNPACKED_MAX
SHEETS = (".csv", ".tsv", ".xlsx", ".xlsm")
EXPORT_TO = {".doc": "DOCX", ".docx": "DOCX", ".hwp": "HWPX", ".hwpx": "HWPX", ".ppt": "PPTX", ".pptx": "PPTX",
             ".xls": "XLSX"}
OLE = b"\xd0\xcf\x11\xe0"  # the older binary formats, and a .docx with a password
EXPORT_ANY = "SQL, XLSX, PDF"
READ_REASON = {"workbook_size": "too_large", "openpyxl": "needs_extra", "empty": "empty"}

Adapter = Callable[[bytes, str], Definitions]
ADAPTERS: dict[str, Adapter] = {}
_env_loaded = False


class IngestError(ValueError):
    """A file could not be read; `reason` is format, empty, too_large, needs_extra or export_needed, and `info` holds
    what the reason needs (export_to, the format to export to)."""

    def __init__(self, message: str, reason: str = "format", **info: str):
        super().__init__(message)
        self.reason = reason
        self.info = info


def register(extensions: str | Iterable[str], fn: Adapter) -> None:
    """Read these extensions with `fn(data, source) -> Definitions`; the last one registered wins."""
    for ext in [extensions] if isinstance(extensions, str) else extensions:
        ADAPTERS["." + ext.lower().lstrip(".")] = fn


def adapter_paths(value: str) -> list[str]:
    """Paths separated by `;` or `:`; the `:` of a Windows drive stays in its path."""
    return [p for part in value.split(";") for p in re.findall(r"(?:[A-Za-z]:[\\/])?[^:]+", part) if p.strip()]


def load_adapters(paths: str | Iterable[str]) -> None:
    """Run python files that call `register`. They come from whoever runs the studio, never from an upload."""
    for p in adapter_paths(paths) if isinstance(paths, str) else paths:
        path = Path(p)
        name = f"xds_adapter_{path.stem}"
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None or not path.is_file():
            raise IngestError(f"{p}: not an adapter file", "format")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module  # dataclasses look their module up while the file runs
        spec.loader.exec_module(module)


def ingest(data: bytes, source: str) -> Definitions:
    """The definitions and documents a file holds."""
    global _env_loaded
    if not _env_loaded:
        _env_loaded = True
        load_adapters(os.environ.get("XDS_ADAPTERS", ""))
    if not data:
        raise IngestError(f"{source}: the file is empty", "empty")
    try:
        fn = ADAPTERS.get(Path(source).suffix.lower()) or _sniff(data, source)
        out = fn(data, source)
    except IngestError:
        raise
    except Exception as e:  # whatever a malformed upload trips over, it ends in an answer
        raise IngestError(f"{source}: could not be read ({type(e).__name__}: {e})", "format") from e
    if not isinstance(out, Definitions):
        raise IngestError(f"{source}: the adapter returned no definitions", "format")
    return out


def is_sheet(data: bytes, source: str) -> bool:
    """A file of rows: data for the page, unless its headers make it a definition sheet. A .txt may be either rows or
    prose."""
    if Path(source).suffix.lower() != ".txt":
        return Path(source).suffix.lower() in SHEETS
    try:
        return _tabular(_text(data, source))
    except IngestError:
        return True  # the sheet reader says what is wrong with the encoding


def _sniff(data: bytes, source: str) -> Adapter:
    if data[:4] == b"PK\x03\x04":
        names = set(_Archive(data, source).names)
        fn = next((fn for member, fn in _ZIP_MEMBERS if member in names), None)
        if fn is None:
            raise _export(source)
        return fn
    if data[:5] == b"%PDF-":
        return _pdf
    if b"\0" in data[:4096] and data[:2] not in (b"\xff\xfe", b"\xfe\xff"):
        raise _export(source)
    text = _text(data, source)
    head = text.lstrip()[:2000].lower()
    if head.startswith("{"):
        return _json
    if head.startswith("<"):
        if "powerdesigner" in head or 'xmlns:a="attribute"' in head:
            return _pdm
        if re.search(r"<(!doctype html|html|body|div|p)\b", head):
            return _html
        raise _export(source)
    if re.search(r"\bcreate\s+table\b", text, re.I):
        return _sql
    if re.search(r"^[ \t]*(table\s+\S+.*\{|enum\s+\S+.*\{|ref\b[^\n]*[:{])", text, re.I | re.M):
        return _dbml
    return _txt


def _export(source: str) -> IngestError:
    ext = Path(source).suffix.lower()
    to = EXPORT_TO.get(ext, EXPORT_ANY)
    return IngestError(f"{source}: {ext or 'this format'} cannot be read directly; export it to {to}", "export_needed",
                       export_to=to)


def _text(data: bytes, source: str) -> str:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):  # SQL Server scripts are saved as UTF-16
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp949"):  # exports in Korea are often cp949
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise IngestError(f"{source}: the file is neither UTF-8 nor CP949 text", "format")


def _tabular(text: str) -> bool:
    """Lines that split into the same number of cells: a delimited file, not prose."""
    lines = [x for x in text.splitlines()[:20] if x.strip()]
    return len(lines) > 1 and any(lines[0].count(d) and all(x.count(d) == lines[0].count(d) for x in lines[1:])
                                  for d in "\t,;|")


def _describe(obj: TableDef | ColumnDef, text: str | None) -> None:
    """A comment: its first line names the object, the rest describes it."""
    first, _, rest = (text or "").strip().partition("\n")
    obj.label, obj.description = first.strip(), rest.strip()


def _primary(t: TableDef, names: list[str]) -> None:
    t.primary_key = []
    for n in names:
        c = t.column(n)
        if c is not None:
            c.pk = c.required = True
        t.primary_key.append(c.name if c is not None else n)


def _code_group(t: TableDef, c: ColumnDef, values: list, defs: Definitions) -> None:
    """Values a column allows and the file does not name: a code group of that column alone."""
    c.code = f"{t.name}.{c.name}"
    defs.codes[c.code] = CodeGroup(c.code, "", [{"code": str(v), "name": "", "use": True} for v in values])


def _found(defs: Definitions, source: str, aliases: dict[str, str] | None = None) -> Definitions:
    """Columns join the enum their type names, and groups take the names their columns got later in the file."""
    for t in defs.tables.values():
        for c in t.columns:
            base = c.type.rsplit(".", 1)[-1]
            base = (aliases or {}).get(base, base)
            if not c.code and base in defs.codes:
                c.code = base
            g = defs.codes.get(c.code)
            if g is not None and not g.label:
                g.label = c.label
    if not defs.tables and not defs.codes:
        raise IngestError(f"{source}: no table definitions found", "empty")
    return defs


# ---- zip and XML ---------------------------------------------------------------------------------------------


class _Archive:
    """A zip read within UNPACKED_MAX: what it declares is checked first, what it really inflates to while reading."""

    def __init__(self, data: bytes, source: str):
        self.source = source
        if data[:4] == OLE:
            raise _export(source)
        try:
            self.zip = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise IngestError(f"{source}: not a valid archive", "format") from None
        self.names = self.zip.namelist()
        self.left = UNPACKED_MAX
        if sum(i.file_size for i in self.zip.infolist()) > UNPACKED_MAX:
            raise self._too_large()

    def _too_large(self) -> IngestError:
        return IngestError(f"{self.source}: the archive unpacks to more than {UNPACKED_MAX >> 20}MB", "too_large")

    def read(self, name: str) -> bytes:
        with self.zip.open(name) as f:
            blob = f.read(self.left + 1)
        if len(blob) > self.left:
            raise self._too_large()
        self.left -= len(blob)
        return blob


def _xml(data: bytes) -> ET.Element:
    """XML as elements named without their prefixes, since each format's prefixes vary and its local names do not.
    Attributes keep theirs: a slide id has both id and r:id."""
    tree = ET.TreeBuilder()

    def refuse(*_: object) -> None:
        raise IngestError("the XML declares a document type, which is not read", "format")

    p = expat.ParserCreate()
    p.buffer_text = True
    p.StartDoctypeDeclHandler = refuse
    p.EntityDeclHandler = refuse
    p.StartElementHandler = lambda name, attrs: tree.start(name.rsplit(":", 1)[-1], attrs)
    p.EndElementHandler = lambda name: tree.end(name.rsplit(":", 1)[-1])
    p.CharacterDataHandler = tree.data
    p.Parse(data, True)
    return tree.close()


def _attr(el: ET.Element, name: str) -> str:
    return next((v for k, v in el.attrib.items() if k.rsplit(":", 1)[-1] == name), "")


# ---- documents -----------------------------------------------------------------------------------------------

_POLICY = re.compile(r"제\s*\d+\s*조|정책|규정|약관|불가|금지|해야\s*한다|할\s*수\s*(?:있|없)|\b(?:policy|must|shall|prohibited)\b", re.I)
_NUMBERED = re.compile(r"(?:제\s*\d+\s*[장절조관]\s*|\d{1,2}(?:\.\d{1,2})+\.?\s+|\d{1,2}[.)]\s*(?=[^\d\s]))\S.*")
_HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_HTML_SKIP = {"script", "style", "noscript", "template", "title"}
_HTML_BLOCKS = _HEADINGS | {"p", "div", "li", "ul", "ol", "section", "article", "header", "footer", "main", "aside",
                            "nav", "table", "blockquote", "pre", "dl", "dt", "dd", "hr", "form", "figure"}


class _Outline:
    """Lines as they are read, cut into sections at each heading."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.sections: list[dict] = []

    def heading(self, title: str) -> None:
        title = " ".join(title.split())
        if title:
            self.lines.append(title)
            self.sections.append({"title": title, "lines": []})

    def line(self, text: str) -> None:
        text = text.rstrip()
        if text.strip():
            self.lines.append(text)
            if not self.sections:
                self.sections.append({"title": "", "lines": []})
            self.sections[-1]["lines"].append(text)

    def numbered(self, text: str) -> None:
        """A line of a file without heading styles, where only a number marks a heading."""
        s = text.strip()
        if len(s) <= 60 and _NUMBERED.fullmatch(s) and s[-1] not in ".다요":
            self.heading(s)
        else:
            self.line(text)


def _document(out: _Outline, source: str, kind: str = "") -> Definitions:
    text = "\n".join(out.lines)
    if not text.strip():
        raise IngestError(f"{source}: no text found", "empty")
    kind = kind or ("policy" if len(_POLICY.findall(text)) >= 3 else "other")
    return Definitions(sources=[source], documents=[{
        "name": Path(source).stem, "kind": kind, "text": text,
        "sections": [{"title": s["title"], "text": "\n".join(s["lines"])} for s in out.sections]}])


def _word_headings(z: _Archive) -> set[str]:
    """The paragraph styles that are headings. The id does not say: Korean Word calls Heading 1 just "1"."""
    if "word/styles.xml" not in z.names:
        return set()
    found = set()
    for st in _xml(z.read("word/styles.xml")).iter("style"):
        name = st.find("name")
        label = _attr(name, "val").lower() if name is not None else ""
        if label == "title" or re.fullmatch(r"(?:heading|제목)\s*\d", label):
            found.add(_attr(st, "styleId"))
    return found


def _word_blocks(parent: Iterable[ET.Element]) -> Iterator[ET.Element]:
    for el in parent:
        if el.tag in ("p", "tbl"):
            yield el
        elif el.tag in ("sdt", "sdtContent", "customXml", "ins"):
            yield from _word_blocks(el)


def _word_text(el: ET.Element) -> str:
    """A paragraph's text. Word keeps a second copy of a drawing's text for older readers, under Fallback."""
    out = []
    for c in el:
        if c.tag == "t":
            out.append(c.text or "")
        elif c.tag == "tab":
            out.append("\t")
        elif c.tag in ("br", "cr"):
            out.append("\n")
        elif c.tag not in ("pPr", "rPr", "Fallback", "del", "moveFrom"):
            out.append(_word_text(c))
    return "".join(out)


def _docx(data: bytes, source: str) -> Definitions:
    z = _Archive(data, source)
    if "word/document.xml" not in z.names:
        raise IngestError(f"{source}: not a Word document", "format")
    headings = _word_headings(z)
    body = _xml(z.read("word/document.xml")).find("body")
    out = _Outline()
    for el in _word_blocks(body if body is not None else ()):
        if el.tag == "tbl":
            for row in el.findall("tr"):
                out.line(" | ".join(" ".join(_word_text(p).strip() for p in tc.iter("p")).strip()
                                    for tc in row.findall("tc")))
            continue
        ppr = el.find("pPr")
        style = ppr.find("pStyle") if ppr is not None else None
        sid = _attr(style, "val") if style is not None else ""
        level = ppr.find("outlineLvl") if ppr is not None else None
        text = _word_text(el)
        if sid in headings or sid.lower().startswith("heading") or (level is not None and _attr(level, "val") != "9"):
            out.heading(text)
        elif ppr is not None and ppr.find("numPr") is not None and text.strip():
            out.line(f"- {text.strip()}")
        else:
            out.line(text)
    return _document(out, source)


def _slide_files(z: _Archive) -> list[str]:
    """Slides in the order the deck shows them, which is not the order of their file names."""
    names = sorted((n for n in z.names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                   key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    rels = "ppt/_rels/presentation.xml.rels"
    if "ppt/presentation.xml" not in z.names or rels not in z.names:
        return names
    target = {r.get("Id"): r.get("Target", "") for r in _xml(z.read(rels)).iter("Relationship")}
    paths = [target.get(s.get("r:id"), "") for s in _xml(z.read("ppt/presentation.xml")).iter("sldId")]
    ordered = [n for n in (p.lstrip("/") if p.startswith("/") else f"ppt/{p}" for p in paths) if n in names]
    return ordered or names


def _slide_items(parent: Iterable[ET.Element]) -> Iterator[tuple[bool, str]]:
    """(is the title, text) of each shape's paragraphs and each table's rows, as they lie on the slide."""
    for el in parent:
        if el.tag in ("grpSp", "AlternateContent", "Choice"):
            yield from _slide_items(el)
        elif el.tag == "sp":
            ph = next(el.iter("ph"), None)
            title = ph is not None and ph.get("type") in ("title", "ctrTitle")
            for p in el.iter("p"):
                yield title, "".join(t.text or "" for t in p.iter("t"))
        elif el.tag == "graphicFrame":
            for tbl in el.iter("tbl"):
                for tr in tbl.findall("tr"):
                    yield False, " | ".join(" ".join(t.text or "" for t in tc.iter("t")).strip()
                                            for tc in tr.findall("tc"))


def _pptx(data: bytes, source: str) -> Definitions:
    z = _Archive(data, source)
    slides = _slide_files(z)
    if not slides:
        raise IngestError(f"{source}: not a PowerPoint deck", "format")
    out = _Outline()
    for n, name in enumerate(slides, 1):
        tree = _xml(z.read(name)).find("cSld/spTree")
        items = [(is_title, s) for is_title, s in _slide_items(tree if tree is not None else ()) if s.strip()]
        if items:
            titles = [s for is_title, s in items if is_title]
            out.heading(" ".join(titles) or f"Slide {n}")
            for is_title, s in items:
                if not is_title:
                    out.line(s)
    return _document(out, source, "screen")


def _hwp_text(t: ET.Element) -> str:
    """A text run, which holds tabs and line breaks between its pieces of text."""
    out = [t.text or ""]
    for c in t:
        out += [{"tab": "\t", "lineBreak": "\n", "nbSpace": " ", "fwSpace": " "}.get(c.tag, ""), c.tail or ""]
    return "".join(out)


def _hwp_walk(el: ET.Element, out: _Outline, headings: set[str]) -> None:
    """Paragraphs in reading order, also those in text boxes and notes; a table's rows stay rows."""
    for c in el:
        if c.tag == "p":
            text = "".join(_hwp_text(t) for r in c.findall("run") for t in r.findall("t"))
            if _attr(c, "styleIDRef") in headings:
                out.heading(text)
            else:
                out.numbered(text)
            _hwp_walk(c, out, headings)
        elif c.tag == "tbl":
            for tr in c.findall("tr"):
                out.line(" | ".join(" ".join(_hwp_text(t) for t in tc.iter("t")).strip() for tc in tr.findall("tc")))
            for caption in c.findall("caption"):
                _hwp_walk(caption, out, headings)
        elif c.tag != "t":
            _hwp_walk(c, out, headings)


def _hwpx(data: bytes, source: str) -> Definitions:
    z = _Archive(data, source)
    sections = sorted((n for n in z.names if re.fullmatch(r"Contents/section\d+\.xml", n)),
                      key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)))
    if not sections:
        raise IngestError(f"{source}: not a Hancom document", "format")
    headings = set()
    if "Contents/header.xml" in z.names:
        headings = {_attr(s, "id") for s in _xml(z.read("Contents/header.xml")).iter("style")
                    if re.fullmatch(r"(?:개요|outline)\s*\d+", (_attr(s, "name") or _attr(s, "engName")).lower())}
    out = _Outline()
    for name in sections:
        _hwp_walk(_xml(z.read(name)), out, headings)
    return _document(out, source)


class _Html(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out = _Outline()
        self.skip = 0
        self.buf: list[str] = []
        self.row: list[str] | None = None
        self.cell = False
        self.bullet = False

    def _words(self) -> str:
        text = " ".join("".join(self.buf).split())
        self.buf = []
        return text

    def flush(self, heading: bool = False) -> None:
        text = self._words()
        if heading:
            self.out.heading(text)
        elif text:
            self.out.line(f"- {text}" if self.bullet else text)
            self.bullet = False

    def _end_cell(self) -> None:
        if self.cell and self.row is not None:
            self.row.append(self._words())
        self.cell = False

    def _end_row(self) -> None:
        self._end_cell()
        if self.row:
            self.out.line(" | ".join(self.row))
        self.row = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _HTML_SKIP:
            self.skip += 1
        elif self.skip:
            return
        elif tag == "br":
            self.buf.append(" ")
        elif tag == "tr":
            self.flush()
            self._end_row()
            self.row = []
        elif tag in ("td", "th"):
            self._end_cell()
            self.buf, self.cell = [], True
        elif tag in _HTML_BLOCKS:
            self.flush()
            self.bullet = tag == "li"

    def handle_endtag(self, tag: str) -> None:
        if tag in _HTML_SKIP:
            self.skip = max(0, self.skip - 1)
        elif self.skip:
            return
        elif tag in ("td", "th"):
            self._end_cell()
        elif tag == "tr":
            self._end_row()
        elif tag in _HTML_BLOCKS:
            self._end_row()
            self.flush(tag in _HEADINGS)

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.buf.append(data)


def _html(data: bytes, source: str) -> Definitions:
    p = _Html()
    p.feed(_text(data, source))
    p.close()
    p._end_row()
    p.flush()
    return _document(p.out, source)


def _md(data: bytes, source: str) -> Definitions:
    out, fenced = _Outline(), False
    for line in _text(data, source).splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        m = None if fenced else re.match(r" {0,3}#{1,6}[ \t]+(.*)", line)
        if m:
            out.heading(m.group(1).rstrip().rstrip("#"))
        else:
            out.line(line)
    return _document(out, source)


def _txt(data: bytes, source: str) -> Definitions:
    text = _text(data, source)
    if _tabular(text):
        try:
            return _sheets(data, source)
        except IngestError:
            pass  # rows that are no definition sheet are still text
    out = _Outline()
    for line in text.splitlines():
        out.numbered(line)
    return _document(out, source)


def _pdf(data: bytes, source: str) -> Definitions:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise IngestError("reading .pdf needs pypdf (pip install 'xgen-data-studio[pdf]')", "needs_extra") from None
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted and not reader.decrypt(""):
        raise IngestError(f"{source}: the PDF needs a password", "format")
    out, size = _Outline(), 0
    for page in reader.pages:
        text = page.extract_text() or ""
        size += len(text)
        if size > UNPACKED_MAX:
            raise IngestError(f"{source}: the text runs past {UNPACKED_MAX >> 20}MB", "too_large")
        for line in text.splitlines():
            out.numbered(line)
    return _document(out, source)


# ---- sheets and JSON -----------------------------------------------------------------------------------------


def _sheets(data: bytes, source: str) -> Definitions:
    name = source
    if Path(source).suffix.lower() not in (*SHEETS, ".txt"):  # found by its content, under some other name
        name = source + (".xlsx" if data[:2] == b"PK" else ".csv")
    try:
        sheets = read_file(data, name)
    except ReadError as e:
        raise IngestError(str(e), READ_REASON.get(e.reason, "format")) from None
    out = from_sheets(sheets, source)
    if out is None:
        raise IngestError(f"{source}: no table, code, term or message sheet found", "format")
    return out


def _json(data: bytes, source: str) -> Definitions:
    out = read_definitions(data, f"{Path(source).stem}.json")
    if out is None:
        raise IngestError(f"{source}: no tables, codes, terms, messages or documents found", "format")
    return out


# ---- SQL DDL -------------------------------------------------------------------------------------------------


class _Tok(NamedTuple):
    kind: str  # word, name (a quoted one), str, num, or the punctuation itself
    value: str
    first: bool = False  # the first on its line


_END = _Tok("", "")
_SQL_WORD = re.compile(r"[^\W\d][\w$#]*")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_DOLLAR = re.compile(r"\$(?:[^\W\d]\w*)?\$")
_TABLE_WORDS = {"OR", "REPLACE", "UNLOGGED", "FOREIGN", "EXTERNAL"}  # a temporary table is no part of the schema
_NOT_COLUMNS = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "EXCLUDE", "LIKE", "FULLTEXT", "SPATIAL",
                "PERIOD", "SUPPLEMENTAL"}
_COLUMN_ATTRS = {"NOT", "NULL", "DEFAULT", "PRIMARY", "UNIQUE", "REFERENCES", "CHECK", "COMMENT", "CONSTRAINT",
                 "GENERATED", "AUTO_INCREMENT", "AUTOINCREMENT", "IDENTITY", "COLLATE", "AS", "ON", "KEY", "ENABLE",
                 "DISABLE", "ENCRYPT", "INVISIBLE", "VISIBLE", "ROWGUIDCOL", "SPARSE", "MASKED", "CHARSET",
                 "COLUMN_FORMAT", "STORAGE"}


def _kw(t: _Tok) -> str:
    return t.value.upper() if t.kind == "word" else ""


def _at(toks: list[_Tok], i: int) -> _Tok:
    return toks[i] if 0 <= i < len(toks) else _END


def _closing(text: str, i: int, quote: str, backslash: bool = False) -> int:
    """Where the quote opened at i closes; a doubled quote stays inside, and an open one runs to the end of the text."""
    j = i + 1
    while True:
        k = text.find(quote, j)
        if k < 0:
            return len(text)
        if backslash:
            b = k
            while b > i and text[b - 1] == "\\":
                b -= 1
            if (k - b) % 2:
                j = k + 1
                continue
        if text[k + 1:k + 2] == quote:
            j = k + 2
            continue
        return k


def _sql_tokens(text: str) -> list[_Tok]:
    out: list[_Tok] = []
    i, n, first = 0, len(text), True
    backslash = "`" in text  # MySQL scripts escape quotes with a backslash; to the others it is an ordinary character
    while i < n:
        c = text[i]
        if c == "\n":
            first, i = True, i + 1
            continue
        if c.isspace():
            i += 1
            continue
        if text.startswith("--", i) or (c == "#" and not (text[i + 1:i + 2].isalnum() or text[i + 1:i + 2] == "_")):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "NnEeBbXxUu" and text[i + 1:i + 2] == "'":  # N'x', E'x': the prefix changes nothing here
            i, c = i + 1, "'"
        if c in "'\"`":
            j = _closing(text, i, c, backslash)
            value = text[i + 1:j].replace(c * 2, c)
            out.append(_Tok("str" if c == "'" else "name", value.replace("\\'", "'") if backslash else value, first))
            i = j + 1
        elif c == "[" and text[i + 1:i + 2] != "]" and not (out and _kw(out[-1]) == "ARRAY"):
            j = _closing(text, i, "]")
            out.append(_Tok("name", text[i + 1:j].replace("]]", "]"), first))
            i = j + 1
        elif c == "$" and (m := _DOLLAR.match(text, i)):  # a body between $$ holds semicolons of its own
            j = text.find(m.group(), m.end())
            out.append(_Tok("str", text[m.end():n if j < 0 else j], first))
            i = n if j < 0 else j + len(m.group())
        elif m := _SQL_WORD.match(text, i):
            out.append(_Tok("word", m.group(), first))
            i = m.end()
        elif m := _NUMBER.match(text, i):
            out.append(_Tok("num", m.group(), first))
            i = m.end()
        else:
            out.append(_Tok(c, c, first))
            i += 1
        first = False
    return out


def _statements(toks: list[_Tok]) -> Iterator[list[_Tok]]:
    st: list[_Tok] = []
    depth = 0
    for t in toks:
        end = t.kind == ";" or (t.first and depth <= 0 and (_kw(t) == "GO" or t.kind == "/"))
        # a script that leaves out its terminators still starts each statement on a new line
        if end or (t.first and depth <= 0 and _kw(t) in ("CREATE", "ALTER")):
            if st:
                yield st
            st, depth = [], 0
            if end:
                continue
        st.append(t)
        depth += (t.kind == "(") - (t.kind == ")")
    if st:
        yield st


def _dotted(toks: list[_Tok], i: int) -> tuple[list[str], int]:
    parts: list[str] = []
    while _at(toks, i).kind in ("word", "name"):
        parts.append(toks[i].value)
        i += 1
        if _at(toks, i).kind != ".":
            break
        i += 1
    return parts, i


def _group(toks: list[_Tok], i: int) -> int:
    """The index just past the bracket opened at i."""
    depth = 0
    for j in range(i, len(toks)):
        depth += (toks[j].kind == "(") - (toks[j].kind == ")")
        if depth == 0:
            return j + 1
    return len(toks) + 1  # never closed: as if it closed after the last token


def _items(toks: list[_Tok]) -> list[list[_Tok]]:
    out: list[list[_Tok]] = [[]]
    depth = 0
    for t in toks:
        if t.kind == "," and depth == 0:
            out.append([])
            continue
        depth += (t.kind == "(") - (t.kind == ")")
        out[-1].append(t)
    return [x for x in out if x]


def _bracket_names(toks: list[_Tok], i: int) -> tuple[list[str], int]:
    """The first word of each item in the bracket at i, which leaves out ASC and a key's prefix length."""
    end = _group(toks, i)
    return [x[0].value for x in _items(toks[i + 1:end - 1])], end


def _next_bracket(toks: list[_Tok], i: int) -> int | None:
    return next((j for j in range(i, len(toks)) if toks[j].kind == "("), None)


def _type_of(toks: list[_Tok]) -> tuple[str, int, list[str]]:
    """A column type: its words, the first number in its brackets, and the strings of ENUM('a','b')."""
    words, length, values, depth = [], 0, [], 0
    for t in toks:
        if t.kind == "(":
            depth += 1
        elif t.kind == ")":
            depth -= 1
        elif depth == 0:
            words.append(t.value)
        elif t.kind == "num" and not length:
            length = int(float(t.value))
        elif t.kind == "str":
            values.append(t.value)
    return re.sub(r"\s*([.\[\]])\s*", r"\1", " ".join(words)), length, values


def _allowed(toks: list[_Tok]) -> tuple[str, list[str]] | None:
    """The column and values of CHECK (c IN ('A','B')), also in the two spellings databases print it back in:
    c = ANY (ARRAY['A'::text, 'B'::text]), and c = 'A' OR c = 'B'."""
    core: list[_Tok] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.kind == ":" and _at(toks, i + 1).kind == ":":  # a cast: 'A'::character varying(20)
            i += 2
            while _at(toks, i).kind == "word":
                i += 1
            if _at(toks, i).kind == "(":
                i = _group(toks, i)
            continue
        i += 1
        if t.kind not in ("(", ")", "[", "]", ",") and not (t.value.startswith("_") and _at(toks, i).kind == "str"):
            core.append(t)  # _utf8mb4'A' is how MySQL prints a string back
    if len(core) < 3 or core[0].kind not in ("word", "name"):
        return None
    col, rest = core[0].value, core[1:]
    if _kw(rest[0]) == "IN":
        values = rest[1:]
    elif rest[0].kind == "=" and _kw(rest[1]) == "ANY":
        values = [v for v in rest[2:] if _kw(v) != "ARRAY"]
    else:
        values = []
        for k in range(0, len(core), 4):
            c = core[k:k + 4]
            if len(c) < 3 or c[0].value != col or c[1].kind != "=" or (len(c) == 4 and _kw(c[3]) != "OR"):
                return None
            values.append(c[2])
    if not values or any(v.kind not in ("str", "num") for v in values):
        return None
    return col, [v.value for v in values]


def _check(t: TableDef, toks: list[_Tok], defs: Definitions) -> None:
    found = _allowed(toks)
    c = t.column(found[0]) if found else None
    if c is not None:
        _code_group(t, c, found[1], defs)


def _reference(cols: list[str], toks: list[_Tok], i: int) -> dict | None:
    parts, i = _dotted(toks, i)
    if not parts or not cols:
        return None
    ref = _bracket_names(toks, i)[0] if _at(toks, i).kind == "(" else []
    return {"columns": cols, "table": parts[-1], "ref_columns": ref}


def _is_constraint(item: list[_Tok]) -> bool:
    head = _kw(item[0])
    if head in ("KEY", "INDEX"):  # a column may be called key: key VARCHAR(10), against KEY idx (a)
        return (_at(item, 1).kind == "(" or any(_kw(x) in ("USING", "CLUSTERED", "NONCLUSTERED") for x in item)
                or (_at(item, 2).kind == "(" and _at(item, 3).kind != "num"))
    return head in _NOT_COLUMNS


def _constraint(t: TableDef, item: list[_Tok], defs: Definitions) -> None:
    i = 0
    if _kw(item[0]) == "CONSTRAINT":
        i = 1 if _kw(_at(item, 1)) in ("PRIMARY", "FOREIGN", "UNIQUE", "CHECK") else 2
    head = _kw(_at(item, i))
    j = _next_bracket(item, i)
    if j is None:
        return
    if head == "PRIMARY":
        _primary(t, _bracket_names(item, j)[0])
    elif head == "FOREIGN":
        cols, j = _bracket_names(item, j)
        while j < len(item) and _kw(item[j]) != "REFERENCES":
            j += 1
        ref = _reference(cols, item, j + 1)
        if ref:
            t.references.append(ref)
    elif head == "CHECK":
        _check(t, item[j + 1:_group(item, j) - 1], defs)


def _column(t: TableDef, item: list[_Tok], defs: Definitions) -> None:
    c = ColumnDef(item[0].value)
    t.columns.append(c)
    i, kinds = 1, []
    while i < len(item):
        k = _kw(item[i])
        if k in _COLUMN_ATTRS or (k == "CHARACTER" and _kw(_at(item, i + 1)) == "SET"):
            break
        end = _group(item, i) if item[i].kind == "(" else i + 1
        kinds += item[i:end]
        i = end
    c.type, c.length, values = _type_of(kinds)
    if values:
        _code_group(t, c, values, defs)
    while i < len(item):
        k = _kw(item[i])
        if item[i].kind == "(":
            i = _group(item, i)
            continue
        if k == "NOT" and _kw(_at(item, i + 1)) == "NULL":
            c.required = True
        elif k == "PRIMARY":
            c.pk = c.required = True
            t.primary_key.append(c.name)
        elif k == "REFERENCES":
            ref = _reference([c.name], item, i + 1)
            if ref:
                t.references.append(ref)
        elif k == "CHECK" and _at(item, i + 1).kind == "(":
            _check(t, item[i + 2:_group(item, i + 1) - 1], defs)
        elif k == "COMMENT":
            text = _at(item, i + 2 if _at(item, i + 1).kind == "=" else i + 1)
            if text.kind == "str":
                _describe(c, text.value)
        i += 1


def _create_table(st: list[_Tok], defs: Definitions) -> None:
    i = 1
    while _kw(_at(st, i)) in _TABLE_WORDS:
        i += 1
    if _kw(_at(st, i)) != "TABLE":
        return
    i += 1
    if [_kw(_at(st, i + k)) for k in range(3)] == ["IF", "NOT", "EXISTS"]:
        i += 3
    parts, i = _dotted(st, i)
    if not parts or _at(st, i).kind != "(":
        return  # AS SELECT, LIKE another table, PARTITION OF: nothing of its own to read
    end = _group(st, i)
    t = TableDef(parts[-1])
    items = _items(st[i + 1:end - 1])
    for item in items:
        if not _is_constraint(item):
            _column(t, item, defs)
    for item in items:  # a key may come before the columns it names
        if _is_constraint(item):
            _constraint(t, item, defs)
    if not t.columns:
        return
    _primary(t, t.primary_key)
    tail = st[end:]
    for j, x in enumerate(tail):
        if _kw(x) == "COMMENT":
            text = _at(tail, j + 2 if _at(tail, j + 1).kind == "=" else j + 1)
            if text.kind == "str":
                _describe(t, text.value)
    defs.tables[t.name] = t


def _create_type(st: list[_Tok], defs: Definitions) -> None:
    """PostgreSQL's named enum: CREATE TYPE mood AS ENUM ('a', 'b')."""
    parts, i = _dotted(st, 2)
    if parts and _kw(_at(st, i)) == "AS" and _kw(_at(st, i + 1)) == "ENUM":
        values = [{"code": x.value, "name": "", "use": True} for x in st[i + 2:] if x.kind == "str"]
        defs.codes[parts[-1]] = CodeGroup(parts[-1], "", values)


def _alter(st: list[_Tok], defs: Definitions) -> None:
    if _kw(_at(st, 1)) != "TABLE":
        return
    i = 2
    while _kw(_at(st, i)) in ("ONLY", "IF", "EXISTS"):
        i += 1
    parts, i = _dotted(st, i)
    t = defs.table(parts[-1]) if parts else None
    if t is None:
        return
    for item in _items(st[i:]):
        k = next((j for j, x in enumerate(item) if _kw(x) == "ADD"), None)
        if k is None:
            continue
        rest = item[k + 1:]
        if _at(rest, 0).kind == "(":  # Oracle: ADD (CONSTRAINT ..., CONSTRAINT ...)
            subs = _items(rest[1:_group(rest, 0) - 1])
        else:
            subs = [rest] if rest else []
        for sub in subs:
            if _is_constraint(sub):
                _constraint(t, sub, defs)


def _comment_on(st: list[_Tok], defs: Definitions) -> None:
    kind = _kw(_at(st, 2))
    parts, i = _dotted(st, 3)
    text = _at(st, i + 1)
    if _kw(_at(st, i)) != "IS" or text.kind != "str" or not parts:
        return
    if kind == "TABLE":
        t = defs.table(parts[-1])
        if t is not None:
            _describe(t, text.value)
    elif kind == "COLUMN" and len(parts) > 1:
        t = defs.table(parts[-2])
        c = t.column(parts[-1]) if t is not None else None
        if c is not None:
            _describe(c, text.value)


def _extended_property(st: list[_Tok], defs: Definitions) -> None:
    """SQL Server keeps its comments as MS_Description properties: name, value, then type and name of each level."""
    v = [x.value for x in st if x.kind == "str"]
    if len(v) < 2 or v[0] != "MS_Description":
        return
    levels = {v[k].upper(): v[k + 1] for k in range(2, len(v) - 1, 2)}
    t = defs.table(levels.get("TABLE", ""))
    if t is None:
        return
    c = t.column(levels["COLUMN"]) if "COLUMN" in levels else None
    if "COLUMN" not in levels:
        _describe(t, v[1])
    elif c is not None:
        _describe(c, v[1])


def _sql(data: bytes, source: str) -> Definitions:
    defs = Definitions(sources=[source])
    for st in _statements(_sql_tokens(_text(data, source))):
        head = _kw(st[0])
        if head == "CREATE" and _kw(_at(st, 1)) == "TYPE":
            _create_type(st, defs)
        elif head == "CREATE":
            _create_table(st, defs)
        elif head == "ALTER":
            _alter(st, defs)
        elif head == "COMMENT" and _kw(_at(st, 1)) == "ON":
            _comment_on(st, defs)
        elif head in ("EXEC", "EXECUTE") and any(_kw(x) == "SP_ADDEXTENDEDPROPERTY" for x in st):
            _extended_property(st, defs)
    return _found(defs, source)


# ---- DBML ----------------------------------------------------------------------------------------------------

_DBML_WORD = re.compile(r"[\w$]+")


def _dbml_tokens(text: str) -> list[_Tok]:
    out: list[_Tok] = []
    i, n, first = 0, len(text), True
    while i < n:
        c = text[i]
        if c == "\n":
            first, i = True, i + 1
            continue
        if c.isspace() or c == "?":  # a ? only marks one side of a relation optional
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if text.startswith("'''", i):
            j = _closing(text, i + 2, "'''", True)
            out.append(_Tok("str", text[i + 3:j].replace("\\'", "'").strip(), first))
            i = j + 3
        elif c in "'\"`":
            j = _closing(text, i, c, True)
            kind = {"'": "str", '"': "name", "`": "expr"}[c]
            out.append(_Tok(kind, text[i + 1:j].replace(f"\\{c}", c), first))
            i = j + 1
        elif text.startswith("<>", i):
            out.append(_Tok("<>", "<>", first))
            i += 2
        elif m := _DBML_WORD.match(text, i):
            out.append(_Tok("num" if m.group().isdigit() else "word", m.group(), first))
            i = m.end()
        else:
            out.append(_Tok(c, c, first))
            i += 1
        first = False
    return out


class _Dbml:
    """DBML as published at dbml.dbdiagram.io/docs."""

    def __init__(self, toks: list[_Tok], source: str):
        self.t, self.i = toks, 0
        self.defs = Definitions(sources=[source])
        self.aliases: dict[str, str] = {}
        self.partials: dict[str, TableDef] = {}
        self.injects: dict[str, list[str]] = {}
        self.refs: list[tuple[str, tuple, tuple, bool]] = []

    @property
    def kind(self) -> str:
        return _at(self.t, self.i).kind

    def word(self, ahead: int = 0) -> str:
        return _kw(_at(self.t, self.i + ahead)).lower()

    def path(self) -> list[str]:
        parts, self.i = _dotted(self.t, self.i)
        return parts

    def skip_block(self) -> None:
        depth = 0
        while self.i < len(self.t):
            depth += (self.kind == "{") - (self.kind == "}")
            self.i += 1
            if depth == 0:
                return

    def settings(self) -> list[tuple[str, list[_Tok]]]:
        """[a, b: c] as (key, what follows the colon), with the cursor past the bracket."""
        items: list[list[_Tok]] = [[]]
        depth = 0
        self.i += 1
        while self.i < len(self.t):
            t = self.t[self.i]
            self.i += 1
            if t.kind == "]":
                break
            depth += (t.kind == "(") - (t.kind == ")")
            if t.kind == "," and depth == 0:
                items.append([])
            else:
                items[-1].append(t)
        out = []
        for item in items:
            colon = next((k for k, x in enumerate(item) if x.kind == ":"), len(item))
            out.append((" ".join(x.value.lower() for x in item[:colon]), item[colon + 1:]))
        return out

    def run(self) -> Definitions:
        while self.i < len(self.t):
            w = self.word()
            if w in ("table", "tablepartial"):
                self.table(w == "tablepartial")
            elif w == "enum":
                self.enum()
            elif w == "ref":
                self.ref()
            elif self.kind == "{":
                self.skip_block()
            else:
                self.i += 1
        return self.finish()

    def table(self, partial: bool) -> None:
        self.i += 1
        path = self.path()
        if not path:
            return
        t = TableDef(path[-1])
        if self.word() == "as":
            self.aliases[_at(self.t, self.i + 1).value] = t.name
            self.i += 2
        if self.kind == "[":
            note = next((v for k, v in self.settings() if k == "note" and v), None)
            if note:
                _describe(t, note[0].value)
        if self.kind != "{":
            return
        self.i += 1
        while self.i < len(self.t) and self.kind != "}":
            ahead = _at(self.t, self.i + 1).kind
            if self.word() == "indexes" and ahead == "{":
                self.indexes(t)
            elif self.word() == "note" and ahead in (":", "{"):
                self.i += 2
                if self.kind == "str":
                    _describe(t, self.t[self.i].value)
                    self.i += 1
                if ahead == "{":
                    self.i += 1
            elif self.kind == "~":
                self.injects.setdefault(t.name, []).append(_at(self.t, self.i + 1).value)
                self.i += 2
            elif ahead == "{" or self.word() == "records":  # checks and records say nothing about the structure
                while self.kind not in ("{", "}", ""):
                    self.i += 1
                self.skip_block()
            elif self.kind in ("word", "name"):
                self.column(t)
            else:
                self.i += 1
        self.i += 1
        if partial:
            self.partials[t.name] = t
        else:
            self.defs.tables[t.name] = t

    def column(self, t: TableDef) -> None:
        c = ColumnDef(self.t[self.i].value)
        t.columns.append(c)
        self.i += 1
        kinds: list[_Tok] = []
        while self.i < len(self.t):
            x = self.t[self.i]
            if x.first or x.kind == "}" or (x.kind == "[" and _at(self.t, self.i + 1).kind != "]"):
                break
            kinds.append(x)
            self.i += 1
        c.type, c.length, _ = _type_of(kinds)
        if self.kind != "[" or self.t[self.i].first:
            return
        for key, value in self.settings():
            if key in ("pk", "primary key"):
                c.pk = c.required = True
                t.primary_key.append(c.name)
            elif key == "not null":
                c.required = True
            elif key == "note" and value:
                _describe(c, value[0].value)
            elif key == "ref" and len(value) > 1:
                self.refs.append((value[0].kind, (t.name, [c.name]), self.endpoint(value[1:]), True))

    def indexes(self, t: TableDef) -> None:
        self.i += 2
        while self.kind not in ("}", ""):
            if self.kind == "(":
                end = _group(self.t, self.i)
                cols = [x[0].value for x in _items(self.t[self.i + 1:end - 1])]
                self.i = end
            else:
                cols = [self.t[self.i].value]
                self.i += 1
            if self.kind == "[" and any(k in ("pk", "primary key") for k, _ in self.settings()):
                _primary(t, cols)
        self.i += 1

    def enum(self) -> None:
        self.i += 1
        path = self.path()
        if not path:
            return
        g = CodeGroup(path[-1])
        if self.word() == "as":
            self.aliases[_at(self.t, self.i + 1).value] = g.name
            self.i += 2
        if self.kind != "{":
            return
        self.i += 1
        while self.kind not in ("}", ""):
            value = self.t[self.i].value
            self.i += 1
            note = next((v[0].value for k, v in self.settings() if k == "note" and v), "") if self.kind == "[" else ""
            g.values.append({"code": value, "name": note, "use": True})
        self.i += 1
        self.defs.codes[g.name] = g

    @staticmethod
    def endpoint(toks: list[_Tok]) -> tuple[str, list[str]]:
        parts, i = _dotted(toks, 0)
        if _at(toks, i).kind == "(":  # table.(a, b)
            return (parts[-1] if parts else ""), _bracket_names(toks, i)[0]
        return (parts[-2] if len(parts) > 1 else ""), parts[-1:]

    def ref(self) -> None:
        self.i += 1
        while self.kind not in (":", "{", ""):
            self.i += 1  # the optional name
        if self.kind == ":":
            self.i += 1
            self.ref_line()
        elif self.kind == "{":
            self.i += 1
            while self.kind not in ("}", ""):
                self.ref_line()
            self.i += 1

    def ref_line(self) -> None:
        left: list[_Tok] = []
        right: list[_Tok] = []
        op, start = "", self.i
        while self.i < len(self.t):
            x = self.t[self.i]
            if x.kind == "}" or (x.first and self.i > start):
                break
            if x.kind == "[":
                self.settings()
                break
            self.i += 1
            if x.kind in ("<", ">", "-", "<>") and not op:
                op = x.kind
            else:
                (right if op else left).append(x)
        if op and left and right:
            self.refs.append((op, self.endpoint(left), self.endpoint(right), False))

    def finish(self) -> Definitions:
        for name, partials in self.injects.items():
            t = self.defs.tables.get(name)
            if t is None:
                continue
            own = {c.name for c in t.columns}  # a table's own columns win, then the partial injected last
            taken: dict[str, ColumnDef] = {}
            for p in (self.partials[x] for x in partials if x in self.partials):
                taken.update({c.name: replace(c) for c in p.columns if c.name not in own})
                t.primary_key = t.primary_key or list(p.primary_key)
            t.columns = [*taken.values(), *t.columns]
        for op, left, right, inline in self.refs:
            if op == "<>":
                continue  # many to many lives in a join table, which the file does not define
            # a one-to-one puts the key on the second side, or on the column that carries the ref
            child, parent = (right, left) if op == "<" or (op == "-" and not inline) else (left, right)
            t = self.defs.table(self.aliases.get(child[0], child[0]))
            if t is not None and child[1] and parent[0]:
                t.references.append({"columns": child[1], "table": self.aliases.get(parent[0], parent[0]),
                                     "ref_columns": parent[1]})
        return self.defs


def _dbml(data: bytes, source: str) -> Definitions:
    p = _Dbml(_dbml_tokens(_text(data, source)), source)
    return _found(p.run(), source, p.aliases)


# ---- modelling tools -----------------------------------------------------------------------------------------


def _child(el: ET.Element, tag: str) -> str:
    return (el.findtext(tag) or "").strip()


def _ref(el: ET.Element, tag: str) -> str:
    """The object a PowerDesigner collection points to: <c:ParentTable><o:Table Ref="o1"/></c:ParentTable>."""
    x = el.find(tag)
    return x[0].get("Ref", "") if x is not None and len(x) else ""


def _pdm(data: bytes, source: str) -> Definitions:
    if not data.lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<"):
        raise IngestError(f"{source}: a binary PowerDesigner model; save it as XML first", "export_needed",
                          export_to="XML")
    root = _xml(data)
    if root.tag != "Model":
        raise IngestError(f"{source}: not a PowerDesigner model", "format")
    defs = Definitions(sources=[source])
    tables: dict[str, TableDef] = {}
    columns: dict[str, ColumnDef] = {}
    owner: dict[str, TableDef] = {}
    outside = {s.get("Id"): _child(s, "Code") for s in root.iter("Shortcut") if s.get("Id")}  # another model's objects
    for el in root.iter("Table"):
        code = _child(el, "Code")
        if not el.get("Id") or not code:
            continue  # a mention of a table, not its definition
        t = TableDef(code, _child(el, "Name"), _child(el, "Comment"))
        for c in el.findall("Columns/Column"):
            col = ColumnDef(_child(c, "Code"), _child(c, "Name"), description=_child(c, "Comment"))
            col.type, col.length, _ = _type_of(_sql_tokens(_child(c, "DataType")))
            col.required = (_child(c, "Column.Mandatory") or _child(c, "Mandatory")) == "1"
            t.columns.append(col)
            columns[c.get("Id", "")], owner[c.get("Id", "")] = col, t
            values = [x.split("\t") for x in _child(c, "ListOfValues").splitlines() if x.strip()]
            if values:
                _code_group(t, col, [v[0] for v in values], defs)
                for item, v in zip(defs.codes[col.code].values, values):
                    item["name"] = v[1].strip() if len(v) > 1 else ""
        keys = {k.get("Id"): [x.get("Ref") for x in k.findall("Key.Columns/Column")] for k in el.findall("Keys/Key")}
        _primary(t, [columns[r].name for r in keys.get(_ref(el, "PrimaryKey"), []) if r in columns])
        tables[el.get("Id", "")] = t
        defs.tables[t.name] = t
    for el in root.iter("Reference"):
        child = tables.get(_ref(el, "ChildTable"))
        pid = _ref(el, "ParentTable")
        parent = tables[pid].name if pid in tables else outside.get(pid)
        if child is None or not parent:
            continue
        src, dst = [], []
        for j in el.findall("Joins/ReferenceJoin"):
            a, b = _ref(j, "Object1"), _ref(j, "Object2")
            if owner.get(a) is child and owner.get(b) is not child:
                a, b = b, a
            if b in columns:
                src.append(columns[b].name)
                dst.append(columns[a].name if a in columns else outside.get(a, ""))
        if src:
            child.references.append({"columns": src, "table": parent, "ref_columns": dst})
    return _found(defs, source)


def _fields(obj: ET.Element) -> dict[str, ET.Element]:
    return {c.get("key", ""): c for c in obj}


def _text_of(f: dict[str, ET.Element], key: str) -> str:
    return (f[key].text or "").strip() if key in f else ""


def _mwb(data: bytes, source: str) -> Definitions:
    z = _Archive(data, source)
    if "document.mwb.xml" not in z.names:
        raise IngestError(f"{source}: not a MySQL Workbench model", "format")
    root = _xml(z.read("document.mwb.xml"))
    defs = Definitions(sources=[source])
    tables: dict[str, TableDef] = {}
    columns: dict[str, ColumnDef] = {}
    found = [o for o in root.iter("value") if o.get("struct-name", "").endswith(".Table") and o.get("id")]
    for obj in found:
        f = _fields(obj)
        t = TableDef(_text_of(f, "name"))
        _describe(t, _text_of(f, "comment"))
        for col in f.get("columns", ()):
            cf = _fields(col)
            c = ColumnDef(_text_of(cf, "name"))
            _describe(c, _text_of(cf, "comment"))
            c.type = (_text_of(cf, "simpleType") or _text_of(cf, "userType")).rsplit(".", 1)[-1].upper()
            c.length = max(int(_text_of(cf, "length") or 0), int(_text_of(cf, "precision") or 0), 0)
            c.required = _text_of(cf, "isNotNull") == "1"
            t.columns.append(c)
            columns[col.get("id", "")] = c
            values = _type_of(_sql_tokens(_text_of(cf, "datatypeExplicitParams")))[2]
            if values:
                _code_group(t, c, values, defs)
        tables[obj.get("id", "")] = t
        defs.tables[t.name] = t
    for obj in found:
        f = _fields(obj)
        t = tables[obj.get("id", "")]
        for index in f.get("indices", ()):
            xf = _fields(index)
            if _text_of(xf, "isPrimary") == "1" or _text_of(xf, "indexType") == "PRIMARY":
                ids = [_text_of(_fields(x), "referencedColumn") for x in xf.get("columns", ())]
                _primary(t, [columns[i].name for i in ids if i in columns])
        for fk in f.get("foreignKeys", ()):
            kf = _fields(fk)
            target = tables.get(_text_of(kf, "referencedTable"))
            src = [columns[x.text].name for x in kf.get("columns", ()) if x.text in columns]
            dst = [columns[x.text].name for x in kf.get("referencedColumns", ()) if x.text in columns]
            if target is not None and src:
                t.references.append({"columns": src, "table": target.name, "ref_columns": dst})
    return _found(defs, source)


_ZIP_MEMBERS = (("word/document.xml", _docx), ("ppt/presentation.xml", _pptx), ("xl/workbook.xml", _sheets),
                ("document.mwb.xml", _mwb), ("Contents/content.hpf", _hwpx), ("Contents/section0.xml", _hwpx))

register([".sql", ".ddl"], _sql)
register(".dbml", _dbml)
register(".pdm", _pdm)
register(".mwb", _mwb)
register(".docx", _docx)
register(".pptx", _pptx)
register(".hwpx", _hwpx)
register([".html", ".htm"], _html)
register([".md", ".markdown"], _md)
register(".txt", _txt)
register(".pdf", _pdf)
register(SHEETS, _sheets)
register(".json", _json)
