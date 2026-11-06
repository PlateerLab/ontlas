"""Anything in, one JSON out: read a file of any kind into the canonical definitions object.

A file is read by its extension, then by what its content looks like, and comes out as `definitions.Definitions`:
tables, codes, terms, messages and documents, the shape of `Definitions.to_dict`. From there one path makes modules.
A format of your own is a python file that calls `register`, loaded with `load_adapters`.

Uploads are untrusted. A zip is read only up to UNPACKED_MAX, whatever it declares, and its entries stay in memory;
XML that declares a document type is refused, so no entity is ever defined or fetched; nothing in a file is run. A
compound file's chains and records are followed a bounded number of steps, whatever it says of itself.
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable, Iterator
from dataclasses import replace
from datetime import datetime, timedelta
from html.parser import HTMLParser
from itertools import accumulate
from pathlib import Path
from typing import NamedTuple
from xml.parsers import expat

from xgen_space.definitions import (
    CodeGroup,
    ColumnDef,
    Definitions,
    TableDef,
    from_sheets,
    header_row,
    read_definitions,
)
from xgen_space.draft import XLSX_UNPACKED_MAX, ReadError, Table, _table, read_file

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
        name = f"xspace_adapter_{path.stem}"
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
        load_adapters(os.environ.get("XSPACE_ADAPTERS", ""))
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
    if data[:16] == b"SQLite format 3\0":
        return _sqlite
    if data[:4] == OLE:
        return _office
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


def _locked(source: str) -> IngestError:
    to = EXPORT_TO.get(Path(source).suffix.lower(), EXPORT_ANY)
    return IngestError(f"{source}: the file has a password; take it off, or export it to {to}", "export_needed",
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


def _slide(out: _Outline, n: int, items: list[tuple[bool, str]]) -> None:
    if items:
        titles = [s for is_title, s in items if is_title]
        out.heading(" ".join(titles) or f"Slide {n}")
        for is_title, s in items:
            if not is_title:
                out.line(s)


def _pptx(data: bytes, source: str) -> Definitions:
    z = _Archive(data, source)
    slides = _slide_files(z)
    if not slides:
        raise IngestError(f"{source}: not a PowerPoint deck", "format")
    out = _Outline()
    for n, name in enumerate(slides, 1):
        tree = _xml(z.read(name)).find("cSld/spTree")
        _slide(out, n, [(is_title, s) for is_title, s in _slide_items(tree if tree is not None else ()) if s.strip()])
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


class _Compound:
    """The streams of an OLE compound file, read from memory. Every chain is followed a bounded number of steps, so a
    malformed file ends in an error, not a loop."""

    END = 0xFFFFFFFE

    def __init__(self, data: bytes, source: str):
        if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" or len(data) < 512:
            raise IngestError(f"{source}: not a compound file", "format")
        self.data, self.source = data, source
        self.size = 1 << struct.unpack_from("<H", data, 30)[0]
        self.mini_size = 1 << struct.unpack_from("<H", data, 32)[0]
        if self.size not in (512, 4096) or self.mini_size != 64:  # the only sizes there are; a FAT grows with the sector
            raise IngestError(f"{source}: not a compound file", "format")
        self.limit = len(data) // self.size + 2
        directory, = struct.unpack_from("<I", data, 48)
        self.cutoff, mini_fat, _, difat_next, difat_count = struct.unpack_from("<IIIII", data, 56)
        places = [x for x in struct.unpack_from("<109I", data, 76) if x < self.END]
        for _ in range(min(difat_count, self.limit)):  # the list of FAT sectors goes on in sectors of its own
            if difat_next >= self.END:
                break
            words = struct.unpack_from(f"<{self.size // 4}I", self._sector(difat_next))
            places += [x for x in words[:-1] if x < self.END]
            difat_next = words[-1]
            if len(places) > self.limit:  # a file has no more FAT sectors than sectors: this list runs in a circle
                raise IngestError(f"{source}: the sector list does not end", "format")
        self.fat = [w for p in places for w in struct.unpack(f"<{self.size // 4}I", self._sector(p))]
        chain = self._chain(mini_fat, self.fat)
        self.mini_fat = [w for p in chain for w in struct.unpack(f"<{self.size // 4}I", self._sector(p))]
        self.entries = self._entries(b"".join(self._sector(p) for p in self._chain(directory, self.fat)))
        root = self.entries[0] if self.entries else None
        if root is None:
            raise IngestError(f"{source}: no directory", "format")
        self.mini = b"".join(self._sector(p) for p in self._chain(root["start"], self.fat))
        self.paths: dict[str, dict] = {}
        self._walk(root["child"], "", set())

    def _sector(self, n: int) -> bytes:
        at = (n + 1) * self.size
        if at + self.size > len(self.data) + self.size:
            raise IngestError(f"{self.source}: a sector lies past the end", "format")
        return self.data[at:at + self.size].ljust(self.size, b"\0")

    def _chain(self, first: int, fat: list[int]) -> list[int]:
        out, n = [], first
        while n < self.END and n < len(fat):
            out.append(n)
            if len(out) > self.limit * (self.size // self.mini_size + 1):
                raise IngestError(f"{self.source}: a sector chain does not end", "format")
            n = fat[n]
        return out

    @staticmethod
    def _entries(raw: bytes) -> list[dict]:
        out = []
        for at in range(0, len(raw) - 127, 128):
            e = raw[at:at + 128]
            length, = struct.unpack_from("<H", e, 64)
            left, right, child = struct.unpack_from("<III", e, 68)
            start, = struct.unpack_from("<I", e, 116)
            size, = struct.unpack_from("<Q", e, 120)
            out.append({"name": e[:max(length - 2, 0)].decode("utf-16-le", "ignore"), "type": e[66], "left": left,
                        "right": right, "child": child, "start": start, "size": size})
        return out

    def _walk(self, n: int, prefix: str, seen: set[int]) -> None:
        if n >= len(self.entries) or n in seen:
            return
        seen.add(n)
        e = self.entries[n]
        self._walk(e["left"], prefix, seen)
        self._walk(e["right"], prefix, seen)
        path = prefix + e["name"]
        if e["type"] == 2:
            self.paths[path] = e
        elif e["type"] == 1:
            self._walk(e["child"], path + "/", seen)

    def find(self, name: str) -> str | None:
        """The path of a stream at the top of the file; some writers spell these names in other cases."""
        return next((p for p in self.paths if p.lower() == name.lower()), None)

    def read(self, path: str) -> bytes:
        e = self.paths[path]
        size = e["size"] & 0xFFFFFFFF if self.size == 512 else e["size"]  # older writers left the high half unset
        if size > UNPACKED_MAX:
            raise IngestError(f"{self.source}: {path} is too large", "too_large")
        if size < self.cutoff:
            raw = b"".join(self.mini[p * self.mini_size:(p + 1) * self.mini_size] for p in self._chain(e["start"], self.mini_fat))
        else:
            raw = b"".join(self._sector(p) for p in self._chain(e["start"], self.fat))
        return raw[:size]


def _compound(data: bytes, source: str) -> _Compound:
    """A compound file; the older binary formats, and a file that only looks like one, are told what to export to."""
    try:
        return _Compound(data, source)
    except (IngestError, struct.error, IndexError):
        raise _export(source) from None


_HWP_WIDE = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}  # controls of eight units
_HWP_PARA_TEXT = 67


def _hwp_line(raw: bytes) -> str:
    units = struct.unpack(f"<{len(raw) // 2}H", raw[:len(raw) // 2 * 2])
    out, i = [], 0
    while i < len(units):
        u = units[i]
        if u in _HWP_WIDE:
            if u == 9:
                out.append(ord(" "))
            i += 8
            continue
        if u >= 32:
            out.append(u)
        elif u in (10, 30, 31):
            out.append(ord(" "))
        i += 1
    return struct.pack(f"<{len(out)}H", *out).decode("utf-16-le", "ignore")


def _hwp_lines(raw: bytes) -> Iterator[str]:
    """The paragraphs of a section: records of a tag and a size, the text in its own tag, tables' cells in order."""
    i = 0
    while i + 4 <= len(raw):
        head, = struct.unpack_from("<I", raw, i)
        i += 4
        size = head >> 20
        if size == 0xFFF:
            size, = struct.unpack_from("<I", raw, i)
            i += 4
        if head & 0x3FF == _HWP_PARA_TEXT:
            yield _hwp_line(raw[i:i + size])
        i += size


