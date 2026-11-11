"""Rules in three layers, and the record of each rule.

A decision rule belongs to the layer of the module that wrote it: an `axiom` module writes AXIOM rules (laws, arithmetic
integrity: always true, nothing below can change or remove them), a `customer` module and the page's workspace write
Custom rules, and every other module writes Standard ones. A table checks its AXIOM rules first.

A rule card is the record of one rule: what it says, what it applies to, its conditions, result and exceptions, where it
comes from, who answers for it and how far it is reviewed. Many rules run as decision rows; a card can also state a rule
that something else carries out (a computation, a state transition, what a screen shows) and point at it. An AXIOM card
may carry a check on a named value (a parameter): a composition whose final value breaks it does not hold.
"""
from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

LAYERS = ("axiom", "custom", "standard")  # the order a decision checks them in
LAYER_LABEL = {"axiom": "AXIOM", "custom": "Custom", "standard": "Standard"}
LAYER_TEXT = {
    "axiom": "법령 · 정합성 규칙입니다. 판정에서 가장 먼저 적용하며 Custom · Standard 모듈과 관리 변경으로 변경할 수 없습니다.",
    "custom": "고객사 모듈과 관리 변경에서 정의한 규칙입니다. Standard 규칙보다 먼저 적용합니다.",
    "standard": "공통 기본 규칙입니다.",
}
CARD_TYPES = {"decide": "판정", "compute": "계산", "transition": "전이", "restore": "복원", "order": "순서",
              "display": "표시", "watch": "감시"}
CARD_STATUS = {"draft": "초안", "review": "검토 중", "approved": "승인"}
LEGAL_REVIEW = {"none": "해당 없음", "pending": "검토 대기", "done": "검토 완료"}
CARD_FIELDS = ("id", "type", "statement", "applies_to", "conditions", "result", "exceptions", "params", "source", "owner",
               "status", "legal_review", "layer", "implements", "check")
STATE_WORD = {"fired": "적용", "passed": "통과", "none": "해당 없음", "held": "선행 규칙 적용"}
REF_KINDS = ("decision", "function", "action", "object", "property", "link", "parameter", "query", "metric", "role",
             "states")
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REF = re.compile(r"^([a-z_]+):(\S+)$")
_NAMED = re.compile(r"@([A-Za-z_][A-Za-z0-9_]*)")


class CardError(ValueError):
    """A rule card that cannot be read; the message names the card and the field."""


def layer_of(kind: str) -> str:
    """The layer a module of this kind writes rules in."""
    return "axiom" if kind == "axiom" else "custom" if kind == "customer" else "standard"


def _strings(v: Any) -> list[str]:
    if v in (None, "", []):
        return []
    return [str(x) for x in v] if isinstance(v, (list, tuple)) else [str(v)]


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _num(v: Any) -> str:
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def card_spec(card: Any, kind: str = "domain") -> dict:
    """A card as written in a module, read and checked; `kind` is the kind of the module writing it."""
    if not isinstance(card, dict):
        raise CardError("a rule card is a mapping with an id")
    cid = str(card.get("id") or "")
    if not _ID.match(cid):
        raise CardError(f"rule card id '{cid}' must be letters, digits, _ and - starting with a letter")
    unknown = sorted(set(card) - set(CARD_FIELDS))
    if unknown:
        raise CardError(f"rule card '{cid}': unknown fields {unknown}; use {list(CARD_FIELDS)}")
    kind_of = str(card.get("type") or "")
    if kind_of not in CARD_TYPES:
        raise CardError(f"rule card '{cid}': type '{kind_of}' is not one of {tuple(CARD_TYPES)}")
    statement = " ".join(str(card.get("statement") or "").split())
    if not statement:
        raise CardError(f"rule card '{cid}': give a statement")
    status = str(card.get("status") or "draft")
    if status not in CARD_STATUS:
        raise CardError(f"rule card '{cid}': status '{status}' is not one of {tuple(CARD_STATUS)}")
    legal = str(card.get("legal_review") or "none")
    if legal not in LEGAL_REVIEW:
        raise CardError(f"rule card '{cid}': legal review '{legal}' is not one of {tuple(LEGAL_REVIEW)}")
    own = layer_of(kind)
    layer = str(card.get("layer") or own)
    if layer not in LAYERS:
        raise CardError(f"rule card '{cid}': layer '{layer}' is not one of {LAYERS}")
    if layer == "axiom" and own != "axiom":
        raise CardError(f"rule card '{cid}': layer axiom is written only by an axiom module")
    implements = _strings(card.get("implements"))
    bad = [r for r in implements if not _REF.match(r)]
    if bad:
        raise CardError(f"rule card '{cid}': implements '{bad[0]}' is not kind:name")
    params = card.get("params") or {}
    if not isinstance(params, dict):
        raise CardError(f"rule card '{cid}': params is a mapping of names to values")
    check = card.get("check") or None
    if check is not None:
        if not isinstance(check, dict) or set(check) - {"parameter", "min", "max"} or \
                not _NAME.match(str(check.get("parameter") or "")) or \
                not any(_number(check.get(k)) for k in ("min", "max")) or \
                any(check.get(k) is not None and not _number(check[k]) for k in ("min", "max")):
            raise CardError(f"rule card '{cid}': check needs a parameter and a numeric min or max")
        check = {k: check[k] for k in ("parameter", "min", "max") if check.get(k) is not None}
    return {"id": cid, "type": kind_of, "statement": statement, "applies_to": _strings(card.get("applies_to")),
            "conditions": _strings(card.get("conditions")), "result": str(card.get("result") or ""),
            "exceptions": _strings(card.get("exceptions")), "params": dict(params), "source": str(card.get("source") or ""),
            "owner": str(card.get("owner") or ""), "status": status, "legal_review": legal, "layer": layer,
            "implements": implements, "check": check}


