"""What the quality screens and two of the operations screens ask: a validation question written whole and tried
before it is saved, the log of what was decided and approved, and which documents stand behind which Object.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ontlas.web.routes import get, post

QUESTION_KEYS = ("text", "decision", "key", "query", "params")  # what update_question cannot change: written anew
META_KEYS = ("type", "holdout", "grading", "keywords", "owner")
# an audit event as the log names it: (word, tone)
EVENT = {"decided": ("판정", "b"), "answered": ("질문 답변", ""), "function_ran": ("함수 실행", ""),
         "requested": ("Action 요청", "warn"), "approved": ("승인", "ok"), "auto_approved": ("자동 승인", "ok"),
         "rejected": ("반려", "bad"), "executed": ("데이터 소스 반영", "ok"), "written": ("데이터 소스 기록", "ok"),
         "called": ("외부 호출", ""), "call_failed": ("외부 호출 실패", "bad"), "rolled_back": ("되돌림", "warn"),
         "stale": ("재검사 실패", "bad")}
CHANGE_EVENT = {"proposed": ("변경 요청", ""), "approved": ("승인", "ok"), "rejected": ("반려", "bad")}
DOC_KIND = {"policy": "정책서", "screen": "화면 정의", "other": "문서"}
DOC_STATE = {"embedded": "색인 완료", "pending": "색인 대기", "failed": "색인 실패", "off": "검색 제외", "none": "본문 없음"}


# ---- a validation question ------------------------------------------------------------------------------------------

def _keywords(v: Any) -> list[str]:
    return [str(w).strip() for w in (v.split(",") if isinstance(v, str) else v or []) if str(w).strip()]


def _question(a: dict, onto) -> dict:
    """What a form sent, as add_question takes it. What a question asks (a decision, a query, or what a word means) is
    read from what it names; its type is the word it is filed under. Says in a person's words what is missing."""
    from ontlas.model import GRADINGS, QUESTION_TYPES

    text = " ".join(str(a.get("text") or "").split())
    if not text:
        raise ValueError("질문이 없어 저장하지 못했습니다. 질문을 입력해 주세요.")
    kind = str(a.get("type") or "")
    if kind not in QUESTION_TYPES:
        raise ValueError("유형이 없어 저장하지 못했습니다. 정의형, 판정형, 값 조회형 중 하나를 선택해 주세요.")
    grading = str(a.get("grading") or "")
    if grading and grading not in GRADINGS:
        raise ValueError("평가 방법이 올바르지 않아 저장하지 못했습니다. 평가 방법을 다시 선택해 주세요.")
    out: dict[str, Any] = {"text": text, "type": kind, "grading": grading, "holdout": bool(a.get("holdout")),
                           "keywords": _keywords(a.get("keywords")), "owner": str(a.get("owner") or "").strip()}
    by_words = bool(out["keywords"]) and grading in ("keywords", "evidence")  # held right by its words, not by a value
    expect = a.get("expect")
    if a.get("decision"):
        name = str(a["decision"])
        if name not in onto.decisions:
            raise ValueError("결정표가 선택되지 않아 저장하지 못했습니다. 결정표를 선택해 주세요.")
        given = a.get("values") if isinstance(a.get("values"), dict) else {}
        values = {str(k): v for k, v in given.items() if v != ""}  # None stays: the value is given as none
        key = str(a.get("key") or "").strip()
        if not key and not values:
            raise ValueError("판정 값이나 레코드 키가 없어 저장하지 못했습니다. 판정 값 또는 레코드 키를 입력해 주세요.")
        expect = expect if isinstance(expect, dict) else {}
        if not expect and not by_words:
            raise ValueError("정답이 없어 저장하지 못했습니다. 정답 판정 결과를 하나 이상 입력해 주세요.")
        out.update(decision=name, key=key, values=values, expect=expect)
    elif a.get("query"):
        name = str(a["query"])
        if name not in onto.queries:
            raise ValueError("질의가 선택되지 않아 저장하지 못했습니다. 등록된 질의를 선택해 주세요.")
        params = a.get("params") if isinstance(a.get("params"), dict) else {}
        if expect in (None, "", {}, []) and not by_words:
            raise ValueError("정답이 없어 저장하지 못했습니다. 기대 행 수를 입력해 주세요.")
        out.update(query=name, params=params, expect=expect if expect not in (None, "") else {})
    else:
        if kind != "definition":
            raise ValueError("판정 대상이 없어 저장하지 못했습니다. 결정표 또는 질의를 선택해 주세요.")
        words = expect if isinstance(expect, list) else [expect] if isinstance(expect, str) and expect.strip() else []
        words = [str(w).strip() for w in words if str(w).strip()]
        if not words and not out["keywords"]:
            raise ValueError("정답이 없어 저장하지 못했습니다. 정답 또는 키워드를 입력해 주세요.")
        out["expect"] = words[0] if len(words) == 1 else words
    return out


