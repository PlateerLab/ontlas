"""The space itself: documents, their vectors and their ontology, beside the domain ontology and tied to it.

A document that comes in is cut into chunks, embedded, and written to every vector store the space has. The same document
becomes rows of a document ontology (document, section, concept) that runs on the engine the domain ontology runs on, so
SPARQL, Cypher or SQL reach it the same way. Concepts are what ties the two: a section that says 주문상품 mentions the
object OrderItem, so a search can land on a document and go on to the definition, and a definition can show its documents.

Nothing here depends on a store, a model or a domain: those arrive as adapters.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from xgen_space.embed import Embedder, EmbedError, open_embedder, shared_wording
from xgen_space.relations import Busy, Relation
from xgen_space.vectors import MemoryStore, Point, VectorError, VectorStore, open_vector_store

CHUNK = 520  # characters: a paragraph or two, what a person reads as one passage
OVERLAP = 60
KEYWORDS_PER_DOCUMENT = 14
RELATED_PER_CONCEPT = 4
GRAPH_SECTIONS_MAX = 240  # past this the document graph shows documents and concepts and leaves sections out
_WORD = re.compile(r"[가-힣]{2,}|[A-Za-z][A-Za-z0-9-]{2,}")
_SENTENCE = re.compile(r"(?<=[.!?。])\s+|\n+")
_JOSA = ("으로써", "으로서", "에서는", "에서도", "에게서", "까지는", "부터는", "이라고", "으로는", "이라는", "에서", "에게", "까지", "부터",
         "보다", "처럼", "만큼", "라고", "으로", "이나", "이며", "에는", "에도", "하고", "와", "과", "은", "는", "이", "가", "을", "를",
         "의", "에", "로", "도", "만", "나")
_ENDINGS = ("합니다", "습니다", "됩니다", "입니다", "있습니다", "없습니다", "하는", "되는", "하여", "되어", "하며", "해야", "한다", "된다", "한",
            "할", "된", "될")
_STOP = {"경우", "대한", "관한", "위한", "따라", "다음", "해당", "이상", "이내", "이하", "미만", "각호", "사항", "내용", "기준", "가능", "모든", "또는",
         "그리고", "있는", "없는", "있다", "없다", "같은", "등의", "다시", "돌려", "보내", "받은", "받습", "the", "and", "for", "with", "that", "this", "from"}
SAMPLE = 6  # passages a change of model is timed on
KIND_WORD = {"object": "객체", "property": "속성", "value": "허용값", "decision": "결정", "action": "Action", "term": "용어",
             "keyword": "키워드"}


@dataclass
class Chunk:
    id: str
    document: str
    section: str
    ordinal: int
    text: str


def _id(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:20]


def _pieces(text: str, size: int, overlap: int) -> list[str]:
    """Whole sentences up to a size; a sentence longer than that is cut, and the next piece repeats the tail of the last."""
    out, cur = [], ""
    for s in (x.strip() for x in _SENTENCE.split(text)):
        if not s:
            continue
        while len(s) > size:
            if cur:
                out.append(cur)
                cur = ""
            out.append(s[:size])
            s = s[size - overlap:]
        if cur and len(cur) + len(s) + 1 > size:
            out.append(cur)
            cur = cur[-overlap:] + " " + s if overlap else s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def split(document: dict, *, size: int = CHUNK, overlap: int = OVERLAP) -> list[Chunk]:
    """A document's passages, in order, each knowing its section."""
    sections = [s for s in document.get("sections") or [] if (s.get("text") or "").strip()]
    if not sections and (document.get("text") or "").strip():
        sections = [{"title": document.get("name", ""), "text": document["text"]}]
    out, name = [], document.get("name", "")
    for s in sections:
        title = s.get("title") or name
        for piece in _pieces(s["text"], size, overlap):
            out.append(Chunk(_id(name, title, len(out), piece), name, title, len(out), piece))
    return out


def _verb(word: str) -> bool:
    return word.endswith(("습니다", "합니다", "입니다", "됩니다", "니다", "세요", "해요", "었다", "였다", "한다", "된다", "하면", "되면", "으면", "해서"))


def _stem(word: str) -> str:
    for tail in _ENDINGS + _JOSA:
        if len(word) > len(tail) + 1 and word.endswith(tail):
            return word[:-len(tail)]
    return word


@dataclass
class Concept:
    id: str
    label: str
    kind: str
    element: str = ""


def dictionary(onto, terms: list[dict] | None = None) -> dict[str, Concept]:
    """Every name the definitions give, longest first. A word people use for a thing is how a document finds that thing."""
    out: dict[str, Concept] = {}

    def add(label: str, kind: str, element: str = "") -> None:
        label = str(label or "").strip()
        if len(label) >= 2 and label not in out and label.lower() not in _STOP:
            out[label] = Concept(_id(kind, label), label, kind, element)

    if onto is not None:
        for o in onto.objects.values():
            add(o.label or o.name, "object", f"object:{o.name}")
        for d in onto.decisions.values():
            add(d.label, "decision", f"decision:{d.name}")
        for a in onto.actions.values():
            add(a.label, "action", f"action:{a.name}")
        for o in onto.objects.values():
            for p in o.properties.values():
                add(p.label, "property", f"property:{o.name}.{p.name}")
                for label in (p.labels or {}).values():
                    add(label, "value", f"property:{o.name}.{p.name}")
    for t in terms or []:
        add(t.get("term"), "term")
        for s in t.get("synonyms") or []:
            add(s, "term")
    return dict(sorted(out.items(), key=lambda kv: -len(kv[0])))


