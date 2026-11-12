"""Deciding with no source, and validating in two stages.

A workflow or an agent that only goes through the API decides on the values it has: by a decision's input name, by the
target property the input reads (a date for an elapsed-days input) or by its parameter. An input given as null is a value
(no delivery date yet); one not given at all is asked for, never read as null. A validation question that states its
values is measured with no source (stage 1); with a record key as well it is measured on the record once a source is
connected (stage 2), and where only the record is wrong the mapping is what to look at."""
from datetime import datetime
from pathlib import Path

import pytest

from ontlas.config import load_studio
from ontlas.decide.table import MissingValues
from ontlas.model import Question
from ontlas.rest import Rest, openapi
from ontlas.tools import StudioTools
from ontlas.validate import validate_ontology

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
VIP_IN_WINDOW = {"days_since_delivery": 4, "item_status": "NORMAL", "category_returnable": True, "customer_grade": "VIP"}


@pytest.fixture(scope="module")
def studio():
    return load_studio(SHOP)


def _rest(studio, **kw):
    return Rest([("t", StudioTools(studio, actor_id="flow", audit=True))], **kw)


def _call(rest, path, body, method="POST"):
    return rest.answer(method, path, body, rest.caller("Bearer t"))


# ---- values instead of a record --------------------------------------------------------------------------------------

def test_a_decision_on_given_values_matches_the_one_on_the_record(studio):
    on_record = studio.decide("returnEligibility", "I1001")
    on_values = studio.decide("returnEligibility", values=dict(on_record.inputs))
    assert on_values.outputs == on_record.outputs and on_values.matched == on_record.matched
    assert all(e.source == "given" for e in on_values.evidence)


def test_a_property_value_stands_for_the_input_that_reads_it(studio):
    at = datetime(2026, 10, 30)
    res = studio.decide("returnEligibility", values={"delivered_at": "2026-10-20", "item_status": "NORMAL",
                                                     "category_returnable": True, "customer_grade": "BASIC"}, at=at)
    assert res.inputs["days_since_delivery"] == 10 and res.outputs["eligible"] is False
    by = {e.input: e for e in res.evidence}
    assert by["days_since_delivery"].property == "delivered_at" and by["days_since_delivery"].object_type == "OrderItem"


def test_an_input_not_given_is_asked_for_and_null_is_a_value(studio):
    with pytest.raises(MissingValues) as e:
        studio.decide("returnEligibility", values={"days_since_delivery": 3})
    assert [m["input"] for m in e.value.missing] == ["item_status", "category_returnable", "customer_grade"]
    assert e.value.missing[0]["label"] and e.value.missing[0]["property"] == "item_status"
    res = studio.decide("returnEligibility", values={**VIP_IN_WINDOW, "days_since_delivery": None})
    assert res.matched[0] == "not-delivered"  # null given: no delivery date, which the rule decides on


def test_a_value_of_the_wrong_type_is_refused(studio):
    from ontlas.decide.table import DecisionError

    with pytest.raises(DecisionError, match="days_since_delivery"):
        studio.decide("returnEligibility", values={**VIP_IN_WINDOW, "days_since_delivery": "four"})


# ---- the API --------------------------------------------------------------------------------------------------------

def test_the_api_decides_on_values_and_says_what_decided(studio):
    code, out = _call(_rest(studio), "/v1/decide", {"decision": "returnEligibility", "values": VIP_IN_WINDOW})
    assert code == 200 and out["mode"] == "values" and out["outputs"]["eligible"] is True and out["verdict"]
    assert out["decided_by"]["rule"] == "vip-window" and out["decided_by"]["layer"] == "custom" and out["decided_by"]["version"]
    assert [x["layer"] for x in out["path"]["layers"]] == ["axiom", "custom", "standard"]
    assert len(out["decision_id"]) == 32 and {m["kind"] for m in out["modules"]} >= {"domain", "axiom"}
    assert studio.actions.audit[-1].detail["id"] == out["decision_id"]  # the audit trail finds it by that id


