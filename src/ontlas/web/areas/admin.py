"""What the admin screens ask: who signs in to this server and what each role may do, how it keeps people signed in,
what it is connected to and limited by, the records it keeps, and what the open ontology is made of.

Nearly all of it is read. A user is added, changed or removed here, and the language model is tried once.
What only the server holds (its sign-ins, its sessions, its API clients, its limits) is what it was started with:
routes.SERVER, which the server fills when it starts.
"""
from __future__ import annotations

import inspect
import platform
import re
import threading
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from ontlas.web.routes import SERVER, get, post, require
from ontlas.web.team import ITERATIONS, LEVELS, NEEDS, Logins, User
from ontlas.words import fix as with_particles

STARTED = time.time()
PASSWORD_MIN = 10  # what team.Users.add asks of a password
USER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]{1,63}")
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


def _note(s, who, what: str, text: str) -> None:
    entry = {"at": datetime.now().isoformat(timespec="seconds"), "by": who.name if who is not None else s.who, "what": what, "text": text}
    journal = s.studio.changes.journal
    if journal is not None:
        journal.write("admin", entry)
    else:
        _log.append(entry)
        del _log[:-LOG_MAX]


def _notes(s) -> list[dict]:
    """What was done on these screens, oldest first: from the journal where the server keeps one, so a restart does
    not forget it."""
    journal = s.studio.changes.journal
    if journal is None:
        return list(_log)
    return [r for r in journal.read() if r.get("kind") == "admin"][-LOG_MAX:]


def _user_rows() -> list[dict]:
    users, logins = _users(), _logins()
    if users is None:
        return []
    now = time.time()
    signed: dict[str, float] = {}  # who is signed in, and when they last signed in (a token lasts ttl from then)
    with logins.lock:
        for uid, until in logins.tokens.values():
            if until > now:
                signed[uid] = max(signed.get(uid, 0.0), until - logins.ttl)
    return [{"id": u.id, "name": u.name, "roles": list(u.roles), "signed_in": u.id in signed,
             "signed_at": datetime.fromtimestamp(signed[u.id]).isoformat(timespec="seconds") if u.id in signed else ""}
            for u in users.users.values()]


def _matrix() -> list[dict]:
    return [{"label": label, "needs": NEEDS.get(route, "viewer"),
             "may": {lv: User("", "", "", [lv]).may(NEEDS.get(route, "viewer")) for lv in LEVELS}}
            for label, route in CAPABILITIES]


def _clients() -> list[dict]:
    """The platforms and agents that call /v1 with a token of their own: how many, and which of them may write. Their
    names stay with the server: on a server nobody signs in to, every visitor reads these screens."""
    rest = SERVER.get("rest")
    return [{"write": not getattr(tools, "read_only", True)} for _, tools in getattr(rest, "clients", None) or []]


