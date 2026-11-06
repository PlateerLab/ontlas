"""One index over what a space knows. Definitions and rules come from the ontology, passages from the documents, and a
question goes to both at once, so a rule and the clause behind it land side by side.

The retriever is a port like the stores. `words` needs nothing; `omnifuse` fuses the same entries with the graph between
them (`pip install xgen-space[omnifuse]`). Which one runs never changes what an entry is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from xgen_space.embed import shared_wording

KIND_WORD = {"document": "문서", "rule": "규칙", "object": "객체", "query": "등록 질의", "action": "Action"}
SPACES = re.compile(r"\s+")
ARTICLE = re.compile(r"(\d+)(?:\.\d+)?\s*조")
KEPT_FROM_STORE = 2  # passages the vector store ranks highest stay among the found, whatever the fusion made of them
KEPT_SCORE = 0.5  # of the best score: below what fusion ranked, above what is noise


@dataclass
class Entry:
    id: str
    kind: str
    title: str
    text: str
    element: str = ""  # what it is in the ontology: object:Order, decision:returnEligibility
    mentions: list[str] = field(default_factory=list)  # the elements it speaks of
    meta: dict[str, Any] = field(default_factory=dict)


def _object(onto, o) -> Entry:
    names = [p.label or p.name for p in o.properties.values()]
    links = [lk.label or lk.name for lk in onto.links.values() if o.name in (lk.source, lk.target)]
    body = " ".join(x for x in (o.description, "속성 " + ", ".join(names) if names else "", "관계 " + ", ".join(links) if links else "") if x)
    return Entry(f"object:{o.name}", "object", o.label or o.name, body, f"object:{o.name}")


def _rules(onto) -> list[Entry]:
    from xgen_space.decide.words import reads, rule_sentence

    out = []
    for t in onto.decisions.values():
        about = [f"decision:{t.name}"] + ([f"object:{t.target}"] if t.target else [])
        for name in t.inputs:
            here, prop = reads(onto, t, name)
            if here:
                about.append(f"object:{here}")
            if here and prop:
                about.append(f"property:{here}.{prop}")
        for r in t.rules:
            out.append(Entry(f"rule:{t.name}.{r.id}", "rule", f"{t.label or t.name} · {r.id}", rule_sentence(onto, t, r),
                             f"decision:{t.name}", sorted(set(about)), {"decision": t.name, "rule": r.id, "cite": r.cite or t.cite}))
    return out


def entries(onto, space=None, terms: list[dict] | None = None) -> list[Entry]:
    """Everything a question can be answered from, each in words."""
    items: list[Entry] = []
    if onto is not None:
        items += [_object(onto, o) for o in onto.objects.values()]
        items += _rules(onto)
        for name, q in onto.queries.items():
            items.append(Entry(f"query:{name}", "query", q.label or name, q.description or q.label or name, f"query:{name}"))
        for a in onto.actions.values():
            items.append(Entry(f"action:{a.name}", "action", a.label or a.name, f"{a.label or a.name} 처리 요청", f"action:{a.name}",
                               [f"object:{a.target}"]))
    if space is not None:
        made = space.concepts(onto, terms)
        for c in space.chunks.values():
            found = made["sections"].get((c.document, c.section), {})
            about = sorted({made["concepts"][i].element for i in found if i in made["concepts"] and made["concepts"][i].element})
            items.append(Entry(c.id, "document", f"{c.document} {c.section}", c.text, "", about, {"document": c.document, "section": c.section}))
    return items


def _tight(text: str) -> str:
    return SPACES.sub("", text or "")


def links_between(onto, items: list[Entry]) -> list[tuple[str, str, str]]:
    """The graph between entries. A rule's citation ties it to the clause it comes from."""
    out: list[tuple[str, str, str]] = []
    if onto is not None:
        for lk in onto.links.values():
            out.append((f"object:{lk.source}", lk.label or lk.name, f"object:{lk.target}"))
    docs = [e for e in items if e.kind == "document"]
    for e in items:
        out += [(e.id, "언급", m) for m in e.mentions if m != e.id]
        cite = _tight(e.meta.get("cite", ""))
        if not cite:
            continue
        number = ARTICLE.search(e.meta.get("cite", ""))
        for d in docs:
            if _tight(d.meta.get("document", "")) in cite and number and f"{number.group(1)}조" in d.meta.get("section", ""):
                out += [(e.id, "출처", d.id), (d.id, "근거 규칙", e.id)]
    return out


class WordsRetriever:
    """The vector store for passages, shared wording for definitions. Needs nothing beyond the space itself."""

    kind = "words"

    def __init__(self, items: list[Entry], links: list[tuple[str, str, str]], space=None, embed=None):
        self.items, self.links, self.space = items, links, space
        self.by_id = {e.id: e for e in items}

    def search(self, text: str, k: int) -> list[tuple[Entry, float]]:
        passages = {h["id"]: h["score"] for h in self.space.search(text, k)} if self.space is not None and self.space.chunks else {}
        scored = []
        for e in self.items:
            s = passages.get(e.id, 0.0) if e.kind == "document" else shared_wording(text, f"{e.title} {e.text}")
            if s > 0:
                scored.append((e, s))
        return sorted(scored, key=lambda x: -x[1])[:k]

    def relations(self, text: str) -> list[str]:
        return []


