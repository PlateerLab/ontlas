"""What is wrong right now, each as something a person can act on.

The board says a stage failed. This says which items are behind it, why they came to be, what they reach and the ways
to fix each: here in the workspace, at once when it can be undone, or at the source with the list to hand over. A
failure is told as caused by another only when what failed reads what is broken; anything else stands on its own.
"""
from __future__ import annotations

import difflib
import json
import re
from typing import Any

from ontlas.manage import NAME as WORKSPACE
from ontlas.web.monitor import FINDING

KEEP_ON = {"core", "domain", "binding"}  # what everything else stands on: taking one off is never offered as a fix
KIND_WORD = {"property": "속성", "query": "질의", "link": "관계", "object": "Entity", "decision": "결정", "action": "액션", "rule": "규칙",
             "function": "함수", "role": "역할", "question": "검증 질문"}
SQL_TYPE = (("TIMESTAMP", "datetime"), ("DATETIME", "datetime"), ("DATE", "date"), ("TIME", "datetime"), ("BOOL", "boolean"), ("BIT", "boolean"),
            ("INT", "integer"), ("REAL", "decimal"), ("NUM", "decimal"), ("DEC", "decimal"), ("DOUBLE", "decimal"), ("FLOAT", "decimal"))
ITEMS_MAX = 12


def _issue(iid: str, kind: str, level: str, floor: str, title: str, detail: str, *, key: str = "", items: list | None = None,
           note: str = "", fixes: list | None = None, alert: bool = True) -> dict:
    return {"id": iid, "kind": kind, "level": level, "floor": floor, "floors": [floor], "title": title, "detail": detail,
            "keys": [key] if key else [], "items": (items or [])[:ITEMS_MAX], "total": len(items or []), "note": note, "cause": None,
            "effects": [], "fixes": fixes or [], "members": [], "direct": None, "alert": alert, "since": ""}


def _fix(label: str, where: str, say: str, cta: str, *, go: dict | None = None, steps: list | None = None, run: dict | None = None,
         preview: str = "", copy: str = "", recommended: bool = False) -> dict:
    """One way to fix it. `where` is here (the workspace, then a change request), now (undoable, at once) or source."""
    return {"label": label, "where": where, "say": say, "cta": cta, "go": go, "steps": steps or [], "run": run, "preview": preview,
            "copy": copy, "recommended": recommended}


def _pct(v: Any) -> str:
    return "-" if v is None else f"{round(v * 100)}%"


def _said(q: Any) -> str:
    return json.dumps(q, ensure_ascii=False)


def _short(v: Any) -> str:
    return (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))[:80]


def _columns(src, table: str) -> dict:
    try:
        return (src.columns(table) if src is not None else None) or {}
    except Exception:  # a table that cannot be read has no columns to offer
        return {}


def _near(column: str, have: dict) -> str:
    """The column of the table that reads most like the one missing, if any does."""
    got = difflib.get_close_matches(column.lower(), list(have), n=1, cutoff=0.72)
    return got[0] if got else ""


def _type_of(sql_type: str) -> str:
    s = (sql_type or "").upper()
    return next((t for k, t in SQL_TYPE if k in s), "string")


def _amount(elements: list[str]) -> str:
    """속성 2개와 질의 1개, from the element ids a module brings."""
    n: dict[str, int] = {}
    for el in elements:
        word = KIND_WORD.get(el.split(":", 1)[0])
        if word:
            n[word] = n.get(word, 0) + 1
    parts = [f"{k} {v}개" for k, v in n.items()]
    return "와 ".join(filter(None, [", ".join(parts[:-1]), parts[-1] if parts else ""]))


