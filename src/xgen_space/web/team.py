"""A team studio: people sign in, share one studio, and may do what their roles allow.

    users:
      kim: {name: 김하람, password: "pbkdf2_sha256$260000$<salt>$<hash>", roles: [editor, approver]}

viewer reads and asks; editor changes data and modules and files requests; approver approves changes and actions;
admin also sets the flow and resets the studio. A change is approved by someone other than the person who asked.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ITERATIONS = 260_000
LEVELS = ("viewer", "editor", "approver", "admin")
# what each POST route needs; every GET and anything not listed needs viewer
NEEDS = {
    "attach": "editor", "detach": "editor", "upload": "editor", "files/sample": "editor", "catalog/folder": "editor",
    "catalog/remove": "editor", "catalog/rename": "editor", "catalog/include": "editor", "catalog/embed": "editor", "catalog/use": "editor",
    "catalog/repository": "editor", "catalog/import": "editor", "pipeline": "editor", "catalog/move": "editor", "catalog/trash": "editor",
    "draft": "editor", "draft/preview": "editor", "draft/apply": "approver", "connect": "editor",
    "module/save": "editor", "module/propose": "editor", "request": "editor", "identity/resolve": "editor",
    "sync": "editor", "draft/decision": "editor", "draft/decision/drop": "editor", "draft/map": "editor",
    "draft/map/apply": "approver", "policy/draft": "editor", "policy/draft/result": "editor", "manage/edit": "editor",
    "manage/questions": "editor", "space/store": "admin", "connect/gateway": "editor", "space/embedder": "admin",
    "space/relations/start": "editor", "space/relations/stop": "editor", "space/relations/forget": "editor", "conflict/pick": "editor", "transitions/advance": "approver",
    "draft/table": "editor", "draft/review/apply": "approver", "draft/review/preview": "editor",  # a reviewed draft replaces the shared space: an approver applies it
    "manage/undo": "editor", "manage/trial": "editor", "manage/yaml": "editor", "element/comment": "editor",
    "graph/view": "editor", "graph/view/forget": "editor", "workspace/layout": "editor",
    "manage/discard": "editor", "manage/propose": "editor", "function/run": "editor",
    "manage/redo": "editor", "manage/revert": "editor",
    "change/decide": "approver", "change/mark": "approver", "change/comment": "editor", "approve": "approver", "rollback": "approver",
    "flow/save": "admin", "reset": "admin",
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


@dataclass
class User:
    id: str
    name: str
    password: str
    roles: list[str] = field(default_factory=list)

    def may(self, level: str) -> bool:
        if level == "viewer":
            return True
        if "admin" in self.roles:
            return True
        if level == "editor":
            return bool({"editor", "approver"} & set(self.roles))
        return level in self.roles


class Users:
    def __init__(self, users: dict[str, User], path: Path | None = None):
        self.users, self.path = users, path

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
            users[str(uid)] = User(str(uid), str(u.get("name") or uid), str(u.get("password") or ""), roles)
        return cls(users, p)

    def add(self, uid: str, password: str, *, name: str = "", roles: list[str] = ("viewer",)) -> User:
        import yaml

        bad = [r for r in roles if r not in LEVELS]
        if bad:
            raise ValueError(f"unknown roles {bad}; roles are {LEVELS}")
        if len(password) < 10:
            raise ValueError("a password has at least 10 characters")
        u = User(uid, name or uid, hash_password(password), list(roles))
        self.users[uid] = u
        if self.path is not None:
            body = {"users": {k: {"name": v.name, "password": v.password, "roles": v.roles}
                              for k, v in self.users.items()}}
            self.path.write_text(yaml.safe_dump(body, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return u

    def verify(self, uid: str, password: str) -> User | None:
        u = self.users.get(uid)
        if u is None:
            check_password(password, hash_password("x" * 10, iterations=ITERATIONS))  # the same time for no one
            return None
        return u if check_password(password, u.password) else None


class Logins:
    """Signed-in people by session token; a token ends after `hours` or on sign-out."""

    def __init__(self, users: Users, *, hours: float = 12):
        self.users, self.ttl = users, hours * 3600
        self.tokens: dict[str, tuple[str, float]] = {}
        self.lock = threading.Lock()
        self.tries: dict[str, list[float]] = {}

    def allow_try(self, ip: str, per_minute: int = 10) -> bool:
        now = time.time()
        with self.lock:
            hits = [t for t in self.tries.get(ip, []) if now - t < 60]
            if len(hits) >= per_minute:
                self.tries[ip] = hits
                return False
            self.tries[ip] = hits + [now]
            return True

    def sign_in(self, uid: str, password: str) -> tuple[str, User] | None:
        u = self.users.verify(uid, password)
        if u is None:
            return None
        token = secrets.token_urlsafe(24)
        with self.lock:
            self.tokens[token] = (u.id, time.time() + self.ttl)
        return token, u

    def user(self, token: str) -> User | None:
        with self.lock:
            hit = self.tokens.get(token or "")
            if hit is None:
                return None
            uid, until = hit
            if time.time() > until:
                del self.tokens[token]
                return None
        return self.users.users.get(uid)

    def sign_out(self, token: str) -> None:
        with self.lock:
            self.tokens.pop(token or "", None)


class TeamSessions:
    """One studio the whole team works in, built once."""

    team = True

    def __init__(self, build: Callable, logins: Logins):
        self.logins = logins
        self.shared = build()
        self.shared.self_approve = False
        self.shared._adopt(self.shared.studio)
        self.lock = threading.Lock()
        self.items = {"team": self.shared}

    def get(self, sid: str):
        return sid, self.shared, False

    def reset(self, sid: str):
        return self.shared


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
