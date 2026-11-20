"""What the admin screens ask: who signs in to this server and what each role may do, how it keeps people signed in,
what it is connected to and limited by, the records it keeps, and what the open ontology is made of.

Nearly all of it is read. A user is added, changed, let in, locked out or unlocked here, the policy people sign in
under is set, and the language model is tried once.
What only the server holds (its sign-ins, its sessions, its API clients, its limits) is what it was started with:
routes.SERVER, which the server fills when it starts.
"""
from __future__ import annotations

import inspect
import ipaddress
import platform
import re
import threading
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from ontlas.web.routes import SERVER, asked, get, post, require
from ontlas.web.team import EMAIL, ITERATIONS, LEVELS, NEEDS, POLICY, USER_ID, Logins, User, ip_allowed
from ontlas.words import fix as with_particles

STARTED = time.time()
LOG_MAX = 500
TEST_PER_MINUTE = 6  # tries of the language model a minute, at most
_log: list[dict] = []  # what was done on these screens, oldest first, where the server keeps no journal

# what a role may do, by the route that does it: the table is read from what the server asks of each route
CAPABILITIES = [
    ("정의 · 규칙 편집, 변경 요청 작성", "manage/edit"),
    ("자료 업로드 · 초안 생성", "upload"),
    ("초안 적용", "draft/apply"),
    ("변경 요청 승인 · 버전 배포", "change/decide"),
    ("Action 승인 · 되돌리기", "approve"),
    ("데이터 소스 연결", "connect"),
    ("저장소 · 임베딩 설정", "space/store"),
    ("검증 통과 조건 저장", "flow/save"),
    ("온톨로지 만들기 · 삭제", "library/new"),
    ("사용자 추가 · 변경", "admin/user/save"),
]  # 초기화 is not a role's: a team's shared space is never reset (team.TeamSessions.reset)
ROLE_WORD = {"viewer": "조회자", "editor": "편집자", "approver": "승인자", "admin": "관리자"}  # as the screens name the roles
# the quality targets 온톨로지 설정 sets, by the pass condition each one is: what the screen calls it
TARGETS = {("check", "min_accuracy"): "정답률", ("check", "min_grounded"): "근거 제시율", ("decide", "min_agreement"): "판정 일치율",
           ("index", "min_found"): "문서 검색 적중률", ("query", "min_agree"): "저장소 간 결과 일치율", ("bind", "max_errors"): "Binding 검사 오류"}
_targets_lock = threading.Lock()  # two admins saving at once each lay their change on what the other saved
CHANGE_EVENT = {"proposed": "변경 요청", "approved": "승인 · 배포", "rejected": "반려", "marked": "항목 검토", "commented": "댓글",
                "reopened": "작성 중으로 되돌림"}
# the screens the language model works behind: [what it does there, the screen]
MODEL_USES = [("질문 답변 · 자연어 질의", "search"), ("AI 초안 생성", "ai"), ("정책서 규칙 초안", "ruleagent"),
              ("문서 관계 추출", "evidence"), ("개념 초안", "concepts")]


def bind(**parts: Any) -> None:
    """Stand in for the server where a handler is made without it: logins, sessions, rest, limits, ask_limit."""
    SERVER.update(parts)


def _ask_per_minute() -> int | None:
    limits = SERVER.get("limits") or {}
    return limits.get("ask_per_minute") or getattr(SERVER.get("ask_limit"), "per_minute", None)


def _logins():
    return SERVER.get("logins")


_gate: list = []  # the limit these screens keep on trying the model, made on the first try


def _ask_gate():
    """What holds back tries of the language model: never more a minute than questions may be asked."""
    if SERVER.get("ask_limit") is not None:  # the server's own counter of questions, where it was lent
        return SERVER["ask_limit"]
    if not _gate:
        from ontlas.web.server import RateLimit

        _gate.append(RateLimit(min(TEST_PER_MINUTE, _ask_per_minute() or TEST_PER_MINUTE)))
    return _gate[0]


def _users():
    logins = _logins()
    return logins.users if logins is not None else None


SERVERS = ("user", "login")  # what is the server's, not one ontology's: who signs in to it, and how


def _server_journal(s):
    """Where what is the server's is kept: the first ontology's journal, whichever one the person looks at."""
    return (s.team.shared if s.team is not None else s).studio.changes.journal


def _note(s, who, what: str, text: str, *, by: str | None = None, server: bool = False) -> None:
    """One line of the audit log, with the address the request came from where it is known. `server` keeps a kind
    that is otherwise the open ontology's (a setting) with what is the server's."""
    entry = {"at": datetime.now().isoformat(timespec="seconds"), "by": by if by is not None else who.name if who is not None else s.who,
             "what": what, "text": text, "ip": asked().get("ip", "")}
    if server:
        entry["server"] = True
    journal = _server_journal(s) if what in SERVERS or server else s.studio.changes.journal
    if journal is not None:
        journal.write("admin", entry)
    else:
        _log.append(entry)
        del _log[:-LOG_MAX]


