"""What the rules screens ask: the rules that wait for review and a reviewer's word on one, and how a rule card or a
named value came to read as it does."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from ontlas.config import load_studio
from ontlas.manage import EditError
from ontlas.web import routes
from ontlas.web.api import StudioSession
from ontlas.web.team import NEEDS

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"


@pytest.fixture()
def session():
    routes.load()
    return StudioSession(load_studio(SHOP))


def get(s, route, **a):
    return routes.find("GET", route)(s, a, None)


def post(s, route, **a):
    return routes.find("POST", route)(s, a, None)


def draft_card(s, cid="probe-window", **more):
    s.manage_edit("add_rule_card", {"id": cid, "type": "decide", "statement": "시험 규칙", "conditions": ["조건 하나"],
                                    "result": "결과", "source": "시험 문서 1조", "applies_to": ["object:OrderItem"], **more})


def test_the_routes_are_registered_and_deciding_needs_an_approver():
    routes.load()
    assert routes.find("GET", "sem/drafts") and routes.find("GET", "sem/history") and routes.find("POST", "sem/draft/decide")
    assert NEEDS["sem/draft/decide"] == "approver"


def test_what_waits_is_listed_with_its_layer_its_grounds_and_the_objects_it_is_about(session):
    out = get(session, "sem/drafts")
    assert out["counts"] == {"waiting": 1, "approved": 0, "rejected": 0} and out["axiom"] == 1 and out["decidable"] == 0
    (d,) = out["drafts"]
    assert d["ref"] == "card:law-price-shown" and d["layer"] == "axiom" and d["state"] == "waiting" and not d["decidable"]
    assert d["legal_review"] == "pending" and d["areas"] and d["source"]
    assert out["modules"] and out["parameters"] == len(session.studio.onto.parameters)
    assert [c["id"] for c in out["conflicts"]] == ["vipExchangeWindow"]  # the one two documents answer differently


def test_a_custom_draft_is_approved_with_what_the_reviewer_corrected(session):
    draft_card(session)
    out = get(session, "sem/drafts")
    mine = next(d for d in out["drafts"] if d["id"] == "probe-window")
    assert mine["state"] == "waiting" and mine["decidable"] and mine["areas"] == ["주문"] and out["counts"]["waiting"] == 2
    out = post(session, "sem/draft/decide", ref="card:probe-window", verdict="approve", fields={"result": "고친 결과", "conditions": ["조건 하나", "조건 둘"]})
    assert out["ok"] and out["counts"]["waiting"] == 1
    card = next(c for c in session.semantic_state()["cards"] if c["id"] == "probe-window")
    assert card["status"] == "approved" and card["result"] == "고친 결과" and card["conditions"] == ["조건 하나", "조건 둘"]
    # a card made and approved in the same pending edits was never a waiting draft of the applied definition
    assert not [d for d in out["drafts"] if d["id"] == "probe-window"]


def test_a_draft_of_the_applied_definition_moves_between_the_three_lists(session):
    draft_card(session)
    draft_card(session, "probe-two")
    assert session.manage_propose()["ok"]  # one visitor is both sides: the two drafts are in the definition now
    assert {d["id"] for d in get(session, "sem/drafts")["drafts"] if d["decidable"]} == {"probe-window", "probe-two"}
    out = post(session, "sem/draft/decide", ref="card:probe-window", verdict="approve")
    out = post(session, "sem/draft/decide", ref="card:probe-two", verdict="reject")
    state = {d["id"]: d["state"] for d in out["drafts"]}
    assert state["probe-window"] == "approved" and state["probe-two"] == "rejected"
    assert out["counts"] == {"waiting": 1, "approved": 1, "rejected": 1}
    assert "probe-two" in session.semantic_state()["removed"]
    session.manage_discard()
    assert get(session, "sem/drafts")["counts"] == {"waiting": 3, "approved": 0, "rejected": 0}


def test_an_axiom_draft_is_not_decided_here_and_the_page_says_why(session):
    with pytest.raises(ValueError, match="법무 검토"):
        post(session, "sem/draft/decide", ref="card:law-price-shown", verdict="approve")
    with pytest.raises(ValueError, match="승인 또는 거절"):
        post(session, "sem/draft/decide", ref="card:law-price-shown", verdict="later")
    with pytest.raises(ValueError, match="찾지 못했습니다"):
        post(session, "sem/draft/decide", ref="card:no-such-card", verdict="approve")
    assert not session._ws().dirty


def test_a_draft_row_of_a_decision_table_is_approved_or_taken_out(session):
    session.manage_edit("add_rule", {"decision": "shippingFee", "id": "probe-row", "when": {"order_total": {"op": "gte", "value": "900000"}},
                                     "then": {"fee": 0, "reason": "시험"}, "status": "draft", "first": True})
    assert session.manage_propose()["ok"]
    out = get(session, "sem/drafts")
    row = next(d for d in out["drafts"] if d["ref"] == "decision:shippingFee#probe-row")
    assert row["kind"] == "executable" and row["decidable"] and row["areas"] == ["주문"]
    out = post(session, "sem/draft/decide", ref=row["ref"], verdict="approve")
    rule = next(r for r in session.manage_state()["decisions"][1]["rules"] if r["id"] == "probe-row")
    assert rule["status"] == "approved" and out["counts"]["approved"] == 1
    session.manage_discard()
    out = post(session, "sem/draft/decide", ref=row["ref"], verdict="reject")
    assert out["counts"]["rejected"] == 1
    assert "probe-row" not in [r["id"] for r in session.manage_state()["decisions"][1]["rules"]]


def test_reviewing_is_an_edit_that_can_be_taken_back_and_made_again(session):
    draft_card(session)
    session.manage_propose()
    ws = session._ws()
    ws.apply("review_rule_card", {"id": "probe-window", "verdict": "approve"})
    assert ws.edits[-1].op == "review_rule_card" and ws.edits[-1].target == "rule_card:probe-window"
    ws.undo()
    assert not ws.dirty
    ws.redo()
    assert next(c for c in ws.composed().cards if c["id"] == "probe-window")["status"] == "approved"
    with pytest.raises(EditError, match="AXIOM"):
        ws.apply("review_rule_card", {"id": "law-return-min-days", "verdict": "reject"})
    with pytest.raises(EditError, match="approve or reject"):
        ws.apply("review_rule_card", {"id": "probe-window", "verdict": "maybe"})


def test_a_standard_card_is_reviewed_as_an_extension_and_stays_standard(session):
    """A card of a standard module is not this module's to rewrite: the review is what the pending edits give it."""
    from ontlas.modules import Module, compose

    comp = session.studio.composition
    std = next(m for m in comp.modules if m.name == "commerce")
    body = std.to_dict()
    body["rule_cards"] = [*body.get("rule_cards", []), {"id": "std-draft", "type": "decide", "statement": "표준 초안", "status": "draft"}]
    from ontlas.manage import Workspace

    ws = Workspace([Module.from_dict(body) if m.name == "commerce" else m for m in comp.modules], compose_kw=session.studio._compose_kw)
    ws.apply("review_rule_card", {"id": "std-draft", "verdict": "approve", "result": "정한 결과"})
    card = next(c for c in ws.composed().cards if c["id"] == "std-draft")
    assert card["status"] == "approved" and card["layer"] == "standard" and card["module"] == "commerce" and card["result"] == "정한 결과"
    assert ws.module.extend["rule_cards"]["std-draft"] == {"result": "정한 결과", "status": "approved"}
    ws.apply("review_rule_card", {"id": "std-draft", "verdict": "reject"})
    assert "std-draft" not in [c["id"] for c in ws.composed().cards]
    assert compose([*ws.base, ws.module], **ws.kw).issues == []