def _reach(onto, elements: list[str]) -> tuple[set[str], set[str], set[str]]:
    """The queries, decisions and questions that read any of these elements."""
    queries: set[str] = set()
    decisions: set[str] = set()
    for el in elements:
        kind, name = el.split(":", 1)
        if kind == "property" and "." in name:
            prop = name.split(".", 1)[1]
            queries |= {n for n, q in onto.queries.items() if f".{prop}" in _said(q.query)}
            decisions |= {n for n, d in onto.decisions.items()
                          if any(prop in (i.source.get("property"), i.source.get("days_since")) for i in d.inputs.values())}
        elif kind in ("object", "link"):
            queries |= {n for n, q in onto.queries.items() if f'"{name}"' in _said(q.query)}
            if kind == "object":
                decisions |= {n for n, d in onto.decisions.items() if d.target == name}
    return queries, decisions, {q.id for q in onto.questions if q.query in queries or q.decision in decisions}


# ---- the source against the definition --------------------------------------------------------------------------------


def _bind_item(s, f: dict, src) -> dict:
    el, kind, data = f["element"], f["kind"], f.get("data") or {}
    name, label = el.split(":", 1)[1], s._element_label(el)
    item = {"element": el, "name": name, "label": label, "say": FINDING.get(kind, kind), "evidence": "", "near": "", "row": f"bind:{el}",
            "go": {"tab": "model", "el": el}, "message": ""}
    go = item["go"]
    item["message"] = {"column": f"{data.get('table')} 테이블에 {data.get('column')} 컬럼이 없습니다.", "table": f"원천 DB에 {data.get('table')} 테이블이 없습니다.",
                       "type": f"{data.get('column')} 컬럼은 원천에서 {data.get('sql_type') or '알 수 없는 자료형'}입니다.",
                       "key": f"키 값이 겹칩니다: {', '.join(data.get('keys') or [])}", "required": f"값이 없는 행이 {data.get('count', 0):,}건 있습니다.",
                       "enum": f"정의에 없는 값이 있습니다: {', '.join(data.get('extra') or [])}", "orphan": f"연결되지 않는 행이 {data.get('count', 0):,}건 있습니다."}.get(kind, "")
    if kind == "column" and el.startswith("property:"):
        item["near"] = _near(data.get("column", ""), _columns(src, data.get("table", "")))
        go.update({"field": "column", **({"prefill": item["near"]} if item["near"] else {})})
    elif kind == "table" and el.startswith("object:"):
        go["field"] = "table"
    elif kind == "type":
        go["field"] = "type"
        item["evidence"] = f"정의 {data.get('type')} · 원천 {data.get('sql_type') or '알 수 없음'}"
    elif kind == "key":
        go["field"] = "key"
        item["evidence"] = f"중복된 키 {', '.join(data.get('keys') or [])}"
    elif kind == "required":
        go.update({"field": "required", "prefill": False})
        item["evidence"] = f"빈 값 {data.get('count', 0):,}행" + (f" · 예: {', '.join(data.get('keys') or [])}" if data.get("keys") else "")
    elif kind == "enum":
        go.update({"field": "values", "append": data.get("extra") or []})
        item["evidence"] = ", ".join(f"{v} ({n:,}건)" for v, n in (data.get("counts") or {}).items())
    elif kind == "orphan":
        go["field"] = "sp"
        item["evidence"] = f"끊긴 행 {data.get('count', 0):,}건" + (f" · 예: {', '.join(data.get('values') or [])}" if data.get("values") else "")
    return item


def _steps(items: list[dict]) -> list[dict]:
    return [{"label": x["label"], "go": x["go"]} for x in items]


def _cleanup(found: list[dict], items: list[dict]) -> str:
    """The rows to hand to whoever keeps the source."""
    lines = ["온톨로지 정의와 원천 DB를 맞추기 위해 원천 정리가 필요합니다."]
    for f, x in zip(found, items):
        data = f.get("data") or {}
        where = ".".join(filter(None, [data.get("table"), data.get("column") or ",".join(data.get("columns") or [])]))
        tail = f" · {x['evidence']}" if x["evidence"] else ""
        lines.append(f"- {where or x['name']} · {x['say']}{tail}")
    return "\n".join(lines)


def _attached(s, owner: str) -> dict | None:
    return next((e for e in s.log if e.get("kind") == "attach" and owner in (e.get("added") or [])), None)