def _next_id(ids: list[str]) -> str:
    """The id a new question takes: the next number of the series the others are numbered in (Q1, Q2 → Q3)."""
    shaped = [m for m in (re.fullmatch(r"(.*?)(\d+)", i) for i in ids) if m]
    if not shaped:
        prefix, n, width = "Q", 1, 0
    else:
        prefix = Counter(m.group(1) for m in shaped).most_common(1)[0][0]
        nums = [m.group(2) for m in shaped if m.group(1) == prefix]
        width = max(len(x) for x in nums) if any(x.startswith("0") for x in nums) else 0
        n = max(int(x) for x in nums) + 1
    while f"{prefix}{str(n).zfill(width)}" in ids:
        n += 1
    return f"{prefix}{str(n).zfill(width)}"


def _as_asked(q) -> dict:
    return {"text": q.text, "decision": q.decision, "key": q.key, "query": q.query, "params": dict(q.params or {})}


def _asks(q: dict, cur) -> dict:
    """What the form asks, to compare with what the question asks now. The form does not show the parameters a
    decision question is decided with, so those count as unchanged."""
    out = {k: q.get(k) or ({} if k == "params" else "") for k in QUESTION_KEYS}
    if q.get("decision"):
        out["params"] = dict(cur.params or {})
    return out


@post("qa/question/save", needs="editor")
def question_save(s, a, who) -> dict:
    """One question as the form holds it, into the edits being written. A new one takes the next id when none is given.
    One that exists keeps what did not change; its words and what it asks cannot be changed in place, so they are taken
    out and written anew in one step (either both hold or neither)."""
    from ontlas.manage import EditError
    from ontlas.web.api import _edit_text

    ws = s._ws()
    onto = ws.composed().ontology
    qid = str(a.get("id") or "").strip()
    cur = next((q for q in onto.questions if q.id == qid), None)
    if a.get("new") and cur is not None:
        raise ValueError(f"질문 ID {qid}이(가) 이미 있어 저장하지 못했습니다. 다른 ID를 입력해 주세요.")
    q = _question(a, onto)
    try:
        if cur is None:
            qid = qid or _next_id([x.id for x in onto.questions])
            if not re.fullmatch(r"[\w.\-]{1,40}", qid):
                raise ValueError("질문 ID에 사용할 수 없는 문자가 있어 저장하지 못했습니다. 영문, 숫자, - _ . 만 입력해 주세요.")
            ws.apply("add_question", {"id": qid, **q})
        elif _asks(q, cur) != _as_asked(cur):
            if cur.decision and cur.params:  # add_question writes no parameters beside a decision: they would be lost
                raise ValueError("Parameter로 판정하는 질문이어서 질문과 판정 대상을 변경하지 못했습니다. "
                                 "정답, 판정 값, 평가 방법만 변경해 주세요.")
            ws.apply("delete_question", {"id": qid})
            try:
                ws.apply("add_question", {"id": qid, **q})
            except EditError:
                ws.undo()  # the question stays as it was
                ws._undone.clear()
                raise
        else:
            was = {"type": cur.kind, "holdout": cur.holdout, "grading": cur.grading, "keywords": list(cur.keywords),
                   "owner": cur.owner, "expect": cur.expect, "values": dict(cur.values or {})}
            now = {**{k: q[k] for k in META_KEYS}, "expect": q["expect"], "values": q.get("values") or {}}
            if now["grading"] == cur.graded_by and not cur.grading:
                now["grading"] = ""  # the grading it already has by what it asks is not written down
            changed = {k: v for k, v in now.items() if v != was[k]}
            if not cur.decision:
                changed.pop("values", None)
            if not changed:
                raise ValueError("변경된 내용이 없어 저장하지 못했습니다. 값을 변경한 뒤 다시 저장해 주세요.")
            ws.apply("update_question", {"id": qid, **changed})
    except EditError as e:
        raise ValueError(_edit_text(str(e))) from None
    return {"ok": True, "id": qid, "element": f"question:{qid}", **s.manage_state()}


