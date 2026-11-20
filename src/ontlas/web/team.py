"""A team studio: people sign in, share the studio of the library each looks at, and may do what their roles allow.

    users:
      kim: {name: 김하람, password: "pbkdf2_sha256$260000$<salt>$<hash>", roles: [editor, approver], email: kim@example.com}
    policy: {session_hours: 12, keep_days: 14, password_min: 10, lock_after: 5, lock_minutes: 15, two_factor: false}

viewer reads and asks; editor changes data and files requests; approver approves changes and actions and turns a module
of the definition in use on or off;
admin also sets the flow and resets the studio. A change is approved by someone other than the person who asked.

A person is active, disabled (kept on the list, never let in) or pending (asked to join, waits for an admin). Who signs
in is kept beside the users file (`<name>.logins.json`), by the sha256 of each token only, so a restart signs no one out.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import struct
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from ontlas.words import fix as with_particles

ITERATIONS = 260_000
LEVELS = ("viewer", "editor", "approver", "admin")
STATES = ("active", "disabled", "pending")
# what a users file without a policy is held to
POLICY = {"session_hours": 12, "keep_days": 14, "password_min": 8, "lock_after": 5, "lock_minutes": 15,
          "two_factor": False, "allow_ip": [], "signup": True}
USER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]{1,63}")
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
HISTORY = 3  # earlier passwords a new one may not repeat
TICKET_SECONDS = 300  # between a password that was right and the step after it
ENROLL_SECONDS = 600  # a secret shown on the account screen waits this long for its first code
SEEN_EVERY = 300  # a sign-in's last request is written down no more often than this
SETUP_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I: read off a terminal and typed
# what each POST route needs; every GET and anything not listed needs viewer
NEEDS = {
    "attach": "approver", "detach": "approver",  # the definition the whole team works in changes: as an approval does
    "upload": "editor", "files/sample": "editor", "catalog/folder": "editor",
    "catalog/remove": "editor", "catalog/rename": "editor", "catalog/include": "editor", "catalog/embed": "editor", "catalog/use": "editor",
    "catalog/repository": "editor", "catalog/import": "editor", "pipeline": "editor", "catalog/move": "editor", "catalog/trash": "editor",
    "draft": "editor", "draft/preview": "editor", "draft/apply": "editor", "connect": "admin",  # a data source: the ontology's admin
    "module/save": "editor", "module/propose": "editor", "request": "editor", "identity/resolve": "editor",
    "sync": "editor", "draft/decision": "editor", "draft/decision/drop": "editor", "draft/map": "editor",
    "draft/map/apply": "approver", "policy/draft": "editor", "policy/draft/result": "editor", "manage/edit": "editor",
    "manage/questions": "editor", "space/store": "admin", "connect/gateway": "admin", "space/embedder": "admin",
    "space/relations/start": "editor", "space/relations/stop": "editor", "space/relations/forget": "editor", "conflict/pick": "editor", "transitions/advance": "approver",
    "draft/table": "editor", "draft/review/apply": "editor", "draft/review/preview": "editor",  # a reviewed draft goes into the request being written
    "draft/request": "editor", "draft/request/drop": "editor", "draft/request/apply": "approver",  # an editor files the draft for an approver to apply
    "manage/undo": "editor", "manage/trial": "editor", "manage/yaml": "editor", "element/comment": "editor",
    "graph/view": "editor", "graph/view/forget": "editor", "workspace/layout": "editor",
    "manage/discard": "editor", "manage/propose": "editor", "manage/conflict": "editor", "function/run": "editor",
    "manage/redo": "editor", "manage/revert": "editor", "lexicon/edit": "editor", "lexicon/import": "editor",
    "change/decide": "approver", "change/mark": "approver", "change/comment": "editor", "change/reopen": "editor", "approve": "approver", "rollback": "approver",
    "flow/save": "admin", "reset": "admin",
    # a library made or taken away is the server's, beside the team's others; which one a person looks at ("library") is their own
    "library/file": "admin", "library/file/drop": "admin", "library/new": "admin", "library/drop": "admin",
}


def hash_password(password: str, *, salt: bytes | None = None, iterations: int = ITERATIONS) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(iterations, base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def check_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, digest = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), base64.b64decode(salt), int(iterations))
        return hmac.compare_digest(got, base64.b64decode(digest))
    except (ValueError, TypeError):
        return False


_nobody: list[str] = []  # a hash checked where no one has the name given, so a wrong name takes as long as a wrong password


def _check_nobody(password: str) -> None:
    if not _nobody:
        _nobody.append(hash_password("x" * 10))
    check_password(password, _nobody[0])


# ---- two-step sign-in: RFC 6238, SHA1, 6 digits, 30 seconds ----------------------------------------------------------

def totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret: str, step: int) -> str:
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    mac = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    at = mac[-1] & 0x0F
    return f"{(struct.unpack('>I', mac[at:at + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def totp_match(secret: str, code: str, now: float, after: int = -1) -> int | None:
    """The time step a code was made for, one step either side of now allowed for a clock that drifts; None where it
    is not one of them, or one already used (`after`: the last step used)."""
    code = re.sub(r"\s", "", str(code or ""))
    if not secret or not re.fullmatch(r"\d{6}", code):
        return None
    step = int(now // 30)
    for s in (step - 1, step, step + 1):
        if s > after and hmac.compare_digest(totp_code(secret, s), code):
            return s
    return None


def totp_uri(uid: str, secret: str) -> str:
    return f"otpauth://totp/Ontlas:{quote(uid)}?secret={secret}&issuer=Ontlas"


# ---- where a request comes from -------------------------------------------------------------------------------------

def ip_allowed(ip: str, nets: list[str]) -> bool:
    """Whether an address is in one of the ranges (CIDR or one address); no ranges lets everyone in."""
    if not nets:
        return True
    try:
        addr = ipaddress.ip_address(str(ip or "").strip())
    except ValueError:
        return False
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    for net in nets:
        try:
            if addr in ipaddress.ip_network(str(net), strict=False):
                return True
        except ValueError:
            continue
    return False


def agent_of(header: str) -> str:
    """A User-Agent said as the account screen lists a device: browser · system."""
    ua = str(header or "")
    browser = next((name for mark, name in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"),
                                            ("Safari/", "Safari")) if mark in ua), "")
    system = next((name for mark, name in (("Windows", "Windows"), ("iPhone", "iOS"), ("iPad", "iOS"), ("Android", "Android"),
                                           ("Mac OS X", "macOS"), ("Linux", "Linux")) if mark in ua), "")
    if browser or system:
        return " · ".join(x for x in (browser, system) if x)
    return ua.split("/", 1)[0].strip()[:40]


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t).isoformat(timespec="seconds") if t else ""


def _epoch(iso: str) -> float:
    try:
        return datetime.fromisoformat(str(iso)).timestamp() if iso else 0.0
    except ValueError:
        return 0.0


@dataclass
class User:
    id: str
    name: str
    password: str
    roles: list[str] = field(default_factory=list)
    email: str = ""
    employee_no: str = ""
    note: str = ""
    state: str = "active"
    must_change: bool = False  # a password an admin gave: changed at the next sign-in before going in
    previous: list[str] = field(default_factory=list)  # hashes of the passwords before this one, oldest first
    totp: str = ""  # the two-step secret (base32); there is one where the person turned it on
    failures: int = 0  # wrong passwords or codes in a row
    locked_until: str = ""

    def may(self, level: str) -> bool:
        if level == "viewer":
            return True
        if "admin" in self.roles:
            return True
        if level == "editor":
            return bool({"editor", "approver"} & set(self.roles))
        return level in self.roles

    def locked(self, now: float) -> bool:
        return _epoch(self.locked_until) > now


class Users:
    """The people of a team and the policy they sign in under, as the users file holds them. Everything that changes
    either is written back by save(), the one place the file is written."""

    def __init__(self, users: dict[str, User], path: Path | None = None, policy: dict | None = None):
        self.users, self.path = users, path
        self.policy = {**POLICY, **(policy or {})}
        self.policy["allow_ip"] = list(self.policy["allow_ip"])
        self.lock = threading.RLock()

    @classmethod
    def load(cls, path: str | Path) -> Users:
        import yaml

        p = Path(path)
        d = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
        users = {}
        for uid, u in ((d or {}).get("users") or {}).items():
            roles = [str(r) for r in (u.get("roles") or ["viewer"])]
            bad = [r for r in roles if r not in LEVELS]
            if bad:
                raise ValueError(f"user {uid}: unknown roles {bad}; roles are {LEVELS}")
            state = str(u.get("state") or "active")
            if state not in STATES:
                raise ValueError(f"user {uid}: unknown state {state!r}; states are {STATES}")
            users[str(uid)] = User(str(uid), str(u.get("name") or uid), str(u.get("password") or ""), roles,
                                   email=str(u.get("email") or ""), employee_no=str(u.get("employee_no") or ""),
                                   note=str(u.get("note") or ""), state=state, must_change=bool(u.get("must_change")),
                                   previous=[str(x) for x in u.get("previous") or []][-HISTORY:], totp=str(u.get("totp") or ""),
                                   failures=int(u.get("failures") or 0), locked_until=str(u.get("locked_until") or ""))
        policy = {k: v for k, v in ((d or {}).get("policy") or {}).items() if k in POLICY}
        return cls(users, p, policy)

    def save(self) -> None:
        """The whole file, written beside itself and put in its place, so a crash mid-write leaves the one before."""
        import yaml

        if self.path is None:
            return
        with self.lock:
            body = {"users": {k: {f: v for f, v in asdict(u).items() if f != "id"} for k, u in self.users.items()},
                    "policy": dict(self.policy)}
            text = yaml.safe_dump(body, allow_unicode=True, sort_keys=False)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, self.path)

    def add(self, uid: str, password: str, *, name: str = "", roles: list[str] = ("viewer",)) -> User:
        """One person who may sign in with this password, or a new password for one already there (as `ontlas users
        add` does): let in at once, unlocked, not asked to change it."""
        bad = [r for r in roles if r not in LEVELS]
        if bad:
            raise ValueError(f"unknown roles {bad}; roles are {LEVELS}")
        least = self.policy["password_min"]
        if len(password) < least:
            raise ValueError(f"a password has at least {least} characters")
        with self.lock:
            u = self.users.get(uid)
            if u is None:
                u = self.users[uid] = User(uid, name or uid, "", list(roles))
            u.name, u.roles, u.state, u.failures, u.locked_until = name or uid, list(roles), "active", 0, ""
            self.set_password(u, password)
            self.save()
        return u

    def set_password(self, u: User, password: str, *, must_change: bool = False) -> None:
        with self.lock:
            if u.password:
                u.previous = [*u.previous, u.password][-HISTORY:]
            u.password, u.must_change = hash_password(password), must_change

    def reused(self, u: User, password: str) -> bool:
        """Whether a new password is one of the earlier ones kept."""
        return any(check_password(password, h) for h in u.previous)

    def verify(self, uid: str, password: str) -> User | None:
        u = self.users.get(uid)
        if u is None:
            _check_nobody(password)
            return None
        return u if check_password(password, u.password) else None

    def find(self, said: str) -> User | None:
        """The person a sign-in names: by id, else by email where one person alone has it."""
        u = self.users.get(said)
        if u is not None or "@" not in said:
            return u
        hits = [x for x in self.users.values() if x.email and x.email.lower() == said.lower()]
        return hits[0] if len(hits) == 1 else None

    def email_taken(self, email: str, but: str = "") -> bool:
        return bool(email) and any(u.email.lower() == email.lower() and u.id != but for u in self.users.values())

    def admins(self, without: str = "") -> int:
        """The admins who can sign in, but one."""
        return sum(1 for u in self.users.values() if "admin" in u.roles and u.state == "active" and u.id != without)

    def vet(self, uid: str, email: str, password: str, *, done: str) -> None:
        """What a person made from outside the admin screens (the first admin, one who asks to join) must be. `done`
        is what was not done, as the sentence says it ("회원가입하지")."""
        if not USER_ID.fullmatch(uid):
            raise ValueError(f"아이디 형식이 맞지 않아 {done} 못했습니다. 영문, 숫자, . _ @ - 로 2자 이상 입력해 주세요.")
        if uid in self.users:
            raise ValueError(with_particles(f"아이디 {uid}이(가) 이미 있어 {done} 못했습니다. 다른 아이디를 입력해 주세요."))
        if email and not EMAIL.fullmatch(email):
            raise ValueError(f"이메일 형식이 맞지 않아 {done} 못했습니다. name@example.com 형식으로 입력해 주세요.")
        if self.email_taken(email):
            raise ValueError(with_particles(f"이메일 {email}이(가) 이미 등록되어 {done} 못했습니다. 다른 이메일을 입력해 주세요."))
        least = self.policy["password_min"]
        if len(password) < least:
            raise ValueError(f"비밀번호가 {least}자보다 짧아 {done} 못했습니다. {least}자 이상 입력해 주세요.")


class Refused(Exception):
    """A sign-in step refused: the status it is answered with, and what the page is told beside the sentence."""

    def __init__(self, code: int, message: str, **said):
        super().__init__(message)
        self.code, self.said = code, said


@dataclass
class Login:
    """One sign-in, kept under the sha256 of its token."""
    uid: str
    until: float
    at: float  # signed in
    seen: float  # its last request, to SEEN_EVERY
    ip: str = ""
    agent: str = ""
    keep: bool = False


class Logins:
    """Signed-in people by session token. A sign-in goes through the steps the person and the policy ask for (a code,
    a code's first setting up, a new password) on a ticket that lasts five minutes, and ends after the policy's hours,
    or its days where the person asked to stay signed in, or on sign-out."""

    def __init__(self, users: Users):
        self.users = users
        self.lock = threading.Lock()
        self.clock: Callable[[], float] = time.time  # what "now" is; a test moves it
        self.note: Callable[..., None] | None = None  # the server's audit trail: note(by, text, what="login")
        self.tries: dict[str, list[float]] = {}
        self.tokens: dict[str, Login] = {}  # sha256 of a token -> its sign-in
        self.last: dict[str, dict] = {}  # user id -> {at, seen} of their latest sign-in, kept after it ends
        self.tickets: dict[str, dict] = {}  # a step's ticket -> {uid, step, keep, until, secret}
        self.enrolling: dict[str, tuple[str, float]] = {}  # user id -> (a secret shown on the account screen, until)
        self.used: dict[str, int] = {}  # user id -> the last time step a code was taken for: a code is used once
        self.strangers: dict[str, User] = {}  # names nobody has, counted and locked as a person's would be
        self.setup = ""
        self.path = users.path.with_name(f"{users.path.stem}.logins.json") if users.path is not None else None
        self._read()

    @property
    def policy(self) -> dict:
        return self.users.policy

    def allowed(self, ip: str) -> bool:
        return ip_allowed(ip, self.policy.get("allow_ip") or [])

    def allow_try(self, ip: str, per_minute: int = 10) -> bool:
        now = time.time()
        with self.lock:
            hits = [t for t in self.tries.get(ip, []) if now - t < 60]
            if len(hits) >= per_minute:
                self.tries[ip] = hits
                return False
            self.tries[ip] = hits + [now]
            return True

    def say(self, by: str, text: str, what: str = "login") -> None:
        if self.note is not None:
            self.note(by, text, what)

    # ---- the tokens, and the file that keeps them ------------------------------------------------------------------

    def lifetime(self, keep: bool) -> float:
        days = self.policy["keep_days"]
        return days * 86400 if keep and days else self.policy["session_hours"] * 3600

    def _ends(self, x: Login) -> float:  # a policy made shorter since applies at once
        return min(x.until, x.at + self.lifetime(x.keep))

    def _read(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            now = self.clock()
            self.tokens = {k: Login(**v) for k, v in (d.get("tokens") or {}).items()}
            self.tokens = {k: x for k, x in self.tokens.items() if now <= self._ends(x)}
            self.last = {str(k): dict(v) for k, v in (d.get("last") or {}).items()}
        except (ValueError, TypeError, AttributeError) as e:  # a file cut off or edited by hand: everyone signs in again
            print(f"{self.path.name} did not read ({type(e).__name__}); nobody stays signed in", file=sys.stderr)
            self.tokens, self.last = {}, {}

    def _write(self) -> None:
        """Under self.lock. A token that ended goes; one that could not be written is said, and sign-ins go on."""
        if self.path is None:
            return
        now = self.clock()
        self.tokens = {k: x for k, x in self.tokens.items() if now <= self._ends(x)}
        body = {"tokens": {k: asdict(x) for k, x in self.tokens.items()}, "last": self.last}
        tmp = self.path.with_name(self.path.name + ".tmp")
        try:
            tmp.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as e:
            print(f"{self.path.name} was not written: {e}", file=sys.stderr)

    @staticmethod
    def key(token: str) -> str:
        return hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    def device(self, token: str) -> str:
        """A sign-in as the account screen names it: the first 12 of its key."""
        return self.key(token)[:12] if token else ""

    def _issue(self, u: User, keep: bool, ip: str, agent: str) -> dict:
        now = self.clock()
        keep = bool(keep and self.policy["keep_days"])
        token = secrets.token_urlsafe(24)
        with self.lock:
            self.tokens[self.key(token)] = Login(u.id, now + self.lifetime(keep), now, now, ip, agent, keep)
            self.last[u.id] = {"at": now, "seen": now}
            self._write()
        if u.failures or u.locked_until:
            with self.users.lock:
                u.failures, u.locked_until = 0, ""
                self.users.save()
        self.say(u.name, "로그인" + (" · 로그인 유지" if keep else "") + (f" · {agent}" if agent else ""))
        return {"token": token, "user": u, "keep": keep}

    def user(self, token: str) -> User | None:
        if not token:
            return None
        key, now = self.key(token), self.clock()
        with self.lock:
            x = self.tokens.get(key)
            if x is None:
                return None
            if now > self._ends(x):
                del self.tokens[key]
                self._write()
                return None
            if now - x.seen >= SEEN_EVERY:
                x.seen = now
                self.last.setdefault(x.uid, {"at": x.at})["seen"] = now
                self._write()
        u = self.users.users.get(x.uid)
        return u if u is not None and u.state == "active" else None

    def sign_out(self, token: str) -> Login | None:
        with self.lock:
            gone = self.tokens.pop(self.key(token), None) if token else None
            if gone is not None:
                self._write()
        return gone

    def end(self, uid: str, but: str = "") -> int:
        """Every sign-in of this person ends, but the device `but`."""
        with self.lock:
            gone = [k for k, x in self.tokens.items() if x.uid == uid and k[:12] != but]
            for k in gone:
                del self.tokens[k]
            if gone:
                self._write()
        return len(gone)

    def end_device(self, uid: str, device: str) -> Login | None:
        with self.lock:
            k = next((k for k, x in self.tokens.items() if x.uid == uid and k[:12] == device), None)
            gone = self.tokens.pop(k) if k is not None else None
            if gone is not None:
                self._write()
        return gone

    def devices(self, uid: str, current: str = "") -> list[dict]:
        now = self.clock()
        with self.lock:
            mine = [(k, x) for k, x in self.tokens.items() if x.uid == uid and now <= self._ends(x)]
        mine.sort(key=lambda kx: kx[1].seen, reverse=True)
        return [{"id": k[:12], "agent": x.agent, "ip": x.ip, "at": _iso(x.at), "seen": _iso(x.seen), "current": k[:12] == current}
                for k, x in mine]

    def status(self) -> dict[str, dict]:
        """Per person: whether a sign-in of theirs is live, when they last signed in and last asked anything."""
        now = self.clock()
        with self.lock:
            live = {x.uid for x in self.tokens.values() if now <= self._ends(x)}
            return {uid: {"live": uid in live, "at": _iso(v.get("at") or 0), "seen": _iso(v.get("seen") or 0)}
                    for uid, v in self.last.items()}

    # ---- signing in, step by step ----------------------------------------------------------------------------------

    def _stranger(self, said: str) -> User:
        key = said.lower()[:80]
        with self.lock:
            if len(self.strangers) > 1000:
                now = self.clock()
                self.strangers = {k: v for k, v in self.strangers.items() if v.locked(now)}
            return self.strangers.setdefault(key, User(key, said[:80], ""))

    def _open(self, x: User, now: float) -> None:
        """Refused while locked; a lock that ran out is lifted, with the count behind it."""
        if x.locked(now):
            when = datetime.fromtimestamp(_epoch(x.locked_until))
            raise Refused(423, f"로그인에 {x.failures}회 실패해 계정이 잠겼습니다. {when:%H:%M} 이후 다시 시도하거나 관리자에게 "
                               "잠금 해제를 요청해 주세요.", locked_until=x.locked_until)
        if x.locked_until:
            with self.users.lock:
                x.failures, x.locked_until = 0, ""
                if self.users.users.get(x.id) is x:
                    self.users.save()

    def _failed(self, x: User, why: str, wrong: str) -> None:
        """One more wrong password or code; at the policy's count the account locks. Always raises."""
        now, most, minutes = self.clock(), self.policy["lock_after"], self.policy["lock_minutes"]
        with self.users.lock:
            x.failures += 1
            if x.failures >= most:
                x.locked_until = _iso(now + minutes * 60)
            if self.users.users.get(x.id) is x:
                self.users.save()
        self.say(x.name, f"로그인 실패 · {why}")
        if x.locked_until:
            self.say(x.name, f"계정 잠금 · 로그인 {x.failures}회 실패, {minutes}분")
            self._open(x, now)
        raise Refused(401, f"{wrong} 맞지 않아 로그인하지 못했습니다. (실패 {x.failures}/{most})", failures=x.failures, lock_after=most)

    def _ticket(self, u: User, step: str, keep: bool, secret: str = "") -> str:
        ticket, now = secrets.token_urlsafe(24), self.clock()
        with self.lock:
            self.tickets = {k: t for k, t in self.tickets.items() if t["until"] > now}
            self.tickets[ticket] = {"uid": u.id, "step": step, "keep": keep, "until": now + TICKET_SECONDS, "secret": secret}
        return ticket

    def _next(self, u: User, keep: bool, ip: str, agent: str, *, coded: bool = False) -> dict:
        """What comes after the steps done: a code, a code's setting up, a new password, or the sign-in itself."""
        if not coded and u.totp:
            return {"step": "code", "ticket": self._ticket(u, "code", keep)}
        if not coded and self.policy["two_factor"]:
            secret = totp_secret()
            return {"step": "enroll", "ticket": self._ticket(u, "enroll", keep, secret), "secret": secret, "uri": totp_uri(u.id, secret)}
        if u.must_change:
            return {"step": "password", "ticket": self._ticket(u, "password", keep), "password_min": self.policy["password_min"]}
        return self._issue(u, keep, ip, agent)

    def begin(self, said: str, password: str, *, keep: bool = False, ip: str = "", agent: str = "") -> dict:
        """The first step: an id or an email, and a password. {token, user, keep} once in, else {step, ticket, ...}."""
        said = str(said or "").strip()
        u = self.users.find(said)
        x = u if u is not None else self._stranger(said)
        self._open(x, self.clock())
        if u is None:
            _check_nobody(password)
            self._failed(x, "비밀번호 불일치", "아이디 또는 비밀번호가")
        if not check_password(password, u.password):
            self._failed(u, "비밀번호 불일치", "아이디 또는 비밀번호가")
        if u.state == "disabled":
            self.say(u.name, "로그인 실패 · 사용 중지된 계정")
            raise Refused(403, "사용이 중지된 계정이라 로그인하지 못했습니다. 관리자에게 문의해 주세요.", state="disabled")
        if u.state == "pending":
            self.say(u.name, "로그인 실패 · 승인 대기 계정")
            raise Refused(403, "관리자 승인 전이라 로그인하지 못했습니다. 승인 후 다시 로그인해 주세요.", state="pending")
        return self._next(u, keep, ip, agent)

    def go_on(self, ticket: str, a: dict, *, ip: str = "", agent: str = "") -> dict:
        """A step after the password, on the ticket the step before gave: {code}, {code, secret} or {new_password}."""
        now = self.clock()
        with self.lock:
            t = self.tickets.get(str(ticket or ""))
        u = self.users.users.get(t["uid"]) if t is not None and t["until"] > now else None
        if u is None or u.state != "active":
            self._drop(ticket)
            raise Refused(401, "로그인 확인 시간이 지나 로그인하지 못했습니다. 처음부터 다시 로그인해 주세요.", expired=True)
        try:
            self._open(u, now)
            if t["step"] == "password":
                return self._new_password(u, ticket, t, str(a.get("new_password") or ""), ip, agent)
            secret = t["secret"] if t["step"] == "enroll" else u.totp
            if t["step"] == "enroll" and a.get("secret") and str(a["secret"]) != secret:  # a page that set up another
                raise Refused(401, "로그인 확인 시간이 지나 로그인하지 못했습니다. 처음부터 다시 로그인해 주세요.", expired=True)
            step = totp_match(secret, str(a.get("code") or ""), now, self.used.get(u.id, -1))
            if step is None:
                self._failed(u, "인증 코드 불일치", "인증 코드가")
        except Refused as e:
            if e.code == 423 or e.said.get("expired"):  # locked, or begun again: the password is asked again
                self._drop(ticket)
            raise
        self.used[u.id] = step
        self._drop(ticket)
        if t["step"] == "enroll":
            with self.users.lock:
                u.totp = secret
                self.users.save()
            self.say(u.name, "2단계 인증 켬")
        return self._next(u, t["keep"], ip, agent, coded=True)

    def _drop(self, ticket: str) -> None:
        with self.lock:
            self.tickets.pop(str(ticket or ""), None)

    def _new_password(self, u: User, ticket: str, t: dict, new: str, ip: str, agent: str) -> dict:
        least = self.policy["password_min"]
        if len(new) < least:
            raise ValueError(f"새 비밀번호가 {least}자보다 짧아 변경하지 못했습니다. {least}자 이상으로 입력해 주세요.")
        if check_password(new, u.password):
            raise ValueError("새 비밀번호가 현재 비밀번호와 같아 변경하지 못했습니다. 다른 비밀번호를 입력해 주세요.")
        if self.users.reused(u, new):
            raise ValueError(f"새 비밀번호가 최근에 쓴 비밀번호와 같아 변경하지 못했습니다. 최근 {HISTORY}개와 다른 비밀번호를 입력해 주세요.")
        with self.users.lock:
            self.users.set_password(u, new)
            self.users.save()
        self._drop(ticket)
        self.say(u.name, "비밀번호 변경")
        return self._next(u, t["keep"], ip, agent, coded=True)

    def sign_in(self, uid: str, password: str, *, keep: bool = False, ip: str = "", agent: str = "") -> tuple[str, User] | None:
        """(token, user) where an id and a password alone sign a person in; None where they do not (a wrong password,
        or a step still to go). Refused for an account locked, disabled or waiting."""
        try:
            out = self.begin(uid, password, keep=keep, ip=ip, agent=agent)
        except Refused as e:
            if e.code == 401:
                return None
            raise
        return (out["token"], out["user"]) if "token" in out else None

    # ---- two steps set up from the account screen ------------------------------------------------------------------

    def enroll_start(self, u: User) -> dict:
        secret = totp_secret()
        with self.lock:
            self.enrolling[u.id] = (secret, self.clock() + ENROLL_SECONDS)
        return {"secret": secret, "uri": totp_uri(u.id, secret)}

    def enroll_finish(self, u: User, code: str) -> bool:
        now = self.clock()
        with self.lock:
            secret, until = self.enrolling.get(u.id, ("", 0.0))
        step = totp_match(secret, code, now, self.used.get(u.id, -1)) if until > now else None
        if step is None:
            return False
        with self.lock:
            self.enrolling.pop(u.id, None)
        self.used[u.id] = step
        with self.users.lock:
            u.totp = secret
            self.users.save()
        return True

    # ---- the first admin, and those who ask to join ----------------------------------------------------------------

    def need_setup(self) -> bool:
        return not self.users.admins()

    def setup_code(self) -> str:
        """While no admin can sign in: the code that lets the first be made, made once a start, said on stderr and
        written beside the users file for whoever runs the server."""
        if not self.need_setup():
            return ""
        with self.lock:
            if not self.setup:
                said = "".join(secrets.choice(SETUP_LETTERS) for _ in range(16))
                self.setup = f"{said[:8]}-{said[8:]}"
                if self.users.path is not None:
                    self.users.path.parent.mkdir(parents=True, exist_ok=True)
                    self.users.path.with_name(f"{self.users.path.stem}.setup").write_text(self.setup + "\n", encoding="utf-8")
                print(f"ontlas setup code: {self.setup} (no admin can sign in yet: open the page and finish the first setup with it)",
                      file=sys.stderr, flush=True)
        return self.setup

    def finish_setup(self, code: str, uid: str, name: str, password: str, email: str, *, ip: str = "", agent: str = "") -> dict:
        if not self.need_setup():
            raise Refused(409, "설치 설정이 이미 끝나 처리하지 못했습니다. 로그인해 주세요.")
        plain = lambda c: re.sub(r"[\s-]", "", str(c or "")).upper()  # noqa: E731
        if not hmac.compare_digest(plain(code), plain(self.setup_code())):
            raise Refused(403, "설치 코드가 맞지 않아 설정하지 못했습니다. 서버를 시작할 때 표시된 설치 코드를 입력해 주세요.")
        with self.users.lock:
            self.users.vet(uid, email, password, done="설정하지")
            u = self.users.users[uid] = User(uid, name or uid, hash_password(password), ["admin"], email=email)
            self.users.save()
        with self.lock:
            self.setup = ""
        if self.users.path is not None:
            self.users.path.with_name(f"{self.users.path.stem}.setup").unlink(missing_ok=True)
        self.say(u.name, f"최초 설치 · 시스템 관리자 {u.name}({uid}) 생성")
        return self._issue(u, False, ip, agent)

    def signup(self, uid: str, name: str, email: str, password: str) -> User:
        """One who asks to join: kept as pending, a viewer, until an admin lets them in."""
        if self.need_setup():
            raise Refused(409, "최초 설치 설정이 끝나지 않아 회원가입하지 못했습니다. 시스템 관리자에게 문의해 주세요.")
        if not self.policy["signup"]:
            raise Refused(403, "회원가입을 받지 않는 서버라 가입하지 못했습니다. 관리자에게 계정을 요청해 주세요.")
        if not email:
            raise ValueError("이메일이 없어 회원가입하지 못했습니다. 이메일을 입력해 주세요.")
        with self.users.lock:
            self.users.vet(uid, email, password, done="회원가입하지")
            u = self.users.users[uid] = User(uid, name or uid, hash_password(password), ["viewer"], email=email, state="pending")
            self.users.save()
        self.say(u.name, f"회원가입 신청 · {u.name}({uid})", "user")
        return u


class TeamSessions:
    """The studios a team works in: one a library, the first built at the start and each other the first time someone
    opens it. Everyone who has a library open works in its one studio. Which library a person looks at is their own:
    opening or making another changes it for them and for no one else.

    A request works in one studio under that studio's lock. What is about the libraries themselves (look, make, drop)
    takes its locks here, in one order: a library's gate, then its studio's lock, then api.MAKING. None holds two
    studios' locks."""

    team = True

    def __init__(self, build: Callable, logins: Logins):
        self.logins = logins
        self.shared = build()  # the first library's: where everyone starts, and what /v1 answers from
        self.shared.self_approve = False
        self.shared.team = self
        self.shared._adopt(self.shared.studio)
        self.lock = threading.Lock()
        self.items = {self.shared.library_id: self.shared}  # library id -> its studio, once opened
        self._gates: dict[str, threading.Lock] = {}  # library id -> held while its studio is built or taken away
        # user id -> the library they look at; "" once it was taken away from under them. Kept in the first library's
        # journal where there is one, so a restart leaves each person where they were
        self.at: dict[str, str] = {}
        journal = self.shared.studio.changes.journal
        for r in journal.read() if journal is not None else []:
            if r.get("kind") == "look":
                self.at[str(r.get("user") or "")] = str(r.get("library") or "")

    def get(self, sid: str):
        return sid, self.shared, False

    def reset(self, sid: str):  # the space is the team's: one person cannot wipe it for everyone
        raise ValueError("팀이 함께 쓰는 공간이라 초기화하지 못했습니다. 되돌릴 변경은 변경 요청 · 버전에서 롤백해 주세요.")

    def _gate(self, lid: str) -> threading.Lock:
        with self.lock:
            return self._gates.setdefault(lid, threading.Lock())

    def _journal(self, x: dict) -> Path | None:
        """Where a library other than the first keeps its requests, edits and comments, when the first keeps a journal:
        a made one in its own folder, so they go and come back with it; an offered one beside the first's journal, under
        a name that follows its studio file wherever it stands in the list."""
        main = self.shared.studio.changes.journal
        if main is None or not x.get("path"):
            return None
        home = Path(x["path"]).resolve().parent
        if x.get("made"):
            return home / "journal.jsonl"
        mark = hashlib.sha256(str(home).encode("utf-8")).hexdigest()[:6]
        return main.path.with_name(f"{main.path.stem}.{home.name}-{mark}{main.path.suffix}")

    def _open(self, x: dict, studio=None):
        """A studio of its own for one more library, set up as the first is: the same model, limits and repositories.
        Where the first writes approved changes this one writes them to its own folder, and where the first keeps a
        journal this one keeps its own. What is kept beside the repositories (applied pipelines, what readers found)
        stays the first library's."""
        from dataclasses import replace

        from ontlas.config import load_studio
        from ontlas.library import Library, OverlayLibrary
        from ontlas.web.api import StudioSession

        first = self.shared
        if studio is None:
            if not x.get("path"):
                raise LookupError(f"온톨로지 {x['id']}")
            studio = load_studio(x["path"])
        log = self._journal(x)
        if log is not None:
            studio.keep_journal(log)
        folder = studio.library.base if isinstance(studio.library, OverlayLibrary) else studio.library
        s = StudioSession(studio, llm=first.llm, data=replace(first.data, repositories=None), origin=dict(x["origin"]),
                          repositories=first.repositories)
        s.libraries, s.library_id, s.shelf, s.made_max, s.team = first.libraries, x["id"], first.shelf, first.made_max, self
        s.self_approve = False
        if first.store is not None and x.get("path") and folder is not None:
            s.store = Library(folder.root)
        s._adopt(s.studio)
        if log is not None:
            s.restore_pending()  # the edits being written in it when the server stopped
        return s

    def session(self, lid: str, studio=None):
        """A library's studio, built the first time it is asked for (around `studio` where it was just made)."""
        with self._gate(lid):
            with self.lock:
                s = self.items.get(lid)
            if s is not None:
                return s
            x = next((y for y in self.shared.libraries if y["id"] == lid), None)
            if x is None:
                raise LookupError(f"온톨로지 {lid}")
            try:
                s = self._open(x, studio)
            except LookupError:
                raise
            except Exception as e:  # a studio file that no longer reads, whatever its reader says of it
                print(f"library {lid} did not open: {type(e).__name__}: {e}", file=sys.stderr)
                raise ValueError("온톨로지 파일을 읽지 못해 열지 못했습니다. 서버의 온톨로지 파일을 확인해 주세요.") from None
            with self.lock:
                self.items[lid] = s
            return s

    def of(self, who: User, method: str, route: str):
        """The studio of the library this person looks at: the first, until they open another. Where theirs was taken
        away, nothing they send is written into another: the page reads the first again (state), and until it has, a
        request that writes is refused."""
        lid = self.at.get(who.id)
        if lid is None:
            return self.shared
        if not any(x["id"] == lid for x in self.shared.libraries):  # "" as well: it was taken away from under them
            if method == "GET":
                if route == "state":
                    self._look(who.id, None)
                return self.shared
            raise ValueError("보던 온톨로지가 삭제되어 요청을 처리하지 못했습니다. 화면을 새로고침해 주세요.")
        try:
            return self.session(lid)
        except (LookupError, ValueError):  # it no longer opens: as one taken away
            self.at[who.id] = ""
            return self.of(who, method, route)

    def _look(self, uid: str, lid: str | None) -> None:
        if lid is None or lid == self.shared.library_id:
            lid = None
            self.at.pop(uid, None)
        else:
            self.at[uid] = lid
        journal = self.shared.studio.changes.journal
        if journal is not None:
            journal.write("look", {"user": uid, "library": lid})

    def look(self, who: User, lid: str) -> dict:
        """This person looks at another library from now on. It is opened first: one that does not open leaves them
        where they were."""
        self.session(lid)
        self._look(who.id, lid)
        return {"ok": True}

    def make(self, s, who: User, label: str, start: str, *, key: str = "", modules: list | None = None,
             description: str = "", base: str = "") -> dict:
        """A library made by this person (api.library_make), who then looks at it; everyone else stays where they are.
        It is made in the studio of `base` where it starts on another library's modules, else in `s`, the one the
        person is in, which holds the files it is made from."""
        src = self.session(base) if base else s
        with src.lock:
            src.who = who.name
            out = src.library_make(label, start, key=key, modules=modules, description=description)
            pipes, _ = src._library_held.pop(out["id"])
        self.session(out["id"], pipes[0]["studio"])
        self._look(who.id, out["id"])
        return out

    def drop(self, who: User, lid: str) -> dict:
        """Take a made library away (api.library_drop). Whoever looked at it reads the first again."""
        with self._gate(lid):
            with self.lock:
                gone = self.items.get(lid)
            if gone is None or gone is self.shared:
                out = self.shared.library_drop(lid, by=who.name)
            else:
                with gone.lock:  # nothing is being written in it while its folder moves
                    out = self.shared.library_drop(lid, by=who.name)
                    with self.lock:
                        self.items.pop(lid, None)
            for uid in [u for u, at in self.at.items() if at == lid]:
                self.at[uid] = ""
            if self.at.get(who.id) == "":  # the one who took it away knows it is gone: they are on the first from here
                self._look(who.id, None)
        return out


class Syncer:
    """Reads the source of every open studio again every `every` seconds and sends the graphs what changed."""

    def __init__(self, sessions, every: float):
        self.sessions, self.every = sessions, every
        self.stop = threading.Event()

    def run(self) -> None:
        while not self.stop.wait(self.every):
            with self.sessions.lock:
                items = list(self.sessions.items.values())
            for s in items:
                if not any(b.capabilities.load for b in s.studio.backends.values()):
                    continue
                with s.lock:
                    s.studio.sync()

    def start(self) -> Syncer:
        threading.Thread(target=self.run, daemon=True).start()
        return self
