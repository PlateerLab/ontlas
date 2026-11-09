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


def _decision(tools, name: str, key: str, at=None) -> dict:
    from xgen_space.check import _find_prop
    from xgen_space.decide.words import input_label, verdict

    st = tools.studio
    t = st.onto.decisions[name]
    res = tools.decide(name, key, at=at)
    outs = res["outputs"] if isinstance(res["outputs"], dict) else {"result": res["outputs"]}
    said, good = verdict(t, outs)
    reason = next((v for v in outs.values() if isinstance(v, str)), "")
    by_id = {r.id: r for r in t.rules}

    def word(i: str) -> str:
        return input_label(st.onto, t, i) if i in t.inputs else i

    rules = [{"id": i, "cite": by_id[i].cite or t.cite, **_rule_module(st, name, i),
              "when": [{"input": word(k), "test": str(v)} for k, v in by_id[i].when.items()]}
             for i in res["matched"] or [] if i in by_id]
    also = [{"id": i, "cite": by_id[i].cite or t.cite, "fallback": not by_id[i].when} for i in res.get("also") or [] if i in by_id]
    evidence = []
    for e in res["evidence"]:
        p = _find_prop(st.onto, e["object_type"], e["property"]) if e.get("object_type") and e.get("property") else None
        src = t.inputs[e["input"]].source if e["input"] in t.inputs else {}
        kind = next((k for k in ("param", "count", "days_since") if k in src), "property")
        here = st.onto.objects.get(e.get("object_type") or "")
        evidence.append({"input": e["input"], "label": word(e["input"]), "value": e["value"], "kind": kind,
                         "source": e.get("source") or "", "property": p.label if p is not None else "",
                         "type": e.get("object_type") or "", "type_label": (here.label or here.name) if here else "",
                         "key": e.get("key") or "", "path": _path_labels(st.onto, t.target, src.get("path") or src.get("count") or []),
                         "since": _raw(tools, e) if kind == "days_since" else None})
    target = st.onto.objects.get(t.target)
    return {"name": name, "label": t.label or name, "target": t.target, "target_label": (target.label or t.target) if target else "",
            "key": key, "verdict": said, "good": good, "reason": reason, "outputs": outs, "rules": rules, "evidence": evidence,
            "also": also, "hit_policy": t.hit_policy, "at": (at or st.now()).isoformat(timespec="minutes"),
            "actions": _next_actions(tools, t, key, outs), "reading": _reading(st, t, key)}


def _reading(st, table, key: str) -> str:
    """One query over the source that reads what the decision read, for a person to check by hand. The engine itself reads
    each value on its own path and evaluates the rules, so this is the same values, not the same calls."""
    from xgen_space.ir import Cmp, Column, Edge, Query, Ref

    if not table.target:
        return ""
    nodes, edges, cols, walked = {"x0": table.target}, [], [], {(): "x0"}
    for inp in table.inputs.values():
        prop = inp.source.get("property") or inp.source.get("days_since")
        if not prop:
            continue
        at: tuple = ()
        for step in inp.source.get("path") or []:
            lk = st.onto.links.get(step) or st.onto.link_by_inverse(step)
            if lk is None:
                return ""
            nxt = (*at, step)
            if nxt not in walked:
                walked[nxt] = f"x{len(nodes)}"
                nodes[walked[nxt]] = lk.target if lk.name == step else lk.source
                edges.append(Edge(walked[at], step, walked[nxt]))
            at = nxt
        cols.append(Column(Ref(walked[at], prop), prop if "days_since" in inp.source else inp.name))  # the date, not the days
    q = Query(nodes=nodes, edges=edges, where=Cmp(Ref("x0", st.onto.obj(table.target).key), "eq", str(key)), columns=cols)
    try:
        return st.translate(q, "sql").text
    except (KeyError, ValueError):  # a compile error is a ValueError
        return ""


def rule_owner(comp, name: str, rule_id: str) -> str:
    """The module that wrote a rule: the one that defined the table, or a later one that added or rewrote it."""
    owner = comp.owner(f"decision:{name}")
    for m in comp.modules:
        patch = ((m.extend or {}).get("decisions") or {}).get(name) or {}
        added = {r.get("id") for k in ("rules_prepend", "rules_append") for r in patch.get(k) or []}
        if rule_id in added | set(patch.get("rules_replace") or {}):
            owner = m.name
    return owner


