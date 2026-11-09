"""Relation reading: what a document says between the concepts it names, read by a model and kept with the sentence that
says it.

A reader is a port like the stores. `basic` needs nothing but a model; `ontology-build` is xgen-ontology-build's relation
formation (`pip install xgen-space[build]`). Either way the two ends of a relation are concepts the passage names, numbered
for the model, so a model picks between them and never invents one.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

PREDICATE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
OWN_NAMES = {"hassection", "sectionof", "mentions", "mentionedin", "relatedto", "sameas", "instanceof", "subclassof", "type"}
SENTENCE = re.compile(r"(?<=[.!?。])\s+|\n+")
BATCH_CHARS = 3000  # one call's units: what a model reads with care, and an answer that fits its token budget
LABEL_MAX = 30
VOCABULARY_SHOWN = 40
EVIDENCE_MAX = 300

READ_SYSTEM = """문서의 단위마다 글 한 조각과 그 안에 나온 개념의 번호 목록이 있습니다. 그 단위의 글이 명시한 관계만 고릅니다.

규칙:
1. 같은 단위 안의 두 개념 사이에서, 그 단위의 글이 말하는 관계만 적습니다. 추측하지 않습니다.
2. 한 쌍에는 가장 구체적인 관계 하나만 적습니다.
3. p 는 영어 camelCase 동사 한 단어입니다. 같은 뜻의 이름이 '쓰는 관계 이름'에 있으면 그 이름을 그대로 씁니다. 두 개념이 함께 나왔다는 것 외에 뜻이 없는 이름은 쓰지 않습니다.
4. s 는 관계를 행하거나 가지는 쪽, o 는 받는 쪽입니다. label 은 그 관계를 한국어 두세 단어로 씁니다.
5. 관계가 없는 단위는 적지 않습니다.

출력: JSON 배열만 답합니다. [{"u": 단위 번호, "s": 주어 번호, "p": 관계 이름, "o": 목적어 번호, "label": 한국어 이름}]"""


@dataclass
class Relation:
    source: str
    predicate: str
    target: str
    label: str
    chunk: str
    document: str
    section: str
    evidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Unit:
    chunk: str
    document: str
    section: str
    text: str
    mentions: list[str]


class Busy(RuntimeError):
    """The model may not be called now (a limit for the whole site); what was read so far stays."""


def mentions_in(text: str, labels: list[str]) -> list[str]:
    """The labels a text says, in the order it says them. Longest first, so 주문상품 is not also 주문."""
    taken = [False] * len(text)
    found: dict[str, int] = {}
    for label in sorted(set(labels), key=lambda x: (-len(x), x)):
        start = text.find(label)
        while start >= 0:
            end = start + len(label)
            if not any(taken[start:end]):
                taken[start:end] = [True] * len(label)
                found.setdefault(label, start)
            start = text.find(label, end)
    return sorted(found, key=found.get)


def units_of(chunks: list, labels: dict[str, list[str]]) -> list[Unit]:
    """A passage's sentences that name two concepts or more: the only places a relation between concepts can be said."""
    out = []
    for c in chunks:
        for s in (x.strip() for x in SENTENCE.split(c.text)):
            named = mentions_in(s, labels.get(c.id, [])) if s else []
            if len(named) >= 2:
                out.append(Unit(c.id, c.document, c.section, s, named))
    return out


def evidence_of(text: str, a: str, b: str) -> str:
    """The sentence of a passage that names both ends of a relation."""
    for s in (x.strip() for x in SENTENCE.split(text)):
        if a in s and b in s:
            return s[:EVIDENCE_MAX]
    return text[:EVIDENCE_MAX]


def parse_rows(raw: str) -> list | None:
    """The rows of an answer; None when the answer is not one."""
    text = re.sub(r"```(?:json)?", "", raw or "")
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        brace = text.find("{")
        try:
            whole = json.loads(text[brace:text.rfind("}") + 1]) if brace >= 0 else None
        except ValueError:
            return None
        rows = whole.get("relations") if isinstance(whole, dict) else None
        return rows if isinstance(rows, list) else None
    try:
        rows = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return rows if isinstance(rows, list) else None


def good_predicate(name: str) -> bool:
    return bool(PREDICATE.match(name)) and name.lower() not in OWN_NAMES


def vocabulary_lines(vocabulary: dict[str, str]) -> str:
    return "\n".join(f"- {n}: {d}".rstrip(": ") for n, d in list(vocabulary.items())[:VOCABULARY_SHOWN])