def _detach_fix(s, owner: str, recommended: bool, *, why: str = "") -> dict | None:
    st, comp = s.studio, s.studio.composition
    m = next((x for x in comp.modules if x.name == owner), None) if comp else None
    if m is None or owner == WORKSPACE or m.kind in KEEP_ON:
        return None
    try:
        imp = st.detach_impact(owner)
    except Exception:  # what cannot be worked out is not offered
        return None
    if not imp.ok:
        return None
    gone = _amount(imp.removed)
    return _fix(f"{s._label(owner)} 모듈 해제", "now", " ".join(filter(None, [why, f"{gone}가 빠집니다." if gone else ""])), "영향 보고 해제",
                run={"route": "detach", "body": {"name": owner}}, preview=owner, recommended=recommended)


def _missing_fixes(s, owner: str, found: list[dict], items: list[dict]) -> list[dict]:
    """A column or table the definition reads and the source lacks."""
    props = [x for x in items if x["go"].get("field") == "column" or x["go"].get("field") == "table"]
    every_near = bool(props) and all(x["near"] for x in props)
    recent = _attached(s, owner) if owner else None
    out = []
    rebind = _fix("원천 컬럼 다시 지정", "here", (f"비슷한 이름의 컬럼 {props[0]['near']}을 채워 둡니다." if every_near else "모듈을 유지합니다. 작업 공간에서 이 속성의 원천 컬럼 칸이 열립니다."),
                  "고치러 가기", go=items[0]["go"], steps=_steps(items), recommended=every_near)
    leave = _detach_fix(s, owner, not every_near and bool(recent), why="비슷한 컬럼이 없고 방금 적용한 모듈입니다." if recent and not every_near else "")
    out += [leave] if leave and leave["recommended"] else []
    out += [rebind]
    out += [leave] if leave and not leave["recommended"] else []
    tables: dict[str, list[str]] = {}
    for f in found:
        d = f.get("data") or {}
        tables.setdefault(d.get("table", ""), []).extend([d["column"]] if d.get("column") else [])
    said = ", ".join(f"{t}에 {', '.join(c)}" if c else f"{t} 테이블" for t, c in tables.items())
    asked = "\n".join(["온톨로지 정의와 원천 DB를 맞추기 위한 요청입니다.",
                       *[f"- {t} 테이블에 {', '.join(c)} 컬럼이 필요합니다." if c else f"- {t} 테이블이 필요합니다." for t, c in tables.items()]])
    out.append(_fix("원천에 컬럼 추가 요청", "source", f"{said}가 필요하다는 내용을 복사합니다.", "요청 내용 복사", copy=asked))
    return out


def _other_fixes(s, kind: str, owner: str, found: list[dict], items: list[dict]) -> list[dict]:
    first = items[0]
    mine = owner == WORKSPACE
    source = _fix("원천 정리 목록 복사", "source", "원천 담당자에게 넘길 행 목록을 복사합니다.", "목록 복사", copy=_cleanup(found, items))
    if kind == "type":
        data = found[0].get("data") or {}
        retype = _type_of(data.get("sql_type", ""))
        out = [_fix("자료형 맞추기", "here", f"자료형을 원천 컬럼에 맞춰 {retype}으로 채워 둡니다.", "고치러 가기",
                    go={**first["go"], "field": "type", "prefill": retype}, recommended=True)] if mine else []
        return [*out, _fix("변환식 넣기", "here", "원천 값을 읽는 변환식을 지정합니다.", "고치러 가기", go={**first["go"], "field": "transform"}, recommended=not mine)]
    if kind == "key":
        return [*([_fix("키 컬럼 다시 지정", "here", "키 컬럼 칸이 열립니다.", "고치러 가기", go=first["go"], steps=_steps(items))] if mine else []), source]
    if kind == "required":
        return [_fix("필수 해제", "here", "필수 값 표시를 끈 채로 속성을 엽니다.", "고치러 가기", go=first["go"], steps=_steps(items)), source]
    if kind == "enum":
        return [_fix("허용값에 추가", "here", "벗어난 값을 허용값 칸에 채워 둡니다.", "고치러 가기", go=first["go"], steps=_steps(items), recommended=True), source]
    if kind == "orphan":
        return [_fix("관계 연결 기준 열기", "here", "관계의 연결 기준 칸이 열립니다.", "고치러 가기", go=first["go"], steps=_steps(items)), source]
    return [_fix("항목 열기", "here", "작업 공간에서 이 항목을 엽니다.", "고치러 가기", go=first["go"], steps=_steps(items)), source]