def _notes(s) -> list[dict]:
    """What was done on these screens, oldest first: from the journal where the server keeps one, so a restart does
    not forget it. What was set in the open ontology is read from its own records; what is the server's is read
    from the first ontology's, so it is there whichever ontology the person looks at."""
    own, server = s.studio.changes.journal, _server_journal(s)
    rows = [r for r in own.read() if r.get("kind") == "admin"] if own is not None else list(_log)
    if server is not None and server is not own:
        rows = [r for r in rows if r.get("what") not in SERVERS and not r.get("server")]
        rows += [r for r in server.read() if r.get("kind") == "admin" and (r.get("what") in SERVERS or r.get("server"))]
        rows.sort(key=lambda r: str(r.get("at") or ""))
    return rows[-LOG_MAX:]


def _user_rows() -> list[dict]:
    users, logins = _users(), _logins()
    if users is None:
        return []
    now, seen = logins.clock(), logins.status()  # seen: who is signed in, when they last signed in and asked anything
    rows = []
    for u in users.users.values():
        at = seen.get(u.id) or {}
        locked = u.locked(now)
        rows.append({"id": u.id, "name": u.name, "roles": list(u.roles), "email": u.email, "employee_no": u.employee_no,
                     "note": u.note, "state": u.state, "locked": locked, "locked_until": u.locked_until if locked else "",
                     "two_factor": bool(u.totp), "must_change": u.must_change, "signed_in": bool(at.get("live")),
                     "signed_at": at.get("at", ""), "seen": at.get("seen", "")})
    return rows


def _user_counts(rows: list[dict]) -> dict:
    return {"users": len(rows), "admins": sum(r["state"] == "active" and "admin" in r["roles"] for r in rows),
            "locked": sum(r["locked"] for r in rows), "disabled": sum(r["state"] == "disabled" for r in rows),
            "pending": sum(r["state"] == "pending" for r in rows), "two_factor": sum(r["two_factor"] for r in rows)}


def _answer() -> dict:
    """What a change to the users answers: the list and its counts, as they stand now."""
    rows = _user_rows()
    return {"ok": True, "users": rows, "counts": _user_counts(rows)}


def _matrix() -> list[dict]:
    return [{"label": label, "needs": NEEDS.get(route, "viewer"),
             "may": {lv: User("", "", "", [lv]).may(NEEDS.get(route, "viewer")) for lv in LEVELS}}
            for label, route in CAPABILITIES]


def _clients() -> list[dict]:
    """The platforms and agents that call /v1 with a token of their own: how many, and which of them may write. Their
    names stay with the server: on a server nobody signs in to, every visitor reads these screens."""
    rest = SERVER.get("rest")
    return [{"write": not getattr(tools, "read_only", True)} for _, tools in getattr(rest, "clients", None) or []]


def _said(roles: list[str]) -> str:
    return " · ".join(ROLE_WORD.get(r, r) for r in roles)


STATE_WORD = {"active": "사용", "disabled": "비활성", "pending": "승인 대기"}  # as the user screens name a state


def _policy() -> dict:
    store = _users()
    policy = store.policy if store is not None else POLICY
    return {**policy, "allow_ip": list(policy["allow_ip"])}


def _store(done: str):
    """The users file a change is written to; `done` is what was not done without one ("사용자를 저장하지")."""
    store = _users()
    if store is None:
        raise ValueError(f"사용자 파일이 지정되지 않아 {done} 못했습니다. 서버를 --users 옵션으로 시작해 주세요.")
    return store