def test_the_api_lists_what_is_missing_and_refuses_a_call_with_neither(studio):
    rest = _rest(studio)
    code, out = _call(rest, "/v1/decide", {"decision": "returnEligibility", "values": {"days_since_delivery": 3}})
    assert code == 422 and out["needs_values"] and [m["input"] for m in out["missing"]][0] == "item_status"
    code, out = _call(rest, "/v1/decide", {"decision": "returnEligibility"})
    assert code == 400 and "key" in out["error"] and "values" in out["error"]
    code, out = _call(rest, "/v1/decide", {"decision": "returnEligibility", "key": "I1001"})
    assert code == 200 and out["mode"] == "record"


def test_rules_terms_and_questions_are_read_over_the_api(studio):
    rest = _rest(studio)
    code, out = _call(rest, "/v1/rules", {"layer": "axiom"})
    assert code == 200 and out["rules"] and all(r["layer"] == "axiom" for r in out["rules"])
    code, out = _call(rest, "/v1/rules", {"decision": "returnEligibility"})
    assert any(r["id"] == "law-return-min-days" for r in out["rules"])
    assert all(any(x["ref"].startswith("decision:returnEligibility") for x in r["runs"]) for r in out["rules"])
    code, out = _call(rest, "/v1/terms", {"text": "구매자의 주문금액"})
    assert code == 200 and out["text"].startswith("고객") and out["confusables"][0]["confusable"] == "결제금액"
    code, out = _call(rest, "/v1/questions", {"stage": "values"})
    assert code == 200 and out["stages"]["values"]["measured"] == out["stages"]["values"]["passed"] > 0
    assert out["results"] and all("values" in r["stages"] for r in out["results"])


def test_a_caller_names_the_library_it_asks(studio, tmp_path):
    other = load_studio(SHOP)
    other.onto.decisions["returnEligibility"].label = "다른 라이브러리"
    libs = [{"id": "l1", "label": "first", "modules": 1, "load": lambda: studio},
            {"id": "l2", "label": "second", "modules": 1, "load": lambda: other}]
    rest = _rest(studio, libraries=libs)
    code, out = _call(rest, "/v1/libraries", {}, "GET")
    assert code == 200 and [x["id"] for x in out["libraries"]] == ["l1", "l2"] and out["libraries"][0]["default"]
    code, out = _call(rest, "/v1/rules", {"library": "second", "decision": "returnEligibility"})
    assert code == 200 and out["rules"]
    tools = rest.tools_for(rest.caller("Bearer t"), "l2")
    assert tools.studio is other and tools.actor.id == "flow" and rest.tools_for(rest.caller("Bearer t"), "l2") is tools
    assert _call(rest, "/v1/decide", {"library": "nope", "decision": "x"})[0] == 404


