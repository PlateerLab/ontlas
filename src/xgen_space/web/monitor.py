"""The pipeline as a control board: five floors from raw files to checked answers, every number read from the studio.

A floor's state comes from what the flow measures (its pass conditions and the database check) and from what waits on a
person (files that could not be read, changes and actions not yet approved). A failure that crosses floors is told as a
chain, from the stage where it shows down to the module that brought it.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from xgen_space.preview import MODULE_COLOR, TARGETS

FLOORS = [("source", "①", "원천 데이터", "catalog"), ("convert", "②", "변환", "convert"),
          ("ontology", "③", "온톨로지 구축", "library"), ("use", "④", "활용", "query"), ("verify", "⑤", "검증", "check")]
STAGES = {"source": ("source", "원천 데이터", "sources"), "define": ("ontology", "온톨로지 정의", "library"),
          "bind": ("ontology", "DB 대조", "bind"), "project": ("ontology", "그래프 저장소 반영", "onto"),
          "query": ("use", "질의", "query"), "decide": ("use", "판정 · 처리", "decide"), "check": ("verify", "검증", "check")}
FINDING = {"table": "테이블 없음", "column": "컬럼 없음", "type": "타입 불일치", "key": "키 중복", "required": "필수 값 누락",
           "enum": "정의에 없는 값", "orphan": "끊긴 관계"}
RANK = {"off": 0, "ok": 1, "warn": 2, "bad": 3}
NODES_MAX = 8
MODULES_MAX = 8


def _n(v: Any) -> str:
    return f"{v:,}" if isinstance(v, int) else str(v)


def _pct(v: Any) -> str:
    return "-" if v is None else f"{round(v * 100)}%"


def _worst(states: list[str]) -> str:
    return max(states, key=RANK.get) if states else "ok"


def failed(step: dict) -> bool:
    """A stage that does not meet its pass conditions, or the database check that found something."""
    if step.get("on") is False:
        return False
    if any(not g["passed"] for g in step.get("gates") or []):
        return True
    return step["id"] == "bind" and step.get("ok") is False


def _gate_value(g: dict, v: Any) -> str:
    return _pct(v) if str(g.get("condition", "")).startswith("min_") else _n(v)


def _tag(key: str, label: str, value: Any, state: str = "ok", tab: str = "") -> dict:
    return {"key": key, "label": label, "value": _n(value), "status": state, "tab": tab}


def _file_counts(files: dict) -> dict:
    out = {"data": 0, "definition": 0, "document": 0, "unread": 0}
    for f in files.values():
        kind = "unread" if f.get("error") else (f.get("facts") or {}).get("kind")
        if kind in out:
            out[kind] += 1
    return out


def _json_counts(files: dict) -> dict:
    total = {"tables": 0, "codes": 0, "terms": 0, "messages": 0, "documents": 0}
    for f in files.values():
        if f.get("included") and not f.get("error"):
            for k in total:
                total[k] += (f.get("facts") or {}).get(k) or 0
    return total


def _graph(onto) -> tuple[list[dict], list[list[str]]]:
    """The objects with the most relations, and the relations among them."""
    degree: dict[str, int] = {name: 0 for name in onto.objects}
    for lk in onto.links.values():
        for end in (lk.source, lk.target):
            if end in degree:
                degree[end] += 1
    top = sorted(degree, key=lambda k: (-degree[k], k))[:NODES_MAX]
    nodes = [{"id": k, "label": onto.objects[k].label or k} for k in top]
    edges = sorted({tuple(sorted((lk.source, lk.target))) for lk in onto.links.values()
                    if lk.source in top and lk.target in top and lk.source != lk.target})
    return nodes, [list(e) for e in edges]


def _alerts(steps: dict, files: dict, counts: dict, findings: list[dict], *, changes: int, actions: int,
            dirty: bool) -> list[dict]:
    out = []
    if counts["unread"]:
        name = next(p for p, f in files.items() if f.get("error")).rsplit("/", 1)[-1]
        out.append({"floor": "convert", "level": "warn", "title": f"읽기 실패 파일 {counts['unread']}개",
                    "detail": name, "tab": "catalog"})
    if findings:
        first = findings[0]
        where = str(first.get("element", "")).split(":", 1)[-1]
        out.append({"floor": "ontology", "level": "bad", "title": f"DB 대조 오류 {len(findings)}건",
                    "detail": f"{where} · {FINDING.get(first.get('kind'), first.get('kind'))}", "tab": "bind"})
    for s in steps.values():
        if s.get("on") is False:
            continue
        for g in s.get("gates") or []:
            if not g["passed"] and s["id"] != "bind":
                out.append({"floor": STAGES[s["id"]][0], "level": "bad", "title": f"{g['label']} 미충족",
                            "detail": f"기준 {_gate_value(g, g['limit'])} · 현재 {_gate_value(g, g['value'])}",
                            "tab": STAGES[s["id"]][2]})
    if dirty:
        out.append({"floor": "ontology", "level": "warn", "title": "대기 중인 관리 변경", "detail": "변경 요청이 필요합니다",
                    "tab": "objects"})
    if changes:
        out.append({"floor": "ontology", "level": "warn", "title": f"승인 대기 변경 {changes}건", "detail": "온톨로지 라이브러리",
                    "tab": "library"})
    if actions:
        out.append({"floor": "use", "level": "warn", "title": f"승인 대기 처리 {actions}건", "detail": "판정 · 처리",
                    "tab": "decide"})
    return out


def _chain(steps: dict, findings: list[dict], owner_label) -> dict | None:
    """From the last stage that fails down to the first, and to the module that brought the first."""
    bad = [s for s in steps.values() if failed(s)]
    if not bad:
        return None
    path = []
    for s in reversed(bad):
        floor, word, tab = STAGES[s["id"]]
        gate = next((g for g in s.get("gates") or [] if not g["passed"]), None)
        detail = f"{g_label(gate)}" if gate else ""
        path.append({"floor": floor, "label": word, "detail": detail, "tab": tab})
    owners: dict[str, list[str]] = {}
    for f in findings:
        element = str(f.get("element", ""))
        owners.setdefault(owner_label(element), []).append(element.split(":", 1)[-1])
    for label, where in owners.items():
        if label:
            path.append({"floor": "ontology", "label": f"{label} 모듈", "detail": ", ".join(where[:3]), "tab": "library"})
    return {"steps": path, "floors": len({p["floor"] for p in path})}


def g_label(g: dict) -> str:
    return f"{g['label']} {_gate_value(g, g['limit'])} · 현재 {_gate_value(g, g['value'])}"


def board(flow: dict, *, files: dict, onto, modules: list, owner_label, findings: list[dict], changes: int = 0,
          actions: int = 0, dirty: bool = False, faults: list[dict] | None = None) -> dict:
    """The floors, what is wrong on them, and the chain across them."""
    steps = {s["id"]: s for s in flow["steps"]}
    source, define, bind, project = steps["source"], steps["define"], steps["bind"], steps["project"]
    query, decide, check = steps["query"], steps["decide"], steps["check"]
    counts = _file_counts(files)
    one = _json_counts(files)
    alerts = _alerts(steps, files, counts, findings, changes=changes, actions=actions, dirty=dirty)
    conf = query.get("conformance") or {}
    agree = decide.get("agreement") or {}
    gates = [g for s in steps.values() for g in s.get("gates") or []]
    nodes, edges = _graph(onto)

    def state(*stage_ids: str) -> str:
        return "bad" if any(failed(steps[i]) for i in stage_ids) else "ok"

    tags = {
        "source": [_tag("source.tables", "테이블", len(source["tables"]), tab="sources"),
                   _tag("source.rows", "행", source["rows"], tab="sources"),
                   _tag("source.data", "테이블 데이터", counts["data"], tab="catalog"),
                   _tag("source.definition", "정의서", counts["definition"], tab="catalog"),
                   _tag("source.document", "문서", counts["document"], tab="catalog")],
        "convert": [_tag("convert.sheet", "시트 변환", counts["data"], tab="catalog"),
                    _tag("convert.schema", "스키마 변환", counts["definition"], tab="catalog"),
                    _tag("convert.text", "문서 변환", counts["document"], tab="catalog"),
                    _tag("convert.unread", "읽기 실패", counts["unread"], "warn" if counts["unread"] else "ok", "catalog"),
                    _tag("convert.json", "변환 테이블", one["tables"], tab="convert")],
        "ontology": [_tag("ontology.modules", "모듈", len(define["modules"]), tab="library"),
                     _tag("ontology.objects", "객체", define["objects"], tab="objects"),
                     _tag("ontology.links", "관계", define["links"], tab="links"),
                     _tag("ontology.findings", "DB 대조 오류", bind.get("findings") or 0, state("bind"), "bind"),
                     _tag("ontology.nodes", "그래프 노드", project.get("nodes") or 0, tab="onto")],
        "use": [_tag("use.queries", "등록 질의", query["queries"], tab="query"),
                _tag("use.agree", "결과 일치", f"{conf.get('agree', 0)} / {conf.get('queries', 0)}" if conf else "-",
                     state("query"), "query"),
                _tag("use.rules", "결정 규칙", decide["rules"], tab="decide"),
                _tag("use.agreement", "판정 일치율", _pct(agree.get("rate")), state("decide"), "decide"),
                _tag("use.waiting", "승인 대기", actions, "warn" if actions else "ok", "decide")],
        "verify": [_tag("verify.questions", "검증 질문", check["questions"], tab="check"),
                   _tag("verify.accuracy", "정답률", _pct(check.get("accuracy")), state("check"), "check"),
                   _tag("verify.grounded", "근거 제시율", _pct(check.get("grounded")), tab="check"),
                   _tag("verify.gates", "통과 조건", f"{sum(g['passed'] for g in gates)} / {len(gates)}",
                        "ok" if flow["passed"] else "bad", "flow")],
    }
    parts = {
        "source": {"stores": [{"name": source["backend"], "dialect": str(source.get("dialect") or "").upper()}]},
        "ontology": {"modules": [{"label": m["label"], "color": MODULE_COLOR.get(m["kind"], "#8a96a5")}
                                 for m in define["modules"][:MODULES_MAX]],
                     "nodes": nodes, "edges": edges, "store": bool(project.get("backends"))},
        "use": {"targets": [label for _, label in TARGETS]},
        "verify": {"gates": [{"label": g["label"], "passed": g["passed"]} for g in gates]},
    }
    floors = []
    for fid, no, label, tab in FLOORS:
        mine = [a for a in alerts if a["floor"] == fid]
        floors.append({"id": fid, "no": no, "label": label, "tab": tab, "tags": tags[fid], "alerts": len(mine),
                       "status": _worst([a["level"] for a in mine])})
    shape = {k: [v.get(x) for x in sorted(v) if x != "gates"] for k, v in parts.items()}
    shape["gates"] = [g["label"] for g in parts["verify"]["gates"]]
    return {"floors": floors, "parts": parts, "alerts": alerts, "passed": flow["passed"],
            "status": _worst([f["status"] for f in floors]), "gates": {"met": sum(g["passed"] for g in gates), "all": len(gates)},
            "chain": _chain(steps, findings, owner_label), "faults": faults or [],
            "shape": hashlib.sha256(json.dumps(shape, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]}
