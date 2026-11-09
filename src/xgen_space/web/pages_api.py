"""What the page asks for the people who use an ontology rather than build it: a home with what waits on them, one
record with everything around it, and lists of records to open one from.

Kept apart from api.py, which answers the screens that build the definition. A session gets these by inheritance, and
everything here reads `self.studio` through the same helpers the other screens use.
"""
from __future__ import annotations

from typing import Any

from xgen_space.check import all_props, column_of, find_prop
from xgen_space.ir import Agg, Cmp, Column, Contains, Edge, Or, Order, Query, Ref
from xgen_space.web.space_api import plain

LINK_ROWS = 8  # linked records shown under each relation of a record page
LINK_COUNT = 50  # past this a relation says "50+" instead of counting on
LIST_ROWS = 100  # records a list returns at a time
KEY_MENTIONS = 4  # passages that name a record's own key


TITLE_WORDS = ("name", "title", "label")


def _title(onto, type_name: str) -> str:
    """The property a person reads a record by: the declared title, or else a text property called a name."""
    t = onto.obj(type_name)
    if t.title:
        return t.title
    for p in all_props(onto, type_name):
        prop = find_prop(onto, type_name, p)
        if p != t.key and prop.type == "string" and not prop.expr and (
                p.lower() in TITLE_WORDS or p.lower().endswith("_name") or "이름" in (prop.label or "") or (prop.label or "").endswith("명")):
            return p
    return ""


def _lineage(onto, name: str) -> list[str]:
    out, t = [], name
    while t and t in onto.objects and t not in out:
        out.append(t)
        t = onto.objects[t].parent
    return out


