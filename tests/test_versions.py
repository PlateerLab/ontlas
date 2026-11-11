"""Every change kept as a version of the space with its history, the regression a change is reviewed with (the questions
that newly fail or newly pass, the shares on either side, the pass conditions that stop or start passing), and the home's
overview of the space: maturity, its four parts, the Objects and the milestones its studio file names."""
import copy
import json
import threading
import urllib.request
from datetime import date
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "examples" / "library" / "studio.yaml"
VIP = "VIP 고객은 배송 완료 후 14일까지 반품할 수 있습니다"  # what question A1 expects of the overlay's rule

pytest.importorskip("yaml")
pytest.importorskip("rdflib")


@pytest.fixture
def st():
    from ontlas.config import load_studio
    from ontlas.library import OverlayLibrary

    s = load_studio(STUDIO)
    s.library = OverlayLibrary(s.library, [])  # approvals are kept in memory, the example folder is never written
    return s


@pytest.fixture
def session():
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    return StudioSession(load_studio(STUDIO))


def _overlay(library, version: str, reason: str = VIP, question: dict | None = None):
    """The customer overlay at another version, its VIP rule giving `reason`, with one more question if given."""
    from ontlas.modules import Module

    d = copy.deepcopy(library.get("acme-overlay", "1.0.0").to_dict())
    d["version"] = version
    d["extend"]["decisions"]["returnEligibility"]["rules_prepend"][0]["then"]["reason"] = reason
    if question:
        d["questions"] = [*d["questions"], question]
    return Module.from_dict(d)


def _text(module) -> str:
    """A module, or a module's dict, as the text a page sends."""
    import yaml

    return yaml.safe_dump(module if isinstance(module, dict) else module.to_dict(), allow_unicode=True, sort_keys=False)


# ---- the regression a change is reviewed with -----------------------------------------------------------------------

def test_a_change_that_breaks_a_question_lists_it_as_newly_failing(st):
    cr = st.changes.propose(_overlay(st.library, "1.1.0", "VIP 고객 반품 기간 연장"), by="kim")
    reg = cr.review["regression"]
    assert reg["measured"] and reg["questions"] == {"before": 12, "after": 12, "measured": 12, "unmeasured": 0}
    assert [q["id"] for q in reg["newly_failing"]] == ["A1"]
    q = reg["newly_failing"][0]
    assert q["text"].startswith("VIP 고객의 I1001") and q["was"] == "passed" and q["error"] == ""
    assert q["expected"] == {"eligible": True, "reason": VIP} and q["got"]["reason"] == "VIP 고객 반품 기간 연장"
    assert reg["accuracy"]["before"] == 1.0 and reg["accuracy"]["after"] == pytest.approx(11 / 12)
    assert reg["accuracy"]["change"] == pytest.approx(-0.0833) and reg["grounded"]["change"] == 0
    assert reg["agreement"] == {"before": 0.9, "after": 0.9, "change": 0.0}  # past decisions are decided as before
    assert reg["newly_passing"] == [] and reg["unmeasured"] == [] and reg["worse"] and not reg["better"]
    assert reg["gates_failing"] == [] and cr.review["passed"]  # 11 of 12 still meets the 0.9 the studio asks
    assert cr.review["from_version"] == "1.0.0"


def test_a_condition_the_change_stops_meeting_is_named_with_both_values(st):
    st.settings["flow"]["gates"]["check"]["min_accuracy"] = 0.95
    cr = st.changes.propose(_overlay(st.library, "1.1.0", "VIP 고객 반품 기간 연장"), by="kim")
    reg = cr.review["regression"]
    assert [(g["stage"], g["condition"], g["was"]) for g in reg["gates_failing"]] == [("check", "min_accuracy", "passed")]
    g = reg["gates_failing"][0]
    assert g["limit"] == 0.95 and g["before"] == 1.0 and g["after"] == pytest.approx(11 / 12)
    assert not cr.review["passed"]


