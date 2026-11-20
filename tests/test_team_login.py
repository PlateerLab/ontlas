"""How a team signs in: the users file and its policy, locking, a second step, passwords an admin gives, staying signed
in across a restart, devices, the first admin, asking to join, allowed addresses, and the audit log of it all."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from ontlas.web.team import POLICY, Logins, Refused, User, Users, hash_password, totp_code

pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class Clock:
    def __init__(self, at: float = 1_800_000_000.0):
        self.at = at

    def __call__(self) -> float:
        return self.at


def people(path: Path, **policy) -> Users:
    users = Users.load(path)
    users.policy.update(policy)
    users.add("root1", "root-password-1", name="관리 하나", roles=["admin"])
    users.add("kim", "kim-password-1", name="김", roles=["editor"])
    return users


def logins_at(path: Path, **policy) -> tuple[Logins, Clock]:
    logins, clock = Logins(people(path, **policy)), Clock()
    logins.clock = clock
    return logins, clock


# ---- the users file --------------------------------------------------------------------------------------------------

def test_a_users_file_from_before_reads_with_the_defaults_and_is_written_whole(tmp_path):
    path = tmp_path / "users.yaml"
    path.write_text("users:\n  kim: {name: 김, password: '%s', roles: [editor]}\n" % hash_password("kim-password-1"), encoding="utf-8")
    users = Users.load(path)
    kim = users.users["kim"]
    assert (kim.state, kim.email, kim.must_change, kim.previous, kim.totp, kim.failures, kim.locked_until) == ("active", "", False, [], "", 0, "")
    assert users.policy == POLICY and users.verify("kim", "kim-password-1")
    kim.email = "kim@example.com"
    users.policy["lock_after"] = 7
    users.save()
    again = Users.load(path)
    assert again.users["kim"].email == "kim@example.com" and again.policy["lock_after"] == 7 and again.policy["keep_days"] == 14
    assert not list(tmp_path.glob("*.tmp"))  # written beside itself and put in its place
    with pytest.raises(ValueError, match="state"):
        path.write_text("users:\n  kim: {name: 김, password: x, roles: [editor], state: gone}\n", encoding="utf-8")
        Users.load(path)


def test_a_cli_add_on_someone_there_gives_a_new_password_and_lets_them_in(tmp_path):
    users = people(tmp_path / "users.yaml")
    kim = users.users["kim"]
    kim.state, kim.failures, kim.locked_until, kim.email = "disabled", 5, "2099-01-01T00:00:00", "kim@example.com"
    users.add("kim", "kim-password-2", name="김", roles=["editor"])
    again = Users.load(tmp_path / "users.yaml").users["kim"]
    assert (again.state, again.failures, again.locked_until, again.email) == ("active", 0, "", "kim@example.com")
    assert len(again.previous) == 1 and again.must_change is False


# ---- signing in ----------------------------------------------------------------------------------------------------

def test_five_wrong_passwords_lock_an_account_for_the_policys_minutes(tmp_path):
    logins, clock = logins_at(tmp_path / "users.yaml")
    for n in range(1, 5):
        with pytest.raises(Refused) as e:
            logins.begin("kim", "wrong-password")
        assert e.value.code == 401 and e.value.said == {"failures": n, "lock_after": 5} and f"(실패 {n}/5)" in str(e.value)
    with pytest.raises(Refused) as e:
        logins.begin("kim", "wrong-password")  # the fifth: locked at once
    assert e.value.code == 423 and "5회 실패해 계정이 잠겼습니다" in str(e.value) and e.value.said["locked_until"]
    with pytest.raises(Refused) as e:
        logins.begin("kim", "kim-password-1")  # the right one waits too
    assert e.value.code == 423
    assert Users.load(tmp_path / "users.yaml").users["kim"].failures == 5  # a restart keeps the lock
    clock.at += 15 * 60 - 1
    with pytest.raises(Refused):
        logins.begin("kim", "kim-password-1")
    clock.at += 2
    out = logins.begin("kim", "kim-password-1")
    assert out["user"].id == "kim" and logins.users.users["kim"].failures == 0 and logins.users.users["kim"].locked_until == ""


def test_a_name_nobody_has_is_answered_as_a_wrong_password(tmp_path):
    logins, _ = logins_at(tmp_path / "users.yaml")
    with pytest.raises(Refused) as e:
        logins.begin("nobody", "whatever-1")
    assert e.value.code == 401 and e.value.said == {"failures": 1, "lock_after": 5}
    assert "nobody" not in logins.users.users and not (tmp_path / "users.yaml").read_text(encoding="utf-8").count("nobody")


def test_an_email_signs_in_where_one_person_alone_has_it(tmp_path):
    logins, _ = logins_at(tmp_path / "users.yaml")
    logins.users.users["kim"].email = "Kim@Example.com"
    assert logins.begin("kim@example.com", "kim-password-1")["user"].id == "kim"
    logins.users.users["root1"].email = "kim@example.com"  # two have it: neither is signed in by it
    with pytest.raises(Refused) as e:
        logins.begin("kim@example.com", "kim-password-1")
    assert e.value.code == 401


def test_a_disabled_or_waiting_account_is_refused_once_its_password_is_right(tmp_path):
    logins, _ = logins_at(tmp_path / "users.yaml")
    kim = logins.users.users["kim"]
    kim.state = "disabled"
    with pytest.raises(Refused) as e:
        logins.begin("kim", "kim-password-1")
    assert (e.value.code, e.value.said) == (403, {"state": "disabled"}) and "사용이 중지된 계정이라" in str(e.value)
    with pytest.raises(Refused) as e:
        logins.begin("kim", "wrong-password")  # a wrong password is said as wrong: the state is not given away
    assert e.value.code == 401
    kim.state = "pending"
    with pytest.raises(Refused) as e:
        logins.begin("kim", "kim-password-1")
    assert (e.value.code, e.value.said) == (403, {"state": "pending"}) and "관리자 승인 전이라" in str(e.value)


def test_a_code_from_the_authenticator_is_the_second_step_and_is_used_once(tmp_path):
    logins, clock = logins_at(tmp_path / "users.yaml")
    kim = logins.users.users["kim"]
    kim.totp = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    out = logins.begin("kim", "kim-password-1")
    assert set(out) == {"step", "ticket"} and out["step"] == "code"
    with pytest.raises(Refused) as e:
        logins.go_on(out["ticket"], {"code": "000000" if totp_code(kim.totp, int(clock.at // 30)) != "000000" else "111111"})
    assert e.value.code == 401 and e.value.said["failures"] == 1 and "인증 코드가" in str(e.value)
    code = totp_code(kim.totp, int(clock.at // 30) - 1)  # a step behind: a phone's clock a little slow
    signed = logins.go_on(out["ticket"], {"code": code})
    assert signed["user"].id == "kim" and logins.user(signed["token"]) is kim and kim.failures == 0
    with pytest.raises(Refused) as e:
        logins.go_on(out["ticket"], {"code": code})  # the ticket is spent
    assert e.value.said.get("expired")
    again = logins.begin("kim", "kim-password-1")
    with pytest.raises(Refused):
        logins.go_on(again["ticket"], {"code": code})  # the same code again
    clock.at += 30
    assert "token" in logins.go_on(again["ticket"], {"code": totp_code(kim.totp, int(clock.at // 30))})
    late = logins.begin("kim", "kim-password-1")
    clock.at += 301
    with pytest.raises(Refused) as e:
        logins.go_on(late["ticket"], {"code": totp_code(kim.totp, int(clock.at // 30))})
    assert e.value.code == 401 and e.value.said == {"expired": True}


def test_where_the_policy_asks_for_a_second_step_one_without_it_sets_it_up_while_signing_in(tmp_path):
    logins, clock = logins_at(tmp_path / "users.yaml", two_factor=True)
    out = logins.begin("kim", "kim-password-1")
    assert out["step"] == "enroll" and out["uri"] == f"otpauth://totp/Ontlas:kim?secret={out['secret']}&issuer=Ontlas"
    with pytest.raises(Refused):
        logins.go_on(out["ticket"], {"code": totp_code(out["secret"], int(clock.at // 30)), "secret": "OTHERSECRET"})
    out = logins.begin("kim", "kim-password-1")
    signed = logins.go_on(out["ticket"], {"code": totp_code(out["secret"], int(clock.at // 30)), "secret": out["secret"]})
    assert "token" in signed and Users.load(tmp_path / "users.yaml").users["kim"].totp == out["secret"]
    assert logins.begin("kim", "kim-password-1")["step"] == "code"  # from now on it is asked


def test_a_password_an_admin_gave_is_changed_before_going_in_and_not_to_a_recent_one(tmp_path):
    logins, _ = logins_at(tmp_path / "users.yaml")
    users, kim = logins.users, logins.users.users["kim"]
    for p in ("kim-password-2", "kim-password-3"):  # kim-password-1 .. 3 were Kim's own
        users.set_password(kim, p)
    users.set_password(kim, "temporary-pass-1", must_change=True)
    users.save()
    assert logins.sign_in("kim", "temporary-pass-1") is None  # a step still to go
    out = logins.begin("kim", "temporary-pass-1")
    assert out["step"] == "password" and out["password_min"] == 8
    for bad, said in (("short", "짧아"), ("temporary-pass-1", "현재 비밀번호와 같아"), ("kim-password-3", "최근에 쓴"),
                      ("kim-password-1", "최근에 쓴")):
        with pytest.raises(ValueError, match=said):
            logins.go_on(out["ticket"], {"new_password": bad})
    signed = logins.go_on(out["ticket"], {"new_password": "kim-password-9"})  # the same ticket, after what was refused
    again = Users.load(tmp_path / "users.yaml").users["kim"]
    assert "token" in signed and not again.must_change and len(again.previous) == 3
    assert logins.sign_in("kim", "kim-password-9") is not None


# ---- staying signed in --------------------------------------------------------------------------------------------

def test_a_sign_in_outlives_a_restart_and_only_its_hash_is_written(tmp_path):
    logins, _ = logins_at(tmp_path / "users.yaml")
    token, _ = logins.sign_in("kim", "kim-password-1", ip="10.0.0.5", agent="Chrome · Windows")
    kept = (tmp_path / "users.logins.json").read_text(encoding="utf-8")
    assert token not in kept and Logins.key(token) in kept
    again = Logins(Users.load(tmp_path / "users.yaml"))
    assert again.user(token).id == "kim"
    assert again.devices("kim", again.device(token)) == [{"id": again.device(token), "agent": "Chrome · Windows", "ip": "10.0.0.5",
                                                          "at": again.devices("kim")[0]["at"], "seen": again.devices("kim")[0]["seen"],
                                                          "current": True}]
    assert again.sign_out(token) is not None and Logins(Users.load(tmp_path / "users.yaml")).user(token) is None


def test_how_long_a_sign_in_lasts_follows_the_policy(tmp_path):
    logins, clock = logins_at(tmp_path / "users.yaml")
    short = logins.begin("kim", "kim-password-1")
    kept = logins.begin("kim", "kim-password-1", keep=True)
    assert not short["keep"] and kept["keep"]
    clock.at += 12 * 3600 + 1
    assert logins.user(short["token"]) is None and logins.user(kept["token"]) is not None
    clock.at += 14 * 86400
    assert logins.user(kept["token"]) is None
    logins.users.policy["keep_days"] = 0  # staying signed in turned off: asked for, it is a session's length
    assert logins.begin("kim", "kim-password-1", keep=True)["keep"] is False


def test_a_disabled_account_is_signed_out_at_once(tmp_path):
    logins, _ = logins_at(tmp_path / "users.yaml")
    token, kim = logins.sign_in("kim", "kim-password-1")
    kim.state = "disabled"
    assert logins.user(token) is None


# ---- through the server ----------------------------------------------------------------------------------------------

@pytest.fixture()
def server(tmp_path):
    """A team's server on SHOP keeping a journal, with a users file that may start empty: start(users) runs it."""
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import routes
    from ontlas.web.api import StudioSession
    from ontlas.web.server import RateLimit, make_handler
    from ontlas.web.team import TeamSessions

    said = dict(routes.SERVER)
    running: list = []

    def start(users: Users):
        if running:
            running[-1].shutdown()
            running[-1].server_close()

        def build():
            studio = load_studio(SHOP)
            studio.keep_journal(tmp_path / "journal.jsonl")
            return StudioSession(studio)

        sessions = TeamSessions(build, Logins(users))
        sessions.logins.allow_try = lambda ip, per_minute=10: True  # the limit an address has is test_team's
        routes.SERVER.clear()
        routes.SERVER.update(logins=sessions.logins, sessions=sessions)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(sessions, ask_limit=RateLimit(5), quiet=True, logins=sessions.logins))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        running.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}", sessions.logins

    yield start, tmp_path
    if running:
        running[-1].shutdown()
        running[-1].server_close()
    routes.SERVER.clear()
    routes.SERVER.update(said)
    routes.asking()