class BasicReader:
    """Units batched by size, one call a batch, every row checked against the units it names."""

    kind = "basic"

    def __init__(self, llm: Callable[[str, str], str], *, batch_chars: int = BATCH_CHARS):
        self.llm, self.batch_chars = llm, batch_chars

    def batches(self, units: list[Unit]) -> list[list[Unit]]:
        """A passage's units stay in one batch, so a passage is read in full or left for the next run."""
        by_chunk: dict[str, list[Unit]] = {}
        for u in units:
            by_chunk.setdefault(u.chunk, []).append(u)
        out, cur, size = [], [], 0
        for group in by_chunk.values():
            n = sum(len(u.text) + 12 * len(u.mentions) for u in group)
            if cur and size + n > self.batch_chars:
                out.append(cur)
                cur, size = [], 0
            cur += group
            size += n
        if cur:
            out.append(cur)
        return out

    @staticmethod
    def prompt(batch: list[Unit], vocabulary: dict[str, str]) -> str:
        lines = [f"[{i}] ({u.document} / {u.section}) {u.text}\n  개념: " + " ".join(f"{n}={m}" for n, m in enumerate(u.mentions, 1))
                 for i, u in enumerate(batch, 1)]
        head = f"## 쓰는 관계 이름 (같은 뜻이면 이 이름을 씁니다)\n{vocabulary_lines(vocabulary)}\n\n" if vocabulary else ""
        return head + "## 단위\n" + "\n".join(lines)

    @staticmethod
    def relations(batch: list[Unit], rows: list) -> list[Relation]:
        seen, out = set(), []
        for r in rows:
            if not isinstance(r, dict):
                continue
            try:
                u, i, j = int(r.get("u")), int(r.get("s")), int(r.get("o"))
            except (TypeError, ValueError):
                continue
            pred = str(r.get("p") or "").strip()
            if not 1 <= u <= len(batch) or not good_predicate(pred):
                continue
            unit = batch[u - 1]
            if i == j or not (1 <= i <= len(unit.mentions) and 1 <= j <= len(unit.mentions)):
                continue
            a, b = unit.mentions[i - 1], unit.mentions[j - 1]
            if (a, pred.lower(), b) in seen:
                continue
            seen.add((a, pred.lower(), b))
            label = str(r.get("label") or "").strip()[:LABEL_MAX]
            out.append(Relation(a, pred, b, label, unit.chunk, unit.document, unit.section, unit.text[:EVIDENCE_MAX]))
        return out

    def read(self, chunks: list, labels: dict[str, list[str]], vocabulary: dict[str, str], *,
             should_stop: Callable[[], bool] | None = None, progress: Callable[[int, int], None] | None = None) -> dict:
        units = units_of(chunks, labels)
        batches = self.batches(units)
        answered = {c.id for c in chunks} - {u.chunk for u in units}  # a passage naming fewer than two concepts says no relation
        found: list[Relation] = []
        calls, busy = 0, False
        for n, batch in enumerate(batches, 1):
            if should_stop is not None and should_stop():
                break
            calls += 1
            try:
                raw = self.llm(READ_SYSTEM, self.prompt(batch, {**vocabulary, **{r.predicate: r.label for r in found if r.label}}))
            except Busy:
                busy = True
                break
            except Exception:  # a model that timed out or broke off: its passages are asked again on the next run
                continue
            rows = parse_rows(raw)
            if rows is not None:
                found += self.relations(batch, rows)
                answered |= {u.chunk for u in batch}
            if progress is not None:
                progress(n, len(batches))
        return {"relations": found, "answered": answered, "calls": calls, "vocabulary": {}, "busy": busy}


class OntologyBuildReader:
    """xgen-ontology-build's relation formation: its units, batching, vocabulary and naming, verbatim."""

    kind = "ontology-build"

    def __init__(self, llm: Callable[[str, str], str], *, char_budget: int = 6000, max_output_tokens: int = 4000):
        from xgen_ontology_build.extract.relation_formation import KO_RELATION_PROMPTS, RelationFormer
        from xgen_ontology_build.llm import CallableLLM

        self.llm = llm
        self.make = lambda stop, progress: RelationFormer(
            CallableLLM(lambda prompt, system="": self._call(system, prompt)), prompts=KO_RELATION_PROMPTS,
            char_budget=char_budget, max_output_tokens=max_output_tokens, should_stop=stop, progress=progress)
        self.busy = False

    def _call(self, system: str, user: str) -> str:
        try:
            return self.llm(system, user)
        except Busy:
            self.busy = True
            raise

    def read(self, chunks: list, labels: dict[str, list[str]], vocabulary: dict[str, str], *,
             should_stop: Callable[[], bool] | None = None, progress: Callable[[int, int], None] | None = None) -> dict:
        self.busy = False
        former = self.make(lambda: self.busy or bool(should_stop and should_stop()), progress)
        docs: dict[str, list[dict]] = {}
        for c in chunks:
            docs.setdefault(c.document, []).append({"chunk_id": c.id, "chunk_text": c.text, "chunk_index": c.ordinal})
        got, stats = former.extract(docs, {c.id: labels.get(c.id, []) for c in chunks},
                                    vocabulary=[{"name": n, "definition": d} for n, d in vocabulary.items()])
        by_id = {c.id: c for c in chunks}
        found = []
        for r in got:
            c = by_id.get((r.source_chunks or [""])[0])
            if c is None or not good_predicate(r.predicate):
                continue
            found.append(Relation(r.subject, r.predicate, r.object, (r.label or "")[:LABEL_MAX], c.id, c.document, c.section,
                                  evidence_of(c.text, r.subject, r.object)))
        new = {str(v.get("name")): str(v.get("definition") or "") for v in stats.get("new_vocabulary") or [] if v.get("name")}
        return {"relations": found, "answered": {c.id for c in chunks} - set(former.lost_chunk_ids),
                "calls": former.llm_calls, "vocabulary": new, "busy": self.busy}


READERS: dict[str, Callable[..., Any]] = {"basic": BasicReader, "ontology-build": OntologyBuildReader}


def register_reader(kind: str, make: Callable[..., Any]) -> None:
    READERS[kind] = make


def _has_build() -> bool:
    try:
        import xgen_ontology_build  # noqa: F401

        return True
    except ImportError:
        return False


def known_readers() -> list[str]:
    return sorted(k for k in READERS if k != "ontology-build" or _has_build())


def default_reader() -> str:
    return "ontology-build" if _has_build() else "basic"


def open_reader(kind: str, llm: Callable[[str, str], str]):
    kind = kind or default_reader()
    if kind not in READERS:
        raise ValueError(f"unknown relation reader '{kind}'; known: {', '.join(known_readers())}")
    return READERS[kind](llm)


__all__ = ["BasicReader", "Busy", "OntologyBuildReader", "Relation", "Unit", "default_reader", "evidence_of", "known_readers",
           "mentions_in", "open_reader", "parse_rows", "register_reader", "units_of"]
