"""A copy of the space is measured on the same documents, a studio from one ontology file still tries its tables, the
list of what waits for a person never measures, and a wrong answer is not put down to a column it merely mentions."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(load_studio(ROOT / "examples" / "library" / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))


def test_taking_a_module_off_is_measured_on_the_same_documents(session):
    sp = session.studio.space
    sp.checks = [*sp.checks, *({"text": f"없는 문서 질문 {i}", "document": "없는문서"} for i in range(4))]
    session.attach("food")
    preview = session.module_preview("food")
    session.detach("food")
    after = session.issues()
    assert preview["gates"]["met"] == after["gates"]["met"] < preview["gates"]["all"]
    assert "min_found" in preview["gates"]["failed"]


def test_a_trial_compares_the_document_search_with_itself(session):
    sp = session.studio.space
    sp.checks = [*sp.checks, *({"text": f"없는 문서 질문 {i}", "document": "없는문서"} for i in range(4))]
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    got = session.manage_trial()
    index = next(g for g in got["gates"] if g["stage"] == "index")
    assert index["value"] == got["before"]["index.min_found"] and not index["passed"] and not got["passed"]


def test_a_studio_from_one_ontology_file_still_tries_its_tables():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import StudioSession

    s = StudioSession(load_studio(ROOT / "examples" / "commerce" / "studio.yaml"))
    assert s.studio.composition is None
    assert "findings" in s.rules_state()
    name = next(iter(s.studio.onto.decisions))
    assert s.simulate(name)["name"] == name


def test_the_list_of_what_waits_never_measures(session, monkeypatch):
    import ontlas.review as rv

    calls = []
    real = rv.measure
    monkeypatch.setattr(rv, "measure", lambda *a, **k: calls.append(1) or real(*a, **k))
    session.inbox()
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    session.inbox()
    assert not calls


def test_a_wrong_answer_is_not_put_down_to_a_column_its_result_names(session):
    from ontlas.web import issues

    session.attach("food")
    w, _ = session._watched()
    m = dict(w["measured"])
    q = next(q for q in session.studio.onto.questions if q.decision)
    flow = {**w["flow"], "steps": [{**st, "gates": ([{"stage": "check", "condition": "min_accuracy", "label": "x", "limit": 0.9,
                                                       "value": 0.8, "passed": False}] if st["id"] == "check"
                                                     else [g for g in st["gates"] if g["stage"] != "check"])} for st in w["flow"]["steps"]]}
    m["check"] = {"accuracy": 0.8, "grounded": 1.0, "ungrounded": {},
                  "wrong": [{"id": q.id, "text": q.text, "expected": {"eligible": True}, "got": {"eligible": False, "storage": "냉장"}, "error": ""}]}
    got = issues.build(session, {"flow": flow, "measured": m})
    root = next(x for x in got if x["kind"] == "bind.missing")
    assert "gate:check.min_accuracy" not in [y["id"] for y in root["members"]]
    assert any(x["id"] == "gate:check.min_accuracy" for x in got)
