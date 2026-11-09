"""The modelling workspace: an object written back as YAML becomes the same edits a form makes, the last edit taken
back, the edits tried on a copy before they are filed, and comments kept on the elements they are about."""
import pytest

from .conftest import LIB


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    return StudioSession(load_studio(LIB / "studio.yaml"))


def test_an_object_is_read_and_written_back_as_yaml(session):
    import yaml

    text = session.element_yaml("object:Order")["yaml"]
    spec = yaml.safe_load(text)["Order"]
    assert spec["key"] and spec["properties"][spec["key"]]["required"]
    spec["label"] = "주문서"
    spec["properties"]["memo"] = {"type": "string", "label": "메모"}
    state = session.manage_yaml("object:Order", yaml.safe_dump({"Order": spec}, allow_unicode=True))
    ops = [e["op"] for e in state["workspace"]["edits"]]
    assert ops == ["add_property", "update_object"]
    assert yaml.safe_load(session.element_yaml("object:Order")["yaml"])["Order"]["label"] == "주문서"
    with pytest.raises(ValueError):
        session.manage_yaml("object:Order", "Customer: {}")  # another object's name
    with pytest.raises(ValueError):
        session.manage_yaml("object:Order", "Order: [")


def test_a_bad_yaml_edit_leaves_the_workspace_as_it_was(session):
    import yaml

    spec = yaml.safe_load(session.element_yaml("object:Order")["yaml"])["Order"]
    spec["label"] = "주문서"
    spec["properties"]["memo"] = {"type": "nosuchtype"}
    with pytest.raises(ValueError):
        session.manage_yaml("object:Order", yaml.safe_dump({"Order": spec}, allow_unicode=True))
    assert not session.manage_state()["workspace"]["edits"]


def test_the_last_edit_is_taken_back(session):
    session.manage_edit("add_property", {"object": "Order", "name": "memo", "type": "string", "label": "메모"})
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    w = session.manage_undo()["workspace"]
    assert [e["op"] for e in w["edits"]] == ["add_property"]
    assert not session.manage_undo()["workspace"]["dirty"]
    with pytest.raises(ValueError):
        session.manage_undo()


def test_pending_edits_are_tried_on_a_copy_and_say_what_they_reach(session):
    with pytest.raises(ValueError):
        session.manage_trial()  # nothing to try
    state = session.manage_edit("delete_property", {"object": "Order", "name": "status"})
    assert sum(state["workspace"]["impact"].values()) > 0  # something reads the order's status
    t = session.manage_trial()
    assert t["gates"] and all("label" in g for g in t["gates"]) and t["before"]


def test_a_comment_stays_on_its_element(session):
    session.element_comment("object:Order", "  주문 상태 값은 운영팀과 확인  ")
    assert session.element_comments("object:Order")["comments"][0]["text"] == "주문 상태 값은 운영팀과 확인"
    assert session.manage_state()["comments"] == {"object:Order": 1}
    with pytest.raises(ValueError):
        session.element_comment("object:Order", " ")


def test_an_object_says_who_adds_to_it_but_not_where_it_is_bound(session):
    objs = {o["name"]: o for o in session.manage_state()["objects"]}
    assert all("Binding" not in x for o in objs.values() for x in o["extended_by"])


def test_a_rule_moves_and_the_table_is_tried_as_edited(session):
    before = session.simulate("returnEligibility", "I1001")
    assert before["matched"][0] == "vip-window" and not before["pending"] and all(q["passed"] for q in before["questions"])
    session.manage_edit("move_rule", {"decision": "returnEligibility", "id": "in-window", "to": 0})
    order = [r["id"] for d in session.manage_state()["decisions"] if d["name"] == "returnEligibility" for r in d["rules"]]
    assert order[:2] == ["in-window", "vip-window"]
    after = session.simulate("returnEligibility", "I1001")
    assert after["pending"] and after["matched"] == ["in-window"]
    assert any(not q["passed"] for q in after["questions"])  # the VIP question no longer gets its rule
    assert session.studio.decide("returnEligibility", "I1001").matched[0] == "vip-window"  # the studio is unchanged


def test_a_table_takes_another_hit_policy_only_when_its_rules_allow_it(session):
    with pytest.raises(ValueError, match="우선순위"):
        session.manage_edit("update_decision", {"decision": "returnEligibility", "hit_policy": "priority"})
    session.manage_edit("update_decision", {"decision": "returnEligibility", "hit_policy": "collect"})
    d = next(d for d in session.manage_state()["decisions"] if d["name"] == "returnEligibility")
    assert d["hit_policy"] == "collect" and any(r["module"] == "acme-overlay" for r in d["rules"])
    edited = [f for f in session.rules_state()["findings"] if f["decision"] == "returnEligibility"]
    assert not edited  # a collected table has nothing to overlap


def test_a_query_put_together_on_the_page_is_kept_by_its_name(session):
    q = {"match": {"x": "OrderItem", "y": "Order"}, "edges": [["y", "hasItem", "x"]],
         "where": {"eq": ["x.item_status", "NORMAL"]}, "return": ["x.item_id", "y.status"], "limit": 100}
    state = session.manage_edit("add_query", {"name": "normalItems", "label": "정상 주문상품", "query": q})
    assert "normalItems" in [x["name"] for x in state["queries"]]
    with pytest.raises(ValueError, match="이미 있어"):
        session.manage_edit("add_query", {"name": "normalItems", "query": q})
    with pytest.raises(ValueError):
        session.manage_edit("add_query", {"name": "broken", "query": {"match": {}}})