# ---- composition ------------------------------------------------------------------------------------------------

def define_cards(cards: dict[str, dict], m, origin: dict) -> None:
    """The cards a module writes, after those of the modules it composes after."""
    from ontlas.modules import ModuleError

    items = m.body.get("rule_cards") or []
    if not isinstance(items, list):
        raise ModuleError(f"{m.key}: rule_cards is a list of cards")
    for raw in items:
        try:
            spec = card_spec(raw, m.kind)
        except CardError as e:
            raise ModuleError(f"{m.key} {e}") from None
        cid = spec["id"]
        if cid in cards:
            raise ModuleError(f"{m.key} defines rule card '{cid}', already defined by {cards[cid]['module']}; "
                              "extend it instead")
        cards[cid] = {**spec, "module": m.name, "version": m.version}
        origin[f"rule_card:{cid}"] = m.name


def extend_cards(cards: dict[str, dict], m, patches: dict, touched: dict) -> None:
    """Fields a later module gives a card; an AXIOM card takes them only from an axiom module."""
    from ontlas.modules import ModuleError

    for cid, patch in (patches or {}).items():
        cur = cards.get(cid)
        if cur is None:
            raise ModuleError(f"{m.key} extends rule card '{cid}', which no attached module defines")
        if cur["layer"] == "axiom" and m.kind != "axiom":
            raise ModuleError(f"{m.key} changes AXIOM rule card '{cid}'")
        merged = {k: v for k, v in cur.items() if k in CARD_FIELDS}
        merged.update(dict(patch or {}))
        merged["id"] = cid
        try:
            spec = card_spec(merged, m.kind)
        except CardError as e:
            raise ModuleError(f"{m.key} {e}") from None
        cards[cid] = {**spec, "module": cur["module"], "version": cur["version"]}
        touched.setdefault(f"rule_card:{cid}", []).append(m.name)


def remove_cards(cards: dict[str, dict], m, ids: list, removed: dict) -> None:
    from ontlas.modules import ModuleError

    for cid in ids or []:
        cur = cards.get(cid)
        if cur is None:
            raise ModuleError(f"{m.key} removes rule card '{cid}', which is not there")
        if cur["layer"] == "axiom" and m.kind != "axiom":
            raise ModuleError(f"{m.key} removes AXIOM rule card '{cid}'")
        del cards[cid]
        removed[f"rule_card:{cid}"] = m.name


def value_setters(modules: list) -> dict[str, str]:
    """Each named value, and the module that set the value it has: the one defining it, or the last to give it one."""
    out: dict[str, str] = {}
    for m in modules:
        for k in m.body.get("parameters") or {}:
            out[k] = m.name
        for k, patch in ((m.extend or {}).get("parameters") or {}).items():
            if not isinstance(patch, dict) or "value" in patch:
                out[k] = m.name
    return out