def test_a_change_that_fixes_a_question_lists_it_as_newly_passing(st):
    broke = st.changes.propose(_overlay(st.library, "1.1.0", "VIP 고객 반품 기간 연장"), by="kim")
    st.changes.approve(broke.id, by="lee")
    assert broke.decided_at and broke.decided_by == "lee"
    st.settings["flow"]["gates"]["check"]["min_accuracy"] = 0.95  # the studio now misses it: 11 of 12
    fix = st.changes.propose(_overlay(st.library, "1.2.0"), by="kim")
    reg = fix.review["regression"]
    assert [q["id"] for q in reg["newly_passing"]] == ["A1"] and reg["newly_failing"] == []
    assert reg["newly_passing"][0]["got"]["reason"] == VIP
    assert reg["accuracy"]["after"] == 1.0 and reg["accuracy"]["change"] > 0 and reg["better"] and not reg["worse"]
    assert [(g["stage"], g["condition"]) for g in reg["gates_passing"]] == [("check", "min_accuracy")]
    assert fix.review["from_version"] == "1.1.0" and fix.review["passed"]


def test_a_question_the_change_adds_and_fails_is_new_not_a_regression_of_an_old_one(st):
    wrong = {"id": "A2", "text": "I1003 은 VIP 기간으로 반품되나요?", "decision": "returnEligibility", "key": "I1003",
             "expect": {"eligible": True}}
    reg = st.changes.propose(_overlay(st.library, "1.1.0", question=wrong), by="kim").review["regression"]
    assert [(q["id"], q["was"]) for q in reg["newly_failing"]] == [("A2", "absent")]
    assert reg["questions"]["before"] == 12 and reg["questions"]["after"] == 13


def test_without_a_source_a_question_that_reads_rows_is_not_measured_not_failed(tmp_path):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    from .test_no_source import _no_backend

    s = StudioSession(load_studio(_no_backend(tmp_path)))
    d = copy.deepcopy(s.studio.library.get("commerce").to_dict())
    d["version"] = "1.1.0"
    rule = next(r for r in d["decisions"]["returnEligibility"]["rules"] if r["id"] == "in-window")
    rule["then"]["eligible"] = False  # Q2 would fail, if it could be asked
    change = s.propose_module(_text(d))["change"]
    reg = change["regression"]
    assert "Q2" in reg["unmeasured"] and reg["newly_failing"] == [] and not reg["measured"] and not reg["worse"]
    assert reg["accuracy"] is None and reg["note"] and "측정 대상 아닌 질문" in reg["summary"]
    assert change["passed"]


def test_the_trial_and_the_change_detail_carry_the_regression(session):
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    trial = session.manage_trial()
    assert trial["regression"]["measured"] and trial["regression"]["newly_failing"] == []
    assert trial["regression"]["summary"] == "달라진 결과 없음"
    session.manage_discard()
    session.studio.settings["flow"]["gates"]["check"]["min_accuracy"] = 0.95
    change = session.propose_module(_text(_overlay(session.studio.library, "1.1.0", "VIP 고객 반품 기간 연장")))["change"]
    detail = session.change_detail(change["id"])
    reg = detail["regression"]
    assert [q["id"] for q in reg["newly_failing"]] == ["A1"] and reg["summary"].startswith("새로 틀리는 질문 1개")
    assert reg["gates_failing"][0]["label"] == "검증 질문 정답률 최소" and reg["gates_failing"][0]["stage_label"] == "검증"
    assert detail["from_version"] == "1.0.0" and detail["decided_at"] == ""
    json.dumps(detail)


# ---- every version of the space -------------------------------------------------------------------------------------

