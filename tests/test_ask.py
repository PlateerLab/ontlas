import pytest

from .test_web import _build


def test_a_question_tries_again_only_while_the_page_can_still_wait(monkeypatch):
    pytest.importorskip("rdflib")
    from xgen_data_studio.web import api

    calls = []
    s = _build()
    s.llm = lambda system, user: calls.append(user) or "not a JSON object"
    out = s.ask("VIP 등급 고객의 이름을 알려 주세요")
    assert not out["ok"] and len(calls) == 3  # in time: the first answer and two repairs
    calls.clear()
    monkeypatch.setattr(api, "ASK_RETRY_WITHIN", -1.0)  # below zero: the clock may not move between fast calls
    out = s.ask("VIP 등급 고객의 이름을 알려 주세요")
    assert not out["ok"] and len(calls) == 1  # out of time: the first answer only
    assert "not one JSON object" in out["error"] and "응답 시간 한도" in out["error"]  # what the model said, and why


def test_a_column_named_after_another_property_is_sent_back():
    from xgen_data_studio.nl import IRGenerator

    s = _build()
    answers = iter(['{"match": {"c": "Customer"}, "where": {"eq": ["c.grade", "VIP"]}, '
                    '"return": [{"col": "c.customer_id", "as": "name"}]}',
                    '{"match": {"c": "Customer"}, "where": {"eq": ["c.grade", "VIP"]}, "return": ["c.name"]}'])
    gen = IRGenerator(s.studio.onto, lambda system, user: next(answers)).generate("VIP 고객 이름")
    assert "another property of Customer" in gen.attempts[0].issues[0]
    assert gen.ok and [c.name for c in gen.query.columns] == ["name"] and gen.query.columns[0].expr.prop == "name"
