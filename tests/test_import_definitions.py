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


def test_an_entity_two_files_both_list_is_one_entity_whichever_comes_first():
    named = {"entities": [{"name": "Order", "class": "Order", "label_ko": "주문", "definition": "한 번의 결제로 묶인 거래"}]}
    filled = {"entities": [{"class": "Order", "definition": "", "properties": [
        {"name": "orderNumber", "label_ko": "주문번호", "kind": "값", "range": "Text", "cardinality": "1", "required": True}]}]}
    more = {"entities": [{"class": "Order", "properties": [
        {"name": "orderNumber", "label_ko": "다른 이름", "range": "Integer"},
        {"name": "note", "label_ko": "메모", "kind": "값", "range": "Text", "cardinality": "0..1"}]}]}
    made = [from_definitions(docs, "shop", requires=[])[0][0].body["objects"] for docs in ([named, filled, more], [filled, more, named])]
    assert made[0] == made[1] and list(made[0]) == ["Order"]
    order = made[0]["Order"]
    assert order["label"] == "주문" and order["description"] == "한 번의 결제로 묶인 거래" and order["key"] == "orderNumber"
    assert list(order["properties"]) == ["orderNumber", "note"] and order["properties"]["orderNumber"]["label"] == "주문번호"


def test_an_entity_is_filed_under_the_object_its_row_names_by_label_or_by_english_name():
    """As a rule's Object is read: the label, or the English name as the draft writes it. An Object the draft does not
    have files the Entity under none."""
    draft = {"objects": [{"label_ko": "주문", "class": "Order"}, {"label_ko": "손님", "class": "shop:Patron"}],
             "entities": [{"name": "Receipt", "label_ko": "영수증", "object": "주문"},
                          {"name": "Basket", "label_ko": "장바구니", "object": "Order"},
                          {"name": "Member", "label_ko": "단골", "object": "Patron"},
                          {"name": "Visit", "label_ko": "방문", "object": "shop:Patron"},
                          {"name": "Coupon", "label_ko": "쿠폰", "object": "손님@shop:Patron"},
                          {"name": "Shelf", "label_ko": "선반", "object": "창고"},
                          {"name": "Note", "label_ko": "메모"}],
             "rules": [{"id": "R-1", "type": "의무", "name": "영수증 발급", "object": "shop:Patron"}]}
    modules, report = from_definitions([draft], "shop", requires=[])
    assert {n: o.get("area") for n, o in modules[0].body["objects"].items()} == {
        "Receipt": "Order", "Basket": "Order", "Member": "Patron", "Visit": "Patron", "Coupon": "Patron", "Shelf": None, "Note": None}
    assert modules[0].body["rule_cards"][0]["applies_to"] == ["area:Patron"] and not [x for x in report.adjusted if "R-1" in x]


# ---- the same draft kept as workbooks: a sheet to a section, named and headed in Korean as a team writes them ----

