"""온톨로지 매니저의 Object · Entity · 상태 전이 화면이 묻는 것.

An Entity's history is its own changes and its Properties' in one list; a state machine's history is the part of its
Entity's that touched the states.
"""
from __future__ import annotations

from typing import Any

from ontlas.web.areas.items import STATUS_WORD
from ontlas.web.routes import get


def _rows(s, name: str, sides: dict[str, list], states_only: bool) -> tuple[str, list[dict]]:
    """One change as it reads for an Entity: what happened to the Entity itself, then to each of its Properties."""
    own = sides.get(f"object:{name}")
    kind = "changed"
    rows: list[dict] = []
    if own is not None:
        before, after = own
        kind = "added" if before is None else "removed" if after is None else "changed"
        for f in s._field_diff(f"object:{name}", before, after):
            if states_only and not str(f["field"]).startswith("states"):
                continue
            rows.append({"field": f["field"], "label": f["label"], "before": f["before"], "after": f["after"]})
    if states_only:
        return kind, rows
    for el, (before, after) in sorted(sides.items()):
        if not el.startswith(f"property:{name}."):
            continue
        prop = el.split(".", 1)[1]
        word = ((after or before) or {}).get("label") or prop
        if before is None or after is None:
            rows.append({"label": f"Property {word}", "before": None if before is None else prop,
                         "after": None if after is None else prop})
            continue
        for f in s._field_diff(el, before, after):
            said = f.get("said") or [None, None]
            rows.append({"label": f"{word} · {f['label']}", "before": said[0] if said[0] is not None else f["before"],
                         "after": said[1] if said[1] is not None else f["after"]})
    return kind, rows


def _flat(d: Any, pre: str = "") -> list[dict]:
    out: list[dict] = []
    for k, v in (d or {}).items():
        if isinstance(v, dict) and v:
            out += _flat(v, f"{pre}{k}.")
        else:
            out.append({"label": f"{pre}{k}", "value": v})
    return out


@get("ont/history")
def history(s, a, who) -> dict:
    """How an Entity (kind=entity) or its state machine (kind=state) came to read as it does, newest first: every
    change request that touched it or one of its Properties, and the edits not yet sent as the request being written."""
    from ontlas.review import element_sides

    name, kind = str(a.get("name") or ""), str(a.get("kind") or "entity")
    if not name or kind not in ("entity", "state"):
        raise ValueError("Entity 이름이 없어 이력을 찾지 못했습니다. Entity를 선택한 뒤 다시 열어 주세요.")
    states_only = kind == "state"

    def entry(sides: dict, **about: Any) -> dict | None:
        mine = {el: v for el, v in sides.items() if el == f"object:{name}" or el.startswith(f"property:{name}.")}
        if not mine:
            return None
        what, rows = _rows(s, name, mine, states_only)
        if states_only and not rows:
            return None
        own = mine.get(f"object:{name}") or [None, None]
        whole = (own[1] or own[0] or {})
        return {**about, "kind": what, "rows": rows,
                "all": _flat({"states": whole.get("states")} if states_only else whole)}

    entries = []
    for cr in s.studio.changes.requests.values():
        e = entry((cr.review or {}).get("elements") or {}, change=cr.id, version=cr.version, status=cr.status,
                  status_label=STATUS_WORD.get(cr.status, cr.status), at=cr.decided_at or cr.at, by=cr.requested_by,
                  reason=cr.reason, deployed=cr.status == "approved")
        if e is not None:
            entries.append(e)
    entries.reverse()
    if s.studio.composition is not None:
        ws = s._ws()
        if ws.dirty:
            try:
                sides = element_sides(s.studio.onto, ws.composed().ontology)
            except Exception:  # edits that no longer compose have nothing to show for this Entity
                sides = {}
            e = entry(sides, change="", version="", status="draft", status_label="작성 중", at="", by=s.who, reason="",
                      deployed=False)
            if e is not None:
                entries.insert(0, e)
    notes = sorted(s._notes().get(f"object:{name}", []), key=lambda n: str(n.get("at") or ""))
    for i, e in enumerate(entries):
        older = entries[i + 1]["at"] if i + 1 < len(entries) else ""
        e["notes"] = [n for n in notes if str(n.get("at") or "") > str(older or "")
                      and (not e["at"] or str(n.get("at") or "") <= str(e["at"]))]
    return {"name": name, "kind": kind, "label": s._element_label(f"object:{name}"), "entries": entries}
