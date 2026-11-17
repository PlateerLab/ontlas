"""What a library already holds is edited and taken out from the screens: a Standard rule card and a module's query
through the edits that wait in the workspace, an AXIOM card as a change request to its own module."""
from pathlib import Path

import pytest

from ontlas.config import load_studio
from ontlas.web import routes
from ontlas.web.api import StudioSession

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"


@pytest.fixture()
def session():
    routes.load()
    return StudioSession(load_studio(SHOP))


def card(s, cid):
    return next((c for c in s.semantic_state()["cards"] if c["id"] == cid), None)


def test_a_standard_rule_card_is_edited_and_removed_as_the_workspaces_change(session):
    assert card(session, "return-request-moves")["layer"] == "standard"
    session.manage_edit("update_rule_card", {"id": "return-request-moves", "owner": "반품 운영팀"})
    got = card(session, "return-request-moves")
    assert got["owner"] == "반품 운영팀" and got["layer"] == "standard" and got["pending"]
    res = session.manage_propose()  # one visitor is both sides: filed and approved
    assert res["ok"] and card(session, "return-request-moves")["owner"] == "반품 운영팀"

    session.manage_edit("delete_rule_card", {"id": "return-request-moves"})
    assert "return-request-moves" in session.semantic_state()["removed"]
    assert session.manage_propose()["ok"] and card(session, "return-request-moves") is None


def test_a_query_a_module_defines_is_changed_by_extending_it(session):
    before = session.studio.onto.queries["allParties"]
    session.manage_edit("update_query", {"name": "allParties", "label": "당사자 전체", "description": "고객과 판매자"})
    assert session.manage_propose()["ok"]
    after = session.studio.onto.queries["allParties"]
    assert after.label == "당사자 전체" and after.query == before.query

    session.manage_edit("delete_query", {"name": "allParties"})
    assert session.manage_propose()["ok"] and "allParties" not in session.studio.onto.queries


def test_an_axiom_card_is_changed_as_a_request_to_its_own_module(session):
    change = routes.find("POST", "sem/axiom/card")
    with pytest.raises(ValueError):
        session.manage_edit("update_rule_card", {"id": "law-return-min-days", "owner": "법무팀"})
    with pytest.raises(ValueError):
        change(session, {"id": "return-request-moves", "fields": {"owner": "x"}}, None)  # not an AXIOM card
    with pytest.raises(ValueError):
        change(session, {"id": "no-such-card", "fields": {}}, None)

    out = change(session, {"id": "law-return-min-days", "fields": {"owner": "준법지원팀"}}, None)
    cr = out["change"]
    assert cr["status"] == "pending" and cr["module"] == out["module"] == card(session, "law-return-min-days")["module"]
    assert card(session, "law-return-min-days")["owner"] != "준법지원팀"  # nothing moves until it is approved
    assert session.decide_change(cr["id"], True)["ok"]
    assert card(session, "law-return-min-days")["owner"] == "준법지원팀"

    gone = change(session, {"id": "law-price-shown", "remove": True}, None)["change"]
    assert session.decide_change(gone["id"], True)["ok"] and card(session, "law-price-shown") is None
