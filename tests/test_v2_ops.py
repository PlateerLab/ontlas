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
    with pytest.raises(LookupError):
        ops.try_call(session, {"path": "/v1/decide", "policy": "nobody", "body": {}}, None)


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
