"""The studio page over HTTP: one studio per visitor, built from a studio file, dropped after a while."""
from __future__ import annotations

import hashlib
import json
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
from xgen_data_studio.web.api import StudioSession

STATIC = Path(__file__).parent / "static"
COOKIE = "xds_session"
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


def make_handler(sessions: Sessions, *, ask_limit: RateLimit, quiet: bool = False):
    body_html = page()
    etag = hashlib.sha256(body_html).hexdigest()[:16]

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

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("요청 본문이 64KB 한도를 넘었습니다.")
            raw = self.rfile.read(n) if n else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(data, dict):
                raise ValueError("요청 본문은 JSON 객체여야 합니다.")
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
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "없는 주소입니다."})
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            self._api("GET", url.path[5:], q)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if not url.path.startswith("/api/"):
                return self._json(404, {"error": "없는 주소입니다."})
            try:
                body = self._body()
            except (ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"error": str(e)})
            self._api("POST", url.path[5:], body)

        def _api(self, method: str, route: str, a: dict) -> None:
            sid, s, new = self._session()
            try:
                with s.lock:
                    out = self._route(method, route, a, s, sid)
            except LookupError as e:
                return self._json(400, {"error": f"찾을 수 없는 이름입니다. {e}"}, sid=sid, new=new)
            except PermissionError as e:
                return self._json(403, {"error": str(e)}, sid=sid, new=new)
            except Exception as e:
                return self._json(500, {"error": f"{type(e).__name__}: {e}"}, sid=sid, new=new)
            if isinstance(out, tuple):
                code, data, ctype, name = out
                return self._send(code, data, ctype, sid=sid, new=new,
                                  extra={"Content-Disposition": f'attachment; filename="{name}"'})
            if out is None:
                return self._json(404, {"error": "없는 주소입니다."}, sid=sid, new=new)
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
                    return {"ok": False, "error": "질문 요청이 분당 한도에 도달했습니다. 잠시 뒤에 다시 시도해 주세요."}
                return s.ask(str(a.get("question", "")), role=role, principal=principal)
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
            if route == "reset":
                sessions.reset(sid)
                return {"ok": True}
            return None

    return Handler


def serve(build: Callable[[], StudioSession], *, host: str = "127.0.0.1", port: int = 7710, limit: int = 24,
          idle: float = 3600, ask_per_minute: int = 20, quiet: bool = False) -> None:
    sessions = Sessions(build, limit=limit, idle=idle)
    httpd = ThreadingHTTPServer((host, port), make_handler(sessions, ask_limit=RateLimit(ask_per_minute),
                                                           quiet=quiet))
    httpd.daemon_threads = True
    print(f"xgen-data-studio on http://{host}:{port}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
