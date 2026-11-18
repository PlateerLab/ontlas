"""What the rules screens ask beyond the semantic view: the rules that wait for review and a reviewer's word on one,
and how a rule card or a named value came to read as it does.

A rule waits while its status is draft or review. A Standard or Custom one is approved or taken out here, as an edit
among the pending ones (it goes out with the next change request); an AXIOM one is settled by legal review, in its
own module, so it is shown and not decided here.
"""
from __future__ import annotations

import json
from typing import Any

from ontlas.web.routes import get, post
from ontlas.words import fix as with_particles

WAITING = ("draft", "review")
COUNTED = ("category", "source_kind", "policy_check")  # what the waiting rules are also counted by, as the draft file's tally is
CARD_WORD = {"id": "규칙 ID", "type": "유형", "statement": "규칙 이름", "applies_to": "적용 대상", "conditions": "조건",
             "result": "결과", "exceptions": "예외", "params": "기준값", "source": "근거", "owner": "담당자", "status": "상태",
             "legal_review": "법무 검토", "layer": "계층", "implements": "실행 위치", "check": "검사", "risk": "위반 시",
             "verification": "근거 확인", "category": "분류", "law": "대표 법령", "source_kind": "근거 종류",
             "policy_check": "정책서 대조", "related": "관련 대상"}
VALUE_WORD = {"label": "이름", "value": "값", "type": "자료형", "unit": "단위", "description": "설명", "cite": "근거", "min": "최솟값",
              "max": "최댓값", "owner": "담당자", "scale": "배율", "formula": "산식", "denominator": "분모", "time": "기준 시각",
              "params": "입력값"}
STATUS_WORD = {"pending": "검토 중", "approved": "배포", "rejected": "반려"}
SECTIONS = {"card": ("rule_cards", CARD_WORD), "parameter": ("parameters", VALUE_WORD), "metric": ("metrics", VALUE_WORD)}
TYPE_WORD = {"integer": "정수", "decimal": "소수", "number": "숫자", "float": "소수", "string": "문자열", "boolean": "참 · 거짓",
             "date": "날짜", "datetime": "일시"}
AGG_WORD = {"count": "건수", "sum": "합계", "avg": "평균", "min": "최솟값", "max": "최댓값"}
OP_WORD = {"eq": "같음", "ne": "다름", "lt": "미만", "lte": "이하", "gt": "초과", "gte": "이상", "not_null": "값 있음", "is_null": "값 없음"}


# ---- the rules that wait ----------------------------------------------------------------------------------------

def _areas_of(onto, card: dict) -> list[str]:
    """The Objects a rule is about, from what it applies to (an Entity's Object, a property's Entity's Object)."""
    out: list[str] = []
    for ref in card.get("applies_to") or []:
        kind, _, name = str(ref).partition(":")
        name = name.split(".")[0] if kind == "property" else name
        t = onto.objects.get(name) if kind in ("object", "property") else None
        area = onto.areas.get(t.area) if t is not None and t.area else onto.areas.get(name) if kind == "area" else None
        if area is not None and (area.label or area.name) not in out:
            out.append(area.label or area.name)
    return out


def _views(s) -> tuple[dict, dict, Any]:
    """The rule cards as applied and as the pending edits leave them, and the definition the pending edits leave."""
    from ontlas.semantic import semantic_view

    st = s.studio
    applied = st.composition
    before = semantic_view(st.onto, applied)
    comp = applied
    ws = s._ws() if applied is not None else None
    if ws is not None and ws.dirty:
        try:
            comp = ws.composed()
        except Exception:  # edits that no longer compose: the definition as applied
            comp = applied
    onto = comp.ontology if comp is not None else st.onto
    after = before if comp is applied else semantic_view(onto, comp)
    return before, after, onto


