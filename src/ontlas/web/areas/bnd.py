"""Data Binding: what its screens ask beyond the routes the older tabs already had.

- a registered query as its screen shows it (where it starts, the relations it follows, what it takes and returns,
  who uses it), and its change or removal as an edit like any other,
- a query being written, read into every store's language without being run,
- the SQL an Entity's binding makes,
- an action tried without being requested: the checks a request would meet, and nothing kept or called.
"""
from __future__ import annotations

import re
from typing import Any

from ontlas.web.api import TARGETS, plain
from ontlas.web.routes import get, post

# what the query checker and the compilers say, in the words these screens use; a reason not listed is said as the
# store's language refusing the query
_COMPILE_SAID = [
    (r"alias '(\w+)': unknown object type '([^']*)'", r"Entity 없음 · \2"),
    (r"(\w+) \('\w+'\) has no property '([^']*)'", r"Property 없음 · \1.\2"),
    (r"(\w+) has no property '([^']*)'", r"Property 없음 · \1.\2"),
    (r"unknown link '([^']*)'", r"Relation 없음 · \1"),
    (r"link '([^']*)' goes (\w+) -> (\w+); it cannot join", r"Relation 방향 불일치 · \1 \2 → \3"),
    (r"(?:unknown alias|uses an alias that is not matched|is not connected by any edge|touches no earlier alias)", "별칭 연결 오류"),
    (r"(\w+) has no source table and no bound subtype", r"테이블 미지정 Entity · \1"),
    (r"link (\w+) has no source binding", r"Relation 소스 미지정 · \1"),
    (r"(\w+)\.(\w+) is computed, so", r"계산 Property · \1.\2"),
    (r"missing parameters \[([^\]]*)\]", r"입력값 없음 · \1"),
    (r"'match' maps aliases to object types", "match 형식 오류"),
    (r"'return' lists at least one column", "반환 Property 없음"),
    (r"a query is an object", "질의 정의 형식 오류"),
    (r"expected 'alias\.property', got '?([^']*)'?", r"Property 형식 오류 · \1"),
    (r"unknown filter '?(\w+)'?", r"알 수 없는 조건 · \1"),
    (r"cannot compare (\w+) with (\w+)", r"비교할 수 없는 타입 · \1 ↔ \2"),
    (r"is not a valid (\w+)", r"값 형식 오류 · \1"),
    (r"limit must be positive", "건수 오류"),
    (r"order by '([^']*)' is not a returned column", r"정렬 기준 오류 · \1"),
]


def _compile_said(msg: str, other: str = "이 저장소 언어로 변환 불가") -> str:
    """A refusal of the query as the screens say it: each reason found, joined; the engine's own words are not shown."""
    said: list[str] = []
    for pattern, word in _COMPILE_SAID:
        for m in re.finditer(pattern, msg):
            text = m.expand(word).replace("'", "")
            if text not in said:
                said.append(text)
    return " · ".join(said) or other


def _finding_said(f) -> str:
    """What a binding check found, as the screens say it: the place and what is wrong there."""
    d = f.data or {}
    where = ".".join(x for x in (d.get("table"), d.get("column")) if x)
    shown = lambda xs: ", ".join(str(x) for x in list(xs or [])[:5])  # noqa: E731
    if f.kind == "table":
        named = re.search(r"'([^']*)'", f.detail)
        return f"{d.get('table') or (named.group(1) if named else '')} 테이블 없음" if d else f"{named.group(1) if named else ''} 식별 정보 미확정"
    if f.kind == "column":
        return f"{where} 컬럼 없음"
    if f.kind == "type":
        return f"{where} {d.get('sql_type') or '?'} · Property {d.get('type', '')}"
    if f.kind == "key":
        return f"중복 키 {shown(d.get('keys'))}"
    if f.kind == "required":
        return f"빈 값 {d.get('count', 0)}행 · {shown(d.get('keys'))}"
    if f.kind == "enum":
        return f"정의에 없는 값 {shown(d.get('extra'))}"
    if f.kind == "orphan":
        return f"대상 없는 값 {d.get('count', 0)}행 · {shown(d.get('values'))}"
    return f.detail


def _said(col: Any) -> str:
    """One returned column as its definition writes it: o.order_id, or count(i) as items."""
    if isinstance(col, str):
        return col
    if isinstance(col, dict):
        name = col.get("as") or ""
        if "col" in col:
            return str(col["col"])
        for agg in ("count", "sum", "avg", "min", "max", "count_distinct"):
            if agg in col:
                return f"{agg}({col[agg]})" + (f" as {name}" if name else "")
        return name or ", ".join(f"{k} {v}" for k, v in col.items())
    return str(col)


