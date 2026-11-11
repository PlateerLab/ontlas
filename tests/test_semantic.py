"""Rules in three layers (AXIOM › Custom › Standard) and the rule cards that record them: AXIOM rules are checked first
and nothing below changes or removes them, a value an AXIOM card bounds cannot be set outside the bound, and a decision
says layer by layer how it was reached."""
import json
from pathlib import Path

import pytest

from ontlas import Ontology
from ontlas.decide.table import evaluate_table
from ontlas.modules import KINDS, Module, ModuleError, compose, removal_impact
from ontlas.preview import MODULE_COLOR, MODULE_KIND
from ontlas.semantic import LAYERS, decision_path, semantic_view
from ontlas.studio import Studio

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
NS = "https://example.org/t#"


def _shop(**more) -> Module:
    return Module.from_dict({
        "module": "shop", "namespace": NS,
        "parameters": {"window": {"type": "integer", "value": 7, "min": 1, "label": "반품 기간", "unit": "일"}},
        "objects": {"Line": {"key": "line_id", "properties": {"line_id": {"type": "string"},
                                                              "age": {"type": "integer"}, "grade": {"type": "string"}}}},
        "decisions": {"returnable": {
            "target": "Line", "outputs": {"ok": "boolean", "why": "string"}, "hit_policy": "first",
            "inputs": {"age": {"type": "integer", "property": "age"}, "grade": {"type": "string", "property": "grade"}},
            "rules": [{"id": "missing", "when": {"age": "null"}, "then": {"ok": False, "why": "no date"}},
                      {"id": "in", "when": {"age": "<= @window"}, "then": {"ok": True, "why": "in window"}},
                      {"id": "out", "when": {}, "then": {"ok": False, "why": "late"}}]}},
        "rule_cards": [{"id": "std-window", "type": "decide", "statement": "Within the window a line comes back.",
                        "implements": ["decision:returnable#in"], "status": "approved"}],
        **more})


def _law(**more) -> Module:
    return Module.from_dict({
        "module": "law", "kind": "axiom", "label": "법령 기준", "requires": ["shop"],
        "extend": {"decisions": {"returnable": {"rules_append": [
            {"id": "negative", "when": {"age": "< 0"}, "then": {"ok": False, "why": "impossible age"}, "owner": "법무팀"}]}}},
        "rule_cards": [{"id": "law-window", "type": "decide", "statement": "The window is at least 7 days.",
                        "check": {"parameter": "window", "min": 7}, "status": "approved", "legal_review": "done",
                        "implements": ["decision:returnable#in", "parameter:window"]},
                       {"id": "law-refund", "type": "compute", "statement": "A refund never exceeds the payment."}],
        **more})


def _acme(**more) -> Module:
    return Module.from_dict({"module": "acme", "kind": "customer", "label": "ACME", "requires": ["shop"], **more})


# ---- the axiom kind and the layers ----------------------------------------------------------------------------------

def test_an_axiom_module_is_a_kind_with_a_label_and_a_colour():
    assert "axiom" in KINDS and MODULE_KIND["axiom"] == "AXIOM" and MODULE_COLOR["axiom"].startswith("#")
    assert list(MODULE_KIND)[0] == "axiom"  # listed first: it is checked first
    assert LAYERS == ("axiom", "custom", "standard")


def test_axiom_rules_come_first_and_every_rule_knows_its_layer_module_and_version():
    vip = {"id": "vip", "when": {"grade": '"VIP"'}, "then": {"ok": True, "why": "vip"}}
    comp = compose([_shop(), _law(), _acme(version="2.0.0", extend={"decisions": {"returnable": {"rules_prepend": [vip]}}})])
    assert comp.issues == []
    rules = comp.ontology.decisions["returnable"].rules
    assert [(r.id, r.layer, r.module, r.version) for r in rules] == [
        ("negative", "axiom", "law", "0.1.0"), ("vip", "custom", "acme", "2.0.0"),
        ("missing", "standard", "shop", "0.1.0"), ("in", "standard", "shop", "0.1.0"), ("out", "standard", "shop", "0.1.0")]
    assert rules[0].owner == "법무팀"
    t = comp.ontology.decisions["returnable"]
    assert evaluate_table(t, {"age": -1, "grade": "VIP"})[1] == ["negative"]  # the AXIOM rule before the customer's


