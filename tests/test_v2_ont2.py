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
    out = call("POST", "ont2/draft", s, {"title": "  회원  표기 정리 ", "description": "고객을 회원으로 부릅니다"})
    assert out["title"] == "회원 표기 정리" and out["description"] == "고객을 회원으로 부릅니다"
    assert out["dirty"] is False  # a title alone is not a change
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    assert call("GET", "ont2/draft", s)["edits"] == 1
    change = s.manage_propose()["change"]
    assert change["module_label"] == "회원 표기 정리" and change["status"] == "approved"
    # the next request starts without a title: the one just deployed is not carried over as its own
    after = call("GET", "ont2/draft", s)
    assert after["title"] == "" and after["description"] == "" and after["current"] == d["current"] + 1
    with pytest.raises(ValueError, match="제목이 같아"):
        call("POST", "ont2/draft", s, {"title": "회원 표기 정리"})
    call("POST", "ont2/draft", s, {"title": "주문 표기 정리"})
    s.manage_edit("update_object", {"name": "Order", "label": "주문서"})
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
    assert back["kept"] == 3 and back["rollbacks"] == []  # the first version of the module had nothing to go back to
    assert set(back["titles"].values()) == {""}  # neither request was given a title: the label a workspace starts with is none


def test_a_rollback_to_an_earlier_version_is_named_as_one(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    s.manage_propose()
    s.manage_edit("update_object", {"name": "Customer", "label": "단골"})
    second = s.manage_propose()["change"]
    out = call("POST", "ont2/rollback", s, {"change": second["id"]})
    assert s.studio.onto.objects["Customer"].label == "회원"
    back = call("GET", "ont2/versions", s)["rollbacks"]
    assert [(b["change"], b["restored"]) for b in back] == [(out["change"]["id"], "0.1.0")]


def test_only_the_change_in_use_is_taken_back_and_not_over_unsent_edits(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    first = s.manage_propose()["change"]
    s.manage_edit("update_object", {"name": "Customer", "label": "단골"})
    with pytest.raises(ValueError, match="작성 중인 변경"):
        call("POST", "ont2/rollback", s, {"change": first["id"]})
    s.manage_propose()
    with pytest.raises(ValueError, match="가장 최근"):
        call("POST", "ont2/rollback", s, {"change": first["id"]})
