"""The studio page over HTTP: one studio per visitor, built from a studio file, dropped after a while."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, quote, urlparse

from ontlas.backends.base import NoSource
from ontlas.preview import CSS as BASE_CSS
from ontlas.web import routes
from ontlas.web.api import NO_SOURCE, NO_SOURCE_SAID, DataOptions, StudioSession

STATIC = Path(__file__).parent / "static"
COOKIE = "ontlas_session"
LOGIN = "ontlas_login"
MEDIA = "/media/demo.mp4"
KIT = "/graph-kit.js"
MAX_BODY = 64 * 1024
MODULE_BODY_MAX = 1 << 20  # a module's whole text, sent from its editor (api.MODULE_TEXT_MAX, with room for the JSON around it)
MODULE_ROUTES = {"module/check", "module/save", "module/propose"}


def page() -> bytes:
    """index.html with the stylesheet and script inlined, so a cache in front never serves a stale pair."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    parts = sorted((STATIC / "v2").glob("*"))  # the screens, one file an area; they are written inside app.js's scope
    css = BASE_CSS + "".join(p.read_text(encoding="utf-8") for p in
                             [STATIC / "app.css", STATIC / "kit.css", *(p for p in parts if p.suffix == ".css")])
    app = (STATIC / "app.js").read_text(encoding="utf-8").replace(
        "/*PARTS*/", "\n".join(p.read_text(encoding="utf-8") for p in parts if p.suffix == ".js"))
    js = f"window.GRAPH_KIT_URL={json.dumps(KIT + '?v=' + kit_version())};" + "".join(
        (STATIC / name).read_text(encoding="utf-8") for name in ("scene.js", "graph.js")) + app
    return html.replace("/*CSS*/", css).replace("/*JS*/", js).encode("utf-8")


def kit_version() -> str:
    """The graph engine stays out of the page, loaded when a graph opens; its address changes with its content."""
    return hashlib.sha256((STATIC / "graph-kit.js").read_bytes()).hexdigest()[:10]


class Sessions:
    """Visitors' studios, with one built ahead so a new visitor does not wait for the seed and projection."""

    def __init__(self, build: Callable[[], StudioSession], *, limit: int = 24, idle: float = 3600, spare: int = 1):
        self.build, self.limit, self.idle, self.spare = build, limit, idle, spare
        self.items: dict[str, StudioSession] = {}
        self.spares: list[StudioSession] = []
        self.lock = threading.Lock()
        self._filling = False
        self.fill()

    def fill(self) -> None:
        with self.lock:
            if self._filling or len(self.spares) >= self.spare:
                return
            self._filling = True

        def work() -> None:
            try:
                while True:
                    with self.lock:
                        if len(self.spares) >= self.spare:
                            return
                    s = self.build()
                    with self.lock:
                        self.spares.append(s)
            finally:
                with self.lock:
                    self._filling = False

        threading.Thread(target=work, daemon=True).start()

    def _take(self) -> StudioSession:
        with self.lock:
            s = self.spares.pop() if self.spares else None
        s = s or self.build()
        self.fill()
        return s

    def get(self, sid: str) -> tuple[str, StudioSession, bool]:
        now = time.time()
        with self.lock:
            for k in [k for k, s in self.items.items() if now - s.used > self.idle]:
                del self.items[k]
            s = self.items.get(sid) if sid else None
            if s is not None:
                s.used = now
                return sid, s, False
        s = self._take()
        sid = secrets.token_urlsafe(18)
        with self.lock:
            while len(self.items) >= self.limit:
                del self.items[min(self.items, key=lambda k: self.items[k].used)]
            s.used = now
            self.items[sid] = s
        return sid, s, True

    def reset(self, sid: str) -> StudioSession:
        s = self._take()
        with self.lock:
            s.used = time.time()
            self.items[sid] = s
        return s


class RateLimit:
    def __init__(self, per_minute: int):
        self.per_minute, self.hits, self.lock = per_minute, deque(), threading.Lock()

    def allow(self) -> bool:
        now = time.time()
        with self.lock:
            while self.hits and now - self.hits[0] > 60:
                self.hits.popleft()
            if len(self.hits) >= self.per_minute:
                return False
            self.hits.append(now)
            return True


def guide(video: Path | None) -> dict:
    """The demo video the page offers next to its manual, with the chapters written beside it (x.chapters.json)."""
    if video is None or not video.is_file():
        return {"video": "", "chapters": []}
    marks = video.with_suffix(".chapters.json")
    chapters = json.loads(marks.read_text(encoding="utf-8")) if marks.is_file() else []
    return {"video": f"{MEDIA}?v={int(video.stat().st_mtime)}", "chapters": chapters}




# these take the session's lock only around its data, or not at all: a model's answer waits tens of seconds, and a
# person's own account touches the sign-ins only, so it does not queue behind a long measurement of the shared space
OWN_LOCK = {"space/ask/more", "entry/password", "entry/profile", "entry/2fa/start", "entry/2fa/on", "entry/2fa/off",
            "entry/device/out"}
