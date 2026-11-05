import pytest

from xgen_space.library import Library
from xgen_space.modules import Module, ModuleError, compose

from .conftest import EXAMPLE
from .test_web import _build

LIB = EXAMPLE.parent / "library"
NS = "https://example.org/studio#"


def test_a_quality_module_raises_the_pass_conditions_and_detaching_it_lowers_them_again():
    pytest.importorskip("rdflib")
    s = _build()
    own = s.studio.flow.gates
    assert s.attach("return-quality")["ok"]
    st = s.studio
    assert st.flow.gates["check"] == {"min_accuracy": 1.0, "min_grounded": 1.0}
    assert st.flow.gates["decide"]["min_agreement"] == 0.9 and st.flow.gates["bind"] == own["bind"]
    assert st.raised_gates() == {"check.min_accuracy": "return-quality", "check.min_grounded": "return-quality",
                                 "decide.min_agreement": "return-quality"}
    form = s.flow_settings()
    assert form["settings"]["gates"]["check"] == own["check"]  # the form edits the studio's own; saving keeps it so
    assert {(r["stage"], r["condition"]) for r in form["raised"]} == {("check", "min_accuracy"),
                                                                       ("check", "min_grounded"),
                                                                       ("decide", "min_agreement")}
    flow = s.flow()
    by = {g["condition"]: g["by"] for x in flow["steps"] for g in x["gates"]}
    assert flow["passed"] and by["min_grounded"] == "검증 기준 · 반품" and by["max_errors"] == ""
    assert {"RQ1", "RQ2", "RQ3"} <= {q.id for q in st.onto.questions}
    assert s.detach("return-quality")["ok"]
    assert s.studio.flow.gates == own and not s.studio.raised_gates()


def test_a_module_cannot_lower_a_bar_another_module_set():
    mods = Library(LIB).resolve(["commerce"])
    strict = Module.from_dict({"module": "strict", "kind": "quality", "requires": ["commerce"],
                               "flow": {"gates": {"check": {"min_accuracy": 1.0}}}})
    loose = Module.from_dict({"module": "loose", "kind": "quality", "requires": ["commerce"],
                              "flow": {"gates": {"check": {"min_accuracy": 0.5}, "bind": {"max_errors": 3}}}})
    comp = compose([*mods, strict, loose], namespace=NS)
    assert comp.gates == {"check": {"min_accuracy": 1.0}, "bind": {"max_errors": 3}}
    assert comp.gate_by == {"check.min_accuracy": "strict", "bind.max_errors": "loose"}


def test_a_module_flow_and_draft_rules_are_checked_when_they_compose():
    mods = Library(LIB).resolve(["commerce"])
    for bad, words in (({"flow": {"gates": {"check": {"min_speed": 1}}}}, "unknown condition"),
                       ({"flow": {"gates": {"check": {"min_accuracy": 2}}}}, "between 0 and 1"),
                       ({"flow": {"off": ["bind"]}}, "only gates"),
                       ({"draft_rules": {"enum_maxx": 3}}, "unknown draft rules")):
        m = Module.from_dict({"module": "bad", "kind": "quality", "requires": ["commerce"], **bad})
        with pytest.raises(ModuleError, match=words):
            compose([*mods, m], namespace=NS)


def test_a_method_module_gives_the_draft_its_rules():
    pytest.importorskip("rdflib")
    s = _build()
    assert s.files_state()["defaults"]["enum_max"] == 20
    assert s.attach("build-rules")["ok"]
    fs = s.files_state()
    assert fs["defaults"]["enum_max"] == 12 and fs["rules"]["enum_repeat"] == 3.0 and fs["rules_by"] == ["구축 규칙 · 예시"]
    s.upload("차주.csv", "차주 번호,이름,처리\nB1,한별,접수\nB2,누리,접수\nB3,가람,완료\nB4,다솜,완료\n".encode("utf-8"))
    s.make_draft("차주 파일")
    assert s.pending[3].enum_max == 12 and "처리" in s.pending[3].state_hints
    assert s.make_draft("차주 파일", rules={"enum_max": 30}) and s.pending[3].enum_max == 30  # what the visitor sets
    assert s.detach("build-rules")["ok"] and s.files_state()["defaults"]["enum_max"] == 20
    assert Module.from_dict(Library(LIB).get("build-rules").to_dict()).draft_rules["enum_max"] == 12  # round trip


def test_an_answer_is_grounded_by_its_rule_cite_its_source_columns_and_its_version():
    pytest.importorskip("rdflib")
    s = _build()
    rep = s.studio.questions()
    assert rep.grounded == 1.0 and all(r.grounded for r in rep.results)
    d = s.studio.onto.decisions["returnEligibility"]
    d.cite = ""
    next(r for r in d.rules if r.id == "expired").cite = ""
    gaps = {r.id: r.gaps for r in s.studio.questions().results if not r.grounded}
    assert gaps == {"Q3": ["rule expired has no cite"]}  # the other verdicts cite their own clause
    page = s.questions()
    assert page["grounded"] < 1 and next(r for r in page["results"] if r["id"] == "Q3")["gaps"] == ["규칙 expired 출처 없음"]


def test_a_change_to_a_quality_module_is_reviewed_against_the_bar_it_sets():
    pytest.importorskip("rdflib")
    s = _build()
    assert s.attach("return-quality")["ok"]
    text = s.studio.library.get("return-quality").to_dict()
    text["version"] = "1.0.1"
    text["questions"].append({"id": "RQ4", "text": "틀린 정답", "decision": "returnEligibility", "key": "I1002",
                              "expect": {"eligible": True}})
    import yaml

    r = s.propose_module(yaml.safe_dump(text, allow_unicode=True))
    gates = {(g["stage"], g["condition"]): g["passed"] for g in r["change"]["gates"]}
    assert gates[("check", "min_accuracy")] is False and not r["change"]["passed"]