BOOK = {
    "안내": [["가게 표준 초안"], ["구성", "Object · Entity · Property · 열거형 · 관계 · 규칙 연결"]],
    "Object 초안": [
        ["번호", "Object 표기", "어휘", "정의", "상태 흐름", "주요 Entity", "Entity 수"],
        [1, "주문@Order", "schema.org", "손님이 물건을 사려고 만든 거래", "접수 → 결제 → 배송 → 완료", "주문@Order, 주문 줄@shop:OrderLine", 2],
        [2, "손님@shop:Patron", "shop", "가게에서 사는 사람", None, "손님@Person", 1],
        ["합계", None, None, None, None, None, 3],
    ],
    "Entity": [
        ["Entity", "영문 이름", "클래스", "어휘", "정의"],
        ["주문", "Order", "Order", "schema.org", "한 번의 결제로 묶인 거래"],
        ["주문 줄", "OrderLine", "shop:OrderLine", "shop", None],
        ["손님", "Person", "Person", "schema.org", "—"],
    ],
    "Property": [
        ["Entity 클래스", "Entity", "속성", "한글 이름", "종류", "어휘", "값 유형", "값 유형 (한글)", "개수", "필수"],
        ["Order", "주문", "orderNumber", "주문번호", "값", "schema.org", "Text", "글", 1, "필수"],
        ["Order", "주문", "orderStatus", "주문 상태", "열거형", None, "OrderStatus", "주문 상태", 1, "필수"],
        ["Order", "주문", "shop:giftWrap", "선물 포장", "값", "shop", "Boolean", "참 · 거짓", "0..1", None],
        ["Order", "주문", "validFrom", "받은 때", "값", None, "DateTime", "일시", "0..1", None],
        ["Order", "주문", "customer", "주문한 손님", "관계", None, "Person", "손님", 1, None],
        ["Order", "주문", "orderedItem", "주문 줄", "관계", None, "shop:OrderLine", "주문 줄", "1..n", None],
        ["shop:OrderLine", "주문 줄", "shop:quantity", "수량", "값", None, "Integer", "정수", 1, "필수"],
        ["shop:OrderLine", "주문 줄", "validFrom", "담은 날", "값", None, "Date", "날짜", "0..1", None],
        ["Person", "손님", "identifier", "손님 번호", "값", None, "Text", "글", 1, "필수"],
        ["Person", "손님", "orderedItem", "자주 사는 것", "값", None, "Text", "글", "0..1", None],
        ["Person", "손님", "orderStatus", "요즘 형편", "값", None, "Text", "글", "0..1", None],
        ["Person", "손님", "seller", "단골 가게", "관계", None, "shop:Nowhere", "없는 곳", "0..1", None],
    ],
    "열거형": [["열거형", "값 수", "값 (한글)"], ["OrderStatus", 2, "OrderProcessing · 처리 중\nOrderDelivered · 배송 완료"]],
    "Object 관계": [["주어 Object", "관계 유형", "대상 Object", "개수"], ["주문", "ordered_by", "손님", "N:1"]],
    "Entity 관계": [["주어 클래스", "속성", "대상 클래스", "개수", "뜻"], ["Order", "customer", "Person", 1, "주문한 손님"]],
    "규칙 연결": [["규칙 ID", "관련 Entity (클래스)"], ["D-AX-01", "Order"]],
}
RULE_BOOK = {
    "규칙 초안": [
        ["초안 ID", "계층 제안", "영역", "유형", "규칙 이름", "조건", "결과", "예외 · 비고", "근거", "대표 법령", "근거 종류", "위반 시 · 위험",
         "확인 수준", "가게 정책서 대조", "관련 Object · Entity", "적용 Object", "검토 상태"],
        ["D-AX-01", "AXIOM 후보", "무르기", "제한", "무르기 기간 하한", "무르기 기간을 정할 때", "받은 날부터 7일 이내에는 무를 수 있어야 한다", "—",
         "가게법 제3조", "가게법", "법률", "과태료", "조문 대조 필요", "정책서에 없음", "주문 · 무르기 접수", None, "초안"],
        ["D-ST-01", "Standard 제안", None, "의무", "늦은 배송 알림", "배송이 늦어질 때", "새 예정일을 알린다", None, "업계 관행", None, None, None,
         None, None, None, "손님", "초안"],
        ["D-ST-02", "Standard 제안", None, "의무", "포장 상자 재사용", None, "상자를 다시 쓴다", None, None, None, None, None, None, None, None,
         "창고", "초안"],
        ["D-CU-01", "Custom", None, "판정", "단골 무르기", None, "단골은 14일까지 무를 수 있다", None, None, None, None, None, None, None, None,
         None, "초안"],
    ],
    "규칙 연결": [["규칙 ID", "주 Object"], ["D-AX-01", "주문"]],
    "기준값": [["키", "값", "종류", "쓰는 규칙 (초안 ID)", "쓰는 규칙 수"], ["@undo_days_min", 7, "법정 기준", "D-AX-01", 1],
            ["@late_fee_rate", "15%", "법정 기준", None, 0], ["@cutoff_time", "14:00", "제안 기본값", None, 0]],
    "금지 표현": [["품목 · 상황", "표현 예", "구분", "이유", "근거", "쓸 수 있는 조건 · 대체 표현"],
              ["먹을거리", "병을 고치는 · 약 대신", "금지", "약으로 오인", "먹을거리법 제8조", "성분 사실만 표기"],
              ["값", "제일 싼", "조건부", "근거 없는 최상급", "가게법 제5조", "조사 기간 · 범위를 함께 표기"]],
    "근거 법령": [["대표 법령", "규칙 수"], ["가게법", 1]],
}
WORD_BOOK = {
    "안내": [["가게 용어"]],
    "용어": [["용어", "영문 표기", "연결 개념", "정의", "동의어"], ["선물 포장", "shop:giftWrap", "주문 › 주문", "선물로 싸 주는 것", "포장 서비스"]],
    "표현 관계": [["관계", "표준 용어 (A)", "다른 표현 (B)", "설명"],
              ["혼동주의", "주문 줄@shop:OrderLine", "주문", "주문은 묶음, 주문 줄은 그 안의 한 줄"],
              ["동의어", "손님@Person", "고객, 구매자", None], ["쓰지 않는 표현", "손님@Person", "호갱", None]],
    "고객 표기": [["관리자 표기 (처리 단계)", "고객 표기", "표준 값"], ["출고확정 · 배송지시", "상품준비중", "OrderProcessing"]],
    "보존어": [["표현", "종류"], ["안 · 못", "부정어"]],
    "집계": [["집계"], ["구분", "수"], ["용어", 1]],
}