BLOCKED = "허용되지 않은 IP에서 접속해 요청을 처리하지 못했습니다. 관리자에게 문의해 주세요."
# in a team these are about the libraries themselves (which one a person looks at, one made, one taken away), not about
# one studio: each takes the lock of the one studio it reads or writes itself (team.TeamSessions)
TEAM_OWN_LOCK = {"library", "library/new", "library/drop", "entry/ontology/new"}


def make_handler(sessions: Sessions, *, ask_limit: RateLimit, quiet: bool = False, upload_max: int = 1 << 20,
                 video: Path | None = None, logins=None, rest=None):
    from ontlas.web.team import NEEDS, Refused, agent_of

    routes.load()
    body_html = page()
    live = bool(os.environ.get("ONTLAS_STATIC_LIVE"))  # while the screens are being written: every request reads the files again
    team = logins is not None
    etag = hashlib.sha256(body_html).hexdigest()[:16]
    the_guide = guide(video)
    if team:  # sign-ins are the server's records: kept in the first library's journal, as what admins do to users
        from ontlas.web.areas.admin import _note

        logins.note = lambda by, text, what="login": _note(sessions.shared, None, what, text, by=by)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ontlas"
        sys_version = ""

        def log_message(self, fmt: str, *args) -> None:
            if not quiet:
                sys.stderr.write(f"{self.log_date_time_string()} {fmt % args}\n")

        # ---- plumbing ----------------------------------------------------------------------------------------

        def _session(self) -> tuple[str, StudioSession, bool]:
            jar = SimpleCookie(self.headers.get("Cookie") or "")
            sid = jar[COOKIE].value if COOKIE in jar else ""
            return sessions.get(sid)

        def _token(self) -> str:
            jar = SimpleCookie(self.headers.get("Cookie") or "")
            return jar[LOGIN].value if LOGIN in jar else ""

        def _user(self):
            return logins.user(self._token()) if team else None

        def _secure(self) -> str:
            https = (self.headers.get("X-Forwarded-Proto") or "").lower() == "https"
            return "; Secure" if https else ""

        def _same_origin(self) -> bool:
            """A team studio's writes come from its own page: the custom header a form cannot send, and the origin."""
            if self.headers.get("X-Ontlas-Request") != "1":
                return False
            origin = self.headers.get("Origin")
            return not origin or urlparse(origin).netloc == (self.headers.get("Host") or "")

        def _refuse(self, code: int, message: str) -> None:
            """Answer without doing the request, after reading what the client sent, so it is not cut off mid-send."""
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 4 * max(upload_max, MAX_BODY):
                while n > 0:
                    chunk = self.rfile.read(min(n, 1 << 16))
                    if not chunk:
                        break
                    n -= len(chunk)
            self.close_connection = True
            self._json(code, {"error": message})

        def _client(self) -> str:
            """The visitor's address: as the tunnel in front says it, else the first proxy's, else the socket's."""
            fwd = (self.headers.get("CF-Connecting-IP") or "").strip() or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            return fwd or self.client_address[0]

        def _asked(self, path: str) -> bool:
            """Says where this request came from to the routes (routes.asked); False where a team's policy does not
            let that address in. What a page loads, /healthz and /v1 (its own keys) are not asked."""
            routes.asking(ip=self._client(), device=logins.device(self._token()) if team else "")
            return not (team and path.startswith("/api/") and not logins.allowed(self._client()))

        def _signed(self, out: dict) -> None:
            """A step's answer, or the sign-in it ended in: a cookie for as long as the person asked to stay."""
            if "token" not in out:
                return self._json(200, out)
            u, age = out["user"], f"; Max-Age={int(logins.lifetime(True))}" if out["keep"] else ""
            cookie = f"{LOGIN}={out['token']}; Path=/; HttpOnly; SameSite=Strict{age}{self._secure()}"
            return self._json(200, {"ok": True, "user": {"id": u.id, "name": u.name, "roles": u.roles}}, extra={"Set-Cookie": cookie})

        def _send(self, code: int, data: bytes, ctype: str, *, sid: str = "", new: bool = False,
                  extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if "Cache-Control" not in (extra or {}):
                self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
            if new and sid:
                self.send_header("Set-Cookie", f"{COOKIE}={sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _json(self, code: int, obj, **kw) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8",
                       **kw)

        def _media(self, path: Path) -> None:
            """One file, with byte ranges so the player can seek; the URL carries its version, so caches may keep it."""
            size = path.stat().st_size
            start, end, code = 0, size - 1, 200
            m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
            if m and (m[1] or m[2]):
                if m[1]:
                    start, end = int(m[1]), min(int(m[2]) if m[2] else size - 1, size - 1)
                else:
                    start = max(size - int(m[2]), 0)
                if start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    return self.end_headers()
                code = 206
            self.send_response(code)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("X-Content-Type-Options", "nosniff")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if self.command == "HEAD":
                return
            left = end - start + 1
            try:
                with path.open("rb") as f:
                    f.seek(start)
                    while left > 0:
                        chunk = f.read(min(left, 1 << 16))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # players drop a range request as soon as they have what they need

        def _body(self, most: int = MAX_BODY) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n > most:
                raise ValueError(f"요청 크기가 {most >> 10}KB 한도를 초과해 처리하지 못했습니다. 요청을 줄여 다시 시도해 주세요.")
            raw = self.rfile.read(n) if n else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("요청 형식이 올바르지 않아 처리하지 못했습니다. UTF-8 JSON으로 보내 주세요.") from None
            if not isinstance(data, dict):
                raise ValueError("요청 형식이 올바르지 않아 처리하지 못했습니다. JSON 객체로 보내 주세요.")
            return data

        # ---- routes ------------------------------------------------------------------------------------------

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/healthz":
                return self._send(200, b"ok", "text/plain; charset=utf-8")
            if url.path.startswith("/v1/"):
                return self._rest("GET", url.path, {k: v[0] for k, v in parse_qs(url.query).items()})
            if not self._asked(url.path):
                return self._json(403, {"error": BLOCKED})
            if url.path in ("/", "/index.html"):
                sid, _, new = self._session()
                body = page() if live else body_html
                return self._send(200, body, "text/html; charset=utf-8", sid=sid, new=new,
                                  extra={"ETag": hashlib.sha256(body).hexdigest()[:16] if live else etag, "Content-Security-Policy":
                                         "default-src 'self'; "
                                         "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
                                         "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                                         "font-src https://cdn.jsdelivr.net; img-src 'self' data:; "
                                         "connect-src 'self' https://cloudflareinsights.com; "
                                         "frame-ancestors 'none'"})
            if url.path == MEDIA and the_guide["video"]:
                return self._media(video)
            if url.path == KIT:
                return self._send(200, (STATIC / "graph-kit.js").read_bytes(), "text/javascript; charset=utf-8",
                                  extra={"Cache-Control": "public, max-age=31536000, immutable"})
            if url.path == "/api/guide":
                return self._json(200, the_guide)
            if url.path == "/api/me":
                u = self._user()
                said = {"team": team, "user": {"id": u.id, "name": u.name, "roles": u.roles} if u else None}
                if team and u is None:  # what the sign-in page offers: the first admin's setting up, or asking to join
                    setup, policy = logins.need_setup(), logins.policy
                    said.update(setup=setup, signup=bool(policy["signup"]) and not setup, password_min=policy["password_min"],
                                keep_days=policy["keep_days"])
                    if setup:
                        said["model"] = sessions.shared.llm is not None
                return self._json(200, said)
            if team and self._user() is None and url.path.startswith("/api/"):
                return self._json(401, {"error": "로그인하지 않아 요청을 처리하지 못했습니다. 로그인해 주세요."})
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "요청한 주소를 찾을 수 없습니다."})
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            self._api("GET", url.path[5:], q)

        def _rest(self, method: str, path: str, body: dict) -> None:
            """The API for other platforms: no session, a token. What it can do is described without one."""
            from ontlas import __version__
            from ontlas.rest import openapi, tool_list

            if path == "/v1/openapi.json":  # a platform that imports it needs to know where it answers
                host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or ""
                scheme = self.headers.get("X-Forwarded-Proto") or "http"
                return self._json(200, openapi(__version__, f"{scheme}://{host}" if host else ""))
            if path == "/v1/tools":
                return self._json(200, {"tools": tool_list()})
            if rest is None:
                return self._json(404, {"error": "API is off on this server. Start it with --api-token-env."})
            tools = rest.caller(self.headers.get("Authorization") or "")
            if tools is None:
                return self._json(401, {"error": "a valid bearer token is required"})
            with rest.lock:
                code, out = rest.answer(method, path, body, tools)
            self._json(code, out)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if url.path.startswith("/v1/"):
                try:
                    body = self._body()
                except (ValueError, json.JSONDecodeError) as e:
                    return self._json(400, {"error": str(e)})
                return self._rest("POST", url.path, body if isinstance(body, dict) else {})
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "요청한 주소를 찾을 수 없습니다."})
            if not self._asked(url.path):
                return self._refuse(403, BLOCKED)
            if team:
                if not self._same_origin():
                    return self._refuse(403, "이 페이지에서 보낸 요청이 아니어서 처리하지 못했습니다. 페이지를 새로 열어 "
                                             "다시 시도해 주세요.")
                if url.path in ("/api/login", "/api/logout"):
                    return self._login(url.path == "/api/login")
                if url.path in ("/api/setup", "/api/signup"):
                    return self._join(url.path == "/api/setup")
                user = self._user()
                if user is None:
                    return self._refuse(401, "로그인하지 않아 요청을 처리하지 못했습니다. 로그인해 주세요.")
                need = NEEDS.get(url.path[5:], "viewer")
                if not user.may(need):
                    return self._refuse(403, f"{user.name} 님의 권한으로는 이 작업을 할 수 없어 처리하지 못했습니다. "
                                             "권한이 있는 사람에게 요청해 주세요.")
            if url.path in ("/api/upload", "/api/library/file"):  # the file itself is the body; its path rides in the query
                n = int(self.headers.get("Content-Length") or 0)
                if n > upload_max:
                    if n <= 4 * upload_max:  # a file a little over the limit gets an answer it can show; more is cut off
                        while n > 0:
                            chunk = self.rfile.read(min(n, 1 << 16))
                            if not chunk:
                                break
                            n -= len(chunk)
                    self.close_connection = True
                    return self._json(400, {"error": f"파일 크기가 {upload_max >> 10:,}KB 한도를 초과해 업로드하지 못했습니다. 파일을 나누어 다시 업로드해 주세요."})
                q = {k: v[0] for k, v in parse_qs(url.query).items()}
                return self._api("POST", url.path[5:], {"path": q.get("path", ""), "data": self.rfile.read(n)})
            try:
                body = self._body(MODULE_BODY_MAX if url.path[5:] in MODULE_ROUTES else MAX_BODY)
            except (ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"error": str(e)})
            self._api("POST", url.path[5:], body)

        def _login(self, signing_in: bool) -> None:
            if not signing_in:
                try:
                    self._body()  # read what was sent, so the client is not cut off while it sends
                except ValueError:
                    pass
                gone = logins.sign_out(self._token())
                if gone is not None:
                    u = logins.users.users.get(gone.uid)
                    logins.say(u.name if u is not None else gone.uid, "로그아웃")
                return self._json(200, {"ok": True}, extra={"Set-Cookie": f"{LOGIN}=; Path=/; HttpOnly; "
                                                                          f"SameSite=Strict; Max-Age=0{self._secure()}"})
            if not logins.allow_try(self._client()):
                return self._refuse(429, "로그인 시도가 분당 한도를 초과해 처리하지 못했습니다. 1분 뒤 다시 시도해 주세요.")
            try:
                body = self._body()
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            ip, agent = self._client(), agent_of(self.headers.get("User-Agent") or "")
            try:
                if body.get("ticket"):  # a step after the password: a code, a code's setting up, a new password
                    out = logins.go_on(str(body["ticket"]), body, ip=ip, agent=agent)
                else:
                    out = logins.begin(str(body.get("user", "")), str(body.get("password", "")), keep=bool(body.get("keep")),
                                       ip=ip, agent=agent)
            except Refused as e:
                return self._json(e.code, {"error": str(e), **e.said})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            return self._signed(out)

        def _join(self, setting_up: bool) -> None:
            """The first admin, made with the code the server showed when it started; or one who asks to join."""
            if not logins.allow_try(self._client()):
                return self._refuse(429, "요청 시도가 분당 한도를 초과해 처리하지 못했습니다. 1분 뒤 다시 시도해 주세요.")
            try:
                body = self._body()
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            uid, name = str(body.get("id") or "").strip(), " ".join(str(body.get("name") or "").split())[:80]
            email, password = str(body.get("email") or "").strip()[:120], str(body.get("password") or "")
            try:
                if not setting_up:
                    logins.signup(uid, name, email, password)
                    return self._json(200, {"ok": True, "pending": True})
                out = logins.finish_setup(str(body.get("code") or ""), uid, name, password, email, ip=self._client(),
                                          agent=agent_of(self.headers.get("User-Agent") or ""))
            except Refused as e:
                return self._json(e.code, {"error": str(e), **e.said})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            return self._signed(out)

        def _api(self, method: str, route: str, a: dict) -> None:
            sid, s, new = self._session()
            user = self._user()
            try:
                if team and user is not None:
                    s = sessions.of(user, method, route)  # the studio of the library this person looks at
                # a page that says which library it shows writes nothing into another: the person opened one elsewhere
                # (another window) and this page has not read it yet. Opening one is how a page says it moves on
                shown = self.headers.get("X-Ontlas-Library")
                if method == "POST" and shown and shown != s.library_id and route != "library":
                    raise ValueError("다른 창에서 온톨로지를 전환해 요청을 처리하지 못했습니다. 화면을 새로고침해 주세요.")
                if route in OWN_LOCK or (team and route in TEAM_OWN_LOCK):
                    out = self._route(method, route, a, s, sid)
                else:
                    with s.lock:
                        if user is not None:
                            s.who = user.name
                        try:
                            out = self._route(method, route, a, s, sid)
                        finally:
                            if method == "POST":  # the edits being written, into the journal when they changed
                                s.keep_pending()
            except NoSource:  # it reads rows, and this studio holds its definition only: said as that, not as a failure
                return self._json(409, {"error": NO_SOURCE_SAID.get(route, NO_SOURCE), "no_source": True}, sid=sid, new=new)
            except LookupError as e:  # a sentence of the page's stays; an engine's key is not shown
                said = str(e.args[0]) if e.args and isinstance(e.args[0], str) else ""
                return self._json(400, {"error": said if re.search("[가-힣]", said) and said.endswith(".")
                                        else "요청한 항목을 찾지 못해 처리하지 못했습니다. 화면을 새로고침해 주세요."}, sid=sid, new=new)
            except PermissionError as e:
                return self._json(403, {"error": str(e)}, sid=sid, new=new)
            except ValueError as e:  # what a visitor sent does not fit: a file, a limit, an empty draft
                return self._json(400, {"error": str(e)}, sid=sid, new=new)
            except Exception as e:
                return self._json(500, {"error": f"{type(e).__name__}: {e}"}, sid=sid, new=new)
            if isinstance(out, tuple):
                code, data, ctype, name = out
                return self._send(code, data, ctype, sid=sid, new=new,
                                  extra={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})
            if out is None:
                return self._json(404, {"error": "요청한 주소를 찾을 수 없습니다."}, sid=sid, new=new)
            self._json(200, out, sid=sid, new=new)

        def _route(self, method: str, route: str, a: dict, s: StudioSession, sid: str):
            added = routes.find(method, route)
            if added is not None:
                return added(s, a, self._user())
            role = str(a.get("role") or "")
            principal = a.get("principal") if isinstance(a.get("principal"), dict) else None
            if method == "GET":
                if route == "state":
                    return s.state()
                if route == "object":
                    return s.object(a["name"])
                if route == "keys":
                    return {"keys": s.keys(a["type"]), **s.no_source()}
                if route == "actions/pending":
                    return s.pending_actions()
                if route == "audit":
                    return {"audit": s.audit()}
                if route == "functions/log":
                    return s.function_log()
                if route == "values":
                    return s.value_state()
                if route == "issues":
                    return s.issues()
                if route == "issue/preview":
                    return s.module_preview(a["module"])
                if route == "manage/link/suggest":
                    return s.link_suggest(a["source"], a["target"])
                if route == "naming":
                    return s.name_for(str(a.get("label", "")), str(a.get("kind", "object")))
                if route == "object/profile":
                    return s.object_profile(a["name"])
                if route == "files":
                    return s.files_state()
                if route == "catalog":
                    return s.catalog_state(str(a.get("folder", "")))
                if route == "catalog/file":
                    return s.catalog_file(str(a.get("path", "")))
                if route == "catalog/convert":
                    return s.catalog_convert()
                if route == "catalog/download":
                    return s.catalog_download(str(a.get("path", "")))
                if route == "catalog/json":
                    return s.catalog_json()
                if route == "catalog/trash":
                    return s.catalog_trash()
                if route == "catalog/history":
                    return s.catalog_history()
                if route == "explorer":
                    return s.explorer()
                if route == "explorer/items":
                    return s.explorer_items(str(a.get("node", "")))
                if route == "explorer/search":
                    return s.explorer_search(str(a.get("q", "")), str(a.get("kind", "")))
                if route == "module":
                    return s.module_source(a["name"], a.get("version", ""))
                if route == "object/rows":
                    return s.object_rows(a["name"], int(a.get("limit", 20)))
                if route == "record":
                    return s.record_page(a["type"], a["key"])
                if route == "records":
                    return s.record_list(a["type"], a.get("q", ""), int(a.get("limit", 50)))
                if route == "inbox":
                    return s.inbox()
                if route == "change":
                    return s.change_detail(a["id"])
                if route == "record/links":
                    return s.record_links(a["type"], a["key"])
                if route == "records/labels":
                    return s.record_labels(a["type"], str(a.get("keys", "")).split(","), a.get("prop", ""))
                if route == "graph/views":
                    return s.graph_views()
                if route == "build/steps":
                    return s.build_steps()
                if route == "overview":
                    return s.overview()
                if route == "versions":
                    return s.versions()
                if route == "record/path":
                    return s.record_path(a["from_type"], a["from_key"], a["to_type"], a["to_key"])
                if route == "element/readers":
                    return s.element_readers(a["id"])
                if route == "records/find":
                    return s.record_find(a.get("q", ""), a.get("limit", 10), a.get("type", ""), a.get("offset", 0))
                if route == "element/yaml":
                    return s.element_yaml(a["id"])
                if route == "element/comments":
                    return s.element_comments(a["id"])
                if route == "export/module":
                    return (200, s.export_module(a["name"]).encode("utf-8"), "application/yaml; charset=utf-8",
                            f"{a['name']}.yaml")
                if route == "export/library":
                    data, name = s.export_library()
                    return 200, data, "application/zip", name
                if route == "library/files":
                    return s.library_files()
                if route == "rules":
                    return s.rules_state()
                if route == "semantic":
                    return s.semantic_state()
                if route == "metric":
                    return s.metric_run(a["name"], a.get("since") or None, a.get("until") or None)
                if route == "space":
                    return s.space_state()
                if route == "space/graph":
                    return s.space_graph(str(a.get("folder", "")))
                if route == "space/relations":
                    return s.relations_list(str(a.get("folder", "")), str(a.get("concept", "")))
                if route == "space/relations/status":
                    return s.relations_status(str(a.get("job", "")))
                if route == "space/queries":
                    return s.space_queries()
                if route == "space/section":
                    return s.space_section(a["document"], a["section"])
                if route == "space/map":
                    return s.space_map()
                if route == "space/map/node":
                    return s.space_map_node(a["node"])
                if route == "adapters":
                    return s.adapters()
                if route == "connections":
                    return s.connections()
                if route == "integrations":
                    return s.integrations()
                if route == "monitor":
                    return {**s.monitor(), "visitors": 1 if team else len(getattr(sessions, "items", {})) or 1}
                if route == "manage":
                    return s.manage_state()
                if route == "lexicon":
                    return s.lexicon_state()
                if route == "flow":
                    return s.flow()
                if route == "flow/settings":
                    return s.flow_settings()
                if route == "changes":
                    return s.changes_state()
                if route == "agreement":
                    return s.agreement(pending=a.get("pending") in ("1", "true"))
                if route == "identities":
                    return s.identities()
                if route == "standards":
                    return s.standards()
                if route == "export/owl":
                    return 200, s.export_owl().encode("utf-8"), "text/turtle; charset=utf-8", "ontology.ttl"
                if route == "export/jdm":
                    from ontlas.decide.zen import to_jdm

                    jdm = to_jdm(s.studio.onto.decisions[a["decision"]])
                    return (200, json.dumps(jdm, ensure_ascii=False, indent=2).encode("utf-8"),
                            "application/json; charset=utf-8", f"{a['decision']}.json")
                return None
            if route == "impact":
                return s.impact(a["name"], bool(a.get("cascade")))
            if route == "detach":
                return s.detach(a["name"], bool(a.get("cascade")))
            if route == "attach":
                return s.attach(a["name"])
            if route == "query":
                out = s.run_query(a["name"], a.get("params") or {}, role=role, principal=principal)
                s.event("query", f"질의 실행 · {out.get('label') or a['name']}")
                return out
            if route == "text":
                return s.run_text(str(a.get("language", "sparql")), str(a.get("text", "")), role=role,
                                  principal=principal)
            if route == "conflict/pick":
                return s.conflict_pick(a.get("id", ""), a.get("source", ""), a.get("reason", ""))
            if route == "transitions/advance":
                return s.transitions_advance()
            if route == "space/search":
                return s.space_search(a.get("text", ""), a.get("k", 5), a.get("store", ""), str(a.get("folder", "")))
            if route == "space/embedder":
                return s.space_embedder(str(a.get("op", "plan")), a.get("spec") or {})
            if route == "space/store":
                return s.space_store(a.get("op", "add"), a.get("name", ""), a.get("kind", ""), a.get("url", ""))
            if route == "adapters/check":
                return s.adapters_check()
            if route == "reasoner":
                return s.reasoner_run(a.get("name", ""))
            if route == "space/relations/start":
                return s.relations_start(str(a.get("folder", "")), str(a.get("reader", "")), gate=ask_limit.allow)
            if route == "space/relations/stop":
                return s.relations_stop()
            if route == "space/relations/forget":
                return s.relations_forget(str(a.get("folder", "")))
            if route == "space/ask":
                return s.space_ask(str(a.get("text", "")), str(a.get("role", "")), a.get("principal") or None,
                                   pick=a.get("pick") or None, folder=str(a.get("folder", "")))
            if route == "space/ask/more":
                if not ask_limit.allow():
                    return {"ok": False, "error": "요청이 많아 답변을 만들지 못했습니다. 잠시 후 다시 시도해 주세요."}
                return s.space_ask_more(str(a.get("text", "")), str(a.get("role", "")), a.get("principal") or None,
                                        str(a.get("folder", "")))
            if route == "space/answer":
                if not ask_limit.allow():
                    return {"ok": False, "error": "요청이 많아 답변을 만들지 못했습니다. 1분 뒤에 다시 시도해 주세요."}
                return s.space_answer(a.get("text", ""))
            if route == "ask":
                if not ask_limit.allow():
                    return {"ok": False, "error": "분당 질문 한도를 초과해 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}
                return s.ask(str(a.get("question", "")), role=role, principal=principal)
            if route == "policy/draft":  # the same model and the same limit as questions
                if not ask_limit.allow():
                    return {"ok": False, "error": "분당 모델 호출 한도를 초과해 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."}
                return s.policy_start(str(a.get("text", "")), str(a.get("target", "")), str(a.get("name", "")))
            if route == "policy/draft/result":
                return s.policy_result(str(a.get("job", "")))
            if route == "policy/document":
                return s.document_text(str(a.get("name", "")), str(a.get("section", "")))
            if route == "policy/sample":
                return s.policy_sample()
            if route == "decide":
                s.event("decide", f"판정 · {a['name']} {a['key']}")
                return s.decide(a["name"], str(a["key"]))
            if route == "request":
                return s.request(a["action"], str(a["key"]), a.get("params") or {}, role, principal,
                                 kind="human" if a.get("kind") == "human" else "agent")
            if route == "approve":
                return s.approve(str(a["id"]), bool(a.get("approve", True)))
            if route == "function/run":
                return s.function_run(str(a.get("name", "")), str(a.get("key", "")), a.get("params") if isinstance(a.get("params"), dict) else {})
            if route == "questions":
                return s.questions()
            if route == "bindings":
                return s.bindings()
            if route == "upload":
                return s.catalog_upload(str(a["path"]), a["data"])
            if route == "files/sample":
                return s.use_samples()
            if route == "library":  # in a team the person looks at another library; the studio everyone works in stays
                return sessions.look(self._user(), str(a.get("id", ""))) if team else s.library_use(str(a.get("id", "")))
            if route == "library/file":
                return s.library_file(str(a["path"]), a["data"])
            if route == "library/file/drop":
                return s.library_file_drop(str(a.get("name", "")))
            if route == "library/new":
                label, start = str(a.get("label", "")), str(a.get("start", ""))
                kw = {"key": str(a.get("key", "")), "modules": a.get("modules") if isinstance(a.get("modules"), list) else None}
                return sessions.make(s, self._user(), label, start, **kw) if team else s.library_new(label, start, **kw)
            if route == "library/drop":
                return sessions.drop(self._user(), str(a.get("id", ""))) if team else s.library_drop(str(a.get("id", "")))
            if route == "pipeline":
                if a.get("op") == "delete":  # taking a data source out is as connecting one: the admin's
                    who = self._user()
                    if who is not None and not who.may(NEEDS["connect"]):
                        raise PermissionError(f"{who.name} 님의 권한으로는 이 작업을 할 수 없어 처리하지 못했습니다. "
                                              "권한이 있는 사람에게 요청해 주세요.")
                    return s.pipeline_delete(str(a.get("id", "")))
                return s.pipeline_use(str(a.get("id", "")))
            if route == "catalog/folder":
                return s.catalog_folder(str(a.get("path", "")))
            if route == "catalog/remove":
                return s.catalog_remove(list(a.get("paths") or []))
            if route == "catalog/rename":
                return s.catalog_rename(str(a.get("path", "")), str(a.get("name", "")))
            if route == "catalog/include":
                return s.catalog_include(list(a.get("paths") or []), bool(a.get("on")))
            if route == "catalog/use":
                return s.catalog_use(str(a.get("path", "")), str(a.get("use", "")))
            if route == "catalog/embed":
                return s.catalog_embed(list(a.get("paths") or []), bool(a.get("on")))
            if route == "catalog/move":
                return s.catalog_move(list(a.get("paths") or []), str(a.get("folder", "")))
            if route == "catalog/trash":
                return s.catalog_trash_op(str(a.get("op", "")), list(a.get("ids") or []))
            if route == "catalog/repository":
                return s.catalog_repository(str(a.get("op", "")), str(a.get("id", "")), str(a.get("label", "")))
            if route == "catalog/import":
                return s.catalog_import(str(a.get("path", "")), str(a.get("folder", "")))
            if route == "draft":
                return s.make_draft(str(a.get("label", "")), a.get("rules"), a.get("tables"))
            if route == "draft/preview":
                return s.preview_draft(a.get("edits"))
            if route == "draft/apply":
                return s.apply_draft(a.get("edits") if "edits" in a else {"drop": a.get("drop"),
                                                                           "labels": a.get("labels")})
            if route == "draft/decision":
                return s.induce_decision(str(a.get("target", "")), a.get("inputs") or [], str(a.get("label", "")),
                                         a.get("edits"))
            if route == "draft/decision/drop":
                return s.drop_decision(str(a.get("name", "")))
            if route == "draft/map":
                return s.suggest_mapping(a.get("standard") or [], a.get("edits"), a.get("tables"))
            if route == "draft/map/apply":
                return s.apply_mapping(a.get("standard") or [], a.get("edits"), a.get("mapping"))
            if route == "draft/table":
                return s.draft_table(str(a.get("table", "")))
            if route == "draft/review/preview":
                return s.review_preview(a.get("standard") or [], a.get("edits"), a.get("choices"))
            if route == "draft/review/apply":
                return s.apply_review(a.get("standard") or [], a.get("edits"), a.get("choices"), a.get("mapping"))
            if route == "draft/request":
                return s.request_draft(a.get("standard") or [], a.get("edits"), a.get("choices"))
            if route == "draft/request/drop":
                return s.drop_draft_request()
            if route == "draft/request/apply":
                return s.apply_draft_request()
            if route == "connect/gateway":
                return s.connect_gateway(a.get("url", ""), a.get("connection", ""), a.get("token", ""), a.get("dialect", "postgres"),
                                         str(a.get("label", "")), a.get("rules"))
            if route == "connect":
                return s.connect(str(a.get("dsn", "")), str(a.get("label", "")), a.get("rules"))
            if route == "module/check":
                return s.check_module(str(a.get("text", "")))
            if route == "module/save":
                return s.save_module(str(a.get("text", "")), bool(a.get("apply")))
            if route == "module/propose":
                return s.propose_module(str(a.get("text", "")), bool(a.get("apply")))
            if route == "manage/edit":
                return s.manage_edit(str(a.get("op", "")), a.get("args") if isinstance(a.get("args"), dict) else {})
            if route == "manage/questions":
                return s.manage_import_questions(str(a.get("text", "")))
            if route == "lexicon/edit":
                return s.lexicon_edit(str(a.get("op", "")), a.get("args") if isinstance(a.get("args"), dict) else {})
            if route == "lexicon/import":
                return s.lexicon_import(str(a.get("text", "") or ""), str(a.get("name", "") or ""), str(a.get("path", "") or ""))
            if route == "manage/discard":  # in a team a person's own edits; everyone's is the admin's
                who = self._user()
                everyone = bool(a.get("all"))
                if everyone and who is not None and not who.may("admin"):
                    raise PermissionError(f"{who.name} 님의 권한으로는 모든 사람의 편집을 폐기할 수 없어 처리하지 못했습니다. "
                                          "자기 편집만 폐기하거나 관리자에게 요청해 주세요.")
                return s.manage_discard(everyone)
            if route == "manage/undo":
                return s.manage_undo()
            if route == "manage/redo":
                return s.manage_redo()
            if route == "manage/revert":
                return s.manage_revert(int(a.get("index", -1)))
            if route == "manage/trial":
                return s.manage_trial()
            if route == "manage/yaml":
                return s.manage_yaml(str(a.get("id", "")), str(a.get("text", "")))
            if route == "element/comment":
                return s.element_comment(str(a.get("id", "")), str(a.get("text", "")))
            if route == "graph/view":
                return s.graph_view_save(str(a.get("name", "")), a.get("hide") or [], a.get("color"), a.get("label"),
                                         str(a.get("role", "") or ""))
            if route == "graph/view/forget":
                return s.graph_view_forget(str(a.get("name", "")))
            if route == "workspace/layout":
                return s.workspace_layout(str(a.get("pipeline", "")), a.get("positions") or {})
            if route == "manage/propose":
                return s.manage_propose()
            if route == "manage/conflict":
                return s.manage_conflict(str(a.get("id", "")), bool(a.get("keep")))
            if route == "change/mark":
                return s.change_mark(str(a.get("id", "")), str(a.get("element", "")), str(a.get("mark", "")))
            if route == "change/comment":
                return s.change_comment(str(a.get("id", "")), str(a.get("element", "")), str(a.get("text", "")))
            if route == "rest/try":
                return s.rest_try(str(a.get("path", "")), a.get("body") if isinstance(a.get("body"), dict) else {})
            if route == "decide/simulate":
                return s.simulate(str(a.get("name", "")), str(a.get("key", "") or ""),
                                  a.get("inputs") if isinstance(a.get("inputs"), dict) else {})
            if route == "change/decide":
                return s.decide_change(str(a.get("id", "")), bool(a.get("approve", True)), str(a.get("reason", "")),
                                       back=bool(a.get("back")))
            if route == "change/reopen":
                return s.reopen_change(str(a.get("id", "")))
            if route == "flow/save":
                return s.save_flow(a.get("settings") if isinstance(a.get("settings"), dict) else {},
                                   a.get("base") if isinstance(a.get("base"), dict) else None)
            if route == "identity/resolve":
                return s.resolve_identity(str(a.get("name", "")))
            if route == "sync":
                return s.sync()
            if route == "rollback":
                return s.rollback(str(a.get("id", "")))
            if route == "reset":
                sessions.reset(sid)
                return {"ok": True}
            return None

    return Handler


class Server(ThreadingHTTPServer):
    """The page's server. Python holds 5 connections waiting to be accepted by default: a page asks for several things at
    once, so a few visitors arriving together while a request is being worked on had their connections reset."""

    request_queue_size = 128
    daemon_threads = True


def serve(build: Callable[[], StudioSession], *, host: str = "127.0.0.1", port: int = 7710, limit: int = 24,
          idle: float = 3600, ask_per_minute: int = 20, quiet: bool = False, data: DataOptions | None = None,
          video: Path | None = None, users: Path | None = None, sync: float = 0,
          api: dict | list[dict] | None = None, libraries: list[dict] | None = None) -> None:
    """Serve the page: a studio per visitor, or with `users` one shared studio for a team that signs in.
    `api` turns /v1 on: one client, or a list of them, each {name, token, role, principal, write}."""
    from ontlas.web.team import Logins, Syncer, TeamSessions, Users

    logins = Logins(Users.load(users)) if users else None
    sessions = TeamSessions(build, logins) if logins else Sessions(build, limit=limit, idle=idle)
    rest = None
    clients = [c for c in ([api] if isinstance(api, dict) else api or []) if c.get("token")]
    if clients:  # a team's own studio, or one of its own; read-only unless told otherwise
        from ontlas.rest import Rest
        from ontlas.tools import StudioTools

        shared = sessions.shared if logins else None
        studio = shared.studio if shared else build().studio
        rest = Rest([(c["token"], StudioTools(studio, role=c.get("role") or None, principal=c.get("principal"),
                                              actor_id=c.get("name") or "api", read_only=not c.get("write"), audit=True))
                     for c in clients], source=(lambda: shared.studio) if shared else None,
                    lock=shared.lock if shared else None, libraries=libraries)
    # what the server was started with, for the areas that show it (who may call /v1, who signs in, the limits)
    routes.load()
    routes.started(rest=rest, logins=logins, sessions=sessions, limits={"sessions": limit, "idle": idle, "ask_per_minute": ask_per_minute,
                                                                          "upload_bytes": (data or DataOptions()).file_bytes},
                   users=users, video=video, host=host, port=port)
    httpd = Server((host, port), make_handler(sessions, ask_limit=RateLimit(ask_per_minute),
                                              quiet=quiet, upload_max=(data or DataOptions()).file_bytes,
                                              video=video, logins=logins, rest=rest))
    if sync:
        Syncer(sessions, sync).start()
    if logins is not None:
        logins.setup_code()  # no admin can sign in yet: the code for 최초 설치 설정, said once at the start
    print(f"ontlas on http://{host}:{port}" + (" (team)" if logins else ""), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
