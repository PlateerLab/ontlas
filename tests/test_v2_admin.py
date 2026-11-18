"""The admin screens' routes: what the open ontology is made of, what each role may do, the users, the records, and
what the server runs on. They are read by an admin only, and a user is added, changed and removed with guards."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"


@pytest.fixture()
def routes():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.web import routes
    from ontlas.web.areas import admin

    routes.load()
    kept = dict(routes.SERVER)
    routes.SERVER.clear()
    del admin._log[:], admin._gate[:]
    yield routes
    routes.SERVER.clear()
    routes.SERVER.update(kept)
    del admin._log[:], admin._gate[:]


@pytest.fixture()
def session(routes):
    from ontlas.config import load_studio
    from ontlas.web import library_entry
    from ontlas.web.api import StudioSession

    first = load_studio(SHOP)
    s = StudioSession(first)
    s.libraries = [library_entry("l1", SHOP, first)]
    return s


@pytest.fixture()
def people(tmp_path, routes):
    from ontlas.web.areas import admin
    from ontlas.web.team import Logins, Users

    users = Users.load(tmp_path / "users.yaml")
    users.add("root1", "root-password-1", name="관리 하나", roles=["admin"])
    users.add("maker1", "maker-password-1", name="편집 하나", roles=["editor"])
    users.add("reader1", "reader-password-1", name="조회 하나", roles=["viewer"])
    logins = Logins(Users.load(tmp_path / "users.yaml"))
    admin.bind(logins=logins)
    return logins


def test_the_settings_say_what_the_ontology_is_called_and_how_its_names_are_written(session, routes):
    d = routes.GET["admin/settings"](session, {}, None)
    assert d["id"] == "l1" and d["namespace"].startswith("http") and d["version"]["number"] == 1
    assert len(d["modules"]) >= 3 and all(m["version"] for m in d["modules"])
    entity, prop = d["naming"]["entity"], d["naming"]["property"]
    assert entity["style"] == "PascalCase" and entity["follow"] == entity["total"] == len(session.studio.onto.objects)
    assert prop["style"] == "snake_case" and 0 < prop["follow"] <= prop["total"]
    assert "schema.org" in [v["name"] for v in d["vocabularies"]]
    assert d["approval"] == {"self_approve": True, "apply_needs": "approver", "decide_needs": "approver"}
    assert d["model_state"] == "off"  # no model: 미연결, and a model set but not yet called is not said to be 연결됨


def _gate(session, stage, cond):
    return (session.flow_settings()["settings"]["gates"].get(stage) or {}).get(cond)


def test_a_quality_target_is_saved_alone_and_kept_in_the_audit_with_who(session, routes, people, tmp_path):
    from ontlas.journal import Journal

    session.studio.changes.keep(Journal(tmp_path / "journal.jsonl"))
    root, save = people.users.users["root1"], routes.POST["admin/targets"]
    found, accuracy = _gate(session, "index", "min_found"), _gate(session, "check", "min_accuracy")
    out = save(session, {"changes": [{"stage": "check", "condition": "min_accuracy", "was": accuracy, "value": 0.88}]}, root)
    assert out["ok"] and _gate(session, "check", "min_accuracy") == 0.88 and _gate(session, "index", "min_found") == found
    rows = [r for r in routes.GET["admin/audit"](session, {}, root)["rows"] if r["kind"] == "setting"]
    assert len(rows) == 1 and rows[0]["by"] == "관리 하나" and rows[0]["text"].startswith("품질 목표 변경 · 정답률 ")
    assert rows[0]["text"].endswith("→ 88%") and not [r for r in routes.GET["admin/audit"](session, {}, root)["rows"] if r["kind"] == "note"]
    assert any(json.loads(x)["kind"] == "admin" and json.loads(x)["what"] == "setting"
               for x in (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines())  # a restart does not forget it
    from ontlas.web.team import NEEDS

    assert NEEDS["admin/targets"] == "admin"


def test_two_admins_saving_targets_do_not_put_back_each_others(session, routes, people):
    root, save = people.users.users["root1"], routes.POST["admin/targets"]
    found, accuracy = _gate(session, "index", "min_found"), _gate(session, "check", "min_accuracy")
    # both read the same conditions; one saves 문서 검색 적중률, the other 정답률 after it
    assert save(session, {"changes": [{"stage": "index", "condition": "min_found", "was": found, "value": 0.6}]}, root)["ok"]
    assert save(session, {"changes": [{"stage": "check", "condition": "min_accuracy", "was": accuracy, "value": 0.88}]}, root)["ok"]
    assert _gate(session, "index", "min_found") == 0.6 and _gate(session, "check", "min_accuracy") == 0.88
    # the same target changed by both: the later save is said back with the value it found, nothing is overwritten
    out = save(session, {"changes": [{"stage": "index", "condition": "min_found", "was": found, "value": 0.7}]}, root)
    assert not out["ok"] and "문서 검색 적중률" in out["error"] and "60%" in out["error"] and _gate(session, "index", "min_found") == 0.6
    assert out["settings"]["gates"]["index"]["min_found"] == 0.6
    # a target emptied stays empty: the stage is kept with no condition, its default does not come back
    assert save(session, {"changes": [{"stage": "index", "condition": "min_found", "was": 0.6, "value": None}]}, root)["ok"]
    assert _gate(session, "index", "min_found") is None


def test_a_quality_target_that_is_not_a_number_of_its_kind_is_refused(session, routes, people):
    root, save = people.users.users["root1"], routes.POST["admin/targets"]
    errors = _gate(session, "bind", "max_errors")
    for change in ({"stage": "bind", "condition": "max_errors", "value": 1.5}, {"stage": "bind", "condition": "max_errors", "value": -1},
                   {"stage": "check", "condition": "min_accuracy", "value": 1.5}, {"stage": "check", "condition": "min_accuracy", "value": "0.8"},
                   {"stage": "check", "condition": "min_accuracy", "value": True}, {"stage": "check", "condition": "nothing", "value": 0.5}):
        with pytest.raises(ValueError, match="저장하지 못했습니다"):
            save(session, {"changes": [{**change, "was": None}]}, root)
    assert _gate(session, "bind", "max_errors") == errors


def test_names_are_counted_by_the_way_they_are_written():
    from ontlas.web.areas.admin import _naming

    assert _naming(["OrderItem", "Order", "Sku"]) == {"style": "PascalCase", "follow": 3, "total": 3}
    assert _naming(["unit_price", "status", "ordered_at", "orderId"]) == {"style": "snake_case", "follow": 3, "total": 4}
    assert _naming(["shop:Claim", "shop:Refund"])["style"] == "PascalCase"  # a prefixed name is read after its prefix
    assert _naming([]) == {"style": "", "follow": 0, "total": 0}


def test_the_vocabularies_are_read_from_what_the_definition_is_aligned_to(session, routes):
    d = routes.GET["admin/vocab"](session, {}, None)
    schema = next(v for v in d["vocabularies"] if v["name"] == "schema.org")
    assert schema["counts"]["Entity"] >= 1 and sum(schema["counts"].values()) == len(schema["terms"])
    hit = next(t for t in schema["terms"] if t["element"] == "OrderItem")
    assert hit["term"] == "OrderItem" and hit["iri"] == "https://schema.org/OrderItem" and hit["kind"] == "Entity"
    assert d["defined"]["Entity"] == len(session.studio.onto.objects)


def test_what_a_role_may_do_is_read_from_what_the_server_asks_of_each_route(session, routes):
    from ontlas.web.team import NEEDS

    d = routes.GET["admin/members"](session, {}, None)
    rows = {m["label"]: m for m in d["matrix"]}
    edit, decide, users = rows["정의 · 규칙 편집, 변경 요청 작성"], rows["변경 요청 승인 · 버전 배포"], rows["사용자 추가 · 변경"]
    assert edit["needs"] == NEEDS["manage/edit"] and edit["may"] == {"viewer": False, "editor": True, "approver": True, "admin": True}
    assert decide["may"] == {"viewer": False, "editor": False, "approver": True, "admin": True}
    assert users["may"] == {"viewer": False, "editor": False, "approver": False, "admin": True}
    assert "초기화" not in rows  # a team's shared space is never reset, so no role is said to reset it
    assert d["team"] is False and d["users"] == []  # nobody signs in to this server
    owners = {a["name"]: a["owner"] for a in d["areas"]}
    assert set(owners) == set(session.studio.onto.areas) and any(owners.values())


def test_the_overview_counts_the_open_ontology_and_lists_what_waits(session, routes):
    d = routes.GET["admin/overview"](session, {}, None)
    row = d["libraries"][0]
    assert row["open"] and row["counts"]["entities"] == len(session.studio.onto.objects) and sum(row["levels"]) == row["counts"]["entities"]
    assert row["version"] == "버전 1" and d["users"] is None and d["clients"] is None
    assert [t["kind"] for t in d["todo"]] == [i["kind"] for i in session.inbox()["items"]]


def test_the_overview_names_the_packs_the_last_accuracy_and_the_objects_no_one_answers_for(session, routes):
    comp = session.studio.composition
    packs = [f"{m.label or m.name} {m.version}" for m in comp.modules if m.kind == "domain"]
    row = routes.GET["admin/overview"](session, {}, None)["libraries"][0]
    assert packs and row["packs"] == packs == routes.GET["admin/settings"](session, {}, None)["packs"]
    assert row["accuracy"] is None  # 검증 has not been looked at: no share is made up
    session.flow()
    d = routes.GET["admin/overview"](session, {}, None)
    accuracy = d["libraries"][0]["accuracy"]
    assert accuracy == session._measured["check"]["accuracy"] and 0 <= accuracy <= 1
    assert d["unowned"] == [ar.label or ar.name for ar in session.studio.onto.areas.values() if not ar.owner] and d["unowned"]
    session.manage_edit("update_object", {"name": next(iter(session.studio.onto.objects)), "label": "이름을 바꾼 것"})
    session.manage_propose()  # another definition: the share measured on the one before is not its
    assert routes.GET["admin/overview"](session, {}, None)["libraries"][0]["accuracy"] is None


def test_a_signed_in_user_says_when_they_signed_in(session, routes, people):
    from datetime import datetime

    admin = people.users.users["root1"]
    before = datetime.now().replace(microsecond=0)
    people.sign_in("maker1", "maker-password-1")
    rows = {u["id"]: u for u in routes.GET["admin/users"](session, {}, admin)["users"]}
    assert rows["maker1"]["signed_in"] and before <= datetime.fromisoformat(rows["maker1"]["signed_at"]) <= datetime.now()
    assert not rows["reader1"]["signed_in"] and rows["reader1"]["signed_at"] == ""


def test_the_audit_holds_a_change_request_and_its_decision(session, routes):
    assert routes.GET["admin/audit"](session, {}, None)["total"] == 0
    name = next(iter(session.studio.onto.objects))
    session.manage_edit("update_object", {"name": name, "label": "이름을 바꾼 것"})
    session.manage_propose()
    d = routes.GET["admin/audit"](session, {}, None)
    said = [r["text"] for r in d["rows"] if r["kind"] == "change"]
    assert len(said) == 2 and said[0].startswith("승인 · 배포") and said[1].startswith("변경 요청")  # newest first
    assert d["counts"]["change"] == 2 and d["kept"] is False


def test_the_system_says_what_it_runs_on_and_is_limited_by(session, routes):
    from ontlas import __version__

    d = routes.GET["admin/system"](session, {}, None)
    assert d["version"] == __version__ == routes.GET["admin/version"](session, {}, None)["version"]
    names = [p["name"] for p in d["parts"]]
    assert names[0] == "애플리케이션 서버" and "임베딩 모델" in names and "언어 모델" in names
    assert next(p for p in d["parts"] if p["name"] == "언어 모델")["state"] == "off"  # no model was given
    assert d["limits"]["files"] == session.data.files and d["sessions"] is None and d["ask_per_minute"] is None
    assert d["usage"] == {"files": 0, "mb": 0.0}
    assert d["platform"] == "" and d["python"].count(".") == 1 and "·" not in d["parts"][0]["detail"]  # a visitor is not told the host
    assert d["keeps"] == {"journal": False, "journal_file": "", "journal_kb": 0, "library_write": False, "repositories": False}


def test_the_server_lends_its_sessions_and_its_question_limit(session, routes):
    from ontlas.web.areas import admin
    from ontlas.web.server import RateLimit, Sessions

    sessions = Sessions(lambda: session, limit=7, idle=600, spare=0)
    sessions.get("")
    routes.SERVER.update(sessions=sessions, limits={"ask_per_minute": 13})  # what the server says when it starts (routes.started)
    assert admin.SERVER is routes.SERVER
    d = routes.GET["admin/system"](session, {}, None)
    assert d["sessions"] == {"count": 1, "limit": 7, "idle_minutes": 10} and d["ask_per_minute"] == 13
    assert routes.GET["admin/ai"](session, {}, None)["ask_per_minute"] == 13
    admin.bind(limits={}, ask_limit=RateLimit(9))  # a handler made without the server: its counter says the limit
    assert routes.GET["admin/system"](session, {}, None)["ask_per_minute"] == 9


def test_an_admin_who_signed_in_is_told_what_the_host_runs_on(session, routes, people):
    import platform

    d = routes.GET["admin/system"](session, {}, people.users.users["root1"])
    assert d["python"] == platform.python_version() and platform.system() in d["platform"] and platform.system() in d["parts"][0]["detail"]


def test_the_security_values_are_the_ones_the_sign_in_uses(session, routes, people):
    from ontlas.web.team import ITERATIONS

    d = routes.GET["admin/security"](session, {}, people.users.users["root1"])
    assert d["team"] and d["users"] == 3 and d["session_hours"] == 12 and d["iterations"] == ITERATIONS and d["tries_per_minute"] == 10
    with pytest.raises(ValueError):  # the length these screens say is the one the users file asks for
        people.users.add("short1", "x" * (d["password_min"] - 1))
    people.users.add("long1", "x" * d["password_min"])


def test_the_model_is_tried_once_and_says_how_it_went(session, routes):
    with pytest.raises(ValueError):
        routes.POST["admin/ai/test"](session, {}, None)  # no model
    session.llm = lambda system, user: "ok"
    out = routes.POST["admin/ai/test"](session, {}, None)
    assert out["ok"] and out["answered"] and out["state"] == "ok" and out["ms"] >= 0

    def down(system, user):
        raise OSError("connection refused")

    session.llm = down
    out = routes.POST["admin/ai/test"](session, {}, None)
    assert not out["ok"] and out["state"] == "bad" and out["error"]


def test_the_ai_screen_names_the_model_and_never_its_address_or_key(session, routes):
    import json

    from ontlas.nl import openai_chat

    assert routes.GET["admin/ai"](session, {}, None)["llm"]["model"] == ""  # no model
    session.llm = openai_chat("http://models.internal:8000/v1", "house-model-7b", key="secret-key-1")
    d = routes.GET["admin/ai"](session, {}, None)
    assert d["llm"]["model"] == "house-model-7b" and d["llm"]["kind"] == "openai"
    said = json.dumps(d, ensure_ascii=False)
    assert "secret-key-1" not in said and "models.internal" not in said
    assert session.llm.roomier(100, 5).model == "house-model-7b"  # the roomier call asks the same model


def test_the_model_is_not_tried_more_often_than_questions_may_be_asked(session, routes):
    from ontlas.web.areas import admin
    from ontlas.web.server import RateLimit

    calls = []
    session.llm = lambda system, user: calls.append(1) or "ok"
    for _ in range(admin.TEST_PER_MINUTE):  # these screens keep a limit of their own on tries
        routes.POST["admin/ai/test"](session, {}, None)
    with pytest.raises(ValueError, match="한도"):
        routes.POST["admin/ai/test"](session, {}, None)
    del admin._gate[:]
    routes.SERVER.update(limits={"ask_per_minute": 2})  # never more than questions may be asked on this server
    routes.POST["admin/ai/test"](session, {}, None)
    routes.POST["admin/ai/test"](session, {}, None)
    with pytest.raises(ValueError, match="한도"):
        routes.POST["admin/ai/test"](session, {}, None)
    admin.bind(ask_limit=RateLimit(1))  # the server's own counter of questions, where a handler was lent it
    routes.POST["admin/ai/test"](session, {}, None)
    with pytest.raises(ValueError, match="한도"):
        routes.POST["admin/ai/test"](session, {}, None)
    assert len(calls) == admin.TEST_PER_MINUTE + 3


def test_what_was_done_to_users_outlives_a_restart_where_there_is_a_journal(session, routes, people, tmp_path):
    from ontlas.journal import Journal
    from ontlas.web.areas import admin

    session.studio.changes.keep(Journal(tmp_path / "journal.jsonl"))
    root = people.users.users["root1"]
    before = list(admin._log)  # what tests before this one left in the process
    routes.POST["admin/user/save"](session, {"id": "new5", "name": "새로 다섯", "roles": ["viewer"], "password": "new-password-5", "new": True}, root)
    assert admin._log == before  # the journal holds it, not the process
    lines = [json.loads(x) for x in (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["kind"] for x in lines] == ["admin"] and lines[0]["what"] == "user" and "new-password-5" not in json.dumps(lines)
    d = routes.GET["admin/audit"](session, {}, root)
    assert d["kept"] and [r["text"] for r in d["rows"] if r["kind"] == "user"] == ["사용자 새로 다섯(new5) 추가 · 역할 조회자"]
    assert routes.GET["admin/overview"](session, {}, root)["recent"][0]["by"] == "관리 하나"


def test_only_an_admin_reads_the_admin_screens(session, routes, people):
    admin, maker = people.users.users["root1"], people.users.users["maker1"]
    for route in ("admin/users", "admin/settings", "admin/members", "admin/vocab", "admin/overview", "admin/audit", "admin/system",
                  "admin/security", "admin/ai", "admin/version"):
        assert routes.GET[route](session, {}, admin)
        with pytest.raises(PermissionError):
            routes.GET[route](session, {}, maker)
    from ontlas.web.team import NEEDS

    assert NEEDS["admin/user/save"] == NEEDS["admin/user/drop"] == NEEDS["admin/ai/test"] == "admin"


def test_a_user_is_added_changed_and_removed_and_the_file_keeps_it(session, routes, people, tmp_path):
    from ontlas.web.team import Users

    admin = people.users.users["root1"]
    save, drop = routes.POST["admin/user/save"], routes.POST["admin/user/drop"]
    out = save(session, {"id": "new1", "name": "새로 하나", "roles": ["editor", "viewer"], "password": "new-password-1", "new": True}, admin)
    assert next(u for u in out["users"] if u["id"] == "new1")["roles"] == ["viewer", "editor"]  # in the order of the levels
    token, _ = people.sign_in("new1", "new-password-1")
    assert next(u for u in routes.GET["admin/users"](session, {}, admin)["users"] if u["id"] == "new1")["signed_in"]

    save(session, {"id": "new1", "name": "새로 둘", "roles": ["approver"], "password": "", "new": False}, admin)
    kept = Users.load(tmp_path / "users.yaml").users["new1"]
    assert kept.name == "새로 둘" and kept.roles == ["approver"] and people.sign_in("new1", "new-password-1")  # the password stayed
    save(session, {"id": "new1", "name": "새로 둘", "roles": ["approver"], "password": "another-password-2", "new": False}, admin)
    assert people.sign_in("new1", "new-password-1") is None and people.sign_in("new1", "another-password-2")

    drop(session, {"id": "new1"}, admin)
    assert "new1" not in Users.load(tmp_path / "users.yaml").users and people.user(token) is None  # signed out at once
    said = [r["text"] for r in routes.GET["admin/audit"](session, {}, admin)["rows"] if r["kind"] == "user"]
    assert len(said) == 4 and "폐기" in said[0] and "추가 · 역할 조회자 · 편집자" in said[-1] and all("관리 하나" == r["by"] for r in routes.GET["admin/audit"](session, {}, admin)["rows"] if r["kind"] == "user")


def test_a_user_that_cannot_be_saved_is_refused_with_the_reason(session, routes, people):
    admin = people.users.users["root1"]
    save, drop = routes.POST["admin/user/save"], routes.POST["admin/user/drop"]
    ok = {"id": "new2", "name": "새로 셋", "roles": ["viewer"], "password": "new-password-2", "new": True}
    for wrong in ({"id": "a b"}, {"id": ""}, {"roles": []}, {"roles": ["owner"]}, {"password": "short"}, {"id": "maker1"}):
        with pytest.raises(ValueError):
            save(session, {**ok, **wrong}, admin)
    with pytest.raises(ValueError, match="찾지 못해 저장하지 못했습니다"):
        save(session, {**ok, "new": False}, admin)
    with pytest.raises(ValueError, match=r"아이디 maker1이 이미 있어"):
        save(session, {**ok, "id": "maker1"}, admin)
    with pytest.raises(ValueError, match="마지막 관리자"):
        save(session, {"id": "root1", "name": "관리 하나", "roles": ["editor"], "password": "", "new": False}, admin)
    with pytest.raises(ValueError, match="본인"):
        drop(session, {"id": "root1"}, admin)
    with pytest.raises(ValueError, match="찾지 못해 폐기하지 못했습니다"):
        drop(session, {"id": "nobody"}, admin)
    assert sorted(people.users.users) == ["maker1", "reader1", "root1"]


def test_without_a_users_file_there_is_nobody_to_manage(session, routes):
    d = routes.GET["admin/users"](session, {}, None)
    assert d["team"] is False and d["managed"] is False and d["users"] == [] and len(d["matrix"]) >= 8
    with pytest.raises(ValueError, match="--users"):
        routes.POST["admin/user/save"](session, {"id": "new3", "name": "x", "roles": ["viewer"], "password": "new-password-3", "new": True}, None)


def test_the_server_refuses_the_admin_routes_to_everyone_but_an_admin(tmp_path, routes):
    """Through the server itself: a GET by what the handler checks, a POST by what the route is registered to need."""
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession
    from ontlas.web.areas import admin
    from ontlas.web.server import RateLimit, make_handler
    from ontlas.web.team import Logins, TeamSessions, Users

    users = Users.load(tmp_path / "users.yaml")
    users.add("root1", "root-password-1", name="관리 하나", roles=["admin"])
    users.add("maker1", "maker-password-1", name="편집 하나", roles=["editor"])
    sessions = TeamSessions(lambda: StudioSession(load_studio(SHOP)), Logins(Users.load(tmp_path / "users.yaml")))
    admin.bind(sessions=sessions, logins=sessions.logins)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(sessions, ask_limit=RateLimit(5), quiet=True, logins=sessions.logins))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path, body=None, cookie=""):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json", "X-Ontlas-Request": "1", "Origin": base, **({"Cookie": cookie} if cookie else {})}
        try:
            with urllib.request.urlopen(urllib.request.Request(base + "/api/" + path, data=data, headers=headers)) as r:
                return r.status, json.loads(r.read()), r.headers.get("Set-Cookie", "")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}"), ""

    try:
        root = call("login", {"user": "root1", "password": "root-password-1"})[2].split(";")[0]
        maker = call("login", {"user": "maker1", "password": "maker-password-1"})[2].split(";")[0]
        assert call("admin/users", cookie=root)[0] == 200 and len(call("admin/users", cookie=root)[1]["users"]) == 2
        assert call("admin/users", cookie=maker)[0] == 403 and call("admin/users")[0] == 401
        new = {"id": "new4", "name": "새로 넷", "roles": ["viewer"], "password": "new-password-4", "new": True}
        assert call("admin/user/save", new, cookie=maker)[0] == 403
        assert call("admin/user/save", new, cookie=root)[0] == 200
        assert call("admin/user/drop", {"id": "new4"}, cookie=maker)[0] == 403 and call("admin/user/drop", {"id": "new4"}, cookie=root)[0] == 200
    finally:
        httpd.shutdown()
        httpd.server_close()
