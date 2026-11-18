"""운영 › 연동 · API, 저장소 · 엔진: who may call /v1, a call tried as a policy would make it, and embedding again."""
import json

import pytest

from .conftest import LIB

CFG = LIB / "studio.yaml"
VALUES = {"days_since_delivery": 3, "item_status": "NORMAL", "category_returnable": True, "customer_grade": "VIP"}


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    return StudioSession(load_studio(CFG))


@pytest.fixture
def ops(monkeypatch):
    from ontlas.web.areas import ops as area

    monkeypatch.setitem(area._REST, "rest", None)
    return area


def _rest(studio):
    from ontlas.rest import Rest
    from ontlas.tools import StudioTools

    return Rest([("token-of-the-workflow", StudioTools(studio, actor_id="workflow", read_only=True, audit=True)),
                 ("token-of-the-agent", StudioTools(studio, role="customer_agent", principal={"customer_id": "C001"},
                                                    actor_id="cs-agent", audit=True))])


def test_with_no_api_the_screen_is_told_so(session, ops):
    out = ops.targets(session, {}, None)
    assert out["rest"] is False and out["listed"] is False and out["targets"] == []


def test_the_callers_are_named_with_their_policy_and_never_their_token(session, ops):
    rest = _rest(session.studio)
    ops.register_rest(rest)
    out = ops.targets(session, {}, None)
    assert out["listed"] is True
    assert [(t["name"], t["policy"], t["write"], t["principal"]) for t in out["targets"]] == [
        ("workflow", "", False, []), ("cs-agent", "customer_agent", True, ["customer_id"])]
    assert all(t["policy_known"] and t["calls"] == 0 and t["last"] == "" for t in out["targets"])
    said = json.dumps(out, ensure_ascii=False)
    assert "token-of" not in said and "C001" not in said  # a token and a caller's own rows are not for the page


def test_what_a_caller_asked_is_counted_from_the_audit_trail(session, ops):
    rest = _rest(session.studio)
    ops.register_rest(rest)
    code, _ = rest.answer("POST", "/v1/decide", {"decision": "returnEligibility", "values": VALUES}, rest.clients[0][1])
    assert code == 200
    code, _ = rest.answer("POST", "/v1/decide", {"decision": "returnEligibility", "values": {}}, rest.clients[0][1])
    assert code == 422  # nothing was decided, so nothing is recorded
    out = ops.targets(session, {}, None)
    first, second = out["targets"]
    assert (first["calls"], first["month"], first["events"]) == (1, 1, {"판정": 1}) and first["last"]
    assert second["calls"] == 0 and out["calls_month"] == 1 and out["month"] == first["last"][:7]
    assert out["days"] == int(first["last"][8:10])  # the days of the month so far, for the average a day


def test_the_callers_that_requested_an_action_are_said_by_the_action(session, ops):
    """What taking an Action out leaves: the callers whose requests for it the audit trail holds, each with how many."""
    rest = _rest(session.studio)
    ops.register_rest(rest)
    for key, want in (("I1001", 200), ("I1005", 200), ("I1003", 403)):  # the last is another customer's: never asked
        code, _ = rest.answer("POST", "/v1/actions", {"action": "requestReturn", "key": key, "params": {"reason": "변심"}},
                              rest.clients[1][1])
        assert code == want
    code, _ = rest.answer("POST", "/v1/decide", {"decision": "returnEligibility", "values": VALUES}, rest.clients[0][1])
    out = ops.targets(session, {}, None)
    assert out["actions"] == {"requestReturn": [{"name": "cs-agent", "requests": 2}]}  # a decision is no request
    ops.register_rest(None)
    assert ops.targets(session, {}, None)["actions"] == {}


def test_a_caller_whose_policy_this_ontology_does_not_define_is_marked(session, ops):
    from ontlas.rest import Rest
    from ontlas.tools import StudioTools

    tools = StudioTools(session.studio, actor_id="old-agent", read_only=True, audit=True)
    tools.role = "retired_policy"  # a policy of another library, or one since removed
    ops.register_rest(Rest([("t", tools)]))
    assert ops.targets(session, {}, None)["targets"][0]["policy_known"] is False


def test_a_call_is_tried_as_the_policy_picked_would_make_it(session, ops):
    body = {"decision": "returnEligibility", "values": VALUES, "library": "ignored-on-the-page"}
    free = ops.try_call(session, {"path": "/v1/decide", "body": body}, None)
    assert free["status"] == 200 and free["body"]["outputs"]["eligible"] is True and free["policy"] == ""
    may = ops.try_call(session, {"path": "/v1/decide", "policy": "customer_agent", "body": body}, None)
    assert may["status"] == 200 and may["policy"] == "customer_agent"
    may_not = ops.try_call(session, {"path": "/v1/decide", "policy": "support_agent", "body": body}, None)
    assert may_not["status"] == 403  # that policy does not run this decision: the page shows what the platform would get