def _bounds(f: dict) -> str:
    unit = f.get("unit") or ""
    low, high = f.get("min"), f.get("max")
    if low is not None and high is not None:
        return f"{_num(low)}~{_num(high)}{unit}"
    return f"{_num(low)}{unit} 이상" if low is not None else f"{_num(high)}{unit} 이하"


def check_cards(cards: list[dict], onto, modules: list) -> list[dict]:
    """Every card's check on the final named values. An AXIOM card's check that fails stops the composition (see
    `violations`); any other is for a person to look at."""
    setters = value_setters(modules)
    names = {m.name: m.label or m.name for m in modules}
    out = []
    for c in cards:
        chk = c.get("check")
        if not chk:
            continue
        name = chk["parameter"]
        p = onto.parameters.get(name)
        by = setters.get(name, "")
        f = {"card": c["id"], "layer": c["layer"], "module": c["module"], "parameter": name,
             "label": (p.label or name) if p is not None else name, "unit": p.unit if p is not None else "",
             "value": p.value if p is not None else None, "min": chk.get("min"), "max": chk.get("max"),
             "set_by": by, "set_by_label": names.get(by, by), "blocking": c["layer"] == "axiom", "passed": None,
             "failed": ""}
        if p is None:
            f["said"] = f"기준값 {name}이(가) 정의에 없어 확인하지 못했습니다."
        elif not _number(p.value):
            f.update(passed=False, failed="type", said=f"{f['label']} 값 '{p.value}'이(가) 숫자가 아닙니다.")
        elif f["min"] is not None and p.value < f["min"]:
            f.update(passed=False, failed="min", said=f"{f['label']} {_num(p.value)}{f['unit']} · {_bounds(f)}이어야 합니다.")
        elif f["max"] is not None and p.value > f["max"]:
            f.update(passed=False, failed="max", said=f"{f['label']} {_num(p.value)}{f['unit']} · {_bounds(f)}여야 합니다.")
        else:
            f.update(passed=True, said=f"{f['label']} {_num(p.value)}{f['unit']} · {_bounds(f)} 충족")
        out.append(f)
    return out


def violation(f: dict) -> str:
    """A failed AXIOM check as a composition issue: the card, the value, the bound and who set the value."""
    head = f"AXIOM {f['card']}: {f['parameter']} ({f['label']}) is {_num(f['value'])}"
    by = f"set by {f['set_by'] or '-'} ({f['set_by_label'] or '-'})"
    if f["failed"] == "min":
        return f"{head}, below the minimum {_num(f['min'])}; {by}"
    if f["failed"] == "max":
        return f"{head}, above the maximum {_num(f['max'])}; {by}"
    return f"{head}, which is not a number; {by}"


def violations(checks: list[dict]) -> list[str]:
    return [violation(f) for f in checks if f["blocking"] and f["passed"] is False]


# ---- one decision, layer by layer --------------------------------------------------------------------------------

def decision_path(table, matched: list[str], held: list[str], labels: dict[str, str] | None = None) -> dict:
    """What each layer did for one decision, AXIOM first: how many rules it has, which fired, which held but an earlier
    rule decided, or that none applied (an AXIOM layer that none of its rules stopped is passed). `source` is the rule
    that gave the answer, with its layer and the module and version that wrote it."""
    labels = labels or {}
    by = {r.id: r for r in table.rules}
    fired = [i for i in (list(matched[:1]) if table.hit_policy in ("first", "priority") else list(matched)) if i in by]
    layers = []
    for layer in LAYERS:
        ids = [r.id for r in table.rules if r.layer == layer]
        hit = [i for i in fired if by[i].layer == layer]
        rest = [i for i in held if i in ids and i not in hit]
        state = "fired" if hit else "held" if rest else "passed" if layer == "axiom" else "none"
        layers.append({"layer": layer, "label": LAYER_LABEL[layer], "rules": len(ids), "fired": hit, "held": rest,
                       "state": state, "said": STATE_WORD[state]})
    top = by[fired[0]] if fired else None
    source = None if top is None else {
        "rule": top.id, "layer": top.layer, "layer_label": LAYER_LABEL.get(top.layer, top.layer), "module": top.module,
        "module_label": labels.get(top.module, top.module), "version": top.version, "cite": top.cite or table.cite}
    text = " › ".join(f"{x['label']} {', '.join(x['fired'])} {x['said']}" if x["fired"] else f"{x['label']} {x['said']}"
                      for x in layers)
    return {"layers": layers, "source": source, "layer": top.layer if top else "", "text": text}


