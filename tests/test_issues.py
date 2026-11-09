"""What is wrong said as something to act on: the items behind a failure, why they came to be, what they reach and the
ways to fix each, with failures that read what is broken gathered under it and nothing gathered on a guess."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    return StudioSession(load_studio(ROOT / "examples" / "library" / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))


def built(session, findings=(), **measured):
    """The issues for a measurement written by hand, on the flow as it stands."""
    from xgen_space.web import issues

    w, _ = session._watched()
    return issues.build(session, {"flow": w["flow"], "measured": {"bind": {"findings": list(findings)}, **measured}})


def finding(kind, element, severity="error", **data):
    return {"severity": severity, "kind": kind, "element": element, "detail": "", "data": data}


def test_nothing_wrong_nothing_on_the_board(session):
    got = session.issues()["issues"]
    assert not [x for x in got if x["alert"]]
    conflict = next(x for x in got if x["kind"] == "conflict")  # waits on a person, chosen in the panel, not a failure
    assert not conflict["direct"] and [f["run"]["route"] for f in conflict["fixes"] if f["run"]] == ["conflict/pick", "conflict/pick"]


def test_three_alerts_with_one_cause_are_told_as_one(session):
    session.attach("food")
    board = session.monitor()
    assert len(board["alerts"]) == 3 and len(board["issues"]) == 1
    root = board["issues"][0]
    assert root["title"] == "식품 업종 확장 모듈이 없는 컬럼을 읽습니다" and root["bind_title"] == "DB 대조 오류 2건"
    assert root["cause"]["ref"] == "food" and root["cause"]["at"] and "속성 2개와 질의 1개" in root["cause"]["text"]
    assert [i["element"] for i in root["items"]] == ["property:Sku.expires_on", "property:Sku.storage"]
    assert "skus 테이블 컬럼 8개 중 비슷한 이름이 없습니다." == root["note"]
    assert {m["kind"] for m in root["members"]} == {"query", "check.values"} and root["floors"] == ["ontology", "use", "verify"]
    assert {"label": "질의 유통기한 임박 단품", "say": "원천 DB 실행 실패"} in root["effects"]
    assert root["fixes"][0]["recommended"] and root["fixes"][0]["where"] == "now" and root["fixes"][0]["preview"] == "food"  # nothing close and just attached
    rebind, ask = root["fixes"][1:]
    assert rebind["where"] == "here" and len(rebind["steps"]) == 2 and rebind["go"] == {"tab": "model", "el": "property:Sku.expires_on", "field": "column"}
    assert ask["where"] == "source" and "skus 테이블에 expires_on, storage 컬럼이 필요합니다." in ask["copy"]


def test_taking_the_module_off_is_tried_first_and_closes_the_issue(session):
    session.attach("food")
    session.issues()
    p = session.module_preview("food")
    assert p["gates"] == {"met": 6, "all": 6, "failed": []} and "단품 · 유통기한" in p["removed"]
    assert session.studio.composition.owner("property:Sku.expires_on") == "food"  # the try touched nothing
    session.detach("food")
    assert not [x for x in session.issues()["issues"] if x["alert"]]
    assert any(e["text"].startswith("해결됨") for e in session.events)


def test_when_an_issue_opened_outlives_a_restart(session, tmp_path):
    from xgen_space.journal import Journal
    from xgen_space.web import StudioSession

    session.studio.changes.journal = Journal(tmp_path / "j.jsonl")
    session.attach("food")
    since = next(x for x in session.issues()["issues"] if x["alert"])["since"]
    assert since
    other = StudioSession(session.studio)
    other._issue_open = None
    assert other.issues()["issues"][0]["since"] == since
    kinds = [(r["event"], r["id"]) for r in session.studio.changes.journal.read() if r["kind"] == "issue"]
    assert ("open", "bind:missing:food") in kinds


def test_a_near_column_is_offered_and_filled_in(session):
    got = built(session, [finding("column", "property:Sku.size", table="skus", column="sizes")])
    fix = next(f for f in got[0]["fixes"] if f["label"] == "원천 컬럼 다시 지정")
    assert fix["recommended"] and fix["go"]["prefill"] == "size" and "비슷한 이름" in got[0]["note"]


def test_each_kind_of_finding_opens_the_field_that_mends_it(session):
    enum = built(session, [finding("enum", "property:Order.status", "warning", table="orders", column="status", extra=["ODD"], counts={"ODD": 3})])[0]
    assert enum["level"] == "warn" and enum["items"][0]["go"]["append"] == ["ODD"] and "ODD (3건)" in enum["items"][0]["evidence"]
    assert enum["fixes"][0]["recommended"] and enum["fixes"][-1]["where"] == "source" and "ODD" in enum["fixes"][-1]["copy"]
    required = built(session, [finding("required", "property:Order.status", table="orders", columns=["status"], count=4, keys=["O1"])])[0]
    assert required["items"][0]["go"]["prefill"] is False and "빈 값 4행" in required["items"][0]["evidence"]
    orphan = built(session, [finding("orphan", "link:hasItem", "warning", table="order_items", column="order_id", count=2, values=["X"])])[0]
    assert orphan["items"][0]["go"]["field"] == "sp"
    key = built(session, [finding("key", "object:Order", table="orders", columns=["order_id"], keys=["O1"])])[0]
    assert [f["where"] for f in key["fixes"]] == ["source"]  # the key is the standard's: only its module may change it
    typed = built(session, [finding("type", "property:Order.status", "warning", table="orders", column="status", type="integer", sql_type="TEXT")])[0]
    assert typed["fixes"][0]["go"]["field"] == "transform"


def test_a_failure_that_does_not_read_the_broken_column_stands_alone(session):
    from xgen_space.web import issues

    w, _ = session._watched()
    flow = {**w["flow"], "steps": [{**s, "gates": [{"stage": "query", "condition": "min_agree", "label": "x", "limit": 1, "value": 0.9, "passed": False}] if s["id"] == "query" else s["gates"]} for s in w["flow"]["steps"]]}
    session.attach("food")
    report = {"agree": 19, "queries": 20, "reports": [{"name": "allParties", "outcomes": {"source": {"rows": 3, "error": ""}, "graph": {"rows": 2, "error": ""}}}]}
    bad = [finding("column", "property:Sku.expires_on", table="skus", column="expires_on")]
    got = issues.build(session, {"flow": flow, "measured": {"bind": {"findings": bad}, "query": report}})
    assert {x["kind"] for x in got} == {"bind.missing", "query"} and not next(x for x in got if x["kind"] == "bind.missing")["members"]
    query = next(x for x in got if x["kind"] == "query")
    assert query["fixes"][0]["label"] == "질의 열기" and query["fixes"][1]["recommended"]  # no error: the graph is behind, read the source again
    assert query["items"][0]["evidence"] == "source 3행 · graph 2행"


def test_what_waits_on_a_person_opens_directly(session):
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    x = next(i for i in session.issues()["issues"] if i["kind"] == "workspace")
    assert x["direct"] == {"tab": "model", "left": "changes"} and not x["fixes"]
    assert next(a for a in session.monitor()["alerts"] if a["key"] == "dirty")["tab"] == "model"


def test_a_finding_names_what_it_is_about(session):
    session.attach("food")
    f = session.bindings()["findings"][0]
    assert f["data"] == {"table": "skus", "column": "expires_on"}