def _bindings(s, bind: dict, alert: bool) -> list[dict]:
    st = s.studio
    comp, src = st.composition, st.backends.get(st.source) if st.source else None
    groups: dict[tuple[str, str], list[dict]] = {}
    for f in bind.get("findings") or []:
        owner = (comp.owner(f["element"]) if comp else "") or ""
        groups.setdefault((owner, "missing" if f["kind"] in ("table", "column") else f["kind"]), []).append(f)
    out = []
    for (owner, fam), found in groups.items():
        items = [_bind_item(s, f, src) for f in found]
        errors = any(f["severity"] == "error" for f in found)
        fixes = _missing_fixes(s, owner, found, items) if fam == "missing" else _other_fixes(s, fam, owner, found, items)
        note = ""
        if fam == "missing":
            data = found[0].get("data") or {}
            have = _columns(src, data.get("table", ""))
            near = [x for x in items if x["near"]]
            note = (f"비슷한 이름의 컬럼이 있습니다: {', '.join(x['near'] for x in near)}" if near
                    else f"{data.get('table')} 테이블 컬럼 {len(have)}개 중 비슷한 이름이 없습니다." if have else "")
        more = f" 외 {len(found) - 1}건" if len(found) > 1 else ""
        issue = _issue(f"bind:{fam}:{owner or 'none'}", f"bind.{fam}", "bad" if errors else "warn", "ontology",
                       f"DB 대조 {'오류' if errors else '경고'} {len(found)}건", f"{items[0]['name']}{more} · {FINDING.get(found[0]['kind'], found[0]['kind'])}",
                       key="bind", items=items, note=note, fixes=fixes, alert=alert)
        issue["owner"] = owner
        if owner and owner != WORKSPACE:
            entry = _attached(s, owner)
            imp = st.detach_impact(owner)
            brought = _amount(imp.removed)
            at = str(entry.get("at", ""))[11:19] if entry else ""
            issue["cause"] = {"kind": "module", "ref": owner, "label": s._label(owner), "at": at,
                              "text": (f"{at}에 적용한 {s._label(owner)} 모듈이 {brought}를 추가했습니다." if at and brought else f"이 항목은 {s._label(owner)} 모듈이 정의합니다.")}
            if entry and "그래프 저장소에 반영하지" in str(entry.get("text", "")):
                issue["effects"].append({"label": "그래프 저장소", "say": "이 정의를 반영하지 못함"})
        seen: list[str] = []
        for x in items:
            seen += [r for r in s._readers(x["element"]) if r not in seen]
        issue["readers"] = seen[:8]
        out.append(issue)
    return out


# ---- what fails further down ------------------------------------------------------------------------------------------


def _open_for(q) -> dict:
    if not (q.decision or q.query):  # a question on what a word means reads neither: its row is where it is seen
        return {"tab": "check", "row": f"q:{q.id}"}
    return {"tab": "mgrules", "decision": q.decision} if q.decision else {"tab": "query", "query": q.query}


