"""What the home, the search screen and the AI draft screen ask: the home's summary judged from what is here, one list
of everything a question touches, and the record of the drafts made from the AI draft screen."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from ontlas.config import load_studio
from ontlas.web import routes
from ontlas.web.api import StudioSession
from ontlas.web.team import NEEDS

pytest.importorskip("yaml")
pytest.importorskip("rdflib")  # the example studio projects a graph

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
FILES = ROOT / "examples" / "files"


@pytest.fixture()
def session():
    routes.load()
    return StudioSession(load_studio(SHOP))


def get(s, route, **a):
    return routes.find("GET", route)(s, a, None)


def post(s, route, **a):
    return routes.find("POST", route)(s, a, None)


def upload(s, *names):
    for n in names:
        s.catalog_upload(n, (FILES / n).read_bytes())


def test_the_summary_is_the_overview_with_the_homes_own_facts_beside_it(session):
    out = get(session, "home/summary")
    for key in ("maturity", "components", "objects", "version", "rules", "materials", "waiting", "changes", "steps", "name"):
        assert key in out, key
    assert out["name"]
    r = out["rules"]
    assert r["cards"] > 0 and sum(r["layers"].values()) == r["cards"]
    assert set(r["layers"]) <= {"axiom", "custom", "standard"}
    assert [x["id"] for x in out["steps"]] == ["upload", "drafts", "questions", "version", "agents", "source"]
    assert all(x["state"] in ("done", "doing", "todo", "optional") for x in out["steps"])


def test_the_steps_are_judged_from_what_is_here(session):
    steps = {x["id"]: x for x in get(session, "home/summary")["steps"]}
    assert steps["upload"]["state"] == "todo" and steps["upload"]["files"] == 0
    assert steps["version"]["state"] == "done" and steps["questions"]["state"] == "done"
    assert steps["source"]["state"] == "done"  # the example studio reads its own database
    assert steps["agents"]["state"] == "todo"  # no token was given, so the API for other platforms is off
    upload(session, "주문.csv", "주문상품.csv")
    steps = {x["id"]: x for x in get(session, "home/summary")["steps"]}
    assert steps["upload"]["state"] == "done" and steps["upload"]["files"] == 2 and steps["upload"]["data"] == 2


def test_a_draft_made_from_files_waits_for_review_until_it_is_applied_or_dropped(session):
    before = get(session, "home/summary")["waiting"]
    assert before["concepts"] == 0 and before["draft"] is None
    upload(session, "주문.csv", "주문상품.csv")
    session.make_draft("주문 초안")
    out = get(session, "home/summary")
    d = session.pending[0]
    assert out["waiting"]["concepts"] == len(d.objects) + len(d.links) > 0
    assert out["waiting"]["draft"] == {"label": "주문 초안", "objects": len(d.objects), "links": len(d.links)}
    assert out["waiting"]["all"] == before["all"] + out["waiting"]["concepts"]
    assert next(x for x in out["steps"] if x["id"] == "drafts")["state"] == "doing"
    session.pending = None
    assert get(session, "home/summary")["waiting"]["concepts"] == 0


def test_rule_cards_not_yet_approved_wait_for_review(session):
    out = get(session, "home/summary")
    cards = session.semantic_state()["cards"]
    assert out["waiting"]["rules"] == sum(1 for c in cards if c["status"] in ("draft", "review"))
    assert out["rules"]["legal"] == sum(1 for c in cards if c["legal_review"] == "pending")


def test_find_lists_everything_a_question_touches_with_what_each_is(session):
    out = get(session, "home/find", q="  반품   기간 ")
    assert out["q"] == "반품 기간" and out["total"] == len(out["found"]) > 0
    assert sum(out["counts"].values()) == out["total"]
    groups = {x["group"] for x in out["found"]}
    assert "rule" in groups and "doc" in groups
    for x in out["found"]:
        assert x["title"] and x["word"] and x["go"]
        assert x["group"] == {"object": "def", "query": "def", "action": "def", "rule": "rule", "document": "doc", "term": "term"}[x["kind"]]
    rule = next(x for x in out["found"] if x["kind"] == "rule")
    assert rule["id"].startswith("rule:") and "." in rule["id"] and rule["word"] == "규칙" and rule["go"] == "semrules"
    doc = next(x for x in out["found"] if x["kind"] == "document")
    assert "›" in doc["title"] and doc["word"] == "자료"


def test_find_names_a_term_the_lexicon_holds(session):
    terms = session.lexicon_state()["rows"]
    word = terms[0]["term"]
    out = get(session, "home/find", q=word)
    hit = [x for x in out["found"] if x["kind"] == "term"]
    assert hit and hit[0]["title"] == word and hit[0]["go"] == "lexicon"
    assert out["counts"]["term"] == len(hit)


def test_find_without_words_says_so(session):
    with pytest.raises(ValueError):
        get(session, "home/find", q="   ")


def test_the_ai_screen_reads_what_a_draft_can_be_made_from(session):
    out = get(session, "home/ai")
    assert out["model"] == {"on": False, "kind": ""} and out["composed"] is True and out["running"] is False
    assert out["materials"]["files"] == 0 and out["tables"] == 0 and out["documents"] == []
    assert out["existing"]["entities"] == len(session.studio.onto.objects) and out["existing"]["rules"] > 0
    assert out["packs"] and all(p["label"] and p["version"] for p in out["packs"])
    assert out["targets"] and out["jobs"] == [] and out["month"] == {"jobs": 0, "made": 0, "excluded": 0}
    upload(session, "주문.csv")
    session.catalog_upload("교환정책서.md", (ROOT / "examples" / "policies" / "교환정책서.md").read_bytes())
    out = get(session, "home/ai")
    assert out["materials"]["data"] == 1 and out["materials"]["document"] == 1 and out["tables"] == 1
    assert [d["name"] for d in out["documents"]] and out["documents"][0]["sections"] >= 1


def test_a_draft_made_here_is_recorded_from_what_the_studio_holds(session):
    assert NEEDS["home/ai/job"] == "editor"
    with pytest.raises(ValueError):
        post(session, "home/ai/job", kind="concepts")
    upload(session, "주문.csv", "주문상품.csv")
    session.make_draft("주문 초안")
    d = session.pending[0]
    out = post(session, "home/ai/job", kind="concepts")
    job = out["jobs"][0]
    assert job["kind"] == "concepts" and job["label"] == "주문 초안" and job["files"] == 2
    assert job["made"] == {"objects": len(d.objects), "links": len(d.links), "all": len(d.objects) + len(d.links),
                           "excluded": len(d.skipped)}
    assert (job["state"], job["state_label"]) == ("waiting", "검토 대기")
    assert out["month"] == {"jobs": 1, "made": job["made"]["all"], "excluded": job["made"]["excluded"]}
    session.pending = None  # applied or dropped: it no longer waits
    assert get(session, "home/ai")["jobs"][0]["state"] == "done"


def test_a_rule_draft_is_recorded_with_what_its_check_found_and_follows_its_change_request(session):
    with pytest.raises(ValueError):
        post(session, "home/ai/job", kind="rules")
    session._draft = {"id": "j1", "out": {"ok": True, "label": "교환 가능 여부", "module": "policy-exchange", "decision": "exchange",
                                         "target": "OrderItem", "rules": [{"id": "a"}, {"id": "b"}], "issues": ["rule b has no cite"]}}
    out = post(session, "home/ai/job", kind="rules", scope="교환정책서 › 제2조")
    job = out["jobs"][0]
    assert job["kind"] == "rules" and job["scope"] == "교환정책서 › 제2조" and job["module"] == "policy-exchange"
    assert job["made"] == {"rules": 2, "all": 2, "excluded": 1} and job["state"] == "waiting"
    requests = session.studio.changes.requests
    requests["T1"] = SimpleNamespace(module="policy-exchange", status="pending")
    try:
        assert get(session, "home/ai")["jobs"][0]["state"] == "filed"
        requests["T1"].status = "approved"
        assert get(session, "home/ai")["jobs"][0]["state_label"] == "배포됨"
    finally:
        del requests["T1"]


def test_a_kind_that_is_neither_draft_is_refused(session):
    with pytest.raises(ValueError):
        post(session, "home/ai/job", kind="terms")