def _draft(c: dict, onto, state: str, editable: bool) -> dict:
    keep = ("ref", "id", "kind", "layer", "layer_label", "statement", "conditions", "result", "exceptions", "source", "owner",
            "status", "status_label", "legal_review", "legal_review_label", "verification", "risk", "type", "type_label",
            "category", "law", "source_kind", "policy_check", "related",
            "module", "module_label", "version", "decision", "decision_label", "rule")
    return {**{k: c.get(k) for k in keep}, "areas": _areas_of(onto, c), "state": state,
            "decidable": editable and state == "waiting" and c["layer"] != "axiom"}


def drafts_view(s) -> dict:
    """The rules that wait for review, those the pending edits approve, and those they take out."""
    from ontlas.decide.checks import decision_findings

    before, after, onto = _views(s)
    editable = s.studio.composition is not None
    was = {c["ref"]: c for c in before["cards"]}
    now = {c["ref"]: c for c in after["cards"]}
    rows = [_draft(c, onto, "waiting", editable) for c in after["cards"] if c["status"] in WAITING]
    rows += [_draft(c, onto, "approved", editable) for ref, c in now.items()
             if c["status"] == "approved" and ref in was and was[ref]["status"] in WAITING]
    rows += [_draft(c, s.studio.onto, "rejected", editable) for ref, c in was.items()
             if ref not in now and c["status"] in WAITING]
    waiting = [r for r in rows if r["state"] == "waiting"]
    tally: dict[str, dict[str, int]] = {"verification": {}, "area": {}, "module": {}, **{k: {} for k in COUNTED}}
    for r in waiting:
        for k in ("verification", *COUNTED):
            if r[k]:
                tally[k][r[k]] = tally[k].get(r[k], 0) + 1
        for a in r["areas"] or ["기타"]:
            tally["area"][a] = tally["area"].get(a, 0) + 1
        if r["module_label"]:
            tally["module"][r["module_label"]] = tally["module"].get(r["module_label"], 0) + 1
    ranked = {k: sorted(v.items(), key=lambda x: -x[1]) for k, v in tally.items()}
    draft_tables = {r["decision"] for r in rows if r["kind"] == "executable"}
    overlaps = [f for f in decision_findings(onto) if f.kind in ("overlap", "tie") and f.severity == "warning"
                and f.decision in draft_tables]
    conflicts = [c for c in onto.source_conflicts() if c.open]
    return {"drafts": rows,
            "counts": {k: sum(r["state"] == k for r in rows) for k in ("waiting", "approved", "rejected")},
            "axiom": sum(r["layer"] == "axiom" for r in waiting),
            "decidable": sum(r["decidable"] for r in waiting),
            "by_verification": [{"word": k, "count": n} for k, n in ranked["verification"]],
            "by_area": [{"word": k, "count": n} for k, n in ranked["area"]],
            **{f"by_{k}": [{"word": w, "count": n} for w, n in ranked[k]] for k in COUNTED},
            "modules": [k for k, _ in ranked["module"]],
            "parameters": len(onto.parameters),
            "overlaps": [{"decision": f.decision, "label": onto.decisions[f.decision].label or f.decision, "rules": list(f.rules)}
                         for f in overlaps],
            "conflicts": [{"id": c.id, "label": c.label or c.id, "sources": [a.source for a in c.answers]} for c in conflicts],
            "editable": editable}


@get("sem/drafts")
def drafts(s, a, who) -> dict:
    return drafts_view(s)


@get("sem/rule/without")
def rule_without(s, a, who) -> dict:
    """What taking a row out of its decision table changes, on the definition the pending edits leave: the rows on the
    other side of its conditions, the rows that would answer where it does, and where no row would."""
    from ontlas.decide.checks import without
    from ontlas.decide.words import input_label, where_words

    _, _, onto = _views(s)
    table = onto.decisions.get(str(a.get("decision") or ""))
    rid = str(a.get("rule") or "")
    if table is None or not any(r.id == rid for r in table.rules):
        raise ValueError("규칙을 찾을 수 없어 삭제 영향을 확인하지 못했습니다. 화면을 새로고침해 주세요.")
    out = without(table, rid, onto)
    label = lambda n: input_label(onto, table, n) if n in table.inputs else n  # noqa: E731
    return {**out, "opposite": [{"rule": x["rule"], "inputs": [label(n) for n in x["inputs"]]} for x in out["opposite"]],
            "takers": [{**x, "where": [where_words(onto, table, w) for w in x["where"]]} for x in out["takers"]],
            "gaps": [where_words(onto, table, w) for w in out["gaps"]]}


