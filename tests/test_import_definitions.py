"""Definitions drafted outside the studio (tables kept as YAML) become a library's modules."""
import pytest

from ontlas.exchange.definitions import from_definitions
from ontlas.library import Library
from ontlas.modules import compose
from ontlas.semantic import card_spec

DRAFT = {
    "meta": {"title": "가게 표준 초안", "notation": {"접두어 없음": "표준 (https://schema.org/)", "shop:": "확장"}},
    "objects": [
        {"label_ko": "주문", "class": "Order", "vocabulary": "schema.org", "definition": "손님이 물건을 사려고 만든 거래",
         "lifecycle": "접수 → 결제 → 배송 → 완료", "entities": [{"class": "Order"}, {"class": "shop:OrderLine"}]},
        {"label_ko": "손님", "class": "shop:Patron", "vocabulary": "shop", "definition": "가게에서 사는 사람", "entities": [{"class": "Person"}]},
    ],
    "entities": [
        {"name": "Order", "class": "Order", "label_ko": "주문", "vocabulary": "schema.org", "definition": "한 번의 결제로 묶인 거래", "properties": [
            {"name": "orderNumber", "label_ko": "주문번호", "kind": "값", "range": "Text", "cardinality": "1", "required": True, "vocabulary": "schema.org"},
            {"name": "orderStatus", "label_ko": "주문 상태", "kind": "열거형", "range": "OrderStatus", "cardinality": "1", "required": True},
            {"name": "shop:giftWrap", "label_ko": "선물 포장", "kind": "값", "range": "Boolean", "cardinality": "0..1", "vocabulary": "shop"},
            {"name": "validFrom", "label_ko": "받은 때", "kind": "값", "range": "DateTime", "cardinality": "0..1"},
            {"name": "customer", "label_ko": "주문한 손님", "kind": "관계", "range": "Person", "cardinality": "1"},
            {"name": "orderedItem", "label_ko": "주문 줄", "kind": "관계", "range": "shop:OrderLine", "cardinality": "1..n"}]},
        {"name": "OrderLine", "class": "shop:OrderLine", "label_ko": "주문 줄", "vocabulary": "shop", "properties": [
            {"name": "shop:quantity", "label_ko": "수량", "kind": "값", "range": "Integer", "cardinality": "1", "required": True},
            {"name": "validFrom", "label_ko": "담은 날", "kind": "값", "range": "Date", "cardinality": "0..1"}]},
        {"name": "Person", "class": "Person", "label_ko": "손님", "vocabulary": "schema.org", "properties": [
            {"name": "identifier", "label_ko": "손님 번호", "kind": "값", "range": "Text", "cardinality": "1", "required": True},
            {"name": "orderedItem", "label_ko": "자주 사는 것", "kind": "값", "range": "Text", "cardinality": "0..1"},
            {"name": "orderStatus", "label_ko": "요즘 형편", "kind": "값", "range": "Text", "cardinality": "0..1"},
            {"name": "seller", "label_ko": "단골 가게", "kind": "관계", "range": "shop:Nowhere", "cardinality": "0..1"}]},
    ],
    "enumerations": [{"name": "OrderStatus", "values": [{"value": "OrderProcessing", "label_ko": "처리 중"},
                                                         {"value": "OrderDelivered", "label_ko": "배송 완료"}]}],
    "relations": {"object_level": [{"subject": "주문", "predicate": "ordered_by", "object": "손님", "cardinality": "N:1"}],
                  "entity_level": [{"subject": "Order", "property": "customer", "object": "Person", "cardinality": "1", "label_ko": "주문한 손님"}]},
    "rule_links": [{"rule": "D-AX-01", "entities": ["Order"]}],
}
RULES = {
    "rules": [
        {"id": "D-AX-01", "tier": "AXIOM 후보", "area": "무르기", "type": "제한", "name": "무르기 기간 하한", "condition": "무르기 기간을 정할 때",
         "result": "받은 날부터 7일 이내에는 무를 수 있어야 한다", "exception": "—", "basis": "가게법 제3조", "law": "가게법",
         "basis_kind": "법률", "risk": "과태료", "verification": "조문 대조 필요", "policy_check": "정책서에 없음",
         "related": "주문 · 무르기 접수"},
        {"id": "D-ST-01", "tier": "Standard 제안", "type": "의무", "name": "늦은 배송 알림", "condition": "배송이 늦어질 때",
         "result": "새 예정일을 알린다", "basis": "업계 관행", "object": "손님"},
        {"id": "D-ST-02", "tier": "Standard 제안", "type": "의무", "name": "포장 상자 재사용", "result": "상자를 다시 쓴다",
         "object": "창고"},
        {"id": "D-CU-01", "tier": "Custom", "type": "판정", "name": "단골 무르기", "result": "단골은 14일까지 무를 수 있다"},
    ],
    # another file's links of the same rule name its Object and no Entities: the Entities linked before stay
    "rule_links": [{"rule": "D-AX-01", "area": "무르기", "object": "주문"}],
    "parameters": [{"key": "@undo_days_min", "value": "7", "kind": "법정 기준", "rules": ["D-AX-01"]},
                   {"key": "@late_fee_rate", "value": "15%", "kind": "법정 기준", "rules": []},
                   {"key": "@cutoff_time", "value": "14:00", "kind": "제안 기본값", "rules": []}],
    "banned_expressions": [{"scope": "먹을거리", "examples": "병을 고치는 · 약 대신", "kind": "금지", "reason": "약으로 오인",
                            "basis": "먹을거리법 제8조", "allowed_when": "성분 사실만 표기"},
                           {"scope": "값", "examples": "제일 싼", "kind": "조건부", "reason": "근거 없는 최상급",
                            "basis": "가게법 제5조", "allowed_when": "조사 기간 · 범위를 함께 표기"}],
    "laws": [{"key": "가게법"}],
}
GLOSSARY = {
    "meta": {"title": "가게 용어", "notation": {"접두어 없음": "표준"}},  # a later file that names no vocabulary takes none away
    "terms": [{"term": "선물 포장", "english": "shop:giftWrap", "concept": "주문 › 주문", "definition": "선물로 싸 주는 것", "synonyms": ["포장 서비스"]}],
    "relations": [
        {"relation": "혼동주의", "standard": "주문 줄@shop:OrderLine", "expressions": ["주문"], "note": "주문은 묶음, 주문 줄은 그 안의 한 줄"},
        {"relation": "동의어", "standard": "손님@Person", "expressions": ["고객", "구매자"]},
        {"relation": "쓰지 않는 표현", "standard": "손님@Person", "expressions": ["호갱"]},
    ],
    "customer_labels": [{"admin_labels": ["출고확정", "배송지시"], "customer_label": "상품준비중", "standard_value": "OrderProcessing"}],
    "preserved_words": [{"words": ["안", "못"]}],
}