def _hwp(data: bytes, source: str) -> Definitions:
    """Text of a Hancom .hwp (5.x), standard library only; a file with a password or for viewing only says so."""
    z = _compound(data, source)
    if "FileHeader" not in z.paths or not z.read("FileHeader").startswith(b"HWP Document File"):
        raise _export(source)
    flags, = struct.unpack_from("<I", z.read("FileHeader"), 36)
    sections = sorted((p for p in z.paths if re.fullmatch(r"BodyText/Section\d+", p)), key=lambda p: int(p[16:]))
    if flags & 2 or flags & 4 or not sections:  # a password, or a distribution copy whose body is encrypted
        raise _export(source)
    out = _Outline()
    for name in sections:
        raw = z.read(name)
        if flags & 1:
            inflate = zlib.decompressobj(-15)
            try:
                raw = inflate.decompress(raw, UNPACKED_MAX)
            except zlib.error:
                raise IngestError(f"{source}: {name} cannot be unpacked", "format") from None
            if inflate.unconsumed_tail:
                raise IngestError(f"{source}: {name} unpacks past the limit", "too_large")
        for line in _hwp_lines(raw):
            out.numbered(line)
    return _document(out, source)


# ---- older Office files --------------------------------------------------------------------------------------

_CONTROLS = {c: None for c in range(32) if c != 9}
_DOC_CHARS = {**_CONTROLS, 0x0B: "\n", 0x1E: "-"}  # a line break, a hyphen that does not break
_DOC_MARKS = re.compile("[\r\x07\x0c]")  # the end of a paragraph, of a table cell or row, of a page
_DOC_FIELD = re.compile("[\x13\x14\x15]")  # a field opens, its instruction ends, it closes
_DOC_HEADINGS = {*range(1, 10), 62}  # the built-in ids of Heading 1 to 9 and Title, the same in every language
_DOC_OPERANDS = (1, 1, 2, 4, 2, 2, 0, 3)  # a property's operand size by the top bits of its id; 0: its first byte says
_DOC_PLAIN = (0, False, False)