def _refused(e: Exception) -> str:
    from ontlas.web.api import _edit_text

    msg = str(e)
    if "is AXIOM; it is settled by legal review" in msg:
        return "AXIOM 후보여서 승인하거나 거절하지 못했습니다. 법무 검토로 확정해 주세요."
    if msg.startswith("a review of a rule card"):
        return "지원하지 않는 검토 결과여서 처리하지 못했습니다. 승인 또는 거절을 선택해 주세요."
    return _edit_text(msg)


@post("sem/draft/decide", needs="approver")
def decide(s, a, who) -> dict:
    """Approve a waiting rule (with what the reviewer corrected) or take it out. It becomes one of the pending edits."""
    from ontlas.manage import CARD_REVIEW_FIELDS, EditError

    ref, verdict = str(a.get("ref") or ""), str(a.get("verdict") or "")
    if verdict not in ("approve", "reject"):
        raise ValueError("지원하지 않는 검토 결과여서 처리하지 못했습니다. 승인 또는 거절을 선택해 주세요.")
    if s.studio.composition is None:
        raise ValueError("모듈로 구성된 온톨로지가 아니어서 규칙 초안을 검토하지 못했습니다. 모듈 라이브러리에서 모듈을 구성해 주세요.")
    fields = a.get("fields") if isinstance(a.get("fields"), dict) else {}
    kind, _, name = ref.partition(":")
    try:
        if kind == "card":
            given = {k: fields[k] for k in CARD_REVIEW_FIELDS if k in fields}
            s._ws().apply("review_rule_card", {"id": name, "verdict": verdict, **given})
        elif kind == "decision" and "#" in name:
            table, rid = name.split("#", 1)
            d = next((x for x in s.manage_state()["decisions"] if x["name"] == table), None)
            r = next((x for x in (d or {}).get("rules", []) if x["id"] == rid), None)
            if r is None:
                raise ValueError("규칙을 찾을 수 없어 처리하지 못했습니다. 화면을 새로고침해 주세요.")
            if verdict == "reject":
                s._ws().apply("delete_rule", {"decision": table, "id": rid})
            else:
                s._ws().apply("update_rule", {"decision": table, "id": rid, "when": r["when"], "then": r["then"],
                                              "cite": str(fields.get("source") or r.get("cite") or ""),
                                              "owner": str(fields.get("owner") or r.get("owner") or ""), "status": "approved"})
        else:
            raise ValueError("규칙을 찾을 수 없어 처리하지 못했습니다. 화면을 새로고침해 주세요.")
    except EditError as e:
        raise ValueError(_refused(e)) from None
    return {"ok": True, **drafts_view(s)}


# ---- how a rule card or a named value came to read as it does ------------------------------------------------------

def _given(module, section: str, name: str) -> dict | None:
    """What one version of a module says of an entry: its fields (marked _own where it defines the entry), the fields it
    gives another module's entry, or that it takes the entry out. None where it says nothing of it."""
    if module is None:
        return None
    if name in (module.remove.get(section) or []):
        return {"_removed": True}
    held = module.body.get(section)
    if section == "rule_cards":
        own = next((dict(c) for c in held or [] if isinstance(c, dict) and c.get("id") == name), None)
    else:
        own = (held or {}).get(name)
        own = None if own is None else dict(own) if isinstance(own, dict) else {"value": own}
    if own is not None:
        return {**own, "_own": True}
    patch = (module.extend.get(section) or {}).get(name)
    if patch is None:
        return None
    return dict(patch) if isinstance(patch, dict) else {"value": patch}


