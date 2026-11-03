import json
from pathlib import Path

import pytest

from xgen_data_studio.library import Library
from xgen_data_studio.policy import PolicyDrafter, cites

from .conftest import EXAMPLE
from .test_web import _build

LIB = EXAMPLE.parent / "library"
NS = {"namespace": "https://example.org/studio#"}
POLICY = (EXAMPLE.parent / "policies" / "교환정책서.md").read_text(encoding="utf-8")


def _table(**over):
    t = {"name": "exchangeEligibility", "label": "교환 가능 여부", "target": "OrderItem", "hit_policy": "first",
         "inputs": {"days": {"type": "integer", "days_since": "delivered_at"},
                    "status": {"type": "string", "property": "item_status"},
                    "grade": {"type": "string", "path": ["itemOf", "placedBy"], "property": "grade"}},
         "outputs": {"exchangeable": "boolean"},
         "rules": [{"id": "undelivered", "when": {"days": "null"}, "then": {"exchangeable": False}, "cite": "제3조 ①"},
                   {"id": "in-progress", "when": {"status": '!= "NORMAL"'}, "then": {"exchangeable": False},
                    "cite": "제3조 ②"},
                   {"id": "vip", "when": {"grade": '"VIP"', "days": "<= 30"}, "then": {"exchangeable": True},
                    "cite": "제2조 ②"},
                   {"id": "window", "when": {"days": "<= 14"}, "then": {"exchangeable": True}, "cite": "제2조 ①"},
                   {"id": "rest", "when": {}, "then": {"exchangeable": False}, "cite": "제4조"}]}
    t.update(over)
    return t


def _drafter(answers):
    seen = []
    it = iter(answers)

    def llm(system, user):
        seen.append(user)
        return next(it)

    return PolicyDrafter(Library(LIB).resolve(["commerce", "commerce-bindings"]), llm, compose_kw=NS), seen


def test_a_cite_names_a_clause_the_policy_numbers():
    assert cites("제3조 ②", POLICY) and cites("제2조", POLICY) and cites("교환 기간", POLICY)
    assert not cites("제9조", POLICY) and not cites("", POLICY) and not cites("반품 정책 2.1", POLICY)


def test_a_drafted_table_that_checks_becomes_a_module_that_requires_what_it_reads():
    drafter, _ = _drafter(["Here it is:\n```json\n" + json.dumps(_table(), ensure_ascii=False) + "\n```"])
    d = drafter.draft(POLICY)
    assert d.ok and len(d.attempts) == 1
    m = d.module
    assert m.name == "policy-exchange-eligibility" and m.kind == "customer" and [str(r) for r in m.requires] == ["commerce"]
    assert m.body["decisions"]["exchangeEligibility"]["rules"][2]["cite"] == "제2조 ②"


def test_what_is_wrong_goes_back_to_the_model_until_it_checks():
    bad = _table(inputs={**_table()["inputs"], "grade": {"type": "string", "path": ["itemOf", "placedBy"],
                                                           "property": "tier"}})
    bad["rules"][-1]["cite"] = "제9조"
    drafter, seen = _drafter([json.dumps(bad, ensure_ascii=False), json.dumps(_table(), ensure_ascii=False)])
    d = drafter.draft(POLICY, target="OrderItem")
    first = d.attempts[0].issues
    assert any("no property 'tier'" in i for i in first) and any("'제9조'" in i for i in first)
    assert "It has these problems" in seen[1] and "The decision is about OrderItem" in seen[0]
    assert d.ok and len(d.attempts) == 2


def test_a_table_that_cannot_be_a_module_says_why():
    drafter, _ = _drafter(["not json", json.dumps(_table(name="returnEligibility")),
                           json.dumps(_table(target="Nothing"))])
    d = drafter.draft(POLICY)
    assert [a.issues[0] for a in d.attempts] == [
        "the answer was not one JSON object", "decision 'returnEligibility' already exists; give the new one another name",
        "target 'Nothing' is not an object type"]
    assert d.module is None and not d.ok


def test_the_page_drafts_from_the_sample_policy_and_opens_a_module_that_decides():
    pytest.importorskip("rdflib")
    from xgen_data_studio.web import DataOptions

    s = _build()
    assert not s.policy_draft("제1조 ...")["ok"]  # no language model
    s.data = DataOptions(policies=Path(EXAMPLE.parent / "policies"))
    s.llm = lambda system, user: json.dumps(_table(), ensure_ascii=False)
    sample = s.policy_sample()
    assert sample["ok"] and sample["name"] == "교환정책서.md" and s.state()["data"]["policy_sample"]
    r = s.policy_draft(sample["text"], target="OrderItem")
    assert r["ok"] and r["decision"] == "exchangeEligibility" and not r["issues"] and r["attempts"] == 1
    assert [x["cite"] for x in r["rules"]] == ["제3조 ①", "제3조 ②", "제2조 ②", "제2조 ①", "제4조"]
    change = s.propose_module(r["yaml"], attach=True)["change"]  # a person files it; the copy decides with it
    assert change["passed"] and "decision:exchangeEligibility" in change["diff"]["added"]
    with pytest.raises(ValueError, match="정책서 내용이 없어"):
        s.policy_draft("  ")


def test_policy_drafts_need_an_editor_in_a_team_studio():
    from xgen_data_studio.web.team import NEEDS

    assert NEEDS["policy/draft"] == "editor"