def call(base, path, body=None, cookie="", ip="", agent=CHROME):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "X-Ontlas-Request": "1", "User-Agent": agent}
    if cookie:
        headers["Cookie"] = cookie
    if ip:
        headers["X-Forwarded-For"] = ip
    req = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read()), r.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers.get("Set-Cookie", "")


def sign_in(base, user, password, keep=False, ip="", agent=CHROME):
    code, out, cookie = call(base, "/api/login", {"user": user, "password": password, "keep": keep}, ip=ip, agent=agent)
    assert code == 200 and out["ok"], out
    return cookie.split(";", 1)[0], cookie


def test_staying_signed_in_is_a_cookie_kept_for_the_policys_days(server):
    start, tmp = server
    base, _ = start(people(tmp / "users.yaml"))
    _, short = sign_in(base, "kim", "kim-password-1")
    _, kept = sign_in(base, "kim", "kim-password-1", keep=True)
    assert "Max-Age" not in short and "HttpOnly" in short and "SameSite=Strict" in short
    assert "Max-Age=1209600" in kept


def test_the_first_admin_is_made_with_the_code_the_server_showed(server, capsys):
    start, tmp = server
    base, logins = start(Users.load(tmp / "users.yaml"))  # nobody yet
    code = logins.setup_code()
    assert code in capsys.readouterr().err and (tmp / "users.setup").read_text(encoding="utf-8").strip() == code
    me = call(base, "/api/me")[1]
    assert me == {"team": True, "user": None, "setup": True, "signup": False, "password_min": 8, "keep_days": 14, "model": False}
    assert call(base, "/api/signup", {"id": "hong", "email": "hong@example.com", "password": "hong-password-1"})[0] == 409
    first = {"code": code.lower().replace("-", " "), "id": "admin", "name": "관리자", "password": "admin-password-1", "email": "admin@example.com"}
    status, out, _ = call(base, "/api/setup", {**first, "code": "WRONGCODE-1234567"})
    assert status == 403 and "설치 코드가 맞지 않아" in out["error"]
    assert call(base, "/api/setup", {**first, "password": "short"})[0] == 400
    status, out, cookie = call(base, "/api/setup", first)
    assert status == 200 and out["user"] == {"id": "admin", "name": "관리자", "roles": ["admin"]} and "ontlas_login=" in cookie
    cookie = cookie.split(";", 1)[0]
    assert call(base, "/api/me", cookie=cookie)[1]["user"]["id"] == "admin" and not (tmp / "users.setup").exists()
    assert call(base, "/api/setup", {**first, "id": "admin2"})[0] == 409  # once
    assert call(base, "/api/me")[1] == {"team": True, "user": None, "setup": False, "signup": True, "password_min": 8,
                                  "keep_days": 14}
    assert not Users.load(tmp / "users.yaml").users["admin"].must_change
    rows = call(base, "/api/admin/audit", cookie=cookie)[1]["rows"]
    assert any(r["kind"] == "login" and r["text"] == "최초 설치 · 시스템 관리자 관리자(admin) 생성" and r["ip"] == "127.0.0.1" for r in rows)