def _query(s, conf: dict, gate: dict) -> dict:
    onto = s.studio.onto
    reports = conf.get("reports") or []

    def outcome(o: dict) -> str:
        return "실행 실패" if o.get("error") else f"{o.get('rows') or 0:,}행"

    items = []
    for r in reports:
        q = onto.queries.get(r["name"])
        failed = any(o.get("error") for o in r["outcomes"].values())
        items.append({"element": f"query:{r['name']}", "name": r["name"], "label": (q.label if q else "") or r["name"], "row": f"conf:{r['name']}",
                      "say": "원천 DB 실행 실패" if failed and (r["outcomes"].get(s.studio.source) or {}).get("error") else "실행 실패" if failed else "저장소 결과 불일치",
                      "evidence": " · ".join(f"{b} {outcome(o)}" for b, o in r["outcomes"].items()), "near": "", "go": {"tab": "check", "row": f"conf:{r['name']}"}})
    errors = any("실행 실패" in x["say"] for x in items)
    fixes = []
    if items:
        fixes.append(_fix("질의 열기", "here", "질의 화면에서 이 질의를 선택해 실행합니다.", "질의 열기", go={"tab": "query", "query": items[0]["name"]},
                          steps=[{"label": x["label"], "go": {"tab": "query", "query": x["name"]}} for x in items], recommended=errors))
    fixes.append(_fix("원천 다시 읽기", "now", "원천을 그래프 저장소에 다시 반영한 뒤 다시 측정합니다.", "다시 읽기", run={"route": "sync", "body": {}}, recommended=not errors))
    detail = " · ".join([items[0]["label"], items[0]["say"]]) if items else (conf.get("error") or f"기준 {_pct(gate['limit'])} · 현재 {_pct(gate['value'])}")
    title = f"Backend 결과 일치 {conf.get('agree')} / {conf.get('queries')}" if "queries" in conf else "Backend 결과 비교 실패"
    return _issue("gate:query.min_agree", "query", "bad", "use", title, detail, key="gate:query.min_agree", items=items, note=conf.get("error", ""), fixes=fixes)


def _decide(s, agree: dict, gate: dict) -> dict:
    st = s.studio
    spec, name = st.flow.agreement or {}, (st.flow.agreement or {}).get("decision", "")
    key = spec.get("key")
    items = []
    for x in (agree.get("mismatches") or [])[:ITEMS_MAX]:
        case = x.get("case") or {}
        who = str(case.get(key) if key else next(iter(case.values()), ""))
        items.append({"element": f"decision:{name}", "name": who, "label": who, "row": f"case:{who}", "near": "",
                      "say": f"과거 처리 {_short(x.get('expected'))}", "evidence": f"지금 판정 {_short(x.get('got'))}",
                      "go": {"tab": "mgrules", "decision": name, **({"key": who} if key else {})}})
    d = st.onto.decisions.get(name)
    label = (d.label if d else "") or name
    fixes = [_fix("그 사례로 규칙 시험", "here", "규칙 화면에서 이 사례를 판정해 어느 규칙이 답했는지 봅니다.", "규칙 열기", go=items[0]["go"], steps=_steps(items), recommended=True)] if items else []
    fixes.append(_fix("결정표 열기", "here", f"{label} 결정표를 엽니다.", "결정표 열기", go={"tab": "mgrules", "decision": name}))
    return _issue("gate:decide.min_agreement", "decide", "bad", "use", f"판정 일치율 {_pct(agree.get('rate'))}",
                  agree.get("error") or f"기준 {_pct(gate['limit'])} · 불일치 {len(agree.get('mismatches') or [])}건", key="gate:decide.min_agreement", items=items, fixes=fixes)


def _accuracy(s, check: dict, gate: dict) -> dict:
    onto = s.studio.onto
    items = []
    fixes = []
    for w in check.get("wrong") or []:
        q = next((x for x in onto.questions if x.id == w["id"]), None)
        items.append({"element": f"question:{w['id']}", "name": w["id"], "label": w.get("text") or w["id"], "row": f"q:{w['id']}", "near": "",
                      "say": "실행 실패" if w.get("error") else f"기대 {_short(w.get('expected'))}", "evidence": w.get("error") or f"결과 {_short(w.get('got'))}", "error": w.get("error") or "",
                      "go": _open_for(q) if q else {"tab": "check", "row": f"q:{w['id']}"}})
    if items:
        fixes.append(_fix("규칙 · 질의 열기", "here", "이 질문이 읽는 규칙이나 질의를 엽니다.", "열기", go=items[0]["go"], steps=_steps(items), recommended=True))
        fixes.append(_fix("의도한 변경이면 정답 갱신", "here", "검증 화면의 이 질문 행에서 현재 결과를 정답으로 바꿉니다.", "질문 보기",
                          go={"tab": "check", "row": items[0]["row"]}))
    return _issue("gate:check.min_accuracy", "check.accuracy", "bad", "verify", f"검증 질문 정답률 {_pct(check.get('accuracy'))}",
                  f"기준 {_pct(gate['limit'])} · 틀린 질문 {len(items)}개", key="gate:check.min_accuracy", items=items, fixes=fixes)