@post("qa/question/try", needs="viewer")
def question_try(s, a, who) -> dict:
    """The question asked now, as the studio stands, without saving it: whether the answer is the one expected."""
    from ontlas.model import Question
    from ontlas.web.api import UNMEASURED, _gap_text, plain, said

    st = s.studio
    try:
        q = _question(a, st.onto)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    qs = Question(id=str(a.get("id") or "new"), text=q["text"], expect=q["expect"], query=q.get("query", ""),
                  decision=q.get("decision", ""), key=q.get("key", ""), params=q.get("params") or {}, type=q["type"],
                  holdout=q["holdout"], grading=q["grading"], keywords=q["keywords"], owner=q["owner"],
                  values=q.get("values") or {})
    held = st.onto.questions
    st.onto.questions = [qs]  # asked the way the check asks every question, on this one alone
    try:
        r = st.questions().results[0]
    finally:
        st.onto.questions = held
    return plain({"ok": True, "measured": not r.unmeasured, "note": UNMEASURED.get(r.unmeasured, ""),
                  "passed": None if r.unmeasured else r.passed, "expected": r.expected, "got": r.got,
                  "error": said(r.error) if r.error else "", "grounded": r.grounded,
                  "gaps": [_gap_text(g) for g in r.gaps], "diagnosis": r.diagnosis, "stages": r.stages})


# ---- the log of what was decided and approved ---------------------------------------------------------------------

@get("qa/decisions")
def decisions(s, a, who) -> dict:
    """Decisions, answers, action requests and their approvals, change requests and their approvals, and each
    measurement of the pipeline, newest first. Each row says what it stood on: the rules and the module versions."""
    st = s.studio
    rows: list[dict] = []
    label = s._label

    def versions(names: list[str]) -> list[dict]:
        out = []
        for ref in names or []:
            name, _, ver = str(ref).partition("@")
            out.append({"module": name, "label": label(name), "version": ver})
        return out

    for e in st.actions.audit:
        word, tone = EVENT.get(e.event, (e.event, ""))
        d = e.detail or {}
        target = s._obj_label(e.target) if e.target else ""
        if e.event == "decided":
            outs = d.get("outputs") if isinstance(d.get("outputs"), dict) else {}
            given = " · ".join(f"{k} {_word(v)}" for k, v in list(outs.items())[:3])
            text = " · ".join(x for x in (f"{target} {e.key}".strip(), s._element_label(f"decision:{e.action}"), given) if x)
        elif e.event == "answered":
            text = " → ".join(x for x in (str(d.get("question") or ""), str(d.get("answer") or "")[:120]) if x)
        else:
            what = st.onto.actions[e.action].label or e.action if e.action in st.onto.actions else e.action
            text = " · ".join(x for x in (what, f"{target} {e.key}".strip(), str(d.get("reason") or "")) if x)
        rows.append({"at": e.at, "kind": word, "tone": tone, "text": text, "by": e.actor,
                     "rules": [str(r).split(".", 1)[-1] for r in d.get("rules") or []], "versions": versions(e.versions)})
    for e in st.changes.audit:
        if e.get("event") not in CHANGE_EVENT:
            continue
        word, tone = CHANGE_EVENT[e["event"]]
        text = " · ".join(x for x in (f"{label(e.get('module', ''))} {e.get('version', '')}".strip(),
                                      str(e.get("reason") or ""), str(e.get("by") or "")) if x)
        rows.append({"at": e.get("at", ""), "kind": word, "tone": tone, "text": text, "by": e.get("by", ""),
                     "rules": [], "change": e.get("change", ""),
                     "versions": [{"module": e.get("module", ""), "label": label(e.get("module", "")),
                                   "version": e.get("version", "")}]})
    for e in s.events:
        if e.get("kind") == "measure":
            rows.append({"at": e["at"], "kind": "검증", "tone": "", "text": e["text"], "by": "", "rules": [], "versions": []})
    # newest first; of two written in the same second, the one written later comes first
    rows = [r for _, r in sorted(enumerate(rows), key=lambda p: (str(p[1]["at"]), p[0]), reverse=True)]
    limit = max(1, min(int(a.get("limit") or 50), 200))
    return {"rows": rows[:limit], "total": len(rows)}


