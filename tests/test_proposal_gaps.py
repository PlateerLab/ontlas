"""What the screen proposal asked for beyond the redesign: an element's status, a parent that cannot be taken out from
under its children, a request's size in the list of what waits, an answer that says why it is unknown and whom to ask,
perspectives and card positions kept for everyone, a file read as a person says it is, past cases decided by the
edited tables, and a draft that an approver applies in a team."""
from pathlib import Path

import pytest

from .conftest import LIB

ROOT = Path(__file__).resolve().parent.parent
CFG = LIB / "studio.yaml"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    return StudioSession(load_studio(CFG))


@pytest.fixture
def drafted(session):
    """The session with the example shop's files drafted and waiting to be applied."""
    from xgen_space.web.api import DataOptions

    session.data = DataOptions(samples=ROOT / "examples" / "files")
    session.use_samples()
    session.make_draft("가상 쇼핑몰")
    return session


def test_an_element_has_a_status_that_survives_the_file_and_the_modules():
    pytest.importorskip("yaml")
    from xgen_space.model import Ontology
    from xgen_space.modules import Module, compose

    o = Ontology.from_dict({"name": "t", "namespace": "https://example.org/t#", "objects": {
        "Order": {"key": "id", "status": "deprecated", "properties": {"id": {"type": "string"}, "memo": {"type": "string", "status": "draft"}}},
        "Item": {"key": "id", "properties": {"id": {"type": "string"}}}},
        "links": {"hasItem": {"from": "Order", "to": "Item", "status": "draft"}}})
    assert o.objects["Order"].status == "deprecated" and o.objects["Item"].status == "active"
    assert o.objects["Order"].properties["memo"].status == "draft" and o.links["hasItem"].status == "draft"
    d = o.to_dict()
    assert d["objects"]["Order"]["status"] == "deprecated" and "status" not in d["objects"]["Item"]
    assert d["links"]["hasItem"]["status"] == "draft"
    assert Ontology.from_dict(d).objects["Order"].status == "deprecated"
    base = Module.from_dict({"module": "base", "version": "1.0.0", "kind": "domain", "objects": d["objects"], "links": d["links"]})
    over = Module.from_dict({"module": "over", "version": "1.0.0", "kind": "customer", "requires": ["base"],
                             "extend": {"objects": {"Order": {"status": "active"}}, "links": {"hasItem": {"status": "deprecated"}}}})
    c = compose([base, over], namespace="https://example.org/t#")
    assert c.ontology.objects["Order"].status == "active" and c.ontology.links["hasItem"].status == "deprecated"
    bad = Ontology.from_dict({"name": "t", "namespace": "https://example.org/t#", "objects": {"A": {"key": "id", "status": "gone", "properties": {"id": {"type": "string"}}}}})
    assert any("status 'gone'" in i for i in bad.validate())


def test_the_workspace_sets_a_status_and_a_parent_is_not_taken_out_from_under_its_children(session):
    st = session.manage_edit("update_object", {"name": "Order", "status": "deprecated"})
    assert next(o for o in st["objects"] if o["name"] == "Order")["status"] == "deprecated"
    st = session.manage_edit("update_property", {"object": "Customer", "name": "phone", "status": "draft"})
    assert next(p for p in st["properties"] if p["object"] == "Customer" and p["name"] == "phone")["status"] == "draft"
    st = session.manage_edit("update_object", {"name": "Order", "status": "active"})  # back in use: nothing kept for it
    assert next(o for o in st["objects"] if o["name"] == "Order")["status"] == "active"
    with pytest.raises(ValueError) as e:
        session.manage_edit("delete_object", {"name": "Party"})
    assert "하위 객체" in str(e.value) and "Customer" in str(e.value) and "parent" not in str(e.value)


def test_the_inbox_says_how_much_a_request_changes_against_its_limit(session):
    if "changePrice" not in session.studio.onto.actions:
        session.attach("commerce-operations")
    o = session.studio.onto
    a = o.actions["changePrice"]
    role = next(r.name for r in o.roles.values() if r.can("request", a.name))
    row = next(r for r in session.studio.run("listSku").records()) if "listSku" in o.queries else None
    key = row["sku_id"] if row else session.studio.fetch("Sku", "S1")["sku_id"]
    before = float(session.studio.fetch("Sku", key)["price"])
    session.request(a.name, key, {"price": round(before * 1.3)}, role, kind="human")
    item = next(x for x in session.inbox()["items"] if x["kind"] == "action")
    assert "변화율 +30" in item["delta"] and "자동 승인 한도 10%" in item["delta"] and "초과" in item["delta"]


