import json
import shutil
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from ontlas.web.team import Users, check_password, hash_password

from .conftest import EXAMPLE, LIB


def test_passwords_are_salted_and_checked_in_constant_form():
    a, b = hash_password("correct horse"), hash_password("correct horse")
    assert a != b and a.startswith("pbkdf2_sha256$") and check_password("correct horse", a)
    assert not check_password("wrong horse", a) and not check_password("x", "not-a-hash")


@pytest.fixture
def team(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.library import Library
    from ontlas.web.api import StudioSession
    from ontlas.web.server import RateLimit, make_handler
    from ontlas.web.team import Logins, TeamSessions

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
        headers["X-Ontlas-Request"] = "1"
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
    assert _call(base, "/api/me")[1] == {"team": True, "user": None, "setup": True, "signup": False, "password_min": 8, "keep_days": 14,
                                         "model": False}  # no admin yet
    assert _call(base, "/api/login", {"user": "kim", "password": "nope-nope-1"})[0] == 401
    kim, lee, park = (_login(base, u, f"{u}-password-1") for u in ("kim", "lee", "park"))
    assert _call(base, "/api/me", cookie=kim)[1]["user"]["name"] == "김"
    # a write without the page's own header is refused: another site cannot send it in the user's name
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=kim, header=False)[0] == 403
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=park)[0] == 403  # viewer
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=kim)[0] == 403  # an editor files requests; the definition in use is the approver's
    code, out, _ = _call(base, "/api/detach", {"name": "fashion"}, cookie=lee)
    assert code == 200 and out["ok"]
    state = _call(base, "/api/state", cookie=park)[1]  # the viewer sees the approver's change: one studio
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
    from ontlas.rest import Rest
    from ontlas.tools import StudioTools

    base, _, sessions = team
    shared = sessions.shared
    rest = Rest(StudioTools(shared.studio, actor_id="api"), "t", source=lambda: shared.studio, lock=shared.lock,
                unscoped=True)
    ask = {"decision": "returnEligibility", "key": "I1001"}
    assert "14일" in rest.answer("POST", "/v1/decide", ask)[1]["outputs"]["reason"]
    kim, lee = _login(base, "kim", "kim-password-1"), _login(base, "lee", "lee-password-1")
    src = _call(base, "/api/module?name=acme-overlay", cookie=kim)[1]["yaml"]
    cid = _call(base, "/api/module/save", {"text": src.replace("14일까지", "21일까지")}, cookie=kim)[1]["change"]["id"]
    assert "14일" in rest.answer("POST", "/v1/decide", ask)[1]["outputs"]["reason"]  # asked, not approved
    assert _call(base, "/api/change/decide", {"id": cid}, cookie=lee)[1]["ok"]
    assert "21일" in rest.answer("POST", "/v1/decide", ask)[1]["outputs"]["reason"]


def test_a_request_from_outside_waits_where_a_person_finds_it(team):
    from ontlas.rest import Rest
    from ontlas.tools import StudioTools

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
    from ontlas.config import load_studio

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
    from ontlas.config import load_studio
    from ontlas.mcp_server import following
    from ontlas.tools import StudioTools

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


def test_what_is_switched_on_stays_on_across_a_restart(team):
    from ontlas.config import load_studio

    base, root, _ = team
    lee = _login(base, "lee", "lee-password-1")
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=lee)[1]["ok"]
    again = load_studio(root / "library" / "studio.yaml")
    assert "fashion" not in {m.name for m in again.composition.modules}
    assert _call(base, "/api/attach", {"name": "fashion"}, cookie=lee)[1]["ok"]
    assert "fashion" in {m.name for m in load_studio(root / "library" / "studio.yaml").composition.modules}


def test_a_module_that_stopped_fitting_cannot_keep_a_studio_from_starting(team):
    from ontlas.config import load_studio
    from ontlas.library import Library

    _, root, _ = team
    config = root / "library" / "studio.yaml"
    Library(root / "library").keep_applied(["core", "commerce", "commerce-bindings", "food"])  # food reads a column this source lacks
    assert "food" not in {m.name for m in load_studio(config).composition.modules}


def test_an_earlier_version_can_be_read_and_filed_again(team):
    base, _, _ = team
    kim, lee = _login(base, "kim", "kim-password-1"), _login(base, "lee", "lee-password-1")
    now = _call(base, "/api/module?name=acme-overlay", cookie=kim)[1]
    out = _call(base, "/api/module/save", {"text": now["yaml"].replace("14일까지", "21일까지")}, cookie=kim)[1]
    assert _call(base, "/api/change/decide", {"id": out["change"]["id"]}, cookie=lee)[1]["ok"]
    later = _call(base, "/api/module?name=acme-overlay", cookie=kim)[1]
    assert later["versions"] == ["1.0.0", "1.0.1"] and "21일까지" in later["yaml"]
    old = _call(base, "/api/module?name=acme-overlay&version=1.0.0", cookie=kim)[1]
    assert old["version"] == "1.0.0" and "14일까지" in old["yaml"]
    out = _call(base, "/api/module/save", {"text": old["yaml"]}, cookie=kim)[1]
    assert out["pending"] and out["change"]["version"] == "1.0.2"
    assert _call(base, "/api/change/decide", {"id": out["change"]["id"]}, cookie=lee)[1]["ok"]
    assert "14일까지" in _call(base, "/api/module?name=acme-overlay", cookie=kim)[1]["yaml"]


def test_the_rows_under_an_object_read_in_its_own_words(team):
    base, _, _ = team
    kim = _login(base, "kim", "kim-password-1")
    out = _call(base, "/api/object/rows?name=Order&limit=5", cookie=kim)[1]
    assert out["ok"] and 0 < len(out["rows"]) <= 5 and out["labels"]["order_id"] == "주문 번호"
    assert _call(base, "/api/object/rows?name=Party", cookie=kim)[1]["ok"] is False  # a concept has no table


