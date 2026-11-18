"""The quality screens' own routes: a validation question written whole and tried before it is saved, the log of
what was decided and approved, and which documents stand behind which Object."""
from pathlib import Path

import pytest

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

SHOP = Path(__file__).resolve().parent.parent / "examples" / "library" / "studio.yaml"


@pytest.fixture
def s():
    pytest.importorskip("yaml")
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    return StudioSession(load_studio(SHOP))


def routes():
    from ontlas.web import routes as r

    r.load()
    return r


def pending(s, qid):
    return next((q for q in s.manage_state()["questions"] if q["id"] == qid), None)


def test_a_new_question_takes_the_next_id_of_the_series(s):
    save = routes().find("POST", "qa/question/save")
    out = save(s, {"new": True, "type": "definition", "text": "반품 귀책 구분에는 어떤 것이 있나요?", "expect": "고객",
                   "keywords": "고객, 판매자", "grading": "keywords"}, None)
    ids = [q.id for q in s.studio.onto.questions]
    assert out["ok"] and out["id"] not in ids and out["element"] == f"question:{out['id']}"
    q = pending(s, out["id"])
    assert q["pending"] and q["type"] == "definition" and q["grading"] == "keywords" and q["keywords"] == ["고객", "판매자"]


def test_the_next_id_follows_the_numbering_the_others_use():
    from ontlas.web.areas.qa import _next_id

    assert _next_id([]) == "Q1"
    assert _next_id(["Q1", "Q2", "OP1"]) == "Q3"
    assert _next_id(["TF-Q01", "TF-Q09"]) == "TF-Q10"
    assert _next_id(["ask-abc"]) == "Q1"


def test_a_decision_question_needs_values_or_a_key_and_an_expected_verdict(s):
    save = routes().find("POST", "qa/question/save")
    base = {"new": True, "type": "decision", "text": "배송 완료 20일 된 주문상품, 반품 되나요?", "decision": "returnEligibility"}
    with pytest.raises(ValueError, match="판정 값이나 레코드 키"):
        save(s, {**base, "expect": {"eligible": False}}, None)
    with pytest.raises(ValueError, match="정답"):
        save(s, {**base, "key": "I1001"}, None)
    out = save(s, {**base, "key": "I1001", "expect": {"eligible": True}, "holdout": True}, None)
    q = pending(s, out["id"])
    assert q["decision"] == "returnEligibility" and q["key"] == "I1001" and q["holdout"] and q["expect"] == {"eligible": True}


def test_a_question_graded_by_keywords_is_refused_without_keywords_before_it_is_written(s):
    save = routes().find("POST", "qa/question/save")
    base = {"new": True, "type": "definition", "text": "반품 기간은 얼마인가요?", "expect": "14일", "grading": "keywords"}
    with pytest.raises(ValueError, match="^키워드가 없어 저장하지 못했습니다"):
        save(s, {**base, "keywords": " , "}, None)
    assert not s.manage_state()["workspace"]["dirty"]
    assert save(s, {**base, "keywords": "14일"}, None)["ok"]


def test_a_decision_question_keeps_the_inputs_it_gives_and_no_others(s):
    """Some inputs given and the rest left to the table: saved as given, none filled in as 값 없음."""
    save = routes().find("POST", "qa/question/save")
    out = save(s, {"new": True, "type": "decision", "text": "주문 금액 3만 원이면 배송비는?", "decision": "shippingFee",
                   "values": {"order_total": 30000}, "expect": {"fee": 3000}}, None)
    assert pending(s, out["id"])["values"] == {"order_total": 30000}


def test_an_id_already_used_is_refused_for_a_new_question(s):
    save = routes().find("POST", "qa/question/save")
    with pytest.raises(ValueError, match="이미 있어"):
        save(s, {"new": True, "id": "Q1", "type": "definition", "text": "무엇인가요?", "expect": "값"}, None)


def test_what_did_not_change_is_not_rewritten_and_nothing_changed_is_said(s):
    save = routes().find("POST", "qa/question/save")
    q = next(x for x in s.manage_state()["questions"] if x["id"] == "Q2")
    same = {"id": "Q2", "type": q["type"], "text": q["text"], "decision": q["decision"], "key": q["key"],
            "values": q["values"], "expect": q["expect"], "grading": q["grading"], "holdout": q["holdout"],
            "keywords": q["keywords"], "owner": q["owner"]}
    with pytest.raises(ValueError, match="변경된 내용이 없어"):
        save(s, same, None)
    save(s, {**same, "holdout": True, "owner": "고객센터"}, None)
    now = pending(s, "Q2")
    assert now["holdout"] and now["owner"] == "고객센터" and now["text"] == q["text"] and now["expect"] == q["expect"]
    assert [e["op"] for e in s.manage_state()["workspace"]["edits"]] == ["update_question"]


