"""Requests, approvals and the audit trail outlive a restart; each agent is itself, reads its own documents and requests,
and a request is settled by someone other than the one who made it."""
import json
from pathlib import Path

import pytest

from xgen_space import Ontology
from xgen_space.actions import Actor
from xgen_space.backends.sql import SqliteBackend
from xgen_space.rest import Rest
from xgen_space.studio import Studio
from xgen_space.tools import StudioTools

SEED = """
CREATE TABLE goods (goods_id TEXT PRIMARY KEY, name TEXT, price INTEGER, shop_id TEXT, stock INTEGER);
INSERT INTO goods VALUES ('G1', '연필', 1000, 'H1', 3), ('G2', '공책', 3000, 'H2', 0), ('G3', '지우개', 500, 'H1', 9);
"""
SPEC = {
    "ontology": "shop", "version": "2.1.0", "namespace": "https://example.org/shop#",
    "objects": {"Goods": {"key": "goods_id", "source": {"table": "goods"},
                          "properties": {"goods_id": {"type": "string"}, "name": {"type": "string"},
                                         "price": {"type": "integer"}, "shop_id": {"type": "string"},
                                         "stock": {"type": "integer"}}}},
    "decisions": {"canSell": {"target": "Goods", "inputs": {"stock": {"type": "integer", "property": "stock"}},
                              "outputs": {"ok": "boolean"},
                              "rules": [{"id": "none", "when": {"stock": "<= 0"}, "then": {"ok": False}},
                                        {"id": "some", "when": {}, "then": {"ok": True}}]}},
    "actions": {"setPrice": {"target": "Goods", "parameters": {"to": {"type": "integer"}}, "set": {"price": "$to"},
                             "criteria": [{"decision": "canSell", "expect": {"ok": True}}]}},
    "roles": {"clerk": {"read": ["Goods"], "run": ["canSell"], "request": ["setPrice"], "execute": ["setPrice"]},
              "seller": {"read": ["Goods"], "run": ["canSell"], "request": ["setPrice"],
                         "row_filters": {"Goods": {"eq": ["$self.shop_id", {"principal": "shop_id"}]}},
                         "documents": ["안내*"]}},
}


def studio(db: Path) -> Studio:
    st = Studio(Ontology.from_dict(SPEC).check())
    b = SqliteBackend(str(db))
    if not b.conn.execute("SELECT name FROM sqlite_master WHERE name = 'goods'").fetchone():
        b.script(SEED)
    st.add_backend("source", b)
    return st


KIM, LEE = Actor("kim", "human", ["clerk"]), Actor("lee", "human", ["clerk"])


# ---- a restart forgets nothing

def test_a_waiting_request_and_its_audit_trail_survive_a_restart(tmp_path):
    db, kept = tmp_path / "shop.db", tmp_path / "journal.jsonl"
    first = studio(db)
    first.keep_journal(kept)
    p = first.actions.request("setPrice", "G1", {"to": 1100}, actor=KIM)
    assert p.status == "pending"
    trail = len(first.actions.audit)

    again = studio(db)  # the process ends; a new one reads the same file
    again.keep_journal(kept)
    assert again.actions.proposals["P1"].status == "pending"
    assert len(again.actions.audit) == trail and again.actions.audit[0].actor == "kim"
    q = again.actions.approve("P1", approver=LEE)
    assert q.status == "executed" and again.fetch("Goods", "G1")["price"] == 1100
    assert again.actions.request("setPrice", "G3", {"to": 600}, actor=KIM).id == "P2"  # numbering goes on

    third = studio(db)
    third.keep_journal(kept)
    done = third.actions.proposals["P1"]
    assert done.approved_by == "lee" and done.before == {"price": 1000}
    third.actions.rollback("P1", actor=LEE)  # what it replaced was kept, so it can still be put back
    assert third.fetch("Goods", "G1")["price"] == 1000


def test_a_line_cut_off_by_a_crash_leaves_the_lines_before_it(tmp_path):
    db, kept = tmp_path / "shop.db", tmp_path / "journal.jsonl"
    first = studio(db)
    first.keep_journal(kept)
    first.actions.request("setPrice", "G1", {"to": 1100}, actor=KIM)
    with kept.open("a", encoding="utf-8") as f:
        f.write('{"kind": "action", "audit": {"at": "2026')
    again = studio(db)
    again.keep_journal(kept)
    assert again.actions.proposals["P1"].status == "pending"