def test_sign_in_attempts_are_limited(team):
    base, _, _ = team  # a name each time: an account locks at five (test_team_login), an address at ten a minute
    codes = [_call(base, "/api/login", {"user": f"guess{i}", "password": "bad-guess-00"})[0] for i in range(11)]
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
    assert code == 400 and "상위 Entity" in out["error"]
    code, out, _ = _call(base, "/api/manage/propose", {}, cookie=kim)
    assert code == 200 and out["pending"] and out["change"]["module"] == "workspace"
    assert not out["workspace"]["dirty"]  # filed: the request holds the edits now
    code, out, _ = _call(base, "/api/change/decide", {"id": out["change"]["id"]}, cookie=lee)
    assert code == 200 and out["ok"]
    state = _call(base, "/api/manage", cookie=park)[1]
    assert next(o for o in state["objects"] if o["name"] == "Customer")["label"] == "회원"
    assert (root / "library" / "workspace" / "0.1.0.yaml").is_file()


def test_only_an_admin_connects_a_data_source_or_takes_one_out(team):
    """As the data source screen lets only the ontology's admin connect one (BND-01), so does the server."""
    import sqlite3

    from ontlas.web.api import DataOptions

    base, root, sessions = team
    sessions.logins.users.add("choi", "choi-password-1", name="최", roles=["admin"])
    sessions.shared.data = DataOptions(allow_connect=True)
    db = root / "shop.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE member (member_id TEXT PRIMARY KEY, name TEXT)")
        c.execute("INSERT INTO member VALUES ('M1', '가')")
    c.close()
    kim, lee, choi = (_login(base, u, f"{u}-password-1") for u in ("kim", "lee", "choi"))
    dsn = {"dsn": f"sqlite:///{db.as_posix()}"}
    for who in (kim, lee):  # an editor, an approver
        assert _call(base, "/api/connect", dsn, cookie=who)[0] == 403
        assert _call(base, "/api/connect/gateway", {"url": "https://gw.example/q"}, cookie=who)[0] == 403
        assert _call(base, "/api/pipeline", {"op": "delete", "id": "p2"}, cookie=who)[0] == 403
    code, out, _ = _call(base, "/api/connect", dsn, cookie=choi)
    assert code == 200 and out["pending"], out
    code, out, _ = _call(base, "/api/pipeline", {"op": "delete", "id": "p1"}, cookie=choi)
    assert code == 400 and "기본 파이프라인" in out["error"]  # past the gate: the first one stays
    assert _call(base, "/api/pipeline", {"op": "use", "id": "p1"}, cookie=kim)[0] == 200  # switching stays the editor's


# ---- what people are still writing outlives an approval and a restart ---------------------------------------------------

@pytest.fixture
def kept(tmp_path, request):
    """A team studio that keeps a journal, started again on the same files by `start()`, as `ontlas serve --users
    --journal --library-write` builds it (without --library-write where the test asks for `kept` False)."""
    writes = getattr(request, "param", True)
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.library import Library
    from ontlas.web.api import StudioSession
    from ontlas.web.server import RateLimit, make_handler
    from ontlas.web.team import Logins, TeamSessions

    root = tmp_path / "examples"
    shutil.copytree(EXAMPLE, root / "commerce")
    shutil.copytree(LIB, root / "library")
    users = Users.load(tmp_path / "users.yaml")
    for uid, roles in (("kim", ["editor"]), ("choi", ["editor"]), ("lee", ["approver"]), ("han", ["admin"])):
        users.add(uid, f"{uid}-password-1", name=uid.capitalize(), roles=roles)
    journal = tmp_path / "journal.jsonl"
    running: list = []

    def build():
        studio = load_studio(root / "library" / "studio.yaml")
        studio.keep_journal(journal)
        s = StudioSession(studio)
        if writes:
            s.store = Library(root / "library")
        s._adopt(s.studio)
        s.restore_pending()
        return s

    def start():
        if running:
            running[-1].shutdown()
            running[-1].server_close()
        sessions = TeamSessions(build, Logins(Users.load(tmp_path / "users.yaml")))
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(sessions, ask_limit=RateLimit(5), quiet=True,
                                                                   logins=sessions.logins))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        running.append(httpd)
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        return base, {u: _login(base, u, f"{u}-password-1") for u in ("kim", "choi", "lee", "han")}

    yield start, journal
    running[-1].shutdown()
    running[-1].server_close()


def _label(base, cookie, name):
    return next(o for o in _call(base, "/api/manage", cookie=cookie)[1]["objects"] if o["name"] == name)["label"]


def _edit(base, cookie, name, label):
    code, out, _ = _call(base, "/api/manage/edit", {"op": "update_object", "args": {"name": name, "label": label}}, cookie=cookie)
    assert code == 200, out
    return out


def test_an_approval_keeps_what_others_are_still_writing(kept):
    start, _ = kept
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    first = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    _edit(base, who["choi"], "Product", "상품 마스터")  # written while the request waits, by someone else
    _edit(base, who["choi"], "Customer", "고객 마스터")  # the item the request changes
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    ws = _call(base, "/api/manage", cookie=who["choi"])[1]["workspace"]
    assert [e["target"] for e in ws["edits"]] == ["object:Product"] and ws["edits"][0]["by"] == "Choi"
    held = ws["conflicts"]
    assert [(c["target"], c["change"], c["why"], c["by"]) for c in held] == [("object:Customer", first, "changed", "Choi")]
    assert "승인된 변경 요청" in held[0]["text"] and held[0]["args"]["label"] == "고객 마스터"
    assert _label(base, who["choi"], "Customer") == "회원"  # what was approved is not written back
    assert _label(base, who["choi"], "Product") == "상품 마스터"
    # filed, the edits go with the request; the one held aside stays for its writer
    out = _call(base, "/api/manage/propose", {}, cookie=who["choi"])[1]
    assert out["pending"] and [c["target"] for c in out["workspace"]["conflicts"]] == ["object:Customer"]
    code, out, _ = _call(base, "/api/manage/conflict", {"id": held[0]["id"], "keep": True}, cookie=who["choi"])
    assert code == 200 and out["workspace"]["conflicts"] == [] and _label(base, who["choi"], "Customer") == "고객 마스터"
    assert _call(base, "/api/manage/conflict", {"id": held[0]["id"], "keep": True}, cookie=who["choi"])[0] == 400