def test_a_rule_says_nothing_of_its_own_layer_its_module_does():
    sly = {"id": "sly", "when": {}, "then": {"ok": True}, "layer": "axiom"}
    comp = compose([_shop(), _acme(extend={"decisions": {"returnable": {"rules_append": [sly]}}})])
    assert next(r for r in comp.ontology.decisions["returnable"].rules if r.id == "sly").layer == "custom"


def test_nothing_below_axiom_changes_or_removes_an_axiom_rule():
    for patch in ({"rules_remove": ["negative"]}, {"rules_replace": {"negative": {"id": "negative", "when": {}, "then": {}}}}):
        with pytest.raises(ModuleError, match="AXIOM rule 'negative' of decision 'returnable'"):
            compose([_shop(), _law(), _acme(requires=["law"], extend={"decisions": {"returnable": patch}})])
    with pytest.raises(ModuleError, match="removes decision 'returnable', which holds AXIOM rule 'negative'"):
        compose([_shop(), _law(), _acme(requires=["law"], remove={"decisions": ["returnable"]})])
    # an axiom module may make a standard rule its own: it is then AXIOM, first, and protected
    law = _law(extend={"decisions": {"returnable": {"rules_replace": {"missing": {
        "id": "missing", "when": {"age": "null"}, "then": {"ok": False, "why": "no date"}, "cite": "Law 1"}}}}})
    rules = compose([_shop(), law]).ontology.decisions["returnable"].rules
    assert [(r.id, r.layer) for r in rules][:1] == [("missing", "axiom")] and rules[0].cite == "Law 1"


def test_under_priority_an_axiom_rule_wins_whatever_number_a_lower_layer_gives_itself():
    shop = _shop()
    t = shop.body["decisions"]["returnable"]
    t["hit_policy"] = "priority"
    for i, r in enumerate(t["rules"]):
        r["priority"] = i + 5
    law = _law(extend={"decisions": {"returnable": {"rules_append": [
        {"id": "negative", "when": {"age": "< 0"}, "then": {"ok": False, "why": "impossible age"}, "priority": 99}]}}})
    cheat = {"id": "cheat", "when": {}, "then": {"ok": True, "why": "always"}, "priority": 0}
    comp = compose([shop, law, _acme(extend={"decisions": {"returnable": {"rules_append": [cheat]}}})])
    out, matched, _ = evaluate_table(comp.ontology.decisions["returnable"], {"age": -3, "grade": "A"})
    assert matched[0] == "negative" and out["ok"] is False
    assert evaluate_table(comp.ontology.decisions["returnable"], {"age": 3, "grade": "A"})[1][0] == "cheat"


def test_a_pick_between_sources_never_sets_an_axiom_rule_aside():
    o = compose([_shop(), _law()]).ontology
    t = o.decisions["returnable"]
    t.rules[0].overruled_by = {"out": "c1"}  # as a pick of the other source would mark it, where both hold
    assert evaluate_table(t, {"age": -1, "grade": "A"})[1] == ["negative"]
    t.rules[1].overruled_by = {"out": "c1"}  # a standard rule is set aside as before
    assert evaluate_table(t, {"age": None, "grade": "A"})[1] == ["out"]


def test_layer_owner_and_status_are_read_and_written_back():
    o = compose([_shop(), _law()]).ontology
    d = o.to_dict()
    rules = d["decisions"]["returnable"]["rules"]
    assert rules[0]["layer"] == "axiom" and rules[0]["owner"] == "법무팀"
    assert all("layer" not in r for r in rules[1:])  # a standard rule is written as it always was
    again = Ontology.from_dict(d)
    assert again.to_dict() == d and again.decisions["returnable"].rules[0].layer == "axiom"
    d["decisions"]["returnable"].update(owner="반품팀", status="approved")
    d["decisions"]["returnable"]["rules"][1]["status"] = "review"
    again = Ontology.from_dict(d)
    assert again.validate() == [] and again.to_dict() == d and again.decisions["returnable"].owner == "반품팀"
    d["decisions"]["returnable"]["rules"][1]["status"] = "done"
    d["decisions"]["returnable"]["rules"][2]["layer"] = "law"
    issues = Ontology.from_dict(d).validate()
    assert any("status 'done'" in i for i in issues) and any("layer 'law'" in i for i in issues)


