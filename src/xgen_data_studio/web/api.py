"""What the studio page asks for, answered from one studio as plain dicts."""
from __future__ import annotations

import ast
import json
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from xgen_data_studio.actions import Actor
from xgen_data_studio.check import all_props, column_of, find_prop
from xgen_data_studio.compile.base import CompileError, compiler_for
from xgen_data_studio.conformance import normalize_rows
from xgen_data_studio.ir import Column, Query, Ref
from xgen_data_studio.library import OverlayLibrary
from xgen_data_studio.modules import Module, ModuleError, compose
from xgen_data_studio.preview import MODULE_COLOR, MODULE_KIND, TARGETS, _highlight, _ir_text
from xgen_data_studio.roles import apply_role
from xgen_data_studio.studio import Studio

KIND_ORDER = list(MODULE_KIND)
CHECK_LABEL = {"role": "역할 권한", "parameters": "파라미터", "target": "대상 확인", "state": "상태 전이",
               "states": "허용 상태", "call": "외부 호출"}
EVENT_LABEL = {"requested": "요청", "rejected": "반려", "approved": "승인", "executed": "원천 반영",
               "written": "원천 기록", "called": "외부 호출", "call_failed": "외부 호출 실패 · 원천 복원",
               "rolled_back": "되돌림"}
GATE_LABEL = {("bind", "max_errors"): "DB 대조 오류 최대", ("bind", "max_warnings"): "DB 대조 경고 최대",
              ("query", "min_agree"): "백엔드 결과 일치율 최소", ("decide", "min_agreement"): "판정 일치율 최소",
              ("check", "min_accuracy"): "검증 질문 정답률 최소", ("check", "min_grounded"): "근거 제시율 최소"}
STAGE_LABEL = {"source": "원천 데이터", "define": "온톨로지 정의", "bind": "DB 대조", "project": "그래프 저장소 반영",
               "query": "질의", "decide": "판정 · 처리", "check": "검증"}
CHANGE_STATUS = {"pending": "승인 대기", "approved": "승인 · 적용", "rejected": "반려"}
READ_ERROR = {
    "format": "지원하지 않는 파일 형식이라 업로드하지 못했습니다. CSV, TSV, XLSX 파일을 업로드해 주세요.",
    "encoding": "파일 인코딩을 확인할 수 없어 읽지 못했습니다. UTF-8 또는 CP949로 저장해 다시 업로드해 주세요.",
    "empty": "데이터 행이 없어 테이블을 만들지 못했습니다. 첫 행에 컬럼 이름이 있는지 확인해 주세요.",
    "workbook": "XLSX 형식이 아니어서 파일을 열지 못했습니다. XLSX로 저장해 다시 업로드해 주세요.",
    "workbook_size": "압축 해제 크기가 64MB 한도를 초과해 파일을 열지 못했습니다. 시트를 나누어 다시 업로드해 주세요.",
    "openpyxl": "Excel 읽기 모듈이 설치되지 않아 XLSX 파일을 처리하지 못했습니다. CSV로 저장해 업로드해 주세요.",
}
MODULE_TEXT_MAX = 48 * 1024
ASK_RETRY_WITHIN = 45.0  # seconds into a natural-language question after which no further attempt starts
POLICY_MAX = 12000  # characters of policy text a draft reads
WORKSPACE = "workspace"  # the module the management screens' edits are filed as (manage.NAME)
EDIT_TEXT = [
    (r"^unknown edit '(.+)'$", r"지원하지 않는 편집(\1)이라 적용하지 못했습니다."),
    (r"^(object|property|link) name '(.*)' must be letters, digits and _ starting with a letter$",
     r"이름 '\2'은 영문자로 시작하고 영문자 · 숫자 · _ 만 쓸 수 있어 만들지 못했습니다."),
    (r"^object type '(.+)' already exists$", r"객체 '\1'이 이미 있어 추가하지 못했습니다. 다른 이름을 입력해 주세요."),
    (r"^give the key and the key property$", "키 속성을 정하지 않아 객체를 추가하지 못했습니다. 키와 키 속성을 입력해 주세요."),
    (r"^object type '(.+)' is unknown$", r"객체 '\1'을 찾지 못했습니다. 화면을 새로 고쳐 주세요."),
    (r"^key '(.+)' is not a property of (.+)$", r"'\1'은 \2의 속성이 아니어서 키로 정하지 못했습니다."),
    (r"^the key of (.+) is set where it is defined; change it there$",
     r"\1의 키는 표준 모듈에서 정해져 있어 여기서 바꾸지 못했습니다. 해당 모듈에서 바꿔 주세요."),
    (r"^(.+) already has '(.+)'$", r"\1에 속성 '\2'이 이미 있어 추가하지 못했습니다."),
    (r"^(\w+)\.(\w+) is unknown$", r"속성 \1.\2을 찾지 못했습니다. 화면을 새로 고쳐 주세요."),
    (r"^the type of (.+) comes from its standard; it cannot be changed here$",
     r"\1의 자료형은 표준 모듈에서 정해져 있어 바꾸지 못했습니다. 새 속성을 추가해 주세요."),
    (r"^'(.+)' is the key of (.+); delete the object instead$",
     r"'\1'은 \2의 키라서 지우지 못했습니다. 객체를 지워 주세요."),
    (r"^'(.+)' comes from (.+), which (.+) specialises; delete it on (.+)$",
     r"'\1'은 상위 객체 \2에서 물려받은 속성이라 \3에서 지우지 못했습니다. \2에서 지워 주세요."),
    (r"^link '(.+)' already exists$", r"관계 '\1'이 이미 있어 추가하지 못했습니다. 다른 이름을 입력해 주세요."),
    (r"^link '(.+)' is unknown$", r"관계 '\1'을 찾지 못했습니다. 화면을 새로 고쳐 주세요."),
    (r"^the endpoints of (.+) come from its standard; add a new link instead$",
     r"\1의 양 끝 객체는 표준 모듈에서 정해져 있어 바꾸지 못했습니다. 새 관계를 추가해 주세요."),
    (r"^question id '(.*)' is empty or already used$",
     r"질문 번호 '\1'이 비어 있거나 이미 있어 추가하지 못했습니다. 다른 번호를 입력해 주세요."),
    (r"^question '(.+)' is unknown$", r"검증 질문 '\1'을 찾지 못했습니다. 화면을 새로 고쳐 주세요."),
]
GAP_TEXT = [(r"^no rule matched$", "적용된 규칙 없음"), (r"^rule (\S+) has no cite$", r"규칙 \1 출처 없음"),
            (r"^(\S+) has no source column$", r"\1 원천 컬럼 없음"), (r"^no version$", "판본 없음"),
            (r"^no answer$", "답 없음")]


def _edit_text(msg: str) -> str:
    """A management edit's refusal, as the page says it; checks the definition raises keep their own words."""
    for pattern, text in EDIT_TEXT:
        if re.match(pattern, msg):
            return re.sub(pattern, text, msg)
    return f"정의 검사를 통과하지 못해 적용하지 않았습니다. {msg}"


def _gap_text(gap: str) -> str:
    """What a question's answer lacks of its grounds, as the page says it."""
    for pattern, text in GAP_TEXT:
        if re.match(pattern, gap):
            return re.sub(pattern, text, gap)
    return gap


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


@dataclass
class DataOptions:
    """What a visitor may bring in: files within these limits, the bundled samples, and (off unless asked) a database."""

    file_bytes: int = 1 << 20
    total_bytes: int = 4 << 20
    files: int = 8
    rows: int = 10_000
    columns: int = 80
    samples: Path | None = None
    allow_connect: bool = False
    policies: Path | None = None  # example policy texts (.md, .txt) for drafting rules