@pytest.fixture(scope="module")
def made():
    return from_definitions([DRAFT, RULES, GLOSSARY], "shop", requires=[])


def test_objects_entities_properties_and_relations_are_carried(made):
    modules, _ = made
    body = modules[0].body
    assert set(body["areas"]) == {"Order", "Patron"} and body["areas"]["Order"]["aligned"] == ["https://schema.org/Order"]
    assert "aligned" not in body["areas"]["Patron"] and "상태 흐름: 접수 → 결제 → 배송 → 완료" in body["areas"]["Order"]["description"]
    order = body["objects"]["Order"]
    assert order["area"] == "Order" and order["key"] == "orderNumber" and order["aligned"] == ["https://schema.org/Order"]
    status = order["properties"]["orderStatus"]
    assert status["type"] == "enum" and status["values"] == ["OrderProcessing", "OrderDelivered"] and status["labels"]["OrderDelivered"] == "배송 완료"
    assert order["properties"]["giftWrap"]["type"] == "boolean" and "aligned" not in order["properties"]["giftWrap"]
    assert body["objects"]["OrderLine"]["key"] == "id"  # nothing in it reads as an identifier, so one is added and said
    assert body["links"]["customer"] == {"from": "Order", "to": "Person", "cardinality": "many_to_one", "label": "주문한 손님",
                                         "status": "draft", "required": True, "aligned": ["https://schema.org/customer"]}
    # a relation is not named as a property is: the one a property's name is taken by goes by its Entity's as well
    assert body["links"]["orderOrderedItem"]["to"] == "OrderLine" and body["links"]["orderOrderedItem"]["cardinality"] == "many_to_many"
    # one name has one type wherever it is used: a date beside a date and time is read as a date and time
    assert order["properties"]["validFrom"]["type"] == body["objects"]["OrderLine"]["properties"]["validFrom"]["type"] == "datetime"
    # a code beside free text of the same name: the later Entity's goes by its own name, and the codes stay where they were
    assert body["objects"]["Person"]["properties"]["personOrderStatus"]["type"] == "string" and "orderStatus" not in body["objects"]["Person"]["properties"]
    assert status["values"] == ["OrderProcessing", "OrderDelivered"]