def _plain(v: Any) -> Any:
    if isinstance(v, bool):
        return "예" if v else "아니요"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def _prop_word(onto, entity: str, prop: str) -> str:
    from ontlas.check import _find_prop

    t = onto.objects.get(entity)
    head = (t.label or t.name) if t is not None else entity
    if not prop:
        return head
    p = _find_prop(onto, entity, prop) if t is not None else None
    return f"{head} · {(p.label or prop) if p is not None else prop}"


def _ref_word(onto, ref: str) -> str:
    from ontlas.semantic import _ref

    kind, _, name = str(ref).partition(":")
    if kind == "area":
        a = onto.areas.get(name)
        return f"Object {(a.label or a.name) if a is not None else name}"
    return _ref(onto, str(ref))["label"]


def _formula_word(onto, f: dict, base: Any = None) -> str:
    """A metric's formula or denominator as a person reads it: 주문상품 건수 · 조건 주문상품 · 상태 같음 RETURNED. A
    denominator reads the formula's names."""
    match = f.get("match") or (base.get("match") if isinstance(base, dict) else None) or {}

    def prop(ref: Any) -> str:
        alias, _, p = str(ref).partition(".")
        return _prop_word(onto, str(match.get(alias, alias)), p)

    value = f.get("value") or {}
    fn = next(iter(value), "")
    out = [f"{prop(value[fn])} {AGG_WORD.get(fn, fn)}"] if fn else []
    where = f.get("where")
    for c in (where.get("and") if isinstance(where, dict) and "and" in where else [where] if where else []):
        op, arg = next(iter(c.items())) if isinstance(c, dict) and len(c) == 1 else ("", None)
        if op in ("not_null", "is_null"):
            out.append(f"조건 {prop(arg)} {OP_WORD[op]}")
        elif op in OP_WORD and isinstance(arg, list) and len(arg) == 2:
            out.append(f"조건 {prop(arg[0])} {OP_WORD[op]} {_plain(arg[1])}")
        else:
            out.append(f"조건 {_plain(c)}")
    if f.get("edges"):
        out.append(f"경유 Relation {len(f['edges'])}개")
    if f.get("label"):
        out.append(str(f["label"]))
    return " · ".join(out)


def _said(onto, section: str, field: str, v: Any, entry: dict) -> Any:
    """A value of a change as a person reads it: the word for a code, the name of what a reference points at."""
    from ontlas.semantic import CARD_STATUS, CARD_TYPES, LAYER_LABEL, LEGAL_REVIEW

    if onto is None or v is None or v == "" or v == [] or v == {}:
        return v
    words = {"status": CARD_STATUS, "legal_review": LEGAL_REVIEW, "layer": LAYER_LABEL,
             "type": CARD_TYPES if section == "rule_cards" else TYPE_WORD}.get(field)
    if words is not None and isinstance(v, str):
        return words.get(v, v)
    if field in ("applies_to", "implements") and isinstance(v, list):
        return ", ".join(_ref_word(onto, r) for r in v)
    if field in ("conditions", "exceptions") and isinstance(v, list):
        return "; ".join(str(x) for x in v)
    if field == "params" and isinstance(v, dict):
        return " · ".join(f"@{k} {_plain(x)}" for k, x in v.items())
    if field in ("formula", "denominator") and isinstance(v, dict):
        return _formula_word(onto, v, entry.get("formula"))
    if field == "time" and isinstance(v, dict):
        alias, _, p = str(v.get("property") or "").partition(".")
        match = (entry["formula"].get("match") or {}) if isinstance(entry.get("formula"), dict) else {}
        return " · ".join(str(x) for x in (v.get("basis"), _prop_word(onto, str(match.get(alias, alias)), p) if p else "") if x)
    if field == "check" and isinstance(v, dict):
        what = f"@{v['parameter']}" if v.get("parameter") else _prop_word(onto, *(str(v.get("property") or "").split(".", 1) + [""])[:2])
        bound = [f"{v['min']} 이상" if v.get("min") is not None else "", f"{v['max']} 이하" if v.get("max") is not None else ""]
        return " ".join([what, " · ".join(x for x in bound if x)]).strip()
    return _plain(v)


