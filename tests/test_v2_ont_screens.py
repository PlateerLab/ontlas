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
    assert next(r for r in e["rows"] if r["label"] == "설명")["field"] == "description"  # the screen names it as its form does
    assert rows["주문 수량 · 이름"] == ("수량", "주문 수량")  # a Property's change is named by the Property
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
    # in the words of the form: the moves as moves, not the definition's text
    assert [r["label"] for r in e["rows"]] == ["허용 전이"]
    (row,) = e["rows"]
    back = f"{machine['states'][-1]} → {machine['states'][0]}"
    assert back in row["after"] and back not in row["before"] and "{" not in row["after"]
    assert [x["label"] for x in e["all"]] == ["상태 Property", "상태 값", "초기 상태", "허용 전이"]
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


def test_a_relation_written_here_says_its_source_in_the_draft_entry_before_it_is_applied(session):
    """The Relation form reads where a Relation is said from its history: one added in the request being written is
    not in the applied definition yet, so its source is in the unsent entry, and after approval in what stands."""
    from ontlas.web.routes import find

    history = find("GET", "item/history")
    session.manage_edit("add_link", {"name": "qaAbout", "source": "OrderItem", "target": "Order", "cardinality": "many_to_one"})
    session.manage_edit("update_link", {"name": "qaAbout", "cite": "검수 자료"})
    out = history(session, {"element": "link:qaAbout"}, None)
    assert out["now"] is None
    draft = next(e for e in out["entries"] if e["status"] == "draft")
    assert draft["after"]["cite"] == "검수 자료"
    assert session.manage_propose()["ok"]
    assert history(session, {"element": "link:qaAbout"}, None)["now"]["cite"] == "검수 자료"


def test_taking_out_states_that_are_not_there_is_refused(session):
    with pytest.raises(ValueError):
        session.manage_edit("delete_states", {"object": "Customer"})
    with pytest.raises(ValueError):
        session.manage_edit("delete_states", {"object": "Nobody"})


def test_a_rule_card_that_applies_to_the_entity_is_in_its_history(session):
    session.manage_edit("add_rule_card", {"id": "QA-LIMIT-1", "type": "limit", "statement": "주문 수량은 99개 이하",
                                          "applies_to": ["property:OrderItem.quantity"]})
    session.manage_edit("add_rule_card", {"id": "QA-OTHER-1", "type": "limit", "statement": "다른 Entity의 제한",
                                          "applies_to": ["object:Order"]})
    (e,) = _history(session, "OrderItem")
    rows = {r["label"]: (r["before"], r["after"]) for r in e["rows"]}
    assert rows == {"Restriction QA-LIMIT-1": (None, "주문 수량은 99개 이하")}  # the card of another Entity is not
    assert _history(session, "OrderItem", "state") == []
    assert session.manage_propose()["ok"]
    (filed,) = _history(session, "OrderItem")
    assert filed["deployed"] and [r["label"] for r in filed["rows"]] == ["Restriction QA-LIMIT-1"]


def test_each_reason_rides_on_the_change_it_was_filed_with(session):
    session.manage_edit("update_object", {"name": "OrderItem", "description": "첫째"})
    session.element_comment("object:OrderItem", "첫째 사유")
    assert session.manage_propose()["ok"]
    session.manage_edit("update_object", {"name": "OrderItem", "description": "둘째"})
    session.element_comment("object:OrderItem", "둘째 사유")
    assert session.manage_propose()["ok"]  # both within one minute: the time alone cannot tell them apart
    newer, older = _history(session, "OrderItem")
    assert [n["text"] for n in newer["notes"]] == ["둘째 사유"] and [n["text"] for n in older["notes"]] == ["첫째 사유"]


def _revert(session, kind: str, name: str, change: str) -> dict:
    from ontlas.web.routes import find

    return find("POST", "ont/revert")(session, {"kind": kind, "name": name, "change": change}, None)


def _filed(session) -> str:
    out = session.manage_propose()
    assert out["ok"] and not out["pending"], out.get("error")
    return out["change"]["id"]


def test_an_object_reverts_to_how_a_change_left_it(session):
    area = next(a for a in session.manage_state()["areas"] if a["name"] == "Customer")
    session.manage_edit("update_area", {"name": "Customer", "description": "첫째"})
    first = _filed(session)
    session.manage_edit("update_area", {"name": "Customer", "description": "둘째", "owner": "둘째 담당"})
    _filed(session)
    out = _revert(session, "object", "Customer", first)
    now = next(a for a in out["areas"] if a["name"] == "Customer")
    assert (now["description"], now["owner"]) == ("첫째", area["owner"])
    assert out["edits"] == ["update_area"] and next(a for a in out["areas"] if a["name"] == "Customer")["pending"]


