import json
import shutil
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from xgen_space.web.team import Users, check_password, hash_password

from .conftest import EXAMPLE, LIB


def test_passwords_are_salted_and_checked_in_constant_form():
    a, b = hash_password("correct horse"), hash_password("correct horse")
    assert a != b and a.startswith("pbkdf2_sha256$") and check_password("correct horse", a)
    assert not check_password("wrong horse", a) and not check_password("x", "not-a-hash")


@pytest.fixture
def team(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.library import Library
    from xgen_space.web.api import StudioSession
    from xgen_space.web.server import RateLimit, make_handler
    from xgen_space.web.team import Logins, TeamSessions

    root = tmp_path / "examples"
    shutil.copytree(EXAMPLE, root / "commerce")
    shutil.copytree(LIB, root / "library")
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
        headers["X-XSPACE-Request"] = "1"
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


def test_a_teams_api_answers_from_the_studio_the_team_works_in(team):
    from xgen_space.rest import Rest
    from xgen_space.tools import StudioTools

    base, _, sessions = team
    shared = sessions.shared
    rest = Rest(StudioTools(shared.studio, actor_id="api"), "t", source=lambda: shared.studio, lock=shared.lock)
    ask = {"decision": "returnEligibility", "key": "I1001"}
    assert "14일" in rest.answer("POST", "/v1/decide", ask)[1]["outputs"]["reason"]
    kim, lee = _login(base, "kim", "kim-password-1"), _login(base, "lee", "lee-password-1")
    src = _call(base, "/api/module?name=acme-overlay", cookie=kim)[1]["yaml"]
    cid = _call(base, "/api/module/save", {"text": src.replace("14일까지", "21일까지")}, cookie=kim)[1]["change"]["id"]
    assert "14일" in rest.answer("POST", "/v1/decide", ask)[1]["outputs"]["reason"]  # asked, not approved
    assert _call(base, "/api/change/decide", {"id": cid}, cookie=lee)[1]["ok"]
    assert "21일" in rest.answer("POST", "/v1/decide", ask)[1]["outputs"]["reason"]


def test_a_request_from_outside_waits_where_a_person_finds_it(team):
    from xgen_space.rest import Rest
    from xgen_space.tools import StudioTools

    base, _, sessions = team
    shared = sessions.shared
    agent = StudioTools(shared.studio, role="customer_agent", principal={"customer_id": "C001"}, actor_id="api")
    rest = Rest(agent, "t", source=lambda: shared.studio, lock=shared.lock)
    code, out = rest.answer("POST", "/v1/actions", {"action": "requestReturn", "key": "I1001", "params": {"reason": "사이즈"}})
    assert code == 200 and out["status"] == "pending"
    lee = _login(base, "lee", "lee-password-1")
    waiting = _call(base, "/api/actions/pending", cookie=lee)[1]["pending"]
    assert [(p["id"], p["key"], p["requested_kind"]) for p in waiting] == [(out["id"], "I1001", "agent")]
    assert _call(base, "/api/approve", {"id": out["id"], "approve": True}, cookie=lee)[1]["ok"]
    assert _call(base, "/api/actions/pending", cookie=lee)[1]["pending"] == []


def test_what_the_management_screens_approved_comes_back_with_the_studio(team):
    from xgen_space.config import load_studio

    _, root, _ = team
    home = root / "library" / "workspace"
    home.mkdir()
    (home / "0.1.0.yaml").write_text("""module: workspace
version: 0.1.0
kind: customer
label: 관리 변경
requires: [commerce]
extend:
  objects:
    Customer:
      properties:
        nickname: {type: string, label: 별명, column: name}
""", encoding="utf-8")
    assert "nickname" in load_studio(root / "library" / "studio.yaml").onto.objects["Customer"].properties


def test_a_running_agent_goes_by_a_change_once_it_reaches_the_library(team):
    pytest.importorskip("mcp")
    from xgen_space.config import load_studio
    from xgen_space.mcp_server import following
    from xgen_space.tools import StudioTools

    _, root, _ = team
    config = root / "library" / "studio.yaml"
    first = load_studio(config)
    current = following(config, first)
    assert current() is first
    home = root / "library" / "acme-overlay"
    text = (home / "1.0.0.yaml").read_text(encoding="utf-8")
    (home / "1.0.1.yaml").write_text(text.replace("version: 1.0.0", "version: 1.0.1").replace("14일까지", "21일까지"), encoding="utf-8")
    assert "21일" in StudioTools(current()).decide("returnEligibility", "I1001")["outputs"]["reason"]
    (home / "1.0.2.yaml").write_text("module: [", encoding="utf-8")
    kept = current()  # a broken file leaves the rules in force
    assert "21일" in StudioTools(kept).decide("returnEligibility", "I1001")["outputs"]["reason"]


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


def test_an_editor_files_management_edits_and_an_approver_applies_them(team):
    base, root, _ = team
    kim, lee, park = (_login(base, u, f"{u}-password-1") for u in ("kim", "lee", "park"))
    edit = {"op": "update_object", "args": {"name": "Customer", "label": "회원"}}
    assert _call(base, "/api/manage/edit", edit, cookie=park)[0] == 403  # a viewer reads the screens only
    assert _call(base, "/api/manage", cookie=park)[0] == 200
    code, out, _ = _call(base, "/api/manage/edit", edit, cookie=kim)
    assert code == 200 and out["workspace"]["dirty"]
    code, out, _ = _call(base, "/api/manage/edit", {"op": "delete_property", "args": {"object": "Customer",
                                                                                      "name": "name"}}, cookie=kim)
    assert code == 400 and "상위 객체" in out["error"]
    code, out, _ = _call(base, "/api/manage/propose", {}, cookie=kim)
    assert code == 200 and out["pending"] and out["change"]["module"] == "workspace"
    assert not out["workspace"]["dirty"]  # filed: the request holds the edits now
    code, out, _ = _call(base, "/api/change/decide", {"id": out["change"]["id"]}, cookie=lee)
    assert code == 200 and out["ok"]
    state = _call(base, "/api/manage", cookie=park)[1]
    assert next(o for o in state["objects"] if o["name"] == "Customer")["label"] == "회원"
    assert (root / "library" / "workspace" / "0.1.0.yaml").is_file()
