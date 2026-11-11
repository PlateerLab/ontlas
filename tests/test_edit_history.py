"""Pending edits taken back and made again: a later edit that no longer holds leaves everything as it was, an edit
that cannot be made again stays to be made, only the last edits keep what came before them, a source pick is an
edit like the others, and a question that takes a new answer keeps what it was asked with."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "examples" / "library"
MODULES = ["core", "commerce", "commerce-bindings", "fashion", "acme-overlay"]
KW = {"namespace": "https://example.org/studio#", "name": "studio"}


@pytest.fixture
def base():
    pytest.importorskip("yaml")
    from ontlas.library import Library

    return Library(LIB).resolve(MODULES)


def coupon():
    return {"name": "Coupon", "label": "쿠폰", "key": "coupon_id", "table": "coupons",
            "properties": {"coupon_id": {"type": "string"}}}


def test_a_later_edit_that_no_longer_composes_leaves_the_edits_as_they_were(base):
    from ontlas.manage import EditError, Workspace
    from ontlas.modules import Module

    old = Workspace(base, compose_kw=KW)
    old.apply("add_object", coupon())
    old.apply("update_property", {"object": "Customer", "name": "name", "label": "B"})
    old.apply("update_property", {"object": "Customer", "name": "grade", "label": "C"})
    promo = Module.from_dict({"module": "promo", "version": "1.0.0", "kind": "domain", "requires": ["commerce"],
                              "objects": {"Coupon": {"label": "쿠폰", "key": "code", "properties": {"code": {"type": "string"}}}}})
    ws = Workspace([*base, promo], compose_kw=KW)  # the modules changed under unsent edits, which carry over
    ws.module, ws.edits, ws._before, ws._undone = old.module, old.edits, old._before, old._undone
    with pytest.raises(EditError):
        ws.revert(1)
    assert [e.target for e in ws.edits] == ["object:Coupon", "property:Customer.name", "property:Customer.grade"]
    assert len(ws._before) == 3
    assert set(ws.module.extend["objects"]["Customer"]["properties"]) == {"name", "grade"}


def test_an_edit_that_cannot_be_made_again_stays_to_be_made(base):
    from ontlas.manage import EditError, Workspace
    from ontlas.modules import Module

    old = Workspace(base, compose_kw=KW)
    old.apply("update_property", {"object": "Customer", "name": "name", "label": "B"})
    old.apply("add_object", coupon())
    old.undo()
    promo = Module.from_dict({"module": "promo", "version": "1.0.0", "kind": "domain", "requires": ["commerce"],
                              "objects": {"Coupon": {"label": "쿠폰", "key": "code", "properties": {"code": {"type": "string"}}}}})
    ws = Workspace([*base, promo], compose_kw=KW)  # a module that brings Coupon itself came in meanwhile
    ws.module, ws.edits, ws._before, ws._undone = old.module, old.edits, old._before, old._undone
    with pytest.raises(EditError):
        ws.redo()
    assert [e.target for e in ws._undone] == ["object:Coupon"] and [e.target for e in ws.edits] == ["property:Customer.name"]


def test_only_the_last_edits_can_each_be_taken_back(base):
    from ontlas.manage import UNDO_DEPTH, TooFarBack, Workspace

    ws = Workspace(base, compose_kw=KW)
    for i in range(UNDO_DEPTH + 2):
        ws.apply("update_property", {"object": "Customer", "name": "name", "label": f"이름 {i}"})
    assert ws._before[:2] == [None, None] and all(b is not None for b in ws._before[2:])
    with pytest.raises(TooFarBack):
        ws.revert(0)
    assert ws.undo() is not None and len(ws.edits) == UNDO_DEPTH + 1


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(load_studio(LIB / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))


def test_a_source_pick_is_an_edit_and_stays_when_an_earlier_edit_is_taken_back(session):
    c = next(x for x in session.studio.onto.source_conflicts() if x.open)
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    session.conflict_pick(c.id, c.answers[0].source)
    ws = session._ws()
    assert [e.op for e in ws.edits] == ["update_object", "pick_conflict"]
    session.manage_revert(0)
    ws = session._ws()
    assert [e.target for e in ws.edits] == [f"conflict:{c.id}"] and ws.dirty
    assert c.id in str(ws.module.to_dict())
    with pytest.raises(ValueError):
        session.conflict_pick(c.id, "no such source")


def test_a_question_that_takes_a_new_answer_keeps_its_params(base):
    from ontlas.manage import Workspace
    from ontlas.modules import Module

    mods = []
    for m in base:
        d = m.to_dict()
        for q in d.get("questions") or []:
            if q.get("decision") and q["id"] == "A1":
                q["params"] = {"today": "2025-01-10"}
        mods.append(Module.from_dict(d))
    ws = Workspace(mods, compose_kw=KW)
    ws.apply("update_question", {"id": "A1", "expect": {"eligible": True}})
    q = [x for x in ws.composed().ontology.questions if x.id == "A1"]
    assert len(q) == 1 and q[0].params == {"today": "2025-01-10"} and q[0].expect == {"eligible": True}