class _DocFields:
    """A field is an instruction and then what it shows; only that is text. Fields nest and may cross paragraphs."""

    def __init__(self) -> None:
        self.open = bytearray()  # each open field, 1 while still in its instruction
        self.hidden = 0

    def strip(self, text: str) -> str:
        out, at = [], 0
        for m in _DOC_FIELD.finditer(text):
            if not self.hidden:
                out.append(text[at:m.start()])
            at = m.end()
            if m.group() == "\x13":
                self.open.append(1)
                self.hidden += 1
            elif self.open:
                self.hidden -= self.open[-1]
                self.open[-1] = 0
                if m.group() == "\x15":
                    self.open.pop()
        if not self.hidden:
            out.append(text[at:])
        return "".join(out)


class _DocProperties:
    """What a paragraph is, by where its mark lies: the stream keeps this in 512-byte pages, a run of marks to a list of
    properties. Marks may be told in any order, so the lists looked through share one budget."""

    def __init__(self, word: bytes, plc: bytes, source: str):
        count = max(len(plc) - 4, 0) // 8
        self.word, self.source, self.left = word, source, 2 * len(word)
        self.limits = struct.unpack_from(f"<{count + 1}I", plc) if count else ()
        self.pages = struct.unpack_from(f"<{count}I", plc, 4 * (count + 1)) if count else ()
        self.last: tuple[tuple[int, int], tuple[int, bool, bool]] = ((-1, -1), _DOC_PLAIN)

    def at(self, fc: int) -> tuple[int, bool, bool]:
        """(style, inside a table, ends a table row) of the paragraph whose mark lies at fc."""
        i = bisect_right(self.limits, fc) - 1
        if not 0 <= i < len(self.pages):
            return _DOC_PLAIN
        page = self.word[self.pages[i] * 512:self.pages[i] * 512 + 512]
        runs = page[-1] if len(page) == 512 else 0
        if not 0 < runs < 30:  # no more fit a page
            return _DOC_PLAIN
        j = bisect_right(struct.unpack_from(f"<{runs + 1}I", page), fc) - 1
        if not 0 <= j < runs:
            return _DOC_PLAIN
        at = page[4 * (runs + 1) + 13 * j] * 2
        if at == 0:
            return _DOC_PLAIN
        if (self.pages[i], at) != self.last[0]:
            self.last = (self.pages[i], at), self._read(page, at)
        return self.last[1]

    def _read(self, page: bytes, at: int) -> tuple[int, bool, bool]:
        size = page[at]
        start = at + 1
        if size:
            size = size * 2 - 1
        else:
            size, start = page[at + 1] * 2, at + 2
        blob = page[start:start + size]
        in_table = row_end = False
        i = 2
        while i + 2 < len(blob):
            self.left -= 1
            if self.left < 0:
                raise IngestError(f"{self.source}: paragraph properties do not end", "format")
            sprm, = struct.unpack_from("<H", blob, i)
            i += 2
            if sprm == 0x2416:
                in_table = bool(blob[i])
            elif sprm == 0x2417:
                row_end = bool(blob[i])
            elif sprm == 0x6646:  # properties too long for the page; only the end of a wide table row has so many
                row_end = True
            size = _DOC_OPERANDS[sprm >> 13]
            if sprm == 0xD608:  # the one list of properties whose length takes two bytes
                size = int.from_bytes(blob[i:i + 2], "little") + 1
            i += size or blob[i] + 1
        return (int.from_bytes(blob[:2], "little"), in_table, row_end)


def _doc_headings(raw: bytes) -> set[int]:
    """The styles that are headings, from the style sheet: a header, then each style's size and id."""
    if len(raw) < 4:
        return set()
    head, count = struct.unpack_from("<HH", raw)
    at, out = 2 + head, set()
    for style in range(count):
        if at + 2 > len(raw):
            break
        size, = struct.unpack_from("<H", raw, at)
        if size >= 2 and struct.unpack_from("<H", raw, at + 2)[0] & 0xFFF in _DOC_HEADINGS:
            out.add(style)
        at += 2 + size
    return out


def _doc_paragraphs(word: bytes, clx: bytes, left: int, source: str) -> Iterator[tuple[str, str, int]]:
    """The main text as (paragraph, the mark that ended it, where that mark lies), read piece by piece. Each piece is
    one byte a character or two, and the pieces need not lie in order: a fast save appends the changes."""
    at = 0
    while clx[at:at + 1] == b"\x01":  # formatting comes before the piece table
        at += 3 + struct.unpack_from("<H", clx, at + 1)[0]
    if clx[at:at + 1] != b"\x02":
        raise IngestError(f"{source}: no piece table", "format")
    size, = struct.unpack_from("<I", clx, at + 1)
    count = (size - 4) // 12
    if count < 1:
        raise IngestError(f"{source}: no piece table", "format")
    cps = struct.unpack_from(f"<{count + 1}I", clx, at + 5)
    pieces = at + 5 + 4 * (count + 1)
    buf: list[str] = []
    for i in range(count):
        if cps[i + 1] < cps[i]:
            raise IngestError(f"{source}: the piece table runs backwards", "format")
        n = min(cps[i + 1] - cps[i], left)  # together the pieces give no more than the text's own length
        left -= n
        if not left and not n:
            break
        fc, = struct.unpack_from("<I", clx, pieces + 8 * i + 2)
        narrow = bool(fc & 0x40000000)
        base = (fc & 0x3FFFFFFF) // 2 if narrow else fc & 0x3FFFFFFF
        text = (word[base:base + n].decode("cp1252", "replace") if narrow
                else word[base:base + 2 * n].decode("utf-16-le", "replace"))
        start = used = 0
        for m in _DOC_MARKS.finditer(text):
            part = text[start:m.start()]
            used += len(part) if narrow else len(part.encode("utf-16-le"))  # a pair of surrogates is one character
            yield "".join([*buf, part]), m.group(), base + used
            buf = []
            used += 1 if narrow else 2
            start = m.end()
        buf.append(text[start:])
    if any(buf):
        yield "".join(buf), "", 0


