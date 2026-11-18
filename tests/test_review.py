import copy

import pytest

from ontlas.modules import Module
from ontlas.review import ChangeError, FlowSettings

from .conftest import LIB

STUDIO = LIB / "studio.yaml"


@pytest.fixture
def st():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.library import OverlayLibrary

    s = load_studio(STUDIO)
    s.library = OverlayLibrary(s.library, [])  # approvals are kept in memory, the example folder is never written
    return s


def _overlay(st, version: str, days: str) -> Module:
    m = st.library.get("acme-overlay")
    d = copy.deepcopy(m.to_dict())
    d["version"] = version
    d["extend"]["decisions"]["returnEligibility"]["rules_prepend"][0]["when"]["days_since_delivery"] = days
    return Module.from_dict(d)


def test_agreement_with_past_decisions_names_each_case_that_differs(st):
    a = st.agreement()
    assert (a["cases"], a["agree"], a["rate"]) == (10, 9, 0.9)
    miss = a["mismatches"][0]
    assert miss["case"]["case_id"] == "RC08" and miss["expected"] == {"eligible": True}
    assert miss["got"] == {"eligible": False} and miss["matched"] == ["expired"]
    assert a["confusion"]["eligible"]["True → False"] == 1


def test_the_flow_passes_its_conditions_and_reports_each(st):
    g = st.gates()
    assert g["passed"] and {(x["stage"], x["condition"]) for x in g["gates"]} == {
        ("bind", "max_errors"), ("query", "min_agree"), ("decide", "min_agreement"), ("check", "min_accuracy"),
        ("define", "max_gaps"), ("define", "max_unreachable"), ("define", "max_axiom_conflicts"), ("check", "max_new_wrong")}
    with pytest.raises(ValueError, match="cannot be switched off"):
        FlowSettings.from_dict({"off": ["source"]})
    with pytest.raises(ValueError, match="share between 0 and 1"):
        FlowSettings.from_dict({"gates": {"check": {"min_accuracy": 90}}})
    st.settings["flow"] = {**st.settings["flow"], "off": ["decide", "check"]}
    assert {x["stage"] for x in st.gates()["gates"]} == {"define", "bind", "query"}  # the definition's own checks stay


def test_a_change_is_reviewed_on_a_copy_and_approved_by_someone_else(st):
    before = st.decide("returnEligibility", "I1001").matched
    cr = st.changes.propose(_overlay(st, "1.1.0", "<= 10"), by="kim")
    rv = cr.review
    assert rv["mode"] == "replace" and rv["base_version"] == "1.0.0" and rv["passed"]
    assert rv["diff"]["changed"] == ["rule:returnEligibility.vip-window"]
    # 10 days no longer covers RC04 (VIP, 12 days, approved then): the review shows the agreement it would have
    assert rv["measured"]["decide"]["rate"] == 0.8
    assert {m["case"]["case_id"] for m in rv["measured"]["decide"]["mismatches"]} == {"RC04", "RC08"}
    assert st.decide("returnEligibility", "I1001").matched == before  # the live studio is untouched by the review
    with pytest.raises(PermissionError):
        st.changes.approve(cr.id, by="kim")
    st.changes.approve(cr.id, by="lee")
    assert cr.status == "approved" and st.library.get("acme-overlay").version == "1.1.0"
    assert st.library.versions("acme-overlay") == ["1.0.0", "1.1.0"]
    assert next(m for m in st.composition.modules if m.name == "acme-overlay").version == "1.1.0"
    assert [e["event"] for e in st.changes.audit] == ["proposed", "approved"]
    with pytest.raises(ChangeError, match="already in the library"):
        st.changes.propose(_overlay(st, "1.1.0", "<= 10"), by="kim")