def workbook(sheets: dict) -> bytes:
    import io

    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, rows in sheets.items():
        ws = wb.create_sheet(title)
        for row in rows:
            ws.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


@pytest.fixture(scope="module")
def books():
    from ontlas.exchange.workbook import read_workbook

    return [read_workbook(workbook(sheets), name) for sheets, name in ((BOOK, "draft.xlsx"), (RULE_BOOK, "rules.xlsx"), (WORD_BOOK, "words.xlsx"))]


def test_a_draft_kept_as_workbooks_makes_the_modules_its_yaml_makes(made, books):
    """Every sheet is read as the section of its name and every column as the key its header names, so what comes out is
    what the same draft as YAML gives: Objects, Entities with their properties and codes, relations, cards, values, terms."""
    modules, report = made
    from_books, book_report = from_definitions(books, "shop", requires=[])
    assert [m.to_dict() for m in from_books] == [m.to_dict() for m in modules]
    assert sorted(book_report.adjusted) == sorted(report.adjusted)
    assert books[0]["meta"]["title"] == "가게 표준 초안" and books[0]["meta"]["notation"] == {"schema.org": "https://schema.org/"}
    assert {k: len(v) for k, v in books[0].items() if k != "meta"} == {"objects": 2, "entities": 3, "enumerations": 1,
                                                                        "object_relations": 1, "entity_relations": 1, "rule_links": 1}
    order = books[0]["entities"][0]
    assert order["properties"][0] == {"name": "orderNumber", "label_ko": "주문번호", "kind": "값", "vocabulary": "schema.org",
                                      "range": "Text", "cardinality": "1", "required": True}
    assert books[0]["objects"][0]["entities"] == [{"class": "Order", "label_ko": "주문"}, {"class": "shop:OrderLine", "label_ko": "주문 줄"}]
    assert "exception" not in books[1]["rules"][0] and "definition" not in books[0]["entities"][2]  # a dash is an empty cell
    assert books[1]["rules"][0]["policy_check"] == "정책서에 없음"  # whose policy it is may be written before the name
    assert books[2]["term_relations"][1]["expressions"] == ["고객", "구매자"] and books[2]["customer_labels"][0]["admin_labels"] == ["출고확정", "배송지시"]


def test_what_a_workbook_holds_that_was_not_read_is_in_the_report(books):
    """A sheet that is no section (notes, a tally, a table the import has no place for), a column that is no key of its
    section and a row that names nothing (a total) are each said, by the sheet's own name."""
    _, report = from_definitions(books, "shop", requires=[])
    said = [x for x in report.unsupported if x.startswith("sheet ")]
    assert "sheet '안내' of draft.xlsx: notes, not a table of rows; only its first line was read, as the draft's title" in said
    assert "sheet '안내' of words.xlsx: notes, not a table of rows; only its first line was read, as the draft's title" in said
    assert "sheet 'Object 초안' of draft.xlsx: columns not read: 번호, Entity 수" in said
    assert "sheet 'Object 초안' of draft.xlsx: 1 of its rows name no item (a total, a note), not read" in said
    assert "sheet 'Property' of draft.xlsx: columns not read: Entity, 값 유형 (한글)" in said  # the nearer of two headers is the key's
    assert "sheet '규칙 초안' of rules.xlsx: columns not read: 검토 상태" in said
    assert "sheet '기준값' of rules.xlsx: columns not read: 쓰는 규칙 수" in said
    assert "sheet '근거 법령' of rules.xlsx (1 rows): not a section of a draft, not read" in said
    assert "sheet '보존어' of words.xlsx (1 rows): not a section of a draft, not read" in said
    assert "sheet '집계' of words.xlsx (2 rows): not a section of a draft, not read" in said
    assert len(said) == 12 and not any(x.startswith("section ") for x in report.unsupported)