def _rows(before: dict | None, after: dict | None, words: dict, onto, section: str, held: dict | None = None) -> list[dict]:
    """What differs, field by field, in words; `held` is the entry as the definition reads it, for the names a part
    given alone does not carry (the Entity a metric's time Property is on)."""
    a, b = before or {}, after or {}
    keys = [k for k in dict.fromkeys([*a, *b]) if not k.startswith("_") and a.get(k) != b.get(k)]
    return [{"field": k, "label": words.get(k, k), "before": _said(onto, section, k, a.get(k), {**(held or {}), **a}),
             "after": _said(onto, section, k, b.get(k), {**(held or {}), **b})} for k in keys]


def _all(entry: dict | None, words: dict, onto, section: str, held: dict | None = None) -> dict:
    e = {**(held or {}), **(entry or {})}
    return {words.get(k, k): _said(onto, section, k, v, e) for k, v in (entry or {}).items() if not k.startswith("_")}


def _composed(comp, onto, section: str, name: str) -> dict | None:
    """An entry as the whole definition reads it."""
    if section == "rule_cards":
        from ontlas.semantic import CARD_FIELDS

        c = next((c for c in getattr(comp, "cards", None) or [] if c["id"] == name), None)
        return None if c is None else {k: c[k] for k in CARD_FIELDS if c.get(k) not in (None, "", [], {})}
    held = (onto.to_dict().get(section) or {}).get(name)
    return dict(held) if isinstance(held, dict) else None


def _file_notes(entries: list[dict], notes: list[dict]) -> None:
    """Why a change was made is a note left when it was saved, so it belongs to the request filed next after it, or to
    the edits not yet sent. A note is timed to the minute: one of the minute the last request was filed in is read as
    written after it."""
    for e in entries:
        e["notes"] = []
    draft = entries[0] if entries and entries[0]["status"] == "draft" else None
    filed = sorted((e for e in entries if e is not draft), key=lambda e: str(e["at"]))
    for n in sorted(notes, key=lambda n: str(n.get("at") or "")):
        at = str(n.get("at") or "")[:16]
        if draft is not None and (not filed or at >= str(filed[-1]["at"])[:16]):
            draft["notes"].append(n)
            continue
        home = next((e for e in filed if str(e["at"])[:16] >= at), filed[-1] if filed else None)
        if home is not None:
            home["notes"].append(n)


@get("sem/history")
def history(s, a, who) -> dict:
    """Every change request that touched a rule card, a named value or a metric, newest first, with what its module
    said of it before and after; the edits not yet sent come first."""
    import yaml

    from ontlas.modules import Module

    kind, name = str(a.get("kind") or ""), str(a.get("name") or "")
    if kind not in SECTIONS or not name:
        raise ValueError("항목 이름이 없어 이력을 찾지 못했습니다.")
    section, words = SECTIONS[kind]
    st = s.studio
    lib = st.changes.store or st.library
    entries = []
    held = _composed(st.composition, st.onto, section, name) if st.composition is not None else None
    for cr in st.changes.requests.values():
        try:
            after = _given(Module.from_dict(yaml.safe_load(cr.text)), section, name)
        except Exception:  # a request whose text no longer reads has nothing to say of this entry
            continue
        base = (cr.review or {}).get("base_version") or ""
        try:
            before = _given(lib.get(cr.module, base), section, name) if lib is not None and base and base in lib.versions(cr.module) else None
        except Exception:
            before = None
        if after == before:
            continue
        # taken out: said so, or no longer written in the module that defined it
        gone = bool(after and after.get("_removed")) or (after is None and bool(before and before.get("_own")))
        entries.append({"change": cr.id, "version": cr.version, "module_label": s._change_label(cr), "status": cr.status,
                        "status_label": STATUS_WORD.get(cr.status, cr.status), "at": cr.decided_at or cr.at, "by": cr.requested_by,
                        "reason": cr.reason, "deployed": cr.status == "approved",
                        "kind": "removed" if gone else "added" if before is None else "changed",
                        "fields": _rows(before, None if gone else after, words, st.onto, section, held),
                        "all": {} if gone else _all(after, words, st.onto, section, held)})
    entries.reverse()
    comp = st.composition
    if comp is not None:
        ws = s._ws()
        if ws.dirty:
            try:
                pending = ws.composed()
                was, now = _composed(comp, st.onto, section, name), _composed(pending, pending.ontology, section, name)
                said = pending.ontology
            except Exception:
                was = now = said = None
            if was != now:
                entries.insert(0, {"change": "", "version": "", "module_label": "", "status": "draft", "status_label": "작성 중",
                                   "at": "", "by": s.who, "reason": "", "deployed": False,
                                   "kind": "removed" if now is None else "added" if was is None else "changed",
                                   "fields": _rows(was, now, words, said, section),
                                   "all": _all(now, words, said, section)})
    _file_notes(entries, s._notes().get(f"{'rule_card' if kind == 'card' else kind}:{name}", []))
    return {"kind": kind, "name": name, "now": held, "entries": entries}