def _prop_label(onto, type_name: str, prop: str) -> str:
    from ontlas.check import find_prop

    try:
        return find_prop(onto, type_name, prop).label or prop
    except Exception:  # a column the definition no longer has is said by its own name
        return prop


def _query_row(s, onto, base, name: str, rq) -> dict:
    q = rq.query or {}
    nodes = dict(q.get("match") or {})
    edges = [list(e) for e in q.get("edges") or []]
    comp = s.studio.composition
    owner = comp.owner(f"query:{name}") if comp is not None and name in base.queries else ""
    module = next((m for m in (comp.modules if comp else []) if m.name == owner), None)
    alias = next(iter(nodes), "")
    start = nodes.get(alias, "")
    label = lambda t: (onto.objects[t].label or t) if t in onto.objects else t  # noqa: E731
    hops = []
    for e in edges:
        if len(e) != 3:
            continue
        lk = onto.links.get(e[1])
        hops.append({"link": e[1], "label": (lk.label or e[1]) if lk else e[1], "from": nodes.get(e[0], e[0]),
                     "to": nodes.get(e[2], e[2]), "to_label": label(nodes.get(e[2], e[2]))})
    returns = []
    for c in q.get("return") or []:
        text = _said(c)
        word = text
        ref = c.get("col") if isinstance(c, dict) else c
        if isinstance(ref, str) and "." in ref and ref.split(".", 1)[0] in nodes:
            a, p = ref.split(".", 1)
            word = f"{label(nodes[a])} · {_prop_label(onto, nodes[a], p)}"
        returns.append({"text": text, "label": word})
    return {"name": name, "label": rq.label or name, "description": rq.description, "ir": q,
            "params": dict(rq.params), "example": dict(rq.example),
            "start": start, "start_label": label(start), "nodes": nodes, "hops": hops, "returns": returns,
            "module": owner or "workspace", "module_label": (module.label or module.name) if module else "",
            "version": module.version if module else "", "new": name not in base.queries,
            "editable": True,  # a module's query is changed by extending it, one made here in place
            "questions": [x.id for x in onto.questions if x.query == name],
            "roles": [{"name": r.name, "label": r.label or r.name} for r in onto.roles.values() if r.can("run", name)]}


@get("bnd/queries")
def queries(s, a, who) -> dict:
    """The registered queries as the pending edits leave them, each with what its screen says about it."""
    onto, pending = s._pending_onto()
    base = s.studio.onto
    rows = [_query_row(s, onto, base, n, rq) for n, rq in onto.queries.items()]
    return plain({"queries": rows, "pending": pending, "removed": sorted(set(base.queries) - set(onto.queries)),
                  "targets": [{"id": t, "label": lbl} for t, lbl in TARGETS]})


@post("bnd/query/check", needs="viewer")
def query_check(s, a, who) -> dict:
    """A query being written, read into each store's language (with the text it makes). Nothing is run."""
    from ontlas.check import find_prop
    from ontlas.compile.base import CompileError, compiler_for
    from ontlas.ir import IRError, Query, Ref

    onto, _ = s._pending_onto()
    try:
        q = Query.from_dict(a.get("query"))
    except (IRError, TypeError, ValueError, KeyError, AttributeError) as e:
        return {"ok": False, "error": _compile_said(str(e), "질의 정의 형식 오류"), "translations": []}
    out, params = [], set()
    for target, label in TARGETS:
        try:
            c = compiler_for(onto, target).compile(q)
            params |= set(c.params) - set(c.literals)  # a value the compiler lifts out of the query itself is no input
            out.append({"target": target, "label": label, "ok": True, "text": c.text})
        except (CompileError, KeyError, ValueError) as e:
            out.append({"target": target, "label": label, "ok": False, "error": _compile_said(str(e))})
    masked = []  # a returned column an access policy may hide, said before the query is saved
    for c in q.columns:
        ref = c.expr if isinstance(c.expr, Ref) else getattr(c.expr, "ref", None)
        t = q.nodes.get(ref.alias, "") if ref is not None else ""
        try:
            p = find_prop(onto, t, ref.prop) if t else None
        except Exception:  # a column the compiler refuses is said by the translations above
            p = None
        if p is not None and p.mask:
            word = f"{onto.objects[t].label or t} · {p.label or ref.prop}"
            if word not in masked:
                masked.append(word)
    return plain({"ok": any(x["ok"] for x in out), "translations": out, "params": sorted(params), "masked": masked})


