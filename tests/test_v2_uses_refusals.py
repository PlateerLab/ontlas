"""What the delete screens are told before anything is asked, and the same checks on the request: the parts of the
validation flow that read an item (a delete cannot take them out with it), the tables that read a Relation by its
inverse name, the column a Mapping set back to its default would read, and the sentence a deploy that does not pass
is refused with. A save that changes nothing is refused like any other."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"
RESET = {"column": "", "transform": "", "source_type": ""}  # what the Mapping delete screen sends


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import routes
    from ontlas.web.api import StudioSession

    routes.load()
    return StudioSession(load_studio(SHOP))


def call(method: str, route: str, s, a: dict | None = None):
    from ontlas.web import routes

    return routes.find(method, route)(s, a or {}, None)


def uses(s, el: str) -> dict:
    return {g["kind"]: g["names"] for g in call("GET", "item/uses", s, {"element": el})["uses"]}


def test_the_routes_are_registered_with_what_they_need():
    from ontlas.web import routes
    from ontlas.web.team import NEEDS

    routes.load()
    assert routes.find("POST", "item/try") and routes.find("GET", "bnd/reset") and NEEDS["item/try"] == "viewer"


def test_what_the_validation_flow_reads_is_a_use_of_it(session):
    s = session
    assert uses(s, "function:soldOut") == {"검증 흐름": ["거래 값 대조 · 품절"]}
    assert uses(s, "query:pastReturnCases") == {"검증 흐름": ["판정 일치율"]}
    assert uses(s, "decision:shippingFee")["검증 흐름"] == ["거래 값 대조 · 배송비"]
    assert "거래 값 대조 · 품절" in uses(s, "property:Sku.stock")["검증 흐름"]  # what the function's expression reads
    assert uses(s, "property:Sku.size") == {}  # read by nothing the flow names
    # an Entity whose rows a value reads: a Sku is read with what its computed prices reach
    price = uses(s, "object:PriceChange")
    assert "거래 값 대조 · 판매가" in price["검증 흐름"] and price["질의"] == ["단품별 판매가 변화"]
    group = next(g for g in call("GET", "item/uses", s, {"element": "function:soldOut"})["uses"] if g["kind"] == "검증 흐름")
    assert group["screen"] == "flow"


def test_a_stage_switched_off_reads_nothing(session):
    s = session
    s.save_flow({**s.studio.own_flow.to_dict(), "off": ["check", "decide"]})
    assert uses(s, "function:soldOut") == {} and uses(s, "query:pastReturnCases") == {}
    assert s.manage_edit("delete_function", {"name": "soldOut"})["ok"]


def test_a_delete_the_flow_would_fail_on_is_refused_before_it_is_filed(session):
    s = session
    with pytest.raises(ValueError) as e:
        s.manage_edit("delete_function", {"name": "soldOut"})
    assert str(e.value) == ("검증 흐름 거래 값 대조 · 품절이 함수 품절 여부를 읽고 있어 삭제하지 못했습니다. "
                            "검증 화면의 통과 조건 편집에서 거래 값 대조 · 품절을 먼저 바꿔 주세요.")
    with pytest.raises(ValueError, match="검증 흐름 판정 일치율이 질의 지난 반품 처리를 읽고 있어 삭제하지 못했습니다"):
        s.manage_edit("delete_query", {"name": "pastReturnCases"})
    # what a delete leaves broken goes with it, and a function the flow names is no exception
    with pytest.raises(ValueError, match="거래 값 대조 · 품절이 읽는 함수 품절 여부가 함께 빠져 삭제하지 못했습니다"):
        s.manage_edit("delete_property", {"object": "Sku", "name": "stock"})
    assert not s._ws().dirty  # nothing of a refused delete stays in the request being written
    assert s.manage_edit("delete_property", {"object": "Sku", "name": "size"})["ok"]


def test_the_delete_screen_is_told_the_same_before_it_asks(session):
    s = session
    tried = call("POST", "item/try", s, {"edits": [["delete_function", {"name": "soldOut"}]]})
    assert tried["ok"] is False and tried["error"].startswith("검증 흐름 거래 값 대조 · 품절이")
    gone = call("POST", "item/try", s, {"edits": [["delete_object", {"name": "PriceChange"}]]})
    assert gone["ok"] and "질의 단품별 판매가 변화" in gone["took_out"] and "Property 단품 · 최초 판매가" in gone["took_out"]
    assert not s._ws().dirty  # trying keeps nothing
    with pytest.raises(ValueError, match="확인할 편집이 없어"):
        call("POST", "item/try", s, {"edits": []})


def test_a_relation_read_by_its_inverse_name_lists_the_table_that_keeps_it(session):
    """returnEligibility reads the customer's grade through [itemOf, placedBy]: placedBy is placed read backwards."""
    s = session
    placed = uses(s, "link:placed")
    assert "반품 가능 여부" in placed["규칙"] and {"고객 · 주문 수", "고객 · 구매 금액"} <= set(placed["계산 Property"])
    tried = call("POST", "item/try", s, {"edits": [["delete_link", {"name": "placed"}]]})
    assert tried["ok"] is False and "결정표 '반품 가능 여부'" in tried["error"] and "returnEligibility" not in tried["error"]
    with pytest.raises(ValueError, match="AXIOM 규칙 'not-delivered'가 든 결정표 '반품 가능 여부'"):
        s.manage_edit("delete_link", {"name": "placed"})
    # a Property is read by the tables whose inputs reach its own Entity, not by any with a Property of that name
    assert uses(s, "property:Customer.grade") == {"검증 흐름": ["판정 일치율"], "규칙": ["반품 가능 여부"]}


