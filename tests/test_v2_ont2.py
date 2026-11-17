"""The routes of the later 온톨로지 매니저 screens: the request being written, a term's history, taking a version back."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "examples"
TERM = "고객@object:Customer"


@pytest.fixture()
def session(monkeypatch):
    """One visitor's session on the example shop, as the page serves it."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import ontlas.web as web
    from ontlas.web import routes

    routes.load()
    got = {}
    monkeypatch.setattr(web, "serve", lambda build, **kw: got.setdefault("session", build()))
    web.serve_config(ROOT / "library" / "studio.yaml")
    return got["session"]


def call(method: str, route: str, s, a: dict | None = None):
    from ontlas.web import routes

    return routes.find(method, route)(s, a or {}, None)


def test_the_routes_are_registered_with_what_they_need():
    from ontlas.web import routes
    from ontlas.web.team import NEEDS

    routes.load()
    assert all(routes.find("GET", r) for r in ("ont2/draft", "ont2/term/history", "ont2/versions"))
    assert NEEDS["ont2/draft"] == "editor" and NEEDS["ont2/rollback"] == "approver"


def test_the_request_being_written_takes_a_title_and_keeps_it_when_sent(session):
    s = session
    d = call("GET", "ont2/draft", s)
    assert d["dirty"] is False and d["edits"] == 0 and d["next"] == d["current"] + 1 and d["title"] == ""
    with pytest.raises(ValueError, match="포함 항목이 없어"):  # a title with nothing under it would wait unseen
        call("POST", "ont2/draft", s, {"title": "회원 표기 정리"})
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    out = call("POST", "ont2/draft", s, {"title": "  회원  표기 정리 ", "description": "고객을 회원으로 부릅니다"})
    assert out["title"] == "회원 표기 정리" and out["description"] == "고객을 회원으로 부릅니다"
    assert out["edits"] == 1  # a title is no edit of its own
    change = s.manage_propose()["change"]
    assert change["module_label"] == "회원 표기 정리" and change["status"] == "approved"
    # the next request starts without a title: the one just deployed is not carried over as its own
    after = call("GET", "ont2/draft", s)
    assert after["title"] == "" and after["description"] == "" and after["current"] == d["current"] + 1
    s.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    with pytest.raises(ValueError, match="제목이 같아"):
        call("POST", "ont2/draft", s, {"title": "회원 표기 정리"})
    call("POST", "ont2/draft", s, {"title": "주문 표기 정리"})
    second = s.manage_propose()["change"]
    titles = call("GET", "ont2/versions", s)["titles"]
    assert titles == {change["id"]: "회원 표기 정리", second["id"]: "주문 표기 정리"}  # each keeps the title it was sent with


def test_a_title_is_needed_and_has_a_length(session):
    with pytest.raises(ValueError, match="제목"):
        call("POST", "ont2/draft", session, {"title": " "})
    with pytest.raises(ValueError, match="60자"):
        call("POST", "ont2/draft", session, {"title": "가" * 61})


def test_a_terms_history_reads_the_edits_waiting_then_the_change_that_carried_them(session):
    s = session
    assert call("GET", "ont2/term/history", s, {"id": TERM})["entries"] == []
    s.lexicon_edit("update_term", {"id": TERM, "synonyms": ["구매자", "회원님"]})
    waiting = call("GET", "ont2/term/history", s, {"id": TERM})["entries"]
    assert [e["status"] for e in waiting] == ["draft"] and waiting[0]["kind"] == "changed"
    assert waiting[0]["fields"] == [{"field": "synonyms", "label": "동의어", "before": "구매자", "after": "구매자, 회원님"}]
    s.manage_propose()
    sent = call("GET", "ont2/term/history", s, {"id": TERM})["entries"]
    assert [(e["status"], e["deployed"], e["change"]) for e in sent] == [("approved", True, "C1")]
    assert sent[0]["fields"][0]["after"] == "구매자, 회원님"
    # one field's changes only: the synonyms moved, the pairs not to be swapped did not
    assert len(call("GET", "ont2/term/history", s, {"id": TERM, "field": "synonyms"})["entries"]) == 1
    assert call("GET", "ont2/term/history", s, {"id": TERM, "field": "confusable"})["entries"] == []


def test_a_term_added_and_taken_out_reads_as_added_and_removed(session):
    s = session
    s.lexicon_edit("add_term", {"term": "단골", "definition": "자주 주문하는 고객", "synonyms": ["충성 고객"]})
    s.manage_propose()
    s.lexicon_edit("delete_term", {"id": "단골"})
    kinds = [e["kind"] for e in call("GET", "ont2/term/history", s, {"id": "단골"})["entries"]]
    assert kinds == ["removed", "added"]


def test_a_history_needs_a_term_and_a_field_it_knows(session):
    with pytest.raises(ValueError):
        call("GET", "ont2/term/history", session, {})
    with pytest.raises(ValueError):
        call("GET", "ont2/term/history", session, {"id": TERM, "field": "nothing"})


def test_the_last_deployed_change_is_taken_back_as_a_new_version(session):
    s = session
    label = s.studio.onto.objects["Customer"].label
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    first = s.manage_propose()["change"]
    assert s.studio.onto.objects["Customer"].label == "회원" and s._space_version()["number"] == 2
    out = call("POST", "ont2/rollback", s, {"change": first["id"]})
    assert out["ok"] and out["pending"] is False and out["change"]["status"] == "approved"
    assert s.studio.onto.objects["Customer"].label == label  # as it read before the change
    assert s._space_version()["number"] == 3  # the rollback is a version of its own
    back = call("GET", "ont2/versions", s)
    # the module held nothing before the change, so no earlier version is brought back: the rollback names the change
    assert back["kept"] == 3 and [(b["change"], b["of"], b["restored"]) for b in back["rollbacks"]] == [(out["change"]["id"], first["id"], "")]
    # the change was given no title (the label a workspace starts with is none); the rollback is called by what it took back
    assert back["titles"] == {first["id"]: "", out["change"]["id"]: f"{first['id']} 롤백"}