def _find(text: str, names: dict[str, Concept]) -> Counter:
    """Longest name first, each stretch of text counted once: 주문상품 is not also 주문."""
    found: Counter = Counter()
    rest = text
    for label, c in names.items():
        n = rest.count(label)
        if n:
            found[c.id] += n
            rest = rest.replace(label, " " * len(label))
    return found


def keywords(chunks: list[Chunk], known: dict[str, Concept], limit: int = KEYWORDS_PER_DOCUMENT) -> list[str]:
    """What a document keeps coming back to, by how many of its sections say it. No model: the same text gives the same words."""
    spread: Counter = Counter()
    total: Counter = Counter()
    for sec in {c.section for c in chunks}:
        words = [_stem(w) for c in chunks if c.section == sec for w in _WORD.findall(c.text) if not _verb(w)]
        words = [w for w in words if len(w) >= 2 and w.lower() not in _STOP and not w.isdigit() and w not in known
                 and w not in _ENDINGS and w not in _JOSA]  # an ending on its own (하는, 되는) names nothing
        total.update(words)
        spread.update(set(words))
    ranked = sorted(total, key=lambda w: (-spread[w], -total[w], w))
    return [w for w in ranked if total[w] >= 2][:limit]


DOCUMENT_MODULE = {
    "module": "documents", "version": "1.0.0", "kind": "domain", "label": "문서 온톨로지",
    "namespace": "https://example.org/space/documents#",
    "description": "공간에 등록된 문서의 구조와 문서가 언급하는 개념으로 자동 생성한 온톨로지입니다",
    "objects": {
        "Document": {"label": "문서", "key": "doc_id", "title": "title", "table": "documents", "properties": {
            "doc_id": {"type": "string", "label": "문서 번호", "required": True}, "title": {"type": "string", "label": "제목"},
            "kind": {"type": "string", "label": "유형"}, "sections": {"type": "integer", "label": "절 수"},
            "chars": {"type": "integer", "label": "글자 수"}}},
        "Section": {"label": "절", "key": "section_id", "title": "title", "table": "sections", "properties": {
            "section_id": {"type": "string", "label": "절 번호", "required": True}, "doc_id": {"type": "string", "label": "문서 번호"},
            "ordinal": {"type": "integer", "label": "순서"}, "title": {"type": "string", "label": "제목"},
            "excerpt": {"type": "string", "label": "발췌"}}},
        "Concept": {"label": "개념", "key": "concept_id", "title": "label", "table": "concepts", "properties": {
            "concept_id": {"type": "string", "label": "개념 번호", "required": True}, "label": {"type": "string", "label": "이름"},
            "kind": {"type": "string", "label": "종류"}, "element": {"type": "string", "label": "온톨로지 요소"}}},
        "Relation": {"label": "관계", "key": "relation_id", "title": "label", "table": "relations", "properties": {
            "relation_id": {"type": "string", "label": "관계 번호", "required": True},
            "source_id": {"type": "string", "label": "주어 개념"}, "target_id": {"type": "string", "label": "목적어 개념"},
            "predicate": {"type": "string", "label": "관계 이름"}, "label": {"type": "string", "label": "표시 이름"},
            "section_id": {"type": "string", "label": "근거 절"}, "evidence": {"type": "string", "label": "근거 문장"}}},
    },
    "links": {
        "hasSection": {"from": "Document", "to": "Section", "cardinality": "one_to_many", "inverse": "sectionOf", "label": "절",
                       "on": {"doc_id": "doc_id"}},
        "mentions": {"from": "Section", "to": "Concept", "inverse": "mentionedIn", "label": "언급",
                     "via": {"table": "section_concepts", "source": "section_id", "target": "concept_id"}},
        "relatedTo": {"from": "Concept", "to": "Concept", "label": "함께 언급",
                      "via": {"table": "concept_links", "source": "source_id", "target": "target_id"}},
        "relationFrom": {"from": "Relation", "to": "Concept", "cardinality": "many_to_one", "label": "주어",
                         "on": {"source_id": "concept_id"}},
        "relationTo": {"from": "Relation", "to": "Concept", "cardinality": "many_to_one", "label": "목적어",
                       "on": {"target_id": "concept_id"}},
        "statedIn": {"from": "Relation", "to": "Section", "cardinality": "many_to_one", "label": "근거 절",
                     "on": {"section_id": "section_id"}},
    },
    "queries": {
        "allDocuments": {"label": "문서 목록", "query": {"match": {"d": "Document"}, "return": ["d.title", "d.kind", "d.sections", "d.chars"],
                                                     "order": ["title"]}},
        "sectionsAbout": {"label": "개념을 언급한 절", "params": {"concept": "string"}, "example": {"concept": "주문"}, "query": {
            "match": {"d": "Document", "s": "Section", "c": "Concept"}, "edges": [["d", "hasSection", "s"], ["s", "mentions", "c"]],
            "where": {"eq": ["c.label", {"param": "concept"}]},
            "return": [{"col": "d.title", "as": "document"}, {"col": "s.title", "as": "section"}], "order": ["document", "section"]}},
        "conceptsByMentions": {"label": "많이 언급된 개념", "query": {
            "match": {"s": "Section", "c": "Concept"}, "edges": [["s", "mentions", "c"]],
            "return": [{"col": "c.label", "as": "concept"}, {"col": "c.kind", "as": "kind"}, {"count": "s", "as": "sections"}],
            "order": ["-sections", "concept"]}},
        "relationsOf": {"label": "개념의 관계", "params": {"concept": "string"}, "example": {"concept": "반품"}, "query": {
            "match": {"r": "Relation", "a": "Concept", "b": "Concept", "s": "Section", "d": "Document"},
            "edges": [["r", "relationFrom", "a"], ["r", "relationTo", "b"], ["r", "statedIn", "s"], ["d", "hasSection", "s"]],
            "where": {"or": [{"eq": ["a.label", {"param": "concept"}]}, {"eq": ["b.label", {"param": "concept"}]}]},
            "return": [{"col": "a.label", "as": "subject"}, {"col": "r.label", "as": "relation"}, {"col": "r.predicate", "as": "name"},
                       {"col": "b.label", "as": "object"}, {"col": "d.title", "as": "document"}, {"col": "s.title", "as": "section"}],
            "order": ["subject", "name", "object"]}},
        "relationNames": {"label": "관계 이름별 수", "query": {
            "match": {"r": "Relation"}, "return": [{"col": "r.predicate", "as": "name"}, {"count": "r", "as": "relations"}],
            "order": ["-relations", "name"]}},
    },
}