def test_a_mapping_set_back_to_a_column_the_table_lacks_is_refused(session):
    s = session
    out = call("GET", "bnd/reset", s, {"element": "property:Coupon.discount_percent"})
    said = ("되돌아갈 컬럼 coupons.discount_percent가 데이터 소스에 없어 쿠폰 · 할인율의 Mapping을 기본값으로 되돌리지 못했습니다. "
            "삭제 대신 Mapping을 편집해 coupons 테이블에 있는 컬럼으로 바꿔 주세요.")
    assert out["connected"] and out["reverts"] == [{"table": "coupons", "column": "discount_percent", "exists": False}]
    assert out["error"] == said
    with pytest.raises(ValueError) as e:
        s.manage_edit("update_property", {"object": "Coupon", "name": "discount_percent", **RESET})
    assert str(e.value) == said
    fine = call("GET", "bnd/reset", s, {"element": "property:Coupon.discount_rate"})
    assert fine["reverts"] == [{"table": "coupons", "column": "discount_rate", "exists": True}] and fine["error"] == ""
    assert call("GET", "bnd/reset", s, {"element": "property:Sku.first_price"})["reverts"] == []  # computed: no Mapping
    with pytest.raises(LookupError):
        call("GET", "bnd/reset", s, {"element": "property:Coupon.nothing"})


def test_a_binding_whose_rows_the_flow_reads_is_not_taken_off(session):
    s = session
    out = call("GET", "bnd/reset", s, {"element": "object:PriceChange"})
    assert out["reverts"] == [] and out["error"].startswith("검증 흐름 거래 값 대조 · 판매가가 판매가 변경 이력의 행을 읽고 있어 Binding을 해제하지 못했습니다.")
    with pytest.raises(ValueError, match="Binding을 해제하지 못했습니다"):
        s.manage_edit("update_object", {"name": "PriceChange", "table": ""})


def test_a_table_bound_only_in_the_edits_being_written_can_be_taken_off_again(session):
    s = session
    s.manage_edit("update_object", {"name": "Party", "table": "customers"})
    s.manage_edit("update_object", {"name": "Party", "table": ""})  # back to what is in use: nothing to refuse
    assert not next(o for o in s.manage_state()["objects"] if o["name"] == "Party").get("table")


def test_with_no_source_a_column_cannot_be_judged(tmp_path):
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import routes
    from ontlas.web.api import StudioSession

    from .test_no_source import _no_backend

    routes.load()
    s = StudioSession(load_studio(_no_backend(tmp_path)))
    assert s.studio.composition is not None
    s.manage_edit("update_object", {"name": "Coupon", "table": "coupons"})
    s.manage_edit("update_property", {"object": "Coupon", "name": "discount_percent", "column": "discount_rate"})
    out = call("GET", "bnd/reset", s, {"element": "property:Coupon.discount_percent"})
    assert out["connected"] is False and out["reverts"] == [] and out["error"] == ""
    assert s.manage_edit("update_property", {"object": "Coupon", "name": "discount_percent", **RESET})["ok"]