def test_a_change_request_survives_a_restart(tmp_path):
    pytest.importorskip("rdflib")
    import copy

    from xgen_space.config import load_studio
    from xgen_space.library import OverlayLibrary
    from xgen_space.modules import Module

    cfg = Path(__file__).resolve().parents[1] / "examples" / "library" / "studio.yaml"
    kept = tmp_path / "journal.jsonl"
    st = load_studio(cfg)
    st.library = OverlayLibrary(st.library, [])  # the example folder is never written
    st.keep_journal(kept)
    d = copy.deepcopy(st.library.get("acme-overlay").to_dict())
    d["version"] = "1.1.0"
    cr = st.changes.propose(Module.from_dict(d), by="kim")
    again = load_studio(cfg)
    again.keep_journal(kept)
    assert again.changes.requests[cr.id].status == "pending" and again.changes.requests[cr.id].version == "1.1.0"
    assert again.changes.audit[-1]["event"] == "proposed" and again.changes.audit[-1]["by"] == "kim"


# ---- who settles a request

def test_the_one_who_asked_does_not_approve_or_reject_it(tmp_path):
    st = studio(tmp_path / "shop.db")
    p = st.actions.request("setPrice", "G1", {"to": 1100}, actor=KIM)
    with pytest.raises(PermissionError, match="another person"):
        st.actions.approve(p.id, approver=KIM)
    with pytest.raises(PermissionError, match="another person"):
        st.actions.reject(p.id, approver=KIM)
    st.actions.self_approve = True  # one person playing both sides, as on a visitor's own page
    assert st.actions.approve(p.id, approver=KIM).status == "executed"


def test_a_request_that_ran_is_rolled_back_not_rejected(tmp_path):
    st = studio(tmp_path / "shop.db")
    p = st.actions.request("setPrice", "G1", {"to": 1100}, actor=KIM)
    st.actions.approve(p.id, approver=LEE)
    with pytest.raises(ValueError, match="roll it back"):
        st.actions.reject(p.id, approver=LEE)
    assert p.status == "executed" and st.fetch("Goods", "G1")["price"] == 1100  # the record and the source agree


def test_an_agent_or_a_person_without_the_right_does_not_reject(tmp_path):
    st = studio(tmp_path / "shop.db")
    p = st.actions.request("setPrice", "G1", {"to": 1100}, actor=KIM)
    with pytest.raises(PermissionError, match="only a person"):
        st.actions.reject(p.id, approver=Actor("bot", "agent", ["clerk"]))
    with pytest.raises(PermissionError, match="may not execute"):
        st.actions.reject(p.id, approver=Actor("park", "human", ["seller"]))
    assert st.actions.reject(p.id, approver=LEE, reason="가격 협의 중").status == "rejected"


# ---- the audit says what an answer stood on

def test_the_audit_names_the_module_version_and_the_rule(tmp_path):
    st = studio(tmp_path / "shop.db")
    st.actions.request("setPrice", "G1", {"to": 1100}, actor=KIM)
    asked = st.actions.audit[0]
    assert asked.versions == ["shop@2.1.0"] and asked.detail["rules"] == ["canSell.some"]
    st.actions.request("setPrice", "G2", {"to": 3100}, actor=KIM)
    refused = st.actions.audit[-1]
    assert refused.event == "rejected" and refused.detail["failed"] == ["decision:canSell"]
    assert refused.detail["rules"] == ["canSell.none"]


def test_an_agents_decision_and_answer_go_into_the_audit(tmp_path):
    st = studio(tmp_path / "shop.db")
    bot = StudioTools(st, role="clerk", actor_id="가격 Agent", audit=True)
    bot.decide("canSell", "G2")
    seen = st.actions.audit[-1]
    assert (seen.actor, seen.event, seen.key, seen.detail["rules"]) == ("가격 Agent", "decided", "G2", ["canSell.none"])
    StudioTools(st, role="clerk").decide("canSell", "G1")  # a caller that is not audited leaves no line
    assert st.actions.audit[-1] is seen


# ---- each agent is itself

