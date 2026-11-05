"""Table and code definitions: a studio drafted from the schema alone, and names and code values for any draft."""
import json

import pytest

from xgen_space.definitions import Definitions, from_sheets, read_definitions, schema_backend
from xgen_space.draft import Table, draft

from .conftest import EXAMPLE

DEFS = EXAMPLE.parent / "definitions"


def _defs() -> Definitions:
    out = None
    for f in ("테이블정의서.csv", "코드정의서.csv"):
        d = read_definitions((DEFS / f).read_bytes(), f)
        assert d is not None
        out = d if out is None else out.merge(d)
    return out


def test_definition_sheets_are_read_with_their_names_keys_references_and_codes():
    d = _defs()
    assert d.counts() == {"tables": 3, "columns": 12, "references": 2, "codes": 2, "code_values": 9}
    member = d.table("tb_member")  # names compare without case
    assert member.label == "회원" and member.primary_key == ["MEMBER_NO"]
    grade = member.column("GRADE_CD")
    assert grade.label == "회원등급(MB01)" and d.code_of(grade).label == "회원등급"  # the group named in the label
    assert d.table("TB_ORDER_ITEM").primary_key == ["ORDER_NO", "ITEM_SEQ"]
    assert d.table("TB_ORDER").references == [{"columns": ["MEMBER_NO"], "table": "TB_MEMBER",
                                               "ref_columns": ["MEMBER_NO"]}]
    assert d.codes["OD01"].values[-1] == {"code": "99", "name": "구 주문상태", "use": False}
    back = Definitions.from_dict(json.loads(json.dumps(d.to_dict())))
    assert back.counts() == d.counts() and back.codes["OD01"].values[-1]["use"] is False


def test_other_header_names_a_nullable_flag_and_a_type_with_its_length():
    sheet = Table("cols", ["Table Name", "Column Name", "Attribute", "Data Type", "Nullable", "PK"],
                  [["orders", "id", "번호", "varchar(20)", "N", "Y"], ["orders", "memo", "메모", "text", "Y", ""]])
    d = from_sheets([sheet])
    cols = d.table("orders").columns
    assert (cols[0].type, cols[0].length, cols[0].required, cols[0].pk) == ("varchar", 20, True, True)
    assert not cols[1].required and from_sheets([Table("x", ["a", "b"], [["1", "2"]])]) is None


def test_json_definitions_take_the_usual_synonyms():
    d = Definitions.from_dict({"tables": [{"table": "T_A", "logical": "가", "columns": [
        {"name": "A_NO", "logical": "가 번호", "pk": True, "not_null": True},
        {"name": "B_NO", "code_group": "G1"}], "fks": [{"columns": ["B_NO"], "ref_table": "T_B"}]}],
        "codes": {"G1": {"name": "그룹", "values": [{"code": 1, "name": "하나", "use": "N"}]}}})
    t = d.table("T_A")
    assert t.label == "가" and t.primary_key == ["A_NO"] and t.columns[1].code == "G1"
    assert t.references == [{"columns": ["B_NO"], "table": "T_B", "ref_columns": []}]
    assert d.codes["G1"].values == [{"code": "1", "name": "하나", "use": False}]


def test_a_studio_is_drafted_from_the_schema_alone():
    pytest.importorskip("yaml")
    from xgen_space.modules import compose

    d = _defs()
    dr = draft(schema_backend(d), name="shop", lang="ko", definitions=d)
    objs = {o.name: o for o in dr.objects}
    assert set(objs) == {"Member", "Order", "OrderItem"}  # the tb_ prefix is left out of the names
    assert dr.skipped == []
    assert next(p for p in objs["OrderItem"].properties if p.name == objs["OrderItem"].key).columns == [
        "ORDER_NO", "ITEM_SEQ"]
    assert objs["Order"].label == "주문" and objs["Member"].key == "member_no"
    stat = objs["Order"].prop_of("ORDER_STAT_CD")
    assert stat.type == "enum" and stat.values[:2] == ["10", "20"] and stat.labels["90"] == "주문취소"
    assert objs["Member"].prop_of("GRADE_CD").label == "회원등급"  # the group's mark is left out of the name
    assert sorted((lk.source, lk.target, lk.on) for lk in dr.links) == [
        ("Order", "Member", ("member_no", "member_no")), ("OrderItem", "Order", ("order_no", "order_no"))]
    assert [s.property for s in dr.states] == ["order_stat_cd"]
    comp = compose(dr.modules(), name="shop")
    assert comp.issues == []
    assert comp.ontology.objects["Order"].properties["order_stat_cd"].labels["10"] == "주문접수"


def test_value_labels_are_part_of_the_definition():
    from xgen_space import Ontology
    from xgen_space.validate import validate_ontology

    o = Ontology.from_dict({"name": "t", "namespace": "https://example.org/t#", "objects": {"Order": {
        "key": "id", "properties": {"id": "string", "status": {"type": "enum", "values": {"10": "접수", "20": "완료"}},
                                    "kind": {"type": "enum", "values": ["A"], "labels": {"A": "가", "B": "나"}}}}}})
    p = o.objects["Order"].properties["status"]
    assert p.values == ["10", "20"] and p.labels == {"10": "접수", "20": "완료"}
    assert o.to_dict()["objects"]["Order"]["properties"]["status"]["labels"] == {"10": "접수", "20": "완료"}
    assert any("labels for values it does not allow" in x for x in validate_ontology(o))


def test_an_extension_adds_names_to_the_names_already_given():
    pytest.importorskip("yaml")
    from xgen_space.modules import Module, compose

    base = Module.from_dict({"module": "a", "version": "1.0.0", "kind": "domain", "objects": {"Order": {
        "key": "id", "properties": {"id": "string", "status": {"type": "enum", "values": {"10": "접수"}}}}}})
    ext = Module.from_dict({"module": "b", "version": "1.0.0", "kind": "customer", "requires": ["a"],
                            "extend": {"objects": {"Order": {"properties": {
                                "status": {"values_add": {"20": "완료"}, "labels": {"10": "주문 접수"}}}}}}})
    p = compose([base, ext], namespace="https://example.org/t#").ontology.objects["Order"].properties["status"]
    assert p.values == ["10", "20"] and p.labels == {"10": "주문 접수", "20": "완료"}


def test_the_page_drafts_from_uploaded_definitions():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web.api import StudioSession

    s = StudioSession(load_studio(EXAMPLE.parent / "library" / "studio.yaml"))
    for f in ("테이블정의서.csv", "코드정의서.csv"):
        st = s.upload(f, (DEFS / f).read_bytes())
    assert st["files"] == [] and [x["source"] for x in st["definitions"]] == ["테이블정의서.csv", "코드정의서.csv"]
    assert st["definitions"][0]["tables"][2] == {"name": "TB_ORDER_ITEM", "label": "주문상품", "columns": 4,
                                                 "key": ["ORDER_NO", "ITEM_SEQ"]}
    with pytest.raises(ValueError, match="tables 또는 codes"):
        s.upload("x.json", b'{"other": 1}')
    st = s.make_draft("쇼핑몰")
    assert st["pending"]["origin"]["kind"] == "definitions" and st["pending"]["counts"]["objects"] == 3
    s.apply_draft()
    onto = s.studio.onto
    assert onto.objects["Order"].label == "주문" and onto.objects["Order"].properties["order_stat_cd"].labels
    prop = next(p for p in s.manage_state()["properties"] if p["name"] == "order_stat_cd")
    assert prop["labels"]["40"] == "배송완료"