class PagesMixin:
    # ---- one record ----------------------------------------------------------------------------------------------

    def record_page(self, type_name: str, key: str) -> dict:
        """One record with what it is, where each value comes from, what it links to, what the rules say of it now, what
        can be done to it, the documents that speak of it and what has happened to it."""
        st, o = self.studio, self.studio.onto
        t = o.obj(type_name)
        key = str(key)
        row = st.fetch(type_name, key)
        if row is None:
            raise LookupError(f"{t.label or type_name} {key}")
        comp = st.composition
        props = []
        for p in all_props(o, type_name):
            prop = find_prop(o, type_name, p)
            v = row.get(p)
            owner = comp.owner(f"property:{type_name}.{p}") if comp and p in t.properties else ""
            props.append({"name": p, "label": prop.label or p, "type": prop.type, "unit": prop.unit, "value": v,
                          "value_label": (prop.labels or {}).get(str(v), "") if v is not None else "",
                          "column": column_of(o, type_name, p) if t.table and not prop.expr else "", "expr": prop.expr,
                          "mask": prop.mask, "key": p == t.key, "module": owner,
                          "module_label": self._label(owner) if owner else ""})
        tp = _title(o, type_name)
        title = row.get(tp) if tp and tp != t.key else None
        return plain({
            "type": type_name, "label": t.label or type_name, "key": key, "title": title, "table": t.table,
            "description": t.description, "props": props, "state": self._record_state(t, row),
            "links": self._record_links(type_name, key), "decisions": self._record_decisions(type_name, key),
            "functions": [{"name": f.name, "label": f.label or f.name, "outputs": list(f.outputs), "status": f.status,
                           "inputs": [{"name": k, "label": (v or {}).get("label") or k if isinstance(v, dict) else k}
                                      for k, v in f.inputs.items()]}
                          for f in o.functions.values() if f.target in _lineage(o, type_name) and f.status != "retired"],
            "actions": self._record_actions(t, row),
            "documents": self._mentions(type_name) if self.space is not None else [],
            "key_documents": self._key_mentions(key),
            "history": self._record_history(type_name, key),
        })

    def _record_state(self, t, row: dict) -> dict | None:
        sm = t.states
        if sm is None:
            return None
        now = row.get(sm.property)
        moves = []
        for tr in sm.transitions:
            if tr.source != now:
                continue
            action = tr.action or next((a.name for a in self.studio.onto.actions.values()
                                        if a.target == t.name and a.transition_to == tr.target), "")
            a = self.studio.onto.actions.get(action)
            moves.append({"to": tr.target, "action": action, "action_label": (a.label or a.name) if a else "",
                          "after": dict(tr.after), "guarded": bool(tr.guard)})
        return {"property": sm.property, "now": now, "states": list(sm.states), "initial": sm.initial, "next": moves}

    def _record_links(self, type_name: str, key: str) -> list[dict]:
        """Each relation the record takes part in, either way round, with the first records on the other side."""
        o = self.studio.onto
        mine = set(_lineage(o, type_name))
        t = o.obj(type_name)
        out = []
        for lk in o.links.values():
            for forward in (True, False):
                here, other = (lk.source, lk.target) if forward else (lk.target, lk.source)
                if here not in mine:
                    continue
                ot = o.obj(other)
                cols = [Column(Ref("y", ot.key), "k")]
                tp = _title(o, other)
                if tp and tp != ot.key:
                    cols.append(Column(Ref("y", tp), "t"))
                edge = Edge("x", lk.name, "y") if forward else Edge("y", lk.name, "x")
                q = Query(nodes={"x": type_name, "y": other}, edges=[edge], where=Cmp(Ref("x", t.key), "eq", key),
                          columns=cols, order=[Order("k")], limit=LINK_COUNT + 1, distinct=True)
                try:
                    rows = self.studio.run(q).rows
                except Exception as e:  # a relation the source cannot answer says why instead of hiding the page
                    out.append({"link": lk.name, "label": lk.label or lk.name, "forward": forward, "type": other,
                                "type_label": ot.label or other, "count": 0, "more": False, "items": [], "error": str(e)})
                    continue
                name = lk.name if forward else (lk.inverse or lk.name)
                out.append({"link": name, "label": (lk.label or lk.name) if forward else (ot.label or other),
                            "forward": forward, "type": other, "type_label": ot.label or other,
                            "cardinality": lk.cardinality, "count": min(len(rows), LINK_COUNT), "more": len(rows) > LINK_COUNT,
                            "items": [{"key": str(r[0]), "title": r[1] if len(r) > 1 else None} for r in rows[:LINK_ROWS]]})
        return out

    def _record_decisions(self, type_name: str, key: str) -> list[dict]:
        out = []
        for name, table in self.studio.onto.decisions.items():
            if table.target != type_name:
                continue
            try:
                d = self.decide(name, key)
            except Exception as e:  # a decision that cannot be made on this record says so in its place
                out.append({"name": name, "label": table.label or name, "error": str(e)})
                continue
            hit = next((r for r in d["rules"] if r["hit"]), None)
            out.append({"name": name, "label": d["label"], "verdict": d["verdict"], "yes": d["yes"], "reason": d["reason"],
                        "matched": d["matched"], "cite": hit["cite"] if hit else ""})
        return out

    def _record_actions(self, t, row: dict) -> list[dict]:
        sm = t.states
        now = row.get(sm.property) if sm else None
        out = []
        for a in self.studio.onto.actions.values():
            if a.target != t.name:
                continue
            ready = True
            if sm is not None and a.transition_to:
                ready = any(tr.source == now and tr.target == a.transition_to for tr in sm.transitions)
            roles = [{"name": r.name, "label": r.label or r.name} for r in self.studio.onto.roles.values() if r.can("request", a.name)]
            out.append({"name": a.name, "label": a.label or a.name, "to": a.transition_to, "ready": ready,
                        "approval": a.approval, "roles": roles,
                        "params": [{"name": k, **(v if isinstance(v, dict) else {"type": v})} for k, v in a.parameters.items()]})
        return out

    def _key_mentions(self, key: str) -> list[dict]:
        """Passages that write this record's own key, such as a policy example or a guide that names an order."""
        if self.space is None or len(key) < 3:
            return []
        try:
            made = self.space.concepts(self.studio.onto, self._terms())
        except Exception:  # documents not indexed yet: the page has the type's documents still
            return []
        out = []
        for doc, chunks in made["chunks"].items():
            for c in chunks:
                if key in c.text:
                    i = c.text.index(key)
                    out.append({"document": doc, "section": c.section, "text": c.text[max(0, i - 50):i + 100]})
                    break
            if len(out) >= KEY_MENTIONS:
                break
        return out

    def _record_history(self, type_name: str, key: str) -> list[dict]:
        mine = set(_lineage(self.studio.onto, type_name))
        waiting = [{"at": "", "event": "승인 대기", "actor": p.requested_by.id, "kind": p.requested_by.kind,
                    "proposal": p.id, "action": p.action, "pending": True}
                   for p in self.studio.actions.proposals.values()
                   if p.status == "pending" and p.target in mine and str(p.key) == key]
        done = [{k: a[k] for k in ("at", "event", "actor", "kind", "proposal", "action")}
                for a in self.audit() if a["target"] in mine and str(a["key"]) == key]
        return waiting + done[:20]

    # ---- lists of records -------------------------------------------------------------------------------------------

    def record_list(self, type_name: str, q: str = "", limit: int = 50) -> dict:
        """Records of one type to open one from: the key, the title, the state and the first date, filtered by words."""
        st, o = self.studio, self.studio.onto
        t = o.obj(type_name)
        names = all_props(o, type_name)
        show = [t.key] + [p for p in [_title(o, type_name), t.states.property if t.states else ""] if p and p != t.key]
        show += [p for p in names if find_prop(o, type_name, p).type in ("datetime", "date") and p not in show][:1]
        q = " ".join(str(q or "").split())[:60]
        where = None
        if q:
            text = [p for p in show if find_prop(o, type_name, p).type in ("string", "enum")]
            parts = [Contains(Ref("x", p), q) for p in text]
            where = Or(parts) if len(parts) > 1 else (parts[0] if parts else None)
            if where is None:
                where = Cmp(Ref("x", t.key), "eq", q)
        limit = max(1, min(int(limit or 50), LIST_ROWS))
        rows = st.run(Query(nodes={"x": type_name}, where=where, columns=[Column(Ref("x", p), p) for p in show],
                            order=[Order(t.key)], limit=limit)).rows
        total = st.run(Query(nodes={"x": type_name}, where=where, columns=[Column(Agg("count", node="x"), "n")])).rows
        labels = {p: find_prop(o, type_name, p).label or p for p in show}
        return plain({"type": type_name, "label": t.label or type_name, "key": t.key, "title": _title(o, type_name), "columns": show,
                      "labels": labels, "total": total[0][0] if total else len(rows), "q": q,
                      "rows": [{"key": str(r[0]), "fields": dict(zip(show[1:], r[1:]))} for r in rows]})

    # ---- what waits on a person ------------------------------------------------------------------------------------

    def inbox(self) -> dict:
        """Every request, change, disagreement and unfiled edit that waits for a person, in one list. `mine` marks what
        the person on this page asked for, which someone else settles."""
        st = self.studio
        items: list[dict[str, Any]] = []
        for p in st.actions.proposals.values():
            if p.status != "pending":
                continue
            v = self._proposal(p)
            failed = [c["title"] for c in v["checks"] if not c["passed"]]
            outside = [x for x in v["limits"] if not x.get("within")]
            change = ", ".join(f"{v['labels'].get(k, k)} {v['before'].get(k, '')} → {x}".strip()
                               for k, x in (v["changes"] or {}).items())[:120]
            items.append({"kind": "action", "id": p.id, "title": f"{v['label']} · {v['target_label']} {p.key}",
                          "target": p.target, "key": str(p.key), "by": p.requested_by.id, "by_kind": p.requested_by.kind,
                          "mine": p.requested_by.id == self.who, "change": change, "failed": failed,
                          "outside": len(outside), "waits": v["waits"]})
        for c in st.changes.requests.values():
            if c.status != "pending":
                continue
            rv = c.review or {}
            gates = rv.get("gates") or []
            items.append({"kind": "change", "id": c.id, "title": f"{self._label(c.module)} {rv.get('base_version') or ''} → {c.version}".replace("  ", " "),
                          "module": c.module, "by": c.requested_by, "mine": c.requested_by == self.who, "at": c.at,
                          "passed": rv.get("passed"), "gates": [sum(bool(g.get("passed")) for g in gates), len(gates)],
                          "diff": {k: len(v) for k, v in (rv.get("diff") or {}).items()}})
        for c in st.onto.source_conflicts():
            if not c.open:
                continue
            answers = " ↔ ".join(f"{a.source} {', '.join(f'{k} {v}' for k, v in a.says.items())}".strip() for a in c.answers)
            items.append({"kind": "conflict", "id": c.id, "title": c.label or c.id, "decision": c.decision,
                          "detail": answers[:160], "mine": False})
        ws = self.workspace
        if ws is not None and ws.dirty:
            items.append({"kind": "workspace", "id": "workspace", "title": f"정의 관리 변경 {len(ws.edits)}건",
                          "detail": ", ".join(e.target for e in ws.edits[-4:]), "mine": True})
        # one visitor plays both sides on their own page, so what they asked for is theirs to settle too
        alone = bool(self.studio.changes.self_approve)
        counts = {"assigned": len(items) if alone else sum(not x["mine"] for x in items), "mine": sum(x["mine"] for x in items),
                  "all": len(items)}
        return plain({"items": items, "counts": counts, "who": self.who, "alone": alone})