def test_every_applied_change_is_a_version_of_the_space_with_its_history(session):
    v = session.versions()
    assert v["current"]["number"] == 1 and v["current"]["label"] == "판본 1" and v["history"] == [] and v["pending"] == []
    first_key = v["current"]["key"]
    assert {m["name"]: m["version"] for m in v["current"]["modules"]}["acme-overlay"] == "1.0.0"
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    out = session.manage_propose()
    assert out["ok"] and out["change"]["status"] == "approved" and out["change"]["decided_at"]
    v = session.versions()
    assert v["current"]["number"] == 2 and v["current"]["change"] == out["change"]["id"] and v["current"]["key"] != first_key
    row = v["history"][0]
    assert (row["module"], row["from"], row["status"], row["applied"], row["number"]) == ("workspace", "", "approved", True, 2)
    assert row["requested_by"] == row["decided_by"] == "방문자" and row["decided_at"] == v["current"]["at"]
    assert row["summary"] == "주문서 변경" and row["counts"] == {"added": 0, "changed": 1, "removed": 0}
    assert row["regression"]["summary"] == "달라진 결과 없음"
    ws = next(r for r in v["library"] if r["name"] == "workspace")
    assert ws["applied"] == row["to"] and ws["versions"][0] == {"version": row["to"], "applied": True, "on_disk": False,
                                                                 "change": row["id"]}
    food = next(r for r in v["library"] if r["name"] == "food")
    assert food["applied"] == "" and food["versions"] == [{"version": "1.0.0", "applied": False, "on_disk": True, "change": ""}]

    pending = session.propose_module(_text(_overlay(session.studio.library, "1.1.0", "VIP 고객 반품 기간 연장")))["change"]
    v = session.versions()
    assert [p["id"] for p in v["pending"]] == [pending["id"]] and v["pending"][0]["from"] == "1.0.0"
    assert v["pending"][0]["to"] == "1.1.0" and v["pending"][0]["number"] is None
    assert v["pending"][0]["regression"]["newly_failing"][0]["id"] == "A1"
    assert session.decide_change(pending["id"], False, "문구 확인 필요")["ok"]
    v = session.versions()
    assert v["pending"] == [] and v["current"]["number"] == 2  # a rejected change makes no version
    rejected = v["history"][0]
    assert (rejected["id"], rejected["status"], rejected["applied"], rejected["number"]) == (pending["id"], "rejected", False, None)
    assert rejected["reason"] == "문구 확인 필요" and rejected["decided_at"] and rejected["summary"] == "반품 가능 여부 · vip-window 변경"
    json.dumps(v)


def test_decision_times_outlive_a_restart_and_older_records_take_theirs_from_the_audit(tmp_path):
    from ontlas.config import load_studio
    from ontlas.library import OverlayLibrary
    from ontlas.web.api import StudioSession

    journal = tmp_path / "journal.jsonl"
    st = load_studio(STUDIO)
    st.library = OverlayLibrary(st.library, [])
    st.keep_journal(journal)
    cr = st.changes.propose(_overlay(st.library, "1.1.0", "VIP 고객 반품 기간 연장"), by="kim")
    st.changes.reject(cr.id, by="lee", reason="문구 확인 필요")
    again = load_studio(STUDIO)
    again.keep_journal(journal)
    kept = again.changes.requests[cr.id]
    assert kept.decided_at == cr.decided_at and kept.review["regression"]["newly_failing"][0]["id"] == "A1"
    # a journal written before decisions kept their time: the time comes from the audit line
    lines = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines()]
    for x in lines:
        (x.get("change") or {}).pop("decided_at", None)
    journal.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines), encoding="utf-8")
    old = load_studio(STUDIO)
    old.keep_journal(journal)
    assert old.changes.requests[cr.id].decided_at == ""
    row = StudioSession(old).versions()["history"][0]
    assert row["decided_at"] == cr.decided_at and row["decided_by"] == "lee" and row["regression"]["worse"]


# ---- the home's overview ----------------------------------------------------------------------------------------------

def test_the_overview_reads_the_last_measurement_and_says_when_there_is_none(session):
    ov = session.overview()
    assert [c["id"] for c in ov["components"]] == ["semantic", "ontology", "binding", "qa"]
    qa, binding = ov["components"][3], ov["components"][2]
    assert (qa["status"], qa["status_label"], qa["accuracy"]) == ("unmeasured", "미측정", None)
    assert (binding["status"], binding["status_label"]) == ("unmeasured", "대조 전") and binding["source"]["connected"]
    levels = [x["entities"] for x in ov["maturity"]["levels"]]
    assert sum(levels) == ov["maturity"]["entities"] == len(session.studio.onto.objects) and levels[3] == 0
    assert not ov["maturity"]["checked"]  # L3 asks for a database check of this definition, and none was taken
    session.flow()
    ov = session.overview()
    qa, binding = ov["components"][3], ov["components"][2]
    assert (qa["status"], qa["accuracy"], qa["counts"]["questions"], qa["gates"]["met"]) == ("ok", 1.0, 12, qa["gates"]["all"])
    assert (binding["status"], binding["check"]) == ("ok", {"errors": 0, "warnings": 0})
    levels = [x["entities"] for x in ov["maturity"]["levels"]]
    bound = sum(1 for t in session.studio.onto.objects.values() if t.table)
    assert ov["maturity"]["checked"] and levels[3] == bound and levels[1] == len(session.studio.onto.objects) - bound
    semantic = ov["components"][0]
    assert semantic["counts"]["decisions"] == 2 and semantic["status"] == "ok"
    assert {r["kind"]: r["rules"] for r in semantic["by_kind"]} == {"domain": 8, "customer": 1}  # the VIP rule is the overlay's
    session.manage_edit("update_object", {"name": "Order", "label": "주문서"})
    session.manage_propose()
    qa = session.overview()["components"][3]
    assert qa["stale"] and qa["status_label"] == "다시 측정 필요"  # the definition moved since the last measurement


