"""What the page asks for around a person's work rather than the definition itself: a home with what waits on them,
one record with everything around it and lists of records to open one from, a change request element by element with
the reviewer's word on each, and a decision table tried on values before it is filed.

Kept apart from api.py, which answers the screens that build the definition. A session gets these by inheritance, and
everything here reads `self.studio` through the same helpers the other screens use.
"""
from __future__ import annotations

import json
import re
from typing import Any

from xgen_space.check import all_props, column_of, find_prop
from xgen_space.ir import Agg, And, Cmp, Column, Contains, Edge, Or, Order, Query, Ref
from xgen_space.web.space_api import plain

LINK_ROWS = 8  # linked records shown under each relation of a record page
GRAPH_ROWS = 25  # records one relation adds to the record graph at a time; past it the rest wait behind a count
PATH_HOPS = 5  # how far apart two records may be for a path between them to be looked for
PATH_TRIES = 12  # chains of relations tried, shortest first
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
        context = self._to_one(type_name, key, depth=2)
        flat = [x for c in context for x in (c, *c["next"])]
        # a thing is read by the name of what it is (the product), not of the person it belongs to: a type that hides
        # some of its values is about a person
        person = {x["type"] for x in flat if any(find_prop(o, x["type"], p).mask for p in all_props(o, x["type"]))}
        named = None if title is not None else next((x for x in flat if x["title"] and x["type"] not in person),
                                                    next((x for x in flat if x["title"]), None))
        return plain({
            "type": type_name, "label": t.label or type_name, "key": key, "title": title, "table": t.table,
            "context": context, "named_by": named,
            "computed": self._computed(o, type_name, key),
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

    def _to_one(self, type_name: str, key: str, depth: int = 1, seen: frozenset = frozenset()) -> list[dict]:
        """The records this one refers to, one each (an order item's order and its SKU), and theirs in turn up to
        `depth`: what a person reads a record by when it has no name of its own."""
        o, st = self.studio.onto, self.studio
        mine = set(_lineage(o, type_name))
        out = []
        for lk in o.links.values():
            # one record on the other side: a relation to one, or a relation from one read backwards
            ahead = lk.source in mine and lk.cardinality in ("many_to_one", "one_to_one")
            back = lk.target in mine and lk.cardinality in ("one_to_many", "one_to_one") and not ahead
            other = lk.target if ahead else lk.source
            if not (ahead or back) or other in seen or other in mine:
                continue
            ot = o.obj(other)
            edge = Edge("x", lk.name, "y") if ahead else Edge("y", lk.name, "x")
            q = Query(nodes={"x": type_name, "y": other}, edges=[edge],
                      where=Cmp(Ref("x", o.obj(type_name).key), "eq", key), columns=[Column(Ref("y", ot.key), "k")], limit=2)
            try:
                rows = st.run(q).rows
            except Exception:  # a relation the source cannot answer is left out of the summary
                continue
            if len(rows) != 1:
                continue
            k = str(rows[0][0])
            row = st.fetch(other, k) or {}
            tp = _title(o, other)
            item = {"type": other, "type_label": ot.label or other, "key": k, "via": (lk.label or lk.name) if ahead else (ot.label or other),
                    "title": row.get(tp) if tp and tp != ot.key else None, "sub": self._summary(other, row), "next": []}
            if depth > 1:
                item["next"] = self._to_one(other, k, depth - 1, seen | mine)
            out.append(item)
        return out

    def _summary(self, type_name: str, row: dict) -> str:
        """Two values a person tells a record by, besides its key and name: a state, a date, a grade."""
        o = self.studio.onto
        t = o.obj(type_name)
        tp = _title(o, type_name)
        picks = []
        for p in all_props(o, type_name):
            prop = find_prop(o, type_name, p)
            v = row.get(p)
            if p in (t.key, tp) or v in (None, "") or prop.expr or prop.mask or p.endswith("_id"):
                continue
            rank = 0 if prop.type == "enum" or (t.states and p == t.states.property) else 1 if prop.type in ("date", "datetime") else 2
            picks.append((rank, str(v)[:16].replace("T", " ") if prop.type in ("date", "datetime") else str(v)))
        return " · ".join(v for _, v in sorted(picks, key=lambda x: x[0])[:2])

    def _computed(self, o, type_name: str, key: str) -> list[dict]:
        """What the record's functions give, worked out on opening when they only read: a formula, a table or a query.
        The runs are not kept in the function log."""
        out = []
        for f in o.functions.values():
            if f.target not in _lineage(o, type_name) or f.status != "active" or f.runtime not in ("expr", "decision", "query"):
                continue
            try:
                got = self.studio.function(f.name, key, {}, by=self.who, log=False)
                out.append({"name": f.name, "label": f.label or f.name, "outputs": got["outputs"]})
            except Exception as e:  # one that needs a value from a person waits for the person
                out.append({"name": f.name, "label": f.label or f.name, "error": str(e)})
        return out

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

    def _record_links(self, type_name: str, key: str, rows_max: int = LINK_ROWS) -> list[dict]:
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
                    out.append({"link": lk.name, "base": lk.name, "base_label": lk.label or lk.name, "label": lk.label or lk.name, "forward": forward, "type": other,
                                "type_label": ot.label or other, "count": 0, "more": False, "items": [], "error": str(e)})
                    continue
                name = lk.name if forward else (lk.inverse or lk.name)
                out.append({"link": name, "base": lk.name, "base_label": lk.label or lk.name,  # one relation read either way
                            "label": (lk.label or lk.name) if forward else (ot.label or other),
                            "forward": forward, "type": other, "type_label": ot.label or other,
                            "cardinality": lk.cardinality, "count": min(len(rows), LINK_COUNT), "more": len(rows) > LINK_COUNT,
                            "items": [{"key": str(r[0]), "title": r[1] if len(r) > 1 else None} for r in rows[:rows_max]]})
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
        o = self.studio.onto
        row = self.studio.fetch(type_name, key) or {}
        source = []  # the moments the source itself keeps on the record: ordered at, delivered at
        for p in all_props(o, type_name):
            prop = find_prop(o, type_name, p)
            if prop.type in ("date", "datetime") and row.get(p) and not prop.expr:
                word = re.sub(r"\s*(일시|일자|시각|날짜|일)$", "", prop.label or p) or (prop.label or p)
                source.append({"at": str(row[p]), "event": word, "actor": "원천 DB", "kind": "source", "proposal": "",
                               "action": ""})
        return waiting + sorted(done[:20] + source, key=lambda x: str(x["at"]), reverse=True)

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

    def record_find(self, q: str, limit: int = 10) -> dict:
        """Records of any type whose key is the words or whose name holds them: where a graph or a search starts."""
        st, o = self.studio, self.studio.onto
        q = " ".join(str(q or "").split())[:60]
        if not q:
            return {"q": q, "items": []}
        out = []
        for name, t in o.objects.items():
            if not t.table or len(out) >= limit:
                continue
            tp = _title(o, name)
            parts = [Cmp(Ref("x", t.key), "eq", q)] + ([Contains(Ref("x", tp), q)] if tp and tp != t.key else [])
            cols = [Column(Ref("x", t.key), "k")] + ([Column(Ref("x", tp), "t")] if tp and tp != t.key else [])
            try:
                rows = st.run(Query(nodes={"x": name}, where=Or(parts) if len(parts) > 1 else parts[0], columns=cols,
                                    order=[Order("k")], limit=3)).rows
            except Exception:  # a type the source cannot search is passed over
                continue
            out += [{"type": name, "type_label": t.label or name, "key": str(r[0]), "title": r[1] if len(r) > 1 else None}
                    for r in rows]
        exact = [x for x in out if x["key"] == q]
        return plain({"q": q, "items": (exact + [x for x in out if x["key"] != q])[:limit]})

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
        from xgen_space.web.api import GATE_LABEL

        standing = self._standing_gates() if any(c.status == "pending" for c in st.changes.requests.values()) else {}
        for c in st.changes.requests.values():
            if c.status != "pending":
                continue
            rv = c.review or {}
            gates = rv.get("gates") or []
            worse = []
            for g in gates:  # what the change would make worse, the way the review says it
                was, now = standing.get(f"{g['stage']}.{g['condition']}"), g.get("value")
                if was is not None and now is not None and (now > was if g["condition"].startswith("max_") else now < was):
                    worse.append({"label": GATE_LABEL.get((g["stage"], g["condition"]), g["condition"]), "was": was, "now": now,
                                  "rate": not g["condition"].startswith("max_")})
            items.append({"kind": "change", "id": c.id, "title": f"{self._change_label(c)} {rv.get('base_version') or ''} → {c.version}".replace("  ", " "),
                          "module": c.module, "by": c.requested_by, "mine": c.requested_by == self.who, "at": c.at,
                          "passed": rv.get("passed"), "gates": [sum(bool(g.get("passed")) for g in gates), len(gates)],
                          "diff": {k: len(v) for k, v in (rv.get("diff") or {}).items()}, "worse": worse})
        for c in st.onto.source_conflicts():
            if not c.open:
                continue
            answers = " ↔ ".join(f"{a.source} {', '.join(f'{k} {v}' for k, v in a.says.items())}".strip() for a in c.answers)
            items.append({"kind": "conflict", "id": c.id, "title": c.label or c.id, "decision": c.decision,
                          "detail": answers[:160], "mine": False})
        bind = (self._standing_measured() or {}).get("bind") or {}
        warned = [f for f in bind.get("findings") or [] if f.get("severity") in ("warning", "error")]
        if warned:  # what the last check of the source against the definition found, for whoever looks after it
            items.append({"kind": "check", "id": "bind", "title": f"DB 대조 {'오류' if bind.get('errors') else '경고'} {len(warned)}건",
                          "detail": " · ".join(str(f.get("detail") or f.get("message") or "") for f in warned[:2])[:160],
                          "mine": False})
        ws = self.workspace
        if ws is not None and ws.dirty:
            items.append({"kind": "workspace", "id": "workspace", "title": f"정의 관리 변경 {len(ws.edits)}건",
                          "detail": ", ".join(e.target for e in ws.edits[-4:]), "mine": True})
        # one visitor plays both sides on their own page, so what they asked for is theirs to settle too
        alone = bool(self.studio.changes.self_approve)
        counts = {"assigned": len(items) if alone else sum(not x["mine"] for x in items), "mine": sum(x["mine"] for x in items),
                  "all": len(items)}
        return plain({"items": items, "counts": counts, "who": self.who, "alone": alone})

    # ---- a change request, element by element -------------------------------------------------------------------------

    def change_detail(self, change_id: str) -> dict:
        """One change request with each element it adds, changes or removes, field by field, what reads that element now,
        the reviewer's word and the comments on it, and the pass conditions as the studio meets them now and after."""
        from xgen_space.modules import compose
        from xgen_space.review import _elements

        st = self.studio
        cr = st.changes._get(change_id)
        out = self._change(cr)
        diff = (cr.review or {}).get("diff") or {}
        before: dict[str, str] = {}
        after: dict[str, str] = {}
        after_onto = None
        if cr.status == "pending" and st.composition is not None:
            module = st.changes._module(cr)
            current = list(st.composition.modules)
            mods = ([module if m.name == module.name else m for m in current] if any(m.name == module.name for m in current)
                    else current + [module] if cr.attach else None)
            if mods is not None:
                try:
                    after_onto = compose(mods, **st._compose_kw).ontology
                    before, after = _elements(st.onto), _elements(after_onto)
                except Exception:  # what does not compose is in the review's issues already
                    before, after = {}, {}
        items = []
        for change in ("changed", "added", "removed"):
            for el in diff.get(change) or []:
                a = json.loads(before[el]) if el in before else None
                b = json.loads(after[el]) if el in after else None
                items.append({"element": el, "kind": el.split(":", 1)[0], "name": el.split(":", 1)[1], "change": change,
                              "label": self._element_label(el, after_onto), "fields": self._field_diff(el, a, b, after_onto),
                              "readers": self._readers(el), "mark": cr.marks.get(el, ""),
                              "comments": [c for c in cr.comments if c["element"] == el]})
        order = ["object", "property", "link", "decision", "rule", "action", "function", "role", "query", "identity", "question"]
        items.sort(key=lambda x: (order.index(x["kind"]) if x["kind"] in order else len(order), x["element"]))
        affected = list(dict.fromkeys(r for x in items for r in x["readers"]))
        out.update({"items": items, "comments": [c for c in cr.comments if not c["element"]], "marks": dict(cr.marks),
                    "affected": affected, "who": self.who, "self_approve": st.changes.self_approve,
                    "yaml": self._change_yaml(cr), "question_notes": [c for c in cr.comments if c["element"].startswith("question:")],
                    "before": self._standing_gates() if cr.status == "pending" else {},
                    "can_decide": cr.status == "pending" and (st.changes.self_approve or cr.requested_by != self.who),
                    "can_mark": cr.status == "pending"})
        return plain(out)

    def _change_yaml(self, cr) -> list[list[str]]:
        """The module file before and after the change, line by line: [' ', line], ['-', line] or ['+', line]."""
        import difflib

        import yaml

        lib = self.studio.changes.store or self.studio.library
        before = ""
        if lib is not None and cr.module in lib.names():
            try:
                versions = [v for v in lib.versions(cr.module) if v != cr.version]
                if versions:
                    before = yaml.safe_dump(lib.get(cr.module, versions[-1]).to_dict(), allow_unicode=True, sort_keys=False)
            except Exception:  # a version that no longer reads is compared as nothing
                before = ""
        out = []
        for line in difflib.ndiff(before.splitlines(), (cr.text or "").splitlines()):
            if line[:1] in (" ", "-", "+"):
                out.append([line[:1], line[2:]])
        return out

    def change_mark(self, change_id: str, element: str, verdict: str) -> dict:
        from xgen_space.review import ChangeError

        try:
            self.studio.changes.mark(change_id, element, verdict, by=self.who)
        except ChangeError as e:
            raise ValueError(f"표시하지 못했습니다. {e}") from None
        return self.change_detail(change_id)

    def change_comment(self, change_id: str, element: str, text: str) -> dict:
        from xgen_space.review import ChangeError

        try:
            self.studio.changes.comment(change_id, element, text, by=self.who)
        except ChangeError as e:
            raise ValueError(f"댓글을 남기지 못했습니다. {e}") from None
        return self.change_detail(change_id)

    def _standing_gates(self) -> dict:
        """The pass conditions as the studio meets them before any change, measured once per definition."""
        from xgen_space.review import gates, measure

        st = self.studio
        sig = (id(st.onto), len(st.actions.audit))
        if self._standing is not None and self._standing[0] == sig:
            return self._standing[1]
        try:
            measured = measure(st, st.flow)
            got = {f"{g.stage}.{g.condition}": g.value for g in gates(measured, st.flow)}
        except Exception:  # the studio as it stands cannot be measured: the review shows the change's numbers alone
            measured, got = {}, {}
        self._standing = (sig, got, measured)
        return got

    def _standing_measured(self) -> dict:
        """What the last standing measurement found, measuring once if nothing has."""
        self._standing_gates()
        return self._standing[2] if self._standing else {}

    _standing: tuple | None = None

    def _element_label(self, el: str, after=None) -> str:
        kind, name = el.split(":", 1)
        for o in (self.studio.onto, after):
            if o is None:
                continue
            if kind == "object" and name in o.objects:
                return o.objects[name].label or name
            if kind == "property" and "." in name:
                t, p = name.split(".", 1)
                if t in o.objects and p in o.objects[t].properties:
                    return f"{o.objects[t].label or t} · {o.objects[t].properties[p].label or p}"
            if kind in ("rule", "decision") and name.split(".")[0] in o.decisions:
                d = o.decisions[name.split(".")[0]]
                return f"{d.label or d.name} · {name.split('.', 1)[1]}" if kind == "rule" else (d.label or d.name)
            section = {"link": o.links, "action": o.actions, "query": o.queries, "function": o.functions, "role": o.roles}.get(kind)
            if section is not None and name in section:
                return getattr(section[name], "label", "") or name
            if kind == "question":
                q = next((q for q in o.questions if q.id == name), None)
                if q is not None:
                    return q.text or name
        return name

    FIELD_WORDS = {"label": "라벨", "type": "타입", "column": "컬럼", "values": "허용값", "required": "필수", "mask": "가림",
                   "expr": "계산식", "unit": "단위", "description": "설명", "table": "테이블", "key": "키", "parent": "상위 객체",
                   "source": "출발 객체", "target": "도착 객체", "cardinality": "카디널리티", "on": "조인 컬럼", "via": "연결 테이블",
                   "inverse": "역방향 이름", "cite": "근거", "text": "질문", "expect": "기대 답", "decision": "결정표", "query": "질의",
                   "params": "Parameter", "hit_policy": "적용 방식", "title": "표시 이름 속성", "states": "상태 전이"}

    def _field_diff(self, el: str, a: dict | None, b: dict | None, after=None) -> list[dict]:
        """What differs, one field at a time, in a person's words: a rule's condition by its input's name."""
        from xgen_space.decide.words import input_label

        def flat(d: Any, pre: str = "") -> dict[str, Any]:
            out: dict[str, Any] = {}
            for k, v in (d or {}).items():
                if isinstance(v, dict) and v and pre.count(".") < 1:
                    out.update(flat(v, f"{pre}{k}."))
                else:
                    out[f"{pre}{k}"] = v
            return out

        fa, fb = flat(a), flat(b)
        kind, name = el.split(":", 1)
        table = None
        if kind == "rule":
            for o in (self.studio.onto, after):
                if o is not None and name.split(".")[0] in o.decisions:
                    table, onto = o.decisions[name.split(".")[0]], o
                    break

        def word(f: str) -> str:
            head, _, rest = f.partition(".")
            if table is not None and head == "when" and rest in table.inputs:
                return f"조건 · {input_label(onto, table, rest)}"
            if head == "then" and rest:
                return f"결과 · {'사유' if rest == 'reason' else rest}"
            if f in self.FIELD_WORDS or not rest:
                return self.FIELD_WORDS.get(f, f)
            return f"{self.FIELD_WORDS.get(head, head)} · {'사유' if rest == 'reason' else rest}"

        keys = sorted(set(fa) | set(fb), key=lambda k: (not k.startswith("when."), not k.startswith("then."), k))
        return [{"field": k, "label": word(k), "before": fa.get(k), "after": fb.get(k)}
                for k in keys if fa.get(k) != fb.get(k) and k not in ("id",)][:16]

    def _readers(self, el: str) -> list[str]:
        """What in the definition reads an element now, so a reviewer sees what a change to it reaches."""
        o = self.studio.onto
        kind, name = el.split(":", 1)
        out: list[str] = []
        said = lambda q: json.dumps(q, ensure_ascii=False)  # noqa: E731
        if kind in ("rule", "decision"):
            d = name.split(".")[0]
            out += [f"검증 질문 {q.id}" for q in o.questions if q.decision == d]
            out += [f"액션 {a.label or a.name}" for a in o.actions.values() if any(c.decision == d for c in a.criteria)]
            out += [f"함수 {f.label or f.name}" for f in o.functions.values() if f.decision == d]
            out += [f"역할 {r.label or r.name}" for r in o.roles.values() if d in r.run]
        elif kind == "property" and "." in name:
            t, p = name.split(".", 1)
            out += [f"결정 {x.label or x.name}" for x in o.decisions.values()
                    if any(p in (i.source.get("property"), i.source.get("days_since")) for i in x.inputs.values())]
            out += [f"질의 {q.label or q.name}" for q in o.queries.values() if f".{p}" in said(q.query)]
            out += [f"계산 속성 {ot.label or tn} · {prop.label or pn}" for tn, ot in o.objects.items()
                    for pn, prop in ot.properties.items() if prop.expr and re.search(rf"\b{re.escape(p)}\b", prop.expr)]
        elif kind == "object":
            out += [f"질의 {q.label or q.name}" for q in o.queries.values() if f'"{name}"' in said(q.query)]
            out += [f"결정 {x.label or x.name}" for x in o.decisions.values() if x.target == name]
            out += [f"액션 {a.label or a.name}" for a in o.actions.values() if a.target == name]
        elif kind == "link":
            out += [f"질의 {q.label or q.name}" for q in o.queries.values() if f'"{name}"' in said(q.query)]
            out += [f"결정 {x.label or x.name}" for x in o.decisions.values()
                    if any(name in (i.source.get("path") or []) for i in x.inputs.values())]
        elif kind == "query":
            out += [f"검증 질문 {q.id}" for q in o.questions if q.query == name]
            out += [f"역할 {r.label or r.name}" for r in o.roles.values() if name in r.run]
        return list(dict.fromkeys(out))[:12]

    # ---- a decision table tried before it is filed ------------------------------------------------------------------

    def _pending_onto(self):
        """The definition as the pending edits leave it, which a table being edited is tried on."""
        ws = self._ws()
        if not ws.dirty:
            return self.studio.onto, False
        try:
            return ws.composed().ontology, True
        except Exception:  # edits that no longer compose are tried as the studio stands
            return self.studio.onto, False

    def simulate(self, name: str, key: str = "", inputs: dict | None = None) -> dict:
        """Decide once on given values (a record's, with any of them changed), then say which single change of one input
        would give another answer, and what the table answers at each threshold its rules name. The table is the one
        being edited: the pending edits are in it before they are filed. The validation questions on the table are
        answered by it too."""
        from xgen_space.decide.table import DecisionError, evaluate_table
        from xgen_space.decide.words import input_label, verdict
        from xgen_space.values import coerce

        st = self.studio
        onto, pending = self._pending_onto()
        table = onto.decisions[name]
        base: dict[str, Any] = {}
        if key:
            base = dict(st.decide(name, key).inputs)
        for k, v in (inputs or {}).items():
            if k in table.inputs:
                base[k] = None if v in ("", None) else coerce(v, table.inputs[k].type)
        values = {i: base.get(i) for i in table.inputs}

        def run(vals: dict) -> dict:
            try:
                outs, matched, _ = evaluate_table(table, vals)
            except DecisionError as e:
                return {"outputs": {}, "matched": [], "verdict": "판정 불가", "yes": False, "error": str(e)}
            word, good = verdict(table, outs)
            return {"outputs": outs, "matched": list(matched), "verdict": word, "yes": good}

        questions = []
        for q in onto.questions:
            if q.decision != name:
                continue
            try:
                got = run(dict(st.decide(name, q.key, q.params).inputs))["outputs"]
            except Exception as e:  # a question on a record the source no longer has
                questions.append({"id": q.id, "text": q.text, "key": q.key, "passed": False, "error": str(e)})
                continue
            passed = isinstance(got, dict) and all(got.get(k) == v for k, v in q.expect.items())
            questions.append({"id": q.id, "text": q.text, "key": q.key, "expect": q.expect, "got": got, "passed": passed})

        now = run(values)
        tries = self._candidates(table, values)
        other, edges = [], []
        for i, vals in tries:
            got = run({**values, i: vals})
            row = {"input": i, "label": input_label(onto, table, i), "value": vals, **got}
            edges.append(row)
            if got["verdict"] != now["verdict"] and not any(x["input"] == i for x in other):
                other.append(row)
        return plain({"name": name, "label": table.label or name, "key": key, "hit_policy": table.hit_policy,
                      "inputs": [{"name": i, "label": input_label(onto, table, i), "type": table.inputs[i].type,
                                  "value": values[i]} for i in table.inputs],
                      **now, "other": other, "edges": edges[:24], "questions": questions, "pending": pending})

    @staticmethod
    def _candidates(table, values: dict) -> list[tuple[str, Any]]:
        """Values worth trying for each input: either side of every number a rule compares it with, and every value a rule
        names for it, nearest to the value it has first."""
        out: list[tuple[str, Any]] = []
        named = table.named
        for i, spec in table.inputs.items():
            cells = [str(r.when.get(i, "")) for r in table.rules if r.when.get(i) not in (None, "-")]
            if spec.type in ("integer", "decimal"):
                nums: set[float] = set()
                for c in cells:
                    nums |= {float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", c)}
                    nums |= {float(named[n]) for n in re.findall(r"@(\w+)", c) if isinstance(named.get(n), (int, float))}
                step = 1 if spec.type == "integer" else 0.01
                seen: set[float] = set()
                for n in sorted(nums):
                    for v in (n - step, n, n + step):
                        if v not in seen:
                            seen.add(v)
                cur = values.get(i)
                ordered = sorted(seen, key=lambda v: abs(v - cur) if isinstance(cur, (int, float)) else v)
                out += [(i, int(v) if spec.type == "integer" else round(v, 4)) for v in ordered[:6]]
            elif spec.type == "boolean":
                out += [(i, v) for v in (True, False) if v != values.get(i)]
            else:
                words = {w for c in cells for w in re.findall(r'"([^"]*)"', c)}
                out += [(i, w) for w in sorted(words) if w != values.get(i)][:4]
        return out

    # ---- records as a graph -------------------------------------------------------------------------------------------

    def record_links(self, type_name: str, key: str) -> dict:
        """The relations of one record with up to GRAPH_ROWS records each, for the record graph to grow from it."""
        o = self.studio.onto
        t = o.obj(type_name)
        tp = _title(o, type_name)
        row = self.studio.fetch(type_name, str(key))
        if row is None:
            raise LookupError(f"{t.label or type_name} {key}")
        return plain({"type": type_name, "label": t.label or type_name, "key": str(key),
                      "title": row.get(tp) if tp and tp != t.key else None,
                      "links": self._record_links(type_name, str(key), GRAPH_ROWS)})

    def record_path(self, from_type: str, from_key: str, to_type: str, to_key: str) -> dict:
        """The records that join two records, along the shortest chain of relations that joins them in the data. Chains
        are tried shortest first; each is one ontology query, so it runs on whatever store the source is."""
        st, o = self.studio, self.studio.onto
        for name in (from_type, to_type):
            o.obj(name)  # an unknown type is said before any path is tried
        ways: dict[str, list[tuple[str, bool, str]]] = {}
        for lk in o.links.values():
            ways.setdefault(lk.source, []).append((lk.name, True, lk.target))
            ways.setdefault(lk.target, []).append((lk.name, False, lk.source))
        chains, frontier = [], [(from_type, [])]
        for _ in range(PATH_HOPS):
            grown = []
            for here, path in frontier:
                seen = {from_type, *(s[3] for s in path)}
                for link, forward, there in ways.get(here, []):
                    if there in seen and not (there == to_type and path):
                        continue
                    step = path + [(link, forward, here, there)]
                    if there == to_type:
                        chains.append(step)
                    elif len(grown) < 4000:
                        grown.append((there, step))
            frontier = grown
            if len(chains) >= PATH_TRIES:
                break
        for chain in chains[:PATH_TRIES]:
            nodes = {f"x{i + 1}": s[3] for i, s in enumerate(chain)}
            nodes = {"x0": from_type, **nodes}
            edges = [Edge(f"x{i}", s[0], f"x{i + 1}") if s[1] else Edge(f"x{i + 1}", s[0], f"x{i}") for i, s in enumerate(chain)]
            last = f"x{len(chain)}"
            where = And([Cmp(Ref("x0", o.obj(from_type).key), "eq", str(from_key)), Cmp(Ref(last, o.obj(to_type).key), "eq", str(to_key))])
            cols = [Column(Ref(a, o.obj(tn).key), a) for a, tn in nodes.items()]
            try:
                rows = st.run(Query(nodes=nodes, edges=edges, where=where, columns=cols, limit=1)).rows
            except Exception:  # a chain one store cannot answer is passed over for the next
                continue
            if not rows:
                continue
            keys = [str(v) for v in rows[0]]
            types = list(nodes.values())
            out_nodes = []
            for tn, k in zip(types, keys):
                tp = _title(o, tn)
                rec = st.fetch(tn, k) if tp else None
                out_nodes.append({"type": tn, "key": k, "label": o.obj(tn).label or tn,
                                  "title": (rec or {}).get(tp) if tp and tp != o.obj(tn).key else None})
            out_edges = []
            for i, s in enumerate(chain):
                lk = o.links[s[0]]
                a, b = (i, i + 1) if s[1] else (i + 1, i)
                out_edges.append({"source": f"{types[a]}:{keys[a]}", "target": f"{types[b]}:{keys[b]}", "link": lk.name,
                                  "label": lk.label or lk.name})
            return plain({"ok": True, "hops": len(chain), "nodes": out_nodes, "edges": out_edges})
        return {"ok": False, "error": f"{PATH_HOPS}단계 안에서 두 레코드를 잇는 관계를 찾지 못했습니다. 다른 레코드로 다시 찾아 주세요."}

    def element_readers(self, element: str) -> dict:
        return {"element": element, "label": self._element_label(element), "readers": self._readers(element)}