# ---- rule cards ---------------------------------------------------------------------------------------------------

def test_rule_cards_go_through_load_and_save_and_join_the_composition(tmp_path):
    law = _law()
    assert Module.from_dict(law.to_dict()).to_dict() == law.to_dict()
    assert "rule_card:law-window" in law.elements() and law.counts()["rule_cards"] == 2
    pytest.importorskip("yaml")
    law.dump(tmp_path / "law.yaml")
    assert Module.load(tmp_path / "law.yaml").to_dict() == law.to_dict()
    comp = compose([_shop(), law])
    cards = {c["id"]: c for c in comp.cards}
    assert (cards["law-window"]["layer"], cards["law-window"]["module"], cards["law-window"]["version"]) == ("axiom", "law", "0.1.0")
    assert cards["std-window"]["layer"] == "standard" and cards["law-refund"]["status"] == "draft"  # unset: a draft
    assert comp.owner("rule_card:law-window") == "law"
    assert "rule_card:law-window" in removal_impact([_shop(), law], "law").removed


def test_a_card_is_checked_when_it_is_composed():
    bad = [({"id": "x", "type": "guess", "statement": "s"}, "type 'guess'"),
           ({"id": "x", "type": "decide"}, "give a statement"),
           ({"id": "x", "type": "decide", "statement": "s", "status": "done"}, "status 'done'"),
           ({"id": "x", "type": "decide", "statement": "s", "check": {"parameter": "window"}}, "check needs"),
           ({"id": "x", "type": "decide", "statement": "s", "implements": ["returnable"]}, "is not kind:name"),
           ({"id": "x", "type": "decide", "statement": "s", "layer": "axiom"}, "only by an axiom module"),
           ({"id": "x", "type": "decide", "statement": "s", "color": "red"}, "unknown fields"),
           ({"id": "x y", "type": "decide", "statement": "s"}, "rule card id")]
    for card, says in bad:
        with pytest.raises(ModuleError, match=says):
            compose([_shop(), _acme(rule_cards=[card])])
    with pytest.raises(ModuleError, match="already defined by shop"):
        compose([_shop(), _acme(rule_cards=[{"id": "std-window", "type": "decide", "statement": "s"}])])


def test_a_customer_extends_or_removes_cards_below_axiom_and_never_an_axiom_card():
    comp = compose([_shop(), _law(), _acme(extend={"rule_cards": {"std-window": {"owner": "고객경험팀"}}})])
    card = next(c for c in comp.cards if c["id"] == "std-window")
    assert card["owner"] == "고객경험팀" and card["module"] == "shop" and comp.touched["rule_card:std-window"] == ["acme"]
    assert [c["id"] for c in compose([_shop(), _acme(remove={"rule_cards": ["std-window"]})]).cards] == []
    with pytest.raises(ModuleError, match="changes AXIOM rule card 'law-window'"):
        compose([_shop(), _law(), _acme(requires=["law"], extend={"rule_cards": {"law-window": {"status": "draft"}}})])
    with pytest.raises(ModuleError, match="removes AXIOM rule card 'law-window'"):
        compose([_shop(), _law(), _acme(requires=["law"], remove={"rule_cards": ["law-window"]})])


# ---- the registration check ----------------------------------------------------------------------------------------

def test_a_value_below_an_axiom_bound_does_not_compose_and_the_message_names_everything():
    comp = compose([_shop(), _law(), _acme(label="ACME 운영", extend={"parameters": {"window": 5}})])
    assert comp.issues == ["AXIOM law-window: window (반품 기간) is 5, below the minimum 7; set by acme (ACME 운영)"]
    assert comp.checks[0]["passed"] is False and comp.checks[0]["set_by"] == "acme"
    with pytest.raises(ModuleError, match="AXIOM law-window"):
        Studio.from_modules([_shop(), _law(), _acme(extend={"parameters": {"window": 5}})])
    ok = compose([_shop(), _law(), _acme(extend={"parameters": {"window": 10}})])
    assert ok.issues == [] and ok.checks[0]["passed"] is True and "10일 · 7일 이상 충족" in ok.checks[0]["said"]
    assert compose([_shop(), _acme(extend={"parameters": {"window": 5}})]).issues == []  # no AXIOM module, no bound