def test_an_unknown_answer_says_what_it_understood_and_whom_to_ask(session):
    out = session.space_ask("지난달 VIP 고객 반품률은?", "", {})
    if out.get("route") != "none":
        pytest.skip("the example answers this question now")
    assert "반품률" in out["reason"] and out["ask"] and out["ask"][0]["who"] == "고객경험팀"
    assert any(d["element"] == "metric:returnRate" for d in out["definitions"])


def test_an_unknown_answer_says_how_a_metric_is_not_split_and_how_to_ask_again(session):
    from xgen_space.answer import _unknown
    from xgen_space.tools import StudioTools

    if "returnRate" not in session.studio.onto.metrics:
        session.attach("commerce-operations")
    tools = StudioTools(session.studio)
    reason, ask = _unknown(tools, "고객 등급별 반품률은?", [])
    assert reason.startswith("질문에서 알아들은 것은 지표 반품률입니다.")
    assert "지표 반품률은(는) 등급별로 나누어 계산하도록 정의되어 있지 않습니다." in reason
    assert ask == [{"who": "고객경험팀", "about": "지표 반품률"}]
    reason, _ = _unknown(tools, "월별로 반품률은 어땠나", [])
    assert "월별로 나누어 계산하도록" in reason
    reason, _ = _unknown(tools, "지난달 반품률은?", [])  # nothing to split by: the first sentence alone
    assert "나누어" not in reason
    reason, ask = _unknown(tools, "그거 어떻게 돼?", [])
    assert reason.startswith("질문에서 정의된 객체, 지표, 판정, 문서를 찾지 못했습니다.") and ask == []
    assert "레코드 번호(예: I1001)나 정의의 이름을 넣어 다시 물어보세요." in reason


def test_graph_perspectives_and_card_positions_are_kept_for_everyone(session):
    v = session.graph_view_save("고객 상담", ["Order", "Nowhere"], {"Customer": "#1a73e8", "Nowhere": "#000000", "Order": "red"},
                                {"Customer": "name", "Order": "nope"}, "ops")
    view = v["views"]["고객 상담"]
    assert view["hide"] == ["Order"] and view["color"] == {"Customer": "#1a73e8"} and view["label"] == {"Customer": "name"}
    assert session.graph_views()["views"]["고객 상담"]["role"] == "ops"
    assert session.graph_view_save("전체", [], {}, {}, "boss")["views"]["전체"]["role"] == ""  # an unknown role is everyone's
    labels = session.record_labels("Customer", ["C001", "C002", "C999"], "name")["labels"]
    assert labels["C001"] and "C999" not in labels
    with pytest.raises(LookupError):
        session.record_labels("Customer", ["C001"], "nope")
    assert "고객 상담" not in session.graph_view_forget("고객 상담")["views"]
    with pytest.raises(ValueError):
        session.graph_view_save("  ", [], {}, {})
    got = session.workspace_layout("p1", {"Order": {"x": 10.4, "y": 20}, "Nowhere": {"x": 1, "y": 1}, "Item": "bad"})
    assert got["positions"] == {"Order": {"x": 10, "y": 20}}
    assert session.manage_state()["layout"] == {"Order": {"x": 10, "y": 20}}


def test_a_file_is_read_as_a_person_says_it_is(session):
    csv = "코드,이름\nA,가\nB,나\n".encode("utf-8")
    session.catalog_upload("코드.csv", csv)
    row = lambda: next(f for f in session.catalog_state()["files"] if f["path"] == "코드.csv")  # noqa: E731
    assert row()["facts"]["kind"] == "data" and not row().get("use")
    session.catalog_use("코드.csv", "raw")
    assert row()["facts"]["kind"] == "raw" and row()["use"] == "raw"
    session.catalog_use("코드.csv", "document")
    assert row()["error"] and "문서로 읽지 못했습니다" in row()["error"]
    session.catalog_use("코드.csv", "")
    assert row()["facts"]["kind"] == "data" and not row()["error"]
    session.catalog_upload("코드.csv", csv)  # a replaced file keeps what it was said to be
    session.catalog_use("코드.csv", "raw")
    session.catalog_upload("코드.csv", csv)
    assert row()["facts"]["kind"] == "raw"
    with pytest.raises(ValueError):
        session.catalog_use("코드.csv", "picture")


def test_past_cases_are_decided_by_the_edited_tables_when_asked(session):
    before = session.agreement()
    assert before["ok"] and not before["pending"]
    d = session.studio.onto.decisions["returnEligibility"]
    rule = next(r for r in d.rules if r.id == "in-window")
    session.manage_edit("update_rule", {"decision": d.name, "id": rule.id, "when": {**rule.when, "days_since_delivery": {"op": "lte", "value": 1}},
                                        "then": dict(rule.then)})
    after = session.agreement(pending=True)
    assert after["ok"] and after["pending"] and after["agree"] < before["agree"]
    assert session.agreement()["agree"] == before["agree"]  # the applied tables have not changed