def test_new_words_for_a_question_are_one_step_that_keeps_its_id(s):
    save = routes().find("POST", "qa/question/save")
    q = next(x for x in s.manage_state()["questions"] if x["id"] == "Q2")
    args = {"id": "Q2", "type": q["type"], "text": q["text"] + " 다시 묻습니다", "decision": q["decision"], "key": q["key"],
            "values": q["values"], "expect": q["expect"], "grading": q["grading"]}
    save(s, args, None)
    now = pending(s, "Q2")
    assert now["text"].endswith("다시 묻습니다") and now["decision"] == q["decision"] and now["expect"] == q["expect"]
    assert len([x for x in s.manage_state()["questions"] if x["id"] == "Q2"]) == 1


def test_a_rewrite_that_does_not_hold_leaves_the_question_as_it_was(s):
    save = routes().find("POST", "qa/question/save")
    q = next(x for x in s.manage_state()["questions"] if x["id"] == "Q1")
    with pytest.raises(ValueError):
        save(s, {"id": "Q1", "type": "value", "text": q["text"] + " 바꿈", "query": "noSuchQuery", "expect": {"rows": 1}}, None)
    assert pending(s, "Q1")["text"] == q["text"] and not s.manage_state()["workspace"]["dirty"]


def test_a_question_is_tried_as_the_check_asks_it_and_nothing_is_kept(s):
    attempt = routes().find("POST", "qa/question/try")
    held = list(s.studio.onto.questions)
    q = next(x for x in s.manage_state()["questions"] if x["id"] == "Q2")
    args = {"type": "decision", "text": q["text"], "decision": q["decision"], "key": q["key"], "values": q["values"],
            "expect": q["expect"]}
    right = attempt(s, args, None)
    assert right["ok"] and right["measured"] and right["passed"] is True
    assert right["unmeasured"] == "" and "note" not in right  # why one is not measured is said by its reason, in the screen's words
    wrong = attempt(s, {**args, "expect": {k: (not v if isinstance(v, bool) else v) for k, v in q["expect"].items()}}, None)
    assert wrong["passed"] is False
    assert s.studio.onto.questions == held and not s.manage_state()["workspace"]["dirty"]
    assert attempt(s, {"type": "decision", "text": "x"}, None)["ok"] is False


def test_a_question_filed_under_one_type_may_ask_another_way(s):
    """A value question may be answered by a decision table and held right by its words: it is saved as it is."""
    save = routes().find("POST", "qa/question/save")
    q = next(x for x in s.manage_state()["questions"] if x["id"] == "OP6")
    assert q["type"] == "value" and q["decision"]
    args = {"id": "OP6", "type": q["type"], "text": q["text"], "decision": q["decision"], "key": q["key"], "values": q["values"],
            "expect": q["expect"], "grading": q["grading"], "keywords": q["keywords"], "owner": "배송팀"}
    save(s, args, None)
    now = pending(s, "OP6")
    assert now["owner"] == "배송팀" and now["type"] == "value" and now["decision"] == q["decision"] and now["values"] == q["values"]
    with pytest.raises(ValueError, match="판정 대상이 없어"):
        save(s, {"new": True, "type": "value", "text": "얼마인가요?", "expect": {"rows": 1}}, None)


def test_the_log_lists_change_requests_and_measurements_newest_first(s):
    log = routes().find("GET", "qa/decisions")
    assert log(s, {}, None) == {"rows": [], "total": 0}
    s.manage_edit("update_question", {"id": "Q2", "holdout": True})
    s.manage_propose()
    s.event("measure", "파이프라인 점검 완료 · 통과 조건 6 / 6 충족")
    out = log(s, {}, None)
    kinds = [r["kind"] for r in out["rows"]]
    assert "검증" in kinds and "변경 요청" in kinds and "승인" in kinds
    assert [r["at"] for r in out["rows"]] == sorted((r["at"] for r in out["rows"]), reverse=True)
    filed = [r["kind"] for r in out["rows"] if r.get("change")]
    assert filed.index("승인") < filed.index("변경 요청")  # written in the same second: the later one first
    change = next(r for r in out["rows"] if r["kind"] == "변경 요청")
    assert change["change"] and change["versions"][0]["version"]
    assert len(log(s, {"limit": 1}, None)["rows"]) == 1