def test_a_check_on_a_card_below_axiom_is_a_finding_and_a_missing_value_is_not_checked():
    soft = {"id": "soft", "type": "watch", "statement": "s", "check": {"parameter": "window", "max": 5}}
    gone = {"id": "gone", "type": "watch", "statement": "s", "check": {"parameter": "nothing", "min": 1}}
    comp = compose([_shop(), _acme(rule_cards=[soft, gone])])
    by = {c["card"]: c for c in comp.checks}
    assert comp.issues == [] and by["soft"]["passed"] is False and not by["soft"]["blocking"]
    assert by["gone"]["passed"] is None and "정의에 없어" in by["gone"]["said"]


def test_detaching_what_kept_a_value_inside_its_bound_is_refused():
    shop = _shop()
    shop.body["parameters"]["window"]["value"] = 5
    st = Studio.from_modules([shop, _acme(extend={"parameters": {"window": 10}}), _law()])
    assert not removal_impact(st.composition.modules, "acme").ok
    with pytest.raises(ModuleError, match="AXIOM law-window: window"):
        st.detach("acme")


# ---- the decision path ----------------------------------------------------------------------------------------------

def test_the_path_says_layer_by_layer_what_happened():
    comp = compose([_shop(), _law(), _acme(label="ACME", extend={"decisions": {"returnable": {"rules_prepend": [
        {"id": "vip", "when": {"grade": '"VIP"'}, "then": {"ok": True, "why": "vip"}}]}}})])
    t = comp.ontology.decisions["returnable"]
    labels = {m.name: m.label or m.name for m in comp.modules}

    def path(values):
        _, matched, _ = evaluate_table(t, values)
        from ontlas.decide.table import holding

        return decision_path(t, matched, [r.id for r in holding(t, values)], labels)

    p = path({"age": 3, "grade": "VIP"})
    assert [(x["label"], x["rules"], x["fired"], x["said"]) for x in p["layers"]] == [
        ("AXIOM", 1, [], "통과"), ("Custom", 1, ["vip"], "적용"), ("Standard", 3, [], "앞 규칙 우선")]
    assert p["source"] == {"rule": "vip", "layer": "custom", "layer_label": "Custom", "module": "acme",
                           "module_label": "ACME", "version": "0.1.0", "cite": ""} and p["layer"] == "custom"
    p = path({"age": 30, "grade": "A"})
    assert [x["said"] for x in p["layers"]] == ["통과", "해당 없음", "적용"] and p["source"]["rule"] == "out"
    p = path({"age": -1, "grade": "VIP"})
    assert p["layers"][0]["fired"] == ["negative"] and p["source"]["module_label"] == "법령 기준"
    assert p["text"].startswith("AXIOM negative 적용")


def test_a_single_definition_has_standard_rules_and_no_cards():
    o = compose([_shop()]).ontology
    view = semantic_view(Ontology.from_dict(o.to_dict()))
    assert [x["layer"] for x in view["layers"]] == list(LAYERS)
    assert [c["id"] for c in view["cards"]] == ["returnable#missing", "returnable#in", "returnable#out"]
    assert {c["layer"] for c in view["cards"]} == {"standard"} and view["checks"] == []


# ---- the example studio and the page --------------------------------------------------------------------------------

@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    return StudioSession(load_studio(SHOP))


