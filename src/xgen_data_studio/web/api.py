"""What the studio page asks for, answered from one studio as plain dicts."""
from __future__ import annotations

import ast
import json
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

from xgen_data_studio.actions import Actor
from xgen_data_studio.check import all_props, column_of, find_prop
from xgen_data_studio.compile.base import CompileError
from xgen_data_studio.conformance import normalize_rows
from xgen_data_studio.ir import Column, Query, Ref
from xgen_data_studio.modules import ModuleError
from xgen_data_studio.preview import MODULE_COLOR, MODULE_KIND, TARGETS, _highlight, _ir_text
from xgen_data_studio.roles import apply_role
from xgen_data_studio.studio import Studio

KIND_ORDER = list(MODULE_KIND)
CHECK_LABEL = {"role": "역할 권한", "parameters": "파라미터", "target": "대상 확인", "state": "상태 전이",
               "states": "허용 상태"}
EVENT_LABEL = {"requested": "요청", "rejected": "반려", "approved": "승인", "executed": "원천 반영"}


def plain(v: Any) -> Any:
    """A value the page can show as JSON."""
    if isinstance(v, bool) or v is None or isinstance(v, (int, str)):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else v
    if isinstance(v, Decimal):
        return plain(float(v))
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): plain(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [plain(x) for x in v]
    return str(v)


def principal_keys(node: Any) -> list[str]:
    """The principal attributes a role's row filters ask for, e.g. ['customer_id']."""
    found: list[str] = []
    if isinstance(node, dict):
        if isinstance(node.get("principal"), str):
            found.append(node["principal"])
        for v in node.values():
            found += principal_keys(v)
    elif isinstance(node, list):
        for v in node:
            found += principal_keys(v)
    return list(dict.fromkeys(found))


class StudioSession:
    """One visitor's studio: modules plugged in and out, queries, decisions and approvals, kept apart from others."""

    def __init__(self, studio: Studio, *, llm: Callable[[str, str], str] | None = None):
        self.studio = studio
        self.llm = llm
        self.lock = threading.RLock()
        self.log: list[dict] = []
        self.used = time.time()
        self._library_rows = studio.library.list() if studio.library is not None else []

    # ---- helpers -------------------------------------------------------------------------------------------

    def _note(self, kind: str, text: str, **detail) -> None:
        self.log.insert(0, {"kind": kind, "text": text, **plain(detail)})
        del self.log[30:]

    def _reproject(self) -> dict:
        graphs = [n for n, b in self.studio.backends.items() if b.capabilities.load]
        if not graphs:
            return {}
        try:
            return plain(self.studio.project(into=graphs))
        except Exception as e:  # a composition without bindings has nothing to project
            return {"error": f"{type(e).__name__}: {e}"}

    def _label(self, module: str) -> str:
        row = next((r for r in self._library_rows if r["name"] == module), None)
        if row:
            return row["label"] or module
        comp = self.studio.composition
        return next((m.label or m.name for m in (comp.modules if comp else []) if m.name == module), module)

    def _obj_label(self, name: str) -> str:
        o = self.studio.onto
        return o.objects[name].label or name if name in o.objects else name

    # ---- the whole page ------------------------------------------------------------------------------------

    def state(self) -> dict:
        st, o = self.studio, self.studio.onto
        comp = st.composition
        on = [m.name for m in comp.modules] if comp else [o.name]
        rows = [dict(r) for r in self._library_rows] if self._library_rows else [
            {"name": m.name, "label": m.label, "kind": m.kind, "latest": m.version, "versions": [m.version],
             "requires": [str(r) for r in m.requires], "counts": m.counts(), "description": m.description}
            for m in (comp.modules if comp else [])]
        for r in rows:
            r["on"] = r["name"] in on
            r["kind_label"] = MODULE_KIND.get(r["kind"], r["kind"])
            r["color"] = MODULE_COLOR.get(r["kind"], "#8a96a5")
            r["version"] = next((m.version for m in comp.modules if m.name == r["name"]), r["latest"]) if comp \
                else r["latest"]
        rows.sort(key=lambda r: (KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else 99, r["name"]))
        layers = []
        if comp:
            for k in KIND_ORDER:
                ms = [{"name": m.name, "label": m.label or m.name, "version": m.version}
                      for m in comp.modules if m.kind == k]
                if ms:
                    layers.append({"kind": k, "kind_label": MODULE_KIND[k], "color": MODULE_COLOR[k], "modules": ms})
        roles = [{"name": r.name, "label": r.label or r.name,
                  "principal": principal_keys({k: v for k, v in r.row_filters.items()})}
                 for r in o.roles.values()]
        domains = [m.label or m.name for m in comp.modules if m.kind == "domain"] if comp else [o.label or o.name]
        registered = st.registered()
        return plain({
            "title": " · ".join(domains),
            "modules_on": len(on),
            "library": rows,
            "layers": layers,
            "graph": self.graph(),
            "stats": {"objects": len(o.objects), "links": len(o.links),
                      "properties": sum(len(t.properties) for t in o.objects.values()),
                      "decisions": len(o.decisions), "actions": len(o.actions), "queries": len(o.queries),
                      "questions": len(o.questions)},
            "queries": [{"name": q.name, "label": q.label or q.name, "params": q.params,
                         "example": registered.get(q.name, (None, {}))[1]} for q in o.queries.values()],
            "questions": [{"id": q.id, "text": q.text, "decision": q.decision, "key": q.key, "query": q.query,
                           "params": q.params} for q in o.questions],
            "decisions": [{"name": d.name, "label": d.label or d.name, "target": d.target,
                           "target_label": self._obj_label(d.target)} for d in o.decisions.values()],
            "actions": [{"name": a.name, "label": a.label or a.name, "target": a.target, "parameters": a.parameters,
                         "decisions": [c.decision for c in a.criteria if c.decision], "approval": a.approval}
                        for a in o.actions.values()],
            "roles": roles,
            "backends": [{"name": n, "language": b.capabilities.language, "dialect": b.capabilities.dialect}
                         for n, b in st.backends.items()],
            "targets": [{"id": t, "label": lbl} for t, lbl in TARGETS],
            "ask": self.llm is not None,
            "zen": _has_zen(),
            "log": self.log,
        })

    def graph(self) -> dict:
        st, o = self.studio, self.studio.onto
        comp = st.composition
        nodes, clusters = [], {}
        for t in o.objects.values():
            owner = comp.owner(f"object:{t.name}") if comp else o.name
            clusters.setdefault(owner, self._label(owner))
            nodes.append({"id": t.name, "label": t.label or t.name, "table": t.table, "abstract": t.abstract,
                          "key": t.key, "module": owner})
        edges = [{"source": lk.source, "target": lk.target, "label": lk.label or lk.name, "subtype": False}
                 for lk in o.links.values()]
        edges += [{"source": t.name, "target": t.parent, "label": "하위 유형", "subtype": True}
                  for t in o.objects.values() if t.parent in o.objects]
        return {"nodes": nodes, "edges": edges, "clusters": [{"id": k, "label": v} for k, v in clusters.items()]}

    def object(self, name: str) -> dict:
        st, o = self.studio, self.studio.onto
        t = o.obj(name)
        comp = st.composition
        props = []
        for p in all_props(o, name):
            prop = find_prop(o, name, p)
            inherited = p not in t.properties
            owner = comp.owner(f"property:{name}.{p}") if comp and not inherited else ""
            props.append({"name": p, "label": prop.label or p, "type": prop.type, "unit": prop.unit,
                          "values": prop.values, "required": prop.required, "cite": prop.cite,
                          "column": column_of(o, name, p) if t.table else "", "key": p == t.key,
                          "module": owner, "module_label": self._label(owner) if owner else "",
                          "inherited": inherited})
        links = []
        for lk in o.links.values():
            if name in (lk.source, lk.target):
                out = lk.source == name
                other = lk.target if out else lk.source
                links.append({"name": lk.name if out else (lk.inverse or lk.name), "label": lk.label or lk.name,
                              "other": other, "other_label": self._obj_label(other), "out": out,
                              "cardinality": lk.cardinality})
        children = [c.name for c in o.objects.values() if c.parent == name]
        owner = comp.owner(f"object:{name}") if comp else ""
        return plain({
            "name": name, "label": t.label or name, "description": t.description, "key": t.key, "table": t.table,
            "abstract": t.abstract, "parent": t.parent, "parent_label": self._obj_label(t.parent) if t.parent else "",
            "children": [{"name": c, "label": self._obj_label(c)} for c in children],
            "aligned": t.aligned, "cite": t.cite, "module": owner, "module_label": self._label(owner) if owner else "",
            "touched": [self._label(m) for m in (comp.touched.get(f"object:{name}", []) if comp else [])],
            "states": {"property": t.states.property, "states": t.states.states, "initial": t.states.initial}
            if t.states else None,
            "properties": props, "links": links,
        })

    # ---- modules ---------------------------------------------------------------------------------------------

    def impact(self, name: str, cascade: bool = False) -> dict:
        imp = self.studio.detach_impact(name, cascade=cascade)
        d = imp.to_dict()
        d["label"] = self._label(name)
        d["cascade"] = cascade
        d["dependents_labels"] = [self._label(x) for x in imp.dependents]
        return d

    def detach(self, name: str, cascade: bool = False) -> dict:
        try:
            imp = self.studio.detach(name, cascade=cascade)
        except ModuleError as e:
            imp = getattr(e, "impact", None)
            return {"ok": False, "error": str(e), "impact": imp.to_dict() if imp else None}
        gone = [name, *imp.dependents] if cascade else [name]
        proj = self._reproject()
        warning = _projection_warning(proj)
        self._note("detach", f"{', '.join(self._label(x) for x in gone)} 모듈을 뺐습니다. "
                   f"{len(imp.removed)}개 항목이 빠졌습니다. {warning}".strip(), removed=imp.removed[:12])
        return {"ok": True, "impact": imp.to_dict(), "projection": proj, "warning": warning}

    def attach(self, name: str) -> dict:
        before = {m.name for m in self.studio.composition.modules} if self.studio.composition else set()
        try:
            comp = self.studio.attach(name)
        except ModuleError as e:
            return {"ok": False, "error": str(e)}
        added = [m.name for m in comp.modules if m.name not in before]
        proj = self._reproject()
        warning = _projection_warning(proj)
        self._note("attach", f"{', '.join(self._label(x) for x in added)} 모듈을 꽂았습니다. {warning}".strip(),
                   added=added)
        return {"ok": True, "added": added, "projection": proj, "warning": warning}

    def export_owl(self) -> str:
        from xgen_data_studio.exchange.owl import to_owl

        comp = self.studio.composition
        ttl, _ = to_owl(self.studio.onto, origin=comp.origin if comp else None)
        return ttl

    # ---- queries ---------------------------------------------------------------------------------------------

    def run_query(self, query: str | dict | Query, params: dict | None = None, *, role: str = "",
                  principal: dict | None = None) -> dict:
        st = self.studio
        name = query if isinstance(query, str) else ""
        q = st.query(query)
        values = dict(params or {})
        shown, extra = q, {}
        if role:
            if name and not st.onto.roles[role].can("run", name):
                return {"ok": False, "error": f"{st.onto.roles[role].label or role} 역할은 이 질의를 실행할 수 없습니다."}
            shown, extra = apply_role(st.onto, q, role, principal)
        bound = {**values, **extra}
        translations = []
        for target, label in TARGETS:
            try:
                c = st.translate(shown, target)
                text = c.preview(bound) if set(c.params) <= set(bound) | set(c.literals) else c.text
                translations.append({"target": target, "label": label, "ok": True, "text": text,
                                     "html": _highlight(text, target), "params": c.params})
            except CompileError as e:
                translations.append({"target": target, "label": label, "ok": False, "error": str(e)})
        results, first, agree = [], None, True
        for bname, b in st.backends.items():
            try:
                res = st.run(q, values, backend=bname, role=role or None, principal=principal)
                rows = normalize_rows(res.rows, res.columns, res.compiled.column_types)
                if first is None:
                    first = rows
                elif sorted(map(repr, rows)) != sorted(map(repr, first)):
                    agree = False
                results.append({"backend": bname, "language": b.capabilities.language,
                                "dialect": b.capabilities.dialect, "columns": res.columns, "rows": plain(rows),
                                "ok": True})
            except Exception as e:
                agree = False
                results.append({"backend": bname, "language": b.capabilities.language,
                                "dialect": b.capabilities.dialect, "ok": False, "error": f"{type(e).__name__}: {e}"})
        source = {"ir": _ir_text(q.to_dict())}
        for lang in ("sparql", "cypher"):
            try:
                c = st.translate(q, lang)
                source[lang] = c.preview(values) if set(c.params) <= set(values) | set(c.literals) else c.text
            except CompileError:
                pass
        return plain({"ok": True, "name": name, "label": st.onto.queries[name].label if name else "",
                      "ir": _ir_text(shown.to_dict()), "params": bound, "translations": translations,
                      "results": results, "agree": agree and len(results) > 1, "source": source})

    def run_text(self, language: str, text: str, *, role: str = "", principal: dict | None = None) -> dict:
        if len(text) > 8000:
            return {"ok": False, "error": "쿼리문이 8,000자 한도를 넘었습니다. 줄여서 다시 입력해 주세요."}
        try:
            if language == "sparql":
                from xgen_data_studio.parse.sparql import parse_sparql

                q = parse_sparql(text, self.studio.onto)
            elif language == "cypher":
                from xgen_data_studio.parse.cypher import parse_cypher

                q = parse_cypher(text, self.studio.onto)
            else:
                q = Query.from_dict(json.loads(text))
        except Exception as e:
            return {"ok": False, "error": f"쿼리문을 온톨로지 질의로 읽지 못했습니다. {e}"}
        return self.run_query(q, role=role, principal=principal)

    def ask(self, question: str, *, role: str = "", principal: dict | None = None) -> dict:
        if self.llm is None:
            return {"ok": False, "error": "자연어 질문을 받을 언어 모델이 연결되어 있지 않습니다."}
        from xgen_data_studio.nl import IRGenerator

        gen = IRGenerator(self.studio.onto, self.llm, role=role or None).generate(question[:500])
        if not gen.ok:
            issues = gen.attempts[-1].issues if gen.attempts else []
            return {"ok": False, "error": "질문을 온톨로지 질의로 바꾸지 못했습니다. " + " / ".join(issues[:3])}
        out = self.run_query(gen.registered or gen.query, gen.params, role=role, principal=principal)
        out["attempts"] = len(gen.attempts)
        return out

    # ---- decisions and actions -------------------------------------------------------------------------------

    def keys(self, type_name: str) -> list[dict]:
        o = self.studio.onto
        t = o.obj(type_name)
        names = all_props(o, type_name)
        show = [t.key] + [p for p in [t.title, t.states.property if t.states else ""] if p and p != t.key]
        show += [p for p in names if find_prop(o, type_name, p).type in ("datetime", "date") and p not in show][:1]
        show += [p for p in names if p.endswith("_id") and p not in show][:1]
        q = Query(nodes={"x": type_name}, columns=[Column(Ref("x", p), p) for p in show])
        rows = self.studio.run(q).rows
        out = [{"key": str(r[0]), "fields": {p: plain(v) for p, v in zip(show[1:], r[1:])}} for r in rows]
        return sorted(out, key=lambda x: x["key"])

    def decide(self, name: str, key: str) -> dict:
        st = self.studio
        table = st.onto.decisions[name]
        res = st.decide(name, key)
        outs = res.outputs if isinstance(res.outputs, dict) else {"result": res.outputs}
        zen = None
        if _has_zen():
            try:
                from xgen_data_studio.decide.zen import evaluate_zen

                z = evaluate_zen(table, res.inputs)
                zen = {"outputs": plain(z), "same": plain(z) == plain(res.outputs)}
            except Exception as e:
                zen = {"error": f"{type(e).__name__}: {e}"}
        first = next(iter(table.outputs), "")
        rules = [{"id": r.id, "when": r.when, "then": r.then, "cite": r.cite, "hit": r.id in res.matched}
                 for r in table.rules]
        comp = st.composition
        touched = comp.touched.get(f"decision:{name}", []) if comp else []
        evidence = []
        for e in res.evidence:
            prop = find_prop(st.onto, e.object_type, e.property) if e.object_type and e.property else None
            evidence.append({"input": e.input, "value": e.value, "object": e.object_type,
                             "object_label": self._obj_label(e.object_type), "key": e.key, "property": e.property,
                             "property_label": prop.label if prop else "", "source": e.source})
        actions = [a.name for a in st.onto.actions.values() if any(c.decision == name for c in a.criteria)]
        return plain({
            "name": name, "label": table.label or name, "target": table.target,
            "target_label": self._obj_label(table.target), "key": key, "hit_policy": table.hit_policy,
            "inputs": list(table.inputs), "outputs": list(table.outputs), "result": outs,
            "yes": bool(outs.get(first)) if first else False, "reason": next(
                (v for v in outs.values() if isinstance(v, str)), ""),
            "matched": res.matched, "rules": rules, "values": res.inputs, "evidence": evidence,
            "engine": res.engine, "zen": zen, "notes": res.notes,
            "touched": [self._label(m) for m in touched], "actions": actions,
        })

    def _proposal(self, p) -> dict:
        st = self.studio
        a = st.onto.actions.get(p.action)
        checks = []
        for c in p.checks:
            detail = c.detail
            if c.name.startswith("decision:"):
                d = st.onto.decisions.get(c.name.split(":", 1)[1])
                title = f"판정 · {d.label if d else c.name}"
                try:  # the outputs as they were when the request was checked
                    res = ast.literal_eval(c.detail)
                except (ValueError, SyntaxError):
                    res = None
                detail = ", ".join(f"{k} {_word(v)}" for k, v in res.items()) if isinstance(res, dict) else c.detail
            elif c.name == "role":
                labels = [st.onto.roles[r].label or r for r in p.requested_by.roles if r in st.onto.roles]
                detail = ", ".join(labels) if c.passed else f"{', '.join(labels) or '역할 없음'} 역할에는 요청 권한이 없습니다"
                title = CHECK_LABEL[c.name]
            elif c.name == "target":
                detail = f"{self._obj_label(p.target)} {p.key}"
                title = CHECK_LABEL[c.name]
            elif c.name == "parameters":
                detail = ", ".join(f"{k} {v}" for k, v in p.params.items()) if c.passed else c.detail
                title = CHECK_LABEL[c.name]
            else:
                detail = c.detail.replace("->", "→")
                title = CHECK_LABEL.get(c.name, c.name)
            checks.append({"name": c.name, "title": title, "passed": c.passed, "detail": detail})
        return plain({"id": p.id, "action": p.action, "label": a.label if a else p.action, "target": p.target,
                      "target_label": self._obj_label(p.target), "key": p.key, "params": p.params,
                      "requested_by": p.requested_by.id, "status": p.status, "checks": checks,
                      "changes": p.changes, "before": p.before, "approved_by": p.approved_by})

    def request(self, action: str, key: str, params: dict, role: str) -> dict:
        actor = Actor(self.studio.onto.roles[role].label or role if role else "에이전트", "agent",
                      [role] if role else [])
        p = self.studio.actions.request(action, key, params, actor=actor)
        state = "승인을 기다립니다." if p.status == "pending" else "검사를 통과하지 못해 반려했습니다."
        self._note("request", f"요청: {actor.id}, {self._obj_label(p.target)} {key} {self._proposal(p)['label']}. {state}")
        return {"ok": True, "proposal": self._proposal(p)}

    def approve(self, proposal_id: str, approve: bool) -> dict:
        approver_role = next((r.name for r in self.studio.onto.roles.values()
                              if any(r.can("execute", a) for a in self.studio.onto.actions)), "")
        approver = Actor("운영자", "human", [approver_role] if approver_role else [])
        acts = self.studio.actions
        try:
            p = acts.approve(proposal_id, approver=approver) if approve else \
                acts.reject(proposal_id, approver=approver, reason="화면에서 반려")
        except (PermissionError, ValueError, RuntimeError) as e:
            return {"ok": False, "error": str(e)}
        proj = self._reproject() if p.status == "executed" else {}
        verb = "승인해 원천에 반영했습니다" if p.status == "executed" else "반려했습니다"
        self._note("approve", f"요청 {p.id}: 운영자가 {verb}.", projection=proj)
        return {"ok": True, "proposal": self._proposal(p), "projection": proj}

    def audit(self) -> list[dict]:
        return [{"at": a.at, "actor": a.actor, "kind": a.actor_kind, "event": EVENT_LABEL.get(a.event, a.event),
                 "proposal": a.proposal, "key": a.key, "detail": plain(a.detail)}
                for a in reversed(self.studio.actions.audit)]

    # ---- checks ----------------------------------------------------------------------------------------------

    def questions(self) -> dict:
        st = self.studio
        rep = st.questions()
        conf = None
        if len(st.backends) > 1:
            try:
                c = st.conformance()
                conf = {"passed": c.passed, "summary": c.summary(),
                        "queries": [{"name": r.name, "label": st.onto.queries[r.name].label or r.name,
                                     "agree": r.agree, "detail": r.detail,
                                     "rows": {b: (len(o.rows) if o.rows is not None else None)
                                              for b, o in r.outcomes.items()},
                                     "errors": {b: o.error for b, o in r.outcomes.items() if o.error}}
                                    for r in c.queries]}
            except Exception as e:
                conf = {"passed": False, "error": f"{type(e).__name__}: {e}"}
        return plain({"accuracy": rep.accuracy, "results": [r.__dict__ for r in rep.results],
                      "conformance": conf})

    def bindings(self) -> dict:
        source = self.studio.source
        if not source:
            return {"ok": False, "error": "대조할 원천 데이터베이스가 연결되어 있지 않습니다."}
        rep = self.studio.check_bindings()
        return plain({"ok": rep.ok, "checked": rep.checked, "backend": source,
                      "findings": [f.__dict__ for f in rep.findings]})


def _word(v: Any) -> str:
    return ("true" if v else "false") if isinstance(v, bool) else str(plain(v))


def _projection_warning(proj: dict) -> str:
    if "error" not in proj:
        return ""
    return "원천 DB가 이 정의와 맞지 않아 그래프 저장소에 반영하지 못했습니다. DB 대조에서 확인해 주세요."


_ZEN: bool | None = None


def _has_zen() -> bool:
    global _ZEN
    if _ZEN is None:
        try:
            import zen  # noqa: F401

            _ZEN = True
        except ImportError:
            _ZEN = False
    return _ZEN
