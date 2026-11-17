"""What the Object, Entity and state transition screens ask of the server: an Entity's history with its Properties'
in one list, a state machine's history as the part that touched the states, and the edit that takes a state machine
out."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "examples" / "library"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import routes
    from ontlas.web.api import StudioSession

    routes.load()
    return StudioSession(load_studio(LIB / "studio.yaml"))


def _history(session, name: str, kind: str = "entity") -> list[dict]:
    from ontlas.web.routes import find

    return find("GET", "ont/history")(session, {"name": name, "kind": kind}, None)["entries"]


def _note(session) -> None:
    session.manage_edit("add_object", {"name": "Note", "label": "메모", "key": "note_id", "area": "Order", "properties": {
        "note_id": {"type": "string"}, "kind": {"type": "enum", "label": "종류", "values": ["OPEN", "DONE"]}}})


def test_the_history_route_is_registered_with_the_areas():
    from ontlas.web import routes

    routes.load()
    assert routes.find("GET", "ont/history") is not None and routes.find("POST", "ont/history") is None


def test_an_entity_with_no_change_has_no_history(session):
    assert _history(session, "OrderItem") == []


def test_unsent_edits_are_the_first_entry_with_the_entity_and_its_properties_together(session):
    session.manage_edit("update_object", {"name": "OrderItem", "description": "주문에 담긴 상품 한 줄"})
    session.manage_edit("update_property", {"object": "OrderItem", "name": "quantity", "label": "주문 수량"})
    session.manage_edit("add_property", {"object": "OrderItem", "name": "memo", "label": "메모", "type": "string"})
    (e,) = _history(session, "OrderItem")
    assert (e["status"], e["status_label"], e["deployed"], e["change"], e["kind"]) == ("draft", "작성 중", False, "", "changed")
    rows = {r["label"]: (r["before"], r["after"]) for r in e["rows"]}
    assert rows["설명"] == (None, "주문에 담긴 상품 한 줄")
    assert rows["주문 수량 · 라벨"] == ("수량", "주문 수량")  # a Property's change is named by the Property
    assert rows["Property 메모"] == (None, "memo")  # a Property that was added
    assert {"label": "key", "value": "item_id"} in e["all"]


def test_a_filed_change_is_an_entry_with_its_request_and_the_edits_after_it_come_first(session):
    session.manage_edit("update_object", {"name": "OrderItem", "description": "주문에 담긴 상품 한 줄"})
    out = session.manage_propose()  # one visitor is both sides: filed and applied
    assert out["ok"] and not out["pending"]
    (filed,) = _history(session, "OrderItem")
    assert (filed["change"], filed["status"], filed["deployed"]) == (out["change"]["id"], "approved", True)
    assert filed["version"] and filed["at"]
    session.manage_edit("update_object", {"name": "OrderItem", "description": "주문상품 한 줄"})
    draft, older = _history(session, "OrderItem")
    assert draft["status"] == "draft" and older["change"] == out["change"]["id"]
    assert [r["after"] for r in draft["rows"]] == ["주문상품 한 줄"]


def test_a_new_entity_reads_as_added(session):
    _note(session)
    (e,) = _history(session, "Note")
    assert e["kind"] == "added"
    assert {"Property 종류", "Property note_id"} <= {r["label"] for r in e["rows"]}


def test_a_state_machines_history_is_only_what_touched_the_states(session):
    session.manage_edit("update_object", {"name": "OrderItem", "description": "주문에 담긴 상품 한 줄"})
    assert _history(session, "OrderItem", "state") == []  # the Entity changed, its states did not
    machine = next(x for x in session.manage_state()["states"] if x["object"] == "OrderItem")
    session.manage_edit("update_states", {"object": "OrderItem", "property": machine["property"], "states": machine["states"],
                                          "initial": machine["initial"],
                                          "transitions": [*machine["transitions"], {"from": machine["states"][-1], "to": machine["states"][0]}]})
    (e,) = _history(session, "OrderItem", "state")
    assert e["rows"] and all(r["label"].startswith("상태 전이") for r in e["rows"])
    assert all(x["label"].startswith("states.") for x in e["all"])
    assert len(_history(session, "OrderItem")[0]["rows"]) > len(e["rows"])  # the Entity's own history has the description too


def test_the_note_left_with_a_change_rides_on_its_entry(session):
    session.manage_edit("update_object", {"name": "OrderItem", "description": "주문에 담긴 상품 한 줄"})
    session.element_comment("object:OrderItem", "정의 문구 보완")
    (e,) = _history(session, "OrderItem")
    assert [n["text"] for n in e["notes"]] == ["정의 문구 보완"]


def test_history_needs_a_name_and_a_known_kind(session):
    from ontlas.web.routes import find

    route = find("GET", "ont/history")
    with pytest.raises(ValueError):
        route(session, {"name": "", "kind": "entity"}, None)
    with pytest.raises(ValueError):
        route(session, {"name": "OrderItem", "kind": "relation"}, None)


def test_a_state_machine_made_here_is_taken_out_whole(session):
    _note(session)
    session.manage_edit("update_states", {"object": "Note", "property": "kind", "states": ["OPEN", "DONE"], "initial": "OPEN",
                                          "transitions": [{"from": "OPEN", "to": "DONE"}]})
    assert "Note" in [x["object"] for x in session.manage_state()["states"]]
    out = session.manage_edit("delete_states", {"object": "Note"})
    assert out["edit"] == {"op": "delete_states", "target": "states:Note", "took_out": []}
    assert "Note" not in [x["object"] for x in out["states"]]
    assert "Note" in [x["name"] for x in out["objects"]]  # the Entity stays; only its states go


def test_another_modules_state_machine_is_removed_by_this_module_and_says_what_went_with_it(session):
    out = session.manage_edit("delete_states", {"object": "OrderItem"})
    assert "OrderItem" not in [x["object"] for x in out["states"]]
    assert out["edit"]["target"] == "states:OrderItem"
    assert any(x.startswith("action:") for x in out["edit"]["took_out"])  # the action that moved the state cannot stand without it
    session.manage_undo()
    assert "OrderItem" in [x["object"] for x in session.manage_state()["states"]]


def test_taking_out_states_that_are_not_there_is_refused(session):
    with pytest.raises(ValueError):
        session.manage_edit("delete_states", {"object": "Customer"})
    with pytest.raises(ValueError):
        session.manage_edit("delete_states", {"object": "Nobody"})