def test_the_history_of_a_card_names_the_pending_edit_and_then_the_request_that_filed_it(session):
    assert get(session, "sem/history", kind="card", name="acme-vip-window")["entries"] == []
    draft_card(session)
    out = get(session, "sem/history", kind="card", name="probe-window")
    (e,) = out["entries"]
    assert e["status"] == "draft" and e["kind"] == "added" and not e["deployed"]
    assert {"field": "statement", "label": "규칙 이름", "before": None, "after": "시험 규칙"} in e["fields"]
    change = session.manage_propose()["change"]
    out = get(session, "sem/history", kind="card", name="probe-window")
    (e,) = out["entries"]
    assert e["change"] == change["id"] and e["deployed"] and e["kind"] == "added" and e["all"]["규칙 이름"] == "시험 규칙"
    session.manage_edit("update_rule_card", {"id": "probe-window", "result": "바꾼 결과"})
    session.element_comment("rule_card:probe-window", "결과를 다시 적음")
    first, second = get(session, "sem/history", kind="card", name="probe-window")["entries"]
    assert first["status"] == "draft" and first["kind"] == "changed"
    assert first["fields"] == [{"field": "result", "label": "결과", "before": "결과", "after": "바꾼 결과"}]
    assert [n["text"] for n in first["notes"]] == ["결과를 다시 적음"] and second["change"] == change["id"]