def _doc(z: _Compound, path: str, source: str) -> Definitions:
    """Text of a Word 97 to 2003 .doc: paragraphs into sections at heading styles and numbers, a table's rows as rows.
    Only the main text is read; footnotes, headers and text boxes lie outside it."""
    word = z.read(path)
    ident, = struct.unpack_from("<H", word)
    flags, = struct.unpack_from("<H", word, 0x0A)
    if ident != 0xA5EC:  # Word 95 and before lay the file out differently
        raise _export(source)
    if flags & 0x0100:
        raise _locked(source)
    name = z.find("1Table" if flags & 0x0200 else "0Table")
    if name is None:
        raise IngestError(f"{source}: no table stream", "format")
    table = z.read(name)

    def part(at: int) -> bytes:
        fc, size = struct.unpack_from("<II", word, at)
        return table[fc:fc + size]

    length, = struct.unpack_from("<I", word, 76)
    if length > UNPACKED_MAX:
        raise IngestError(f"{source}: the text runs past {UNPACKED_MAX >> 20}MB", "too_large")
    headings, props, fields = _doc_headings(part(0xA2)), _DocProperties(word, part(0x102), source), _DocFields()
    out = _Outline()
    row: list[str] = []
    cell: list[str] = []
    for raw, mark, fc in _doc_paragraphs(word, part(0x1A2), length, source):
        text = fields.strip(raw).translate(_DOC_CHARS)
        style, in_table, row_end = props.at(fc)
        if mark == "\x07" and row_end:
            if any(row):
                out.line(" | ".join(row))
            row = []
        elif mark == "\x07":
            row.append(" ".join(" ".join(cell + [text]).split()))  # a row stays one line, whatever breaks a cell holds
            cell = []
        elif in_table:
            cell.append(text)
        elif style in headings:
            out.heading(text)
        else:
            out.numbered(text)
    if any(row):
        out.line(" | ".join(row))
    return _document(out, source)


_PPT_TEXT = {0x0FA0: "utf-16-le", 0x0FA8: "latin-1"}  # TextCharsAtom, TextBytesAtom
_PPT_TITLES = (0, 6)  # what a TextHeaderAtom calls a title and a centred title


