"""One question, one answer. The engine decides what it can: a key and a decision run the table, a key alone reads the record,
a registered query runs by its name. What is left goes to the passages and the rules found, and a model only ever words those.

Every answer carries what it stands on: the rule, the source values, the clause.
"""
from __future__ import annotations

import re
from typing import Any

from xgen_space.embed import shared_wording

KEY = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z]{1,6}[-_]?\d[\w-]*|(?<!\d)\d{4,}(?!\d)")
PLAIN = {"가능", "여부", "결과", "판정", "금액", "기준"}  # words of a decision's name that say nothing of what it decides
QUERY_MATCH = 0.6  # how much of a registered query's name a question must have to run it without a model
TYPES_MAX = 40  # object types a key is looked for in
SOURCE_FLOOR = 0.4  # a source scoring under this share of the best one is noise, not evidence


def keys_in(text: str) -> list[str]:
    return list(dict.fromkeys(KEY.findall(text)))


def _named_types(tools, text: str) -> list[str]:
    """The types a key may belong to: those a question names, then those decisions are about, then the rest."""
    onto = tools.studio.onto
    named = [o.name for o in onto.objects.values() if (o.label or o.name) in text]
    targets = [t.target for t in onto.decisions.values() if t.target]
    rest = [o.name for o in onto.objects.values()]
    return [t for t in dict.fromkeys(named + targets + rest) if onto.objects[t].table][:TYPES_MAX]


def find_record(tools, text: str) -> tuple[str, str] | None:
    """The first key in a question that is really there, and its type."""
    for key in keys_in(text):
        for t in _named_types(tools, text):
            try:
                if tools.studio.fetch(t, key) is not None:
                    return t, key
            except (KeyError, ValueError, RuntimeError):
                continue
    return None


def decisions_for(tools, text: str, type_name: str) -> list[str]:
    """Decisions about this type whose name the question speaks of."""
    out = []
    for t in tools.studio.onto.decisions.values():
        if t.target != type_name:
            continue
        words = [w for w in re.split(r"[\s·,]+", t.label or t.name) if len(w) >= 2 and w not in PLAIN]
        if any(w in text for w in words):
            out.append(t.name)
    return out


def _decision(tools, name: str, key: str) -> dict:
    from xgen_space.check import _find_prop
    from xgen_space.decide.words import input_label, verdict

    st = tools.studio
    t = st.onto.decisions[name]
    res = tools.decide(name, key)
    outs = res["outputs"] if isinstance(res["outputs"], dict) else {"result": res["outputs"]}
    said, good = verdict(t, outs)
    reason = next((v for v in outs.values() if isinstance(v, str)), "")
    rules = [{"id": r.id, "cite": r.cite or t.cite} for r in t.rules if r.id in (res["matched"] or [])]
    evidence = []
    for e in res["evidence"]:
        p = _find_prop(st.onto, e["object_type"], e["property"]) if e.get("object_type") and e.get("property") else None
        evidence.append({"label": input_label(st.onto, t, e["input"]) if e["input"] in t.inputs else e["input"], "value": e["value"],
                         "source": e.get("source") or "", "property": p.label if p is not None else ""})
    target = st.onto.objects.get(t.target)
    return {"name": name, "label": t.label or name, "target": t.target, "target_label": (target.label or t.target) if target else "",
            "key": key, "verdict": said, "good": good, "reason": reason, "outputs": outs, "rules": rules, "evidence": evidence}


def _sources(found: list[dict], k: int) -> list[dict]:
    kept = [f for f in found if f["kind"] in ("document", "rule")]
    floor = kept[0]["score"] * SOURCE_FLOOR if kept else 0
    return [f for f in kept if f["score"] >= floor][:k]


def _definitions(found: list[dict], k: int = 6) -> list[dict]:
    return [{"id": f["id"], "kind_label": f["kind_label"], "title": f["title"], "element": f["element"]}
            for f in found if f["kind"] in ("object", "query", "action")][:k]


def _query(tools, text: str, found: list[dict]) -> dict | None:
    """A registered query the question names, when it needs nothing more to run."""
    onto = tools.studio.onto
    for f in found:
        if f["kind"] != "query":
            continue
        name = f["id"].split(":", 1)[1]
        q = onto.queries.get(name)
        close = min(shared_wording(f["title"], text), shared_wording(text, f["title"]))  # a question that adds a condition is another query
        if q is None or close < QUERY_MATCH or q.params:
            continue
        res = tools.run_query(name)
        return {"name": name, "label": f["title"], "columns": res["columns"], "rows": res["rows"][:50], "total": len(res["rows"])}
    return None


def answer_question(tools, text: str, *, k: int = 6) -> dict[str, Any]:
    text = " ".join(str(text or "").split())[:300]
    if not text:
        raise ValueError("질문이 없어 답변하지 못했습니다. 질문을 입력해 주세요.")
    know = tools.knowledge()
    found = know.find(text, max(k * 4, 24))
    out: dict[str, Any] = {"ok": True, "question": text, "route": "documents", "answer": "", "engine": know.retriever.kind,
                           "sources": _sources(found, k), "definitions": _definitions(found), "relations": know.relations(text)}
    hit = find_record(tools, text)
    if hit:
        type_name, key = hit
        names = decisions_for(tools, text, type_name)
        allowed = tools.describe()["decisions"]
        names = [n for n in names if n in allowed]
        if names:
            out["decisions"] = [_decision(tools, n, key) for n in names]
            d = out["decisions"][0]
            out["route"], out["answer"] = "decision", f"{d['target_label']} {key}: {d['label']} {d['verdict']}. {d['reason']}".strip()
            used = [f"rule:{x['name']}.{r['id']}" for x in out["decisions"] for r in x["rules"]]
            first = [e for i in used for e in know.standing_on(i)]
            seen = {e["id"] for e in first}
            out["sources"] = (first + [s for s in out["sources"] if s["id"] not in seen and s["kind"] == "document"])[:k]  # other rules did not apply
            return out
        out["route"], out["record"] = "record", tools.record(type_name, key)
        out["answer"] = f"{out['record']['label']} {key}의 값입니다."
        return out
    q = _query(tools, text, found)
    if q is not None:
        out["route"], out["query"] = "query", q
        out["answer"] = f"{q['label']} 결과 {q['total']}건입니다."
        return out
    top = out["sources"][0] if out["sources"] else None
    out["needs_model"] = True
    if top is None:
        out["route"], out["answer"] = "none", "관련 정의와 문서를 찾지 못했습니다."
    else:
        out["answer"] = top["text"].split("\n")[0][:220]
    return out


__all__ = ["answer_question", "decisions_for", "find_record", "keys_in"]