def test_one_who_asks_to_join_waits_for_an_admin(server):
    start, tmp = server
    base, _ = start(people(tmp / "users.yaml"))
    ask = {"id": "hong", "name": "홍길동", "email": "hong@example.com", "password": "hong-password-1"}
    for wrong, said in (({"id": "a b"}, "아이디 형식"), ({"id": "kim"}, "이미 있어"), ({"email": ""}, "이메일이 없어"),
                        ({"email": "hong"}, "이메일 형식"), ({"password": "short"}, "짧아")):
        status, out, _ = call(base, "/api/signup", {**ask, **wrong})
        assert status == 400 and said in out["error"], out
    assert call(base, "/api/signup", ask)[1] == {"ok": True, "pending": True}
    status, out, _ = call(base, "/api/signup", {**ask, "id": "hong2"})
    assert status == 400 and "이미 등록되어" in out["error"]
    status, out, _ = call(base, "/api/login", {"user": "hong@example.com", "password": "hong-password-1"})
    assert status == 403 and out["state"] == "pending"
    root, _ = sign_in(base, "root1", "root-password-1")
    listed = call(base, "/api/admin/users", cookie=root)[1]
    assert listed["counts"]["pending"] == 1 and next(u for u in listed["users"] if u["id"] == "hong")["state"] == "pending"
    status, out, _ = call(base, "/api/admin/user/approve", {"id": "hong", "roles": ["editor"]}, cookie=root)
    assert status == 200 and out["counts"]["pending"] == 0
    assert call(base, "/api/admin/user/approve", {"id": "hong"}, cookie=root)[0] == 400  # once
    hong, _ = sign_in(base, "hong", "hong-password-1")
    assert call(base, "/api/me", cookie=hong)[1]["user"]["roles"] == ["editor"]
    assert call(base, "/api/signup", {"id": "lee", "email": "lee@example.com", "password": "lee-password-1"})[0] == 200  # no name: the id
    assert call(base, "/api/admin/user/reject", {"id": "lee"}, cookie=root)[0] == 200 and "lee" not in Users.load(tmp / "users.yaml").users
    texts = [r["text"] for r in call(base, "/api/admin/audit", cookie=root)[1]["rows"] if r["kind"] == "user"]
    assert {"회원가입 신청 · 홍길동(hong)", "가입 승인 · 사용자 홍길동(hong) · 역할 편집자", "가입 거절 · 사용자 lee(lee)"} <= set(texts)
    policy = call(base, "/api/admin/security", cookie=root)[1]["policy"]
    assert call(base, "/api/admin/security/save", {"policy": {**policy, "signup": False}}, cookie=root)[0] == 200
    status, out, _ = call(base, "/api/signup", {**ask, "id": "park", "email": "park@example.com"})
    assert status == 403 and "회원가입을 받지 않는" in out["error"] and call(base, "/api/me")[1]["signup"] is False