def _grounded(s, check: dict, gate: dict) -> dict:
    onto = s.studio.onto
    items = []
    for qid, gaps in (check.get("ungrounded") or {}).items():
        q = next((x for x in onto.questions if x.id == qid), None)
        items.append({"element": f"question:{qid}", "name": qid, "label": (q.text if q else "") or qid, "row": f"q:{qid}", "near": "", "say": "근거 부족",
                      "evidence": ", ".join(gaps), "go": _open_for(q) if q else {"tab": "check", "row": f"q:{qid}"}})
    fixes = [_fix("규칙 · 질의 열기", "here", "근거가 빠진 질문이 읽는 규칙이나 질의를 엽니다.", "열기", go=items[0]["go"], steps=_steps(items), recommended=True)] if items else []
    return _issue("gate:check.min_grounded", "check.grounded", "bad", "verify", f"근거 제시율 {_pct(check.get('grounded'))}",
                  f"기준 {_pct(gate['limit'])} · 근거가 빠진 질문 {len(items)}개", key="gate:check.min_grounded", items=items, fixes=fixes)


def _values(s, check: dict, gate: dict) -> dict:
    err = check.get("value_error")
    if err:
        m = re.search(r"no such column: (\S+)", err)
        said = f"원천 DB에 {m.group(1).split('.')[-1]} 컬럼이 없습니다." if m else err
        items = [{"element": "", "name": "values", "label": "거래 값 대조", "say": "실행 실패", "evidence": said, "near": "", "row": "values", "go": {"tab": "check", "row": "values"}}]
        title, detail = "거래 값 대조 실행 실패", said
    else:
        items = [{"element": "", "name": str(w.get("key")), "label": f"{v.get('label')} · {w.get('key')}", "say": f"온톨로지 {_short(w.get('answer'))}", "near": "",
                  "evidence": f"거래 시스템 {_short(w.get('truth'))}", "row": "values", "go": {"tab": "check", "row": "values"}}
                 for v in check.get("values") or [] for w in v.get("mismatches") or []]
        title, detail = f"거래 값 오류 {check.get('value_errors')}건", f"기준 {gate['limit']}건 · 대조 {check.get('value_cases', 0):,}건"
    fixes = [_fix("대조 결과 열기", "here", "검증 화면의 거래 값 정확도로 이동합니다.", "결과 열기", go={"tab": "check", "row": "values"}, recommended=not err),
             _fix("대조 항목 설정 열기", "here", "흐름 설정의 거래 값 대조로 이동합니다.", "설정 열기", go={"tab": "flow", "row": "values"})]
    return _issue("gate:check.max_value_errors", "check.values", "bad", "verify", title, detail, key="gate:check.max_value_errors", items=items, fixes=fixes)


def _index(s, index: dict, gate: dict) -> dict:
    items = [{"element": "", "name": x["text"], "label": x["text"], "say": f"기대 문서 {x['document']}", "evidence": "", "near": "", "row": "", "go": {"tab": "vectors"}}
             for x in index.get("missed") or []]
    fixes = [_fix("문서 추가", "here", "카탈로그에서 문서를 올린 뒤 다시 측정합니다.", "카탈로그 열기", go={"tab": "catalog"}, recommended=True),
             _fix("문서 · 벡터 화면 열기", "here", "색인 상태와 검색 결과를 확인합니다.", "화면 열기", go={"tab": "vectors"})]
    return _issue("gate:index.min_found", "index", "bad", "store", f"문서 검색 적중 {index.get('found')} / {index.get('questions')}",
                  f"기준 {_pct(gate['limit'])} · 못 찾은 질문 {len(items)}개", key="gate:index.min_found", items=items, fixes=fixes)