def test_a_try_stays_within_reading_and_deciding(session, ops):
    with pytest.raises(ValueError):
        ops.try_call(session, {"path": "/v1/actions", "body": {}}, None)
    with pytest.raises(ValueError, match="접근 정책 nobody"):
        ops.try_call(session, {"path": "/v1/decide", "policy": "nobody", "body": {}}, None)


def test_a_policy_with_row_rules_is_tried_with_the_caller_attributes_it_compares_with(session, ops):
    body = {"decision": "returnEligibility", "key": "I1001"}  # an item of order O1, which customer C001 placed
    asked = ops.try_call(session, {"path": "/v1/decide", "policy": "customer_agent", "body": body}, None)
    assert asked["status"] == 403 and "customer_id" in asked["body"]["error"]
    mine = ops.try_call(session, {"path": "/v1/decide", "policy": "customer_agent", "principal": {"customer_id": "C001"},
                                  "body": body}, None)
    other = ops.try_call(session, {"path": "/v1/decide", "policy": "customer_agent", "principal": {"customer_id": "C002"},
                                   "body": body}, None)
    assert mine["status"] == 200 and other["status"] == 403


def test_a_policy_the_change_request_adds_or_changes_is_tried_as_written(session, ops):
    body = {"decision": "returnEligibility", "values": VALUES}
    session.manage_edit("add_role", {"name": "fresh_policy", "label": "새 정책", "read": ["*"], "run": ["returnEligibility"]})
    fresh = ops.try_call(session, {"path": "/v1/decide", "policy": "fresh_policy", "body": body}, None)
    assert fresh["status"] == 200 and fresh["draft"] is True
    assert "fresh_policy" not in session.studio.onto.roles  # tried on a copy: nothing was deployed
    before = ops.try_call(session, {"path": "/v1/decide", "policy": "support_agent", "body": body}, None)
    assert before["status"] == 403 and before["draft"] is False
    run = list(session.studio.onto.roles["support_agent"].run)
    session.manage_edit("update_role", {"name": "support_agent", "run": [*run, "returnEligibility"]})
    after = ops.try_call(session, {"path": "/v1/decide", "policy": "support_agent", "body": body}, None)
    assert after["status"] == 200 and after["draft"] is True
    same = ops.try_call(session, {"path": "/v1/decide", "policy": "customer_agent", "body": body}, None)
    assert same["draft"] is False  # a policy the change request leaves as it is goes on the deployed definition
    session.manage_edit("delete_role", {"name": "fresh_policy"})
    with pytest.raises(ValueError, match="접근 정책 fresh_policy"):
        ops.try_call(session, {"path": "/v1/decide", "policy": "fresh_policy", "body": body}, None)


def test_every_passage_is_embedded_again(session, ops):
    from ontlas.space import signature

    sp = session.space
    sp.add({"name": "반품 안내", "kind": "md", "text": "", "sections": [
        {"title": "반품 기간", "text": "배송 완료 후 7일 이내의 주문상품은 반품할 수 있습니다."},
        {"title": "반품 비용", "text": "단순 변심이면 왕복 배송비를 고객이 부담합니다."}]}, fixed=True)
    before = session.space_state()
    assert before["chunks"] == 2
    calls = []
    embed = sp.embedder.embed
    sp.embedder.embed = lambda texts: calls.append(len(texts)) or embed(texts)
    out = ops.reindex(session, {}, None)
    assert out["ok"] and out["chunks"] == before["chunks"] and out["errors"] == {}
    assert sum(calls) >= before["chunks"]  # each passage went through the model once more
    assert sp.model == signature(sp.embedder)
    assert [s["count"] for s in out["space"]["stores"]] == [s["count"] for s in before["stores"]]


def test_the_routes_ask_for_the_level_they_need(ops):
    from ontlas.web import routes
    from ontlas.web.team import NEEDS

    assert routes.find("GET", "ops/targets") is ops.targets
    assert routes.find("POST", "ops/try") is ops.try_call and NEEDS["ops/try"] == "viewer"
    assert routes.find("POST", "ops/reindex") is ops.reindex and NEEDS["ops/reindex"] == "editor"


def test_a_store_added_or_taken_out_is_in_the_audit_log(session):
    """As the admin screens keep what they set: a vector store added and one taken out, by whom, never its address."""
    from ontlas.web import routes
    from ontlas.web.api import DataOptions

    routes.load()
    session.data = DataOptions(allow_connect=True)
    session.who = "관리자 갑"
    session.space_store("add", "side", "memory", "")
    session.space_store("remove", "side")
    rows = [r for r in routes.GET["admin/audit"](session, {}, None)["rows"] if r["kind"] == "setting" and "side" in r["text"]]
    assert [r["text"] for r in rows] == ["벡터 저장소 side 삭제", "벡터 저장소 side 추가 · memory"]  # newest first
    assert {r["by"] for r in rows} == {"관리자 갑"}