def test_rules_go_to_the_module_of_their_layer_with_what_they_cost_and_how_far_they_were_checked(made):
    modules, _ = made
    by = {m.name: m for m in modules}
    assert [m.kind for m in modules] == ["domain", "axiom", "customer"] and by["shop-axiom"].requires[0].name == "shop"
    axiom = {c["id"]: c for c in by["shop-axiom"].body["rule_cards"]}
    limit = card_spec(axiom["D-AX-01"], "axiom")
    assert limit["type"] == "limit" and limit["layer"] == "axiom" and limit["legal_review"] == "pending"
    assert limit["risk"] == "과태료" and limit["verification"] == "조문 대조 필요" and limit["exceptions"] == []
    assert limit["applies_to"] == ["area:Order", "object:Order", "parameter:undo_days_min"] and limit["params"] == {"undo_days_min": 7}
    ban = card_spec(axiom["BX-01"], "axiom")
    assert ban["type"] == "ban" and ban["conditions"] == ["병을 고치는", "약 대신"] and ban["exceptions"] == ["성분 사실만 표기"]
    assert card_spec(by["shop"].body["rule_cards"][0], "domain")["type"] == "duty"
    assert card_spec(by["shop-custom"].body["rule_cards"][0], "customer")["layer"] == "custom"
    values = by["shop"].body["parameters"]
    assert values["undo_days_min"]["value"] == 7 and values["undo_days_min"]["label"] == "무르기 기간 하한"  # known by the rule that reads it
    assert values["late_fee_rate"] == {"type": "integer", "value": 15, "label": "late_fee_rate", "unit": "%", "cite": "법정 기준"}
    assert values["cutoff_time"]["type"] == "string" and values["cutoff_time"]["value"] == "14:00"


def test_a_rule_keeps_its_group_its_law_how_it_stands_against_the_policy_and_the_object_it_is_filed_under(made):
    """Every column a rule sheet gives has a field on the card: the Object it is filed under is what it applies to first
    (named by its label, from the rule or from another file's links of it), and an expression allowed only once a
    condition is met is a limit, not a ban."""
    modules, report = made
    by = {m.name: m for m in modules}
    axiom = {c["id"]: card_spec(c, "axiom") for c in by["shop-axiom"].body["rule_cards"]}
    limit = axiom["D-AX-01"]
    assert (limit["category"], limit["law"], limit["source_kind"], limit["policy_check"], limit["related"]) == \
        ("무르기", "가게법", "법률", "정책서에 없음", "주문 · 무르기 접수")
    standard = {c["id"]: card_spec(c, "domain") for c in by["shop"].body["rule_cards"]}
    assert standard["D-ST-01"]["applies_to"] == ["area:Patron"] and standard["D-ST-01"]["category"] == ""
    assert standard["D-ST-02"]["applies_to"] == []  # an Object the draft does not have is left off, and said
    assert "rule D-ST-02: Object '창고' is not in the draft, left off what it applies to" in report.adjusted
    assert [(c["id"], c["type"]) for c in axiom.values() if c["id"].startswith("BX-")] == [("BX-01", "ban"), ("BX-02", "limit")]
    assert axiom["BX-02"]["exceptions"] == ["조사 기간 · 범위를 함께 표기"]


def test_the_fields_an_import_gives_a_card_are_ones_a_person_edits(tmp_path):
    """What an import put on a card a person changes as any other field: an edit of the workspace gives it, and a new
    card is made with it."""
    from ontlas.manage import Workspace

    lib = Library(tmp_path)
    lib.import_definitions([DRAFT, RULES, GLOSSARY], "shop")
    ws = Workspace(lib.resolve(["shop", "shop-axiom", "shop-custom"]), compose_kw={"namespace": "https://example.org/shop#"})
    ws.apply("update_rule_card", {"id": "D-ST-01", "category": " 배송  알림 ", "policy_check": "관련 내용 있음 · 보완"})
    ws.apply("add_rule_card", {"id": "C-1", "type": "duty", "statement": "알린다", "law": "가게법", "source_kind": "고시"})
    cards = {c["id"]: c for c in ws.composed().cards}
    assert (cards["D-ST-01"]["category"], cards["D-ST-01"]["policy_check"]) == ("배송 알림", "관련 내용 있음 · 보완")
    assert (cards["C-1"]["law"], cards["C-1"]["source_kind"], cards["C-1"]["related"]) == ("가게법", "고시", "")