def test_a_relation_reverts_and_the_edits_not_yet_sent_are_set_back_too(session):
    session.manage_edit("update_link", {"name": "placed", "label": "첫째"})
    first = _filed(session)
    session.manage_edit("update_link", {"name": "placed", "label": "둘째", "required": True})
    _filed(session)
    session.manage_edit("update_link", {"name": "placed", "cite": "작성 중 근거"})
    out = _revert(session, "relation", "placed", first)
    link = next(x for x in out["links"] if x["name"] == "placed")
    assert (link["label"], link["required"]) == ("첫째", False)
    from ontlas.web.routes import find

    assert find("GET", "ont/links")(session, {}, None)["links"]["placed"]["cite"] == ""


def test_an_entity_reverts_with_its_properties(session):
    _note(session)
    first = _filed(session)
    session.manage_edit("update_object", {"name": "Note", "description": "둘째"})
    session.manage_edit("update_property", {"object": "Note", "name": "kind", "label": "분류"})
    session.manage_edit("add_property", {"object": "Note", "name": "memo", "label": "메모", "type": "string"})
    _filed(session)
    out = _revert(session, "entity", "Note", first)
    props = {p["name"]: p for p in out["properties"] if p["object"] == "Note"}
    assert "memo" not in props and props["kind"]["label"] == "종류"
    assert next(o for o in out["objects"] if o["name"] == "Note")["description"] == ""
    assert sorted(out["edits"]) == ["delete_property", "update_object", "update_property"]


def test_a_state_machine_reverts_to_its_moves_then(session):
    machine = next(x for x in session.manage_state()["states"] if x["object"] == "OrderItem")
    keep = {k: machine[k] for k in ("property", "states", "initial")}
    back = {"from": machine["states"][-1], "to": machine["states"][0]}
    session.manage_edit("update_states", {"object": "OrderItem", **keep, "transitions": [*machine["transitions"], back]})
    first = _filed(session)
    session.manage_edit("update_states", {"object": "OrderItem", **keep, "transitions": machine["transitions"]})
    _filed(session)
    out = _revert(session, "state", "OrderItem", first)
    moves = next(x for x in out["states"] if x["object"] == "OrderItem")["transitions"]
    assert any(m["from"] == back["from"] and m["to"] == back["to"] for m in moves)
    assert out["edits"] == ["update_states"]


MOVES = {  # what OrderItem's moves say beyond their ends and action, put on a copy of the library
    "{from: NORMAL, to: RETURN_REQUESTED, action: requestReturn}":
        "{from: NORMAL, to: RETURN_REQUESTED, action: requestReturn, guard: {decision: returnEligibility, expect: {eligible: true}}}",
    "{from: RETURN_REQUESTED, to: RETURNED, action: completeReturn}":
        "{from: RETURN_REQUESTED, to: RETURNED, action: completeReturn, set: {delivered_at: $now},"
        " call: {url: 'https://oms.example/return/$key', method: POST}}",
    "{from: RETURN_REQUESTED, to: NORMAL, action: rejectReturn}":
        "{from: RETURN_REQUESTED, to: NORMAL, action: rejectReturn}\n        - {from: RETURNED, to: NORMAL, after: {days: 30, since: delivered_at}}",
}


