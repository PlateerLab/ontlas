import json
import threading
import time
from pathlib import Path

import pytest

from xgen_space.library import Library
from xgen_space.policy import PolicyDrafter, cites

from .conftest import EXAMPLE, LIB
from .test_web import _build

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
    from xgen_space.web import DataOptions

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
    from xgen_space.web.team import NEEDS

    assert NEEDS["policy/draft"] == "editor"


def test_a_bare_number_cites_a_numbered_heading_and_not_a_digit_in_the_text():
    text = "1. 반품 기간\n배송 후 14일 이내입니다.\n2) 반품 제한\n속옷은 안 됩니다."
    assert cites("1", text) and cites("2.", text) and cites("2) 반품 제한", text) and cites("1. 반품 기간", text)
    assert not cites("4", text) and not cites("3", text) and not cites("제1조", text)


def test_an_answer_cut_off_by_the_token_budget_is_told_apart_and_a_draft_gets_a_larger_budget(monkeypatch):
    import io
    import urllib.request

    from xgen_space.nl import AnswerCutOff, openai_chat

    seen = []

    def fake(req, timeout):
        body = json.loads(req.data)
        seen.append((body["max_tokens"], timeout))
        room = body["max_tokens"] > 4000
        choice = {"message": {"content": "{}" if room else None}, "finish_reason": "stop" if room else "length"}
        return io.BytesIO(json.dumps({"choices": [choice]}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake)
    chat = openai_chat("http://model/v1", "m", extra={"max_tokens": 4000})
    with pytest.raises(AnswerCutOff):
        chat("s", "u")
    assert chat.roomier(12000, 200.0)("s", "u") == "{}"
    assert seen == [(4000, 90), (12000, 200.0)]


def _wait_for(s, job):
    for _ in range(500):
        r = s.policy_result(job)
        if not r.get("running"):
            return r
        time.sleep(0.01)
    raise AssertionError("the draft did not finish")


def test_a_draft_runs_apart_from_the_page_request_and_the_page_collects_it():
    pytest.importorskip("rdflib")
    s = _build()
    gate = threading.Event()

    def slow(system, user):
        gate.wait(5)
        return json.dumps(_table(), ensure_ascii=False)

    s.llm = slow
    job = s.policy_start(POLICY, target="OrderItem")["job"]
    assert s.policy_result(job) == {"ok": True, "running": True}
    assert s.policy_start(POLICY, target="OrderItem")["job"] == job  # one at a time for a visitor
    gate.set()
    r = _wait_for(s, job)
    assert r["ok"] and r["decision"] == "exchangeEligibility" and not r["issues"]
    assert not s.policy_result("another")["ok"]
    assert s.policy_start(POLICY)["job"] != job  # a finished draft leaves room for the next


def test_a_draft_that_cannot_finish_ends_the_wait_with_a_reason_in_plain_words():
    pytest.importorskip("rdflib")
    from xgen_space.nl import AnswerCutOff

    s = _build()

    def cut(system, user):
        raise AnswerCutOff("the token budget ran out before the answer")

    s.llm = cut
    r = _wait_for(s, s.policy_start(POLICY, target="OrderItem")["job"])
    assert not r["ok"] and "답변을 끝내지 못했습니다" in r["error"] and "AnswerCutOff" not in r["error"]
    r = _wait_for(s, s.policy_start("  ")["job"])
    assert not r["ok"] and "정책서 내용이 없어" in r["error"]