def signature(embedder: Embedder) -> str:
    """Which model made a vector: vectors of two models do not compare."""
    d = embedder.describe()
    return f"{d['kind']}:{d['name']}:{d['dim']}"


def folder_of(document: dict) -> str:
    path = str(document.get("path") or "")
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _under(folder: str, scope: str) -> bool:
    return not scope or folder == scope or folder.startswith(scope + "/")


WIDER = 4  # a model's nearest passage is not always the one that says it, so a search looks at more than it returns
WORDING = 0.3  # the share of the question's own words in the order; the model keeps the rest


class Space:
    """Documents, one embedder and any number of vector stores. Every store holds the same chunks, so one can replace another
    and a question can be asked of all of them at once."""

    def __init__(self, embedder: Embedder | None = None, stores: dict[str, VectorStore] | None = None, *, collection: str = "documents",
                 checks: list[dict] | None = None):
        self.embedder = embedder or open_embedder({"kind": "hash"})
        self.stores: dict[str, VectorStore] = stores or {"memory": MemoryStore()}
        self.collection = collection
        self.checks = list(checks or [])
        self.fixed: dict[str, dict] = {}  # documents a space is configured with, by name
        self.uploaded: dict[str, dict] = {}  # documents from the catalog, by name
        self.passages: dict[str, Chunk] = {}  # every passage of every document: what the document ontology reads
        self.chunks: dict[str, Chunk] = {}  # the passages the stores hold: those of documents whose embedding is on
        self.model = ""  # the embedder the stores' vectors were made by
        self.embed_error = ""  # why the last passages could not be embedded; they are asked again on the next round
        self.errors: dict[str, str] = {}  # store -> why it is behind the others
        self.indexed_at = 0.0
        self.took = 0
        self.lock = threading.RLock()
        self._made: dict[str, Any] = {}
        self.retriever = ""  # the port a question goes through; with nothing said, the best one installed
        self._knowledge: tuple | None = None
        self.relations: dict[str, list[Relation]] = {}  # passage -> what a reader found there
        self.read_by: dict[str, str] = {}  # passage -> the reader that went through it
        self.vocabulary: dict[str, str] = {}  # relation name -> what it means, so later readings use the same names
        self.relations_version = 0

    # ---- documents ---------------------------------------------------------------------------------------------

    def documents(self) -> dict[str, dict]:
        return {**self.fixed, **self.uploaded}

    def add(self, document: dict, *, fixed: bool = False) -> None:
        (self.fixed if fixed else self.uploaded)[document["name"]] = document

    def set_uploaded(self, documents: list[dict]) -> None:
        """The catalog says what is in the space now: each document with its file's path and whether it is embedded."""
        self.uploaded = {d["name"]: d for d in documents}

    def index(self) -> dict:
        """Bring every store in line with the documents: only what changed, or what another model embedded, is embedded
        and written. A document whose embedding is off stays in the document ontology and leaves the stores."""
        with self.lock:
            started = time.perf_counter()
            docs = self.documents()
            every = {c.id: c for d in docs.values() for c in split(d)}
            if every.keys() != self.passages.keys():
                self.passages = every
                self._made.clear()
            wanted = {i: c for i, c in every.items() if docs[c.document].get("embed", True) is not False}
            sig = signature(self.embedder)
            new = [c for i, c in wanted.items() if sig != self.model or i not in self.chunks]
            gone = [i for i in self.chunks if i not in wanted]
            behind = [n for n in self.stores if n in self.errors]
            if new or gone or behind:
                try:
                    self._write(new, gone, wanted, behind, docs, sig)
                except EmbedError as e:  # the stores were not touched: what they held is still searched
                    self.embed_error = str(e)
                    return {"added": 0, "removed": 0, "chunks": len(self.chunks), "errors": dict(self.errors),
                            "embed_error": self.embed_error}
                self.embed_error = ""
                self.chunks, self.model = wanted, sig
                self.indexed_at = time.time()
                self.took = round((time.perf_counter() - started) * 1000)
            return {"added": len(new), "removed": len(gone), "chunks": len(wanted), "errors": dict(self.errors)}

    def _point(self, c: Chunk, vector: list[float], docs: dict[str, dict], sig: str) -> Point:
        return Point(c.id, vector, {"document": c.document, "section": c.section, "ordinal": c.ordinal, "text": c.text,
                                    "folder": folder_of(docs.get(c.document, {})), "embedder": sig})

    def _write(self, new: list[Chunk], gone: list[str], wanted: dict[str, Chunk], behind: list[str], docs: dict[str, dict],
               sig: str) -> None:
        """Every vector is made before any store is written, so a model that fails leaves the stores as they were."""
        points = [self._point(c, v, docs, sig) for c, v in zip(new, self.embedder.embed([c.text for c in new]))] if new else []
        full: list[Point] = []
        if behind:  # a store that missed a round gets everything again
            made = {p.id: p for p in points}
            rest = [c for i, c in wanted.items() if i not in made]
            full = list(made.values()) + ([self._point(c, v, docs, sig) for c, v in zip(rest, self.embedder.embed([c.text for c in rest]))]
                                          if rest else [])
        for name, store in self.stores.items():
            try:
                if name in behind:
                    store.drop(self.collection)
                    batch = full
                else:
                    batch = points
                if batch:
                    store.ensure(self.collection, len(batch[0].vector))
                    store.upsert(self.collection, batch)
                if gone and name not in behind:
                    store.delete(self.collection, gone)
                self.errors.pop(name, None)
            except (VectorError, OSError) as e:
                self.errors[name] = str(e)

    def add_store(self, name: str, spec: dict) -> dict:
        """A store joins at any time and is filled with what the space holds."""
        with self.lock:
            store = open_vector_store({**spec, "name": name})
            self.stores[name] = store
            self.errors[name] = "색인 전"
            return self.index()

    def remove_store(self, name: str) -> None:
        with self.lock:
            if len(self.stores) <= 1:
                raise ValueError("벡터 저장소가 하나뿐이라 제거하지 못했습니다.")
            self.stores.pop(name, None)
            self.errors.pop(name, None)

    # ---- the model: which one made the vectors, and what another one would embed again --------------------------

    def reembed_plan(self, embedder: Embedder) -> dict:
        """What a change of model embeds again, before anything changes: every passage of every embedded document, since
        a question the new model embeds compares with none of the old vectors. The time is the new model's, on a few passages."""
        self.index()
        docs = self.documents()
        held = [c for c in self.passages.values() if docs[c.document].get("embed", True) is not False]
        rows: dict[str, dict] = {}
        for c in held:
            r = rows.setdefault(c.document, {"document": c.document, "path": str(docs[c.document].get("path") or ""), "chunks": 0,
                                             "chars": 0})
            r["chunks"] += 1
            r["chars"] += len(c.text)
        sample = [c.text for c in held[:SAMPLE]]
        started = time.perf_counter()
        if sample:
            embedder.embed(sample)
        per_char = (time.perf_counter() - started) / max(1, sum(len(x) for x in sample))
        chars = sum(r["chars"] for r in rows.values())
        return {"from": self.embedder.describe(), "to": embedder.describe(), "same": signature(embedder) == self.model,
                "files": sorted(rows.values(), key=lambda r: (-r["chunks"], r["document"])), "chunks": len(held), "chars": chars,
                "seconds": round(per_char * chars, 1)}

    def use_embedder(self, embedder: Embedder) -> dict:
        """Another model for the whole space. The stores let go of the old vectors and every passage is embedded again."""
        with self.lock:
            if signature(embedder) == self.model:
                self.embedder = embedder
                return self.index()
            for name, store in self.stores.items():
                try:
                    store.drop(self.collection)
                except (VectorError, OSError) as e:
                    self.errors[name] = str(e)
            self.embedder, self.chunks, self.model = embedder, {}, ""
            return self.index()

    def document_rows(self) -> list[dict]:
        """Each document with its file, whether it is embedded, and how many of its passages the stores hold."""
        held = Counter(c.document for c in self.chunks.values())
        every = Counter(c.document for c in self.passages.values())
        current = self.model == signature(self.embedder)
        out = []
        for name, d in self.documents().items():
            on = d.get("embed", True) is not False
            if not on:
                state = "off"
            elif not every[name]:
                state = "none"
            elif current and held[name] == every[name]:
                state = "embedded"
            else:
                state = "failed" if self.embed_error else "pending"
            out.append({"name": name, "path": str(d.get("path") or ""), "folder": folder_of(d), "embed": on, "passages": every[name],
                        "indexed": held[name], "state": state})
        return out

    def folders(self) -> list[str]:
        """The folders documents came from, each with the folders above it."""
        out = set()
        for d in self.documents().values():
            f = folder_of(d)
            while f:
                out.add(f)
                f = f.rsplit("/", 1)[0] if "/" in f else ""
        return sorted(out)

    def in_folder(self, name: str, scope: str) -> bool:
        d = self.documents().get(name)
        return d is not None and _under(folder_of(d), scope)

    def path_of(self, name: str) -> str:
        return str((self.documents().get(name) or {}).get("path") or "")

    # ---- search ------------------------------------------------------------------------------------------------

    def primary(self) -> str:
        return next((n for n in self.stores if n not in self.errors), next(iter(self.stores)))

    def search(self, text: str, k: int = 5, *, store: str = "", where: dict | None = None, folder: str = "") -> list[dict]:
        """The passages nearest a question; with a folder, only those of documents in it or in a folder under it."""
        self.index()
        name = store or self.primary()
        if name not in self.stores:
            raise LookupError(f"벡터 저장소 {name}")
        if folder:
            inside = sorted({folder_of(d) for d in self.documents().values() if _under(folder_of(d), folder)})
            if not inside:
                return []
            where = {**(where or {}), "folder": inside}
        vector = self.embedder.embed([text])[0]
        semantic = self.embedder.semantic  # a wording embedder has counted the words already
        found = self.stores[name].search(self.collection, vector, max(k * WIDER, k) if semantic else k, where)
        hits = [{"id": h.id, "score": round(h.score, 4), "document": h.payload.get("document", ""), "section": h.payload.get("section", ""),
                 "text": h.payload.get("text", ""), "folder": h.payload.get("folder", ""), "store": name} for h in found]
        if semantic:
            for h in hits:
                h["score"] = round((1 - WORDING) * h["score"] + WORDING * shared_wording(text, h["text"]), 4)
            hits.sort(key=lambda h: -h["score"])  # stable: a tie stays in the store's order
        return hits[:k]

    def compare(self, text: str, k: int = 5) -> dict:
        """The same question to every store, each with its own answer and how long it took."""
        self.index()
        vector = self.embedder.embed([text])[0]
        out = {}
        for name, store in self.stores.items():
            started = time.perf_counter()
            try:
                hits = store.search(self.collection, vector, k)
                out[name] = {"kind": store.kind, "ids": [h.id for h in hits], "scores": [round(h.score, 3) for h in hits],
                             "ms": round((time.perf_counter() - started) * 1000, 1)}
            except (VectorError, OSError) as e:
                out[name] = {"kind": store.kind, "ids": [], "error": str(e)}
        ranks = [tuple(v["scores"]) for v in out.values() if not v.get("error")]  # two points with one score may swap places
        return {"stores": out, "same": len(set(ranks)) <= 1}

    def check(self, k: int = 5) -> dict | None:
        """Questions with the document that should come back, for the flow's pass condition."""
        if not self.checks:
            return None
        results = []
        for c in self.checks:
            hits = self.search(str(c.get("text", "")), k)
            want = str(c.get("document", ""))
            at = next((i + 1 for i, h in enumerate(hits) if h["document"] == want), 0)
            results.append({"text": c.get("text", ""), "document": want, "rank": at})
        found = sum(1 for r in results if r["rank"])
        return {"questions": len(results), "found": found, "share": found / len(results), "results": results, "k": k}

    # ---- the document ontology ---------------------------------------------------------------------------------

    def concepts(self, onto=None, terms: list[dict] | None = None) -> dict:
        """Who mentions what, over every passage whether embedded or not. Cached until the documents or the names change."""
        self.index()
        names = dictionary(onto, terms)
        key = _id("concepts", *sorted(self.passages), *sorted(names))
        if key in self._made:
            return self._made[key]
        by_doc: dict[str, list[Chunk]] = {}
        for c in self.passages.values():
            by_doc.setdefault(c.document, []).append(c)
        words = dict(names)
        for chunks in by_doc.values():
            for w in keywords(chunks, names):
                words.setdefault(w, Concept(_id("keyword", w), w, "keyword"))
        ordered = dict(sorted(words.items(), key=lambda kv: -len(kv[0])))
        section_of: dict[tuple[str, str], Counter] = {}
        per_chunk: dict[str, Counter] = {}
        for c in self.passages.values():
            per_chunk[c.id] = _find(c.text, ordered)
            section_of.setdefault((c.document, c.section), Counter()).update(per_chunk[c.id])
        by_id = {c.id: c for c in ordered.values()}
        used = {i for found in section_of.values() for i in found}
        pairs: Counter = Counter()
        for found in section_of.values():
            ids = sorted(found)
            pairs.update((a, b) for i, a in enumerate(ids) for b in ids[i + 1:])
        degree: Counter = Counter()
        links = []
        for (a, b), n in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):
            if n >= 2 and degree[a] < RELATED_PER_CONCEPT and degree[b] < RELATED_PER_CONCEPT:
                links.append((a, b, n))
                degree[a] += 1
                degree[b] += 1
        out = {"concepts": {i: by_id[i] for i in used}, "sections": section_of, "links": links, "chunks": by_doc,
               "per_chunk": per_chunk}
        self._made[key] = out
        return out

    def _rows(self, onto, terms, folder: str = "") -> dict[str, list[tuple]]:
        made = self.concepts(onto, terms)
        docs, secs, mentions = [], [], []
        for name, doc in self.documents().items():
            if folder and not _under(folder_of(doc), folder):
                continue
            parts = made["chunks"].get(name, [])
            titles = list(dict.fromkeys(c.section for c in parts))
            did = _id("doc", name)
            docs.append((did, name, doc.get("kind", ""), len(titles), sum(len(c.text) for c in parts)))
            for i, title in enumerate(titles):
                sid = _id("sec", name, title)
                first = next(c for c in parts if c.section == title)
                secs.append((sid, did, i + 1, title, first.text[:160]))
                mentions += [(sid, cid) for cid in made["sections"].get((name, title), {})]
        seen = {cid for _, cid in mentions}
        concepts = [(c.id, c.label, c.kind, c.element) for c in made["concepts"].values() if c.id in seen]
        by_label = {c.label: c.id for c in made["concepts"].values() if c.id in seen}
        relations, said = [], set()
        for r in self.live_relations(folder):
            a, b = by_label.get(r.source), by_label.get(r.target)
            if a and b:  # a concept the names no longer give is no end of a relation
                relations.append((_id("rel", r.chunk, r.source, r.predicate, r.target), a, b, r.predicate, r.label or r.predicate,
                                  _id("sec", r.document, r.section), r.evidence))
                said |= {(a, b), (b, a)}
        co = [(a, b) for a, b, _ in made["links"] if a in seen and b in seen and (a, b) not in said]  # a named relation says more
        return {"documents": docs, "sections": secs, "concepts": concepts, "section_concepts": mentions, "concept_links": co,
                "relations": list({r[0]: r for r in relations}.values())}

    def studio(self, onto=None, terms: list[dict] | None = None):
        """The document ontology as a studio of its own: the compilers, the graph stores and the checks all apply."""
        from xgen_space.backends.sql import SqliteBackend
        from xgen_space.modules import Module
        from xgen_space.studio import Studio

        rows = self._rows(onto, terms)
        key = _id("studio", *[len(v) for v in rows.values()], *sorted(self.passages), self.relations_version)
        if key in self._made:
            return self._made[key]
        st = Studio.from_modules([Module.from_dict(DOCUMENT_MODULE)], name="documents")
        src = SqliteBackend()
        src.script("""CREATE TABLE documents (doc_id TEXT PRIMARY KEY, title TEXT, kind TEXT, sections INTEGER, chars INTEGER);
CREATE TABLE sections (section_id TEXT PRIMARY KEY, doc_id TEXT, ordinal INTEGER, title TEXT, excerpt TEXT);
CREATE TABLE concepts (concept_id TEXT PRIMARY KEY, label TEXT, kind TEXT, element TEXT);
CREATE TABLE section_concepts (section_id TEXT, concept_id TEXT);
CREATE TABLE concept_links (source_id TEXT, target_id TEXT);
CREATE TABLE relations (relation_id TEXT PRIMARY KEY, source_id TEXT, target_id TEXT, predicate TEXT, label TEXT, section_id TEXT,
                        evidence TEXT);""")
        for table, values in rows.items():
            if values:
                marks = ", ".join("?" * len(values[0]))
                src.conn.executemany(f"INSERT INTO {table} VALUES ({marks})", values)
        src.conn.commit()
        st.add_backend("source", src, source=True)
        try:
            from xgen_space.backends.rdf import RdflibBackend

            st.add_backend("graph", RdflibBackend())
            st.project()
        except ImportError:  # the graph side is an extra; the SQL side still answers
            pass
        self._made[key] = st
        return st

    # ---- relations a model reads between the concepts a passage names -------------------------------------------

    def live_relations(self, folder: str = "") -> list[Relation]:
        """The relations of passages still in the space: a passage that changed is a new passage, read again."""
        self.index()
        docs = self.documents()
        return [r for cid, rows in self.relations.items() if cid in self.passages for r in rows
                if not folder or _under(folder_of(docs.get(r.document, {})), folder)]

    def to_read(self, folder: str = "") -> list[Chunk]:
        """Passages no reader has gone through yet, in document order."""
        self.index()
        docs = self.documents()
        return [c for c in sorted(self.passages.values(), key=lambda c: (c.document, c.ordinal))
                if c.id not in self.read_by and (not folder or _under(folder_of(docs.get(c.document, {})), folder))]

    def reading(self, folder: str = "") -> dict:
        """How far the reading of a folder (or of everything) has come."""
        self.index()
        docs = self.documents()
        scope = [c for c in self.passages.values() if not folder or _under(folder_of(docs.get(c.document, {})), folder)]
        found = self.live_relations(folder)
        return {"folder": folder, "passages": len(scope), "read": sum(1 for c in scope if c.id in self.read_by),
                "relations": len(found), "names": len({r.predicate for r in found}),
                "readers": sorted({self.read_by[c.id] for c in scope if c.id in self.read_by})}

    def read_relations(self, reader, onto=None, terms: list[dict] | None = None, *, folder: str = "",
                       should_stop=None, progress=None) -> dict:
        """Passages not read yet go through a reader. Each one comes back read in full or is left for the next run."""
        made = self.concepts(onto, terms)
        chunks = self.to_read(folder)
        labels = {c.id: [made["concepts"][i].label for i in made["per_chunk"].get(c.id, {}) if i in made["concepts"]] for c in chunks}
        vocabulary = {**{r.predicate: r.label for r in self.live_relations() if r.label}, **self.vocabulary}
        try:
            out = reader.read(chunks, labels, vocabulary, should_stop=should_stop, progress=progress)
        except Busy:  # a reader that keeps nothing when it is stopped
            out = {"relations": [], "answered": set(), "calls": 0, "vocabulary": {}, "busy": True}
        with self.lock:
            for c in chunks:
                if c.id in out["answered"]:
                    self.read_by[c.id] = reader.kind
                    self.relations[c.id] = [r for r in out["relations"] if r.chunk == c.id]
            self.vocabulary.update(out.get("vocabulary") or {})
            self.relations_version += 1
            self._made.clear()
        answered = sum(1 for c in chunks if c.id in out["answered"])
        return {"reader": reader.kind, "read": answered, "left": len(chunks) - answered, "calls": out["calls"],
                "found": sum(len(self.relations.get(c.id, [])) for c in chunks), "busy": bool(out.get("busy"))}

    def forget_relations(self, folder: str = "") -> int:
        """Read a folder again from the start: what readers found there goes."""
        with self.lock:
            docs = self.documents()
            gone = [cid for cid, c in self.passages.items() if cid in self.read_by
                    and (not folder or _under(folder_of(docs.get(c.document, {})), folder))]
            for cid in gone:
                self.read_by.pop(cid, None)
                self.relations.pop(cid, None)
            self.relations_version += 1
            self._made.clear()
            return len(gone)

    def relations_dump(self) -> dict:
        """What readers found, for a space kept across restarts. Passages that left the space are not kept."""
        live = [cid for cid in self.read_by if cid in self.passages]
        return {"read_by": {cid: self.read_by[cid] for cid in live},
                "relations": {cid: [r.to_dict() for r in self.relations.get(cid, [])] for cid in live},
                "vocabulary": dict(self.vocabulary)}

    def relations_load(self, data: dict) -> None:
        with self.lock:
            self.read_by.update({str(k): str(v) for k, v in (data.get("read_by") or {}).items()})
            for cid, rows in (data.get("relations") or {}).items():
                self.relations[str(cid)] = [Relation(**{k: str(r.get(k, "")) for k in Relation.__dataclass_fields__}) for r in rows]
            self.vocabulary.update(data.get("vocabulary") or {})
            self.relations_version += 1
            self._made.clear()

    def relation_triples(self, onto=None, terms: list[dict] | None = None) -> list[tuple[str, str, str, str]]:
        """(subject, relation, object, passage) with the object's or action's id where a concept is one, so a relation the
        documents state joins the definition it is about; any other concept goes by its name."""
        made = self.concepts(onto, terms)
        by_label = {c.label: c for c in made["concepts"].values()}

        def end(label: str) -> str:
            c = by_label.get(label)
            return c.element if c is not None and c.element.startswith(("object:", "action:")) else f"concept:{label}"

        return [(end(r.source), r.label or r.predicate, end(r.target), r.chunk) for r in self.live_relations()]

    def graph(self, onto=None, terms: list[dict] | None = None, folder: str = "") -> dict:
        """The picture of it, in the shape the page's graph takes; with a folder, only the documents in it."""
        rows = self._rows(onto, terms, folder)
        with_sections = len(rows["sections"]) <= GRAPH_SECTIONS_MAX
        nodes = [{"id": r[0], "label": r[1], "module": "document", "abstract": False, "table": r[2], "key": ""} for r in rows["documents"]]
        edges = []
        title = {r[0]: r[3] for r in rows["sections"]}
        parent = {r[0]: r[1] for r in rows["sections"]}
        if with_sections:
            nodes += [{"id": r[0], "label": r[3], "module": "section", "abstract": False, "table": "", "key": ""} for r in rows["sections"]]
            edges += [{"source": r[1], "target": r[0], "label": "절", "subtype": False} for r in rows["sections"]]
        for cid, label, kind, element in rows["concepts"]:
            nodes.append({"id": cid, "label": label, "module": "ontology" if element else kind, "abstract": False, "table": element, "key": ""})
        seen = set()
        for sid, cid in rows["section_concepts"]:
            src = sid if with_sections else parent.get(sid, sid)
            if (src, cid) not in seen:
                seen.add((src, cid))
                edges.append({"source": src, "target": cid, "label": "언급", "subtype": False})
        edges += [{"source": a, "target": b, "label": "함께 언급", "subtype": True} for a, b in rows["concept_links"]]
        edges += [{"source": r[1], "target": r[2], "label": r[4], "subtype": False, "relation": r[3], "evidence": r[6]}
                  for r in rows["relations"]]
        kinds = {n["module"] for n in nodes}
        words = {"document": "문서", "section": "절", "ontology": "온톨로지 요소", "term": "용어", "keyword": "키워드"}
        return {"nodes": nodes, "edges": edges, "clusters": [{"id": k, "label": v} for k, v in words.items() if k in kinds],
                "sections_shown": with_sections, "titles": title, "relations": len(rows["relations"]), "folder": folder}

    def mentions_of(self, element: str, onto=None, terms: list[dict] | None = None, limit: int = 6) -> list[dict]:
        """The sections that speak of one definition, for the object screen and an agent's evidence."""
        made = self.concepts(onto, terms)
        ids = {i for i, c in made["concepts"].items() if c.element == element or c.element.startswith(element + ".")}
        out = []
        for (doc, section), found in made["sections"].items():
            n = sum(found[i] for i in ids if i in found)
            if n:
                first = next(c for c in made["chunks"][doc] if c.section == section)
                out.append({"document": doc, "section": section, "count": n, "text": first.text[:150]})
        return sorted(out, key=lambda x: (-x["count"], x["document"], x["section"]))[:limit]

    def knowledge(self, onto=None, terms: list[dict] | None = None):
        """Definitions, rules, passages and the relations read between them in one index, built again when any changes."""
        from xgen_space.knowledge import build

        self.index()
        key = (id(onto), tuple(sorted(self.chunks)), len(terms or []), self.retriever, self.relations_version)
        if self._knowledge is None or self._knowledge[0] != key:
            self._knowledge = (key, build(onto, self, terms, self.retriever))
        return self._knowledge[1]

    def concepts_in(self, text: str, onto=None, terms: list[dict] | None = None) -> list[dict]:
        """The definitions a sentence names, which is how a search goes on from documents to the ontology."""
        names = dictionary(onto, terms)
        by_id = {c.id: c for c in names.values()}
        return [asdict(by_id[i]) | {"kind_label": KIND_WORD.get(by_id[i].kind, by_id[i].kind)} for i in _find(text, names)]

    # ---- what it is right now ------------------------------------------------------------------------------------

    def state(self) -> dict:
        self.index()
        stores = []
        for name, s in self.stores.items():
            try:
                held = s.count(self.collection)
            except (VectorError, OSError) as e:
                held, self.errors[name] = 0, str(e)
            stores.append({**s.describe(), "name": name, "count": held, "error": self.errors.get(name, ""), "primary": name == self.primary()})
        docs = self.documents()
        return {"embedder": self.embedder.describe(), "stores": stores, "collection": self.collection, "documents": len(docs),
                "fixed": len(self.fixed), "uploaded": len(self.uploaded), "chunks": len(self.chunks), "passages": len(self.passages),
                "sections": len({(c.document, c.section) for c in self.chunks.values()}), "took": self.took, "checks": len(self.checks),
                "embed_error": self.embed_error, "ok": not self.errors and not self.embed_error}


def _read_documents(patterns: list[str], base: Path) -> list[dict]:
    from xgen_space.ingest import ingest

    out = []
    for pat in patterns:
        for p in sorted(base.glob(pat)):
            if p.is_file():
                out += ingest(p.read_bytes(), p.name).documents
    return out


def open_space(spec: dict | None, base: Path | None = None) -> Space:
    """`space:` in a studio file. With nothing said, a space still works: exact search in memory and the hash embedder."""
    spec = dict(spec or {})
    stores = {n: open_vector_store({**s, "name": n}) for n, s in (spec.get("vectors") or {}).items()}
    space = Space(open_embedder(spec.get("embedder")), stores or None, collection=spec.get("collection", "documents"),
                  checks=spec.get("checks"))
    space.retriever = str(spec.get("retriever") or "")
    for d in _read_documents(list(spec.get("documents") or []), base or Path(".")):
        space.add(d, fixed=True)
    return space


__all__ = ["Chunk", "Concept", "DOCUMENT_MODULE", "KIND_WORD", "Space", "dictionary", "keywords", "open_space", "split"]
