"""What the screens outside an ontology ask: the ontologies there are to choose from with what each holds, one made
from another, and what waits on the person, what happened and what was settled.

An ontology is a library the deployment offers (a studio file) or one made on the page. The one open and the ones this
session opened before (in a team, the ones anyone has open) are read from their studios; one not opened yet is read
from its files alone, without opening what it reads from, so the list never waits on a source.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ontlas.web import routes
from ontlas.web.areas.admin import _note
from ontlas.web.routes import get, post
from ontlas.web.team import EMAIL, HISTORY, POLICY, check_password
from ontlas.words import fix as with_particles

ROWS_MAX = 30
WRONG_PER_MINUTE = 5
_wrong: dict[str, list[float]] = {}  # user id -> when a wrong current password was given, to slow guessing down


def _held_log(s, x: dict) -> list[dict]:
    if x["id"] == s.library_id:
        return s.log
    if s.team is not None:
        other = s.team.items.get(x["id"])
        return list(other.log[:1]) if other is not None else []
    held = s._library_held.get(x["id"])
    if not held:
        return []
    pipes, pid = held
    return next(p for p in pipes if p["id"] == pid).get("log") or []


def _light(s, x: dict):
    """(the definition, the modules applied, the library's rows, a description) of a library not opened yet, from its
    files: the studio file and the modules it names, composed. Kept for the session while its studio file stands as it
    was (one taken away and put back is written again, and read again); None where it cannot be read."""
    kept = s.__dict__.setdefault("_entry_light", {})
    try:
        sig = Path(x["path"]).stat().st_mtime_ns
    except OSError:
        sig = 0
    if kept.get(x["id"], (None,))[0] == sig:
        return kept[x["id"]][1]
    out = None
    try:
        import yaml

        from ontlas.library import Library
        from ontlas.manage import NAME
        from ontlas.modules import compose

        p = Path(x["path"])
        spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if spec.get("modules") or "ontology" not in spec:
            lib = Library(p.parent / spec.get("library", "."))
            wanted = lib.applied() or list(spec.get("modules") or [])
            if NAME in lib.names() and NAME not in wanted:
                wanted.append(NAME)
            comp = compose(lib.resolve(wanted), namespace=spec.get("namespace", ""), name=spec.get("name", ""),
                           label=str(spec.get("label") or ""))
            out = (comp.ontology, list(comp.modules), lib.list(), str(spec.get("description") or ""), len(comp.cards))
        else:
            from ontlas.model import Ontology

            o = Ontology.load(p.parent / spec["ontology"])
            out = (o, [], [], str(spec.get("description") or ""), 0)
    except Exception:  # a file that no longer reads: the row keeps its name and says nothing more
        out = None
    kept[x["id"]] = (sig, out)
    return out


def _maturity(o, levels: dict[str, int]) -> dict | None:
    """How far the definition has come, by Object: the level being worked toward, and how many Objects are there.
    Where no Entity is filed under an Object the Entities are counted instead."""
    if not levels:
        return None
    groups = [[levels[t.name] for t in o.objects.values() if t.area == a.name] for a in o.areas.values()]
    lows = [min(g) for g in groups if g]
    unit = "Object"
    if not lows:
        lows, unit = list(levels.values()), "Entity"
    low = min(lows)
    at = min(low + 1, 3)
    return {"low": low, "at": at, "done": sum(v >= at for v in lows), "all": len(lows), "unit": unit, "full": low >= 3}


def _rows(lib_rows: list[dict], modules: list) -> list[dict]:
    from ontlas.modules import Requirement
    from ontlas.preview import MODULE_KIND
    from ontlas.web.api import KIND_ORDER, WORKSPACE

    on = {m.name: m.version for m in modules}
    rows = [{"name": r["name"], "label": r.get("label") or r["name"], "kind": r.get("kind", ""),
             "kind_label": MODULE_KIND.get(r.get("kind", ""), r.get("kind", "")), "version": on.get(r["name"], r.get("latest", "")),
             "on": r["name"] in on, "requires": [Requirement.parse(str(q)).name for q in r.get("requires") or []],
             "counts": {k: (r.get("counts") or {}).get(k, 0) for k in ("areas", "objects", "properties", "links", "rule_cards", "decisions", "terms", "questions")},
             "description": r.get("description", "")}
            for r in lib_rows if r["name"] != WORKSPACE]
    rows.sort(key=lambda r: (KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else 99, r["name"]))
    return rows


def _one(s, x: dict) -> dict:
    from ontlas.bindings import entity_level

    current = x["id"] == s.library_id
    studio = s.library_studio(x["id"])
    out: dict[str, Any] = {"id": x["id"], "label": x["label"], "made": bool(x.get("made")), "current": current,
                           "held": studio is not None, "source": x.get("source", ""), "description": str(x.get("description") or ""),
                           "base": "", "modules": [], "counts": None, "maturity": None, "version": "", "last": None}
    base = next((b for b in s.libraries if b["id"] == x.get("base")), None)
    if base is not None:
        out["base"] = base["label"]
    elif x.get("base_label"):
        out["base"] = x["base_label"]
    o, modules, lib_rows, cards = None, [], [], 0
    if studio is not None:
        o = studio.onto
        comp = studio.composition
        modules = list(comp.modules) if comp else []
        cards = len(comp.cards) if comp else 0
        lib_rows = (s._library_rows if current else studio.library.list()) if studio.library is not None else []
        if not out["source"] and studio.source:
            b = studio.backends.get(studio.source)
            out["source"] = str(getattr(b, "kind", "") or "")
        levels = s._entity_levels() if current else {t.name: entity_level(o, t.name) for t in o.objects.values()}
        log = _held_log(s, x)
        if log:
            out["last"] = {"text": log[0].get("text", ""), "at": log[0].get("at", "")}
    else:
        light = _light(s, x) if x.get("path") else None
        if light is None:
            return out
        o, modules, lib_rows, said, cards = light
        out["description"] = out["description"] or said
        levels = {t.name: entity_level(o, t.name) for t in o.objects.values()}
    out["modules"] = _rows(lib_rows, modules)
    domain = next((m for m in modules if m.kind == "domain"), modules[0] if modules else None)
    out["version"] = domain.version if domain is not None else str(getattr(o, "version", "") or "")
    if not out["description"] and domain is not None:
        out["description"] = domain.description or ""
    out["counts"] = {"objects": len(o.areas), "entities": len(o.objects),
                     "properties": sum(len(t.properties) for t in o.objects.values()), "links": len(o.links),
                     "rules": cards + sum(len(d.rules) for d in o.decisions.values()),
                     "terms": sum((r["counts"].get("terms") or 0) for r in out["modules"] if r["on"]),
                     "questions": len(o.questions)}
    out["maturity"] = _maturity(o, levels)
    return out


@get("entry/ontologies")
def ontologies(s, a, who) -> dict:
    """Every ontology there is to choose, each with what it is made of and how far it has come. Where the server
    keeps the ones made here, those who make them also read the ones taken away, to put one back."""
    from ontlas.web.api import plain

    made = sum(bool(x.get("made")) for x in s.libraries)
    return plain({"ontologies": [_one(s, x) for x in list(s.libraries)], "current": s.library_id, "made": made,
                  "made_max": s.made_max,
                  "deleted": s.library_deleted() if who is None or who.may("admin") else []})


@get("entry/export")
def export(s, a, who):
    """One ontology's definitions as a zip, read by its id: the one the person looks at stays the one they look at.
    The zip is the one the open ontology exports (export/library)."""
    from types import SimpleNamespace

    x = next((y for y in s.libraries if y["id"] == str(a.get("id") or "")), None)
    if x is None:
        raise ValueError("온톨로지를 찾지 못해 내보내지 못했습니다. 온톨로지 목록을 다시 열어 주세요.")
    studio = s.library_studio(x["id"])
    if studio is None:  # not opened yet: composed from its files, as the list reads it
        light = _light(s, x) if x.get("path") else None
        if light is None:
            raise ValueError("온톨로지 파일을 읽지 못해 내보내지 못했습니다. 서버의 온톨로지 파일을 확인해 주세요.")
        studio = SimpleNamespace(onto=light[0], composition=SimpleNamespace(modules=light[1]) if light[1] else None)
    data, name = type(s).export_library(SimpleNamespace(studio=studio, libraries=s.libraries, library_id=x["id"]))
    return 200, data, "application/zip", name


@post("entry/ontology/new", needs="admin")
def ontology_new(s, a, who) -> dict:
    """An ontology made here. `start` is pack (the modules chosen from an ontology's library), base (every module an
    ontology applies), files (the definition files held) or empty. `base` names the ontology the modules come from."""
    start = str(a.get("start") or "")
    if start not in ("pack", "base", "files", "empty"):
        raise ValueError("시작 방법을 선택하지 않아 생성하지 못했습니다. 시작 방법을 선택해 주세요.")
    came = s.library_id
    base, modules = None, None
    if start in ("pack", "base"):
        base = next((x for x in s.libraries if x["id"] == str(a.get("base") or came)), None)
        if base is None:
            raise ValueError("기반 온톨로지를 찾지 못해 생성하지 못했습니다. 기반 온톨로지를 다시 선택해 주세요.")
        modules = [str(m) for m in (a.get("modules") or [])] if start == "pack" else None
        if start == "pack" and not modules:
            raise ValueError("적용할 모듈이 없어 생성하지 못했습니다. 도메인 팩 모듈을 하나 이상 선택해 주세요.")
    said = {"key": str(a.get("key") or ""), "modules": modules, "description": str(a.get("description") or "")}
    label, start = str(a.get("label") or ""), "base" if base is not None else start
    if s.team is not None:  # made in the base's own studio; only the person who made it goes on to look at it
        return s.team.make(s, who, label, start, base=base["id"] if base is not None else "", **said)
    if base is not None and base["id"] != came:
        s.library_use(base["id"])
    try:
        return s.library_new(label, start, **said)
    except Exception:
        if s.library_id != came:  # nothing was made: the person is back on the ontology they were on
            s.library_use(came)
        raise


@post("entry/ontology/restore", needs="admin")
def ontology_restore(s, a, who) -> dict:
    """An ontology that was taken away, put back as it was."""
    return s.library_restore(str(a.get("id") or ""))


def _decided(s) -> list[dict]:
    """What was settled: change requests approved or rejected, action requests that ran or were turned down."""
    out: list[dict] = []
    for cr in s.studio.changes.requests.values():
        if cr.status == "pending":
            continue
        row = s._version_row(cr, None)
        moved = f"{row['from']} → {row['to']}" if row["from"] else row["to"]  # a module's first version comes from none
        out.append({"kind": "change", "id": cr.id, "title": f"{row['module_label']} {moved}",
                    "status": cr.status, "status_label": row["status_label"], "by": cr.decided_by or "",
                    "at": row["decided_at"] or cr.at, "detail": row["summary"]})
    when: dict[str, str] = {}
    for e in s.studio.actions.audit:
        when[e.proposal] = e.at
    for p in s.studio.actions.proposals.values():
        if p.status == "pending":
            continue
        v = s._proposal(p)
        out.append({"kind": "action", "id": p.id, "title": f"{v['label']} · {v['target_label']} {p.key}", "status": p.status,
                    "status_label": "", "by": v.get("approved_by") or v.get("rolled_back_by") or "", "at": when.get(p.id, ""),
                    "detail": f"{v['requested_by']} 요청", "target": p.target, "key": str(p.key)})
    out.sort(key=lambda x: str(x["at"]), reverse=True)
    return out[:ROWS_MAX]


@get("entry/inbox")
def inbox(s, a, who) -> dict:
    """The person's list in three parts: what waits on someone, what happened in this ontology, what was settled."""
    from ontlas.web.api import plain

    return plain({"box": s.inbox(), "notes": list(s.log)[:ROWS_MAX], "done": _decided(s)})


def _two_factor(logins, u) -> dict:
    return {"on": bool(u is not None and u.totp), "required": bool(logins is not None and logins.policy["two_factor"])}


@get("entry/me")
def me(s, a, who) -> dict:
    """How this server lets people in, as the account screen says it: how long a sign-in lasts, or where nobody signs
    in how long an unused session is kept, whether the person can change their own password here, their email, their
    second step and the devices they are signed in on."""
    logins, limits = routes.SERVER.get("logins"), routes.SERVER.get("limits") or {}
    policy = logins.policy if logins is not None else POLICY
    idle = limits.get("idle") if logins is None else None
    mine = who is not None and logins is not None
    return {"team": who is not None, "hours": policy["session_hours"] if logins is not None else None,
            "idle_minutes": round(idle / 60) if idle else None, "password_min": policy["password_min"],
            "can_change_password": mine and logins.users.path is not None,
            "email": who.email if mine else "", "two_factor": _two_factor(logins, who if mine else None),
            "devices": logins.devices(who.id, routes.asked().get("device", "")) if mine else [],
            "keep_days": policy["keep_days"] if logins is not None else None,
            "session_hours": policy["session_hours"] if logins is not None else None}


def _slowed(uid: str, done: str) -> list[float]:
    """The wrong passwords this person gave in the last minute; too many and nothing more is tried for now."""
    import time

    now = time.time()
    tries = [t for t in _wrong.get(uid, []) if now - t < 60]
    if len(tries) >= WRONG_PER_MINUTE:
        raise ValueError(f"현재 비밀번호 입력 오류가 반복되어 {done} 못했습니다. 1분 후 다시 시도해 주세요.")
    return tries


def _wrong_once(uid: str, tries: list[float]) -> None:
    import time

    _wrong[uid] = [*tries, time.time()]


@post("entry/password", needs="viewer")
def password(s, a, who) -> dict:
    """The signed-in person's own password, changed with the one they have now: as long as the policy asks, and none
    of the last ones again. Every sign-in of theirs ends with it, and a password an admin gave is theirs from now."""
    logins = routes.SERVER.get("logins")
    if who is None or logins is None or logins.users.path is None or who.id not in logins.users.users:
        raise ValueError("비밀번호를 변경할 수 없는 계정이어서 변경하지 못했습니다. 시스템 관리자에게 재설정을 요청해 주세요.")
    u = logins.users.users[who.id]
    tries = _slowed(u.id, "변경하지")
    current, new = str(a.get("current") or ""), str(a.get("new") or "")
    if not check_password(current, u.password):
        _wrong_once(u.id, tries)
        raise ValueError("현재 비밀번호가 맞지 않아 변경하지 못했습니다. 다시 입력해 주세요.")
    least = logins.policy["password_min"]
    if len(new) < least:
        raise ValueError(f"새 비밀번호가 {least}자보다 짧아 변경하지 못했습니다. {least}자 이상으로 입력해 주세요.")
    if new == current:
        raise ValueError("새 비밀번호가 현재 비밀번호와 같아 변경하지 못했습니다. 다른 비밀번호를 입력해 주세요.")
    if logins.users.reused(u, new):
        raise ValueError(f"새 비밀번호가 최근에 쓴 비밀번호와 같아 변경하지 못했습니다. 최근 {HISTORY}개와 다른 비밀번호를 입력해 주세요.")
    with logins.users.lock:
        logins.users.set_password(u, new)
        logins.users.save()
    _wrong.pop(u.id, None)
    logins.end(u.id)
    _note(s, who, "login", "비밀번호 변경")
    return {"ok": True}


def _mine(who, done: str):
    """The sign-ins and the record of the person asking; `done` is what was not done without them."""
    logins = routes.SERVER.get("logins")
    if who is None or logins is None or who.id not in logins.users.users:
        raise ValueError(f"로그인한 팀 계정이 없어 {done} 못했습니다. 팀 서버에 로그인해 주세요.")
    return logins, logins.users.users[who.id]


@post("entry/profile", needs="viewer")
def profile(s, a, who) -> dict:
    """The signed-in person's own name and email."""
    logins, u = _mine(who, "프로필을 저장하지")
    name, email = " ".join(str(a.get("name") or "").split())[:80], str(a.get("email") or "").strip()[:120]
    if not name:
        raise ValueError("이름이 비어 있어 저장하지 못했습니다. 이름을 입력해 주세요.")
    if email and not EMAIL.fullmatch(email):
        raise ValueError("이메일 형식이 맞지 않아 저장하지 못했습니다. name@example.com 형식으로 입력해 주세요.")
    if logins.users.email_taken(email, but=u.id):
        raise ValueError(with_particles(f"이메일 {email}이(가) 이미 등록되어 저장하지 못했습니다. 다른 이메일을 입력해 주세요."))
    if name == u.name and email == u.email:
        raise ValueError("변경된 내용이 없어 저장하지 못했습니다. 내용을 수정한 뒤 저장해 주세요.")
    with logins.users.lock:
        u.name, u.email = name, email
        logins.users.save()
    _note(s, who, "user", f"사용자 {u.name}({u.id}) 프로필 변경")
    return {"ok": True, "name": u.name, "email": u.email}


@post("entry/2fa/start", needs="viewer")
def two_factor_start(s, a, who) -> dict:
    """A secret for the person's authenticator app, kept ten minutes for the code that turns it on."""
    logins, u = _mine(who, "2단계 인증을 설정하지")
    if u.totp:
        raise ValueError("2단계 인증이 이미 켜져 있어 설정하지 못했습니다. 다시 설정하려면 먼저 꺼 주세요.")
    return logins.enroll_start(u)


@post("entry/2fa/on", needs="viewer")
def two_factor_on(s, a, who) -> dict:
    logins, u = _mine(who, "2단계 인증을 켜지")
    if u.totp:
        raise ValueError("2단계 인증이 이미 켜져 있어 처리하지 못했습니다. 화면을 새로 고친 뒤 다시 시도해 주세요.")
    if not logins.enroll_finish(u, str(a.get("code") or "")):
        raise ValueError("인증 코드가 맞지 않아 2단계 인증을 켜지 못했습니다. 인증 앱의 6자리 코드를 다시 입력하거나 설정을 다시 시작해 주세요.")
    _note(s, who, "login", "2단계 인증 켬")
    return {"ok": True, "two_factor": _two_factor(logins, u)}


@post("entry/2fa/off", needs="viewer")
def two_factor_off(s, a, who) -> dict:
    """The second step turned off with the person's password, where the policy does not ask everyone for it."""
    logins, u = _mine(who, "2단계 인증을 끄지")
    if not u.totp:
        raise ValueError("2단계 인증이 꺼져 있어 처리하지 못했습니다. 화면을 새로 고친 뒤 다시 시도해 주세요.")
    if logins.policy["two_factor"]:
        raise ValueError("모든 사용자에게 2단계 인증이 필수라 끄지 못했습니다. 관리자에게 문의해 주세요.")
    tries = _slowed(u.id, "2단계 인증을 끄지")
    if not check_password(str(a.get("password") or ""), u.password):
        _wrong_once(u.id, tries)
        raise ValueError("비밀번호가 맞지 않아 2단계 인증을 끄지 못했습니다. 다시 입력해 주세요.")
    _wrong.pop(u.id, None)
    with logins.users.lock:
        u.totp = ""
        logins.users.save()
    _note(s, who, "login", "2단계 인증 끔")
    return {"ok": True, "two_factor": _two_factor(logins, u)}


@post("entry/device/out", needs="viewer")
def device_out(s, a, who) -> dict:
    """One device of the person's signed out, or with id "others" every one but the one asking."""
    logins, u = _mine(who, "로그아웃하지")
    device, here = str(a.get("id") or ""), routes.asked().get("device", "")
    if device == "others":
        ended = logins.end(u.id, but=here)
        if ended:
            _note(s, who, "login", f"다른 기기 모두 로그아웃 · {ended}대")
    else:
        gone = logins.end_device(u.id, device) if device else None
        if gone is None:
            raise ValueError("로그인한 기기를 찾지 못해 로그아웃하지 못했습니다. 목록을 새로 고친 뒤 다시 시도해 주세요.")
        ended = 1
        _note(s, who, "login", "기기 로그아웃" + (f" · {gone.agent}" if gone.agent else ""))
    return {"ok": True, "ended": ended, "devices": logins.devices(u.id, here)}