def test_a_held_edit_can_be_let_go_for_what_was_approved(kept):
    start, _ = kept
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    first = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    _edit(base, who["choi"], "Customer", "고객 마스터")
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    held = _call(base, "/api/manage", cookie=who["choi"])[1]["workspace"]["conflicts"]
    assert _call(base, "/api/manage/conflict", {"id": held[0]["id"], "keep": False}, cookie=who["choi"])[0] == 200
    ws = _call(base, "/api/manage", cookie=who["choi"])[1]["workspace"]
    assert ws["conflicts"] == [] and not ws["dirty"] and _label(base, who["choi"], "Customer") == "회원"


def test_the_edits_being_written_come_back_after_a_restart(kept):
    start, journal = kept
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    first = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    _edit(base, who["choi"], "Product", "상품 마스터")
    _edit(base, who["choi"], "Customer", "고객 마스터")
    code, out, _ = _call(base, "/api/lexicon/edit", {"op": "add_term", "args": {"term": "구매 확정", "definition": "주문을 끝낸 상태"}},
                         cookie=who["choi"])
    assert code == 200, out
    assert _call(base, "/api/ont2/draft", {"title": "상품 이름 정리", "description": "이름을 맞춘다"}, cookie=who["choi"])[0] == 200
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    _edit(base, who["kim"], "Category", "분류")
    assert _call(base, "/api/manage/undo", {}, cookie=who["kim"])[0] == 200  # taken back: it can be made again after a restart too
    before = _call(base, "/api/manage", cookie=who["kim"])[1]["workspace"]

    base, who = start()  # the server stops and starts again on the same files
    after = _call(base, "/api/manage", cookie=who["kim"])[1]["workspace"]
    assert [(e["target"], e["by"], e["at"]) for e in after["edits"]] == [(e["target"], e["by"], e["at"]) for e in before["edits"]]
    assert [e["target"] for e in after["edits"]] == ["object:Product", "term:구매 확정"]
    assert [(c["target"], c["change"]) for c in after["conflicts"]] == [("object:Customer", first)]
    assert after["label"] == "상품 이름 정리" and after["redo"] == 1
    assert _label(base, who["kim"], "Customer") == "회원" and _label(base, who["kim"], "Product") == "상품 마스터"
    assert any(r["term"] == "구매 확정" for r in _call(base, "/api/lexicon", cookie=who["kim"])[1]["rows"])
    assert _call(base, "/api/manage/redo", {}, cookie=who["kim"])[0] == 200
    assert _label(base, who["kim"], "Category") == "분류"
    kinds = [json.loads(line)["kind"] for line in journal.read_text(encoding="utf-8").splitlines()]
    assert "ws_edit" in kinds and "ws" in kinds


