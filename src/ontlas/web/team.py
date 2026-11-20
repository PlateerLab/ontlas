"""A team studio: people sign in, share the studio of the library each looks at, and may do what their roles allow.

    users:
      kim: {name: 김하람, password: "pbkdf2_sha256$260000$<salt>$<hash>", roles: [editor, approver]}

viewer reads and asks; editor changes data and files requests; approver approves changes and actions and turns a module
of the definition in use on or off;
admin also sets the flow and resets the studio. A change is approved by someone other than the person who asked.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ITERATIONS = 260_000
LEVELS = ("viewer", "editor", "approver", "admin")
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
