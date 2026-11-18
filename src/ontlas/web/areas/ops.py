"""운영 › 저장소 · 엔진, 연동 · API, 접근 정책: what those screens ask that the older routes do not answer.

- who may call /v1 on this server (the names the server was started with, never a token), what each may do, and what the
  audit trail says each has asked;
- one /v1 call tried from the page as a given access policy would make it;
- every passage embedded again.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from ontlas.web.routes import get, post
from ontlas.words import fix as with_particles

# the callers of /v1, handed over by the server once it has made them (see register_rest); None where /v1 is off
_REST: dict[str, Any] = {"rest": None}

# what the audit trail calls an agent's call, in the page's words
EVENT_WORD = {"decided": "판정", "answered": "답변", "validated": "값 검증", "function_ran": "함수 실행", "requested": "Action 요청",
              "executed": "Action 실행", "auto_approved": "자동 승인"}


def register_rest(rest) -> None:
    """The server says who may call /v1. The screens then name each caller and its policy; a token is never read."""
    _REST["rest"] = rest


def on_serve(*, rest=None, **_) -> None:
    register_rest(rest)


def _studios(rest, tools) -> list:
    """Every studio this caller has asked: the one it holds, and each library it named."""
    out = [tools.studio]
    out += [t.studio for (owner, _), t in rest._tools.items() if owner == id(tools)]
    return list({id(x): x for x in out}.values())


def _target(rest, tools, month: str) -> dict:
    calls, last, by_event, this_month = 0, "", {}, 0
    for studio in _studios(rest, tools):
        for e in studio.actions.audit:
            if e.actor != tools.actor.id or e.actor_kind != "agent":
                continue
            calls += 1
            last = max(last, str(e.at))
            this_month += str(e.at).startswith(month)
            word = EVENT_WORD.get(e.event, e.event)
            by_event[word] = by_event.get(word, 0) + 1
    return {"name": tools.actor.id, "policy": tools.role or "", "write": not tools.read_only,
            "principal": sorted(tools.principal), "calls": calls, "month": this_month, "last": last, "events": by_event}


def _asked(rest, tools, library: str) -> dict[str, int]:
    """The Actions this caller requested of the ontology open on the page, each with its requests, from the audit trail:
    a request filed, or one turned away before it was (both stamped with the caller)."""
    first = not rest.libraries or library in ("", rest.libraries[0].get("id"))
    held = tools if first else rest._tools.get((id(tools), library))
    out: dict[str, set] = {}
    for e in held.studio.actions.audit if held is not None else []:
        if e.actor == tools.actor.id and e.actor_kind == "agent" and e.action and e.event in ("requested", "rejected"):
            out.setdefault(e.action, set()).add(e.proposal)
    return {k: len(v) for k, v in out.items()}


@get("ops/targets")
def targets(s, a, who) -> dict:
    """The callers of /v1 on this server: each with its policy, whether it may request actions, and what the audit
    trail holds of it (decisions, answers, functions, action requests: the calls that are recorded)."""
    rest = _REST["rest"]
    on = bool(getattr(s.data, "rest", False))
    now = dt.datetime.now()  # the audit trail is stamped by the machine's clock, so the month is too
    month = now.strftime("%Y-%m")
    rows = [_target(rest, tools, month) for _, tools in rest.clients] if rest is not None else []
    roles = set(s.studio.onto.roles)
    for r in rows:
        r["policy_known"] = not r["policy"] or r["policy"] in roles
    asked: dict[str, list] = {}  # by Action: the callers that requested it, for what taking the Action out leaves
    for _, tools in rest.clients if rest is not None else []:
        for action, n in sorted(_asked(rest, tools, str(getattr(s, "library_id", "") or "")).items()):
            asked.setdefault(action, []).append({"name": tools.actor.id, "requests": n})
    return {"rest": on, "listed": rest is not None, "targets": rows, "month": month, "days": now.day,  # days of the month so far
            "calls_month": sum(r["month"] for r in rows), "calls": sum(r["calls"] for r in rows), "actions": asked}


def _tried_on(s, role: str):
    """The studio a policy is tried on, and whether it is the definition being written: a policy that change request
    adds or changes is tried as it would be deployed, on a copy of the studio over that change request; any other on
    the deployed definition, as a platform calls it now."""
    from ontlas.modules import ModuleError
    from ontlas.review import FlowSettings, element_diff, trial

    deployed = s.studio.onto.roles
    try:
        ws = s._ws()
    except ValueError:  # a studio not made of modules has no change request to write
        ws = None
    if ws is None or not ws.dirty:
        if role and role not in deployed:
            raise ValueError(with_particles(f"접근 정책 {role}이(가) 없어 실행하지 못했습니다. 접근 정책을 다시 선택해 주세요."))
        return s.studio, False
    try:
        comp = ws.composed()
    except ModuleError:
        raise ValueError("작성 중인 변경 요청의 정의 오류로 정책을 시험하지 못했습니다. 변경 요청을 확인해 주세요.") from None
    if role and role not in comp.ontology.roles:
        raise ValueError(with_particles(f"접근 정책 {role}이(가) 없어 실행하지 못했습니다. 접근 정책을 다시 선택해 주세요."))
    if not role or (role in deployed and f"role:{role}" not in element_diff(s.studio.onto, comp.ontology)["changed"]):
        return s.studio, False
    return trial(s.studio, list(comp.modules), FlowSettings(off=["project"])), True


@post("ops/try", needs="viewer")
def try_call(s, a, who) -> dict:
    """One /v1 call on this page's library as an access policy would make it: the status and the body a platform with
    that policy gets, the policy's caller attributes as its token would carry them. Reading and deciding only, as the
    older route allows."""
    from ontlas.rest import Rest
    from ontlas.tools import StudioTools

    path, role = str(a.get("path") or ""), str(a.get("policy") or "")
    if path not in s.TRY:
        raise ValueError("실행할 수 없는 API라 요청하지 못했습니다. 판정 · 값 검증 · 용어 해석 · 개념 조회 API를 선택해 주세요.")
    studio, draft = _tried_on(s, role)
    principal = {str(k): str(v).strip() for k, v in (a.get("principal") or {}).items() if str(v).strip()} if role else {}
    body = {k: v for k, v in (a.get("body") or {}).items() if k != "library"}  # this page is on one library already
    tools = StudioTools(studio, role=role or None, principal=principal, actor_id="page")
    code, out = Rest(tools).answer("POST", path, body)
    return {"status": code, "body": out, "policy": role, "draft": draft}


@post("ops/reindex", needs="editor")
def reindex(s, a, who) -> dict:
    """Embed every passage again with the model in use and write the stores anew: what a person asks for after a
    store was restored or when a search looks stale."""
    from ontlas.embed import EmbedError
    from ontlas.vectors import VectorError

    s._sync_space()
    sp = s.space
    with sp.lock:
        sp.model = ""  # no passage counts as embedded by this model, so each is embedded and written again
    try:
        r = sp.index()
    except (VectorError, OSError, EmbedError) as e:
        raise ValueError(f"색인 오류로 재색인하지 못했습니다. {e}") from None
    if r.get("embed_error"):
        raise ValueError(f"임베딩 모델이 응답하지 않아 재색인하지 못했습니다. {r['embed_error']} 임베딩 모델 연결을 확인해 주세요.")
    s.event("adapter", f"재색인 · 청크 {r['chunks']}개")
    return {"ok": True, "chunks": r["chunks"], "errors": r.get("errors") or {}, "space": s.space_state()}