def _rule_module(st, name: str, rule_id: str) -> dict:
    """The module that wrote a rule and its version."""
    comp = st.composition
    if comp is None:
        return {"module": "", "module_label": "", "version": st.onto.version}
    owner = rule_owner(comp, name, rule_id)
    mod = next((m for m in comp.modules if m.name == owner), None)
    return {"module": owner, "module_label": (mod.label or owner) if mod else owner, "version": mod.version if mod else ""}


def _path_labels(onto, start: str, path: list[str]) -> list[str]:
    """The types a path walks through, by name: 주문상품 → 주문 → 고객."""
    if not path or start not in onto.objects:
        return []
    here, out = start, [onto.objects[start].label or start]
    for step in path:
        lk = onto.links.get(step) or onto.link_by_inverse(step)
        if lk is None:
            break
        here = lk.target if lk.name == step else lk.source
        out.append((onto.objects[here].label or here) if here in onto.objects else here)
    return out


def _raw(tools, e: dict) -> Any:
    """The date a day count was counted from, unless the role sees that property hidden."""
    from xgen_space.roles import mask_style

    st = tools.studio
    if tools.role and mask_style(st.onto, st.onto.roles[tools.role], e["object_type"], e["property"]):
        return None
    row = st.fetch(e["object_type"], e["key"]) if e.get("object_type") and e.get("key") else None
    return row.get(e["property"]) if row else None


def _next_actions(tools, table, key: str, outs: dict) -> list[dict]:
    """The actions this decision gates and the role may request, and whether this record may take them now."""
    st = tools.studio
    allowed = tools.describe()["actions"]
    obj = st.onto.objects.get(table.target)
    sm = obj.states if obj is not None else None
    row = st.fetch(table.target, key) if sm is not None else None
    out = []
    for a in st.onto.actions.values():
        crit = [c for c in a.criteria if c.decision == table.name]
        if not crit or a.name not in allowed:
            continue
        met = all(outs.get(k) == v for c in crit for k, v in c.expect.items())
        moves = not (sm and a.transition_to and row) or any(tr.source == row.get(sm.property) and tr.target == a.transition_to
                                                            for tr in sm.transitions)
        out.append({"name": a.name, "label": a.label or a.name, "ready": met and moves, "met": met, "approval": bool(a.approval)})
    return out


def _sources(found: list[dict], k: int) -> list[dict]:
    kept = [f for f in found if f["kind"] in ("document", "rule")]
    floor = kept[0]["score"] * SOURCE_FLOOR if kept else 0
    return [f for f in kept if f["score"] >= floor][:k]


def _definitions(found: list[dict], onto=None, text: str = "", k: int = 6) -> list[dict]:
    """The definitions a question touches: objects, queries and actions it names, the decision tables behind the rules
    it found, and the metrics it names."""
    out = [{"id": f["id"], "kind_label": f["kind_label"], "title": f["title"], "element": f["element"]}
           for f in found if f["kind"] in ("object", "query", "action")]
    seen = {d["id"] for d in out}
    for f in found:
        if f["kind"] != "rule" or onto is None:
            continue
        name = f["id"].split(":", 1)[1].rsplit(".", 1)[0]
        d = onto.decisions.get(name)
        if d is not None and f"decision:{name}" not in seen:
            seen.add(f"decision:{name}")
            out.append({"id": f"decision:{name}", "kind_label": "결정표", "title": d.label or name, "element": f"decision:{name}"})
    for m in _metrics_named(onto, text):
        if f"metric:{m.name}" not in seen:
            seen.add(f"metric:{m.name}")
            out.append({"id": f"metric:{m.name}", "kind_label": "지표", "title": m.label or m.name, "element": f"metric:{m.name}"})
    return out[:k]


def _metrics_named(onto, text: str) -> list:
    if onto is None or not text:
        return []
    return [m for m in onto.metrics.values() if (m.label and m.label in text) or m.name in text]