def test_in_a_team_an_approver_applies_a_draft_and_a_viewer_moves_nothing():
    from xgen_space.web.team import NEEDS

    assert NEEDS["draft/apply"] == NEEDS["draft/review/apply"] == NEEDS["draft/map/apply"] == "approver"
    assert NEEDS["draft/review/preview"] == NEEDS["draft/table"] == "editor"
    assert NEEDS["catalog/move"] == NEEDS["catalog/trash"] == NEEDS["catalog/use"] == "editor"
    assert NEEDS["graph/view"] == NEEDS["graph/view/forget"] == NEEDS["workspace/layout"] == "editor"


def test_in_a_team_an_editor_files_an_apply_request_and_only_an_approver_applies_it():
    from xgen_space.web.team import NEEDS

    assert NEEDS["draft/request"] == NEEDS["draft/request/drop"] == "editor"
    assert NEEDS["draft/request/apply"] == "approver"


def test_an_editor_files_the_draft_and_an_approver_applies_what_was_filed(drafted):
    s = drafted
    objs = [o.name for o in s.pending[0].objects]
    gone, kept = objs[-1], objs[:-1]
    with pytest.raises(ValueError, match="적용을 요청하지 못했습니다"):
        s.request_draft([], {"names": {objs[0]: "payment"}}, None)  # an edit the draft refuses is refused here, not at the approver
    out = s.request_draft([], {"drop": [f"object:{gone}"]}, None)
    assert out["ok"] and out["request"]["by"] == "방문자" and out["request"]["label"] == "가상 쇼핑몰"
    assert out["request"]["objects"] == len(kept) and out["request"]["at"] and "edits" not in out["request"]
    st = s.files_state()
    assert st["pending"] and st["request"] == out["request"]
    item = next(x for x in s.inbox()["items"] if x["kind"] == "draft")
    assert item["id"] == "draft" and item["title"] == "가상 쇼핑몰 초안 적용" and item["by"] == "방문자" and item["mine"]
    assert item["waits"] == "approver" and item["detail"] == f"객체 {len(kept)}개 · 관계 {out['request']['links']}개"
    assert next(x for x in s.build_steps()["steps"] if x["id"] == "data")["detail"] == "적용 요청 대기"
    assert s.apply_draft_request()["ok"]
    onto = s.studio.onto
    assert set(kept) <= set(onto.objects) and gone not in onto.objects and s.state()["title"] == "가상 쇼핑몰"
    assert s.pending is None and s.draft_request is None and s.files_state()["request"] is None
    assert not [x for x in s.inbox()["items"] if x["kind"] == "draft"]
    with pytest.raises(ValueError):
        s.apply_draft_request()


def test_an_apply_request_is_dropped_or_goes_with_a_new_draft(drafted):
    s = drafted
    s.request_draft([], None, None)
    assert s.files_state()["request"]["objects"] == len(s.pending[0].objects)
    assert s.drop_draft_request()["ok"] and s.files_state()["request"] is None
    assert not [x for x in s.inbox()["items"] if x["kind"] == "draft"]
    assert next(x for x in s.build_steps()["steps"] if x["id"] == "data")["detail"] == "초안 검토 중"
    with pytest.raises(ValueError):
        s.drop_draft_request()
    s.request_draft([], None, None)
    s.make_draft("다시")  # a new draft is not what was filed: the request goes with the old one
    assert s.pending and s.files_state()["request"] is None


def test_an_apply_request_needs_a_draft(session):
    with pytest.raises(ValueError, match="초안을 먼저 생성해 주세요"):
        session.request_draft([], None, None)
    assert session.files_state()["request"] is None


def test_the_build_steps_say_where_the_space_stands(session):
    got = session.build_steps()
    ids = [s["id"] for s in got["steps"]]
    assert ids == ["catalog", "data", "model", "mgrules", "changes", "check", "search", "connect"]
    by = {s["id"]: s for s in got["steps"]}
    assert by["model"]["done"] and "객체" in by["model"]["detail"]  # the example library is a built ontology
    assert by["mgrules"]["done"] and not by["changes"]["done"] and not by["search"]["done"]
    assert by["catalog"]["done"] and "원천 테이블" in by["catalog"]["detail"]  # bound tables count as data brought in
    assert got["next"] == "changes"  # nothing has been reviewed and approved yet
    session.catalog_upload("쿠폰.csv", "쿠폰번호,할인율\nCP1,10\nCP2,20\n".encode("utf-8"))
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    got = session.build_steps()
    by = {s["id"]: s for s in got["steps"]}
    assert by["catalog"]["done"] and "파일" in by["catalog"]["detail"] and "대기 중인 변경 1" in by["model"]["detail"]
