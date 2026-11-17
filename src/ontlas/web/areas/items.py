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
READER_SCREEN = {"검증 질문": "check", "액션": "actions", "함수": "semrules", "역할": "roles", "결정": "semrules", "질의": "query",
                 "계산 속성": "objects"}


def _now_of(s, el: str) -> dict | None:
    from ontlas.review import _elements

    text = _elements(s.studio.onto).get(el)
    return json.loads(text) if text is not None else None


def _entry(s, el: str, sides: list, **about: Any) -> dict:
    before, after = sides
    kind = "added" if before is None else "removed" if after is None else "changed"
    return {**about, "kind": kind, "before": before, "after": after, "fields": s._field_diff(el, before, after)}


@get("item/uses")
def uses(s, a, who) -> dict:
    """What reads the item now, grouped by what the reader is: the delete screen lists these before anything is asked."""
    el = str(a.get("element") or "")
    if ":" not in el:
        raise ValueError("항목 이름이 없어 사용처를 찾지 못했습니다.")
    groups: dict[str, list[str]] = {}
    for r in s._readers(el):
        kind = next((k for k in READER_SCREEN if r.startswith(k + " ")), "")
        groups.setdefault(kind or "기타", []).append(r[len(kind):].strip() if kind else r)
    return {"element": el, "label": s._element_label(el), "exists": _now_of(s, el) is not None,
            "uses": [{"kind": k, "screen": READER_SCREEN.get(k, ""), "names": v} for k, v in groups.items()]}


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
    # why a change was made is a note left on the item when it was saved: each entry carries the notes written up to it
    notes = sorted(s._notes().get(el, []), key=lambda n: str(n.get("at") or ""))
    for i, e in enumerate(entries):
        older = entries[i + 1]["at"] if i + 1 < len(entries) else ""
        e["notes"] = [n for n in notes if str(n.get("at") or "") > str(older or "")
                      and (not e["at"] or str(n.get("at") or "") <= str(e["at"]))]
    return {"element": el, "label": s._element_label(el), "now": _now_of(s, el), "entries": entries}