@get("bnd/columns")
def columns(s, a, who) -> dict:
    """The column or columns each stored Property reads, as the queries will read them: a Property an Entity takes from
    the Entity it specialises may read another column there (its key reads the Entity's own key column). With them, the
    Entities whose rows keep another Entity's history: values over time (series) or rows valid for a time (period),
    each with the Relation that ties it to the Entity it records."""
    from ontlas.check import columns_of, stored_props
    from ontlas.model import TEXT_SUFFIX

    onto, pending = s._pending_onto()
    out: dict[str, list[str]] = {}
    for name in onto.objects:
        for p in stored_props(onto, name):
            try:
                out[f"{name}.{p}"] = [str(c) for c in columns_of(onto, name, p)]
            except Exception:  # a Property the definition cannot place is left to the checks to name
                continue
    histories = []
    for t in onto.objects.values():
        for kind, spec in (("series", t.series), ("period", t.period)):
            if not spec:
                continue
            lk = onto.links.get(str(spec.get("of") or ""))
            histories.append({"entity": t.name, "kind": kind, "of": lk.name if lk else "",
                              "owner": (lk.target if lk.source == t.name else lk.source) if lk else "",
                              "time": [str(spec[k]).removesuffix(TEXT_SUFFIX) for k in ("time", "start", "end") if spec.get(k)]})
    return {"columns": out, "histories": histories, "pending": pending}


@get("bnd/binding")
def binding(s, a, who) -> dict:
    """The SQL an Entity's binding makes: its bound properties read from its table, in the source's own dialect when a
    source is connected and in PostgreSQL's when none is."""
    from ontlas.check import all_props, find_prop
    from ontlas.compile.base import CompileError, compiler_for
    from ontlas.ir import Query

    onto, pending = s._pending_onto()
    name = str(a.get("entity") or "")
    t = onto.objects.get(name)
    if t is None:
        raise LookupError(name)
    st = s.studio
    dialect = st.backend().capabilities.dialect if st.backends and st.source else ""
    target = f"sql:{dialect}" if dialect and st.backend().capabilities.language == "sql" else "sql:postgres"
    out: dict[str, Any] = {"entity": name, "table": t.table or "", "target": target, "sql": "", "error": "", "pending": pending}
    if not t.table:
        out["error"] = "테이블이 지정되지 않은 Entity라 SQL을 생성하지 못했습니다."
        return out
    props = [p for p in all_props(onto, name) if not find_prop(onto, name, p).expr]
    try:
        out["sql"] = compiler_for(onto, target).compile(
            Query.from_dict({"match": {"x": name}, "return": [f"x.{p}" for p in props]})).text
    except (CompileError, KeyError, ValueError) as e:
        out["error"] = f"SQL 생성 불가 · {_compile_said(str(e))}"
    return plain(out)


@post("bnd/check", needs="viewer")
def check(s, a, who) -> dict:
    """The definition as the pending edits leave it, against the source's tables, columns, types, keys and values: what
    Mapping and Entity Binding show is what is checked."""
    from ontlas.bindings import check_bindings

    st = s.studio
    if not st.source:
        return {"ok": False, "no_source": True, "error": "연결된 데이터 소스가 없어 대조하지 못했습니다. 데이터 소스를 연결해 주세요."}
    onto, pending = s._pending_onto()
    backend = st.backend()
    rep = check_bindings(onto, backend)
    findings, checked = list(rep.findings), dict(rep.checked)
    return plain({"ok": not any(f.severity == "error" for f in findings), "checked": checked, "backend": st.source, "pending": pending,
                  "findings": [{**f.__dict__, "detail": _finding_said(f)} for f in findings]})


@post("bnd/query/run", needs="viewer")
def query_run(s, a, who) -> dict:
    """A query not yet deployed, run on the values given for its inputs, under an access policy if one is named."""
    q = a.get("query")
    if not isinstance(q, dict):
        raise ValueError("질의 정의가 없어 실행하지 못했습니다. 질의를 선택해 주세요.")
    params = a.get("params") if isinstance(a.get("params"), dict) else {}
    principal = a.get("principal") if isinstance(a.get("principal"), dict) else None
    return s.run_query(q, {k: v for k, v in params.items() if v not in ("", None)}, role=str(a.get("role") or ""), principal=principal)


def _outputs_said(detail: str) -> str:
    """A decision's outputs as a request's check keeps them ("{'eligible': True, 'reason': '…'}"), in a person's words."""
    import ast

    try:
        res = ast.literal_eval(detail)
    except (ValueError, SyntaxError):
        return detail
    if not isinstance(res, dict):
        return detail
    return " · ".join("가능" if v is True else "불가" if v is False else str(v) for v in res.values() if v not in ("", None))


def _problem_said(problem: str) -> str:
    """What is wrong with a given parameter (check_parameters says it in the engine's words)."""
    name, _, why = problem.partition(": ")
    if why == "required":
        return f"{name} 값 없음"
    if " is not one of " in why:
        return f"{name} 허용값 아님"
    if " is below " in why or " is above " in why:
        return f"{name} 범위 밖"
    if " is not " in why:
        return f"{name} 자료형 다름"
    return problem


