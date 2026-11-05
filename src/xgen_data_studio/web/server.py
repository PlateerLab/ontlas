"""The studio page over HTTP: one studio per visitor, built from a studio file, dropped after a while."""
from __future__ import annotations

import hashlib
import json
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
from urllib.parse import parse_qs, urlparse

from xgen_data_studio.preview import CSS as BASE_CSS
from xgen_data_studio.web.api import DataOptions, StudioSession

STATIC = Path(__file__).parent / "static"
COOKIE = "xds_session"
LOGIN = "xds_login"
MEDIA = "/media/demo.mp4"
MAX_BODY = 64 * 1024


def page() -> bytes:
    """index.html with the stylesheet and script inlined, so a cache in front never serves a stale pair."""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    css = BASE_CSS + (STATIC / "app.css").read_text(encoding="utf-8")
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    return html.replace("/*CSS*/", css).replace("/*JS*/", js).encode("utf-8")


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


def make_handler(sessions: Sessions, *, ask_limit: RateLimit, quiet: bool = False, upload_max: int = 1 << 20,
                 video: Path | None = None, logins=None):
    from xgen_data_studio.web.team import NEEDS

    body_html = page()
    team = logins is not None
    etag = hashlib.sha256(body_html).hexdigest()[:16]
    the_guide = guide(video)

    class Handler(BaseHTTPRequestHandler):
        server_version = "xgen-data-studio"
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
            if self.headers.get("X-XDS-Request") != "1":
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
            fwd = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            return fwd or self.client_address[0]

        def _send(self, code: int, data: bytes, ctype: str, *, sid: str = "", new: bool = False,
                  extra: dict | None = None) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
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

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("요청 크기가 64KB 한도를 초과해 처리하지 못했습니다. 요청을 줄여 다시 시도해 주세요.")
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
            if url.path in ("/", "/index.html"):
                sid, _, new = self._session()
                return self._send(200, body_html, "text/html; charset=utf-8", sid=sid, new=new,
                                  extra={"ETag": etag, "Content-Security-Policy":
                                         "default-src 'self'; "
                                         "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
                                         "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                                         "font-src https://cdn.jsdelivr.net; img-src 'self' data:; "
                                         "connect-src 'self' https://cloudflareinsights.com; "
                                         "frame-ancestors 'none'"})
            if url.path == MEDIA and the_guide["video"]:
                return self._media(video)
            if url.path == "/api/guide":
                return self._json(200, the_guide)
            if url.path == "/api/me":
                u = self._user()
                return self._json(200, {"team": team, "user": {"id": u.id, "name": u.name, "roles": u.roles}
                                        if u else None})
            if team and self._user() is None and url.path.startswith("/api/"):
                return self._json(401, {"error": "로그인하지 않아 요청을 처리하지 못했습니다. 로그인해 주세요."})
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "요청한 주소를 찾을 수 없습니다."})
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            self._api("GET", url.path[5:], q)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "요청한 주소를 찾을 수 없습니다."})
            if team:
                if not self._same_origin():
                    return self._refuse(403, "이 페이지에서 보낸 요청이 아니어서 처리하지 못했습니다. 페이지를 새로 열어 "
                                             "다시 시도해 주세요.")
                if url.path in ("/api/login", "/api/logout"):
                    return self._login(url.path == "/api/login")
                user = self._user()
                if user is None:
                    return self._refuse(401, "로그인하지 않아 요청을 처리하지 못했습니다. 로그인해 주세요.")
                need = NEEDS.get(url.path[5:], "viewer")
                if not user.may(need):
                    return self._refuse(403, f"{user.name} 님의 권한으로는 이 작업을 할 수 없어 처리하지 못했습니다. "
                                             "권한이 있는 사람에게 요청해 주세요.")
            if url.path == "/api/upload":  # the file itself is the body; its name rides in the query
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
                return self._api("POST", "upload", {"name": q.get("name", ""), "data": self.rfile.read(n)})
            try:
                body = self._body()
            except (ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"error": str(e)})
            self._api("POST", url.path[5:], body)

        def _login(self, signing_in: bool) -> None:
            if not signing_in:
                try:
                    self._body()  # read what was sent, so the client is not cut off while it sends
                except ValueError:
                    pass
                logins.sign_out(self._token())
                return self._json(200, {"ok": True}, extra={"Set-Cookie": f"{LOGIN}=; Path=/; HttpOnly; "
                                                                          f"SameSite=Strict; Max-Age=0{self._secure()}"})
            if not logins.allow_try(self._client()):
                return self._refuse(429, "로그인 시도가 분당 한도를 초과해 처리하지 못했습니다. 1분 뒤 다시 시도해 주세요.")
            try:
                body = self._body()
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            hit = logins.sign_in(str(body.get("user", "")), str(body.get("password", "")))
            if hit is None:
                return self._json(401, {"error": "아이디 또는 비밀번호가 맞지 않아 로그인하지 못했습니다. 다시 입력해 주세요."})
            token, u = hit
            cookie = f"{LOGIN}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200{self._secure()}"
            return self._json(200, {"ok": True, "user": {"id": u.id, "name": u.name, "roles": u.roles}},
                              extra={"Set-Cookie": cookie})

        def _api(self, method: str, route: str, a: dict) -> None:
            sid, s, new = self._session()
            user = self._user()
            try:
                with s.lock:
                    if user is not None:
                        s.who = user.name
                    out = self._route(method, route, a, s, sid)
            except LookupError as e:
                return self._json(400, {"error": f"요청한 항목을 찾을 수 없습니다. {e}"}, sid=sid, new=new)
            except PermissionError as e:
                return self._json(403, {"error": str(e)}, sid=sid, new=new)
            except ValueError as e:  # what a visitor sent does not fit: a file, a limit, an empty draft
                return self._json(400, {"error": str(e)}, sid=sid, new=new)
            except Exception as e:
                return self._json(500, {"error": f"{type(e).__name__}: {e}"}, sid=sid, new=new)
            if isinstance(out, tuple):
                code, data, ctype, name = out
                return self._send(code, data, ctype, sid=sid, new=new,
                                  extra={"Content-Disposition": f'attachment; filename="{name}"'})
            if out is None:
                return self._json(404, {"error": "요청한 주소를 찾을 수 없습니다."}, sid=sid, new=new)
            self._json(200, out, sid=sid, new=new)

        def _route(self, method: str, route: str, a: dict, s: StudioSession, sid: str):
            role = str(a.get("role") or "")
            principal = a.get("principal") if isinstance(a.get("principal"), dict) else None
            if method == "GET":
                if route == "state":
                    return s.state()
                if route == "object":
                    return s.object(a["name"])
                if route == "keys":
                    return {"keys": s.keys(a["type"])}
                if route == "audit":
                    return {"audit": s.audit()}
                if route == "files":
                    return s.files_state()
                if route == "module":
                    return s.module_source(a["name"])
                if route == "export/module":
                    return (200, s.export_module(a["name"]).encode("utf-8"), "application/yaml; charset=utf-8",
                            f"{a['name']}.yaml")
                if route == "manage":
                    return s.manage_state()
                if route == "flow":
                    return s.flow()
                if route == "flow/settings":
                    return s.flow_settings()
                if route == "changes":
                    return s.changes_state()
                if route == "agreement":
                    return s.agreement()
                if route == "identities":
                    return s.identities()
                if route == "standards":
                    return s.standards()
                if route == "export/owl":
                    return 200, s.export_owl().encode("utf-8"), "text/turtle; charset=utf-8", "ontology.ttl"
                if route == "export/jdm":
                    from xgen_data_studio.decide.zen import to_jdm

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
                return s.run_query(a["name"], a.get("params") or {}, role=role, principal=principal)
            if route == "text":
                return s.run_text(str(a.get("language", "sparql")), str(a.get("text", "")), role=role,
                                  principal=principal)
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
                return s.decide(a["name"], str(a["key"]))
            if route == "request":
                return s.request(a["action"], str(a["key"]), a.get("params") or {}, role)
            if route == "approve":
                return s.approve(str(a["id"]), bool(a.get("approve", True)))
            if route == "questions":
                return s.questions()
            if route == "bindings":
                return s.bindings()
            if route == "upload":
                return s.upload(str(a["name"]), a["data"])
            if route == "files/remove":
                return s.remove_file(str(a.get("name", "")))
            if route == "files/sample":
                return s.use_samples()
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
            if route == "manage/discard":
                return s.manage_discard()
            if route == "manage/propose":
                return s.manage_propose()
            if route == "change/decide":
                return s.decide_change(str(a.get("id", "")), bool(a.get("approve", True)), str(a.get("reason", "")))
            if route == "flow/save":
                return s.save_flow(a.get("settings") if isinstance(a.get("settings"), dict) else {})
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


def serve(build: Callable[[], StudioSession], *, host: str = "127.0.0.1", port: int = 7710, limit: int = 24,
          idle: float = 3600, ask_per_minute: int = 20, quiet: bool = False, data: DataOptions | None = None,
          video: Path | None = None, users: Path | None = None, sync: float = 0) -> None:
    """Serve the page: a studio per visitor, or with `users` one shared studio for a team that signs in."""
    from xgen_data_studio.web.team import Logins, Syncer, TeamSessions, Users

    logins = Logins(Users.load(users)) if users else None
    sessions = TeamSessions(build, logins) if logins else Sessions(build, limit=limit, idle=idle)
    httpd = ThreadingHTTPServer((host, port), make_handler(sessions, ask_limit=RateLimit(ask_per_minute),
                                                           quiet=quiet, upload_max=(data or DataOptions()).file_bytes,
                                                           video=video, logins=logins))
    httpd.daemon_threads = True
    if sync:
        Syncer(sessions, sync).start()
    print(f"xgen-data-studio on http://{host}:{port}" + (" (team)" if logins else ""), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