def test_the_history_of_a_named_value_and_of_a_metric(session):
    session.manage_edit("update_parameter", {"name": "return_window_days", "value": 10})
    (e,) = get(session, "sem/history", kind="parameter", name="return_window_days")["entries"]
    assert e["status"] == "draft" and {"field": "value", "label": "값", "before": 7, "after": 10} in e["fields"]
    change = session.manage_propose()["change"]
    out = get(session, "sem/history", kind="parameter", name="return_window_days")
    (e,) = out["entries"]
    assert e["change"] == change["id"] and e["deployed"] and out["now"]["value"] == 10
    assert {"field": "value", "label": "값", "before": None, "after": 10} in e["fields"]  # what the request's module says of it
    session.manage_edit("update_metric", {"name": "returnRate", "label": "반품 비율"})
    (m,) = get(session, "sem/history", kind="metric", name="returnRate")["entries"]
    assert {"field": "label", "label": "이름", "before": "반품률", "after": "반품 비율"} in m["fields"]
    with pytest.raises(ValueError):
        get(session, "sem/history", kind="object", name="OrderItem")


def test_the_history_says_codes_and_references_in_words(session):
    session.manage_edit("update_rule_card", {"id": "unit-price-not-negative", "status": "review"})
    (e,) = get(session, "sem/history", kind="card", name="unit-price-not-negative")["entries"]
    assert {"field": "status", "label": "상태", "before": "승인", "after": "검토 중"} in e["fields"]
    assert e["all"]["적용 대상"] == "주문상품 · 결제 단가" and e["all"]["유형"] == "계산" and e["all"]["검사"] == "주문상품 · 결제 단가 0 이상"
    session.manage_edit("update_metric", {"name": "returnRate", "formula": {"match": {"i": "OrderItem"}, "where": {"eq": ["i.item_status", "RETURN_REQUESTED"]},
                                                                           "value": {"count": "i"}}})
    (m,) = get(session, "sem/history", kind="metric", name="returnRate")["entries"]
    (f,) = [f for f in m["fields"] if f["field"] == "formula"]
    assert f["before"] == "주문상품 건수 · 조건 주문상품 · 주문상품 상태 같음 RETURNED" and f["after"].endswith("같음 RETURN_REQUESTED")
    assert m["all"]["기준 시각"] == "배송 완료 시각 · 주문상품 · 배송 완료 일시" and not any("{" in str(v) for v in m["all"].values())
    session.manage_edit("add_parameter", {"name": "probe_flag", "type": "boolean", "value": "true"})
    (b,) = get(session, "sem/history", kind="parameter", name="probe_flag")["entries"]
    assert b["all"]["값"] == "예" and b["all"]["자료형"] == "참 · 거짓"


def test_an_axiom_card_is_changed_as_its_module_s_request_whatever_the_module_s_size(session, monkeypatch):
    """The module is the library's own, not a pasted file: the AXIOM module of a whole law runs past a pasted file's size."""
    import yaml

    from ontlas.web import api as web_api

    monkeypatch.setattr(web_api, "MODULE_TEXT_MAX", 64)
    out = post(session, "sem/axiom/card", id="law-return-min-days", fields={"result": "고친 결과"})
    cr = session.studio.changes.requests[out["change"]["id"]]
    assert out["ok"] and cr.status == "pending" and not session._ws().dirty
    assert next(c for c in yaml.safe_load(cr.text)["rule_cards"] if c["id"] == "law-return-min-days")["result"] == "고친 결과"
    with pytest.raises(ValueError, match="AXIOM 규칙이 아니어서"):
        post(session, "sem/axiom/card", id="acme-vip-window", fields={"result": "고친 결과"})


def test_an_axiom_card_taken_out_is_a_removal_in_its_history(session):
    out = post(session, "sem/axiom/card", id="law-refund-cap", remove=True)
    (e,) = get(session, "sem/history", kind="card", name="law-refund-cap")["entries"]
    assert e["change"] == out["change"]["id"] and e["kind"] == "removed" and e["all"] == {}
    assert e["fields"] and all(f["after"] is None for f in e["fields"])


def test_a_viewer_reads_the_drafts_and_an_editor_does_not_decide():
    from ontlas.web.team import User

    routes.load()
    viewer = User("v", "보는 사람", "", ["viewer"])
    editor = User("e", "고치는 사람", "", ["editor"])
    approver = User("a", "승인하는 사람", "", ["approver"])
    assert viewer.may("viewer") and not editor.may(NEEDS["sem/draft/decide"]) and approver.may(NEEDS["sem/draft/decide"])
    s = StudioSession(load_studio(SHOP))
    assert routes.find("GET", "sem/drafts")(s, {}, SimpleNamespace(name="보는 사람"))["counts"]["waiting"] == 1