def _write(users) -> None:
    """The users file as team.Users.add writes it."""
    import yaml

    if users.path is None:
        return
    body = {"users": {k: {"name": v.name, "password": v.password, "roles": v.roles} for k, v in users.users.items()}}
    users.path.write_text(yaml.safe_dump(body, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _said(roles: list[str]) -> str:
    return " · ".join(ROLE_WORD.get(r, r) for r in roles)


def _admins(users, without: str = "") -> int:
    return sum(1 for u in users.users.values() if "admin" in u.roles and u.id != without)


# ---- users ---------------------------------------------------------------------------------------------------------

@get("admin/users")
def users(s, a, who) -> dict:
    require(who, "admin")
    store = _users()
    return {"team": who is not None or store is not None, "managed": store is not None,
            "kept": bool(store is not None and store.path is not None), "users": _user_rows(),
            "me": who.id if who is not None else "", "levels": list(LEVELS), "password_min": PASSWORD_MIN,
            "matrix": _matrix()}


@post("admin/user/save", needs="admin")
def user_save(s, a, who) -> dict:
    store = _users()
    if store is None:
        raise ValueError("사용자 파일이 지정되지 않아 사용자를 저장하지 못했습니다. 서버를 --users 옵션으로 시작해 주세요.")
    uid, name = str(a.get("id") or "").strip(), " ".join(str(a.get("name") or "").split())[:80]
    roles = [str(r) for r in a.get("roles") or []]
    password, new = str(a.get("password") or ""), bool(a.get("new"))
    if not USER_ID.fullmatch(uid):
        raise ValueError("아이디 형식이 맞지 않아 저장하지 못했습니다. 영문, 숫자, . _ @ - 로 2자 이상 입력해 주세요.")
    if not roles or any(r not in LEVELS for r in roles):
        raise ValueError("역할이 없어 저장하지 못했습니다. 역할을 하나 이상 선택해 주세요.")
    roles = [lv for lv in LEVELS if lv in roles]
    if new and uid in store.users:
        raise ValueError(with_particles(f"아이디 {uid}이(가) 이미 있어 추가하지 못했습니다. 다른 아이디를 입력해 주세요."))
    if not new and uid not in store.users:
        raise ValueError(with_particles(f"사용자 {uid}을(를) 찾지 못해 저장하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    if (new or password) and len(password) < PASSWORD_MIN:
        raise ValueError(f"비밀번호가 {PASSWORD_MIN}자보다 짧아 저장하지 못했습니다. {PASSWORD_MIN}자 이상 입력해 주세요.")
    if not new and "admin" in store.users[uid].roles and "admin" not in roles and not _admins(store, without=uid):
        raise ValueError("마지막 관리자의 관리자 역할은 해제할 수 없어 저장하지 못했습니다. 다른 사용자에게 관리자 역할을 먼저 지정해 주세요.")
    if new:
        store.add(uid, password, name=name, roles=roles)
        _note(s, who, "user", f"사용자 {name or uid}({uid}) 추가 · 역할 {_said(roles)}")
    else:
        from ontlas.web.team import hash_password

        u = store.users[uid]
        if (name or uid) == u.name and roles == list(u.roles) and not password:
            raise ValueError("변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.")
        was = list(u.roles)
        u.name, u.roles = name or uid, roles
        if password:
            u.password = hash_password(password)
        _write(store)
        changed = ("" if was == roles else f" · 역할 {_said(was)} → {_said(roles)}") + (" · 비밀번호 변경" if password else "")
        _note(s, who, "user", f"사용자 {u.name}({uid}) 변경{changed}")
    return {"ok": True, "users": _user_rows()}


@post("admin/user/drop", needs="admin")
def user_drop(s, a, who) -> dict:
    store, logins = _users(), _logins()
    if store is None:
        raise ValueError("사용자 파일이 지정되지 않아 사용자를 폐기하지 못했습니다. 서버를 --users 옵션으로 시작해 주세요.")
    uid = str(a.get("id") or "")
    if uid not in store.users:
        raise ValueError(with_particles(f"사용자 {uid}을(를) 찾지 못해 폐기하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요."))
    if who is not None and who.id == uid:
        raise ValueError("본인 계정은 폐기할 수 없어 처리하지 못했습니다. 다른 관리자에게 요청해 주세요.")
    if "admin" in store.users[uid].roles and not _admins(store, without=uid):
        raise ValueError("마지막 관리자는 폐기할 수 없어 처리하지 못했습니다. 다른 사용자에게 관리자 역할을 먼저 지정해 주세요.")
    gone = store.users.pop(uid)
    _write(store)
    with logins.lock:  # whoever is signed in as that person is signed out now
        for token in [t for t, (owner, _) in logins.tokens.items() if owner == uid]:
            del logins.tokens[token]
    _note(s, who, "user", f"사용자 {gone.name}({uid}) 폐기")
    return {"ok": True, "users": _user_rows()}


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
        elif x["id"] in s._library_held:  # opened earlier in this space: its definition is still in hand
            pipelines, pid = s._library_held[x["id"]]
            studio = next(p for p in pipelines if p["id"] == pid)["studio"]
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
    page keeps of what happened in it."""
    require(who, "admin")
    st = s.studio
    rows: list[dict] = []

    def add(n: int, at: str, by: str, kind: str, text: str) -> None:
        rows.append({"at": at, "by": by, "kind": kind, "text": text, "n": n})  # n: its place among records of its kind

    for n, e in enumerate(st.changes.audit):
        word = CHANGE_EVENT.get(e.get("event"), e.get("event"))
        extra = f" · {s._element_label(e['element'])}" if e.get("element") else (f" · {e['reason']}" if e.get("reason") else "")
        add(n, e.get("at", ""), e.get("by", ""), "change", f"{word} · {s._label(e.get('module', ''))} {e.get('version', '')} · {e.get('change', '')}{extra}")
    trail = s.audit()  # newest first
    for n, e in enumerate(reversed(trail)):
        what = " · ".join(str(x) for x in (e["action"], e["target"], e["key"], e["proposal"]) if x)
        add(n, e["at"], e["actor"], "api" if e["kind"] == "agent" else "action", f"{e['event']} · {what}".strip(" ·"))
    for n, e in enumerate(_notes(s)):
        add(n, e["at"], e["by"], e["what"], e["text"])
    for n, e in enumerate(reversed(s.log)):
        add(n, e["at"], "", "note", e["text"])
    rows.sort(key=lambda r: (str(r["at"]), r["n"]), reverse=True)  # what happened in the same second keeps its order
    for r in rows:
        del r["n"]
    journal = st.changes.journal
    return {"rows": rows[:LOG_MAX], "total": len(rows), "kept": journal is not None,
            "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in ("change", "action", "api", "user", "setting", "note")}}


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
    logins = _logins()
    hours = inspect.signature(Logins.__init__).parameters["hours"].default
    tries = inspect.signature(Logins.allow_try).parameters["per_minute"].default
    return {"team": logins is not None or who is not None, "users": len(_user_rows()) if logins is not None else None,
            "session_hours": round(logins.ttl / 3600, 1) if logins is not None else hours, "password_min": PASSWORD_MIN,
            "hash": "PBKDF2-SHA256", "iterations": ITERATIONS, "tries_per_minute": tries,
            "rest": bool(getattr(s.data, "rest", False)), "clients": _clients(), "connect": bool(s.data.allow_connect),
            "model": s.llm is not None, "kept": s.studio.changes.journal is not None}


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