@pytest.fixture
def guarded(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import shutil

    from ontlas.config import load_studio
    from ontlas.web import routes
    from ontlas.web.api import StudioSession

    shutil.copytree(LIB, tmp_path / "library")
    shutil.copytree(LIB.parent / "commerce", tmp_path / "commerce")  # its data sits beside it
    path = tmp_path / "library" / "commerce" / "1.0.0.yaml"
    text = path.read_bytes()
    for was, now in MOVES.items():
        assert was.encode() in text
        text = text.replace(was.encode(), now.encode())
    path.write_bytes(text)
    routes.load()
    return StudioSession(load_studio(tmp_path / "library" / "studio.yaml"))


def _moves(session) -> dict:
    sm = session._ws().composed().ontology.objects["OrderItem"].states
    return {(t.source, t.target, t.action): {k: getattr(t, k) for k in ("guard", "set", "call", "after") if getattr(t, k)}
            for t in sm.transitions}


def _form(session, extra: list[dict]) -> None:
    """Saved as the state transition form saves: the moves as the screen has them, ends and action only."""
    machine = next(x for x in session.manage_state()["states"] if x["object"] == "OrderItem")
    session.manage_edit("update_states", {"object": "OrderItem", **{k: machine[k] for k in ("property", "states", "initial")},
                                          "transitions": [*machine["transitions"], *extra]})


def test_saving_the_state_form_keeps_what_the_moves_say_beyond_their_ends(guarded):
    said = _moves(guarded)
    assert said[("NORMAL", "RETURN_REQUESTED", "requestReturn")]["guard"]["decision"] == "returnEligibility"
    assert set(said[("RETURN_REQUESTED", "RETURNED", "completeReturn")]) == {"set", "call"}
    assert said[("RETURNED", "NORMAL", "")]["after"] == {"days": 30, "since": "delivered_at"}
    _form(guarded, [{"from": "RETURNED", "to": "RETURN_REQUESTED", "action": ""}])
    now = _moves(guarded)
    assert {k: v for k, v in now.items() if k != ("RETURNED", "RETURN_REQUESTED", "")} == said
    assert ("RETURNED", "RETURN_REQUESTED", "") in now
    guarded.manage_edit("update_states", {  # a move that says its guard sends it, and an empty one takes it off
        "object": "OrderItem", "property": "item_status", "states": ["NORMAL", "RETURN_REQUESTED", "RETURNED"],
        "initial": "NORMAL", "transitions": [{"from": "NORMAL", "to": "RETURN_REQUESTED", "action": "requestReturn", "guard": {}}]})
    assert _moves(guarded) == {("NORMAL", "RETURN_REQUESTED", "requestReturn"): {}}
    with pytest.raises(ValueError):
        guarded.manage_edit("update_states", {"object": "OrderItem", "property": "item_status", "states": ["NORMAL", "RETURNED"],
                                              "transitions": [{"from": "NORMAL", "to": "RETURNED", "set": "x"}]})


def test_a_state_machine_reverts_with_what_its_moves_said_then(guarded):
    said = _moves(guarded)
    _form(guarded, [{"from": "RETURNED", "to": "RETURN_REQUESTED", "action": ""}])
    first = _filed(guarded)
    machine = next(x for x in guarded.manage_state()["states"] if x["object"] == "OrderItem")
    guarded.manage_edit("update_states", {"object": "OrderItem", **{k: machine[k] for k in ("property", "states", "initial")},
                                          "transitions": [{**t, "guard": {}, "set": {}, "call": {}, "after": {}} for t in machine["transitions"]]})
    _filed(guarded)
    assert not any(_moves(guarded).values())
    out = _revert(guarded, "state", "OrderItem", first)
    assert out["edits"] == ["update_states"]
    now = _moves(guarded)
    assert {k: v for k, v in now.items() if k != ("RETURNED", "RETURN_REQUESTED", "")} == said


def test_a_revert_needs_an_applied_change_and_something_to_set_back(session):
    session.manage_edit("update_area", {"name": "Customer", "description": "첫째"})
    first = _filed(session)
    with pytest.raises(ValueError, match="현재 값과 같아"):  # nothing changed it since
        _revert(session, "object", "Customer", first)
    with pytest.raises(ValueError):
        _revert(session, "object", "Customer", "")
    with pytest.raises(ValueError):
        _revert(session, "rule", "Customer", first)
    with pytest.raises(ValueError, match="배포된 변경이 아니어서"):  # a change that did not touch it
        _revert(session, "relation", "placed", first)
    from ontlas.web.routes import find
    from ontlas.web.team import NEEDS

    assert find("POST", "ont/revert") is not None and NEEDS["ont/revert"] == "editor"


def test_a_revert_that_cannot_be_made_leaves_no_edit_behind(session):
    session.manage_edit("update_link", {"name": "placed", "label": "첫째"})
    first = _filed(session)
    session.manage_edit("update_link", {"name": "placed", "label": "둘째", "cardinality": "many_to_many"})
    _filed(session)
    before = len(session._ws().edits)
    import ontlas.web.areas.ont as ont

    real = ont._fields
    ont._fields = lambda want, now, keys, blank=None: {**real(want, now, keys, blank), "cardinality": "never"}
    try:
        with pytest.raises(ValueError):
            _revert(session, "relation", "placed", first)
    finally:
        ont._fields = real
    assert len(session._ws().edits) == before and not session._ws().dirty


def test_a_property_its_parent_gives_reads_again_as_the_parent_says(session):
    parent = next(p for p in session.manage_state()["properties"] if p["object"] == "Customer" and p["name"] == "name")
    assert parent["inherited"]  # Customer has it from the Entity it specialises
    session.manage_edit("update_object", {"name": "Customer", "description": "첫째"})
    first = _filed(session)
    session.manage_edit("update_property", {"object": "Customer", "name": "name", "label": "고객 이름"})
    _filed(session)
    out = _revert(session, "entity", "Customer", first)  # the Property cannot go: it reads as its parent's again
    assert next(p for p in out["properties"] if p["object"] == "Customer" and p["name"] == "name")["label"] == parent["label"]
    assert out["edits"] == ["update_property"]


# ---- what a move needs to be taken (its guard), and how a Property stands beside the standard vocabularies --------------

def _states(session) -> dict:
    from ontlas.web.routes import find

    return find("GET", "ont/states")(session, {}, None)["states"]


def test_each_move_says_what_it_needs_to_be_taken_as_held_and_in_words(guarded):
    moves = _states(guarded)["OrderItem"]
    asked = next(m for m in moves if (m["from"], m["to"]) == ("NORMAL", "RETURN_REQUESTED"))
    assert asked["guard"] == {"decision": "returnEligibility", "expect": {"eligible": True}}
    assert asked["said"] == "반품 가능 여부 · 결과 가능"  # the table's first true or false result is its 결과
    assert [m["said"] for m in moves if m is not asked] == ["", "", ""]
    assert "OrderItem" in _states(guarded) and "Customer" not in _states(guarded)  # only the Entities with states


def test_a_guard_the_state_form_sends_is_kept_said_and_read_in_the_history(guarded):
    guarded.manage_edit("add_property", {"object": "OrderItem", "name": "inspected", "label": "검수 완료", "type": "boolean"})
    machine = next(x for x in guarded.manage_state()["states"] if x["object"] == "OrderItem")
    want = {("NORMAL", "RETURN_REQUESTED"): {"decision": "returnEligibility", "expect": {"eligible": False}},
            ("RETURN_REQUESTED", "RETURNED"): {"property": "inspected"}}
    guarded.manage_edit("update_states", {"object": "OrderItem", **{k: machine[k] for k in ("property", "states", "initial")},
                                          "transitions": [{**t, "guard": want.get((t["from"], t["to"]), {})} for t in machine["transitions"]]})
    said = {(m["from"], m["to"]): m["said"] for m in _states(guarded)["OrderItem"]}
    assert said[("NORMAL", "RETURN_REQUESTED")] == "반품 가능 여부 · 결과 불가"
    assert said[("RETURN_REQUESTED", "RETURNED")] == "검수 완료 예"  # a true or false Property of the Entity must be true
    assert _moves(guarded)[("RETURN_REQUESTED", "RETURNED", "completeReturn")]["guard"] == {"property": "inspected"}
    assert set(_moves(guarded)[("RETURN_REQUESTED", "RETURNED", "completeReturn")]) == {"guard", "set", "call"}  # the rest kept
    (e,) = _history(guarded, "OrderItem", "state")
    rows = {r["label"]: (r["before"], r["after"]) for r in e["rows"]}
    assert rows["전이 조건"][0] == "NORMAL → RETURN_REQUESTED · 반품 가능 여부 · 결과 가능"
    assert rows["전이 조건"][1].startswith("NORMAL → RETURN_REQUESTED · 반품 가능 여부 · 결과 불가, RETURN_REQUESTED → RETURNED · ")
    assert "전이 조건" in [x["label"] for x in e["all"]]


def test_the_vocabulary_route_is_registered_with_the_states_route():
    from ontlas.web import routes

    routes.load()
    assert routes.find("GET", "ont/vocab") is not None and routes.find("GET", "ont/states") is not None


def test_a_property_stands_beside_the_vocabulary_it_is_aligned_to_or_is_the_definitions_own(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import shutil

    from ontlas.config import load_studio
    from ontlas.web import routes
    from ontlas.web.api import StudioSession

    shutil.copytree(LIB, tmp_path / "library")
    shutil.copytree(LIB.parent / "commerce", tmp_path / "commerce")
    path = tmp_path / "library" / "commerce" / "1.0.0.yaml"
    text, was = path.read_bytes(), "      brand: {type: string, label: 브랜드}".encode()
    assert text.count(was) == 1
    path.write_bytes(text.replace(was, "      brand: {type: string, label: 브랜드, aligned: [https://schema.org/brand]}".encode()))
    routes.load()
    session = StudioSession(load_studio(tmp_path / "library" / "studio.yaml"))
    vocab = lambda: routes.find("GET", "ont/vocab")(session, {}, None)  # noqa: E731
    first = vocab()
    assert first["properties"]["Product.brand"] == {"vocab": "schema.org", "name": "brand", "iri": "https://schema.org/brand"}
    assert "Product.name" not in first["properties"] and first["prefix"] == ""  # no name of the definition's own has a prefix
    # the prefix the definition's own names are written with: the one its terms' English names use, not a standard's
    session.lexicon_edit("add_term", {"term": "포장 메모", "english": "shop:wrapNote"})
    session.lexicon_edit("add_term", {"term": "선물 포장", "english": "shop:giftWrap"})
    session.lexicon_edit("add_term", {"term": "상품 이름", "english": "schema:name"})
    session.lexicon_edit("add_term", {"term": "상품 설명", "english": "schema:description"})
    session.lexicon_edit("add_term", {"term": "상품 상표", "english": "schema:brand"})
    assert vocab()["prefix"] == "shop"
