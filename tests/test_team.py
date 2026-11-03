import json
import shutil
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from xgen_data_studio.web.team import Users, check_password, hash_password

from .conftest import EXAMPLE


def test_passwords_are_salted_and_checked_in_constant_form():
    a, b = hash_password("correct horse"), hash_password("correct horse")
    assert a != b and a.startswith("pbkdf2_sha256$") and check_password("correct horse", a)
    assert not check_password("wrong horse", a) and not check_password("x", "not-a-hash")


@pytest.fixture
def team(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_data_studio.config import load_studio
    from xgen_data_studio.library import Library
    from xgen_data_studio.web.api import StudioSession
    from xgen_data_studio.web.server import RateLimit, make_handler
    from xgen_data_studio.web.team import Logins, TeamSessions

    root = tmp_path / "examples"
    shutil.copytree(EXAMPLE, root / "commerce")
    shutil.copytree(EXAMPLE.parent / "library", root / "library")
    users = Users.load(tmp_path / "users.yaml")
    users.add("kim", "kim-password-1", name="김", roles=["editor"])
    users.add("lee", "lee-password-1", name="이", roles=["approver"])
    users.add("park", "park-password-1", name="박", roles=["viewer"])
    config = root / "library" / "studio.yaml"

    def build():
        s = StudioSession(load_studio(config))
        s.store = Library(root / "library")
        s._adopt(s.studio)
        return s

    sessions = TeamSessions(build, Logins(Users.load(tmp_path / "users.yaml")))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(sessions, ask_limit=RateLimit(5), quiet=True,
                                                               logins=sessions.logins))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", root, sessions
    httpd.shutdown()
    httpd.server_close()


def _call(base, path, body=None, cookie="", header=True):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if header and data is not None:
        headers["X-XDS-Request"] = "1"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read()), r.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), e.headers


def _login(base, user, password):
    code, body, h = _call(base, "/api/login", {"user": user, "password": password})
    assert code == 200, body
    cookie = h["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    return cookie.split(";", 1)[0]


def test_a_team_signs_in_and_works_in_one_studio_by_role(team):
    base, root, sessions = team
    assert _call(base, "/api/state")[0] == 401
    assert _call(base, "/api/me")[1] == {"team": True, "user": None}
    assert _call(base, "/api/login", {"user": "kim", "password": "nope-nope-1"})[0] == 401
    kim, lee, park = (_login(base, u, f"{u}-password-1") for u in ("kim", "lee", "park"))
    assert _call(base, "/api/me", cookie=kim)[1]["user"]["name"] == "김"
    # a write without the page's own header is refused: another site cannot send it in the user's name
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=kim, header=False)[0] == 403
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=park)[0] == 403  # viewer
    code, out, _ = _call(base, "/api/detach", {"name": "fashion"}, cookie=kim)
    assert code == 200 and out["ok"]
    state = _call(base, "/api/state", cookie=park)[1]  # the viewer sees the editor's change: one studio
    assert "fashion" not in {r["name"] for r in state["library"] if r["on"]}

    src = _call(base, "/api/module?name=acme-overlay", cookie=kim)[1]["yaml"]
    code, out, _ = _call(base, "/api/module/save", {"text": src.replace("<= 14", "<= 12")}, cookie=kim)
    assert code == 200 and out["pending"] and out["change"]["version"] == "1.0.1"
    cid = out["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": cid}, cookie=kim)[0] == 403  # editor cannot approve
    code, out, _ = _call(base, "/api/change/decide", {"id": cid}, cookie=lee)
    assert code == 200 and out["ok"] and out["change"]["decided_by"] == "이"
    assert (root / "library" / "acme-overlay" / "1.0.1.yaml").is_file()  # --library-write keeps it
    assert _call(base, "/api/flow/save", {"settings": {}}, cookie=lee)[0] == 403  # admin only
    assert _call(base, "/api/logout", {}, cookie=kim)[0] == 200
    assert _call(base, "/api/state", cookie=kim)[0] == 401


def test_sign_in_attempts_are_limited(team):
    base, _, _ = team
    codes = [_call(base, "/api/login", {"user": "kim", "password": "bad-guess-00"})[0] for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_a_visitor_who_proposes_a_change_may_approve_it_alone_but_a_team_may_not(team):
    _, _, sessions = team
    s = sessions.shared
    assert s.studio.changes.self_approve is False
    with s.lock:
        s.who = "김"
        src = s.module_source("acme-overlay")["yaml"]
        cid = s.propose_module(src.replace("<= 14", "<= 13"))["change"]["id"]
        out = s.decide_change(cid, True)
    assert not out["ok"] and "다른 승인자" in out["error"]