def test_the_openapi_document_describes_values_and_the_library():
    spec = openapi("0", "https://x")
    body = spec["paths"]["/v1/decide"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert body["required"] == ["decision"] and {"key", "values", "library"} <= set(body["properties"])
    assert "422" in spec["paths"]["/v1/decide"]["post"]["responses"]
    assert {"/v1/rules", "/v1/terms", "/v1/questions", "/v1/libraries"} <= set(spec["paths"])
    assert spec["paths"]["/v1/space"]["get"]["parameters"][0]["name"] == "library"


# ---- two stages -----------------------------------------------------------------------------------------------------

def _ask(studio, q: Question):
    studio.onto.questions.append(q)
    try:
        return next(r for r in studio.questions().results if r.id == q.id)
    finally:
        studio.onto.questions.remove(q)


def test_right_on_its_values_and_wrong_on_its_record_points_at_the_mapping():
    st = load_studio(SHOP)  # I1003: 12 days, BASIC on the record; the question states 4 days, VIP
    r = _ask(st, Question("X-M1", "I1003", {"eligible": True}, decision="returnEligibility", key="I1003", values=VIP_IN_WINDOW))
    assert r.stages["values"]["passed"] is True and r.stages["record"]["passed"] is False and r.passed is False
    assert r.diagnosis == "mapping"
    assert {d["input"]: (d["given"], d["read"]) for d in r.differs} == {"days_since_delivery": (4, 12),
                                                                          "customer_grade": ("VIP", "BASIC")}
    assert all(d["label"] for d in r.differs)


def test_wrong_on_its_values_points_at_the_rule_and_an_unread_record_at_the_data():
    st = load_studio(SHOP)
    r = _ask(st, Question("X-R1", "규칙", {"eligible": False}, decision="returnEligibility", key="I1001", values=VIP_IN_WINDOW))
    assert r.diagnosis == "rule" and r.stages["values"]["passed"] is False
    d = _ask(st, Question("X-D1", "데이터", {"eligible": True}, decision="returnEligibility", key="NOPE", values=VIP_IN_WINDOW))
    assert d.diagnosis == "data" and d.stages["record"]["error"] and not d.differs
    rep = st.questions().stages()
    assert set(rep["diagnosis"]) == {"rule", "mapping", "data"}


def test_a_question_with_too_few_values_is_the_question_to_fix():
    st = load_studio(SHOP)
    r = _ask(st, Question("X-F1", "값 부족", {"eligible": True}, decision="returnEligibility", values={"days_since_delivery": 3}))
    assert r.passed is False and r.stages["values"]["missing"] and "MissingValues" in r.error
    assert "record" not in r.stages and r.diagnosis == "rule"


def test_a_decision_question_needs_a_key_or_values_and_only_names_it_reads():
    st = load_studio(SHOP)
    st.onto.questions.append(Question("X-V1", "?", {"eligible": True}, decision="returnEligibility"))
    st.onto.questions.append(Question("X-V2", "?", {"eligible": True}, decision="returnEligibility", values={"colour": "red"}))
    issues = validate_ontology(st.onto)
    assert any("X-V1" in i and "key" in i for i in issues) and any("X-V2" in i and "colour" in i for i in issues)


# ---- the page --------------------------------------------------------------------------------------------------------

def test_the_page_tries_the_api_the_way_a_platform_calls_it():
    from ontlas.web.api import StudioSession

    s = StudioSession(load_studio(SHOP))
    i = s.integrations()
    d = next(x for x in i["decisions"] if x["name"] == "returnEligibility")
    days = next(x for x in d["inputs"] if x["name"] == "days_since_delivery")
    assert days["days_since"] and days["property"] == "delivered_at" and d["example"]["values"]
    out = s.rest_try("/v1/decide", {"decision": "returnEligibility", "values": d["example"]["values"], "library": "l9"})
    assert out["status"] == 200 and out["body"]["mode"] == "values"
    assert s.rest_try("/v1/decide", {"decision": "returnEligibility", "values": {}})["status"] == 422
    with pytest.raises(ValueError):
        s.rest_try("/v1/actions", {"action": "requestReturn", "key": "I1001"})  # the page tries reads and decisions only


def test_a_question_is_added_on_values_alone_and_refused_with_neither():
    from ontlas.web.api import StudioSession

    s = StudioSession(load_studio(SHOP))
    s.manage_edit("add_question", {"id": "X-N1", "text": "값만", "decision": "returnEligibility", "values": VIP_IN_WINDOW,
                                   "expect": {"eligible": True}})
    q = next(x for x in s.manage_state()["questions"] if x["id"] == "X-N1")
    assert q["values"] == VIP_IN_WINDOW and not q["key"]
    with pytest.raises(Exception, match="key"):
        s.manage_edit("add_question", {"id": "X-N2", "text": "?", "decision": "returnEligibility", "expect": {"eligible": True}})