def test_the_example_shows_all_three_layers(session):
    st = session.studio
    rules = st.onto.decisions["returnEligibility"].rules
    assert [(r.id, r.layer) for r in rules[:3]] == [("not-delivered", "axiom"), ("vip-window", "custom"), ("in-progress", "standard")]
    r = st.decide("returnEligibility", "I1001")
    assert r.matched == ["vip-window"] and r.path["text"] == "AXIOM 통과 › Custom vip-window 적용 › Standard 앞 규칙 우선"
    r = st.decide("returnEligibility", "I1005")
    assert r.outputs == {"eligible": False, "reason": "배송 완료 전입니다"} and r.path["source"]["module"] == "commerce-law"
    assert st.decide("returnEligibility", "I1003").path["source"]["layer"] == "standard"
    assert r.to_dict()["path"]["layer"] == "axiom"


def test_semantic_state_for_the_page(session):
    s = session.semantic_state()
    json.dumps(s)
    assert [(x["layer"], x["label"]) for x in s["layers"]] == [("axiom", "AXIOM"), ("custom", "Custom"), ("standard", "Standard")]
    assert s["layers"][0]["modules"][0]["label"] == "법령 기준 (예시)" and s["layers"][0]["cards"] == 4
    cards = {c["id"]: c for c in s["cards"]}
    law = cards["law-return-min-days"]
    assert (law["kind"], law["type_label"], law["layer_label"], law["status_label"], law["legal_review_label"]) == \
        ("stated", "판정", "AXIOM", "승인", "검토 완료")
    assert law["implements"][0] == {"ref": "decision:returnEligibility#in-window", "kind": "decision",
                                    "label": "반품 가능 여부 · in-window", "found": True}
    row = cards["returnEligibility#in-window"]
    assert row["kind"] == "executable" and row["layer"] == "standard" and row["module"] == "commerce"
    assert row["conditions"] == ["배송 완료 일시 경과일 7일 이하"] and row["params"] == {"return_window_days": 7}
    assert row["result"] == "가능 · 배송 완료 후 반품기간 7일 이내입니다" and row["status"] == "approved"
    assert {u["ref"] for u in row["used_by"]} == {"action:requestReturn", "card:law-return-min-days"}
    assert cards["returnEligibility#not-delivered"]["legal_review"] == "done"  # from the card that records it
    assert {c["type"] for c in s["cards"]} >= {"decide", "compute", "transition", "display"}
    window = next(p for p in s["parameters"] if p["name"] == "return_window_days")
    assert window["axiom"] == {"min": 7, "max": None, "cards": ["law-return-min-days"]} and window["min"] == 1
    assert s["checks"][0]["passed"] is True and s["violations"] == [] and not s["workspace"]["dirty"]


def test_a_value_an_axiom_bounds_is_refused_on_the_page_in_its_words(session):
    with pytest.raises(ValueError) as e:
        session.manage_edit("update_parameter", {"name": "return_window_days", "value": 5})
    assert str(e.value) == ("반품 기간 값은 AXIOM 규칙 law-return-min-days에 따라 7 이상이어야 하므로 저장하지 못했습니다. "
                            "관리 변경에서 5(으)로 정한 값입니다.")
    assert not session.manage_state()["workspace"]["dirty"]
    session.manage_edit("update_parameter", {"name": "return_window_days", "value": 10})  # longer is fine
    s = session.semantic_state()
    assert s["checks"][0]["value"] == 10 and s["checks"][0]["set_by_label"] == "관리 변경"
    row = next(c for c in s["cards"] if c["id"] == "returnEligibility#in-window")
    assert row["pending"] and row["result"] == "가능 · 배송 완료 후 반품기간 10일 이내입니다"  # the reason says the value
    assert row["conditions"] == ["배송 완료 일시 경과일 10일 이하"]
    session.manage_discard()
    # with the AXIOM module off, 5 is a customer's choice; putting the module back on is then refused
    assert session.detach("commerce-law")["ok"]
    session.manage_edit("update_parameter", {"name": "return_window_days", "value": 5})
    assert session.manage_propose()["change"]["status"] == "approved"
    out = session.attach("commerce-law")
    assert not out["ok"] and out["error"] == ("반품 기간 값은 AXIOM 규칙 law-return-min-days에 따라 7 이상이어야 하므로 "
                                              "적용하지 못했습니다. 관리 변경에서 5(으)로 정한 값입니다.")