def test_an_admin_locks_out_unlocks_resets_a_second_step_and_stops_an_account(server):
    start, tmp = server
    users = people(tmp / "users.yaml")
    users.users["kim"].totp = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    base, logins = start(users)
    root, _ = sign_in(base, "root1", "root-password-1")
    for _ in range(5):
        status, out, _ = call(base, "/api/login", {"user": "kim", "password": "wrong-password"})
    assert status == 423 and "locked_until" in out
    row = next(u for u in call(base, "/api/admin/users", cookie=root)[1]["users"] if u["id"] == "kim")
    assert row["locked"] and row["locked_until"] and row["two_factor"]
    counts = call(base, "/api/admin/user/unlock", {"id": "kim"}, cookie=root)[1]["counts"]
    assert counts["locked"] == 0 and counts["two_factor"] == 1
    assert call(base, "/api/admin/user/unlock", {"id": "kim"}, cookie=root)[0] == 400  # not locked now
    assert call(base, "/api/login", {"user": "kim", "password": "kim-password-1"})[1]["step"] == "code"
    assert call(base, "/api/admin/user/2fa/reset", {"id": "kim"}, cookie=root)[1]["counts"]["two_factor"] == 0
    kim, _ = sign_in(base, "kim", "kim-password-1")
    # a temporary password: Kim is signed out and sets a new one at the next sign-in
    edit = {"id": "kim", "name": "김", "roles": ["editor"], "password": "temporary-pass-1", "new": False, "email": "kim@example.com",
            "employee_no": "E-001", "note": "외부 자문"}
    out = call(base, "/api/admin/user/save", edit, cookie=root)[1]
    row = next(u for u in out["users"] if u["id"] == "kim")
    assert row["must_change"] and (row["email"], row["employee_no"], row["note"]) == ("kim@example.com", "E-001", "외부 자문")
    assert call(base, "/api/me", cookie=kim)[1]["user"] is None
    step = call(base, "/api/login", {"user": "kim@example.com", "password": "temporary-pass-1"})[1]
    status, out, cookie = call(base, "/api/login", {"ticket": step["ticket"], "new_password": "kim-password-2"})
    assert status == 200 and out["ok"]
    # stopped: kept on the list, signed out, and back with state active
    kim = cookie.split(";", 1)[0]
    assert call(base, "/api/admin/user/drop", {"id": "kim"}, cookie=root)[1]["counts"]["disabled"] == 1
    assert call(base, "/api/me", cookie=kim)[1]["user"] is None
    status, out, _ = call(base, "/api/login", {"user": "kim", "password": "kim-password-2"})
    assert status == 403 and out["state"] == "disabled"
    assert call(base, "/api/admin/user/save", {**edit, "password": "", "state": "active"}, cookie=root)[0] == 200
    sign_in(base, "kim", "kim-password-2")
    assert call(base, "/api/admin/user/save", {"id": "root1", "name": "관리 하나", "roles": ["admin"], "new": False, "state": "disabled"},
                cookie=root)[1]["error"].startswith("마지막 관리자는 비활성")
    login = [r["text"] for r in call(base, "/api/admin/audit", cookie=root)[1]["rows"] if r["kind"] == "login"]
    for said in ("계정 잠금 · 로그인 5회 실패, 15분", "잠금 해제 · 사용자 김(kim)", "2단계 인증 초기화 · 사용자 김(kim)",
                 "임시 비밀번호 발급 · 사용자 김(kim)", "비밀번호 변경", "로그인 실패 · 사용 중지된 계정", "로그인 · Chrome · Windows"):
        assert said in login, said


