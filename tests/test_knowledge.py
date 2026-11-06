from pathlib import Path

import pytest

from xgen_space.decide.cells import parse_test
from xgen_space.decide.words import cell_of, cell_parts, cell_words, input_label, rule_sentence, verdict
from xgen_space.knowledge import OmniFuseRetriever, WordsRetriever, build, default_retriever, entries, links_between
from xgen_space.tools import StudioTools

SHOP = Path(__file__).resolve().parents[1] / "examples" / "library" / "studio.yaml"


@pytest.fixture
def shop():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio

    return load_studio(SHOP)


def test_a_decision_table_reads_in_peoples_words(shop):
    t = shop.onto.decisions["returnEligibility"]
    assert input_label(shop.onto, t, "days_since_delivery").endswith("경과일")
    assert cell_words("<= 14", unit="일") == "14일 이하"
    assert cell_words('"VIP"') == "VIP"
    assert cell_words("true") == "예"
    assert cell_words('!= "NORMAL"') == "NORMAL 제외"
    assert cell_words("null") == "값 없음"
    assert cell_words("not a test at all") == "not a test at all"  # what cannot be read stands as written
    vip = next(r for r in t.rules if r.id == "vip-window")
    said = rule_sentence(shop.onto, t, vip)
    assert "14일 이하" in said and "VIP" in said and "days_since" not in said


@pytest.mark.parametrize("cell", ["<= 14", '"VIP"', "true", '!= "NORMAL"', "null", "not null", '>= 5', 'in ["A", "B"]', 'not in ["A"]', "<= @window"])
def test_a_cell_comes_back_the_same_through_a_form(cell):
    part = cell_parts(cell)
    kind = "integer" if any(c.isdigit() for c in cell) else ("boolean" if cell == "true" else "string")
    again = cell_of(part["op"], part["value"], kind)
    assert parse_test(again, {"window": 7}) == parse_test(cell, {"window": 7})


def test_a_verdict_says_what_a_decision_gave(shop):
    ret, fee = shop.onto.decisions["returnEligibility"], shop.onto.decisions["shippingFee"]
    assert verdict(ret, {"eligible": True}) == ("가능", True)
    assert verdict(ret, {"eligible": False}) == ("불가", False)
    assert verdict(fee, {"fee": 3000}) == ("3,000", True)
    assert verdict(fee, {"fee": 0}) == ("0", True)  # free is an amount, not a refusal


def test_definitions_rules_and_passages_are_one_index(shop):
    items = entries(shop.onto, shop.space)
    kinds = {e.kind for e in items}
    assert {"object", "rule", "query", "document"} <= kinds
    rule = next(e for e in items if e.id == "rule:returnEligibility.in-window")
    assert "7일 이하" in rule.text and "object:OrderItem" in rule.mentions
    assert any(s == rule.id and p == "출처" for s, p, _ in links_between(shop.onto, items))  # the clause it cites


def test_the_words_retriever_needs_nothing_beyond_the_space(shop):
    know = build(shop.onto, shop.space, kind="words")
    assert know.retriever.kind == "words" and isinstance(know.retriever, WordsRetriever)
    assert know.find("쿠폰 두 장을 같이 쓸 수 있나요", 3, ("document",))[0]["document"] == "쿠폰약관"


def test_omnifuse_finds_the_same_entries_with_the_graph_between_them(shop):
    pytest.importorskip("omnifuse")
    know = build(shop.onto, shop.space, kind="omnifuse")
    assert isinstance(know.retriever, OmniFuseRetriever) and default_retriever() == "omnifuse"
    top = know.find("쿠폰 두 장을 같이 쓸 수 있나요", 5, ("document",))
    assert top and top[0]["document"] == "쿠폰약관"
    assert all(" → 언급 → " not in r for r in know.relations("반품 기간"))
    assert know.describe()["by_kind"]["규칙"] >= 6


@pytest.mark.parametrize("kind", ["words", "omnifuse"])
def test_one_question_runs_the_table_when_it_names_a_key(shop, kind):
    if kind == "omnifuse":
        pytest.importorskip("omnifuse")
    shop.space.retriever = kind
    a = StudioTools(shop).answer_question("주문상품 I1001 반품 되나요?")
    assert a["route"] == "decision" and a["engine"] == kind
    d = a["decisions"][0]
    assert d["verdict"] == "가능" and d["rules"][0]["id"] == "vip-window" and d["evidence"]
    assert a["sources"][0]["id"] == "rule:returnEligibility.vip-window"  # the rule that applied comes first
    assert not any(s["kind"] == "rule" and s["id"] != a["sources"][0]["id"] for s in a["sources"])  # rules that did not apply are not grounds


def test_an_amount_reads_as_an_amount(shop):
    a = StudioTools(shop).answer_question("주문 O16 배송비 알려 주세요")
    assert a["route"] == "decision" and a["decisions"][0]["verdict"] == "3,000" and "불가" not in a["answer"]


def test_a_key_alone_reads_the_record_under_the_role(shop):
    a = StudioTools(shop).answer_question("주문상품 I1003 정보 알려 줘")
    assert a["route"] == "record" and a["record"]["key"] == "I1003"
    assert any(v["label"] == "주문상품 상태" for v in a["record"]["values"])
    with pytest.raises(PermissionError):
        StudioTools(shop, role="customer_agent", principal={"customer_id": "C001"}).record("OrderItem", "I2074")


def test_a_registered_query_runs_by_its_name_and_a_condition_makes_it_another_question(shop):
    a = StudioTools(shop).answer_question("카테고리별 매출")
    assert a["route"] == "query" and a["query"]["name"] == "revenueByCategory" and a["query"]["rows"]
    b = StudioTools(shop).answer_question("취소된 주문을 빼고 카테고리별 매출 합계를 구해 주세요")
    assert b["route"] != "query" and b["needs_model"]


def test_a_question_with_no_key_goes_to_rules_and_passages(shop):
    a = StudioTools(shop).answer_question("쿠폰 두 장을 같이 쓸 수 있나요")
    assert a["route"] == "documents" and a["needs_model"] and a["sources"][0]["document"] == "쿠폰약관"


def test_an_empty_question_is_refused(shop):
    with pytest.raises(ValueError):
        StudioTools(shop).answer_question("   ")


def test_a_role_answers_only_inside_its_rows(shop):
    agent = StudioTools(shop, role="customer_agent", principal={"customer_id": "C001"})
    assert agent.answer_question("주문상품 I1001 반품 되나요?")["route"] == "decision"
    with pytest.raises(PermissionError):
        agent.answer_question("주문상품 I2074 반품 되나요?")


def test_an_agent_reads_what_a_question_is_about_not_the_whole_ontology(shop):
    t = StudioTools(shop)
    found = t.find_definitions("반품 기간", 4)["found"]
    assert 0 < len(found) <= 4 and all(f["kind"] in ("object", "rule", "query", "action") for f in found)
    one = t.describe_object("OrderItem")
    assert "item_status" in str(one["object"]) and one["links"] and "returnEligibility" in one["decisions"]
    with pytest.raises(KeyError):
        t.describe_object("Nothing")
    agent = StudioTools(shop, role="support_agent")
    assert all(f["element"].split(":", 1)[1] in {*agent.describe()["objects"], *agent.describe()["decisions"], *agent.describe()["queries"], *agent.describe()["actions"]}
               for f in agent.find_definitions("주문", 10)["found"])