def _unknown(tools, text: str, found: list[dict]) -> tuple[str, list[dict]]:
    """Why nothing answers, in terms of what the question did name, and whom to ask for what is missing."""
    onto = tools.studio.onto
    named = [f"{f['kind_label']} {f['title']}" for f in found if f["kind"] in ("object", "query", "action")][:3]
    metrics = _metrics_named(onto, text)
    named += [f"지표 {m.label or m.name}" for m in metrics]
    if named:
        reason = f"질문에서 알아들은 것은 {', '.join(named)}입니다. 이 조합에 답하는 등록 질의, 결정표, 문서가 없습니다."
    else:
        reason = "질문에서 정의된 객체, 지표, 판정, 문서를 찾지 못했습니다."
    ask = [{"who": m.owner, "about": f"지표 {m.label or m.name}"} for m in metrics if m.owner]
    return reason, ask


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
        return {"name": name, "label": f["title"], "columns": res["columns"], "rows": res["rows"][:50], "total": len(res["rows"]),
                "text": res["query_text"], "backend": res["backend"]}
    return None


def _picked(tools, pick: dict) -> tuple[str, str, Any]:
    """What a person corrected of how a question was taken: the record, the decision, the time days are counted to."""
    from xgen_space.values import parse_datetime

    onto = tools.studio.onto
    name = str(pick.get("decision") or "")
    if name and name not in onto.decisions:
        raise ValueError(f"판정 '{name}'을(를) 찾지 못해 다시 묻지 못했습니다. 판정을 다시 골라 주세요.")
    type_name = onto.decisions[name].target if name else str(pick.get("type") or "")
    key = str(pick.get("key") or "").strip()
    t = onto.objects.get(type_name)
    if t is None or not key:
        raise ValueError("레코드 번호가 없어 다시 묻지 못했습니다. 번호를 입력해 주세요.")
    try:
        found = tools.studio.fetch(type_name, key)
    except (KeyError, ValueError, RuntimeError):
        found = None
    if found is None:
        raise ValueError(f"{t.label or type_name} {key}이(가) 없어 다시 묻지 못했습니다. 번호를 확인해 주세요.")
    try:
        at = parse_datetime(pick.get("at") or None)
    except ValueError:
        raise ValueError("기준 시각을 읽지 못해 다시 묻지 못했습니다. 2026-10-30T12:00 처럼 입력해 주세요.") from None
    return type_name, key, at


def answer_question(tools, text: str, *, k: int = 6, pick: dict | None = None, folder: str = "") -> dict[str, Any]:
    """`pick` replaces what the question was taken to be: {type, key, decision, at}, any decision of the type or none.
    `folder` keeps the documents to one folder and the folders under it."""
    text = " ".join(str(text or "").split())[:300]
    if not text:
        raise ValueError("질문이 없어 답변하지 못했습니다. 질문을 입력해 주세요.")
    know = tools.knowledge(folder) if folder else tools.knowledge()
    found = know.find(text, max(k * 4, 24))
    out: dict[str, Any] = {"ok": True, "question": text, "route": "documents", "answer": "", "engine": know.retriever.kind,
                           "sources": _sources(found, k), "definitions": _definitions(found, tools.studio.onto, text),
                           "relations": know.relations(text, [f["id"] for f in found[:k]])}
    at = None
    if pick:
        type_name, key, at = _picked(tools, pick)
        hit = type_name, key
    else:
        hit = find_record(tools, text)
    if hit:
        type_name, key = hit
        allowed = tools.describe()["decisions"]
        out["choices"] = [{"name": n, "label": d.label or n} for n, d in tools.studio.onto.decisions.items()
                          if d.target == type_name and n in allowed]  # what else the record could be asked
        names = ([pick["decision"]] if pick.get("decision") else []) if pick else decisions_for(tools, text, type_name)
        if pick and names and names[0] not in allowed:
            raise PermissionError(f"decision {names[0]} is outside this role")
        names = [n for n in names if n in allowed]
        if names:
            out["decisions"] = [_decision(tools, n, key, at) for n in names]
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
        out["reason"], out["ask"] = _unknown(tools, text, found)
    else:
        out["answer"] = top["text"].split("\n")[0][:220]
    return out


__all__ = ["answer_question", "decisions_for", "find_record", "keys_in"]