def _refused(s, edits) -> str:
    for op, args in edits:
        s.manage_edit(op, args)
    out = s.manage_propose()
    assert out["ok"] is False
    return out["error"]


def test_a_deploy_that_does_not_pass_says_which_request_which_item_and_which_check(session):
    said = _refused(session, [("update_function", {"name": "soldOut", "expr": "stock > 0"})])
    assert said == ("변경 요청 C1의 함수 품절 여부 변경으로 검증 흐름 거래 값 대조 · 품절이 통과 조건 거래 값 오류 최대를 충족하지 못해 "
                    "승인하지 못했습니다. 이 변경을 되돌리거나 정의를 수정해 다시 요청해 주세요.")


def test_a_deploy_names_the_questions_and_the_past_cases_that_fail(session):
    from ontlas.config import load_studio
    from ontlas.web.api import StudioSession

    said = _refused(session, [("update_property", {"object": "Category", "name": "returnable", "column": "category_id"})])
    assert "Property 카테고리 · 반품 가능 카테고리 변경으로 검증 질문 Q2" in said and "검증 질문 정답률 최소" in said
    said = _refused(StudioSession(load_studio(SHOP)), [("update_property", {"object": "ReturnCase", "name": "status_then", "column": "case_id"})])
    assert "그때 주문상품 상태 변경으로 검증 흐름 판정 일치율이 통과 조건 판정 일치율 최소" in said


def test_a_trial_that_cannot_read_the_source_says_the_column_not_the_engine(session):
    s = session
    said = _refused(s, [("update_property", {"object": "Coupon", "name": "discount_percent", "column": "discount_pct"})])
    assert said == ("변경 요청 C1의 쿠폰 · 할인율이 읽는 컬럼 coupons.discount_pct가 데이터 소스에 없어 승인하지 못했습니다. "
                    "Mapping에서 coupons 테이블에 있는 컬럼으로 바꿔 다시 요청해 주세요.")
    assert "no such" not in said and "does not pass" not in said
    assert s.changes_state()["changes"][0]["issues"] == [said]  # the request's own screen says the same, not the engine


def test_a_request_decided_already_is_said_as_such(session):
    s = session
    s.manage_edit("update_function", {"name": "soldOut", "label": "품절"})
    change = s.manage_propose()["change"]
    out = s.decide_change(change["id"], True)
    assert out["ok"] is False and out["error"] == "변경 요청 C1은 이미 승인 · 적용 상태라 승인하지 못했습니다. 변경 요청 목록을 새로고침해 주세요."


def test_a_title_saved_unchanged_is_refused(session):
    s = session
    s.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    call("POST", "ont2/draft", s, {"title": "회원 표기 정리", "description": "고객을 회원으로 부릅니다"})
    with pytest.raises(ValueError, match="변경된 내용이 없어 저장하지 못했습니다"):
        call("POST", "ont2/draft", s, {"title": "회원 표기 정리", "description": "고객을 회원으로 부릅니다"})
    assert call("POST", "ont2/draft", s, {"title": "회원 표기 정리", "description": "설명만 바꿉니다"})["description"] == "설명만 바꿉니다"


def test_a_user_saved_unchanged_is_refused(session, tmp_path):
    from ontlas.web import routes
    from ontlas.web.areas import admin
    from ontlas.web.team import Logins, Users

    kept = dict(routes.SERVER)
    try:
        users = Users.load(tmp_path / "users.yaml")
        users.add("root1", "root-password-1", name="관리 하나", roles=["admin"])
        users.add("maker1", "maker-password-1", name="편집 하나", roles=["editor"])
        logins = Logins(Users.load(tmp_path / "users.yaml"))
        admin.bind(logins=logins)
        root, save = logins.users.users["root1"], routes.POST["admin/user/save"]
        same = {"id": "maker1", "name": "편집 하나", "roles": ["editor"], "password": "", "new": False}
        with pytest.raises(ValueError, match="변경된 내용이 없어 저장하지 못했습니다"):
            save(session, same, root)
        save(session, {**same, "password": "maker-password-2"}, root)  # a new password is a change
        save(session, {**same, "roles": ["viewer", "editor"]}, root)
    finally:
        routes.SERVER.clear()
        routes.SERVER.update(kept)