def test_axiom_rules_are_not_edited_moved_or_removed_on_the_page(session):
    d = next(x for x in session.manage_state()["decisions"] if x["name"] == "returnEligibility")
    assert [(r["id"], r["layer"]) for r in d["rules"][:2]] == [("not-delivered", "axiom"), ("vip-window", "custom")]
    said = "AXIOM 규칙 'not-delivered'은(는) 여기서 바꾸거나 옮기거나 지울 수 없습니다."
    for op, args in (("update_rule", {"when": {}, "then": {"eligible": True}}), ("delete_rule", {}), ("move_rule", {"to": 3})):
        with pytest.raises(ValueError) as e:
            session.manage_edit(op, {"decision": "returnEligibility", "id": "not-delivered", **args})
        assert str(e.value) == said
    session.manage_edit("move_rule", {"decision": "returnEligibility", "id": "in-window", "to": 0})
    order = [r["id"] for x in session.manage_state()["decisions"] if x["name"] == "returnEligibility" for r in x["rules"]]
    assert order[:3] == ["not-delivered", "in-window", "vip-window"]  # the AXIOM rule stays first
    sim = session.simulate("returnEligibility", "I1001")
    assert sim["pending"] and sim["matched"] == ["in-window"] and sim["layer"] == "custom"  # the workspace wrote it now
    assert [x["said"] for x in sim["path"]["layers"]] == ["통과", "적용", "해당 없음"]
    assert sim["path"]["source"]["module_label"] == session._ws().module.label
    with pytest.raises(ValueError, match="AXIOM 규칙 'not-delivered'이\\(가\\) 있어"):
        session.manage_edit("delete_property", {"object": "OrderItem", "name": "delivered_at"})


def test_custom_rule_cards_are_added_changed_and_removed_on_the_page(session):
    card = {"id": "acme-gift-wrap", "type": "display", "statement": "선물 포장 주문은 영수증에 가격을 표시하지 않습니다.",
            "applies_to": ["property:OrderItem.gift_wrap"], "owner": "고객경험팀", "status": "review",
            "implements": ["property:OrderItem.gift_wrap"]}
    session.manage_edit("add_rule_card", card)
    s = session.semantic_state()
    mine = next(c for c in s["cards"] if c["id"] == "acme-gift-wrap")
    assert mine["new"] and mine["pending"] and mine["layer"] == "custom" and mine["module"] == "workspace"
    assert not next(c for c in s["cards"] if c["id"] == "law-return-min-days")["pending"]
    assert s["workspace"]["dirty"]
    session.manage_edit("update_rule_card", {"id": "acme-gift-wrap", "status": "approved", "legal_review": "pending"})
    session.manage_edit("update_rule_card", {"id": "acme-vip-window", "owner": "VIP 운영팀"})  # another customer's card
    cards = {c["id"]: c for c in session.semantic_state()["cards"]}
    assert cards["acme-gift-wrap"]["status"] == "approved" and cards["acme-vip-window"]["owner"] == "VIP 운영팀"
    assert cards["acme-vip-window"]["module"] == "acme-overlay" and cards["acme-vip-window"]["pending"]
    session.manage_edit("delete_rule_card", {"id": "acme-vip-window"})
    session.manage_edit("delete_rule_card", {"id": "acme-gift-wrap"})
    s = session.semantic_state()
    assert "acme-vip-window" in s["removed"] and not any(c["id"] == "acme-gift-wrap" for c in s["cards"])
    refusals = [
        ("update_rule_card", {"id": "law-return-min-days", "status": "draft"},
         "규칙 카드 'law-return-min-days'은(는) AXIOM 규칙이라 여기서 바꾸거나 지우지 못했습니다. Custom 규칙 카드만 바꿀 수 있습니다."),
        ("delete_rule_card", {"id": "return-request-moves"},
         "규칙 카드 'return-request-moves'은(는) Standard 규칙이라 여기서 바꾸거나 지우지 못했습니다. Custom 규칙 카드만 바꿀 수 있습니다."),
        ("add_rule_card", {**card, "id": "law-return-min-days"},
         "규칙 카드 'law-return-min-days'이(가) 이미 있어 추가하지 못했습니다. 다른 번호를 입력해 주세요."),
        ("add_rule_card", {**card, "type": "guess"},
         "규칙 카드 'acme-gift-wrap'의 유형 'guess'은(는) 쓸 수 없습니다. 판정, 계산, 전이, 복원, 순서, 표시, 감시 중에서 골라 주세요."),
        ("add_rule_card", {**card, "layer": "axiom"},
         "여기서 만드는 규칙 카드는 Custom 규칙입니다. 계층을 Custom으로 두고 다시 저장해 주세요."),
        ("update_rule_card", {"id": "nope"}, "규칙 카드 'nope'을(를) 찾지 못했습니다. 화면을 새로고침해 주세요.")]
    for op, args, said in refusals:
        with pytest.raises(ValueError) as e:
            session.manage_edit(op, args)
        assert str(e.value) == said


