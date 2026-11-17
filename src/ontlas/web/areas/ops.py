"""운영 › 저장소 · 엔진, 연동 · API, 접근 정책: what those screens ask that the older routes do not answer.

- who may call /v1 on this server (the names the server was started with, never a token), what each may do, and what the
  audit trail says each has asked;
- one /v1 call tried from the page as a given access policy would make it;
- every passage embedded again.
"""
from __future__ import annotations

from typing import Any

from ontlas.web.routes import get, post

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


@get("ops/targets")
def targets(s, a, who) -> dict:
    """The callers of /v1 on this server: each with its policy, whether it may request actions, and what the audit
    trail holds of it (decisions, answers, functions, action requests: the calls that are recorded)."""
    rest = _REST["rest"]
    on = bool(getattr(s.data, "rest", False))
    month = s.studio.now().strftime("%Y-%m")
    rows = [_target(rest, tools, month) for _, tools in rest.clients] if rest is not None else []
    roles = set(s.studio.onto.roles)
    for r in rows:
        r["policy_known"] = not r["policy"] or r["policy"] in roles
    return {"rest": on, "listed": rest is not None, "targets": rows, "month": month,
            "calls_month": sum(r["month"] for r in rows), "calls": sum(r["calls"] for r in rows)}


@post("ops/try", needs="viewer")
def try_call(s, a, who) -> dict:
    """One /v1 call on this page's library as an access policy would make it: the status and the body a platform with
    that policy gets. Reading and deciding only, as the older route allows."""
    from ontlas.rest import Rest
    from ontlas.tools import StudioTools

    path, role = str(a.get("path") or ""), str(a.get("policy") or "")
    if path not in s.TRY:
        raise ValueError("실행할 수 없는 API라 요청하지 못했습니다. 판정 · 값 검증 · 용어 해석 · 개념 조회 API를 선택해 주세요.")
    if role and role not in s.studio.onto.roles:
        raise LookupError(f"접근 정책 {role}")
    body = {k: v for k, v in (a.get("body") or {}).items() if k != "library"}  # this page is on one library already
    code, out = Rest(StudioTools(s.studio, role=role or None, actor_id="page")).answer("POST", path, body)
    return {"status": code, "body": out, "policy": role}


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