def test_the_glossary_joins_other_words_and_what_a_customer_is_shown_to_the_standard_term(made):
    modules, _ = made
    terms = {t["term"]: t for t in modules[0].terms}
    assert terms["선물 포장"]["concept"] == "property:Order.giftWrap" and terms["선물 포장"]["synonyms"] == ["포장 서비스"]
    assert terms["손님"]["concept"] == "object:Person" and terms["손님"]["synonyms"] == ["고객", "구매자"] and terms["손님"]["avoid"] == ["호갱"]
    assert terms["주문 줄"]["confusable"] == [{"term": "주문", "note": "주문은 묶음, 주문 줄은 그 안의 한 줄"}]
    shown = terms["처리 중"]
    assert shown["concept"] == "value:Order.orderStatus=OrderProcessing" and shown["channels"] == {"고객": "상품준비중"}
    assert shown["synonyms"] == ["출고확정", "배송지시"]


def test_what_has_no_place_is_named_not_dropped(made):
    _, report = made
    said = " | ".join(report.unsupported)
    assert "Person.seller → shop:Nowhere" in said and "1 relations between Objects" in said
    assert "section 'laws'" in said and "section 'preserved_words'" in said
    assert any("OrderLine: no property reads as its identifier" in x for x in report.adjusted)
    assert any("cutoff_time" in x for x in report.adjusted)
    assert any(x.startswith("property validFrom: date on OrderLine, datetime on Order") for x in report.adjusted)


def test_the_modules_compose_and_a_library_takes_them_in_and_gives_them_up(tmp_path):
    lib = Library(tmp_path)
    modules, _ = lib.import_definitions([DRAFT, RULES, GLOSSARY], "shop", label="가게 표준")
    assert lib.names() == ["shop", "shop-axiom", "shop-custom"] and modules[0].label == "가게 표준"
    assert modules[0].description == "가게 표준 초안"  # the first file's title, whatever the later files call themselves
    comp = compose(lib.resolve(["shop", "shop-axiom", "shop-custom"]))
    assert not comp.issues and {c["layer"] for c in comp.cards} == {"axiom", "standard", "custom"} and len(comp.ontology.objects) == 3
    with pytest.raises(Exception):  # a draft whose modules are there already is not written over
        lib.import_definitions([DRAFT], "shop")
    for name in ("shop-custom", "shop-axiom", "shop"):
        lib.delete(name)
    assert lib.names() == []


STALL = {  # a draft whose rows carry their own ids, two Entities sharing a code list and a glossary that points by path
    "objects": [
        {"id": "OB-1", "label_ko": "주문", "class": "Order", "group": "거래", "definition": "손님이 산 것",
         "scope_without_data": "정의만으로 보는 규칙", "scope_with_data": "주문 기록으로 찾는 빠짐",
         "entities": [{"class": "Order"}, {"class": "stall:Parcel"}]},
        {"id": "OB-2", "label_ko": "되돌림", "class": "stall:Undo", "definition": "산 것을 무르는 일", "entities": [{"class": "stall:Giveback"}]},
    ],
    "entities": [
        {"id": "EN-1", "name": "Order", "class": "Order", "label_ko": "주문", "rule_requirements": "주문 상태와 소포", "properties": [
            {"name": "orderNumber", "label_ko": "주문번호", "kind": "값", "range": "Text", "cardinality": "1", "required": True},
            {"name": "stall:parcel", "label_ko": "소포", "kind": "관계", "range": "stall:Parcel", "cardinality": "0..1"}]},
        {"id": "EN-2", "name": "Parcel", "class": "stall:Parcel", "label_ko": "소포", "properties": [
            {"name": "stall:wrapKind", "label_ko": "포장 종류", "kind": "열거형", "range": "stall:WrapKind", "cardinality": "0..1"},
            {"name": "stall:step", "label_ko": "단계", "kind": "열거형", "range": "stall:Step", "cardinality": "1"}]},
        {"id": "EN-3", "name": "Giveback", "class": "stall:Giveback", "label_ko": "되돌림 접수", "properties": [
            {"name": "stall:step", "label_ko": "단계", "kind": "열거형", "range": "stall:Step", "cardinality": "1"}]},
    ],
    "enumerations": [{"name": "stall:WrapKind", "values": [{"value": "Plain", "label_ko": "그냥"}, {"value": "Gift", "label_ko": "선물"}]},
                     {"name": "stall:Step", "values": [{"value": "Waiting", "label_ko": "대기"}, {"value": "Done", "label_ko": "끝"}]}],
}
STALL_WORDS = {
    "terms": [
        {"id": "W-01", "term": "줄 서기", "concept": "주문 › 주문", "definition": "주문을 기다리는 줄"},
        {"id": "W-02", "term": "선물 포장", "english": "stall:WrapKind · Gift", "concept": "주문 › 소포"},
        {"id": "W-03", "term": "포장 방식", "english": "stall:WrapKind", "concept": "주문 › 소포"},
        {"id": "W-04", "term": "보낼 소포", "english": "stall:parcel", "concept": "주문 › 주문"},
        {"id": "W-05", "term": "무르기 단계", "english": "stall:step", "concept": "주문 › 주문 · 되돌림 › 되돌림 접수"},
        {"id": "W-06", "term": "꼼수 안내", "concept": "되돌림 · 되돌림 › 되돌림 접수"},
    ],
    "relations": [
        {"relation": "동의어", "standard": "되돌림@stall:Undo", "expressions": ["무르기"]},
        {"relation": "동의어", "standard": "주문@Order", "expressions": ["오더"]},
        {"relation": "동의어", "standard": "환불 방법", "expressions": ["돈 돌려주기"], "basis": "제안"},
        {"relation": "상위 · 하위", "standard": "되돌림 방법", "expressions": ["환불 방법"], "basis": "가게 수칙", "needs_check": True},
    ],
    "customer_labels": [
        {"area": "되돌림 접수", "admin_labels": ["접수"], "customer_label": "무르기 신청", "standard_value": "Waiting", "needs_check": "Y"},
        {"area": "되돌림 접수", "admin_labels": ["끝냄"], "customer_label": "무르기 끝", "standard_value": "Done"},
    ],
}