def test_a_request_filed_before_another_was_approved_is_approved_on_top_of_it(kept):
    start, _ = kept
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    first = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    _edit(base, who["choi"], "Product", "상품 마스터")
    second = _call(base, "/api/manage/propose", {}, cookie=who["choi"])[1]["change"]
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    base, who = start()  # the second request waits across a restart, with the edits it was filed from
    code, out, _ = _call(base, "/api/change/decide", {"id": second["id"]}, cookie=who["lee"])
    assert code == 200 and out["ok"], out
    assert out["change"]["version"] != second["version"]  # made again on the version the first left
    assert _label(base, who["kim"], "Customer") == "회원" and _label(base, who["kim"], "Product") == "상품 마스터"

    _edit(base, who["kim"], "Order", "주문서")
    third = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    _edit(base, who["choi"], "Order", "구매 주문")
    fourth = _call(base, "/api/manage/propose", {}, cookie=who["choi"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": third}, cookie=who["lee"])[1]["ok"]
    code, out, _ = _call(base, "/api/change/decide", {"id": fourth}, cookie=who["lee"])
    assert code == 200 and not out["ok"] and "겹쳐" in out["error"]  # the same item: not written over what was approved
    assert _label(base, who["kim"], "Order") == "주문서"


def test_a_journal_from_before_edits_were_kept_is_read_as_it_was(kept):
    start, journal = kept
    old = {"id": "C1", "module": "acme-overlay", "version": "1.0.1", "text": "module: acme-overlay\nversion: 1.0.1\n",
           "requested_by": "Kim", "status": "pending", "review": {}, "at": "2026-11-01T09:00:00", "attach": False,
           "decided_by": "", "reason": "", "marks": {}, "comments": [], "decided_at": ""}
    audit = {"at": old["at"], "by": "Kim", "event": "proposed", "change": "C1", "module": "acme-overlay", "version": "1.0.1"}
    journal.write_text(json.dumps({"kind": "change", "audit": audit, "change": old}, ensure_ascii=False) + "\n", encoding="utf-8")
    base, who = start()
    assert [(c["id"], c["status"]) for c in _call(base, "/api/changes", cookie=who["kim"])[1]["changes"]] == [("C1", "pending")]
    ws = _call(base, "/api/manage", cookie=who["kim"])[1]["workspace"]
    assert ws["edits"] == [] and ws["conflicts"] == []


def test_saved_pass_conditions_and_drafts_made_come_back_after_a_restart(kept):
    start, _ = kept
    base, who = start()
    settings = _call(base, "/api/flow/settings", cookie=who["han"])[1]["settings"]
    settings["gates"]["check"]["min_accuracy"] = 0.75
    assert _call(base, "/api/flow/save", {"settings": settings}, cookie=who["han"])[0] == 200
    was = (_call(base, "/api/flow/settings", cookie=who["han"])[1]["settings"]["gates"].get("index") or {}).get("min_found")
    code, out, _ = _call(base, "/api/admin/targets", {"changes": [{"stage": "index", "condition": "min_found", "value": 0.7, "was": was}]},
                         cookie=who["han"])
    assert code == 200 and out["ok"], out
    code, out, _ = _call(base, "/api/home/ai/job", {"kind": "rules", "error": "모델이 응답하지 않음"}, cookie=who["kim"])
    assert code == 200, out
    base, who = start()
    gates = _call(base, "/api/flow/settings", cookie=who["han"])[1]["settings"]["gates"]
    assert gates["check"]["min_accuracy"] == 0.75 and gates["index"]["min_found"] == 0.7
    jobs = _call(base, "/api/home/ai", cookie=who["kim"])[1]["jobs"]
    assert [j["error"] for j in jobs] == ["모델이 응답하지 않음"]


def test_a_module_an_approval_puts_on_stays_on_after_a_restart(kept):
    start, _ = kept
    base, who = start()
    text = """module: extra-notes
version: 1.0.0
kind: customer
label: 추가 메모
requires: [commerce]
extend:
  objects:
    Customer:
      properties:
        memo: {type: string, label: 메모, column: name}
"""
    out = _call(base, "/api/module/save", {"text": text, "apply": True}, cookie=who["kim"])[1]
    assert out["pending"]
    assert _call(base, "/api/change/decide", {"id": out["change"]["id"]}, cookie=who["lee"])[1]["ok"]
    base, who = start()
    assert "extra-notes" in {r["name"] for r in _call(base, "/api/state", cookie=who["kim"])[1]["library"] if r["on"]}


def _upload(base, cookie, name, data: bytes):
    req = urllib.request.Request(f"{base}/api/upload?path={name}", data=data, method="POST",
                                 headers={"Content-Type": "application/octet-stream", "X-Ontlas-Request": "1", "Cookie": cookie})
    with urllib.request.urlopen(req, timeout=60) as r:
        assert r.status == 200


def test_a_draft_applied_in_a_team_goes_into_the_request_being_written(kept):
    """A draft applied as a new pipeline used to take the team's studio away from its journal and library folder: what
    was approved there wrote a version needing the draft's modules, and the server no longer started."""
    start, journal = kept
    base, who = start()
    _upload(base, who["kim"], "widgets.csv", "widget_id,widget_name,weight\nW1,가,3\nW2,나,5\n".encode())
    assert _call(base, "/api/draft", {"label": "부품", "tables": None}, cookie=who["kim"])[0] == 200
    code, out, _ = _call(base, "/api/draft/review/apply", {"standard": [], "edits": None, "choices": {}}, cookie=who["kim"])
    assert code == 200 and out["request"] and out["added"]["objects"] == 1, out
    state = _call(base, "/api/state", cookie=who["kim"])[1]
    assert [p["id"] for p in state["pipelines"]] == ["p1"] and state["pipeline"] == "p1"  # the team's studio stays
    ws = _call(base, "/api/manage", cookie=who["kim"])[1]["workspace"]
    added = [e for e in ws["edits"] if e["op"] == "add_object"]
    assert len(added) == 1 and added[0]["by"] == "Kim"
    name = added[0]["target"].split(":", 1)[1]
    assert "ws_edit" in [json.loads(line)["kind"] for line in journal.read_text(encoding="utf-8").splitlines()]
    cid = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    out = _call(base, "/api/change/decide", {"id": cid}, cookie=who["lee"])[1]
    assert out["ok"], out
    kinds = [json.loads(line)["kind"] for line in journal.read_text(encoding="utf-8").splitlines()]
    assert kinds.count("change") >= 2  # the request and its approval, in the team's journal
    base, who = start()  # and the server starts again on what was approved
    assert any(o["name"] == name for o in _call(base, "/api/manage", cookie=who["kim"])[1]["objects"])


def test_in_a_team_a_person_throws_away_their_own_edits_and_an_admin_everyones(kept):
    start, _ = kept
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    _edit(base, who["choi"], "Product", "상품 마스터")
    code, out, _ = _call(base, "/api/manage/discard", {}, cookie=who["kim"])
    assert code == 200 and out["discarded"] == 1 and out["kept"] == 1
    ws = out["workspace"]
    assert [(e["target"], e["by"]) for e in ws["edits"]] == [("object:Product", "Choi")]
    assert _label(base, who["kim"], "Customer") != "회원" and _label(base, who["kim"], "Product") == "상품 마스터"
    assert _call(base, "/api/manage/discard", {}, cookie=who["kim"])[0] == 400  # none of Kim's left
    assert _call(base, "/api/manage/discard", {"all": True}, cookie=who["lee"])[0] == 403  # everyone's is the admin's
    code, out, _ = _call(base, "/api/manage/discard", {"all": True}, cookie=who["han"])
    assert code == 200 and out["workspace"]["edits"] == [] and not out["workspace"]["dirty"]


def test_a_rejected_request_goes_back_to_the_one_who_wrote_it(kept):
    start, _ = kept
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    first = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    _edit(base, who["choi"], "Product", "상품 마스터")
    code, out, _ = _call(base, "/api/change/decide", {"id": first, "approve": False, "reason": "이름 다시", "back": True}, cookie=who["lee"])
    assert code == 200 and out["ok"] and out["reopened"] == {"made": 1, "held": 0}
    assert out["change"]["status"] == "rejected" and out["change"]["reopened"] and not out["change"]["can_reopen"]
    ws = _call(base, "/api/manage", cookie=who["kim"])[1]["workspace"]
    assert sorted((e["target"], e["by"]) for e in ws["edits"]) == [("object:Customer", "Kim"), ("object:Product", "Choi")]
    assert _call(base, "/api/change/reopen", {"id": first}, cookie=who["kim"])[0] == 400  # once
    # one rejected without it can be taken back afterwards, by an editor
    _call(base, "/api/manage/discard", {"all": True}, cookie=who["han"])
    _edit(base, who["kim"], "Category", "분류")
    second = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": second, "approve": False, "reason": "보류"}, cookie=who["lee"])[1]["ok"]
    assert _call(base, f"/api/change?id={second}", cookie=who["kim"])[1]["can_reopen"]
    base, who = start()  # the decision and the taking back are kept
    assert _call(base, f"/api/change?id={first}", cookie=who["kim"])[1]["reopened"]
    code, out, _ = _call(base, "/api/change/reopen", {"id": second}, cookie=who["kim"])
    assert code == 200 and out["made"] == 1 and [(e["target"], e["by"]) for e in out["workspace"]["edits"]] == [("object:Category", "Kim")]


def test_an_item_a_deployed_change_took_out_has_its_history_and_comes_back(kept):
    start, _ = kept
    base, who = start()
    spec = {"name": "Coupon2", "key": "coupon2_id", "label": "쿠폰 시험",
            "properties": {"coupon2_id": {"type": "string"}, "memo": {"type": "string", "label": "메모"}}}
    assert _call(base, "/api/manage/edit", {"op": "add_object", "args": spec}, cookie=who["kim"])[0] == 200
    added = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": added}, cookie=who["lee"])[1]["ok"]
    assert _call(base, "/api/manage/edit", {"op": "delete_object", "args": {"name": "Coupon2"}}, cookie=who["kim"])[0] == 200
    gone = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": gone}, cookie=who["lee"])[1]["ok"]
    hist = _call(base, "/api/item/history?element=object:Coupon2", cookie=who["kim"])[1]
    assert hist["now"] is None and [(e["change"], e["kind"]) for e in hist["entries"]] == [(gone, "removed"), (added, "added")]
    code, out, _ = _call(base, "/api/item/restore", {"element": "object:Coupon2"}, cookie=who["kim"])
    assert code == 200 and out["how"] == "edit" and out["change"] == gone
    assert [(e["op"], e["by"]) for e in out["workspace"]["edits"]] == [("restore_element", "Kim")]
    assert _call(base, "/api/item/restore", {"element": "object:Coupon2"}, cookie=who["kim"])[0] == 400  # there again
    back = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": back}, cookie=who["lee"])[1]["ok"]
    base, who = start()
    obj = next(o for o in _call(base, "/api/manage", cookie=who["kim"])[1]["objects"] if o["name"] == "Coupon2")
    assert obj["label"] == "쿠폰 시험"
    # one taken out by an edit not yet sent comes back as that edit taken back
    assert _call(base, "/api/manage/edit", {"op": "delete_object", "args": {"name": "Coupon2"}}, cookie=who["choi"])[0] == 200
    code, out, _ = _call(base, "/api/item/restore", {"element": "object:Coupon2"}, cookie=who["choi"])
    assert code == 200 and out["how"] == "undone" and not out["workspace"]["dirty"]


@pytest.mark.parametrize("kept", [False], indirect=True)
def test_where_only_the_journal_keeps_them_approved_versions_run_again_after_a_restart(kept, tmp_path):
    yaml = pytest.importorskip("yaml")
    start, journal = kept  # as `ontlas serve --users --journal`: nothing is written to the library folder
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")
    first = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    _edit(base, who["kim"], "Product", "상품 마스터")
    second = _call(base, "/api/manage/propose", {}, cookie=who["kim"])[1]["change"]["id"]
    assert _call(base, "/api/change/decide", {"id": second}, cookie=who["lee"])[1]["ok"]
    _edit(base, who["choi"], "Category", "분류")  # still being written
    said = _call(base, "/api/versions", cookie=who["kim"])[1]["current"]
    assert said["number"] == 3 and not (tmp_path / "examples" / "library" / "workspace").exists()
    assert _call(base, "/api/detach", {"name": "fashion"}, cookie=who["lee"])[1]["ok"]  # by hand: no record says so

    base, who = start()  # the records say version 3: so does the definition that runs
    again = _call(base, "/api/versions", cookie=who["kim"])[1]["current"]
    assert (again["number"], again["key"], again["change"]) == (3, said["key"], second)
    assert "fashion" in {m["name"] for m in again["modules"]}  # what was switched off by hand is on again: the folder keeps that
    assert _label(base, who["kim"], "Customer") == "회원" and _label(base, who["kim"], "Product") == "상품 마스터"
    ws = _call(base, "/api/manage", cookie=who["choi"])[1]["workspace"]
    assert [(e["target"], e["by"]) for e in ws["edits"]] == [("object:Category", "Choi")] and ws["conflicts"] == []
    third = _call(base, "/api/manage/propose", {}, cookie=who["choi"])[1]["change"]["id"]  # and the next approval stands on them
    assert _call(base, "/api/change/decide", {"id": third}, cookie=who["lee"])[1]["ok"]
    assert [_label(base, who["kim"], n) for n in ("Customer", "Product", "Category")] == ["회원", "상품 마스터", "분류"]
    assert not (tmp_path / "examples" / "library" / "workspace").exists()
    # an approved version that no longer goes on stops the start, said: records and definition are not left apart
    last = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if '"approved"' in x][-1]
    bad = yaml.safe_load(last["change"]["text"])
    bad["version"] = "9.9.9"
    bad.setdefault("objects", {})["Ghost"] = {"parent": "Nowhere", "key": "id", "properties": {"id": {"type": "string"}}}
    last["change"].update(id="C9", version="9.9.9", text=yaml.safe_dump(bad, allow_unicode=True, sort_keys=False))
    last["audit"].update(change="C9", version="9.9.9")
    with journal.open("a", encoding="utf-8") as f:
        f.write(json.dumps(last, ensure_ascii=False) + "\n")
    with pytest.raises(ValueError, match="C9.*--library-write"):
        start()


# ---- each person looks at a library of their own; one made on the page is kept, with what was asked in it -----------------

@pytest.fixture
def libraries(tmp_path, monkeypatch):
    """A team's server offering two libraries, as `ontlas serve --users --journal --library-write --library second`
    builds it, started again on the same files by `start()`."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import ontlas.web as web
    from ontlas.web import routes
    from ontlas.web.server import RateLimit, make_handler
    from ontlas.web.team import Logins, TeamSessions

    said = dict(routes.SERVER)
    root = tmp_path / "examples"
    shutil.copytree(EXAMPLE, root / "commerce")
    shutil.copytree(LIB, root / "library")
    shutil.copytree(LIB / "core", root / "second" / "library" / "core")
    (root / "second" / "studio.yaml").write_text("\n".join(
        ["library: library", "name: second", "label: 둘째", "namespace: https://example.org/second#", "modules: [core]", ""]),
        encoding="utf-8")
    users = Users.load(tmp_path / "users.yaml")
    for uid, roles in (("kim", ["editor"]), ("lee", ["approver"]), ("han", ["admin"]), ("park", ["viewer"])):
        users.add(uid, f"{uid}-password-1", name=uid.capitalize(), roles=roles)
    journal = tmp_path / "journal.jsonl"
    running: list = []

    def start():
        if running:
            running[-1].shutdown()
            running[-1].server_close()
        got = {}
        monkeypatch.setattr(web, "serve", lambda build, **kw: got.update(build=build))
        web.serve_config(root / "library" / "studio.yaml", library_write=True, journal=journal, users=tmp_path / "users.yaml",
                         libraries=[root / "second" / "studio.yaml"])
        sessions = TeamSessions(got["build"], Logins(Users.load(tmp_path / "users.yaml")))
        routes.SERVER.update(logins=sessions.logins, sessions=sessions)  # what the server says when it starts (routes.started)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(sessions, ask_limit=RateLimit(5), quiet=True,
                                                                   logins=sessions.logins))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        running.append(httpd)
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        return base, {u: _login(base, u, f"{u}-password-1") for u in ("kim", "lee", "han", "park")}

    yield start, root, journal
    running[-1].shutdown()
    running[-1].server_close()
    routes.SERVER.clear()
    routes.SERVER.update(said)


def _at(base, cookie):
    return _call(base, "/api/state", cookie=cookie)[1]["library_id"]


def _area(base, cookie, name, label):
    code, out, _ = _call(base, "/api/manage/edit", {"op": "add_area", "args": {"name": name, "label": label}}, cookie=cookie)
    assert code == 200, out


def _edits(base, cookie):
    return [(e["target"], e["by"]) for e in _call(base, "/api/manage", cookie=cookie)[1]["workspace"]["edits"]]


def _make(base, cookie, body):
    code, out, _ = _call(base, "/api/entry/ontology/new", body, cookie=cookie)
    assert code == 200, out
    return out["id"]


def test_one_person_opening_or_making_a_library_leaves_the_others_where_they_are(libraries):
    start, root, _ = libraries
    base, who = start()
    _edit(base, who["kim"], "Customer", "회원")  # being written in the first library
    title = _call(base, "/api/state", cookie=who["kim"])[1]["title"]
    made = _make(base, who["han"], {"label": "시험 온톨로지", "key": "trial", "start": "base", "base": "l2"})  # on a library nobody had open
    assert _at(base, who["han"]) == made and _at(base, who["kim"]) == "l1" and _at(base, who["lee"]) == "l1"
    kim = _call(base, "/api/state", cookie=who["kim"])[1]
    assert kim["title"] == title and [x["id"] for x in kim["libraries"]] == ["l1", "l2", made]
    assert _edits(base, who["kim"]) == [("object:Customer", "Kim")] and _edits(base, who["han"]) == []
    # what is asked and approved in the made one is its own: its folder, its requests
    _area(base, who["han"], "Trial", "시험 구역")
    first = _call(base, "/api/manage/propose", {}, cookie=who["han"])[1]["change"]["id"]
    assert _call(base, "/api/changes", cookie=who["kim"])[1]["changes"] == []
    assert _call(base, "/api/library", {"id": made}, cookie=who["lee"])[0] == 200 and _at(base, who["lee"]) == made
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    assert (root / "library" / "made" / "trial" / "library" / "workspace" / "0.1.0.yaml").is_file()
    assert not (root / "library" / "workspace").exists() and not (root / "second" / "library" / "workspace").exists()
    assert _at(base, who["kim"]) == "l1" and _label(base, who["kim"], "Customer") == "회원"
    # a viewer opens one too: it is what they look at, and nobody else's
    assert _call(base, "/api/library", {"id": "l2"}, cookie=who["park"])[0] == 200
    assert _at(base, who["park"]) == "l2" and _at(base, who["kim"]) == "l1" and _at(base, who["han"]) == made
    assert _call(base, "/api/library", {"id": "s9"}, cookie=who["park"])[0] == 400 and _at(base, who["park"]) == "l2"
    # making and taking away stay the admin's
    assert _call(base, "/api/entry/ontology/new", {"label": "x", "start": "empty"}, cookie=who["kim"])[0] == 403
    assert _call(base, "/api/library/drop", {"id": made}, cookie=who["lee"])[0] == 403
    assert _call(base, "/api/entry/ontology/restore", {"id": made}, cookie=who["lee"])[0] == 403
    # a page that says which library it shows writes nothing into another: Lee opened the made one in another window
    def shown(lid):
        req = urllib.request.Request(base + "/api/manage/edit", data=json.dumps({"op": "add_area", "args": {"name": "Shown", "label": "창"}}).encode(),
                                     headers={"Content-Type": "application/json", "X-Ontlas-Request": "1", "Cookie": who["lee"],
                                              "X-Ontlas-Library": lid}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    code, out = shown("l1")
    assert code == 400 and "다른 창" in out["error"] and _edits(base, who["lee"]) == []
    assert shown(made)[0] == 200 and _edits(base, who["lee"]) == [("area:Shown", "Lee")]


def test_a_made_library_and_what_was_asked_in_it_come_back_after_a_restart(libraries):
    start, root, journal = libraries
    base, who = start()
    made = _make(base, who["han"], {"label": "시험 온톨로지", "key": "trial", "start": "empty", "description": "돌려 보는 것"})
    _area(base, who["han"], "Trial", "시험 구역")
    first = _call(base, "/api/manage/propose", {}, cookie=who["han"])[1]["change"]["id"]
    assert _call(base, "/api/library", {"id": made}, cookie=who["lee"])[0] == 200
    assert _call(base, "/api/change/decide", {"id": first}, cookie=who["lee"])[1]["ok"]
    _area(base, who["han"], "Waiting", "대기 구역")
    second = _call(base, "/api/manage/propose", {}, cookie=who["han"])[1]["change"]["id"]
    _area(base, who["han"], "Writing", "작성 중 구역")
    assert _call(base, "/api/element/comment", {"id": "area:Trial", "text": "돌려 본 뒤 정리"}, cookie=who["han"])[0] == 200
    _edit(base, who["kim"], "Customer", "회원")  # and in the first library
    assert _call(base, "/api/library", {"id": "l2"}, cookie=who["park"])[0] == 200
    _call(base, "/api/library", {"id": "l2"}, cookie=who["kim"])
    _area(base, who["kim"], "Second", "둘째 구역")  # an offered library other than the first keeps what is written in it too
    _call(base, "/api/library", {"id": "l1"}, cookie=who["kim"])

    base, who = start()  # the server stops and starts again on the same files
    libs = _call(base, "/api/state", cookie=who["kim"])[1]["libraries"]
    assert [(x["id"], x["made"]) for x in libs] == [("l1", False), ("l2", False), (made, True)] and libs[-1]["label"] == "시험 온톨로지"
    assert _at(base, who["han"]) == made and _at(base, who["lee"]) == made  # each where they were
    assert _at(base, who["kim"]) == "l1" and _at(base, who["park"]) == "l2"
    areas = {a["name"]: a["label"] for a in _call(base, "/api/manage", cookie=who["han"])[1]["areas"]}
    assert areas == {"Trial": "시험 구역", "Writing": "작성 중 구역"}  # the approved version, and the edit being written on it
    assert {c["id"]: c["status"] for c in _call(base, "/api/changes", cookie=who["han"])[1]["changes"]} == {first: "approved", second: "pending"}
    assert _edits(base, who["han"]) == [("area:Writing", "Han")]
    assert "돌려 본 뒤 정리" in json.dumps(_call(base, "/api/element/comments?id=area:Trial", cookie=who["han"])[1], ensure_ascii=False)
    assert _edits(base, who["kim"]) == [("object:Customer", "Kim")] and _edits(base, who["park"]) == [("area:Second", "Kim")]
    # each library's records are in a file of its own: the made one's in its folder, the offered one's beside the first's
    kinds = lambda p: {json.loads(line)["kind"] for line in p.read_text(encoding="utf-8").splitlines()}  # noqa: E731
    assert {"change", "ws", "ws_edit", "comment"} <= kinds(root / "library" / "made" / "trial" / "journal.jsonl")
    assert [p.name for p in journal.parent.glob("journal.second-*.jsonl")] and "change" not in kinds(journal)
    one = _call(base, "/api/entry/ontologies", cookie=who["park"])[1]
    assert _call(base, "/api/state", cookie=who["park"])[1]["made_kept"] and next(o for o in one["ontologies"] if o["id"] == made)["description"] == "돌려 보는 것"


def test_one_taken_away_takes_nothing_its_readers_send_into_another_and_is_put_back(libraries):
    start, root, _ = libraries
    base, who = start()
    made = _make(base, who["han"], {"label": "시험 온톨로지", "key": "trial", "start": "empty"})
    _area(base, who["han"], "Trial", "시험 구역")
    assert _call(base, "/api/library", {"id": made}, cookie=who["lee"])[0] == 200
    assert _call(base, "/api/library/drop", {"id": "l2"}, cookie=who["han"])[0] == 400  # one the deployment offers stays
    assert _call(base, "/api/library/drop", {"id": made}, cookie=who["han"])[1] == {"ok": True}
    shelf = root / "library" / "made"
    assert not (shelf / "trial").exists() and len(list((shelf / ".deleted").iterdir())) == 1
    _area(base, who["han"], "Mine", "첫 온톨로지 구역")  # the one who took it away is on the first at once: this is written there
    assert _at(base, who["han"]) == "l1" and _edits(base, who["han"]) == [("area:Mine", "Han")]
    # the approver's page still shows the one that went: what it sends is refused, not written into the first library
    code, out, _ = _call(base, "/api/manage/edit", {"op": "add_area", "args": {"name": "Leak", "label": "새는 구역"}}, cookie=who["lee"])
    assert code == 400 and "삭제되어" in out["error"]
    assert _at(base, who["lee"]) == "l1"  # read again, the page is on the first: from here on it writes there
    assert "Leak" not in {a["name"] for a in _call(base, "/api/manage", cookie=who["lee"])[1]["areas"]}
    deleted = _call(base, "/api/entry/ontologies", cookie=who["han"])[1]["deleted"]
    assert [(d["id"], d["label"], d["by"]) for d in deleted] == [(made, "시험 온톨로지", "Han")]
    assert _call(base, "/api/entry/ontologies", cookie=who["kim"])[1]["deleted"] == []  # the list is for those who put one back
    code, out, _ = _call(base, "/api/entry/ontology/restore", {"id": made}, cookie=who["han"])
    assert code == 200 and out["label"] == "시험 온톨로지" and (shelf / "trial" / "studio.yaml").is_file()
    assert _call(base, "/api/library", {"id": made}, cookie=who["han"])[0] == 200
    assert _edits(base, who["han"]) == [("area:Trial", "Han")]  # what was being written in it came back with it


def test_what_is_done_to_the_servers_users_is_kept_once_and_read_from_every_library(libraries):
    start, root, journal = libraries
    base, who = start()
    made = _make(base, who["han"], {"label": "시험 온톨로지", "key": "trial", "start": "empty"})

    def audit(kind):  # what the audit log says of one kind, oldest first, for the library Han looks at
        return [r["text"] for r in reversed(_call(base, "/api/admin/audit", cookie=who["han"])[1]["rows"]) if r["kind"] == kind]

    # Han looks at the made library while adding a person and setting one of its quality targets
    new = {"id": "noh", "name": "노", "roles": ["editor"], "password": "noh-password-1", "new": True}
    assert _call(base, "/api/admin/user/save", new, cookie=who["han"])[0] == 200
    was = (_call(base, "/api/flow/settings", cookie=who["han"])[1]["settings"].get("gates", {}).get("bind") or {}).get("max_errors")
    target = {"changes": [{"stage": "bind", "condition": "max_errors", "value": 5, "was": was}]}
    assert _call(base, "/api/admin/targets", target, cookie=who["han"])[1]["ok"]
    assert audit("user") == ["사용자 노(noh) 추가 · 역할 편집자"] and len(audit("setting")) == 1
    for lid in ("l1", "l2"):  # the person is the server's: read from every library. The target is the made library's own
        assert _call(base, "/api/library", {"id": lid}, cookie=who["han"])[0] == 200
        assert audit("user") == ["사용자 노(noh) 추가 · 역할 편집자"] and audit("setting") == []
    again = {"id": "noh", "name": "노", "roles": ["editor", "approver"]}
    assert _call(base, "/api/admin/user/save", again, cookie=who["han"])[0] == 200  # and one more, from the second library

    base, who = start()  # kept in the first library's journal alone, so it is there after a restart and from each
    said = ["사용자 노(noh) 추가 · 역할 편집자", "사용자 노(noh) 변경 · 역할 편집자 → 편집자 · 승인자"]
    kinds = lambda p: [json.loads(x).get("what") for x in p.read_text(encoding="utf-8").splitlines() if '"kind": "admin"' in x]  # noqa: E731
    assert [k for k in kinds(journal) if k != "login"] == ["user", "user"] and "login" in kinds(journal)  # the sign-ins too
    assert kinds(root / "library" / "made" / "trial" / "journal.jsonl") == ["setting"]
    assert all("admin" not in p.read_text(encoding="utf-8") for p in journal.parent.glob("journal.second-*.jsonl"))
    assert _at(base, who["han"]) == "l2" and audit("user") == said and audit("setting") == []
    assert _call(base, "/api/library", {"id": made}, cookie=who["han"])[0] == 200
    assert audit("user") == said and len(audit("setting")) == 1


def test_where_the_server_keeps_no_folder_for_them_a_made_library_ends_with_it(kept):
    start, _ = kept  # a team's server that writes approved changes by hand, with no shelf for what is made on the page
    base, who = start()
    made = _make(base, who["han"], {"label": "시험 온톨로지", "start": "empty"})
    assert _at(base, who["han"]) == made and _at(base, who["kim"]) == "l1"
    _area(base, who["han"], "Trial", "시험 구역")
    assert _edits(base, who["han"]) == [("area:Trial", "Han")] and _edits(base, who["kim"]) == []
    assert _call(base, "/api/state", cookie=who["han"])[1]["made_kept"] is False
    base, who = start()
    assert [x["id"] for x in _call(base, "/api/state", cookie=who["han"])[1]["libraries"]] == ["l1"]
    assert _at(base, who["han"]) == "l1"  # the one they looked at is gone with the server: they read the first again


def test_requests_sent_together_stay_in_the_library_of_the_one_who_sent_them(libraries):
    start, _, _ = libraries
    base, who = start()
    made = _make(base, who["han"], {"label": "시험 온톨로지", "start": "empty"})
    wrong: list = []

    def work(user: str, want: str, mark: str) -> None:
        for i in range(12):
            _area(base, who[user], f"{mark}{i}", mark)
            st = _call(base, "/api/state", cookie=who[user])[1]
            names = {t.split(":", 1)[1] for t, _ in _edits(base, who[user])}
            if st["library_id"] != want or any(not n.startswith(mark) for n in names):
                wrong.append((user, st["library_id"], sorted(names)))

    threads = [threading.Thread(target=work, args=a) for a in (("kim", "l1", "First"), ("han", made, "Made"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not wrong
    assert len(_edits(base, who["kim"])) == 12 and len(_edits(base, who["han"])) == 12