def test_a_person_sets_up_a_second_step_names_themselves_and_signs_out_a_device(server):
    start, tmp = server
    base, logins = start(people(tmp / "users.yaml"))
    here, _ = sign_in(base, "kim", "kim-password-1")
    there, _ = sign_in(base, "kim", "kim-password-1", agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1")
    third, _ = sign_in(base, "kim", "kim-password-1")
    me = call(base, "/api/entry/me", cookie=here)[1]
    assert me["two_factor"] == {"on": False, "required": False} and me["keep_days"] == 14 and len(me["devices"]) == 3
    assert [d["current"] for d in me["devices"]].count(True) == 1
    phone = next(d for d in me["devices"] if d["agent"] == "Safari · iOS")
    out = call(base, "/api/entry/device/out", {"id": phone["id"]}, cookie=here)[1]
    assert out["ended"] == 1 and len(out["devices"]) == 2 and call(base, "/api/me", cookie=there)[1]["user"] is None
    assert call(base, "/api/entry/device/out", {"id": phone["id"]}, cookie=here)[0] == 400
    out = call(base, "/api/entry/device/out", {"id": "others"}, cookie=here)[1]
    assert out["ended"] == 1 and [d["current"] for d in out["devices"]] == [True] and call(base, "/api/me", cookie=third)[1]["user"] is None
    # name and email
    out = call(base, "/api/entry/profile", {"name": "김하람", "email": "kim@example.com"}, cookie=here)[1]
    assert out == {"ok": True, "name": "김하람", "email": "kim@example.com"}
    assert call(base, "/api/entry/profile", {"name": "김하람", "email": "kim@example.com"}, cookie=here)[0] == 400
    # a second step, on and off
    started = call(base, "/api/entry/2fa/start", {}, cookie=here)[1]
    assert set(started) == {"secret", "uri"}
    assert call(base, "/api/entry/2fa/on", {"code": "12345"}, cookie=here)[0] == 400
    code = totp_code(started["secret"], int(logins.clock() // 30))
    assert call(base, "/api/entry/2fa/on", {"code": code}, cookie=here)[1]["two_factor"] == {"on": True, "required": False}
    assert call(base, "/api/login", {"user": "kim", "password": "kim-password-1"})[1]["step"] == "code"
    assert call(base, "/api/entry/2fa/off", {"password": "wrong-password"}, cookie=here)[0] == 400
    assert call(base, "/api/entry/2fa/off", {"password": "kim-password-1"}, cookie=here)[1]["two_factor"]["on"] is False
    # the account's own password: as long as the policy asks, not a recent one, everyone signed out
    status, out, _ = call(base, "/api/entry/password", {"current": "kim-password-1", "new": "kim-password-2"}, cookie=here)
    assert status == 200 and call(base, "/api/me", cookie=here)[1]["user"] is None
    again, _ = sign_in(base, "kim", "kim-password-2")
    status, out, _ = call(base, "/api/entry/password", {"current": "kim-password-2", "new": "kim-password-1"}, cookie=again)
    assert status == 400 and "최근에 쓴" in out["error"]
    login = [(r["text"], r["ip"]) for r in call(base, "/api/admin/audit", cookie=sign_in(base, "root1", "root-password-1")[0])[1]["rows"]
             if r["kind"] == "login" and r["by"] in ("김", "김하람")]
    for said in ("기기 로그아웃 · Safari · iOS", "다른 기기 모두 로그아웃 · 1대", "2단계 인증 켬", "2단계 인증 끔", "비밀번호 변경"):
        assert (said, "127.0.0.1") in login, said


def test_only_the_allowed_addresses_reach_the_api_and_an_admin_cannot_shut_themselves_out(server):
    start, tmp = server
    base, _ = start(people(tmp / "users.yaml"))
    root, _ = sign_in(base, "root1", "root-password-1", ip="10.1.2.3")
    said = call(base, "/api/admin/security", cookie=root, ip="10.1.2.3")[1]
    assert said["editable"] and said["client_ip"] == "10.1.2.3" and said["policy"] == POLICY
    policy = said["policy"]
    status, out, _ = call(base, "/api/admin/security/save", {"policy": {**policy, "allow_ip": ["192.168.0.0/16"]}}, cookie=root, ip="10.1.2.3")
    assert status == 400 and "지금 접속한 IP 10.1.2.3이 허용 IP 대역에 없어" in out["error"]
    for wrong in ({"allow_ip": ["10.0.0.0/33"]}, {"session_hours": 0}, {"keep_days": 91}, {"password_min": 7}, {"lock_after": "5"},
                  {"two_factor": "yes"}, {"nothing": 1}):
        assert call(base, "/api/admin/security/save", {"policy": {**policy, **wrong}}, cookie=root, ip="10.1.2.3")[0] == 400, wrong
    status, out, _ = call(base, "/api/admin/security/save", {"policy": {**policy, "allow_ip": ["10.0.0.0/8", "fd00::1"], "session_hours": 8}},
                          cookie=root, ip="10.1.2.3")
    assert status == 200 and out["policy"]["allow_ip"] == ["10.0.0.0/8", "fd00::1/128"] and out["policy"]["session_hours"] == 8
    assert Users.load(tmp / "users.yaml").policy["allow_ip"] == ["10.0.0.0/8", "fd00::1/128"]
    status, out, _ = call(base, "/api/me", ip="192.168.1.9")
    assert status == 403 and "허용되지 않은 IP에서 접속해" in out["error"]
    assert call(base, "/api/login", {"user": "kim", "password": "kim-password-1"}, ip="192.168.1.9")[0] == 403
    assert call(base, "/api/state", cookie=root, ip="192.168.1.9")[0] == 403
    assert call(base, "/api/me", cookie=root, ip="10.200.0.1")[1]["user"]["id"] == "root1"
    assert urllib.request.urlopen(base + "/healthz", timeout=30).status == 200  # what is not the api is not asked
    rows = call(base, "/api/admin/audit", cookie=root, ip="10.1.2.3")[1]["rows"]
    saved = next(r for r in rows if r["kind"] == "setting")
    assert saved["text"] == "보안 정책 변경 · 세션 만료 12시간 → 8시간 · 허용 IP 대역 제한 없음 → 10.0.0.0/8, fd00::1/128" and saved["ip"] == "10.1.2.3"
    login = next(r for r in rows if r["kind"] == "login" and r["by"] == "관리 하나")
    assert login["ip"] == "10.1.2.3" and call(base, "/api/admin/audit", cookie=root, ip="10.1.2.3")[1]["counts"]["login"] >= 1


def test_a_failed_sign_in_is_kept_under_the_name_typed_where_nobody_has_it(server):
    start, tmp = server
    base, _ = start(people(tmp / "users.yaml"))
    status, out, _ = call(base, "/api/login", {"user": "x" * 100, "password": "whatever-1"}, ip="10.9.9.9")
    assert status == 401 and out["failures"] == 1 and out["lock_after"] == 5
    call(base, "/api/login", {"user": "kim", "password": "wrong-password"}, ip="10.9.9.9")
    root, _ = sign_in(base, "root1", "root-password-1")
    rows = [(r["by"], r["text"], r["ip"]) for r in call(base, "/api/admin/audit", cookie=root)[1]["rows"] if r["kind"] == "login"]
    assert ("x" * 80, "로그인 실패 · 비밀번호 불일치", "10.9.9.9") in rows and ("김", "로그인 실패 · 비밀번호 불일치", "10.9.9.9") in rows
    assert not any("wrong-password" in json.dumps(r, ensure_ascii=False) or "whatever-1" in json.dumps(r) for r in rows)


def test_a_restarted_server_keeps_who_was_signed_in(server):
    start, tmp = server
    base, _ = start(people(tmp / "users.yaml"))
    kim, _ = sign_in(base, "kim", "kim-password-1", keep=True)
    base, _ = start(Users.load(tmp / "users.yaml"))
    assert call(base, "/api/me", cookie=kim)[1]["user"]["id"] == "kim"


def test_a_user_constructed_by_hand_still_says_what_it_may_do():
    viewer = User("v", "조회", "", ["viewer"])
    assert viewer.state == "active" and viewer.may("viewer") and not viewer.may("editor") and not viewer.locked(0)