# ---- what the page shows ------------------------------------------------------------------------------------------

def _ref(onto, ref: str) -> dict:
    """An element a card points at, by name, and whether the definition has it."""
    m = _REF.match(ref)
    kind, name = (m.group(1), m.group(2)) if m else ("", ref)
    label, found = name, False
    if kind == "decision":
        table, _, rule = name.partition("#")
        d = onto.decisions.get(table)
        found = d is not None and (not rule or any(r.id == rule for r in d.rules))
        label = f"{(d.label or table) if d else table}{f' · {rule}' if rule else ''}"
    elif kind == "property" and "." in name:
        t, p = name.split(".", 1)
        o = onto.objects.get(t)
        found = o is not None and p in o.properties
        label = f"{(o.label or t) if o else t} · {(o.properties[p].label or p) if found else p}"
    elif kind == "states":
        o = onto.objects.get(name)
        found, label = bool(o is not None and o.states), f"{(o.label or name) if o else name} 상태 전이"
    else:
        section = {"function": onto.functions, "action": onto.actions, "object": onto.objects, "link": onto.links,
                   "parameter": onto.parameters, "query": onto.queries, "metric": onto.metrics,
                   "role": onto.roles}.get(kind)
        if section is not None and name in section:
            found, label = True, getattr(section[name], "label", "") or name
    return {"ref": ref, "kind": kind, "label": label, "found": found}


def _card_row(c: dict, onto, labels: dict, extended: list[str]) -> dict:
    return {**{k: c[k] for k in CARD_FIELDS}, "kind": "stated", "ref": f"card:{c['id']}",
            "type_label": CARD_TYPES[c["type"]], "status_label": CARD_STATUS[c["status"]],
            "legal_review_label": LEGAL_REVIEW[c["legal_review"]], "layer_label": LAYER_LABEL[c["layer"]],
            "module": c["module"], "module_label": labels.get(c["module"], c["module"]), "version": c["version"],
            "extended_by": [labels.get(x, x) for x in extended],
            "implements": [_ref(onto, r) for r in c["implements"]], "used_by": []}


def _row_cards(onto, labels: dict, stated: list[dict]) -> list[dict]:
    """One card for each decision row: what it says in words, who wrote it, what reads the decision."""
    from ontlas.decide.table import answer
    from ontlas.decide.words import cell_words, input_label, labels_of, rule_sentence, unit_of, verdict

    out = []
    for t in onto.decisions.values():
        users = [f"action:{a.name}" for a in onto.actions.values() if any(c.decision == t.name for c in a.criteria)]
        users += [f"function:{f.name}" for f in onto.functions.values() if f.decision == t.name]
        named = t.named
        target = onto.objects.get(t.target)
        for pos, r in enumerate(t.rules):
            here = f"decision:{t.name}#{r.id}"
            cards = [c for c in stated if here in c["implements"] or f"decision:{t.name}" in c["implements"]]
            conditions = []
            for k, cell in r.when.items():
                said = cell_words(cell, named, unit=unit_of(onto, t, k), labels=labels_of(onto, t, k)) \
                    if k in t.inputs else str(cell)
                if said != "-":
                    conditions.append(f"{input_label(onto, t, k) if k in t.inputs else k} {said}")
            gives = answer(t, r)  # with the named values in force: "반품기간 {@return_window_days}일" reads 7일
            word, _ = verdict(t, gives)
            reason = [str(v) for v in gives.values() if isinstance(v, str)]
            text = f"{r.when} {r.then}"
            status = r.status or t.status or "approved"
            legal = next((c["legal_review"] for c in cards), "none")
            out.append({
                "id": f"{t.name}#{r.id}", "kind": "executable", "ref": here, "type": "decide",
                "type_label": CARD_TYPES["decide"], "decision": t.name, "decision_label": t.label or t.name,
                "rule": r.id, "position": pos, "hit_policy": t.hit_policy,
                "statement": rule_sentence(onto, t, replace(r, then=gives)),
                "applies_to": [f"object:{t.target}"] if target is not None else [],
                "applies_to_labels": [target.label or t.target] if target is not None else [],
                "conditions": conditions, "result": " · ".join(dict.fromkeys([word, *reason])), "exceptions": [],
                "params": {n: named[n] for n in _NAMED.findall(text) if n in named},
                "source": r.cite or t.cite, "owner": r.owner or t.owner, "status": status,
                "status_label": CARD_STATUS.get(status, status), "legal_review": legal,
                "legal_review_label": LEGAL_REVIEW[legal], "layer": r.layer, "layer_label": LAYER_LABEL.get(r.layer, r.layer),
                "module": r.module, "module_label": labels.get(r.module, r.module), "version": r.version,
                "extended_by": [], "implements": [], "check": None,
                "used_by": [_ref(onto, u) for u in users] + [{"ref": f"card:{c['id']}", "kind": "card",
                                                              "label": c["statement"], "found": True} for c in cards]})
    return out