def test_a_rollback_to_an_earlier_version_is_named_as_one(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    s.manage_propose()
    s.manage_edit("update_object", {"name": "Customer", "label": "단골"})
    second = s.manage_propose()["change"]
    out = call("POST", "ont2/rollback", s, {"change": second["id"]})
    assert s.studio.onto.objects["Customer"].label == "회원"
    back = call("GET", "ont2/versions", s)["rollbacks"]
    assert [(b["change"], b["of"], b["restored"]) for b in back] == [(out["change"]["id"], second["id"], "0.1.0")]


def test_only_the_change_in_use_is_taken_back_and_not_over_unsent_edits(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    first = s.manage_propose()["change"]
    s.manage_edit("update_object", {"name": "Customer", "label": "단골"})
    with pytest.raises(ValueError, match="작성 중인 변경"):
        call("POST", "ont2/rollback", s, {"change": first["id"]})
    s.manage_propose()
    with pytest.raises(ValueError, match="최근 배포 변경 요청이 아니어서"):
        call("POST", "ont2/rollback", s, {"change": first["id"]})


def test_a_request_sent_without_a_description_leaves_nothing_written_behind(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    call("POST", "ont2/draft", s, {"title": "회원 표기 정리"})
    assert call("GET", "ont2/draft", s)["description"] == ""
    s.manage_propose()
    after = call("GET", "ont2/draft", s)
    assert after["dirty"] is False and after["edits"] == 0  # the module read again is the one deployed, not an edit


def test_a_change_request_names_the_terms_it_writes(session):
    s = session
    s.lexicon_edit("add_term", {"term": "단골", "definition": "자주 주문하는 고객", "status": "draft"})
    s.lexicon_edit("update_term", {"id": TERM, "synonyms": ["구매자", "회원님"]})
    first = s.manage_propose()["change"]
    terms = {t["term"]: t for t in call("GET", "ont2/change/terms", s, {"id": first["id"]})["terms"]}
    assert terms["단골"]["change"] == "added" and terms["고객"]["change"] == "changed"
    assert [f["label"] for f in terms["고객"]["fields"]] == ["동의어"]
    status = next(f for f in terms["단골"]["fields"] if f["field"] == "status")
    assert status["after"] == "초안"  # a status is said in words
    back = call("POST", "ont2/rollback", s, {"change": first["id"]})["change"]
    taken = call("GET", "ont2/change/terms", s, {"id": back["id"]})["terms"]
    assert {t["term"]: t["change"] for t in taken} == {"단골": "removed", "고객": "changed"}
    with pytest.raises(ValueError):
        call("GET", "ont2/change/terms", s, {"id": "C99"})


def test_a_terms_history_reads_every_field_in_words(session):
    s = session
    s.lexicon_edit("update_term", {"id": TERM, "status": "review"})
    e = call("GET", "ont2/term/history", s, {"id": TERM})["entries"][0]
    assert ("상태", "사용 중", "확인 필요") in [(f["label"], f["before"], f["after"]) for f in e["fields"]]
    said = {f["label"]: f["value"] for f in e["all"]}
    assert said["용어"] == "고객" and said["상태"] == "확인 필요" and said["연결 개념"].startswith("Entity · ")


def test_a_rollback_keeps_its_title_while_it_waits_and_after_it_is_rejected(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    first = s.manage_propose()["change"]
    s.studio.changes.self_approve = False  # a team: the rollback waits for someone else
    back = call("POST", "ont2/rollback", s, {"change": first["id"]})
    assert back["pending"] is True
    assert call("GET", "ont2/versions", s)["titles"][back["change"]["id"]] == f"{first['id']} 롤백"
    s.decide_change(back["change"]["id"], False, "근거 부족")
    assert s.studio.changes.requests[back["change"]["id"]].reason == "근거 부족"
    assert call("GET", "ont2/versions", s)["titles"][back["change"]["id"]] == f"{first['id']} 롤백"


def test_why_a_term_was_edited_goes_with_the_change_that_carried_it_whatever_the_clock(session):
    s = session
    assert s.studio.now() == s.studio.now()  # the example's clock stands still: every note and request has one time
    for owner, why in (("첫팀", "첫 변경"), ("둘째팀", "둘째 변경")):
        s.lexicon_edit("update_term", {"id": TERM, "owner": owner})
        call("POST", "ont2/term/note", s, {"id": TERM, "fields": ["owner"], "text": why})
        s.manage_propose()
    s.lexicon_edit("update_term", {"id": TERM, "synonyms": ["구매자", "회원님"]})
    call("POST", "ont2/term/note", s, {"id": TERM, "fields": ["synonyms"], "text": "동의어 추가"})
    said = lambda field="": [(e["change"], [n["text"] for n in e["notes"]]) for e in call("GET", "ont2/term/history", s, {"id": TERM, "field": field})["entries"]]  # noqa: E731
    assert said() == [("", ["동의어 추가"]), ("C2", ["둘째 변경"]), ("C1", ["첫 변경"])]  # the unsent edit first
    assert said("synonyms") == [("", ["동의어 추가"])]  # one field: the reasons of that field's edits only
    s.manage_propose()
    assert said("synonyms") == [("C3", ["동의어 추가"])]
    with pytest.raises(ValueError, match="변경 사유"):
        call("POST", "ont2/term/note", s, {"id": TERM, "text": " "})