def test_a_filed_card_goes_with_its_module_and_the_export_still_works(session):
    session.manage_edit("add_rule_card", {"id": "acme-note", "type": "watch", "statement": "반품률을 매주 확인합니다.",
                                          "implements": ["metric:returnRate"]})
    assert session.manage_propose()["change"]["status"] == "approved"
    card = next(c for c in session.studio.composition.cards if c["id"] == "acme-note")
    assert card["module"] == "workspace" and card["layer"] == "custom"
    assert "acme-note" in session.export_module("workspace")
    assert "@prefix" in session.export_owl()


def test_decide_and_rules_say_the_layer(session):
    d = session.decide("returnEligibility", "I1005")
    assert d["layer"] == "axiom" and d["path"]["source"]["module_label"] == "법령 기준 (예시)"
    assert next(r for r in d["rules"] if r["id"] == "not-delivered")["layer"] == "axiom"
    sim = session.simulate("returnEligibility", "I1001")
    assert sim["layer"] == "custom" and sim["path"]["source"]["rule"] == "vip-window" and not sim["pending"]


def test_a_rule_and_its_table_take_an_owner_and_a_status_on_the_page(session):
    rule = next(r for r in session.studio.onto.decisions["returnEligibility"].rules if r.id == "in-window")
    session.manage_edit("update_rule", {"decision": "returnEligibility", "id": "in-window", "when": dict(rule.when),
                                        "then": dict(rule.then), "cite": rule.cite, "owner": "고객경험팀", "status": "review"})
    session.manage_edit("update_decision", {"decision": "returnEligibility", "owner": "반품운영팀", "status": "approved"})
    d = next(x for x in session.manage_state()["decisions"] if x["name"] == "returnEligibility")
    r = next(x for x in d["rules"] if x["id"] == "in-window")
    assert (d["owner"], d["status"], r["owner"], r["status"], r["layer"]) == ("반품운영팀", "approved", "고객경험팀", "review", "custom")
    card = next(c for c in session.semantic_state()["cards"] if c["id"] == "returnEligibility#in-window")
    assert (card["owner"], card["status_label"], card["module"]) == ("고객경험팀", "검토 중", "workspace")
    with pytest.raises(ValueError) as e:
        session.manage_edit("update_decision", {"decision": "returnEligibility", "status": "done"})
    assert str(e.value) == "상태 'done'은(는) 쓸 수 없습니다. 초안, 검토 중, 승인 중에서 골라 주세요."


def test_the_command_line_shows_the_checks_and_the_layers(capsys):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.cli import main

    assert main(["modules", str(SHOP), "--check"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["issues"] == [] and out["checks"][0]["card"] == "law-return-min-days"
    assert main(["modules", str(SHOP), "--rules"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [x["layer"] for x in out["layers"]] == list(LAYERS) and any(c["kind"] == "executable" for c in out["cards"])


def test_a_rule_sentence_says_the_value_in_force_not_its_placeholder():
    from ontlas.config import load_studio
    from ontlas.decide.words import rule_sentence

    st = load_studio(SHOP)
    table = st.onto.decisions["returnEligibility"]
    said = rule_sentence(st.onto, table, next(r for r in table.rules if r.id == "in-window"))
    assert "{@" not in said and "7일" in said  # the search index and answers read the sentence