class OmniFuseRetriever:
    """The same entries through OmniFuse: lexical and dense seeds, then the passages the graph ties to them."""

    kind = "omnifuse"

    def __init__(self, items: list[Entry], links: list[tuple[str, str, str]], space=None, embed: Callable | None = None):
        from omnifuse import Chunk, Node, Triple, build_inmemory

        self.by_id, self.space = {e.id: e for e in items}, space
        labels = {e.id: e.title for e in items}
        ids = {x for s, _, o in links for x in (s, o)} | set(labels)
        nodes = [Node(i, labels.get(i, i.split(":", 1)[-1]), "class" if i.startswith("object:") else "instance") for i in sorted(ids)]
        triples = [Triple(s, p, o) for s, p, o in links]
        vectors = embed([f"{e.title} {e.text}" for e in items]) if embed and items else [None] * len(items)
        chunks = [Chunk(e.id, e.text, entities=list(e.mentions), embedding=v, title=e.title) for e, v in zip(items, vectors)]
        self.fuse = build_inmemory(nodes, triples, chunks, embedder=(lambda q: embed([q])[0]) if embed else None)

    def search(self, text: str, k: int) -> list[tuple[Entry, float]]:
        found = [(self.by_id[c.id], float(s)) for c, s in self.fuse.retrieve(text, limit=k) if c.id in self.by_id]
        if self.space is None or not self.space.chunks or not getattr(self.space.embedder, "semantic", False):
            return found
        seen = {e.id for e, _ in found}  # a passage that shares no word with a question can fall to the fusion's cut; the store's best stay in
        top = found[0][1] if found else 1.0
        for h in self.space.search(text, KEPT_FROM_STORE):
            if h["id"] in self.by_id and h["id"] not in seen:
                found.append((self.by_id[h["id"]], top * KEPT_SCORE))
        return found[:max(k, len(found))]

    def relations(self, text: str) -> list[str]:
        return list(self.fuse.search(text, synthesize=False).relations)[:12]


RETRIEVERS: dict[str, Callable] = {"words": WordsRetriever, "omnifuse": OmniFuseRetriever}


def register_retriever(kind: str, make: Callable) -> None:
    RETRIEVERS[kind] = make


def known_retrievers() -> list[str]:
    return sorted(RETRIEVERS)


def _has_omnifuse() -> bool:
    try:
        import omnifuse  # noqa: F401

        return True
    except ImportError:
        return False


def default_retriever() -> str:
    return "omnifuse" if _has_omnifuse() else "words"


class Knowledge:
    def __init__(self, items: list[Entry], links: list[tuple[str, str, str]], retriever, keep: Any = None):
        self.items, self.links, self.retriever = items, links, retriever
        self._keep = keep  # the ontology this was built from: its identity is the cache key

    def find(self, text: str, k: int = 8, kinds: tuple[str, ...] = ()) -> list[dict]:
        wide = max(k * 4, 24) if kinds else k
        out = []
        for e, score in self.retriever.search(text, wide):
            if kinds and e.kind not in kinds:
                continue
            out.append(self._said(e, score))
        return out[:k]

    def relations(self, text: str) -> list[str]:
        return [r for r in self.retriever.relations(text) if " → 언급 → " not in r]  # that a text names a thing is no relation

    def _said(self, e: Entry, score: float = 1.0) -> dict:
        return {"id": e.id, "kind": e.kind, "kind_label": KIND_WORD.get(e.kind, e.kind), "title": e.title, "text": e.text,
                "element": e.element, "score": round(score, 4), **e.meta}

    def standing_on(self, entry_id: str) -> list[dict]:
        """An entry and the clauses it cites: what a matched rule rests on."""
        by_id = {e.id: e for e in self.items}
        if entry_id not in by_id:
            return []
        cited = [o for s, p, o in self.links if s == entry_id and p == "출처" and o in by_id]
        return [self._said(by_id[i]) for i in [entry_id, *cited]]

    def describe(self) -> dict:
        counts: dict[str, int] = {}
        for e in self.items:
            counts[KIND_WORD.get(e.kind, e.kind)] = counts.get(KIND_WORD.get(e.kind, e.kind), 0) + 1
        return {"kind": self.retriever.kind, "entries": len(self.items), "by_kind": counts, "links": len(self.links),
                "kinds": known_retrievers()}


def build(onto, space=None, terms: list[dict] | None = None, kind: str = "") -> Knowledge:
    items = entries(onto, space, terms)
    links = links_between(onto, items)
    embed = None
    if space is not None and getattr(space.embedder, "semantic", False):
        embed = space.embedder.embed
    make = RETRIEVERS[kind or default_retriever()]
    return Knowledge(items, links, make(items, links, space=space, embed=embed), keep=onto)


__all__ = ["Entry", "KIND_WORD", "Knowledge", "OmniFuseRetriever", "WordsRetriever", "build", "default_retriever", "entries",
           "known_retrievers", "links_between", "register_retriever"]