def semantic_view(onto, comp=None) -> dict:
    """The layers, every rule card (stated, and one per decision row), the named values with the AXIOM bounds on them,
    and how the checks came out, for the page and the command line."""
    labels = {m.name: m.label or m.name for m in comp.modules} if comp is not None else {}
    stated_raw = list(getattr(comp, "cards", None) or [])
    touched = comp.touched if comp is not None else {}
    stated = [_card_row(c, onto, labels, touched.get(f"rule_card:{c['id']}", [])) for c in stated_raw]
    cards = stated + _row_cards(onto, labels, stated_raw)
    checks = list(getattr(comp, "checks", None) or [])
    layers = []
    for i, layer in enumerate(LAYERS):
        writers = [c["module"] for c in cards if c["layer"] == layer and c["module"]]
        mods = [{"name": m.name, "label": m.label or m.name, "version": m.version, "kind": m.kind}
                for m in (comp.modules if comp is not None else []) if m.name in writers]
        layers.append({"layer": layer, "label": LAYER_LABEL[layer], "description": LAYER_TEXT[layer], "order": i + 1,
                       "rules": sum(c["kind"] == "executable" and c["layer"] == layer for c in cards),
                       "cards": sum(c["kind"] == "stated" and c["layer"] == layer for c in cards), "modules": mods})
    setters = value_setters(comp.modules) if comp is not None else {}
    parameters = []
    for p in onto.parameters.values():
        bound = [c for c in stated_raw if c["layer"] == "axiom" and (c.get("check") or {}).get("parameter") == p.name]
        lows = [c["check"]["min"] for c in bound if "min" in c["check"]]
        highs = [c["check"]["max"] for c in bound if "max" in c["check"]]
        owner = comp.owner(f"parameter:{p.name}") if comp is not None else ""
        by = setters.get(p.name, owner)
        parameters.append({
            "name": p.name, "label": p.label or p.name, "value": p.value, "type": p.type, "unit": p.unit, "min": p.min,
            "max": p.max, "cite": p.cite, "module": owner, "module_label": labels.get(owner, owner), "set_by": by,
            "set_by_label": labels.get(by, by),
            "axiom": {"min": max(lows) if lows else None, "max": min(highs) if highs else None,
                      "cards": [c["id"] for c in bound]} if bound else None})
    return {"layers": layers, "types": [{"type": k, "label": v} for k, v in CARD_TYPES.items()],
            "statuses": [{"status": k, "label": v} for k, v in CARD_STATUS.items()],
            "legal_reviews": [{"legal_review": k, "label": v} for k, v in LEGAL_REVIEW.items()],
            "cards": cards, "parameters": parameters, "checks": checks,
            "violations": [f for f in checks if f["passed"] is False]}


__all__ = ["CARD_FIELDS", "CARD_STATUS", "CARD_TYPES", "CardError", "LAYERS", "LAYER_LABEL", "LAYER_TEXT", "LEGAL_REVIEW",
           "card_spec", "check_cards", "decision_path", "layer_of", "semantic_view", "value_setters", "violations"]
