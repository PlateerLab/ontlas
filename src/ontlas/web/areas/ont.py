"""온톨로지 매니저의 Object · Entity · 상태 전이 · Relation 화면이 묻는 것.

An Entity's history is its own changes, its Properties' and the rule cards that apply to it in one list; a state
machine's history is the part of its Entity's that touched the states, in the words of its form. Any of these items is
set back to how a change left it as edits of the request being written.
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from ontlas.web.areas.items import STATUS_WORD
from ontlas.web.routes import get, post

RESTRICTION = ("limit", "duty", "ban")  # the rule cards that hold an Entity, as the Entity screen names them
CARD_PREFIX = "rule_card:"


def _applies(card: dict | None, name: str) -> bool:
    return any(r == f"object:{name}" or str(r).startswith(f"property:{name}.") for r in (card or {}).get("applies_to") or [])


def _card_rows(s, sides: dict[str, list]) -> list[dict]:
    """The rule cards a change added, took out or changed, each named as the Entity screen names it."""
    rows: list[dict] = []
    for el, (before, after) in sorted(sides.items()):
        if not el.startswith(CARD_PREFIX):
            continue
        card = after or before or {}
        word = f"{'Restriction' if card.get('type') in RESTRICTION or card.get('check') else '규칙'} {el[len(CARD_PREFIX):]}"
        if before is None or after is None:
            rows.append({"label": word, "before": None if before is None else before.get("statement") or "-",
                         "after": None if after is None else after.get("statement") or "-"})
            continue
        for f in s._field_diff(el, before, after):
            said = f.get("said") or [None, None]
            rows.append({"label": f"{word} · {f['label']}", "before": said[0] if said[0] is not None else f["before"],
                         "after": said[1] if said[1] is not None else f["after"]})
    return rows


def _said(v: Any) -> str:
    return "가능" if v is True else "불가" if v is False else str(v)  # a true or false result, as an Action's 전제조건 says it


def _guard_words(onto, name: str, guard: dict | None) -> str:
    """What must hold to take a move, as the screens say it: the rule table with each result it must give (its first
    true or false result is 결과, the reason 사유), or the true or false Property of the Entity that must be true."""
    from ontlas.check import _find_prop

    g = guard or {}
    if g.get("property"):
        p = _find_prop(onto, name, g["property"]) if name in onto.objects else None
        return f"{(p.label if p is not None else '') or g['property']} 예"
    if not g.get("decision"):
        return ""
    d = onto.decisions.get(g["decision"])
    first = next(iter(d.outputs), "") if d is not None else ""

    def out(k: str) -> str:
        if k == "reason":
            return "사유"
        return ("결과" if d.outputs[k] == "boolean" else d.label or d.name) if d is not None and k == first else k

    return " · ".join([(d.label or d.name) if d is not None else g["decision"],
                       *(f"{out(k)} {_said(v)}" for k, v in (g.get("expect") or {}).items())])


def _state_words(s, name: str, sm: dict | None) -> dict[str, str]:
    """A state machine as its form says it: the property, the states, the first state, the moves and what each move
    needs to be taken, values by label."""
    if not sm:
        return {}
    labels: dict[str, str] = {}
    onto = s.studio.onto
    t = onto.objects.get(name)
    p = t.properties.get(sm.get("property") or "") if t is not None else None
    if p is not None:
        labels = dict(p.labels or {})
    word = lambda v: labels.get(v) or v  # noqa: E731
    acts = {a.name: a.label or a.name for a in onto.actions.values()}
    moves = [f"{word(m.get('from'))} → {word(m.get('to'))}" + (f" · {acts.get(m['action'], m['action'])}" if m.get("action") else "")
             for m in sm.get("transitions") or []]
    guards = [f"{word(m.get('from'))} → {word(m.get('to'))} · {_guard_words(onto, name, m['guard'])}"
              for m in sm.get("transitions") or [] if m.get("guard")]
    return {"상태 Property": (p.label if p is not None else "") or sm.get("property") or "",
            "상태 값": ", ".join(word(x) for x in sm.get("states") or []),
            "초기 상태": word(sm.get("initial") or ""), "허용 전이": ", ".join(moves), **({"전이 조건": ", ".join(guards)} if guards else {})}


def _rows(s, name: str, sides: dict[str, list], states_only: bool) -> tuple[str, list[dict]]:
    """One change as it reads for an Entity: what happened to the Entity itself, to each of its Properties and to the
    rule cards that apply to it. For its state machine, only the states."""
    own = sides.get(f"object:{name}")
    kind = "changed"
    rows: list[dict] = []
    if own is not None:
        before, after = own
        kind = "added" if before is None else "removed" if after is None else "changed"
        if states_only:
            was, now = _state_words(s, name, (before or {}).get("states")), _state_words(s, name, (after or {}).get("states"))
            return kind, [{"label": k, "before": was.get(k) or None, "after": now.get(k) or None}
                          for k in ("상태 Property", "상태 값", "초기 상태", "허용 전이", "전이 조건") if was.get(k) != now.get(k)]
        for f in s._field_diff(f"object:{name}", before, after):
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
    return kind, rows + _card_rows(s, sides)


def _flat(d: Any, pre: str = "") -> list[dict]:
    out: list[dict] = []
    for k, v in (d or {}).items():
        if isinstance(v, dict) and v:
            out += _flat(v, f"{pre}{k}.")
        else:
            out.append({"label": f"{pre}{k}", "value": v})
    return out


def _draft_sides(s, cards: bool = False) -> dict[str, list] | None:
    """The elements the edits not yet sent change (with the rule cards when asked), or None when there are none."""
    from ontlas.review import _cards, element_sides

    if s.studio.composition is None:
        return None
    ws = s._ws()
    if not ws.dirty:
        return None
    try:
        comp = ws.composed()
        return element_sides(s.studio.onto, comp.ontology, (_cards(s.studio.composition), _cards(comp)) if cards else ((), ()))
    except Exception:  # edits that no longer compose have nothing to show
        return {}


@get("ont/history")
def history(s, a, who) -> dict:
    """How an Entity (kind=entity) or its state machine (kind=state) came to read as it does, newest first: every
    change request that touched it, one of its Properties or a rule card that applies to it, and the edits not yet sent
    as the request being written."""
    name, kind = str(a.get("name") or ""), str(a.get("kind") or "entity")
    if not name or kind not in ("entity", "state"):
        raise ValueError("Entity 이름이 없어 이력을 찾지 못했습니다. Entity를 선택한 뒤 다시 열어 주세요.")
    states_only = kind == "state"

    def entry(sides: dict, **about: Any) -> dict | None:
        mine = {el: v for el, v in sides.items() if el == f"object:{name}" or el.startswith(f"property:{name}.")
                or (not states_only and el.startswith(CARD_PREFIX) and (_applies(v[0], name) or _applies(v[1], name)))}
        if not mine:
            return None
        what, rows = _rows(s, name, mine, states_only)
        if states_only and not rows:
            return None
        own = mine.get(f"object:{name}") or [None, None]
        whole = (own[1] or own[0] or {})
        every = ([{"label": k, "value": v} for k, v in _state_words(s, name, whole.get("states")).items()] if states_only
                 else _flat(whole))
        return {**about, "kind": what, "rows": rows, "all": every}

    entries = []
    for cr in s.studio.changes.requests.values():
        e = entry((cr.review or {}).get("elements") or {}, change=cr.id, version=cr.version, status=cr.status,
                  status_label=STATUS_WORD.get(cr.status, cr.status), at=cr.decided_at or cr.at, by=cr.requested_by,
                  reason=cr.reason, deployed=cr.status == "approved")
        if e is not None:
            entries.append(e)
    entries.reverse()
    sides = _draft_sides(s, cards=not states_only)
    if sides is not None:
        e = entry(sides, change="", version="", status="draft", status_label="작성 중", at="", by=s.who, reason="",
                  deployed=False)
        if e is not None:
            entries.insert(0, e)
    # why a change was made is a note left on the Entity when it was saved: it goes with the change request its edits
    # were filed in, and with the edit not yet sent until then (as an item's own history does)
    for e in entries:
        e["notes"] = []
    filed = sorted((e for e in entries if e["at"]), key=lambda e: str(e["at"]))
    by_id = {e["change"]: e for e in entries if e["change"]}
    draft = entries[0] if entries and entries[0]["status"] == "draft" else None
    for n in sorted(s._notes().get(f"object:{name}", []), key=lambda n: str(n.get("at") or "")):
        if "change" in n:
            home = by_id.get(n["change"])
        elif draft is not None:
            home = draft
        else:
            at = str(n.get("at") or "")[:16]
            home = next((e for e in filed if str(e["at"])[:16] >= at), None)
        if home is not None:
            home["notes"].append({k: n.get(k) for k in ("at", "by", "text")})
    return {"name": name, "kind": kind, "label": s._element_label(f"object:{name}"), "entries": entries}


@get("ont/links")
def links(s, a, who) -> dict:
    """What the Relation list does not carry, as the edits being written leave it: where each Relation is said and how
    it is described."""
    onto = s._ws().composed().ontology if s.studio.composition is not None else s.studio.onto
    return {"links": {lk.name: {"cite": lk.cite, "description": lk.description} for lk in onto.links.values()}}


@get("ont/states")
def states(s, a, who) -> dict:
    """What the state machine list does not carry, as the edits being written leave it: what each move needs to be
    taken (its guard, as the definition holds it and in words)."""
    onto = s._ws().composed().ontology if s.studio.composition is not None else s.studio.onto
    return {"states": {t.name: [{"from": m.source, "to": m.target, "action": m.action, "guard": dict(m.guard),
                                 "said": _guard_words(onto, t.name, m.guard)} for m in t.states.transitions]
                       for t in onto.objects.values() if t.states}}


_COMPACT = re.compile(r"^([A-Za-z][A-Za-z0-9_-]{0,15}):([A-Za-z_][\w.-]*)$")  # shop:listPrice


def _vocab_of(iri: str) -> tuple[str, str]:
    """The vocabulary a name is aligned in and the name there: (schema.org, price), or (shop, listPrice)."""
    u = urlparse(iri)
    if u.scheme in ("http", "https") and u.netloc:
        return u.netloc.removeprefix("www."), u.fragment or u.path.rstrip("/").rsplit("/", 1)[-1]
    m = _COMPACT.match(iri)
    return (m.group(1), m.group(2)) if m else ("", iri)


@get("ont/vocab")
def vocab(s, a, who) -> dict:
    """How each Property stands beside the standard vocabularies, as the edits being written leave it: the vocabulary
    and the name it is aligned to (schema.org · price), and the prefix the definition writes its own names with, the
    one its terms' English names use most that is no standard's (shop:listPrice). A Property aligned to none is the
    definition's own."""
    from ontlas.check import all_props, find_prop

    if s.studio.composition is not None:
        _, comp, _ = s._lexicon_now()
        onto, terms = comp.ontology, list(comp.terms or [])
    else:
        onto, terms = s.studio.onto, []
    props: dict[str, dict] = {}
    for t in onto.objects.values():
        for name in all_props(onto, t.name):
            p = find_prop(onto, t.name, name)
            if p is not None and p.aligned:
                said, local = _vocab_of(str(p.aligned[0]))
                props[f"{t.name}.{name}"] = {"vocab": said, "name": local, "iri": str(p.aligned[0])}
    aligned = [str(u) for x in [*onto.areas.values(), *onto.objects.values(), *onto.links.values()] for u in x.aligned]
    standard = {k for v in [*(x["vocab"] for x in props.values()), *(_vocab_of(u)[0] for u in aligned)] for k in (v, v.split(".")[0])}
    prefixes = Counter(m.group(1) for x in terms if isinstance(x, dict)
                       if (m := _COMPACT.match(str(x.get("english") or "").strip())) and m.group(1) not in standard)
    return {"prefix": prefixes.most_common(1)[0][0] if prefixes else "", "properties": props}