def test_the_object_map_files_each_entity_with_its_level_and_reads_a_tier_where_there_is_one(session):
    session.studio.onto.areas["Order"].tier = "업무"  # what an area may carry; read whether or not the model has it
    ov = session.overview()
    order = next(x for x in ov["objects"] if x["name"] == "Order")
    assert order["label"] == "주문" and order["tier"] == "업무" and order["count"] == len(order["entities"]) == sum(order["levels"])
    assert {e["name"] for e in order["entities"]} == {"Order", "OrderItem", "CheckoutRecord"}
    assert order["level"] == min(e["level"] for e in order["entities"]) and order["level_label"].startswith("L")
    loose = ov["objects"][-1]
    assert loose["name"] == "" and loose["label"] == "미분류" and {e["name"] for e in loose["entities"]} == {"Party", "Agreement"}
    assert ov["components"][1]["counts"]["unfiled"] == 2 and ov["components"][1]["counts"]["objects"] == len(session.studio.onto.areas)
    assert set(ov["todo"]) >= {"assigned", "mine", "all", "kinds"} and ov["version"]["label"] == "판본 1"
    assert ov["milestones"] == []  # the example names none


def test_milestones_come_from_the_studio_file_in_date_order(tmp_path):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    from .test_no_source import _no_backend

    tail = ("milestones:\n"
            "  - {date: 2026-12-20, label: 운영 오픈}\n"
            "  - {date: 2026-11-15, label: 검증 완료, detail: 검증 질문 정답률 0.9 이상}\n"
            "  - {date: 2026-10-01, label: 착수}\n"
            "  - {label: 운영 이관}\n"
            "  - {date: 2026-11-01}\n")
    s = StudioSession(load_studio(_no_backend(tmp_path, tail)))  # the studio's clock reads 2026-10-30
    got = s.overview()["milestones"]
    assert [(m["label"], m["state"], m["days"]) for m in got] == [
        ("착수", "past", -29), ("검증 완료", "next", 16), ("운영 오픈", "later", 51), ("운영 이관", "later", None)]
    assert got[1]["date"] == "2026-11-15" and got[1]["detail"] == "검증 질문 정답률 0.9 이상" and got[3]["date"] == ""
    s.studio.settings["milestones"] = [{"date": date(2026, 10, 30), "label": "오늘"}, "not a milestone"]
    assert [(m["label"], m["state"], m["days"]) for m in s.overview()["milestones"]] == [("오늘", "next", 0)]
    binding = s.overview()["components"][2]
    assert (binding["status"], binding["source"]["connected"]) == ("empty", False)  # nothing bound, nothing to connect


def test_the_page_routes_answer(tmp_path):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession
    from ontlas.web.server import RateLimit, Sessions, make_handler

    from .test_no_source import _no_backend

    cfg = _no_backend(tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Sessions(lambda: StudioSession(load_studio(cfg)), spare=0),
                                                               ask_limit=RateLimit(5), quiet=True))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        for path, keys in (("/api/versions", {"current", "pending", "history", "library", "writes_folder"}),
                           ("/api/overview", {"maturity", "components", "objects", "todo", "milestones", "version"})):
            with urllib.request.urlopen(base + path, timeout=60) as r:
                body = json.loads(r.read().decode("utf-8"))
            assert r.status == 200 and set(body) == keys, path
    finally:
        httpd.shutdown()
        httpd.server_close()