def test_a_draft_row_keeps_its_id_and_its_notes_and_a_glossary_points_where_its_path_says():
    modules, _ = from_definitions([STALL, STALL_WORDS], "stall", requires=[])
    body = modules[0].body
    order = body["areas"]["Order"]
    assert order["cite"] == "OB-1" and "묶음: 거래" in order["description"] and "연결 없이: 정의만으로 보는 규칙" in order["description"]
    assert body["objects"]["Order"]["cite"] == "EN-1" and body["objects"]["Order"]["description"] == "규칙이 요구하는 것: 주문 상태와 소포"
    terms = {}
    for t in modules[0].terms:
        terms.setdefault(t["term"], []).append(t)
    one = {k: v[0] for k, v in terms.items()}
    assert one["줄 서기"]["id"] == "W-01" and one["줄 서기"]["concept"] == "object:Order"
    # the English names a code after its list, the list a property takes, a relation; the first of two paths that names one
    assert one["선물 포장"]["concept"] == "value:Parcel.wrapKind=Gift" and one["포장 방식"]["concept"] == "property:Parcel.wrapKind"
    assert one["보낼 소포"]["concept"] == "link:parcel" and one["무르기 단계"]["concept"] == "property:Giveback.step"
    assert one["꼼수 안내"]["concept"] == "area:Undo"  # a path of an Object alone
    assert one["되돌림"]["concept"] == "area:Undo" and one["주문"]["concept"] == "object:Order"  # no Entity of that class; one of it
    # 상위 · 하위: the standard term is the broader one, and each side says so; the ground and the check of the row stay
    assert one["되돌림 방법"]["narrower"] == ["환불 방법"] and one["환불 방법"]["broader"] == ["되돌림 방법"]
    assert one["되돌림 방법"]["cite"] == "가게 수칙" and one["되돌림 방법"]["status"] == "review" and "status" not in one["환불 방법"]
    # a customer label is the code of the Entity its row names, though the first property allowing the code is another's
    waiting = one["대기"]
    assert waiting["concept"] == "value:Giveback.step=Waiting" and waiting["channels"] == {"고객": "무르기 신청"}
    assert waiting["synonyms"] == ["접수"] and waiting["status"] == "review"
    assert one["끝"]["concept"] == "value:Giveback.step=Done" and "status" not in one["끝"]


def test_a_word_a_customer_label_gives_that_already_names_another_thing_is_an_entry_of_its_own():
    words = {**STALL_WORDS, "terms": [{"term": "대기", "concept": "주문 › 주문"}], "relations": []}
    modules, _ = from_definitions([STALL, words], "stall", requires=[])
    same = [t for t in modules[0].terms if t["term"] == "대기"]
    assert [t["concept"] for t in same] == ["object:Order", "value:Giveback.step=Waiting"]
    assert "channels" not in same[0] and same[1]["channels"] == {"고객": "무르기 신청"}