def _files(files: dict) -> list[dict]:
    bad = [(p, f) for p, f in files.items() if f.get("error")]
    if not bad:
        return []
    items = [{"element": "", "name": p.rsplit("/", 1)[-1], "label": p.rsplit("/", 1)[-1], "say": "읽기 실패", "evidence": str(f.get("error") or ""), "near": "",
              "row": f"file:{p}", "go": {"tab": "catalog", "file": p}} for p, f in bad]
    fixes = [_fix("파일 확인하고 다시 올리기", "here", "카탈로그에서 파일과 실패 사유를 엽니다.", "파일 열기", go=items[0]["go"], steps=_steps(items), recommended=True),
             _fix("휴지통으로 보내기", "now", "이 파일을 쓰지 않습니다. 휴지통에서 되살릴 수 있습니다.", "휴지통으로", run={"route": "catalog/remove", "body": {"paths": [p for p, _ in bad]}})]
    return [_issue("files:unread", "file", "warn", "convert", f"읽기 실패 파일 {len(bad)}개", items[0]["name"], key="files", items=items, fixes=fixes)]


# ---- one cause, what it brings down -------------------------------------------------------------------------------------


def _depends(other: dict, queries: set[str], decisions: set[str], questions: set[str], columns: set[str], check: dict, agree: dict) -> bool:
    """Whether a failure reads what is broken: every item of it, by name, or an error naming a missing column."""
    named = lambda text: any(c and re.search(rf"\b{re.escape(c)}\b", str(text or "")) for c in columns)  # noqa: E731
    if other["kind"] == "query":
        return bool(other["items"]) and all(x["name"] in queries for x in other["items"])
    if other["kind"] in ("check.accuracy", "check.grounded"):
        return bool(other["items"]) and all(x["name"] in questions or named(x.get("error")) for x in other["items"])  # an answer is no error
    if other["kind"] == "check.values":
        return named(check.get("value_error"))
    if other["kind"] == "decide":
        return (st := agree.get("error")) is not None and named(st) or (bool(other["items"]) and all(x["element"].split(":", 1)[1] in decisions for x in other["items"]))
    return False


def _gather(s, issues: list[dict], measured: dict) -> list[dict]:
    """A missing column or table takes in the failures that read it; the module it came with is named as their cause."""
    onto = s.studio.onto
    check, agree = measured.get("check") or {}, measured.get("decide") or {}
    taken: set[str] = set()
    for root in [x for x in issues if x["kind"] == "bind.missing" and x.get("owner") and x["cause"]]:
        queries, decisions, questions = _reach(onto, [i["element"] for i in root["items"]])
        columns = {i["element"].rsplit(".", 1)[-1] for i in root["items"]}
        for other in issues:
            if other is root or other["id"] in taken or not _depends(other, queries, decisions, questions, columns, check, agree):
                continue
            taken.add(other["id"])
            root["members"].append(other)
            root["keys"] += other["keys"]
            root["floors"] = list(dict.fromkeys([*root["floors"], other["floor"]]))
            root["effects"] += [{"label": (f"질의 {x['label']}" if other["kind"] == "query" else x["label"]), "say": x["say"]} for x in other["items"][:4]]
            other["cause"] = {"kind": "issue", "ref": root["id"], "label": root["title"], "at": "", "text": f"{root['cause']['text']} 이 문제는 그 항목을 읽어서 생겼습니다."}
        if root["members"]:
            root["title"], root["bind_title"] = (f"{root['cause']['label']} 모듈이 없는 컬럼을 읽습니다", root["title"])
    return [x for x in issues if x["id"] not in taken]