def test_the_log_keeps_the_drafts_made_beside_the_measurements(s):
    from ontlas.web.areas.home import _jobs

    log = routes().find("GET", "qa/decisions")
    s.event("draft", "반품 가능 여부: 지난 12건으로 규칙 3개를 만들었습니다.")
    s.event("pipeline", "가상 쇼핑몰(으)로 전환")  # what the session did besides is not a decision
    _jobs(s)[:0] = [{"at": "2026-11-18T09:10", "by": "편집자", "kind": "rules", "label": "반품 규칙", "scope": "반품정책서",
                     "made": {"rules": 9, "all": 9, "excluded": 0}},
                    {"at": "2026-11-18T09:12", "by": "편집자", "kind": "rules", "error": "모델 응답 없음", "made": {"all": 0}}]
    rows = log(s, {}, None)["rows"]
    said = {(r["kind"], r["text"], r.get("source", "")) for r in rows}
    assert ("AI 초안", "반품 가능 여부: 지난 12건으로 규칙 3개를 만들었습니다.", "") in said
    assert ("AI 초안", "반품 규칙 · 규칙 초안 9개 생성", "반품정책서") in said  # what it was made from stands beside it
    assert len(rows) == 2  # neither the switch nor the making that failed


def test_approvals_say_how_long_the_oldest_change_request_has_waited(s):
    from datetime import datetime, timedelta

    wait = routes().find("GET", "qa/approvals")
    assert wait(s, {}, None) == {"changes": 0, "oldest_at": "", "waited": 0}
    s.studio.changes.self_approve = False  # a person approves it: the request waits
    s.manage_edit("update_question", {"id": "Q2", "holdout": True})
    s.manage_propose()
    cr = next(iter(s.studio.changes.requests.values()))
    cr.at = (datetime.now() - timedelta(days=3, hours=2)).isoformat(timespec="seconds")
    out = wait(s, {}, None)
    assert out["changes"] == 1 and out["oldest_at"] == cr.at and 3 * 86400 <= out["waited"] < 4 * 86400


def test_a_value_question_is_about_the_entity_its_query_answers_about(s):
    from ontlas.model import RegisteredQuery
    from ontlas.web.areas.qa import _answers_about

    asks = routes().find("GET", "qa/objects")(s, {}, None)["queries"]
    assert set(asks) == set(s.studio.onto.queries)
    assert asks["ordersOfCustomer"] == "Order"  # the orders a customer placed: it answers about Order, not Customer
    q = lambda r: RegisteredQuery(name="x", query={"match": {"c": "Customer", "p": "Payment"}, "return": r})  # noqa: E731
    assert _answers_about(q([{"count": "p", "as": "n"}])) == "Payment"
    assert _answers_about(q([{"sum": "p.amount", "as": "total"}])) == "Payment"
    assert _answers_about(q([{"col": "c.name", "as": "who"}])) == "Customer"
    assert _answers_about(q([])) == "Customer"
    assert _answers_about(RegisteredQuery(name="y", query={})) == ""


def test_every_table_the_quality_screens_read_is_declared_in_the_page():
    """A table of words read by name and declared nowhere stops the screen that reads it (검증 drew nothing once a
    wrong answer came in, when the table of diagnoses it read had been taken out of the page)."""
    import re

    static = Path(__file__).resolve().parent.parent / "src" / "ontlas" / "web" / "static"
    mine = (static / "v2" / "60-qa.js").read_text(encoding="utf-8")
    page = "".join(p.read_text(encoding="utf-8") for p in [static / "app.js", *sorted((static / "v2").glob("*.js"))])
    declared = set(re.findall(r"\b(?:const|let|function)\s+([A-Z][A-Z0-9_]*)\b", page)) | {"JSON"}
    read = set(re.findall(r"(?<![\w$.'\"-])([A-Z][A-Z0-9_]{2,})(?=\[|\.)", re.sub(r"//[^\n]*", "", mine)))
    assert read and not read - declared, sorted(read - declared)


def test_evidence_says_how_many_entities_of_an_object_each_document_names(s):
    ev = routes().find("GET", "qa/evidence")(s, {}, None)
    onto = s.studio.onto
    assert ev["connected"] is True and ev["entities"] == len(onto.objects)
    names = {d["name"] for d in ev["documents"]}
    assert "반품정책서" in names and all(d["state_label"] for d in ev["documents"])
    by = {o["name"]: o for o in ev["objects"]}
    assert set(by) == {a for a in onto.areas if any(t.area == a for t in onto.objects.values())}
    for o in ev["objects"]:
        assert set(o["cells"]) == names
        for c in o["cells"].values():
            assert c["state"] == ("all" if c["count"] == o["entities"] else "some" if c["count"] else "none")
        assert o["source"] in ("all", "some", "none") and o["bound"] <= o["entities"]
    named = by["Customer"]["cells"]["반품정책서"]
    assert named["count"] == 1 and named["entities"] == ["고객"]  # the return policy says 고객
    assert by["Order"]["cells"]["반품정책서"]["state"] == "some"  # 주문 and 주문상품, not the payment screen's record
    assert all(g["kind"] in ("object", "rule") and g["who"] and g["what"] for g in ev["gaps"])
    assert all(u["why"] in ("키 미정", "소스 테이블 미정") for u in ev["unbound"])