class StudioSession:
    """One visitor's studio: modules plugged in and out, queries, decisions and approvals, kept apart from others."""

    def __init__(self, studio: Studio, *, llm: Callable[[str, str], str] | None = None,
                 data: DataOptions | None = None, origin: dict | None = None):
        self.studio = studio
        self.llm = llm
        self.data = data or DataOptions()
        self.origin = origin or {"kind": "config"}
        self.lock = threading.RLock()
        self.log: list[dict] = []
        self.used = time.time()
        if studio.library is not None and not isinstance(studio.library, OverlayLibrary):
            studio.library = OverlayLibrary(studio.library, [])  # a visitor's edited modules are kept here
        self._library_rows = studio.library.list() if studio.library is not None else []
        self.uploads: dict[str, list] = {}  # file name -> the tables read from it
        self.sizes: dict[str, int] = {}
        self.pending = None  # (draft, the database it was drawn from, the tables loaded into it, the rules)
        self.who = "방문자"  # the person behind the requests; a team studio sets it from the login
        self.self_approve = True  # one visitor is both sides of a change; a team studio turns this off
        self.store = None  # a library folder approved changes are written to (xds serve --library-write)
        self.workspace = None  # the management screens' pending edits (manage.Workspace), until filed
        self._ws_sig: tuple = ()
        self._adopt(studio)

    def _adopt(self, studio: Studio) -> None:
        """Make a studio this session's: its change requests follow the session's approval and storage."""
        self.studio = studio
        studio.changes.self_approve = self.self_approve
        studio.changes.store = self.store

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
            "origin": self.origin,
            "data": {"samples": bool(self._sample_files()), "connect": self.data.allow_connect,
                     "files": len(self.uploads),
                     "policy_sample": bool(self._policy_files())},
            "identities": [{"name": i.name, "label": i.label or i.name} for i in o.identities.values()],
            "who": self.who, "self_approve": self.self_approve,
            "changes": sum(c.status == "pending" for c in st.changes.requests.values()),
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
        edges = [{"id": lk.name, "source": lk.source, "target": lk.target, "label": lk.label or lk.name,
                  "subtype": False} for lk in o.links.values()]
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
                          "column": column_of(o, name, p) if t.table and not prop.expr else "", "key": p == t.key,
                          "module": owner, "module_label": self._label(owner) if owner else "",
                          "inherited": inherited, "expr": prop.expr, "mask": prop.mask,
                          "description": prop.description})
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
            "states": {"property": t.states.property, "states": t.states.states, "initial": t.states.initial,
                       "transitions": [{"from": x.source, "to": x.target} for x in t.states.transitions]}
            if t.states else None,
            "series": dict(t.series), "identity": name in o.identities,
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
        self._note("detach", f"{', '.join(self._label(x) for x in gone)} 모듈을 해제했습니다. "
                   f"항목 {len(imp.removed)}개가 제거되었습니다. {warning}".strip(), removed=imp.removed[:12])
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
        self._note("attach", f"{', '.join(self._label(x) for x in added)} 모듈을 적용했습니다. {warning}".strip(),
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
                return {"ok": False, "error": f"{st.onto.roles[role].label or role} 역할에 실행 권한이 없어 질의를 실행하지 못했습니다."}
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
                                "ok": True, "masked": res.masked})
            except Exception as e:
                agree = False
                results.append({"backend": bname, "language": b.capabilities.language,
                                "dialect": b.capabilities.dialect, "ok": False, "error": f"{type(e).__name__}: {e}"})
        source = {"ir": _ir_text(q.to_dict())}
        for lang in ("sparql", "cypher"):  # what a person would write: computed properties by their names
            try:
                comp = compiler_for(st.onto, lang)
                comp.by_name = True
                c = comp.compile(q)
                source[lang] = c.preview(values) if set(c.params) <= set(values) | set(c.literals) else c.text
            except CompileError:
                pass
        return plain({"ok": True, "name": name, "label": st.onto.queries[name].label if name else "",
                      "ir": _ir_text(shown.to_dict()), "params": bound, "translations": translations,
                      "results": results, "agree": agree and len(results) > 1, "source": source})

    def run_text(self, language: str, text: str, *, role: str = "", principal: dict | None = None) -> dict:
        if len(text) > 8000:
            return {"ok": False, "error": "쿼리 길이가 8,000자 한도를 초과해 실행하지 못했습니다. 쿼리를 줄여 다시 입력해 주세요."}
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
            return {"ok": False, "error": f"쿼리 문법을 해석하지 못했습니다. {e}"}
        return self.run_query(q, role=role, principal=principal)

    def ask(self, question: str, *, role: str = "", principal: dict | None = None) -> dict:
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 자연어 질문을 처리하지 못했습니다."}
        from xgen_data_studio.nl import IRGenerator, probe

        llm, tries = self._budgeted()
        gen = IRGenerator(self.studio.onto, llm, role=role or None,
                          runner=probe(self.studio, role=role or None, principal=principal)).generate(question[:500])
        if not gen.ok:
            answered = [a for a in gen.attempts if a.raw]  # what the model last said, not the attempt time stopped
            issues = (answered or gen.attempts)[-1].issues if gen.attempts else []
            late = " 응답 시간 한도로 다시 시도하지 못했습니다." if len(tries) < len(gen.attempts) else ""
            return {"ok": False, "error": "질문을 질의로 변환하지 못했습니다. " + " / ".join(issues[:3]) + late
                                          + " 질문을 바꿔 다시 입력해 주세요."}
        out = self.run_query(gen.registered or gen.query, gen.params, role=role, principal=principal)
        out["attempts"] = len(gen.attempts)
        return out

    def _budgeted(self) -> tuple[Callable[[str, str], str], list]:
        """The model for one page request, and the calls it has made. A proxy in front of the page may give up on
        a request (Cloudflare at 100 s) and a model that reasons first takes 20 to 40 s: another attempt starts only
        early enough to end in time."""
        started, tries = time.monotonic(), []

        def llm(system: str, user: str) -> str:
            if tries and time.monotonic() - started > ASK_RETRY_WITHIN:
                raise TimeoutError("no time left for another attempt")
            tries.append(1)
            return self.llm(system, user)

        return llm, tries

    def _policy_files(self) -> list[Path]:
        d = self.data.policies
        if not d or not Path(d).is_dir():
            return []
        return sorted(p for p in Path(d).iterdir() if p.suffix.lower() in (".md", ".txt"))

    def policy_sample(self) -> dict:
        found = self._policy_files()
        if not found:
            return {"ok": False, "error": "예시 정책서가 설정되지 않아 불러오지 못했습니다."}
        return {"ok": True, "name": found[0].name, "text": found[0].read_text(encoding="utf-8")[:POLICY_MAX]}

    def policy_draft(self, text: str, target: str = "", name: str = "") -> dict:
        """A decision table drafted from policy text by the model and checked by the engine, as module text for
        the editor; a person files it as a change request (see policy.py)."""
        if self.llm is None:
            return {"ok": False, "error": "언어 모델이 연결되어 있지 않아 정책서 규칙 초안을 만들지 못했습니다."}
        text = str(text or "").strip()[:POLICY_MAX]
        if not text:
            raise ValueError("정책서 내용이 없어 규칙 초안을 만들지 못했습니다. 정책서 조항을 입력해 주세요.")
        comp = self.studio.composition
        if comp is None:
            return {"ok": False, "error": "모듈로 구성된 스튜디오가 아니어서 규칙 초안을 모듈로 만들지 못했습니다."}
        if target and target not in self.studio.onto.objects:
            raise ValueError(f"대상 객체 {target} 이(가) 정의에 없어 규칙 초안을 만들지 못했습니다. 대상을 다시 선택해 주세요.")
        import yaml

        from xgen_data_studio.policy import PolicyDrafter

        llm, tries = self._budgeted()
        d = PolicyDrafter(list(comp.modules), llm, compose_kw=self.studio._compose_kw).draft(
            text, target=target, name=str(name or ""))
        late = " 응답 시간 한도로 다시 시도하지 못했습니다." if len(tries) < len(d.attempts) else ""
        if d.module is None:
            answered = [a for a in d.attempts if a.raw]
            issues = (answered or d.attempts)[-1].issues if d.attempts else []
            return {"ok": False, "error": "정책서를 결정표로 바꾸지 못했습니다. " + " / ".join(issues[:3]) + late
                                          + " 정책서 내용이나 대상을 바꿔 다시 시도해 주세요."}
        (dname, table), = d.module.body["decisions"].items()
        return plain({
            "ok": True, "module": d.module.name, "label": d.module.label, "decision": dname, "target": table["target"],
            "yaml": yaml.safe_dump(d.module.to_dict(), allow_unicode=True, sort_keys=False, default_flow_style=None,
                                   width=110),
            "inputs": [{"name": k, **v} for k, v in (table.get("inputs") or {}).items()],
            "rules": [{"id": r.get("id"), "when": r.get("when") or {}, "then": r.get("then") or {},
                       "cite": r.get("cite", "")} for r in table.get("rules") or []],
            "issues": d.issues, "attempts": len(d.attempts), "late": bool(late)})

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
                detail = ", ".join(labels) if c.passed else f"{', '.join(labels) or '역할 없음'} 역할에 요청 권한이 없습니다"
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
                      "changes": p.changes, "before": p.before, "approved_by": p.approved_by, "call": p.call,
                      "rolled_back_by": p.rolled_back_by, "can_roll_back": p.status == "executed" and (
                          not (a and a.call) or bool(a and a.undo))})

    def request(self, action: str, key: str, params: dict, role: str) -> dict:
        actor = Actor(self.studio.onto.roles[role].label or role if role else "에이전트", "agent",
                      [role] if role else [])
        p = self.studio.actions.request(action, key, params, actor=actor)
        state = "승인 대기 중입니다." if p.status == "pending" else "검사를 통과하지 못해 반려되었습니다."
        self._note("request", f"요청 접수: {actor.id}, {self._obj_label(p.target)} {key} {self._proposal(p)['label']}. "
                   f"{state}")
        return {"ok": True, "proposal": self._proposal(p)}

    def _approver(self) -> Actor:
        approver_role = next((r.name for r in self.studio.onto.roles.values()
                              if any(r.can("execute", a) for a in self.studio.onto.actions)), "")
        return Actor(self.who if self.who != "방문자" else "운영자", "human", [approver_role] if approver_role else [])

    def rollback(self, proposal_id: str) -> dict:
        from xgen_data_studio.actions import ActionError

        try:
            p = self.studio.actions.rollback(proposal_id, actor=self._approver(), reason="화면에서 되돌림")
        except (ActionError, PermissionError) as e:
            return {"ok": False, "error": f"되돌릴 수 없는 상태라 되돌리지 못했습니다. {e}"}
        proj = self._reproject()
        self._note("approve", f"요청 {p.id}: 실행 전 값으로 되돌렸습니다.", projection=proj)
        return {"ok": True, "proposal": self._proposal(p), "projection": proj}

    def approve(self, proposal_id: str, approve: bool) -> dict:
        approver = self._approver()
        acts = self.studio.actions
        try:
            p = acts.approve(proposal_id, approver=approver) if approve else \
                acts.reject(proposal_id, approver=approver, reason="운영자 반려")
        except (PermissionError, ValueError, RuntimeError) as e:
            return {"ok": False, "error": str(e)}
        proj = self._reproject() if p.status == "executed" else {}
        verb = {"executed": "승인 후 원천 DB에 반영했습니다", "failed": "외부 호출이 실패해 원천 DB를 실행 전 값으로 복원했습니다"
                }.get(p.status, "반려했습니다")
        self._note("approve", f"요청 {p.id}: {verb}.", projection=proj)
        return {"ok": True, "proposal": self._proposal(p), "projection": proj}

    def audit(self) -> list[dict]:
        return [{"at": a.at, "actor": a.actor, "kind": a.actor_kind, "event": EVENT_LABEL.get(a.event, a.event),
                 "proposal": a.proposal, "key": a.key, "detail": plain(a.detail)}
                for a in reversed(self.studio.actions.audit)]

    # ---- data in: files or a database, drafted into modules, plugged in ---------------------------------------

    def _sample_files(self) -> list[Path]:
        d = self.data.samples
        if d is None or not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.suffix.lower() in (".csv", ".tsv", ".xlsx"))

    def files_state(self) -> dict:
        lim = self.data
        files = [{"source": src, "bytes": self.sizes.get(src, 0),
                  "tables": [{"name": t.name, "sheet": t.source, "rows": len(t.rows), "columns": t.columns,
                              "truncated": t.truncated, "preview": t.rows[:5]} for t in ts]}
                 for src, ts in self.uploads.items()]
        from xgen_data_studio.draft import DraftRules

        base = DraftRules.from_dict(self._method_rules())  # an attached method module's rules, or the defaults
        rules = self.pending[3] if self.pending else base
        comp = self.studio.composition
        return plain({"files": files, "pending": self._draft_view() if self.pending else None,
                      "rules": rules.to_dict(), "defaults": base.to_dict(),
                      "rules_by": [self._label(m) for m in (comp.rules_by if comp else [])],
                      "limits": {"file_bytes": lim.file_bytes, "total_bytes": lim.total_bytes, "files": lim.files,
                                 "rows": lim.rows, "columns": lim.columns},
                      "samples": [p.name for p in self._sample_files()], "connect": lim.allow_connect})

    def upload(self, source: str, data: bytes) -> dict:
        from xgen_data_studio.draft import ReadError, read_file

        lim = self.data
        source = Path(source.replace("\\", "/")).name[:120] or "file.csv"
        others = {k: v for k, v in self.sizes.items() if k != source}
        if len(data) > lim.file_bytes:
            raise ValueError(f"{source}: 파일 크기가 {_size(lim.file_bytes)} 한도를 초과해 업로드하지 못했습니다. "
                             "파일을 나누어 다시 업로드해 주세요.")
        if len(others) >= lim.files:
            raise ValueError(f"업로드 파일 수가 {lim.files}개 한도에 도달해 추가하지 못했습니다. "
                             "파일을 삭제한 뒤 다시 업로드해 주세요.")
        if sum(others.values()) + len(data) > lim.total_bytes:
            raise ValueError(f"전체 업로드 용량이 {_size(lim.total_bytes)} 한도를 초과해 업로드하지 못했습니다. "
                             "파일을 삭제한 뒤 다시 업로드해 주세요.")
        try:
            tables = read_file(data, source, max_rows=lim.rows)
        except ReadError as e:
            raise ValueError(f"{source}: " + READ_ERROR.get(
                e.reason, "파일을 테이블로 읽지 못했습니다. 파일 형식을 확인해 주세요.")) from None
        wide = [t.name for t in tables if len(t.columns) > lim.columns]
        if wide:
            raise ValueError(f"{', '.join(wide)}: 컬럼 수가 {lim.columns}개 한도를 초과해 업로드하지 못했습니다. "
                             "컬럼을 줄여 다시 업로드해 주세요.")
        self.uploads = {**{k: v for k, v in self.uploads.items() if k != source}, source: tables}
        self.sizes = {**others, source: len(data)}
        self.pending = None
        return self.files_state()

    def use_samples(self) -> dict:
        files = self._sample_files()
        if not files:
            raise ValueError("샘플 데이터가 설정되지 않아 불러오지 못했습니다.")
        self.uploads, self.sizes, self.pending = {}, {}, None
        for p in files:
            self.upload(p.name, p.read_bytes())
        return self.files_state()

    def remove_file(self, source: str) -> dict:
        self.uploads.pop(source, None)
        self.sizes.pop(source, None)
        self.pending = None
        return self.files_state()

    def _method_rules(self) -> dict:
        comp = self.studio.composition
        return dict(comp.draft_rules) if comp else {}

    def _rules(self, rules: dict | None):
        from xgen_data_studio.draft import DraftRules

        try:  # what the visitor set, over an attached method module's rules
            return DraftRules.from_dict({**self._method_rules(), **(rules if isinstance(rules, dict) else {})})
        except (TypeError, ValueError):
            raise ValueError("생성 설정 값을 확인할 수 없어 초안을 생성하지 못했습니다. 숫자 항목을 확인해 주세요.") from None

    def make_draft(self, label: str = "", rules: dict | None = None, tables: list | None = None) -> dict:
        from xgen_data_studio.backends.sql import SqliteBackend
        from xgen_data_studio.draft import draft, load_sqlite

        all_tables = [t for ts in self.uploads.values() for t in ts]
        if not all_tables:
            raise ValueError("업로드한 파일이 없어 초안을 생성하지 못했습니다. 파일을 업로드해 주세요.")
        wanted = {str(x) for x in tables} if tables else None
        chosen = [t for t in all_tables if wanted is None or t.name in wanted]
        if not chosen:
            raise ValueError("선택된 테이블이 없어 초안을 생성하지 못했습니다. 테이블을 하나 이상 선택해 주세요.")
        r = self._rules(rules)
        b = SqliteBackend()
        loaded = load_sqlite(chosen, b, row_keys=r.row_keys)
        d = draft(b, name="my-data", label=(label or "내 데이터")[:40], loaded=loaded, lang="ko", rules=r,
                  origin={"kind": "files", "files": list(self.uploads), "detail": f"업로드 파일 {len(self.uploads)}개"})
        self.pending = (d, b, chosen, r)
        return self.files_state()

    def connect(self, dsn: str, label: str = "", rules: dict | None = None) -> dict:
        if not self.data.allow_connect:
            raise PermissionError("공개 데모에서는 DB 연결이 비활성화되어 있어 연결하지 못했습니다. 파일 업로드를 이용해 주세요.")
        from xgen_data_studio.config import open_backend
        from xgen_data_studio.draft import draft

        dsn = dsn.strip()
        u = urlparse(dsn)
        if u.scheme in ("postgres", "postgresql"):
            b = open_backend({"kind": "postgres", "dsn": dsn}, Path("."))
            where = f"PostgreSQL {u.hostname or 'localhost'}{u.path}"  # never the user or the password
        else:
            path = dsn[len("sqlite:///"):] if dsn.startswith("sqlite:///") else dsn
            if not Path(path).is_file():
                raise ValueError("연결 주소를 확인할 수 없어 연결하지 못했습니다. "
                                 "postgresql:// 주소 또는 SQLite 파일 경로를 입력해 주세요.")
            b = open_backend({"kind": "sqlite", "path": str(Path(path).resolve())}, Path("."))
            where = f"SQLite {Path(path).name}"
        r = self._rules(rules)
        d = draft(b, name="my-db", label=(label or "내 데이터베이스")[:40], lang="ko", rules=r,
                  origin={"kind": "database", "detail": where})
        self.uploads, self.sizes = {}, {}
        self.pending = (d, b, [], r)
        return self.files_state()

    def _draft_view(self) -> dict:
        d = self.pending[0]
        return {"label": d.label, "origin": d.origin, "steps": d.steps(), **self._revised(d)}

    @staticmethod
    def _revised(d) -> dict:
        """What a draft would plug in: the graph, the two module files, and the checks it does not pass."""
        import yaml

        modules = d.modules()
        comp = compose(modules, name=d.name)
        graph = StudioSession(Studio.from_modules(modules, name=d.name)).graph() if not comp.issues else None
        return {"graph": graph, "issues": list(comp.issues), "queries": list(d.queries()),
                "query_items": [{"element": f"query:{k}", "label": v["label"], "on": k not in d.no_queries}
                                for k, v in d.queries(dropped=True).items()],
                "counts": {"objects": len(d.objects), "links": len(d.links),
                           "properties": sum(len(o.properties) for o in d.objects), "queries": len(d.queries()),
                           "states": len(d.states), "actions": len(d.actions()), "roles": len(d.roles()),
                           "questions": len(d.questions()), "decisions": len(d.decisions)},
                "modules": [{"name": m.name, "kind": m.kind, "label": m.label,
                             "yaml": yaml.safe_dump(m.to_dict(), allow_unicode=True, sort_keys=False)}
                            for m in modules]}

    @staticmethod
    def _edit(d, edits: dict | None):
        """The page's edits as revise() takes them."""
        e = edits if isinstance(edits, dict) else {}

        def pairs(k: str) -> dict:
            v = e.get(k)
            return {str(a): str(b) for a, b in v.items()} if isinstance(v, dict) else {}

        values = {}
        for k, v in (e.get("values") or {}).items():
            items = v.split(",") if isinstance(v, str) else v if isinstance(v, list) else []
            values[str(k)] = [str(x).strip() for x in items if str(x).strip()]
        return d.revise(drop=[str(x) for x in e.get("drop") or []],
                        labels={k: v[:60] for k, v in pairs("labels").items() if v.strip()},
                        keys=pairs("keys"), types=pairs("types"), values=values, cardinality=pairs("cardinality"),
                        add_links=[x for x in e.get("add_links") or [] if isinstance(x, dict)])

    # ---- a decision table from past outcomes, and bindings onto a standard ----------------------------------------

    def induce_decision(self, target: str, inputs: list, label: str = "", edits: dict | None = None) -> dict:
        from xgen_data_studio.induce import InduceError, induce

        if not self.pending:
            raise ValueError("생성된 초안이 없어 판정 표를 만들지 못했습니다. 초안을 먼저 생성해 주세요.")
        d0, b, _, _ = self.pending
        try:
            d = self._edit(d0, edits)
            onto = compose(d.modules(), name=d.name).ontology
            out = induce(b, onto, str(target), [str(x) for x in inputs or []], label=label[:60])
        except (InduceError, ValueError) as e:
            return {"ok": False, "error": f"판정 표를 만들지 못했습니다. {e}"}
        d0.decisions[out["name"]] = {**out["decision"], "report": out["report"]}
        self._note("draft", f"{out['decision']['label']}: 지난 {out['report']['cases']}건으로 규칙 "
                            f"{out['report']['rules']}개를 만들었습니다.")
        return plain({"ok": True, **out})

    def drop_decision(self, name: str) -> dict:
        if self.pending:
            self.pending[0].decisions.pop(name, None)
        return {"ok": True}

    def standards(self) -> dict:
        lib = self.studio.library
        rows = lib.list() if lib is not None else []
        return {"standards": [{"name": r["name"], "label": r["label"] or r["name"], "kind": r["kind"],
                               "kind_label": MODULE_KIND.get(r["kind"], r["kind"])}
                              for r in rows if r["kind"] in ("domain", "industry")]}

    def _standard(self, names: list) -> tuple[list[Module], Any]:
        lib = self.studio.library
        if lib is None:
            raise ValueError("라이브러리가 없어 표준에 연결하지 못했습니다.")
        names = [str(n) for n in names or []]
        if not names:
            raise ValueError("연결할 표준 모듈을 선택하지 않아 제안을 만들지 못했습니다. 표준 모듈을 선택해 주세요.")
        try:
            mods = lib.resolve(names)
            onto = compose(mods, **self.studio._compose_kw).ontology
        except ModuleError as e:
            raise ValueError(f"표준 모듈을 구성하지 못했습니다. {e}") from None
        return mods, onto

    def suggest_mapping(self, standard: list, edits: dict | None = None) -> dict:
        from xgen_data_studio.mapping import suggest

        if not self.pending:
            raise ValueError("생성된 초안이 없어 연결을 제안하지 못했습니다. 초안을 먼저 생성해 주세요.")
        _, onto = self._standard(standard)
        d = self._edit(self.pending[0], edits)
        s = suggest(d, onto, [str(x) for x in standard])
        objs = []
        for m in s.objects:
            o = onto.objects[m.object]
            objs.append({**m.__dict__, "label": o.label or m.object,
                         "columns": [{**c.__dict__, "label": (find_prop(onto, m.object, c.property).label
                                                              or c.property)} for c in m.columns],
                         "missing": [{"property": p, "label": find_prop(onto, m.object, p).label or p}
                                     for p in m.missing]})
        tables = [{"table": o.table, "columns": [p.column for p in o.properties]} for o in d.objects]
        return plain({"ok": True, "objects": objs, "links": s.links, "unmatched_tables": s.unmatched_tables,
                      "unbound_objects": [{"name": t, "label": onto.objects[t].label or t} for t in s.unbound_objects],
                      "tables": tables, "standard": [str(x) for x in standard]})

    def apply_mapping(self, standard: list, edits: dict | None = None, mapping: dict | None = None) -> dict:
        from xgen_data_studio.backends.rdf import RdflibBackend
        from xgen_data_studio.draft import LABELS
        from xgen_data_studio.mapping import binding, suggest

        if not self.pending:
            raise ValueError("생성된 초안이 없어 표준에 연결하지 못했습니다. 초안을 먼저 생성해 주세요.")
        mods, onto = self._standard(standard)
        d = self._edit(self.pending[0], edits)
        s = suggest(d, onto, [str(x) for x in standard])
        m = binding(s, onto, name=f"{d.name}-standard", label=f"{d.label} 표준 연결", edits=mapping or {}, base=mods)
        comp = compose([*mods, m], **self.studio._compose_kw)
        if comp.issues:
            raise ValueError("정의 검사에서 오류가 발견되어 연결하지 못했습니다. " + "; ".join(comp.issues[:5]))

        def build() -> Studio:
            st = Studio.from_modules([*mods, m], library=OverlayLibrary(self.studio.library, [m]),
                                     use_zen=self.studio.use_zen, **self.studio._compose_kw)
            st.add_backend("source", self.pending[1], source=True)
            st.add_backend("graph", RdflibBackend())
            st.project()
            return st

        st = build()
        # the standard's questions were answered on its own example data. On these tables a question on a query with
        # parameters is asked again with the answer the tables give now (it also gives the query the values the
        # backends are compared with); one on a decision goes. Each kept query without parameters is asked its row
        # count now, as a draft does.
        words = LABELS.get(d.lang, LABELS["en"])["question"]
        asked, wrong, renewed = [], [], 0
        for name, rq in st.onto.queries.items():
            if not rq.params:
                asked.append({"id": f"{m.name}-q{len(asked) + 1}", "text": words.format(q=rq.label or name),
                              "query": name, "expect": {"rows": len(st.run(name, {}, backend="source").rows)}})
        failed = {r.id for r in st.questions(backend="source").results if not r.passed}
        for qs in [q for q in st.onto.questions if q.id in failed]:
            wrong.append(qs.id)
            if qs.query and st.onto.queries[qs.query].params:
                try:
                    rows = len(st.run(qs.query, qs.params, backend="source").rows)
                except Exception:  # a question the tables cannot answer goes
                    continue
                asked.append({"id": f"{m.name}-{qs.id}", "text": qs.text, "query": qs.query,
                              "params": dict(qs.params), "expect": {"rows": rows}})
                renewed += 1
        if wrong or asked:
            if wrong:
                m.remove["questions"] = [*m.remove.get("questions", []), *wrong]
            m.body["questions"] = asked
            st = build()
        self._adopt(st)
        self._library_rows = st.library.list()
        self.origin = {**d.origin, "label": d.label, "standard": [str(x) for x in standard]}
        self.pending, self.log = None, []
        removed = sum(len(v) for v in (m.remove.get("properties") or {}).values())
        uses = [f"{word} {len(m.remove[k])}개" for k, word in (("states", "상태 전이"), ("decisions", "결정"),
                                                              ("actions", "액션")) if m.remove.get(k)]
        self._note("draft", f"{d.label} 테이블을 표준 {', '.join(map(str, standard))} 에 연결했습니다. 객체 "
                            f"{len(m.extend.get('objects') or {})}개, 관계 {len(m.extend.get('links') or {})}개, "
                            f"테이블에 없는 속성 {removed}개 제외"
                            + (f"(이 속성을 쓰는 {', '.join(uses)} 제외)" if uses else "")
                            + (f", 예시 데이터 기준 표준 검증 질문 {renewed}개는 업로드 데이터의 답으로 다시 등록" if renewed else "")
                            + (f", 업로드 데이터로 답할 수 없는 표준 검증 질문 {len(wrong) - renewed}개 제외"
                               if len(wrong) > renewed else ""))
        return plain({"ok": True, "module": m.to_dict()})

    def preview_draft(self, edits: dict | None = None) -> dict:
        if not self.pending:
            raise ValueError("생성된 초안이 없어 미리 보지 못했습니다. 초안을 먼저 생성해 주세요.")
        try:
            r = self._edit(self.pending[0], edits)
        except ValueError as e:
            return {"ok": False, "issues": [str(e)]}
        return plain({"ok": True, **self._revised(r)})

    def apply_draft(self, edits: dict | None = None) -> dict:
        from xgen_data_studio.backends.sql import SqliteBackend
        from xgen_data_studio.draft import ReadError, load_sqlite, studio_from

        if not self.pending:
            raise ValueError("생성된 초안이 없어 적용하지 못했습니다. 초안을 먼저 생성해 주세요.")
        d0, b, tables, rules = self.pending
        try:
            d = self._edit(d0, edits)
        except ValueError as e:
            raise ValueError(f"편집 내용을 확인할 수 없어 적용하지 못했습니다. {e}") from None
        if not d.objects:
            raise ValueError("선택된 객체가 없어 적용하지 못했습니다. 객체를 하나 이상 선택해 주세요.")
        if d.origin.get("kind") == "files":  # a type the person chose is how the values are stored
            was = {(o.table, p.column): p.type for o in d0.objects for p in o.properties}
            original = {lo.table: t.name for t, lo in zip(tables, d0.loaded)}
            asked: dict[str, dict[str, str]] = {}
            for o in d.objects:
                for p in o.properties:
                    if was.get((o.table, p.column)) != p.type:
                        asked.setdefault(original.get(o.table, o.table), {})[p.column] = p.type
            if asked:
                b = SqliteBackend()
                try:
                    load_sqlite(tables, b, row_keys=rules.row_keys, types=asked)
                except ReadError as e:
                    i = e.info
                    raise ValueError(f"{i.get('table')}.{i.get('column')} 값 {i.get('value')!r} 을(를) "
                                     f"{i.get('type')} 타입으로 변환하지 못해 적용하지 못했습니다. 타입을 다시 선택해 "
                                     "주세요.") from None
        try:
            self._adopt(studio_from(d, b, library=self.studio.library, use_zen=self.studio.use_zen))
        except ModuleError as e:
            raise ValueError(f"정의 검사에서 오류가 발견되어 적용하지 못했습니다. {e}") from None
        self._library_rows = self.studio.library.list()
        self.origin = {**d.origin, "label": d.label}
        self.pending, self.log = None, []
        self._note("draft", f"{d.label} 온톨로지를 적용했습니다. 객체 {len(d.objects)}개, 관계 {len(d.links)}개")
        return {"ok": True}

    # ---- module files: read, check, save into this visitor's library, plug in ---------------------------------

    def _module(self, name: str) -> Module:
        comp = self.studio.composition
        for m in comp.modules if comp else []:
            if m.name == name:
                return m
        if self.studio.library is None:
            raise LookupError(name)
        try:
            return self.studio.library.get(name)
        except ModuleError:
            raise LookupError(name) from None

    def module_source(self, name: str) -> dict:
        import yaml

        m = self._module(name)
        comp = self.studio.composition
        return {"name": m.name, "label": m.label or m.name, "kind": m.kind, "version": m.version,
                "applied": bool(comp) and m.name in {x.name for x in comp.modules},
                "yaml": yaml.safe_dump(m.to_dict(), allow_unicode=True, sort_keys=False)}

    @staticmethod
    def _parse_module(text: str) -> Module:
        import yaml

        if len(text.encode("utf-8")) > MODULE_TEXT_MAX:
            raise ValueError("정의 파일 크기가 48KB 한도를 초과해 읽지 못했습니다. 모듈을 나누어 저장해 주세요.")
        try:
            d = yaml.safe_load(text)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            where = f"{mark.line + 1}행의 " if mark is not None else ""
            raise ValueError(f"{where}YAML 형식이 올바르지 않아 읽지 못했습니다. 들여쓰기와 따옴표를 확인해 주세요.") from None
        if not isinstance(d, dict) or not d.get("module"):
            raise ValueError("module 이름이 없어 읽지 못했습니다. 첫 줄에 module: 이름을 입력해 주세요.")
        try:
            return Module.from_dict(d)
        except (ModuleError, KeyError, TypeError, ValueError, AttributeError) as e:
            raise ValueError(f"모듈 형식이 올바르지 않아 읽지 못했습니다. {e}") from None

    def _module_issues(self, m: Module) -> list[str]:
        from xgen_data_studio.library import OverlayLibrary

        comp = self.studio.composition
        current = list(comp.modules) if comp else []
        names = {x.name for x in current}
        if m.name in names:
            mods = [m if x.name == m.name else x for x in current]
        else:
            try:
                picked = OverlayLibrary(self.studio.library, [m]).resolve([*names, m.name])
            except ModuleError as e:
                return [str(e)]
            mods = current + [x for x in picked if x.name not in names]
        try:
            return list(compose(mods, **self.studio._compose_kw).issues)
        except ModuleError as e:
            return [str(e)]

    def check_module(self, text: str) -> dict:
        m = self._parse_module(text)
        comp = self.studio.composition
        issues = self._module_issues(m)
        return plain({"ok": not issues, "issues": issues, "name": m.name, "version": m.version, "kind": m.kind,
                      "counts": m.counts(), "applied": bool(comp) and m.name in {x.name for x in comp.modules}})

    def save_module(self, text: str, apply: bool = False) -> dict:
        """Propose and, where this visitor may approve their own change, approve it in one step."""
        comp = self.studio.composition
        res = self.propose_module(text, attach=apply)
        change = res["change"]
        applied = bool(comp) and change["module"] in {x.name for x in comp.modules}
        if not self.studio.changes.self_approve:
            return {"ok": True, "applied": False, "pending": True, "change": change, "warning": ""}
        out = self.decide_change(change["id"], True)
        if not out["ok"]:
            raise ValueError(out["error"])
        warning = _projection_warning(out.get("projection") or {})
        return {"ok": True, "applied": applied or apply, "warning": warning, "change": out["change"],
                "bumped": res["bumped"]}

    def export_module(self, name: str) -> str:
        return self.module_source(name)["yaml"]

    # ---- definition changes: a module version is proposed, reviewed on a copy, approved by a person ------------

    def _change(self, cr) -> dict:
        rv = cr.review
        gates = [{**g, "label": GATE_LABEL.get((g["stage"], g["condition"]), g["condition"]),
                  "stage_label": STAGE_LABEL.get(g["stage"], g["stage"])} for g in rv.get("gates") or []]
        m = rv.get("measured") or {}
        return plain({
            "id": cr.id, "module": cr.module, "module_label": self._label(cr.module), "version": cr.version,
            "base_version": rv.get("base_version", ""), "mode": rv.get("mode", ""), "status": cr.status,
            "status_label": CHANGE_STATUS.get(cr.status, cr.status), "requested_by": cr.requested_by,
            "decided_by": cr.decided_by, "reason": cr.reason, "at": cr.at, "passed": rv.get("passed"),
            "issues": rv.get("issues") or [], "diff": rv.get("diff") or {}, "gates": gates,
            "measured": {"bind": {k: v for k, v in (m.get("bind") or {}).items() if k != "findings"},
                         "findings": (m.get("bind") or {}).get("findings", [])[:20],
                         "query": m.get("query"), "check": m.get("check"),
                         "decide": {k: v for k, v in (m.get("decide") or {}).items() if k != "mismatches"},
                         "mismatches": (m.get("decide") or {}).get("mismatches", [])[:20]}})

    def propose_module(self, text: str, attach: bool = False) -> dict:
        m = self._parse_module(text)
        issues = self._module_issues(m)
        if issues:
            raise ValueError("정의 검사에서 오류가 발견되어 변경을 요청하지 못했습니다. " + "; ".join(issues[:5]))
        lib = self.studio.changes.store or self.studio.library
        bumped = ""
        if m.version in lib.versions(m.name):
            if lib.get(m.name, m.version).to_dict() == m.to_dict():
                raise ValueError("바뀐 내용이 없어 변경을 요청하지 못했습니다. 정의를 수정한 뒤 다시 요청해 주세요.")
            bumped, m.version = m.version, _next_version(lib.versions(m.name))
        cr = self.studio.changes.propose(m, by=self.who, attach=attach)
        extra = f" 버전 {bumped} 이(가) 이미 있어 {m.version} (으)로 올렸습니다." if bumped else ""
        state = "흐름 통과 조건을 모두 충족합니다" if cr.review.get("passed") else "흐름 통과 조건을 충족하지 못했습니다"
        self._note("change", f"{m.label or m.name} {m.version} 변경을 요청했습니다. {state}.{extra}")
        return {"ok": True, "change": self._change(cr), "bumped": bumped}

    def changes_state(self) -> dict:
        ch = self.studio.changes
        return {"changes": [self._change(c) for c in reversed(list(ch.requests.values()))], "who": self.who,
                "self_approve": ch.self_approve, "writes_folder": ch.store is not None}

    def decide_change(self, change_id: str, approve: bool, reason: str = "") -> dict:
        from xgen_data_studio.review import ChangeError

        ch = self.studio.changes
        try:
            cr = ch.approve(change_id, by=self.who) if approve else                 ch.reject(change_id, by=self.who, reason=reason or "검토 후 반려")
        except PermissionError:
            return {"ok": False, "error": "변경을 요청한 사람은 같은 변경을 승인할 수 없어 승인하지 못했습니다. "
                                          "다른 승인자가 승인해 주세요."}
        except (ChangeError, ModuleError) as e:
            cr = ch.requests.get(change_id)
            failed = [g["label"] for g in (self._change(cr)["gates"] if cr else []) if not g["passed"]]
            why = ", ".join(failed) if failed else str(e)
            return {"ok": False, "error": f"흐름 통과 조건({why})을 충족하지 못해 승인하지 못했습니다. "
                                          "정의를 고쳐 다시 요청해 주세요.",
                    "change": self._change(cr) if cr else None}
        proj = {}
        if cr.status == "approved":
            proj = self._reproject()
            self._library_rows = self.studio.library.list()
            if cr.module == WORKSPACE:
                self.workspace = None  # the edits are in the studio now; the next ones start from there
        verb = "승인하고 적용했습니다" if cr.status == "approved" else "반려했습니다"
        self._note("change", f"{self._label(cr.module)} {cr.version} 변경을 {verb}.", projection=proj)
        return {"ok": True, "change": self._change(cr), "projection": proj}

    # ---- management: objects, properties, relations, questions as one pending overlay module --------------------

    def _ws(self):
        from xgen_data_studio.manage import Workspace

        comp = self.studio.composition
        if comp is None:
            raise ValueError("모듈로 구성된 스튜디오가 아니어서 정의를 관리하지 못했습니다.")
        sig = tuple(m.key for m in comp.modules)
        if self.workspace is None or self._ws_sig != sig:
            current = next((m for m in comp.modules if m.name == WORKSPACE), None)
            old = self.workspace
            ws = Workspace(list(comp.modules), current, compose_kw=self.studio._compose_kw)
            if old is not None and old.dirty:  # unsent edits carry over to the new modules; they are checked again
                ws.module, ws.edits = old.module, old.edits
            self.workspace, self._ws_sig = ws, sig
        return self.workspace

    def manage_state(self) -> dict:
        """The definition as the pending edits would leave it, and what the source holds, for the management screens."""
        from xgen_data_studio.draft import _catalog
        from xgen_data_studio.manage import _lineage
        from xgen_data_studio.review import element_diff

        ws = self._ws()
        issues: list[str] = []
        try:
            comp = ws.composed()
        except ModuleError as e:  # the modules changed under unsent edits and they no longer hold
            comp, issues = self.studio.composition, [str(e)]
        o, base = comp.ontology, self.studio.onto
        issues += list(comp.issues)
        mine = ws.module
        diff = element_diff(base, o) if ws.dirty else {"added": [], "removed": [], "changed": []}
        touched = set(diff["changed"])  # what the unsent edits change; what they add is marked new

        def owner(element: str) -> dict:
            m = comp.owner(element)
            return {"module": m, "module_label": mine.label if m == WORKSPACE else (self._label(m) if m else "")}

        src = self.studio.backends.get(self.studio.source) if self.studio.source else None
        catalog, rows = self._source_catalog(src, _catalog)
        bound: dict[str, list[str]] = {}
        for t in o.objects.values():
            if t.table:
                bound.setdefault(t.table, []).append(t.name)
        linked = {lk.source for lk in o.links.values()} | {lk.target for lk in o.links.values()}
        objects = []
        for t in o.objects.values():
            props = all_props(o, t.name)
            objects.append({
                "name": t.name, "label": t.label or t.name, "description": t.description, "table": t.table,
                "key": t.key, "parent": t.parent, "concept": not t.table, "properties": len(props),
                "computed": sum(1 for p in props if find_prop(o, t.name, p).expr),
                "links": sum(1 for lk in o.links.values() if t.name in (lk.source, lk.target)),
                "rows": rows.get(t.table) if t.table else None, "states": bool(t.states),
                "pending": f"object:{t.name}" in touched, "new": t.name not in base.objects, **owner(f"object:{t.name}")})
        properties = []
        for t in o.objects.values():
            for pname in all_props(o, t.name):
                p = find_prop(o, t.name, pname)
                from_type = t.name if pname in t.properties else next(
                    (x for x in _lineage(o, t.name) if pname in o.objects[x].properties), t.name)
                properties.append({
                    "object": t.name, "name": pname, "label": p.label, "type": p.type, "column": p.col if not p.expr else "",
                    "values": p.values, "required": p.required, "mask": p.mask, "expr": p.expr, "unit": p.unit,
                    "description": p.description, "key": pname == t.key, "inherited": from_type if from_type != t.name else "",
                    "pending": f"property:{t.name}.{pname}" in touched,
                    "new": t.name not in base.objects or pname not in all_props(base, t.name),
                    **owner(f"property:{from_type}.{pname}")})
        links = [{"name": lk.name, "label": lk.label, "source": lk.source, "target": lk.target,
                  "on": list(lk.on) if lk.on else None,
                  "via": {"table": lk.via.table, "source": lk.via.source_column, "target": lk.via.target_column}
                  if lk.via else None, "cardinality": lk.cardinality, "inverse": lk.inverse, "required": lk.required,
                  "pending": f"link:{lk.name}" in touched, "new": lk.name not in base.links, **owner(f"link:{lk.name}")}
                 for lk in o.links.values()]
        questions = [{"id": q.id, "text": q.text, "decision": q.decision, "key": q.key, "query": q.query,
                      "params": q.params, "expect": q.expect, "pending": f"question:{q.id}" in diff["added"],
                      **owner(f"question:{q.id}")} for q in o.questions]
        via: dict[str, list[str]] = {}
        for lk in o.links.values():
            if lk.via:
                via.setdefault(lk.via.table, []).append(lk.name)
        tables = [{"table": t, "columns": [{"name": c, "type": ty} for c, ty in cols], "key": pk,
                   "fks": [{"column": c, "table": rt, "ref": rc} for c, rt, rc in fks], "rows": rows.get(t),
                   "objects": bound.get(t, []), "links": via.get(t, [])} for t, cols, pk, fks in catalog]
        import yaml

        return plain({
            "objects": objects, "properties": properties, "links": links, "questions": questions,
            "unlinked": [x["name"] for x in objects if not x["concept"] and x["name"] not in linked],
            "sources": {"source": {"name": self.studio.source, "dialect": src.capabilities.dialect if src else "",
                                   "tables": tables,
                                   "unbound": [x["table"] for x in tables if not x["objects"] and not x["links"]]},
                        "graphs": [{"name": n, "language": b.capabilities.language}
                                   for n, b in self.studio.backends.items() if n != self.studio.source]},
            "workspace": {"dirty": ws.dirty, "module": WORKSPACE, "label": mine.label,
                          "version": ws.current.version if ws.current else "",
                          "edits": [{"op": e.op, "target": e.target, "took_out": e.took_out} for e in ws.edits],
                          "issues": issues, "diff": diff,
                          "yaml": yaml.safe_dump(mine.to_dict(), allow_unicode=True, sort_keys=False)},
        })

    def _source_catalog(self, src, read) -> tuple[list, dict]:
        """The source's tables and their row counts, read once per source (edits re-read the state often)."""
        if src is None:
            return [], {}
        if getattr(self, "_catalog_of", None) is src:
            return self._catalog_rows
        try:
            catalog = read(src)
        except Exception:  # a source the catalog reader does not know (a graph, a DB-API driver): tables unknown
            catalog = []
        from xgen_data_studio.compile.sql import qi

        rows: dict = {}
        for t, *_ in catalog:
            try:
                rows[t] = src.fetch(f"SELECT COUNT(*) FROM {qi(t)}")[0][0]
            except Exception:  # a view or a table this account may not read
                rows[t] = None
        self._catalog_of, self._catalog_rows = src, (catalog, rows)
        return catalog, rows

    def manage_edit(self, op: str, args: dict) -> dict:
        from xgen_data_studio.manage import EditError

        try:
            edit = self._ws().apply(str(op), dict(args or {}))
        except EditError as e:
            raise ValueError(_edit_text(str(e))) from None
        return {"ok": True, "edit": {"op": edit.op, "target": edit.target, "took_out": edit.took_out},
                **self.manage_state()}

    def manage_import_questions(self, text: str) -> dict:
        """Questions from a YAML or JSON list ({id, text, query, params, expect} or {id, text, decision, key, expect})."""
        import yaml

        from xgen_data_studio.manage import EditError

        try:
            items = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ValueError(f"파일을 읽지 못했습니다. YAML 또는 JSON 목록인지 확인해 주세요. {e}") from None
        if isinstance(items, dict):
            items = items.get("questions")
        if not isinstance(items, list) or not items:
            raise ValueError("검증 질문 목록이 없어 불러오지 못했습니다. questions 목록을 넣어 주세요.")
        added, failed = [], []
        for q in items[:200]:
            try:
                self._ws().apply("add_question", dict(q))
                added.append(str(q.get("id")))
            except (EditError, AttributeError) as e:
                failed.append(f"{q.get('id') if isinstance(q, dict) else q}: {_edit_text(str(e))}")
        return {"ok": True, "added": added, "failed": failed, **self.manage_state()}

    def manage_discard(self) -> dict:
        self.workspace = None
        return {"ok": True, **self.manage_state()}

    def manage_propose(self) -> dict:
        """File the pending edits as a change to the workspace module: tried on a copy, then approved by a person."""
        import yaml

        ws = self._ws()
        if not ws.dirty:
            raise ValueError("바뀐 내용이 없어 변경을 요청하지 못했습니다. 객체 · 속성 · 관계를 고친 뒤 다시 요청해 주세요.")
        text = yaml.safe_dump(ws.module.to_dict(), allow_unicode=True, sort_keys=False)
        res = self.propose_module(text, attach=ws.current is None)
        change = res["change"]
        if not self.studio.changes.self_approve:  # a person approves it on the library screen
            self.workspace = None
            return {"ok": True, "pending": True, "change": change, **self.manage_state()}
        out = self.decide_change(change["id"], True)
        if not out["ok"]:  # the trial did not pass: the edits stay to be fixed, the request goes back with its review
            cr = self.studio.changes.reject(change["id"], by=self.who, reason="흐름 통과 조건 미충족 · 관리 화면에서 수정")
            return {"ok": False, "error": out["error"], "change": self._change(cr), **self.manage_state()}
        self.workspace = None  # approved: what comes next starts from the studio as it now stands
        return {"ok": True, "pending": False, "change": out["change"],
                "warning": _projection_warning(out.get("projection") or {}), **self.manage_state()}

    # ---- the flow's stages and pass conditions, agreement with past decisions, identities, sync --------------

    def flow_settings(self) -> dict:
        from xgen_data_studio.review import GATES, STAGES

        st = self.studio
        qs = [{"name": q.name, "label": q.label or q.name,
               "columns": [c.name for c in st.query(q.name).columns]} for q in st.onto.queries.values()]
        ds = [{"name": d.name, "label": d.label or d.name, "inputs": list(d.inputs), "outputs": list(d.outputs)}
              for d in st.onto.decisions.values()]
        # the form edits the studio's own conditions; a quality module's that ask more are shown next to them
        raised = []
        for ref, m in st.raised_gates().items():
            stage, cond = ref.split(".")
            raised.append({"stage": stage, "condition": cond, "value": st.composition.gates[stage][cond], "module": m,
                           "module_label": self._label(m)})
        return plain({"settings": st.own_flow.to_dict(), "raised": raised,
                      "stages": [{"id": s, "label": STAGE_LABEL[s]} for s in STAGES],
                      "conditions": {s: [{"id": c, "label": GATE_LABEL[(s, c)]} for c in cs]
                                     for s, cs in GATES.items()},
                      "queries": qs, "decisions": ds})

    def save_flow(self, settings: dict) -> dict:
        from xgen_data_studio.review import FlowSettings

        try:
            fs = FlowSettings.from_dict(settings)
        except ValueError as e:
            raise ValueError(f"흐름 설정을 확인할 수 없어 저장하지 못했습니다. {e}") from None
        self.studio.settings["flow"] = fs.to_dict()
        self._note("flow", "흐름 단계와 통과 조건을 저장했습니다.")
        return {"ok": True, "settings": fs.to_dict()}

    def agreement(self) -> dict:
        st = self.studio
        if not st.flow.agreement:
            return {"ok": False, "error": "판정 일치율 설정이 없어 측정하지 못했습니다. 흐름 설정에서 비교할 결정표와 "
                                          "처리 기록 질의를 지정해 주세요."}
        try:
            a = st.agreement()
        except Exception as e:
            return {"ok": False, "error": f"처리 기록을 판정하지 못했습니다. {type(e).__name__}: {e}"}
        d = st.onto.decisions[a["decision"]]
        return plain({"ok": True, "label": d.label or d.name, **a})

    def identities(self) -> dict:
        st = self.studio
        out = []
        for name, ident in st.onto.identities.items():
            try:
                rep = st.resolve_identity(name, write=False)
            except Exception as e:
                out.append({"name": name, "label": ident.label or name, "error": f"{type(e).__name__}: {e}"})
                continue
            out.append({"name": name, "label": ident.label or name, "table": ident.table,
                        "members": [{"type": m.type, "label": self._obj_label(m.type), "fields": m.fields}
                                    for m in ident.members.values()],
                        "rules": [{"id": r.id, "match": r.match, "normalize": r.normalize} for r in ident.rules],
                        **rep.to_dict()})
        return plain({"identities": out})

    def resolve_identity(self, name: str) -> dict:
        src = self.studio.backends.get(self.studio.source)
        if src is None or not getattr(src, "capabilities", None) or not src.capabilities.write:
            return {"ok": False, "error": "원천 DB에 쓸 수 없어 교차표를 만들지 못했습니다. 쓰기 가능한 원천을 연결해 주세요."}
        if self.origin.get("kind") == "connect":
            return {"ok": False, "error": "연결한 DB에는 교차표를 쓰지 않습니다. 사내 설치에서 xds 명령으로 실행해 주세요."}
        rep = self.studio.resolve_identity(name)
        self._note("identity", f"{name}: 기록 {rep.records}건을 {len(rep.clusters)}개로 묶었습니다 "
                               f"(묶인 건 {len(rep.joined)}).")
        return plain({"ok": True, **rep.to_dict()})

    def sync(self) -> dict:
        res = self.studio.sync()
        if res.get("error"):
            return {"ok": False, "error": f"원천을 다시 읽지 못했습니다. {res['error']}"}
        self._note("sync", "원천 변경분을 반영했습니다." if res["changed"] else "원천에 바뀐 내용이 없습니다.")
        return plain({"ok": True, **res})

    # ---- the whole flow, from the source to the checks, with what each stage holds now ----------------------

    def flow(self) -> dict:
        from xgen_data_studio.compile.sql import qi

        st, o = self.studio, self.studio.onto
        src = st.backends.get(st.source)
        tables = sorted({t.table for t in o.objects.values() if t.table} |
                        {lk.via.table for lk in o.links.values() if lk.via})
        rows = []
        for t in tables:
            try:
                rows.append({"table": t, "rows": src.fetch(f"SELECT COUNT(*) FROM {qi(t)}")[0][0]})
            except Exception:  # a table the definition names but the database lacks; DB 대조 shows it
                rows.append({"table": t, "rows": None})
        comp = st.composition
        modules = [{"name": m.name, "label": m.label or m.name, "kind": m.kind,
                    "kind_label": MODULE_KIND.get(m.kind, m.kind)} for m in (comp.modules if comp else [])]
        from xgen_data_studio.review import gates as pass_gates
        from xgen_data_studio.review import measure

        settings = st.flow
        measured = measure(st, settings)
        by = st.raised_gates()
        results = [{**g.__dict__, "label": GATE_LABEL.get((g.stage, g.condition), g.condition),
                    "by": self._label(by[f"{g.stage}.{g.condition}"]) if f"{g.stage}.{g.condition}" in by else ""}
                   for g in pass_gates(measured, settings)]
        bind, conf, qa, agree = (measured.get(k) for k in ("bind", "query", "check", "decide"))
        proj = st.projection
        steps = [
            {"id": "source", "backend": st.source, "dialect": src.capabilities.dialect if src else "",
             "tables": rows, "rows": sum(r["rows"] or 0 for r in rows)},
            {"id": "define", "modules": modules, "objects": len(o.objects), "links": len(o.links),
             "properties": sum(len(t.properties) for t in o.objects.values()),
             "computed": sum(1 for t in o.objects.values() for p in t.properties.values() if p.expr),
             "identities": len(o.identities)},
            {"id": "bind", "ok": bind["ok"] if bind else None, "checked": bind["checked"] if bind else {},
             "findings": len(bind["findings"]) if bind else 0},
            {"id": "project", "backends": [n for n, b in st.backends.items() if b.capabilities.load],
             "nodes": len(proj.nodes) if proj else 0, "edges": len(proj.edges) if proj else 0, "sync": st.last_sync},
            {"id": "query", "queries": len(o.queries), "targets": len(TARGETS),
             "conformance": {k: conf[k] for k in ("agree", "queries", "error") if k in conf} if conf else None},
            {"id": "decide", "decisions": len(o.decisions), "actions": len(o.actions),
             "rules": sum(len(d.rules) for d in o.decisions.values()),
             "agreement": {k: agree.get(k) for k in ("cases", "agree", "rate", "error") if k in agree}
             if agree else None},
            {"id": "check", "questions": len(o.questions), "accuracy": qa["accuracy"] if qa else None,
             "grounded": qa["grounded"] if qa else None},
        ]
        for s in steps:
            s["on"] = settings.on(s["id"])
            s["gates"] = [g for g in results if g["stage"] == s["id"]]
        return plain({"origin": self.origin, "passed": all(g["passed"] for g in results), "steps": steps})

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
        return plain({"accuracy": rep.accuracy, "grounded": rep.grounded,
                      "results": [{**r.__dict__, "gaps": [_gap_text(g) for g in r.gaps]} for r in rep.results],
                      "conformance": conf})

    def bindings(self) -> dict:
        source = self.studio.source
        if not source:
            return {"ok": False, "error": "원천 DB가 연결되어 있지 않아 대조하지 못했습니다."}
        rep = self.studio.check_bindings()
        return plain({"ok": rep.ok, "checked": rep.checked, "backend": source,
                      "findings": [f.__dict__ for f in rep.findings]})


def _next_version(versions: list[str]) -> str:
    from xgen_data_studio.modules import version_key

    last = sorted(versions, key=version_key)[-1]
    parts = last.split(".")
    if all(p.isdigit() for p in parts):
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    return f"{last}.1"


def _size(n: int) -> str:
    return f"{n >> 20}MB" if n >= 1 << 20 and not n % (1 << 20) else f"{n >> 10:,}KB"


def _word(v: Any) -> str:
    return ("true" if v else "false") if isinstance(v, bool) else str(plain(v))


def _projection_warning(proj: dict) -> str:
    if "error" not in proj:
        return ""
    return "원천 DB가 정의와 일치하지 않아 그래프 저장소에 반영하지 못했습니다. DB 대조에서 확인해 주세요."


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