AXIOM_CARD_FIELDS = ("type", "statement", "applies_to", "conditions", "result", "exceptions", "params", "source", "owner", "status",
                     "category", "law", "source_kind", "policy_check", "related")


def _propose(s, body: dict) -> dict:
    """Propose a module the server wrote from the library's own copy, as a module a person sends is proposed. It is
    not a pasted file, so it is not held to a pasted file's size: the AXIOM module of a whole law runs past 48KB."""
    from ontlas.modules import Module
    from ontlas.web.api import _next_version

    m = Module.from_dict(body)
    issues = s._module_issues(m)
    if issues:
        raise ValueError("정의 검사에서 오류가 발견되어 변경을 요청하지 못했습니다. " + "; ".join(issues[:5]))
    lib = s.studio.changes.store or s.studio.library
    if m.version in lib.versions(m.name):
        if {**lib.get(m.name).to_dict(), "version": ""} == {**m.to_dict(), "version": ""}:
            raise ValueError("바뀐 내용이 없어 변경을 요청하지 못했습니다. 정의를 수정한 뒤 다시 요청해 주세요.")
        m.version = _next_version(lib.versions(m.name))
    cr = s.studio.changes.propose(m, by=s.who)
    s._note("change", f"{m.label or m.name} {m.version} 변경 요청을 등록했습니다.")  # passing is in the request
    return s._change(cr)


@post("sem/axiom/card", needs="editor")
def axiom_card(s, a, who) -> dict:
    """A change to an AXIOM card, or its removal, filed as a change request to the module that defines it. The edits
    waiting in the workspace never change an AXIOM card: it is settled where it is written, and approved by a person."""
    import yaml

    cid = str(a.get("id") or "")
    comp = s.studio.composition
    card = next((c for c in (comp.cards if comp else []) if c["id"] == cid), None)
    if card is None:
        raise ValueError(with_particles(f"규칙 카드 '{cid}'을(를) 찾지 못해 처리하지 못했습니다. 화면을 새로고침해 주세요."))
    if card["layer"] != "axiom":
        raise ValueError(with_particles(f"규칙 카드 '{cid}'은(는) AXIOM 규칙이 아니어서 이 경로로 바꾸지 못했습니다. 규칙 화면에서 편집해 주세요."))
    module = yaml.safe_load(s.module_source(card["module"])["yaml"]) or {}
    cards = module.get("rule_cards") or []
    own = next((c for c in cards if isinstance(c, dict) and c.get("id") == cid), None)
    if own is None:
        raise ValueError(f"규칙 카드 '{cid}'의 정의를 모듈 '{card['module']}'에서 찾지 못해 처리하지 못했습니다.")
    if a.get("remove"):
        module["rule_cards"] = [c for c in cards if c is not own]
    else:
        fields = a.get("fields") if isinstance(a.get("fields"), dict) else {}
        for k in AXIOM_CARD_FIELDS:
            if k in fields:
                if fields[k] in (None, "", [], {}):
                    own.pop(k, None)
                else:
                    own[k] = fields[k]
    return {"ok": True, "change": _propose(s, module), "module": card["module"]}