@post("bnd/action/try", needs="viewer")
def action_try(s, a, who) -> dict:
    """An action tried: who asks, what is given, and what its conditions say, on a record's values when a source is
    connected and a record is named, on the values given when not. No request is made and nothing is called."""
    from ontlas.actions import Actor, check_parameters
    from ontlas.decide.words import input_label

    st = s.studio
    onto = st.onto
    name = str(a.get("action") or "")
    act = onto.actions.get(name)
    if act is None:
        raise ValueError("배포되지 않은 Action이라 테스트를 실행하지 못했습니다. 변경 요청을 승인한 뒤 다시 실행해 주세요.")
    role = str(a.get("role") or "")
    key = str(a.get("key") or "").strip()
    given = a.get("params") if isinstance(a.get("params"), dict) else {}
    inputs = a.get("inputs") if isinstance(a.get("inputs"), dict) else {}
    connected = bool(st.backends)
    checks: list[dict] = []
    r = onto.roles.get(role)
    if onto.roles:
        ok = bool(r is not None and r.can("request", name))
        checks.append({"name": "role", "title": "권한", "passed": ok,
                       "detail": (f"{r.label or r.name} 요청 가능" if ok else f"{(r.label or r.name) if r else '접근 정책 없음'}에 요청 권한 없음")})
    _, problems = check_parameters(act.parameters, dict(given))
    checks.append({"name": "parameters", "title": "Parameter", "passed": not problems,
                   "detail": "; ".join(_problem_said(x) for x in problems) if problems else (", ".join(f"{k} {v}" for k, v in given.items() if v not in ("", None)) or "입력값 없음")})
    current = None
    if key and connected:
        current = st.fetch(act.target, key)
        checks.append({"name": "target", "title": "대상 확인", "passed": current is not None,
                       "detail": f"{s._obj_label(act.target)} {key}" + ("" if current is not None else " 없음")})
    if current is not None:
        actor = Actor("테스트 실행", "human", [role] if role else [])
        for c in st.actions._standing(act, key, current):
            title = c.name
            detail = c.detail.replace("->", "→")
            if c.name.startswith("decision:"):
                d = onto.decisions.get(c.name.split(":", 1)[1])
                title = f"전제조건 · {d.label if d else c.name}"
                detail = _outputs_said(c.detail)
            elif c.name == "state":
                title = "상태 전이"
            elif c.name == "states":
                title = "허용 상태"
            elif c.name.startswith("guard:"):
                title = "전이 조건"
            checks.append({"name": c.name, "title": title, "passed": c.passed, "detail": detail})
        outside = st.actions._outside(actor, "request", act, key)
        if outside:
            checks.append({"name": "scope", "title": "행 범위", "passed": False, "detail": "접근 정책 범위 밖 레코드"})
    else:  # no record to read: each condition is asked on the values given for it
        for c in act.criteria:
            if not c.decision:
                continue
            table = onto.decisions.get(c.decision)
            vals = inputs.get(c.decision) if isinstance(inputs.get(c.decision), dict) else {}
            try:
                res = s.simulate(c.decision, "", vals)
            except ValueError as e:
                checks.append({"name": f"decision:{c.decision}", "title": f"전제조건 · {table.label if table else c.decision}",
                               "passed": False, "detail": str(e)})
                continue
            outs = res.get("outputs") or {}
            missing = [input_label(onto, table, i["name"]) for i in res["inputs"] if i["value"] in ("", None)] if table else []
            ok = "error" not in res and all(outs.get(k) == v for k, v in c.expect.items())
            checks.append({"name": f"decision:{c.decision}", "title": f"전제조건 · {res['label']}", "passed": ok,
                           "detail": res.get("error") or f"{res['verdict']}" + (f" · 규칙 {', '.join(res['matched'])}" if res.get("matched") else "")
                           + (f" · 넣지 않은 값 {', '.join(missing)}" if missing else "")})
    call = act.call or {}
    sm = onto.objects[act.target].states if act.target in onto.objects else None
    return plain({
        "ok": all(c["passed"] for c in checks), "action": name, "label": act.label or name, "key": key, "on_record": current is not None,
        "connected": connected, "checks": checks,
        "state": {"property": sm.property if sm and act.transition_to else "", "from": (current or {}).get(sm.property) if sm and current else None,
                  "to": act.transition_to},
        "call": {"method": str(call.get("method") or "POST"), "url": str(call.get("url") or "")} if call else None,
        "approval": bool(act.approval),
    })