def build(s, watch: dict) -> list[dict]:
    """Everything the last measurement found, the failures that share a cause under it."""
    flow, measured = watch["flow"], watch.get("measured") or {}
    steps = {x["id"]: x for x in flow["steps"]}
    failing = {f"{g['stage']}.{g['condition']}": g for x in flow["steps"] if x.get("on") is not False for g in x.get("gates") or [] if not g["passed"]}
    bind_step = steps["bind"]
    bind_failed = bind_step.get("on") is not False and (bind_step.get("ok") is False or any(not g["passed"] for g in bind_step.get("gates") or []))
    out = _files(s.repositories.files(s.repo))
    out += _bindings(s, measured.get("bind") or {}, bind_failed)
    check = measured.get("check") or {}
    makers = [("query.min_agree", _query, measured.get("query") or {}), ("decide.min_agreement", _decide, measured.get("decide") or {}),
              ("check.min_accuracy", _accuracy, check), ("check.min_grounded", _grounded, check), ("check.max_value_errors", _values, check),
              ("index.min_found", _index, measured.get("index") or {})]
    out += [make(s, data, failing[key]) for key, make, data in makers if key in failing]
    out = _gather(s, out, measured)
    for x in out:
        if not x["effects"] and x.get("readers"):
            x["effects"] = [{"label": r, "say": "이 항목을 읽습니다"} for r in x["readers"]]
    return out


def waiting(s, *, dirty: bool, changes: int, actions: int) -> list[dict]:
    """What waits on a person rather than being broken: opened as it is, with no panel in between. And open source
    conflicts, which are chosen in the panel."""
    st = s.studio
    out = []
    if dirty:
        x = _issue("work:workspace", "workspace", "warn", "ontology", "대기 중인 관리 변경", "변경 요청이 필요합니다", key="dirty")
        x["direct"] = {"tab": "model", "left": "changes"}
        out.append(x)
    if changes:
        pending = [c for c in st.changes.requests.values() if c.status == "pending"]
        x = _issue("work:changes", "change", "warn", "ontology", f"승인 대기 변경 {changes}건", s._change_label(pending[0]), key="changes")
        x["direct"] = {"tab": "changes", **({"change": pending[0].id} if len(pending) == 1 else {})}
        out.append(x)
    if actions:
        pending = [p for p in st.actions.proposals.values() if p.status == "pending"]
        x = _issue("work:actions", "action", "warn", "use", f"승인 대기 처리 {actions}건", "판정 · 처리", key="actions")
        x["direct"] = {"tab": "inbox", "row": f"action:{pending[0].id}"} if pending else {"tab": "inbox"}
        out.append(x)
    for c in st.onto.source_conflicts():
        if not c.open:
            continue
        says = [{"label": a.source, "say": ", ".join(f"{k} {v}" for k, v in a.says.items())} for a in c.answers]
        fixes = [_fix(f"{a.source} 고르기", "here", "고른 출처는 대기 중인 변경에 기록되고 변경 요청을 거쳐 반영됩니다.", "고르기",
                      run={"route": "conflict/pick", "body": {"id": c.id, "source": a.source}}) for a in c.answers]
        fixes.append(_fix("규칙 화면에서 보기", "here", "출처 충돌 목록의 이 항목으로 이동합니다.", "화면 열기", go={"tab": "rules", "row": f"conflict:{c.id}"}))
        d = st.onto.decisions.get(c.decision)
        x = _issue(f"conflict:{c.id}", "conflict", "warn", "use", c.label or c.id, "출처끼리 답이 다릅니다", key=f"conflict:{c.id}",
                   items=[{"element": "", "name": a["label"], "label": a["label"], "say": a["say"], "evidence": "", "near": "", "row": "", "go": {"tab": "rules", "row": f"conflict:{c.id}"}} for a in says],
                   fixes=fixes, alert=False)
        x["effects"] = [{"label": f"결정 {(d.label if d else '') or c.decision}" if c.decision else "판정", "say": "고를 때까지 기존 규칙으로 판정합니다"}]
        out.append(x)
    return out