class _PptRecords:
    """The records of a PowerPoint stream. Offsets in the file may point anywhere, so all the walks spend from one
    budget, and records that point back at each other end in an error."""

    def __init__(self, raw: bytes, source: str):
        self.raw, self.source, self.left = raw, source, len(raw) // 2 + 64

    def _spend(self, n: int) -> None:
        self.left -= n
        if self.left < 0:
            raise IngestError(f"{self.source}: the records do not end", "format")

    def end_of(self, at: int, kind: int) -> int:
        """Where the record at `at` ends, when it is the kind the file promised."""
        _, found, size = struct.unpack_from("<HHI", self.raw, at)
        if found != kind:
            raise IngestError(f"{self.source}: a record is not where the file says", "format")
        return at + 8 + size

    def records(self, at: int, end: int, inside: bool = True) -> Iterator[tuple[int, int, int, int]]:
        """(version and instance, kind, where the body lies, its size) of each record; a container's children follow it
        in the stream, so going on from its head walks into them with no stack to overflow."""
        end = min(end, len(self.raw))
        while at + 8 <= end:
            self._spend(1)
            head, kind, size = struct.unpack_from("<HHI", self.raw, at)
            yield head, kind, at + 8, size
            at += 8 if inside and head & 0xF == 0xF else 8 + size

    def places(self, at: int) -> tuple[int, dict[int, int]]:
        """The document's id and where each id lies. Each save adds an edit; the newest says, older ones fill in."""
        document, places, seen = 0, {}, set()
        while at and at not in seen:
            seen.add(at)
            self._spend(1)
            self.end_of(at, 0x0FF5)
            last, directory, ref = struct.unpack_from("<III", self.raw, at + 16)
            document = document or ref
            i, end = directory + 8, self.end_of(directory, 0x1772)
            while i + 4 <= end:
                head, = struct.unpack_from("<I", self.raw, i)
                count = head >> 20
                self._spend(count + 1)
                for k, offset in enumerate(struct.unpack_from(f"<{count}I", self.raw, i + 4)):
                    places.setdefault((head & 0xFFFFF) + k, offset)
                i += 4 + 4 * count
            at = last
        return document, places

    def said(self, at: int, end: int) -> Iterator[int | tuple[bool, str]]:
        """What the records say in order: a slide's id where it starts in a slide list, and (is the title, a line)."""
        title = False
        for _, kind, body, size in self.records(at, end):
            if kind == 0x03F3:  # SlidePersistAtom
                yield struct.unpack_from("<I", self.raw, body)[0]
            elif kind == 0x0F9F:  # TextHeaderAtom: what the text after it is
                title = struct.unpack_from("<I", self.raw, body)[0] in _PPT_TITLES
            elif kind in _PPT_TEXT:
                self._spend(size // 8)  # text is what grows, when many slides name the same record
                for line in re.split("[\r\n\x0b]", self.raw[body:body + size].decode(_PPT_TEXT[kind], "replace")):
                    line = line.translate(_CONTROLS)
                    if line.strip():
                        yield title, line


def _ppt(z: _Compound, path: str, source: str) -> Definitions:
    """Text of a PowerPoint 97 to 2003 deck, a section to a slide. A save may only append, so the stream still holds
    what later edits replaced: slides are found from the newest edit, never by scanning. Title and body text is in the
    slide list, the text of other shapes in the slide; masters and notes have their own and are left out."""
    if z.find("EncryptedSummary"):
        raise _locked(source)
    name = z.find("Current User")
    user = z.read(name) if name else b""
    if len(user) < 20:  # PowerPoint 95 and before
        raise _export(source)
    token, edit = struct.unpack_from("<II", user, 12)
    if token == 0xF3D1C4DF:
        raise _locked(source)
    s = _PptRecords(z.read(path), source)
    document, places = s.places(edit)
    if document not in places:
        raise IngestError(f"{source}: no document record", "format")
    at = places[document]
    slides: list[tuple[int, list[tuple[bool, str]]]] = []
    for head, kind, body, size in s.records(at + 8, s.end_of(at, 0x03E8), inside=False):
        if kind == 0x0FF0 and head >> 4 == 0:  # the list of slides, where the others are masters and notes
            for x in s.said(body, body + size):
                if isinstance(x, int):
                    slides.append((x, []))
                elif slides:
                    slides[-1][1].append(x)
    out = _Outline()
    for n, (ref, items) in enumerate(slides, 1):
        if ref in places:
            listed = {line for _, line in items}
            items += [x for x in s.said(places[ref] + 8, s.end_of(places[ref], 0x03EE))
                      if not isinstance(x, int) and x[1] not in listed]
        _slide(out, n, items)
    return _document(out, source, "screen")


_XLS_BOF = (0x0009, 0x0209, 0x0409, 0x0809)
_XLS_EOF = 0x000A
_XLS_CONTINUE = 0x003C
_XLS_SST = 0x00FC
_XLS_LABELSST, _XLS_NUMBER, _XLS_RK, _XLS_MULRK = 0x00FD, 0x0203, 0x027E, 0x00BD
_XLS_LABEL, _XLS_RSTRING, _XLS_BOOL, _XLS_FORMULA, _XLS_STRING = 0x0204, 0x00D6, 0x0205, 0x0006, 0x0207
_XLS_DATE_FORMATS = (*range(14, 23), *range(27, 37), *range(45, 48), *range(50, 59))  # built in, Korean ones among them
_XLS_1900, _XLS_1904 = datetime(1899, 12, 30), datetime(1904, 1, 1)
_XLS_CELLS = 1 << 23  # a workbook's cells, the blanks between them counted: a small file can spread a few very wide


def _biff(raw: bytes) -> Iterator[tuple[int, int, bytes]]:
    """(where it starts, id, body) of each record."""
    at = 0
    while at + 4 <= len(raw):
        rid, size = struct.unpack_from("<HH", raw, at)
        yield at, rid, raw[at + 4:at + 4 + size]
        at += 4 + size


def _xls_text(rec: bytes, at: int, width: int = 2) -> str:
    """A string: its length in `width` bytes, a flag, then characters of one byte unless the flag says two."""
    n = int.from_bytes(rec[at:at + width], "little")
    at += width + 1
    if rec[at - 1] & 1:
        return rec[at:at + 2 * n].decode("utf-16-le", "replace")
    return rec[at:at + n].decode("latin-1")


def _xls_strings(parts: list[bytes]) -> list[str]:
    """The shared strings. They run on across CONTINUE records, and a string cut by one goes on after a flag byte
    saying how wide its characters are from there."""
    blob = b"".join(parts)
    ends = list(accumulate(map(len, parts)))
    count, = struct.unpack_from("<I", blob, 4)
    at, out = 8, []
    for _ in range(min(count, len(blob) // 3)):  # a string takes at least three bytes, whatever the count says
        if at + 3 > len(blob):
            break
        left, flags = struct.unpack_from("<HB", blob, at)
        at += 3
        wide, runs, extra = flags & 1, 0, 0
        if flags & 8:
            runs, = struct.unpack_from("<H", blob, at)
            at += 2
        if flags & 4:
            extra, = struct.unpack_from("<i", blob, at)
            at += 4
        text = []
        while left and at < len(blob):
            take = min(left, (ends[bisect_left(ends, at)] - at) >> wide)
            text.append(blob[at:at + (take << wide)].decode("utf-16-le" if wide else "latin-1", "replace"))
            at += take << wide
            left -= take
            if left and at < len(blob):
                wide = blob[at] & 1
                at += 1
        out.append("".join(text))
        at += 4 * runs + max(extra, 0)
    return out


def _xls_is_date(code: str) -> bool:
    """A number format shows a date when y, m, d, h or s stand outside its quotes, escapes and brackets."""
    return bool(re.search(r"[ymdhs]", re.sub(r'"[^"]*"|\\.|_.|\*.|\[[^\]]*\]', "", code), re.I))


def _xls_date(v: float, epoch: datetime) -> object:
    """The serial number of a date as .xlsx gives it. Excel takes 1900 for a leap year, so its first dates are a day
    off, and a fraction alone is a time of day."""
    try:
        day, part = divmod(v, 1)
        diff = timedelta(milliseconds=round(part * 86_400_000))
        if 0 <= v < 1 and diff.days == 0:
            return (datetime.min + diff).time()
        if 0 < v < 60 and epoch == _XLS_1900:
            day += 1
        return epoch + timedelta(days=day) + diff
    except (OverflowError, ValueError):  # nan and the like: a date no calendar holds stays the number it is
        return v


def _xls_rk(rk: int) -> float:
    """A number packed in four bytes: an integer or the top of a double, perhaps a hundred times too large."""
    if rk & 2:
        v = float(struct.unpack("<i", struct.pack("<I", rk & 0xFFFFFFFC))[0] >> 2)
    else:
        v = struct.unpack("<d", b"\0\0\0\0" + struct.pack("<I", rk & 0xFFFFFFFC))[0]
    return v / 100 if rk & 1 else v


class _XlsBook(NamedTuple):
    names: dict[int, str]  # the worksheets, by where their records start
    strings: list[str]
    dates: list[bool]  # by cell format: does a number in it show a date
    epoch: datetime


def _xls_book(records: Iterator[tuple[int, int, bytes]], source: str) -> _XlsBook:
    """What the workbook says before its sheets, up to its first end record."""
    names: dict[int, str] = {}
    parts: list[bytes] = []
    formats = dict.fromkeys(_XLS_DATE_FORMATS, True)
    xfs: list[int] = []
    epoch, previous = _XLS_1900, 0
    for _, rid, rec in records:
        if rid == _XLS_EOF:
            break
        if rid == 0x002F:  # FILEPASS
            raise _locked(source)
        if rid == 0x0085 and rec[5] == 0:  # BOUNDSHEET of a worksheet, not of a chart or macros
            names[struct.unpack_from("<I", rec)[0]] = _xls_text(rec, 6, 1)
        elif rid == 0x041E:  # FORMAT
            formats[struct.unpack_from("<H", rec)[0]] = _xls_is_date(_xls_text(rec, 2))
        elif rid == 0x00E0:  # XF
            xfs.append(struct.unpack_from("<H", rec, 2)[0])
        elif rid == 0x0022 and rec[:1] == b"\x01":  # DATEMODE
            epoch = _XLS_1904
        elif rid == _XLS_SST or (rid == _XLS_CONTINUE and previous == _XLS_SST):
            parts.append(rec)
        if rid != _XLS_CONTINUE:
            previous = rid
    return _XlsBook(names, _xls_strings(parts) if parts else [], [formats.get(x, False) for x in xfs], epoch)


def _xls_too_large(source: str) -> IngestError:
    return IngestError(f"{source}: the workbook spreads over more than {_XLS_CELLS} cells", "too_large")


def _xls_cells(records: Iterator[tuple[int, int, bytes]], book: _XlsBook,
               source: str) -> dict[int, dict[int, dict[int, object]]]:
    """Each worksheet's cells by row and column. One pass in file order: a sheet's offset is only checked against where
    records fall, so sheets that claim the same place cannot make it read twice."""
    room = _XLS_CELLS

    def put(rows: dict[int, dict[int, object]], r: int, c: int, value: object) -> None:
        nonlocal room
        if c < 256 and value is not None:  # a sheet has no more columns; a wider cell only spreads the rows out
            rows.setdefault(r, {})[c] = value
            room -= 1
            if room < 0:
                raise _xls_too_large(source)

    def number(v: float, xf: int) -> object:
        if xf < len(book.dates) and book.dates[xf]:
            return _xls_date(v, book.epoch)
        return int(v) if v.is_integer() else v  # .xlsx gives a whole number as one, and a header must read the same

    sheets: dict[int, dict[int, dict[int, object]]] = {}
    rows: dict[int, dict[int, object]] | None = None
    depth = 0
    waiting: tuple[int, int] | None = None
    for at, rid, rec in records:
        if rid in _XLS_BOF:
            depth += 1
            if depth == 1:
                rows = sheets.setdefault(at, {}) if at in book.names else None
        elif rid == _XLS_EOF:
            depth = max(depth - 1, 0)
        elif rows is None or depth != 1:  # a chart inside a sheet has cells of its own
            continue
        elif rid == _XLS_MULRK:
            r, c = struct.unpack_from("<HH", rec)
            for k in range((len(rec) - 6) // 6):
                xf, rk = struct.unpack_from("<HI", rec, 4 + 6 * k)
                put(rows, r, c + k, number(_xls_rk(rk), xf))
        elif rid == _XLS_STRING:
            if waiting:
                put(rows, *waiting, _xls_text(rec, 0))
            waiting = None
        elif rid in (_XLS_LABELSST, _XLS_NUMBER, _XLS_RK, _XLS_LABEL, _XLS_RSTRING, _XLS_BOOL, _XLS_FORMULA):
            r, c, xf = struct.unpack_from("<HHH", rec)
            if rid == _XLS_LABELSST:
                i, = struct.unpack_from("<I", rec, 6)
                put(rows, r, c, book.strings[i] if i < len(book.strings) else None)
            elif rid == _XLS_NUMBER:
                put(rows, r, c, number(struct.unpack_from("<d", rec, 6)[0], xf))
            elif rid == _XLS_RK:
                put(rows, r, c, number(_xls_rk(struct.unpack_from("<I", rec, 6)[0]), xf))
            elif rid == _XLS_BOOL:
                put(rows, r, c, bool(rec[6]) if rec[7] == 0 else None)
            elif rid != _XLS_FORMULA:
                put(rows, r, c, _xls_text(rec, 6))
            elif rec[12:14] != b"\xff\xff":
                put(rows, r, c, number(struct.unpack_from("<d", rec, 6)[0], xf))
            elif rec[6] == 0:  # the text is in the STRING record that follows
                waiting = (r, c)
            elif rec[6] == 1:
                put(rows, r, c, bool(rec[8]))
    return sheets


def read_xls(data: bytes, source: str, *, max_rows: int = 0, header=None) -> list[Table]:
    """Every sheet with rows of an Excel 97 to 2003 workbook, the way `draft.read_xlsx` gives them: the last result of a
    formula, dates as dates, a workbook of one sheet named after the file."""
    z = _compound(data, source)
    path = z.find("Workbook")
    records = _biff(z.read(path)) if path else iter(())
    first = next(records, None)
    if first is None or first[1] != 0x0809 or first[2][:2] != b"\x00\x06":  # Excel 95 and before
        raise _export(source)
    book = _xls_book(records, source)
    sheets = _xls_cells(records, book, source)
    out, spread = [], 0
    for at, name in book.names.items():
        found = sheets.get(at, {})
        spread += sum(max(row) + 1 for row in found.values())
        if spread > _XLS_CELLS:
            raise _xls_too_large(source)
        raw = [[row.get(c) for c in range(max(row) + 1)] for _, row in sorted(found.items())]
        try:
            out.append(_table(Path(source).stem if len(book.names) == 1 else name, f"{source} · {name}", raw, max_rows,
                              header))
        except ReadError:
            continue
    if not out:
        raise ReadError(f"{source}: no sheet has rows", "empty")
    return out


def _xls(data: bytes, source: str) -> Definitions:
    try:
        sheets = read_xls(data, source, header=header_row)
    except ReadError as e:
        raise IngestError(str(e), READ_REASON.get(e.reason, "format")) from None
    out = from_sheets(sheets, source)
    return _sheets_as_text(sheets, source) if out is None else out


def _office(data: bytes, source: str) -> Definitions:
    """An older binary Office file, known by the streams it holds, since its name may be wrong and a web page or a newer
    file is often saved under the old name."""
    if data[:4] != OLE:
        return _sniff(data, source)(data, source)
    z = _compound(data, source)
    if z.find("EncryptedPackage"):  # a newer file with a password is a compound file too
        raise _locked(source)
    word, deck = z.find("WordDocument"), z.find("PowerPoint Document")
    if word:
        return _doc(z, word, source)
    if deck:
        return _ppt(z, deck, source)
    if z.find("Workbook"):
        return _xls(data, source)
    if "FileHeader" in z.paths:
        return _hwp(data, source)
    raise _export(source)


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
        raise IngestError("reading .pdf needs pypdf (pip install 'xgen-space[pdf]')", "needs_extra") from None
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
        sheets = read_file(data, name, header=header_row)
    except ReadError as e:
        raise IngestError(str(e), READ_REASON.get(e.reason, "format")) from None
    out = from_sheets(sheets, source)
    if out is None and Path(name).suffix.lower() == ".csv":
        raise IngestError(f"{source}: no table, code, term or message sheet found", "format")
    return _sheets_as_text(sheets, source) if out is None else out


def _sheets_as_text(sheets: list[Table], source: str) -> Definitions:
    """A project document of some other kind still comes in, as text a person or a model can read."""
    text = "\n".join(" | ".join(str(c) for c in [*s.columns] if c) + "\n" + "\n".join(
        " | ".join(str(c) for c in r if c) for r in s.rows) for s in sheets)
    return Definitions(sources=[source], documents=[{"name": Path(source).stem, "kind": "other", "text": text,
                                                     "sections": []}])


def _sqlite(data: bytes, source: str) -> Definitions:
    """The tables, keys and references of a SQLite file, opened read-only from a temporary copy."""
    import sqlite3
    import tempfile

    from xgen_space.backends.sql import SqliteBackend
    from xgen_space.draft import _catalog, _wide_keys

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "upload.db"
        path.write_bytes(data)
        conn = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)
        try:
            conn.execute("PRAGMA trusted_schema = OFF")  # a file's triggers and views run nothing here
            b = SqliteBackend(conn=conn)
            out = Definitions(sources=[source])
            for name, cols, pk, fks in _catalog(b):
                refs = [{"columns": [c], "table": t, "ref_columns": [r] if r else []} for c, t, r in fks]
                refs += [{"columns": c, "table": t, "ref_columns": r} for c, t, r in _wide_keys(b, name)]
                out.tables[name] = TableDef(name, columns=[ColumnDef(c, type=ty, pk=c in pk) for c, ty in cols],
                                            primary_key=list(pk), references=refs)
        finally:
            conn.close()
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
    return {"columns": cols, "table": parts[-1], "schema": parts[-2] if len(parts) > 1 else "", "ref_columns": ref}


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


def _table_head(st: list[_Tok]) -> tuple[list[str], int] | None:
    """The dotted name of a CREATE TABLE and where its columns open."""
    i = 1
    while _kw(_at(st, i)) in _TABLE_WORDS:
        i += 1
    if _kw(st[0]) != "CREATE" or _kw(_at(st, i)) != "TABLE":
        return None
    i += 1
    if [_kw(_at(st, i + k)) for k in range(3)] == ["IF", "NOT", "EXISTS"]:
        i += 3
    parts, i = _dotted(st, i)
    if not parts or _at(st, i).kind != "(":
        return None  # AS SELECT, LIKE another table, PARTITION OF: nothing of its own to read
    return parts, i


def _schemas(statements: list[list[_Tok]]) -> dict[str, set[str]]:
    """The schemas each table name is created in, in lower case."""
    out: dict[str, set[str]] = {}
    for st in statements:
        head = _table_head(st)
        if head:
            parts = head[0]
            out.setdefault(parts[-1].lower(), set()).add(parts[-2].lower() if len(parts) > 1 else "")
    return out


def _table_name(parts: list[str], schemas: dict[str, set[str]], home: str = "") -> str:
    """A table's name in the definitions. Its schema stays in the name only where two schemas hold the same name, so
    neither table is lost. A name given without a schema means the one in `home`, the schema of the table saying it."""
    name = parts[-1]
    held = schemas.get(name.lower(), set())
    schema = parts[-2] if len(parts) > 1 and parts[-2] else home
    return f"{schema}.{name}" if len(held) > 1 and schema.lower() in held - {""} else name


def _settle(t: TableDef, parts: list[str], schemas: dict[str, set[str]]) -> None:
    """References read so far name their table as `_table_name` does, from where the table holding them lies."""
    home = parts[-2] if len(parts) > 1 else ""
    for r in t.references:
        if "schema" in r:
            r["table"] = _table_name([r.pop("schema"), r["table"]], schemas, home)


def _create_table(st: list[_Tok], defs: Definitions, schemas: dict[str, set[str]]) -> None:
    head = _table_head(st)
    if head is None:
        return
    parts, i = head
    end = _group(st, i)
    t = TableDef(_table_name(parts, schemas))
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
    _settle(t, parts, schemas)
    defs.tables[t.name] = t


def _create_type(st: list[_Tok], defs: Definitions) -> None:
    """PostgreSQL's named enum: CREATE TYPE mood AS ENUM ('a', 'b')."""
    parts, i = _dotted(st, 2)
    if parts and _kw(_at(st, i)) == "AS" and _kw(_at(st, i + 1)) == "ENUM":
        values = [{"code": x.value, "name": "", "use": True} for x in st[i + 2:] if x.kind == "str"]
        defs.codes[parts[-1]] = CodeGroup(parts[-1], "", values)


def _alter(st: list[_Tok], defs: Definitions, schemas: dict[str, set[str]]) -> None:
    if _kw(_at(st, 1)) != "TABLE":
        return
    i = 2
    while _kw(_at(st, i)) in ("ONLY", "IF", "EXISTS"):
        i += 1
    parts, i = _dotted(st, i)
    t = defs.table(_table_name(parts, schemas)) if parts else None
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
    _settle(t, parts, schemas)


def _comment_on(st: list[_Tok], defs: Definitions, schemas: dict[str, set[str]]) -> None:
    kind = _kw(_at(st, 2))
    parts, i = _dotted(st, 3)
    text = _at(st, i + 1)
    if _kw(_at(st, i)) != "IS" or text.kind != "str" or not parts:
        return
    if kind == "TABLE":
        t = defs.table(_table_name(parts, schemas))
        if t is not None:
            _describe(t, text.value)
    elif kind == "COLUMN" and len(parts) > 1:
        t = defs.table(_table_name(parts[:-1], schemas))
        c = t.column(parts[-1]) if t is not None else None
        if c is not None:
            _describe(c, text.value)


def _extended_property(st: list[_Tok], defs: Definitions, schemas: dict[str, set[str]]) -> None:
    """SQL Server keeps its comments as MS_Description properties: name, value, then type and name of each level."""
    v = [x.value for x in st if x.kind == "str"]
    if len(v) < 2 or v[0] != "MS_Description":
        return
    levels = {v[k].upper(): v[k + 1] for k in range(2, len(v) - 1, 2)}
    t = defs.table(_table_name([levels.get("SCHEMA", ""), levels.get("TABLE", "")], schemas))
    if t is None:
        return
    c = t.column(levels["COLUMN"]) if "COLUMN" in levels else None
    if "COLUMN" not in levels:
        _describe(t, v[1])
    elif c is not None:
        _describe(c, v[1])


def _sql(data: bytes, source: str) -> Definitions:
    defs = Definitions(sources=[source])
    statements = list(_statements(_sql_tokens(_text(data, source))))
    schemas = _schemas(statements)
    for st in statements:
        head = _kw(st[0])
        if head == "CREATE" and _kw(_at(st, 1)) == "TYPE":
            _create_type(st, defs)
        elif head == "CREATE":
            _create_table(st, defs, schemas)
        elif head == "ALTER":
            _alter(st, defs, schemas)
        elif head == "COMMENT" and _kw(_at(st, 1)) == "ON":
            _comment_on(st, defs, schemas)
        elif head in ("EXEC", "EXECUTE") and any(_kw(x) == "SP_ADDEXTENDEDPROPERTY" for x in st):
            _extended_property(st, defs, schemas)
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
register(".hwp", _hwp)
register([".doc", ".ppt", ".xls"], _office)
register([".html", ".htm"], _html)
register([".md", ".markdown"], _md)
register(".txt", _txt)
register(".pdf", _pdf)
register(SHEETS, _sheets)
register(".json", _json)
register([".db", ".sqlite", ".sqlite3"], _sqlite)
