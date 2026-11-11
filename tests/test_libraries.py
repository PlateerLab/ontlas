"""Libraries a deployment offers: a visitor switches between studio files, each keeping its own pipelines."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
SMALL = ROOT / "examples" / "commerce" / "studio.yaml"


@pytest.fixture()
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import library_entry
    from ontlas.web.api import StudioSession

    first = load_studio(SHOP)
    s = StudioSession(first)
    s.libraries = [library_entry("l1", SHOP, first), library_entry("l2", SMALL, load_studio(SMALL))]
    return s


def test_the_state_lists_the_libraries_and_the_one_open(session):
    st = session.state()
    assert [x["id"] for x in st["libraries"]] == ["l1", "l2"] and st["library_id"] == "l1"
    assert st["libraries"][0]["modules"] == 8 and st["libraries"][0]["source"] == "sqlite"
    assert st["libraries"][1]["label"] == "커머스 온톨로지 예시"


def test_switching_opens_the_other_studio_and_coming_back_finds_the_first_as_it_was(session):
    first = session.studio
    session.pipelines.append({"id": "p2", "label": "초안", "studio": first, "origin": {}, "rows": [], "log": []})
    session.library_use("l2")
    assert session.studio is not first and session.library_id == "l2"
    assert [p["id"] for p in session.pipelines] == ["p1"]  # the other library starts from its own file
    assert session.state()["title"] != "" and "Order" in session.studio.onto.objects
    session.library_use("l1")
    assert session.studio is first and [p["id"] for p in session.pipelines] == ["p1", "p2"]


def test_an_unknown_library_is_refused(session):
    with pytest.raises(LookupError):
        session.library_use("l9")


def test_a_served_studio_offers_its_libraries_to_every_visitor(monkeypatch):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import ontlas.web as web

    got = {}
    monkeypatch.setattr(web, "serve", lambda build, **kw: got.setdefault("session", build()))
    web.serve_config(SHOP, libraries=[SMALL])
    s = got["session"]
    assert [(x["id"], x["label"]) for x in s.libraries] == [("l1", "이커머스 표준 온톨로지 · 이커머스 운영 온톨로지"), ("l2", "커머스 온톨로지 예시")]