def test_a_sheet_is_read_by_its_yaml_keys_too_under_a_title_and_a_synonym_may_hold_a_middle_dot():
    from ontlas.exchange.workbook import COLUMNS, draft_of, read_workbook

    doc = read_workbook(workbook({"Sheet1": [["가게 말 목록"], [], ["id", "term", "definition", "synonyms", "memo"],
                                             ["W-1", "무르기", "산 것을 되돌리는 일", "되돌리기, 도로 내기", "나중에"],
                                             ["W-2", "먼 곳 배송비", None, "섬 · 산골 배송비", None]]}), "terms.xlsx")
    assert doc["terms"] == [{"id": "W-1", "term": "무르기", "definition": "산 것을 되돌리는 일", "synonyms": ["되돌리기", "도로 내기"]},
                            {"id": "W-2", "term": "먼 곳 배송비", "synonyms": ["섬 · 산골 배송비"]}]  # the one sheet, by its file's name
    assert doc["meta"]["not_read"] == ["sheet 'Sheet1' of terms.xlsx: columns not read: memo"]
    # a sheet named only `relations` is the kind its columns say, as a YAML draft's `relations` is
    pairs = read_workbook(workbook({"relations": [["relation", "standard", "expressions"], ["동의어", "손님", "고객 · 구매자"]],
                                    "Properties": [["entity", "name", "range"], ["Parcel", "weight", "Number"]]}), "more.xlsx")
    assert pairs["term_relations"] == [{"relation": "동의어", "standard": "손님", "expressions": ["고객", "구매자"]}]
    assert pairs["entities"] == [{"class": "Parcel", "properties": [{"name": "weight", "range": "Number"}]}]  # an Entity by its properties alone
    assert draft_of([]) == {}
    for section, keys in COLUMNS.items():  # a name is one key's within a section
        names = [n.lower() for spelled in keys.values() for n in spelled]
        assert len(names) == len(set(names)), section


def test_a_file_that_is_no_workbook_or_holds_no_section_says_why():
    from ontlas.draft import ReadError
    from ontlas.exchange.workbook import read_workbook

    with pytest.raises(ReadError) as e:
        read_workbook(b"not a workbook", "draft.xlsx")
    assert e.value.reason == "workbook"
    with pytest.raises(ReadError, match="its sheets: 매출, 메모") as e:
        read_workbook(workbook({"매출": [["날짜", "금액"], ["2026-01-02", 1200]], "메모": [["한 줄"]]}), "sales.xlsx")
    assert e.value.reason == "empty"


def test_the_command_takes_workbooks(tmp_path, capsys):
    import json

    pytest.importorskip("yaml")  # a module is written as YAML
    from ontlas.cli import main

    files = []
    for sheets, name in ((BOOK, "draft.xlsx"), (RULE_BOOK, "rules.xlsx"), (WORD_BOOK, "words.xlsx")):
        files.append(tmp_path / name)
        files[-1].write_bytes(workbook(sheets))
    assert main(["library", "import-definitions", str(tmp_path / "lib"), "shop", *map(str, files)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["created"] == ["shop@0.1.0", "shop-axiom@0.1.0", "shop-custom@0.1.0"]
    assert out["elements"]["shop"]["object"] == 3 and out["elements"]["shop"]["term"] == 4 and out["elements"]["shop-axiom"]["rule_card"] == 3
    assert "sheet '근거 법령' of rules.xlsx (1 rows): not a section of a draft, not read" in out["report"]["unsupported"]
    assert Library(tmp_path / "lib").get("shop").label == "가게 표준 초안"


def test_the_page_takes_a_workbook_as_a_draft_s_file():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio projects a graph
    from pathlib import Path

    from ontlas.config import load_studio
    from ontlas.web import library_entry
    from ontlas.web.api import StudioSession

    shop = Path(__file__).resolve().parent.parent / "examples" / "library" / "studio.yaml"
    first = load_studio(shop)
    session = StudioSession(first)
    session.libraries = [library_entry("l1", shop, first)]
    held = session.library_file("draft.xlsx", workbook(BOOK))
    assert held["files"][0]["kind"] == "definitions" and held["files"][0]["sections"]["entities"] == 3
    session.library_file("rules.xlsx", workbook(RULE_BOOK))
    for name, data, why in (("broken.xlsx", b"PK no workbook", "XLSX 형식이 아니어서"),
                            ("sales.xlsx", workbook({"매출": [["날짜", "금액"], ["2026-01-02", 1200]]}), "정의 목록이 없어")):
        with pytest.raises(ValueError, match=why):
            session.library_file(name, data)
    assert [f["name"] for f in session.library_files()["files"]] == ["draft.xlsx", "rules.xlsx"]
    out = session.library_new("가게 표준", "files", key="shop")
    assert out["made"]["areas"] == 2 and out["made"]["objects"] == 3 and out["made"]["links"] == 2 and out["made"]["cards"] == 6
    assert out["made"]["parameters"] == 3 and any(x.startswith("sheet '근거 법령'") for x in out["report"]["unsupported"]["lines"])