# ---- 이 시점으로 되돌리기 -------------------------------------------------------------------------------------------

REVERT_KINDS = ("object", "entity", "state", "relation")
SAME = "선택한 시점의 값이 현재 값과 같아 되돌리지 못했습니다. 이전 시점을 선택해 주세요."


def _same(a: Any, b: Any) -> bool:
    empty = (None, "", [], {}, False)
    return json.dumps(None if a in empty else a, sort_keys=True, ensure_ascii=False) == \
        json.dumps(None if b in empty else b, sort_keys=True, ensure_ascii=False)


def _fields(want: dict, now: dict, keys: tuple, blank: dict | None = None) -> dict:
    """The fields that read otherwise at the point picked, each as it read then (a field it did not have, cleared)."""
    blank = blank or {}
    return {k: want.get(k, blank.get(k, "")) for k in keys if not _same(want.get(k), now.get(k))}


@post("ont/revert", needs="editor")
def revert(s, a, who) -> dict:
    """Set an Object (kind=object), an Entity with its Properties (entity), its state machine (state) or a Relation
    (relation) back to how an applied change request left it. Each part a later applied change or the edits being
    written touched reads again as it did then; it all goes in as edits of the request being written, or none does."""
    from ontlas.manage import AREA_FIELDS, LINK_FIELDS, OBJECT_FIELDS, PROP_FIELDS, EditError
    from ontlas.modules import Module
    from ontlas.review import _elements
    from ontlas.web.api import _edit_text

    kind, name, change = str(a.get("kind") or ""), str(a.get("name") or ""), str(a.get("change") or "")
    if kind not in REVERT_KINDS or not name or not change:
        raise ValueError("되돌릴 항목과 시점이 없어 되돌리지 못했습니다. 이력에서 시점을 선택해 주세요.")
    head = {"object": f"area:{name}", "relation": f"link:{name}"}.get(kind, f"object:{name}")
    mine = (lambda el: el == head or el.startswith(f"property:{name}.")) if kind == "entity" else (lambda el: el == head)

    changes = [(cr.id, cr.status, (cr.review or {}).get("elements") or {}) for cr in s.studio.changes.requests.values()]
    changes.reverse()
    draft = _draft_sides(s)
    if draft:
        changes.insert(0, ("", "draft", draft))
    at = next((i for i, c in enumerate(changes) if c[0] == change), None)
    if at is None or changes[at][1] != "approved" or not any(mine(el) for el in changes[at][2]):
        raise ValueError("배포된 변경이 아니어서 되돌리지 못했습니다. 배포된 시점을 선택해 주세요.")
    want: dict[str, Any] = {}  # each part as it read at the point picked: before the first applied change after it
    for _, status, sides in reversed(changes[:at]):
        if status not in ("approved", "draft"):
            continue
        for el, (before, _) in sides.items():
            if mine(el) and el not in want:
                want[el] = before
    ws = s._ws()
    onto = ws.composed().ontology
    every = _elements(onto)
    now = {el: json.loads(v) for el, v in every.items() if mine(el)}

    def inherited(prop: str) -> dict | None:  # the Property as the Entity's parents define it, where one of them does
        t = onto.objects.get(name)
        seen = {name}
        while t is not None and t.parent and t.parent not in seen:
            seen.add(t.parent)
            if f"property:{t.parent}.{prop}" in every:
                return json.loads(every[f"property:{t.parent}.{prop}"])
            t = onto.objects.get(t.parent)
        return None

    if head in want and want[head] is None:
        raise ValueError("선택한 시점에 항목이 없어 되돌리지 못했습니다. 다른 시점을 선택해 주세요.")
    was, cur = want.get(head), now.get(head) or {}
    edits: list[tuple[str, dict]] = []
    if was is not None and kind == "object":
        args = _fields(was, cur, AREA_FIELDS, {"aligned": [], "status": "active"})
        if args:
            edits.append(("update_area", {"name": name, **args}))
    if was is not None and kind == "relation":
        args = _fields(was, cur, LINK_FIELDS, {"required": False, "status": "active"})
        for k, end in (("source", "from"), ("target", "to")):
            if not _same(was.get(end), cur.get(end)):
                args[k] = was.get(end)
        if args:
            edits.append(("update_link", {"name": name, **args}))
    if was is not None and kind == "entity":
        flat = lambda d: {**d, "table": (d.get("source") or {}).get("table", "")}  # noqa: E731
        args = _fields(flat(was), flat(cur), OBJECT_FIELDS, {"status": "active"})
        if not _same(was.get("key"), cur.get("key")):
            args["key"] = was.get("key")
        if args:
            edits.append(("update_object", {"name": name, **args}))
    if was is not None and kind in ("entity", "state") and not _same(was.get("states"), cur.get("states")):
        sm = was.get("states")
        if not sm:
            edits.append(("delete_states", {"object": name}))
        else:
            edits.append(("update_states", {"object": name, "property": sm.get("property"), "states": sm.get("states"),
                                            "initial": sm.get("initial") or "",
                                            "transitions": [{**{k: m.get(k) for k in ("from", "to", "action")},  # all it said then
                                                             **{k: m.get(k) or {} for k in ("guard", "set", "call", "after")}}
                                                            for m in sm.get("transitions") or []]}))
    for el in sorted(x for x in want if x != head):  # an Entity's Properties
        prop, then, there = el.split(".", 1)[1], want[el], now.get(el)
        if then is None and there is not None:
            then = inherited(prop)  # a Property its parent gives reads as the parent says; else it goes
            if then is None:
                edits.append(("delete_property", {"object": name, "name": prop}))
                continue
        if then is not None and there is None:
            edits.append(("add_property", {"object": name, "name": prop, **then}))
        elif then is not None:
            args = _fields(then, there, PROP_FIELDS, {"required": False, "values": [], "labels": {}, "status": "active"})
            if args:
                edits.append(("update_property", {"object": name, "name": prop, **args}))
    if not edits:
        raise ValueError(SAME)
    snap, n = copy.deepcopy(ws.module.to_dict()), len(ws.edits)
    try:
        for op, args in edits:
            ws.apply(op, args)
    except EditError as e:
        ws.module, ws.edits, ws._before = Module.from_dict(snap), ws.edits[:n], ws._before[:n]
        raise ValueError(_edit_text(str(e))) from None
    return {"ok": True, "edits": [op for op, _ in edits], **s.manage_state()}