def test_a_change_that_breaks_the_flow_cannot_be_approved(st):
    # a VIP window of 30 days approves RC10, which was refused: agreement falls to 0.8 and the stricter gate fails
    st.settings["flow"]["gates"]["decide"]["min_agreement"] = 0.9
    cr = st.changes.propose(_overlay(st, "1.2.0", "<= 30"), by="kim")
    gate = next(g for g in cr.review["gates"] if g["stage"] == "decide")
    assert not cr.review["passed"] and gate["value"] == 0.8 and gate["passed"] is False
    with pytest.raises(ChangeError, match="decide.min_agreement"):
        st.changes.approve(cr.id, by="lee")
    st.changes.reject(cr.id, by="lee", reason="VIP 30일은 운영 정책과 다름")
    assert cr.status == "rejected" and st.library.get("acme-overlay").version == "1.0.0"


def test_a_change_that_does_not_compose_is_shown_as_such(st):
    m = _overlay(st, "1.3.0", "<= 10")
    m.extend["objects"]["Nowhere"] = {"properties": {"x": {"type": "string"}}}
    cr = st.changes.propose(m, by="kim")
    assert not cr.review["passed"] and "Nowhere" in cr.review["issues"][0]



def _turned(st, rule: str, then: dict, when: dict | None = None):
    """The example's acme overlay with one more Custom rule written ahead of the others in the return table."""
    m = st.library.get("acme-overlay")
    d = copy.deepcopy(m.to_dict())
    d["version"] = "1.1.0"
    d["extend"]["decisions"]["returnEligibility"]["rules_prepend"].insert(0, {"id": rule, "when": when or {}, "then": then})
    return Module.from_dict(d)


@pytest.fixture
def shop():
    """The example library as people get it: its return table opens with an AXIOM rule."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.library import OverlayLibrary

    from .conftest import EXAMPLE

    s = load_studio(EXAMPLE.parent / "library" / "studio.yaml")
    s.library = OverlayLibrary(s.library, [])
    return s


def test_a_change_may_not_leave_a_gap_a_rule_against_an_axiom_or_a_new_wrong_answer(shop):
    st = shop
    """On unless turned off: what the definition checks find (a gap, a rule that can never answer, a Custom rule giving
    the other verdict where an AXIOM rule holds) and a question the change makes fail stop it."""
    assert FlowSettings.from_dict({"gates": {"check": {"min_accuracy": 0.5}}}).gates["check"]["max_new_wrong"] == 0
    assert FlowSettings.from_dict({"gates": {"define": {"max_gaps": None}}}).gates["define"] == {
        "max_gaps": None, "max_unreachable": 0, "max_axiom_conflicts": 0}  # one turned off stays off
    against = _turned(st, "early", {"eligible": True, "reason": "배송 전에도 가능"}, {"days_since_delivery": "null"})
    rv = st.changes.propose(against, by="kim").review
    failed = {(g["stage"], g["condition"]): g["value"] for g in rv["gates"] if not g["passed"]}
    assert not rv["passed"] and failed[("define", "max_axiom_conflicts")] == 1
    assert {"not-delivered", "early"} <= set(rv["measured"]["define"]["findings"][0]["rules"])
    wrong = _turned(st, "nothing-returns", {"eligible": False, "reason": "반품 불가"})
    rv = st.changes.propose(wrong, by="kim").review
    failed = {(g["stage"], g["condition"]): g["value"] for g in rv["gates"] if not g["passed"]}
    assert failed[("check", "max_new_wrong")] >= 1 and failed[("define", "max_unreachable")] >= 1
    assert rv["regression"]["newly_failing"]
    st.settings["flow"] = {**st.settings["flow"], "gates": {**st.settings["flow"].get("gates", {}),
                                                            "define": {"max_axiom_conflicts": None}}}
    rv = st.changes.propose(_turned(st, "early2", {"eligible": True, "reason": "x"}, {"days_since_delivery": "null"}), by="kim").review
    assert ("define", "max_axiom_conflicts") not in {(g["stage"], g["condition"]) for g in rv["gates"]}