def _word(v: Any) -> str:
    return "예" if v is True else "아니요" if v is False else "값 없음" if v is None else str(v)


# ---- which documents stand behind which Object ---------------------------------------------------------------------

@get("qa/evidence")
def evidence(s, a, who) -> dict:
    """Object by document: how many of an Object's Entities a document names (by the Entity, one of its properties or
    a term tied to it). Beside it, the Entities bound to a table of the source, the Objects and rules with nothing to
    stand on, and the Entities no table holds yet."""
    s._sync_space()
    st, o, sp = s.studio, s.studio.onto, s.space
    made = sp.concepts(o, s._terms())
    named: dict[str, set[str]] = {}  # document -> the Entities it names
    for (doc, _), found in made["sections"].items():
        for cid in found:
            c = made["concepts"].get(cid)
            kind, _, name = (c.element if c else "").partition(":")
            if kind in ("object", "property") and name.split(".")[0] in o.objects:
                named.setdefault(doc, set()).add(name.split(".")[0])
    held = {r["name"]: r for r in sp.document_rows()}
    mentions: Counter = Counter()
    for (doc, _), found in made["sections"].items():
        mentions[doc] += sum(found.values())
    docs = [{"name": n, "kind": d.get("kind", "") or "other", "kind_label": DOC_KIND.get(d.get("kind", ""), "문서"),
             "sections": len({t for (dn, t) in made["sections"] if dn == n}), "passages": held[n]["passages"],
             "indexed": held[n]["indexed"], "state": held[n]["state"], "state_label": DOC_STATE.get(held[n]["state"], ""),
             "fixed": n in sp.fixed, "entities": len(named.get(n, ())), "mentions": mentions[n]}
            for n, d in sp.documents().items()]
    connected = st.source_info()["connected"]
    objects, gaps = [], []
    for area in o.areas.values():
        ents = [t for t in o.objects.values() if t.area == area.name]
        if not ents:
            continue
        cells = {}
        for d in docs:
            hit = [t.label or t.name for t in ents if t.name in named.get(d["name"], ())]
            cells[d["name"]] = {"state": "all" if len(hit) == len(ents) else "some" if hit else "none", "count": len(hit),
                                "entities": hit[:8]}
        bound = [t for t in ents if t.table]
        every = {t.name for t in ents if any(t.name in v for v in named.values())}
        objects.append({"name": area.name, "label": area.label or area.name, "entities": len(ents), "cells": cells,
                        "bound": len(bound), "evidenced": len(every),
                        "source": "all" if bound and len(bound) == len(ents) else "some" if bound else "none"})
        lacking = [t.label or t.name for t in ents if t.name not in every]
        if docs and lacking:
            whole = len(lacking) == len(ents)
            gaps.append({"kind": "object", "object": area.name, "who": area.label or area.name,
                         "what": "자료 근거 없음" if whole else f"Entity {len(lacking)}개 자료 근거 없음",
                         "sub": ("자료에 언급된 Entity 없음" if whole else
                                 ", ".join(lacking[:4]) + (f" 외 {len(lacking) - 4}" if len(lacking) > 4 else ""))})
    for d in o.decisions.values():
        bare = [r.id for r in d.rules if not r.cite]
        if bare:
            gaps.append({"kind": "rule", "decision": d.name, "who": d.label or d.name, "what": f"근거 조항 없는 규칙 {len(bare)}개",
                         "sub": ", ".join(str(x) for x in bare[:5]) + (f" 외 {len(bare) - 5}" if len(bare) > 5 else "")})
    unbound = [{"name": t.name, "label": t.label or t.name,
                "area_label": (o.areas[t.area].label or t.area) if t.area in o.areas else "",
                "why": "키 미정" if not t.key else "소스 테이블 미정"}
               for t in o.objects.values() if not t.table]
    return {"connected": connected, "documents": docs, "objects": objects, "gaps": gaps,
            "unbound": unbound[:40], "unbound_total": len(unbound), "entities": len(o.objects)}
