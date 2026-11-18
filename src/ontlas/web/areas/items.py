"""What an item's own screens ask, whatever kind the item is: who reads it now, and how it came to read as it does.

An item is named as the definition names it: rule:<table>.<id>, decision:<name>, object:<name>, property:<object>.<name>,
link:<name>, area:<name>, action:<name>, query:<name>, question:<id>, function:<name>, role:<name>.
"""
from __future__ import annotations

import json
from typing import Any

from ontlas.web.routes import get

STATUS_WORD = {"pending": "검토 중", "approved": "배포", "rejected": "반려"}
# what a reader is, and the screen that shows it
READER_SCREEN = {"검증 질문": "check", "Action": "actions", "함수": "semrules", "접근 정책": "roles", "규칙 카드": "semrules",
                 "규칙": "semrules", "질의": "query", "계산 Property": "objects"}  # 규칙 카드 before 규칙: the longer word first


def _now_of(s, el: str) -> dict | None:
    from ontlas.review import _cards, _elements

    text = _elements(s.studio.onto, _cards(s.studio.composition)).get(el)
    return json.loads(text) if text is not None else None


def _entry(s, el: str, sides: list, **about: Any) -> dict:
    before, after = sides
    kind = "added" if before is None else "removed" if after is None else "changed"
    every = s._field_diff(el, None, after if after is not None else before, limit=0)  # the item as it read then, in words
    return {**about, "kind": kind, "before": before, "after": after, "fields": s._field_diff(el, before, after),
            "all": [{"label": f["label"], "value": f["said"][1] if f["said"][1] is not None else f["after"]} for f in every]}


@get("item/uses")
def uses(s, a, who) -> dict:
    """What reads the item now, grouped by what the reader is: the delete screen lists these before anything is asked."""
    el = str(a.get("element") or "")
    if ":" not in el:
        raise ValueError("항목 이름이 없어 사용처를 찾지 못했습니다.")
    return {"element": el, "label": s._element_label(el), "exists": _now_of(s, el) is not None, "uses": _groups(s, el)}


@get("item/uses/many")
def uses_many(s, a, who) -> dict:
    """What reads each of several items, for a list that says it on every row: by element, as item/uses groups it."""
    els = [e for e in str(a.get("elements") or "").split(",") if ":" in e][:200]
    return {"uses": {el: _groups(s, el) for el in els}}


def _groups(s, el: str) -> list[dict]:
    groups: dict[str, list[str]] = {}
    for r in s._readers(el):
        kind = next((k for k in READER_SCREEN if r.startswith(k + " ")), "")
        groups.setdefault(kind or "기타", []).append(r[len(kind):].strip() if kind else r)
    return [{"kind": k, "screen": READER_SCREEN.get(k, ""), "names": v} for k, v in groups.items()]


@get("item/history")
def history(s, a, who) -> dict:
    """Every change request that touched the item, newest first, each with what it read before and after, field by
    field. The edits not yet sent come first, as the request being written."""
    from ontlas.review import element_sides

    el = str(a.get("element") or "")
    if ":" not in el:
        raise ValueError("항목 이름이 없어 이력을 찾지 못했습니다.")
    entries = []
    for cr in s.studio.changes.requests.values():
        sides = ((cr.review or {}).get("elements") or {}).get(el)
        if sides is None:
            continue
        entries.append(_entry(s, el, sides, change=cr.id, version=cr.version, module=cr.module, module_label=s._change_label(cr),
                              status=cr.status, status_label=STATUS_WORD.get(cr.status, cr.status), at=cr.decided_at or cr.at,
                              by=cr.requested_by, decided_by=cr.decided_by, reason=cr.reason, deployed=cr.status == "approved"))
    entries.reverse()
    if s.studio.composition is not None:
        ws = s._ws()
        if ws.dirty:
            try:
                sides = element_sides(s.studio.onto, ws.composed().ontology).get(el)
            except Exception:  # edits that no longer compose have nothing to show for this item
                sides = None
            if sides is not None:
                entries.insert(0, _entry(s, el, sides, change="", version="", module="", module_label="", status="draft",
                                         status_label="작성 중", at="", by=s.who, decided_by="", reason="", deployed=False))
    # why a change was made is a note left on the item when it was saved. A note goes with the change request its edits
    # were filed in (none when they were thrown away), and with the edit not yet sent until then. A note kept before
    # notes knew their request belongs to the first change filed at or after it.
    for e in entries:
        e["notes"] = []
    filed = sorted((e for e in entries if e["at"]), key=lambda e: str(e["at"]))
    by_id = {e["change"]: e for e in entries if e["change"]}
    draft = entries[0] if entries and entries[0]["status"] == "draft" else None
    for n in sorted(s._notes().get(el, []), key=lambda n: str(n.get("at") or "")):
        if "change" in n:
            home = by_id.get(n["change"])
        elif draft is not None:
            home = draft
        else:
            at = str(n.get("at") or "")[:16]
            home = next((e for e in filed if str(e["at"])[:16] >= at), None)
        if home is not None:
            home["notes"].append({k: n.get(k) for k in ("at", "by", "text")})
    return {"element": el, "label": s._element_label(el), "now": _now_of(s, el), "entries": entries}