def _person(store, a: dict, done: str):
    uid = str(a.get("id") or "")
    if uid not in store.users:
        raise ValueError(with_particles(f"사용자 {uid}을(를) 찾지 못해 {done} 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    return store.users[uid]


def _roles(a: dict) -> list[str]:
    roles = [str(r) for r in a.get("roles") or []]
    if not roles or any(r not in LEVELS for r in roles):
        raise ValueError("역할이 없어 저장하지 못했습니다. 역할을 하나 이상 선택해 주세요.")
    return [lv for lv in LEVELS if lv in roles]


# ---- users ---------------------------------------------------------------------------------------------------------

@get("admin/users")
def users(s, a, who) -> dict:
    require(who, "admin")
    store, policy = _users(), _policy()
    rows = _user_rows()
    return {"team": who is not None or store is not None, "managed": store is not None,
            "kept": bool(store is not None and store.path is not None), "users": rows, "counts": _user_counts(rows),
            "me": who.id if who is not None else "", "levels": list(LEVELS), "password_min": policy["password_min"],
            "policy": policy, "matrix": _matrix()}


@post("admin/user/save", needs="admin")
def user_save(s, a, who) -> dict:
    store, logins = _store("사용자를 저장하지"), _logins()
    uid, name = str(a.get("id") or "").strip(), " ".join(str(a.get("name") or "").split())[:80]
    password, new = str(a.get("password") or ""), bool(a.get("new"))
    email, number = str(a.get("email") or "").strip()[:120], str(a.get("employee_no") or "").strip()[:40]
    memo, state = str(a.get("note") or "").strip()[:500], str(a.get("state") or "")
    temporary = bool(a.get("must_change", True))  # a password given here is changed by its owner at the next sign-in
    least = store.policy["password_min"]
    if not USER_ID.fullmatch(uid):
        raise ValueError("아이디 형식이 맞지 않아 저장하지 못했습니다. 영문, 숫자, . _ @ - 로 2자 이상 입력해 주세요.")
    roles = _roles(a)
    if state and state not in ("active", "disabled"):
        raise ValueError("상태 값이 맞지 않아 저장하지 못했습니다. 사용 또는 비활성 중에서 선택해 주세요.")
    if new and uid in store.users:
        raise ValueError(with_particles(f"아이디 {uid}이(가) 이미 있어 추가하지 못했습니다. 다른 아이디를 입력해 주세요."))
    if not new and uid not in store.users:
        raise ValueError(with_particles(f"사용자 {uid}을(를) 찾지 못해 저장하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    if (new or password) and len(password) < least:
        raise ValueError(f"비밀번호가 {least}자보다 짧아 저장하지 못했습니다. {least}자 이상 입력해 주세요.")
    if email and not EMAIL.fullmatch(email):
        raise ValueError("이메일 형식이 맞지 않아 저장하지 못했습니다. name@example.com 형식으로 입력해 주세요.")
    if store.email_taken(email, but=uid):
        raise ValueError(with_particles(f"이메일 {email}이(가) 이미 등록되어 저장하지 못했습니다. 다른 이메일을 입력해 주세요."))
    if not new and "admin" in store.users[uid].roles and store.users[uid].state == "active" and not store.admins(without=uid):
        if "admin" not in roles:
            raise ValueError("마지막 관리자의 관리자 역할은 해제할 수 없어 저장하지 못했습니다. 다른 사용자에게 관리자 역할을 먼저 지정해 주세요.")
        if state == "disabled":
            raise ValueError("마지막 관리자는 비활성으로 바꿀 수 없어 저장하지 못했습니다. 다른 사용자에게 관리자 역할을 먼저 지정해 주세요.")
    if new:
        with store.lock:
            u = store.users[uid] = User(uid, name or uid, "", roles, email=email, employee_no=number, note=memo, state=state or "active")
            store.set_password(u, password, must_change=temporary)
            store.save()
        _note(s, who, "user", f"사용자 {u.name}({uid}) 추가 · 역할 {_said(roles)}")
        return _answer()
    u = store.users[uid]
    state = state or u.state
    changed = [word for word, now, was in (("이름 변경", name or uid, u.name), ("이메일 변경", email, u.email),
                                           ("사번 변경", number, u.employee_no), ("메모 변경", memo, u.note)) if now != was]
    if roles != list(u.roles):
        changed.append(f"역할 {_said(u.roles)} → {_said(roles)}")
    if state != u.state:
        changed.append(f"상태 {STATE_WORD[u.state]} → {STATE_WORD[state]}")
    if not changed and not password:
        raise ValueError("변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.")
    with store.lock:
        u.name, u.roles, u.email, u.employee_no, u.note, u.state = name or uid, roles, email, number, memo, state
        if password:
            store.set_password(u, password, must_change=temporary)
        store.save()
    if password or state == "disabled":  # a password reset or an account stopped: whoever is signed in as them is not
        logins.end(uid)
    if changed:
        _note(s, who, "user", f"사용자 {u.name}({uid}) 변경 · " + " · ".join(changed))
    if password:
        _note(s, who, "login", f"{'임시 비밀번호 발급' if temporary else '비밀번호 변경'} · 사용자 {u.name}({uid})")
    return _answer()


@post("admin/user/drop", needs="admin")
def user_drop(s, a, who) -> dict:
    """An account no longer used: kept on the list as disabled, never let in, and signed out now. Saving it as active
    lets it in again."""
    store = _store("사용자를 폐기하지")
    u = _person(store, a, "폐기하지")
    if who is not None and who.id == u.id:
        raise ValueError("본인 계정은 폐기할 수 없어 처리하지 못했습니다. 다른 관리자에게 요청해 주세요.")
    if u.state == "disabled":
        raise ValueError(with_particles(f"사용자 {u.id}은(는) 이미 폐기되어 처리하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    if "admin" in u.roles and u.state == "active" and not store.admins(without=u.id):
        raise ValueError("마지막 관리자는 폐기할 수 없어 처리하지 못했습니다. 다른 사용자에게 관리자 역할을 먼저 지정해 주세요.")
    with store.lock:
        u.state = "disabled"
        store.save()
    _logins().end(u.id)
    _note(s, who, "user", f"사용자 {u.name}({u.id}) 폐기")
    return _answer()


@post("admin/user/unlock", needs="admin")
def user_unlock(s, a, who) -> dict:
    store = _store("잠금 해제하지")
    u = _person(store, a, "잠금 해제하지")
    if not u.locked(_logins().clock()) and not u.failures:
        raise ValueError(with_particles(f"사용자 {u.id}은(는) 잠겨 있지 않아 잠금 해제하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    with store.lock:
        u.failures, u.locked_until = 0, ""
        store.save()
    _note(s, who, "login", f"잠금 해제 · 사용자 {u.name}({u.id})")
    return _answer()


@post("admin/user/2fa/reset", needs="admin")
def user_2fa_reset(s, a, who) -> dict:
    """A lost authenticator: the person signs in with a password alone again, or sets up a new one where the policy
    asks for it."""
    store = _store("2단계 인증을 초기화하지")
    u = _person(store, a, "초기화하지")
    if not u.totp:
        raise ValueError(with_particles(f"사용자 {u.id}은(는) 2단계 인증을 쓰지 않아 초기화하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    with store.lock:
        u.totp = ""
        store.save()
    _logins().used.pop(u.id, None)
    _note(s, who, "login", f"2단계 인증 초기화 · 사용자 {u.name}({u.id})")
    return _answer()


@post("admin/user/approve", needs="admin")
def user_approve(s, a, who) -> dict:
    """One who asked to join, let in with the roles chosen (viewer where none is)."""
    store = _store("가입을 승인하지")
    u = _person(store, a, "승인하지")
    if u.state != "pending":
        raise ValueError(with_particles(f"사용자 {u.id}은(는) 승인 대기 상태가 아니어서 승인하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    roles = _roles(a) if a.get("roles") else ["viewer"]
    with store.lock:
        u.state, u.roles = "active", roles
        store.save()
    _note(s, who, "user", f"가입 승인 · 사용자 {u.name}({u.id}) · 역할 {_said(roles)}")
    return _answer()


@post("admin/user/reject", needs="admin")
def user_reject(s, a, who) -> dict:
    """One who asked to join, turned away: taken off the list, so the id and email may be asked for again."""
    store = _store("가입을 거절하지")
    u = _person(store, a, "거절하지")
    if u.state != "pending":
        raise ValueError(with_particles(f"사용자 {u.id}은(는) 승인 대기 상태가 아니어서 거절하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    with store.lock:
        store.users.pop(u.id, None)
        store.save()
    _note(s, who, "user", f"가입 거절 · 사용자 {u.name}({u.id})")
    return _answer()


# ---- the open ontology: what it is called, how it names things, who answers for what ----------------------------------

def _style(name: str) -> str:
    name = name.split(":", 1)[-1]
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
        return "PascalCase"
    if re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)+", name):
        return "snake_case"
    if re.fullmatch(r"[a-z][a-z0-9]*([A-Z][a-z0-9]*)+", name):
        return "camelCase"
    if re.fullmatch(r"[a-z][a-z0-9]*", name):
        return "소문자"
    return "기타"


def _naming(names: list[str]) -> dict:
    """How a kind of name is written, counted over the names there are: the commonest way and how many follow it."""
    tally: dict[str, int] = {}
    for n in names:
        tally[_style(n)] = tally.get(_style(n), 0) + 1
    # one lower-case word is written the same in snake_case and camelCase: it goes with whichever the rest use
    lower = tally.pop("소문자", 0)
    if not tally:
        return {"style": "소문자" if lower else "", "follow": lower, "total": len(names)}
    best = max(tally, key=lambda k: tally[k])
    return {"style": best, "follow": tally[best] + (lower if best != "PascalCase" else 0), "total": len(names)}


def _vocabularies(o) -> list[dict]:
    """The standard vocabularies the definition borrows names from, read from what its elements are aligned to."""
    found: dict[str, dict] = {}

    def add(kind: str, label: str, name: str, iris: list[str]) -> None:
        for iri in iris or []:
            u = urlparse(str(iri))
            if u.scheme in ("http", "https") and u.netloc:
                key, term = u.netloc.removeprefix("www."), (u.fragment or u.path.rsplit("/", 1)[-1])
            elif ":" in str(iri):
                key, term = str(iri).split(":", 1)
            else:
                continue
            v = found.setdefault(key, {"name": key, "terms": []})
            v["terms"].append({"kind": kind, "label": label, "element": name, "term": term, "iri": str(iri)})

    for ar in o.areas.values():
        add("Object", ar.label or ar.name, ar.name, ar.aligned)
    for t in o.objects.values():
        add("Entity", t.label or t.name, t.name, t.aligned)
        for p in t.properties.values():
            add("Property", f"{t.label or t.name} · {p.label or p.name}", f"{t.name}.{p.name}", p.aligned)
    for lk in o.links.values():
        add("Relation", lk.label or lk.name, lk.name, lk.aligned)
    out = sorted(found.values(), key=lambda v: -len(v["terms"]))
    for v in out:
        v["counts"] = {k: sum(1 for t in v["terms"] if t["kind"] == k) for k in ("Object", "Entity", "Property", "Relation")}
    return out


@get("admin/settings")
def settings(s, a, who) -> dict:
    require(who, "admin")
    st, o = s.studio, s.studio.onto
    lib = next((x for x in s.libraries if x["id"] == s.library_id), None) or {}
    comp = st.composition
    version = s._space_version() if comp is not None else {"number": 1, "label": "버전 1", "modules": []}
    props = [p.name for t in o.objects.values() for p in t.properties.values()]
    aligned = sum(1 for t in o.objects.values() if t.aligned) + sum(1 for ar in o.areas.values() if ar.aligned)
    return {"id": s.library_id, "label": lib.get("label") or o.label or o.name, "name": o.name, "namespace": o.namespace,
            "description": next((m.description for m in (comp.modules if comp else []) if m.kind == "domain" and m.description), ""),
            "made": bool(lib.get("made")), "version": {"number": version["number"], "label": version["label"]},
            "modules": [{"label": m["label"], "kind_label": m["kind_label"], "version": m["version"]} for m in version["modules"]],
            "packs": _packs(st),
            "naming": {"entity": _naming(list(o.objects)), "property": _naming(props), "link": _naming(list(o.links))},
            "vocabularies": [{"name": v["name"], "terms": len(v["terms"])} for v in _vocabularies(o)],
            "aligned": aligned, "defined": len(o.objects) + len(o.areas),
            "approval": {"self_approve": bool(st.changes.self_approve), "apply_needs": NEEDS.get("draft/apply", "viewer"),
                         "decide_needs": NEEDS.get("change/decide", "viewer")},
            "model": s.llm is not None, "model_state": _model_state(s),
            "kept": st.changes.journal is not None, "writes_folder": st.changes.store is not None}


def _packs(studio) -> list[str]:
    """The domain packs an ontology applies, named as 온톨로지 만들기 names them: its domain modules at their versions."""
    comp = studio.composition
    return [f"{m.label or m.name} {m.version}" for m in comp.modules if m.kind == "domain"] if comp is not None else []


def _model_state(s) -> str:
    """How the language model stands, by how its last call went, as the sidebar reads it (no call is made here)."""
    last = getattr(s, "_llm_last", None)
    return "off" if s.llm is None else "idle" if last is None else "ok" if last.get("ok") else "bad"


def _target_word(cond: str, v) -> str:
    if v is None:
        return "조건 없음"
    return f"{round(v * 100, 1):g}%" if cond.startswith("min_") else f"{int(v)}건"


@post("admin/targets", needs="admin")
def targets(s, a, who) -> dict:
    """The quality targets an admin changed on 온톨로지 설정, laid on the pass conditions as they stand now: a target
    another admin saved in the meantime stays, and one both changed is not overwritten but said back with its value."""
    from ontlas.review import FlowSettings

    asked = []
    for c in a.get("changes") or []:
        c = c if isinstance(c, dict) else {}
        stage, cond = str(c.get("stage") or ""), str(c.get("condition") or "")
        word, value = TARGETS.get((stage, cond)), c.get("value")
        if word is None:
            raise ValueError("알 수 없는 품질 목표가 있어 저장하지 못했습니다. 화면을 새로 고친 뒤 다시 시도해 주세요.")
        share = cond.startswith("min_")
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                  or not (0 <= value <= 1 if share else value >= 0 and float(value).is_integer())):
            raise ValueError(f"{word} 값의 형식이 맞지 않아 저장하지 못했습니다. "
                             f"{'0에서 100 사이의 숫자' if share else '0 이상의 정수'}를 입력해 주세요.")
        if value != c.get("was"):
            asked.append((stage, cond, word, value if value is None or share else int(value), c.get("was")))
    with _targets_lock:
        now = s.studio.own_flow.to_dict()
        gates = now.setdefault("gates", {})
        for stage, cond, word, _, was in asked:
            current = (gates.get(stage) or {}).get(cond)
            if current != was:
                return {"ok": False, "settings": now, "error": with_particles(f"다른 관리자가 {word}을(를) 먼저 {_target_word(cond, current)}(으)로 "
                                                                              "바꿔 저장하지 못했습니다. 바뀐 값을 확인한 뒤 다시 입력해 주세요.")}
        said = []
        for stage, cond, word, value, was in asked:
            held = gates.setdefault(stage, {})  # a stage left with no condition stays, empty: left out, its default comes back
            if value is None:
                held.pop(cond, None)
            else:
                held[cond] = value
            said.append(f"{word} {_target_word(cond, was)} → {_target_word(cond, value)}")
        if not said:
            return {"ok": True, "settings": now}
        kept = FlowSettings.from_dict(now).to_dict()
        s.studio.settings["flow"] = kept
        s._keep_flow()
    text = "품질 목표 변경 · " + " · ".join(said)
    _note(s, who, "setting", text)
    s.event("flow", text)
    return {"ok": True, "settings": kept}


@get("admin/members")
def members(s, a, who) -> dict:
    require(who, "admin")
    o = s.studio.onto
    store = _users()
    areas = [{"name": ar.name, "label": ar.label or ar.name, "owner": ar.owner,
              "entities": sum(1 for t in o.objects.values() if t.area == ar.name)} for ar in o.areas.values()]
    return {"team": who is not None or store is not None, "managed": store is not None, "users": _user_rows(),
            "me": who.id if who is not None else "", "levels": list(LEVELS), "matrix": _matrix(), "areas": areas,
            "clients": _clients(), "rest": bool(getattr(s.data, "rest", False))}


@get("admin/vocab")
def vocab(s, a, who) -> dict:
    require(who, "admin")
    o = s.studio.onto
    props = [p.name for t in o.objects.values() for p in t.properties.values()]
    return {"namespace": o.namespace, "vocabularies": _vocabularies(o),
            "naming": {"entity": _naming(list(o.objects)), "property": _naming(props), "link": _naming(list(o.links))},
            "defined": {"Object": len(o.areas), "Entity": len(o.objects), "Property": len(props), "Relation": len(o.links)}}


# ---- the whole server: its ontologies, what waits, what was done, what it runs on --------------------------------------

def _counts(studio) -> dict:
    o, comp = studio.onto, studio.composition
    return {"objects": len(o.areas), "entities": len(o.objects),
            "rules": sum(len(d.rules) for d in o.decisions.values()) + (len(comp.cards) if comp is not None else 0),
            "pending": sum(c.status == "pending" for c in studio.changes.requests.values())}


@get("admin/overview")
def overview(s, a, who) -> dict:
    require(who, "admin")
    rows = []
    for x in s.libraries:
        row = {"id": x["id"], "label": x["label"], "modules": x.get("modules", 0), "source": x.get("source", ""),
               "made": bool(x.get("made")), "open": x["id"] == s.library_id, "counts": None, "version": "", "levels": None,
               "accuracy": None, "packs": None}
        if row["open"]:
            row["counts"], row["packs"] = _counts(s.studio), _packs(s.studio)
            if s.studio.composition is not None:
                row["version"] = s._space_version()["label"]
            levels = s._entity_levels()
            row["levels"] = [sum(1 for v in levels.values() if v == i) for i in range(4)]
            # the share of questions the last 검증 answered right, while the definition it was measured on is this one
            got = (s._measured.get("check") or {}) if s._measured_of is s.studio.onto else {}
            row["accuracy"] = got.get("accuracy")
        elif (studio := s.library_studio(x["id"])) is not None:  # opened earlier in this space, or open in the team: its definition is in hand
            row["counts"], row["packs"] = _counts(studio), _packs(studio)
        rows.append(row)
    box = s.inbox()
    todo = [{"kind": i["kind"], "title": i["title"], "detail": i.get("detail") or i.get("change") or "", "by": i.get("by") or "",
             "at": i.get("at") or ""} for i in box["items"]]
    recent = sorted([{"at": e["at"], "text": e["text"], "by": ""} for e in s.log]
                    + [{"at": e["at"], "text": e["text"], "by": e["by"]} for e in _notes(s)], key=lambda e: e["at"], reverse=True)[:8]
    unowned = [ar.label or ar.name for ar in s.studio.onto.areas.values() if not ar.owner]  # the open ontology's Objects no one answers for
    return {"libraries": rows, "todo": todo, "recent": recent, "unowned": unowned, "users": len(_user_rows()) if _users() is not None else None,
            "clients": len(_clients()) if SERVER.get("rest") is not None else None, "rest": bool(getattr(s.data, "rest", False)),
            "team": who is not None or _users() is not None}


@get("admin/audit")
def audit(s, a, who) -> dict:
    """Everything this ontology's records hold, newest first: change requests and their decisions, requests for
    actions and what was decided on them, calls from outside, what was done on the admin screens, and the notes the
    page keeps of what happened in it. What was done to the server's users is among them whichever ontology is open."""
    require(who, "admin")
    st = s.studio
    rows: list[dict] = []

    def add(n: int, at: str, by: str, kind: str, text: str, ip: str = "") -> None:
        rows.append({"at": at, "by": by, "kind": kind, "text": text, "ip": ip, "n": n})  # n: its place among records of its kind

    for n, e in enumerate(st.changes.audit):
        word = CHANGE_EVENT.get(e.get("event"), e.get("event"))
        extra = f" · {s._element_label(e['element'])}" if e.get("element") else (f" · {e['reason']}" if e.get("reason") else "")
        add(n, e.get("at", ""), e.get("by", ""), "change", f"{word} · {s._label(e.get('module', ''))} {e.get('version', '')} · {e.get('change', '')}{extra}")
    trail = s.audit()  # newest first
    for n, e in enumerate(reversed(trail)):
        what = " · ".join(str(x) for x in (e["action"], e["target"], e["key"], e["proposal"]) if x)
        add(n, e["at"], e["actor"], "api" if e["kind"] == "agent" else "action", f"{e['event']} · {what}".strip(" ·"))
    for n, e in enumerate(_notes(s)):
        add(n, e["at"], e["by"], e["what"], e["text"], e.get("ip") or "")
    for n, e in enumerate(reversed(s.log)):
        add(n, e["at"], "", "note", e["text"])
    rows.sort(key=lambda r: (str(r["at"]), r["n"]), reverse=True)  # what happened in the same second keeps its order
    for r in rows:
        del r["n"]
    journal = st.changes.journal
    return {"rows": rows[:LOG_MAX], "total": len(rows), "kept": journal is not None,
            "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in ("change", "action", "api", "login", "user", "setting", "note")}}


@get("admin/version")
def version(s, a, who) -> dict:
    """The version installed, for the foot of the admin menu."""
    require(who, "admin")
    from ontlas import __version__

    return {"version": __version__}


@get("admin/system")
def system(s, a, who) -> dict:
    require(who, "admin")
    from ontlas import __version__

    sessions, logins = SERVER.get("sessions"), _logins()
    d, st = s.data, s.studio
    con = s.connections()
    journal = st.changes.journal
    host = who is not None  # what the machine runs is said to an admin who signed in, not to a visitor
    python = platform.python_version() if host else ".".join(platform.python_version_tuple()[:2])
    parts = [{"name": "애플리케이션 서버", "detail": f"Python {python}" + (f" · {platform.system()} {platform.release()}" if host else ""), "state": "ok"}]
    for b in con["stores"]:
        parts.append({"name": "소스 DB" if b["source"] else "그래프 저장소", "detail": f"{b['kind']} · {b['language']}" + (f" · 응답 {b['ms']}ms" if b["state"] == "ok" else ""),
                      "state": b["state"], "error": b["error"]})
    for v in con["vectors"]:
        parts.append({"name": "벡터 저장소", "detail": v["kind"], "state": v["state"], "error": v["error"]})
    emb = con["embedder"]
    parts.append({"name": "임베딩 모델", "detail": f"{emb['kind']} · {emb['dim']}차원" + (f" · {emb['name']}" if emb.get("name") else ""), "state": "ok"})
    llm = con["llm"]
    parts.append({"name": "언어 모델", "detail": ("OpenAI 호환 API" if llm["kind"] == "openai" else llm["kind"] or "미연결")
                  + (f" · 마지막 호출 {llm['at'].replace('T', ' ')}" if llm["at"] else ""), "state": llm["state"], "error": llm["error"]})
    parts.append({"name": "외부 API", "detail": "REST /v1 · MCP" if con["rest"] else "사용 안 함", "state": "ok" if con["rest"] else "off"})
    held = None
    if sessions is not None and not getattr(sessions, "team", False):
        with sessions.lock:
            held = {"count": len(sessions.items), "limit": sessions.limit, "idle_minutes": round(sessions.idle / 60)}
    return {"version": __version__, "python": python, "platform": f"{platform.system()} {platform.release()}" if host else "",
            "started": datetime.fromtimestamp(STARTED).isoformat(timespec="seconds"),
            "uptime_minutes": round((time.time() - STARTED) / 60), "team": logins is not None or who is not None, "parts": parts,
            "sessions": held, "ask_per_minute": _ask_per_minute(),
            "limits": {"file_kb": d.file_bytes >> 10, "files": d.files, "total_mb": round(d.total_bytes / (1 << 20), 1), "rows": d.rows,
                       "columns": d.columns, "connect": bool(d.allow_connect)},
            "keeps": {"journal": journal is not None, "journal_file": journal.path.name if journal is not None else "",
                      "journal_kb": round(journal.path.stat().st_size / 1024) if journal is not None and journal.path.is_file() else 0,
                      "library_write": st.changes.store is not None, "repositories": bool(s.repositories.persistent)},
            "usage": {"files": len(s.sizes), "mb": round(sum(s.sizes.values()) / (1 << 20), 2)},  # what this space has taken in
            "libraries": len(s.libraries), "clients": _clients()}


@get("admin/security")
def security(s, a, who) -> dict:
    require(who, "admin")
    logins, store, policy = _logins(), _users(), _policy()
    tries = inspect.signature(Logins.allow_try).parameters["per_minute"].default
    return {"team": logins is not None or who is not None, "users": len(_user_rows()) if logins is not None else None,
            "session_hours": policy["session_hours"], "password_min": policy["password_min"],
            "hash": "PBKDF2-SHA256", "iterations": ITERATIONS, "tries_per_minute": tries,
            "rest": bool(getattr(s.data, "rest", False)), "clients": _clients(), "connect": bool(s.data.allow_connect),
            "model": s.llm is not None, "kept": s.studio.changes.journal is not None,
            "policy": policy, "editable": bool(store is not None and store.path is not None), "client_ip": asked().get("ip", "")}


# what each number of the policy may be, and how the audit log says it: (least, most, name, unit)
POLICY_RANGES = {"session_hours": (1, 168, "세션 만료", "시간"), "keep_days": (0, 90, "로그인 유지", "일"),
                 "password_min": (8, 64, "비밀번호 최소 길이", "자"), "lock_after": (3, 20, "잠금 기준 실패 횟수", "회"),
                 "lock_minutes": (1, 1440, "잠금 시간", "분")}
POLICY_SWITCHES = {"two_factor": "2단계 인증 필수", "signup": "회원가입 받기"}


def _policy_word(key: str, v) -> str:
    if key in POLICY_SWITCHES or (key == "keep_days" and not v):
        return "사용" if v else "사용 안 함"
    if key == "allow_ip":
        return ", ".join(v) if v else "제한 없음"
    return f"{v}{POLICY_RANGES[key][3]}"


@post("admin/security/save", needs="admin")
def security_save(s, a, who) -> dict:
    """The policy people sign in under, in force from the next request. The address it is saved from stays allowed,
    so an admin cannot shut themselves out."""
    store = _users()
    if store is None or store.path is None:
        raise ValueError("사용자 파일이 서버에 없어 보안 정책을 저장하지 못했습니다. 서버를 --users 옵션으로 시작해 주세요.")
    given = a.get("policy") if isinstance(a.get("policy"), dict) else {}
    if set(given) - set(POLICY):
        raise ValueError("알 수 없는 보안 정책 항목이 있어 저장하지 못했습니다. 화면을 새로 고친 뒤 다시 시도해 주세요.")
    was = _policy()
    policy = {**was, **given}
    for key, (least, most, word, _) in POLICY_RANGES.items():
        v = policy[key]
        if isinstance(v, float) and v.is_integer():
            v = policy[key] = int(v)
        if isinstance(v, bool) or not isinstance(v, int) or not least <= v <= most:
            raise ValueError(f"{word} 값이 {least}~{most} 범위를 벗어나 저장하지 못했습니다. {least}에서 {most} 사이의 정수를 입력해 주세요.")
    for key, word in POLICY_SWITCHES.items():
        if not isinstance(policy[key], bool):
            raise ValueError(f"{word} 값의 형식이 맞지 않아 저장하지 못했습니다. 화면을 새로 고친 뒤 다시 시도해 주세요.")
    if not isinstance(policy["allow_ip"], list):
        raise ValueError("허용 IP 대역의 형식이 맞지 않아 저장하지 못했습니다. 한 줄에 대역 하나씩 입력해 주세요.")
    nets: list[str] = []
    for x in (str(n).strip() for n in policy["allow_ip"]):
        try:
            net = str(ipaddress.ip_network(x, strict=False)) if x else ""
        except ValueError:
            raise ValueError(f"허용 IP 대역 {x[:60]}의 형식이 맞지 않아 저장하지 못했습니다. 10.0.0.0/8 또는 10.0.0.5 형식으로 입력해 주세요.") from None
        if net and net not in nets:
            nets.append(net)
    policy["allow_ip"] = nets
    ip = asked().get("ip", "")
    if not ip_allowed(ip, nets):
        raise ValueError(with_particles(f"지금 접속한 IP {ip or '(알 수 없음)'}이(가) 허용 IP 대역에 없어 저장하지 못했습니다. "
                                        "이 IP가 포함된 대역을 추가해 주세요."))
    words = {**{k: r[2] for k, r in POLICY_RANGES.items()}, **POLICY_SWITCHES, "allow_ip": "허용 IP 대역"}
    said = [f"{words[k]} {_policy_word(k, was[k])} → {_policy_word(k, policy[k])}" for k in POLICY if policy[k] != was[k]]
    if not said:
        raise ValueError("변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.")
    with store.lock:
        store.policy = policy
        store.save()
    _note(s, who, "setting", "보안 정책 변경 · " + " · ".join(said), server=True)
    return {"ok": True, "policy": _policy()}


@get("admin/ai")
def ai(s, a, who) -> dict:
    require(who, "admin")
    con = s.connections()
    model = str(getattr(s.llm, "model", "") or "") if s.llm is not None else ""  # the model's name, to an admin only
    return {"llm": {**con["llm"], "model": model}, "embedder": con["embedder"], "ask_per_minute": _ask_per_minute(),
            "uses": [{"label": label, "screen": screen} for label, screen in MODEL_USES]}


@post("admin/ai/test", needs="admin")
def ai_test(s, a, who) -> dict:
    """One short call to the language model, timed: it answers or it says why not."""
    if s.llm is None:
        raise ValueError("언어 모델이 연결되어 있지 않아 테스트하지 못했습니다. 서버를 --llm-url 옵션으로 시작해 주세요.")
    if not _ask_gate().allow():
        raise ValueError("분당 질문 한도를 넘어 테스트하지 못했습니다. 1분 뒤 다시 시도해 주세요.")
    llm, _ = s._budgeted()
    started = time.perf_counter()
    try:
        answer = llm("Answer with the single word: ok", "ok?")
    except Exception:  # what went wrong is kept by the session as the model's last call
        return {"ok": False, "ms": round((time.perf_counter() - started) * 1000), **s.connections()["llm"]}
    return {"ok": True, "ms": round((time.perf_counter() - started) * 1000), "answered": bool(str(answer).strip()), **s.connections()["llm"]}
