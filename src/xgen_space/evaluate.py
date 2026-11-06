"""Does the ontology change the answer? The same questions to the same model, three ways: with nothing, with the documents
alone, and through the space. A right answer is settled by the question file, not by a model.

    xspace compare studio.yaml answers.yaml --llm-url ... --llm-model ...
"""
from __future__ import annotations

import re
from typing import Any, Callable

from xgen_space.tools import StudioTools

Llm = Callable[[str, str], str]

BARE = "쇼핑몰 고객 질문에 한국어로 짧게 답합니다."
PASSAGES = "주어진 근거 안의 내용으로만 한국어로 짧게 답합니다. 근거에 없으면 모른다고 답합니다."
VERDICT = "반품 여부를 묻는 질문이면 답의 첫 단어를 가능, 불가, 모름 중 하나로 씁니다."
MODES = ("none", "documents", "space")
MODE_WORD = {"none": "온톨로지 없음", "documents": "문서 검색만", "space": "XGEN Space"}


def _money(text: str) -> set[int]:
    """Amounts as a person writes them: 3,000원, 3000, 3천원, 무료."""
    found = {int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", text)}
    found |= {int(x) * 1000 for x in re.findall(r"(\d+)\s*천", text)}
    if "무료" in text:
        found.add(0)
    return found


def right(q: dict, text: str, expected: Any = None) -> bool:
    """Whether an answer says what the question file says it should."""
    text = text or ""
    if "eligible" in q:
        head = text.strip()[:40]
        if head.startswith("모름"):  # not knowing is not a verdict
            return False
        no, yes = "불가" in head or "없습니다" in head, "가능" in head
        return (yes and not no) if q["eligible"] else no
    if "fee" in q:
        return q["fee"] in _money(text)
    if q.get("must"):
        return all(w in text for w in q["must"])
    if expected:
        return all(str(v) in text.replace(",", "") for v in expected)
    return False


def _kind(q: dict) -> str:
    return "판정" if q.get("decision") else ("데이터" if q.get("query") else "문서")


def _none(q: dict, tools, llm: Llm) -> str:
    return llm(f"{BARE} {VERDICT}", q["text"])


def _documents(q: dict, tools, llm: Llm) -> str:
    hits = tools.studio.space.search(q["text"], 5)
    lines = "\n".join(f"[{i + 1}] {h['document']} / {h['section']}: {h['text']}" for i, h in enumerate(hits))
    return llm(f"{PASSAGES} {VERDICT}", f"질문: {q['text']}\n\n근거:\n{lines}")


def _space(q: dict, tools, llm: Llm) -> str:
    a = tools.answer_question(q["text"])
    if a["route"] == "decision":
        d = a["decisions"][0]
        return f"{d['verdict']}. {d['reason']}"
    if a["route"] == "query":
        rows = a["query"]["rows"][:1]
        return " ".join(str(v) for r in rows for v in r.values())
    lines = "\n".join(f"[{i + 1}] {s['title']}: {s['text']}" for i, s in enumerate(a["sources"][:5]))
    return llm(PASSAGES, f"질문: {q['text']}\n\n근거:\n{lines}") if lines else a["answer"]


RUN = {"none": _none, "documents": _documents, "space": _space}


def compare(tools: StudioTools, questions: list[dict], llm: Llm, *, modes: tuple[str, ...] = MODES, note: Callable | None = None) -> dict:
    per = {m: {"right": 0, "kinds": {}} for m in modes}
    rows = []
    for q in questions:
        expected = None
        if q.get("query"):
            first = tools.run_query(q["query"])["rows"][0]
            expected = [next(iter(first.values()))]
        said = {}
        for m in modes:
            try:
                text = RUN[m](q, tools, llm)
            except (TimeoutError, OSError, ValueError, RuntimeError) as e:
                text = f"오류 {e}"
            ok = right(q, text, expected)
            said[m] = {"right": ok, "text": text[:240]}
            k = per[m]["kinds"].setdefault(_kind(q), [0, 0])
            k[0] += int(ok)
            k[1] += 1
            per[m]["right"] += int(ok)
        rows.append({"text": q["text"], "kind": _kind(q), **said})
        if note:
            note(rows[-1])
    n = len(questions) or 1
    return {"questions": len(questions), "modes": {m: {"label": MODE_WORD[m], "right": per[m]["right"], "accuracy": round(per[m]["right"] / n, 3),
                                                       "kinds": {k: {"right": v[0], "of": v[1]} for k, v in per[m]["kinds"].items()}} for m in modes},
            "rows": rows}


__all__ = ["MODES", "MODE_WORD", "compare", "right"]