def test_an_agent_sees_its_own_requests_and_no_one_elses(tmp_path):
    st = studio(tmp_path / "shop.db")
    north = StudioTools(st, role="seller", principal={"shop_id": "H1"}, actor_id="북쪽 Agent")
    south = StudioTools(st, role="seller", principal={"shop_id": "H2"}, actor_id="남쪽 Agent")
    north.request_action("setPrice", "G1", {"to": 1100})
    south.request_action("setPrice", "G2", {"to": 3100})
    assert [p["key"] for p in north.list_proposals()] == ["G1"]
    assert [p["key"] for p in south.list_proposals()] == ["G2"]
    assert len(StudioTools(st).list_proposals()) == 2  # a caller with no role reads everything, as before
    with pytest.raises(PermissionError):
        north.get_record("Goods", "G2")
    assert {v["name"]: v["value"] for v in north.get_record("Goods", "G1")["values"]}["price"] == 1000


def test_each_token_is_one_agent_in_the_audit(tmp_path):
    st = studio(tmp_path / "shop.db")
    rest = Rest([("t-north", StudioTools(st, role="seller", principal={"shop_id": "H1"}, actor_id="북쪽 Agent", audit=True)),
                 ("t-south", StudioTools(st, role="seller", principal={"shop_id": "H2"}, actor_id="남쪽 Agent", audit=True))])
    assert rest.caller("Bearer nope") is None
    north, south = rest.caller("Bearer t-north"), rest.caller("Bearer t-south")
    code, out = rest.answer("POST", "/v1/actions", {"action": "setPrice", "key": "G1", "params": {"to": 1100}}, north)
    assert code == 200 and out["requested_by"]["id"] == "북쪽 Agent"
    code, out = rest.answer("GET", "/v1/proposals", {}, south)
    assert code == 200 and out == {"proposals": []}
    code, out = rest.answer("POST", "/v1/record", {"object": "Goods", "key": "G1"}, south)
    assert code == 403
    assert {e.actor for e in st.actions.audit} == {"북쪽 Agent"}


# ---- documents a role reads

def test_a_role_reads_only_its_documents():
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio

    st = load_studio(Path(__file__).resolve().parents[1] / "examples" / "library" / "studio.yaml")
    agent = StudioTools(st, role="customer_agent", principal={"customer_id": "C001"})
    names = {d["name"] for d in agent.list_documents()["documents"]}
    assert "판매자운영기준" not in names and "반품정책서" in names
    hits = agent.search_documents("판매 수수료는 얼마인가요", 5)["hits"]
    assert hits and all(h["document"] != "판매자운영기준" for h in hits)
    said = agent.answer_question("판매 수수료는 얼마인가요")
    assert all(s.get("document") != "판매자운영기준" for s in said["sources"])
    everyone = StudioTools(st)
    assert "판매자운영기준" in {d["name"] for d in everyone.list_documents()["documents"]}


def test_a_document_list_survives_a_module_round_trip():
    onto = Ontology.from_dict({**SPEC, "roles": {"none": {"read": ["Goods"], "documents": []}, "all": {"read": ["Goods"]}}})
    from xgen_space.model import _to_dict

    back = Ontology.from_dict(json.loads(json.dumps(_to_dict(onto))))
    assert back.roles["none"].documents == [] and not back.roles["none"].can_read_document("안내문")
    assert back.roles["all"].documents is None and back.roles["all"].can_read_document("안내문")


# ---- a request from the page

def test_a_person_on_the_page_runs_a_change_inside_its_limit_and_an_agent_waits():
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    s = StudioSession(load_studio(Path(__file__).resolve().parents[1] / "examples" / "library" / "studio.yaml"))
    small = s.request("changePrice", "S1", {"price": 62000}, "operator", kind="human")["proposal"]
    assert small["status"] == "executed" and small["approved_by"] == "auto" and small["requested_kind"] == "human"
    waits = s.request("changePrice", "S2", {"price": 62000}, "operator")["proposal"]  # an agent, by default
    assert waits["status"] == "pending" and waits["requested_kind"] == "agent"
    big = s.request("changePrice", "S3", {"price": 26000}, "operator", kind="human")["proposal"]
    assert big["status"] == "pending" and not big["limits"][0]["within"]
