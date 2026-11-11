"""Areas, the level above the object types: read and written back, checked, plugged in and out with their module,
edited from the management screens, shown with each type's level, and exchanged as SKOS collections."""
import json
from pathlib import Path

import pytest

from ontlas.bindings import entity_level
from ontlas.model import Ontology
from ontlas.modules import Module, ModuleError, compose, removal_impact

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "examples" / "library"
NS = "https://example.org/t#"
SHOP = ["core", "commerce", "commerce-bindings", "commerce-operations", "commerce-operations-bindings", "fashion",
        "acme-overlay"]
KW = {"namespace": "https://example.org/studio#", "name": "studio"}


def _definition() -> dict:
    return {"ontology": "t", "namespace": NS, "version": "0.1.0",
            "areas": {"Order": {"label": "주문", "description": "주문과 주문상품", "cite": "용어집 2장",
                                "aligned": ["https://schema.org/Order"]},
                      "Cart": {"label": "장바구니", "status": "draft"}},
            "objects": {"Order": {"label": "주문", "area": "Order", "key": "order_id",
                                  "properties": {"order_id": {"type": "string"}}},
                        "Note": {"key": "note_id", "properties": {"note_id": {"type": "string"}}}}}


def test_areas_are_read_and_written_back(tmp_path, onto):
    pytest.importorskip("yaml")
    d = _definition()
    o = Ontology.from_dict(d)
    assert o.validate() == []
    assert o.areas["Order"].label == "주문" and o.areas["Order"].aligned == ["https://schema.org/Order"]
    assert o.areas["Cart"].status == "draft" and o.areas["Order"].status == "active"
    assert o.objects["Order"].area == "Order" and o.objects["Note"].area == ""
    assert o.to_dict() == d  # nothing added: an unclassified type has no area, an area in use has no status
    for name in ("t.yaml", "t.json"):
        o.dump(tmp_path / name)
        assert Ontology.load(tmp_path / name).to_dict() == d
    assert Ontology.from_dict({**d, "areas": {"Order": None}, "objects": {}}).areas["Order"].label == ""
    plain = onto.to_dict()  # a definition without areas is written as it always was
    assert "areas" not in plain and not any("area" in t for t in plain["objects"].values())


def test_an_area_has_to_be_there_be_named_as_a_type_is_and_have_a_status():
    d = _definition()
    d["objects"]["Note"]["area"] = "Memo"
    d["areas"]["Cart"]["status"] = "gone"
    d["areas"]["장바구니"] = {"label": "장바구니"}
    assert Ontology.from_dict(d).validate() == [
        "area Cart: status 'gone' is not one of ('draft', 'active', 'deprecated')",
        "area name '장바구니' is not an identifier",
        "Note: area 'Memo' is unknown"]
    assert "Order" in Ontology.from_dict(_definition()).areas  # an area and a type may share a name


def _mod(name, **kw):
    return Module.from_dict({"module": name, **kw})


def _base():
    return _mod("base", namespace=NS, areas={"Order": {"label": "주문"}},
                objects={"Order": {"key": "id", "area": "Order", "properties": {"id": "string"}}})


def test_a_module_defines_areas_and_files_types_under_them():
    base = _base()
    more = _mod("more", requires=["base"], areas={"Pay": {"label": "결제"}},
                extend={"objects": {"Order": {"area": "Pay"}}, "areas": {"Order": {"label": "주문 영역"}}})
    assert "area:Order" in base.elements() and base.counts()["areas"] == 1
    assert Module.from_dict(base.to_dict()).to_dict() == base.to_dict()
    comp = compose([base, more])
    assert comp.issues == []
    assert comp.owner("area:Order") == "base" and comp.owner("area:Pay") == "more"
    assert comp.touched["area:Order"] == ["more"] and comp.touched["object:Order"] == ["more"]
    assert comp.ontology.objects["Order"].area == "Pay" and comp.ontology.areas["Order"].label == "주문 영역"
    with pytest.raises(ModuleError, match="defines area 'Order', already defined by base"):
        compose([base, _mod("twice", requires=["base"], areas={"Order": {"label": "주문서"}})])
    with pytest.raises(ModuleError, match="extends area 'Ship', which no attached module defines"):
        compose([base, _mod("far", requires=["base"], extend={"areas": {"Ship": {"label": "배송"}}})])
    cut = compose([base, _mod("cut", requires=["base"], remove={"areas": ["Order"]})])
    assert cut.removed == {"area:Order": "cut"} and "area:Order" not in cut.origin
    assert cut.issues == [] and cut.ontology.objects["Order"].area == ""  # left unclassified, not broken


def test_detaching_the_module_of_an_area_leaves_its_types_unclassified():
    base = _base()
    cart = _mod("cart", namespace=NS, objects={"Cart": {"key": "id", "area": "Order", "properties": {"id": "string"}}})
    pay = _mod("pay", requires=["base"], areas={"Pay": {"label": "결제"}}, extend={"objects": {"Order": {"area": "Pay"}}})
    assert compose([base, cart]).ontology.objects["Cart"].area == "Order"
    imp = removal_impact([base, cart], "base")
    assert imp.ok and imp.removed == ["area:Order", "object:Order", "property:Order.id"]
    assert imp.changed == ["object:Cart"]  # the type stays and says it is no longer filed
    left = compose([cart])
    assert left.issues == [] and left.ontology.objects["Cart"].area == ""
    imp = removal_impact([base, pay], "pay")  # an area a module set by extension goes back to what it was
    assert imp.ok and imp.removed == ["area:Pay"] and imp.changed == ["object:Order"]
    assert compose([base]).ontology.objects["Order"].area == "Order"


@pytest.fixture
def shop():
    pytest.importorskip("yaml")
    from ontlas.library import Library

    return Library(LIB).resolve(SHOP)


def test_the_example_library_files_its_types_under_areas(shop):
    comp = compose(shop, **KW)
    o = comp.ontology
    assert comp.issues == []
    assert {a.name: [t.name for t in o.objects.values() if t.area == a.name] for a in o.areas.values()} == {
        "Customer": ["Customer"], "Product": ["Product", "Sku", "PriceChange"], "Category": ["Category"],
        "Order": ["Order", "OrderItem", "CheckoutRecord"], "Claim": ["Claim", "ReturnCase"],
        "Payment": ["Payment", "Refund"], "Shipment": ["Carrier", "Shipment"], "Seller": ["Seller"],
        "Promotion": ["Coupon"], "Review": ["Review"]}
    assert [a.label for a in o.areas.values()] == ["고객", "상품", "카테고리", "주문", "클레임", "결제", "배송", "판매자",
                                                  "프로모션", "리뷰"]
    assert all(a.description for a in o.areas.values()) and o.areas["Order"].aligned == ["https://schema.org/Order"]
    assert [t.name for t in o.objects.values() if not t.area] == ["Party", "Agreement"]  # the shared parents
    assert comp.owner("area:Order") == "commerce" and comp.owner("area:Payment") == "commerce-operations"
    imp = removal_impact(shop, "commerce-operations", cascade=True, **KW)
    assert imp.ok and {"area:Payment", "area:Shipment", "area:Seller", "area:Promotion", "area:Review"} <= set(imp.removed)
    assert "area:Order" not in imp.removed


@pytest.fixture
def ws(shop):
    from ontlas.manage import Workspace

    return Workspace(shop, compose_kw=KW)


def test_areas_are_added_changed_and_deleted_from_the_management_screens(ws):
    from ontlas.manage import EditError

    e = ws.apply("add_area", {"name": "Member", "label": "회원", "description": "회원과 등급",
                              "aligned": ["https://schema.org/Person"]})
    assert e.target == "area:Member" and e.took_out == []
    assert ws.module.body["areas"]["Member"] == {"label": "회원", "description": "회원과 등급",
                                                 "aligned": ["https://schema.org/Person"]}
    with pytest.raises(EditError, match="area 'Member' already exists"):
        ws.apply("add_area", {"name": "Member"})
    with pytest.raises(EditError, match="area 'Order' already exists"):  # a standard's area too
        ws.apply("add_area", {"name": "Order"})
    with pytest.raises(EditError, match="area name '회원' must be letters"):
        ws.apply("add_area", {"name": "회원"})
    with pytest.raises(EditError, match="status 'gone' is not one of"):
        ws.apply("add_area", {"name": "Late", "status": "gone"})
    ws.apply("update_area", {"name": "Member", "label": "멤버십", "description": ""})  # its own: changed in place
    assert ws.module.body["areas"]["Member"] == {"label": "멤버십", "aligned": ["https://schema.org/Person"]}
    ws.apply("update_area", {"name": "Order", "label": "주문 관리", "status": "deprecated"})  # a standard's: extended
    assert ws.module.extend["areas"]["Order"] == {"label": "주문 관리", "status": "deprecated"}
    area = ws.composed().ontology.areas["Order"]
    assert (area.label, area.status, area.aligned) == ("주문 관리", "deprecated", ["https://schema.org/Order"])
    assert ws.composed().touched["area:Order"] == ["workspace"] and "commerce" in [r.name for r in ws.module.requires]
    with pytest.raises(EditError, match="area 'Nope' is unknown"):
        ws.apply("update_area", {"name": "Nope", "label": "x"})
    with pytest.raises(EditError, match="area 'Nope' is unknown"):
        ws.apply("delete_area", {"name": "Nope"})
    with pytest.raises(EditError, match="area 'Product' holds PriceChange, Product, Sku"):
        ws.apply("delete_area", {"name": "Product"})
    ws.apply("update_object", {"name": "Category", "area": ""})
    e = ws.apply("delete_area", {"name": "Category"})  # a standard's area, once nothing is filed under it: removed
    assert e.target == "area:Category" and e.took_out == [] and ws.module.remove["areas"] == ["Category"]
    assert "Category" not in ws.composed().ontology.areas and ws.composed().issues == []
    ws.apply("delete_area", {"name": "Member"})  # its own: deleted outright
    assert "Member" not in ws.module.body["areas"] and "Member" not in ws.composed().ontology.areas
    assert [x.op for x in ws.edits] == ["add_area", "update_area", "update_area", "update_object", "delete_area",
                                        "delete_area"]  # refused edits change nothing


def test_a_type_is_filed_under_an_area_when_it_is_added_or_changed(ws):
    from ontlas.manage import EditError

    ws.apply("add_area", {"name": "Member", "label": "회원"})
    ws.apply("add_object", {"name": "Tier", "label": "등급", "key": "tier_id", "area": "Member",
                            "properties": {"tier_id": {"type": "string"}}})
    assert ws.module.body["objects"]["Tier"]["area"] == "Member"
    with pytest.raises(EditError, match="area 'Nope' is unknown"):
        ws.apply("add_object", {"name": "Lost", "key": "id", "area": "Nope", "properties": {"id": {"type": "string"}}})
    with pytest.raises(EditError, match="area 'Nope' is unknown"):
        ws.apply("update_object", {"name": "Customer", "area": "Nope"})
    e = ws.apply("update_object", {"name": "Customer", "area": "Member"})  # a standard's type: by extension
    assert e.target == "object:Customer" and ws.module.extend["objects"]["Customer"] == {"area": "Member"}
    onto = ws.composed().ontology
    assert onto.objects["Customer"].area == "Member" and onto.objects["Tier"].area == "Member"
    with pytest.raises(EditError, match="area 'Member' holds Customer, Tier"):
        ws.apply("delete_area", {"name": "Member"})
    ws.apply("update_object", {"name": "Tier", "area": ""})  # its own type: the area is taken off
    assert "area" not in ws.module.body["objects"]["Tier"]
    ws.apply("update_object", {"name": "Customer", "area": ""})  # a standard's type: unclassified by extension
    assert ws.composed().ontology.objects["Customer"].area == ""
    ws.apply("delete_area", {"name": "Member"})
    assert ws.composed().issues == [] and "Member" not in ws.composed().ontology.areas


def test_area_edits_are_taken_back_and_made_again(ws):
    from ontlas.manage import EditError

    def filed():
        o = ws.composed().ontology
        return sorted(o.areas), o.objects["Customer"].area, o.areas["Order"].label

    start = filed()
    ws.apply("add_area", {"name": "Member", "label": "회원"})
    ws.apply("update_object", {"name": "Customer", "area": "Member"})
    ws.apply("update_area", {"name": "Order", "label": "주문 관리"})
    ws.apply("update_object", {"name": "Category", "area": "Product"})
    ws.apply("delete_area", {"name": "Category"})
    done = filed()
    assert done == (["Claim", "Customer", "Member", "Order", "Payment", "Product", "Promotion", "Review", "Seller",
                     "Shipment"], "Member", "주문 관리")
    assert ws.undo().op == "delete_area" and "Category" in ws.composed().ontology.areas
    assert ws.undo().op == "update_object" and ws.composed().ontology.objects["Category"].area == "Category"
    assert ws.redo().op == "update_object" and ws.redo().op == "delete_area" and ws.redo() is None
    assert filed() == done
    with pytest.raises(EditError, match="object:Customer"):  # a later edit files a type under it: nothing changes
        ws.revert(0)
    assert filed() == done and len(ws.edits) == 5
    assert ws.revert(2).target == "area:Order"  # one edit from the middle, the later ones kept
    assert filed() == (done[0], "Member", "주문") and [e.op for e in ws.edits] == [
        "add_area", "update_object", "update_object", "delete_area"]
    while ws.edits:
        ws.undo()
    assert filed() == start and not ws.dirty


def _levels() -> Ontology:
    return Ontology.from_dict({"ontology": "t", "namespace": NS, "objects": {
        "Idea": {"label": "구상", "key": "id", "properties": {"id": "string"}},
        "Party": {"key": "party_id", "properties": {"party_id": "string", "name": "string"}},
        "Tag": {"key": "tag_id", "properties": {"tag_id": "string"}},
        "Shop": {"parent": "Party", "key": "shop_id", "source": {"table": "shops"},
                 "properties": {"shop_id": "string", "tag_id": {"type": "string", "column": "tag"},
                                "opened": {"type": "date", "format": "YYYYMMDD"},
                                "label_len": {"type": "integer", "expr": "length(name)"}}}},
        "links": {"tagged": {"from": "Shop", "to": "Tag", "cardinality": "many_to_one", "on": {"tag_id": "tag_id"}}}})


def test_the_level_of_a_type_goes_from_a_definition_to_a_checked_binding():
    o = _levels()
    assert o.validate() == []
    assert entity_level(o, "Idea") == 0  # a label and a key
    assert entity_level(o, "Party") == 1  # a property past its key
    assert entity_level(o, "Tag") == 1  # nothing past its key, but a relation reaches it
    assert entity_level(o, "Shop") == 2  # a table: each stored property reads the column it names
    held = {"shop_id", "name", "tag", "opened"}  # the parent's key and the computed property need no column
    assert entity_level(o, "Shop", columns=held) == 2
    assert entity_level(o, "Shop", columns={c.upper() for c in held}) == 1  # the source's columns come in lower case
    assert entity_level(o, "Shop", columns=held - {"tag"}) == 1  # a stored property with no column: not bound yet
    assert entity_level(o, "Shop", columns=held - {"opened"}) == 1  # a date kept as text reads its column too
    assert entity_level(o, "Shop", columns=held, found=set()) == 3  # measured, and nothing against it
    assert entity_level(o, "Shop", found={"property:Tag.tag_id", "object:Party"}) == 3  # findings on other types
    for against in ("object:Shop", "property:Shop.opened", "link:tagged"):
        assert entity_level(o, "Shop", columns=held, found={against}) == 2
    assert entity_level(o, "Tag", found=set()) == 1  # a check says nothing of a type with no table
    assert entity_level(o, "Shop", columns=held - {"tag"}, found=set()) == 1


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(load_studio(LIB / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))


def test_the_state_shows_areas_and_each_types_area_and_level(session):
    st = session.manage_state()
    json.dumps(st)
    areas = {a["name"]: a for a in st["areas"]}
    assert areas["Order"] == {
        "name": "Order", "label": "주문", "description": "주문과 주문에 담긴 주문상품", "cite": "",
        "aligned": ["https://schema.org/Order"], "status": "active", "objects": ["Order", "OrderItem", "CheckoutRecord"],
        "pending": False, "new": False, "module": "commerce", "module_label": "이커머스 표준 온톨로지"}
    assert list(areas) == ["Customer", "Product", "Category", "Order", "Claim", "Payment", "Shipment", "Seller",
                           "Promotion", "Review"]
    rows = {o["name"]: o for o in st["objects"]}
    assert (rows["Sku"]["area"], rows["Sku"]["area_label"]) == ("Product", "상품")
    assert (rows["Party"]["area"], rows["Party"]["area_label"]) == ("", "")
    assert (rows["Party"]["level"], rows["Party"]["level_label"]) == (1, "L1 논리")
    assert (rows["Order"]["level"], rows["Order"]["level_label"]) == (2, "L2 연결")  # bound; nothing was measured yet
    page = session.state()
    assert page["stats"]["areas"] == 10
    assert {n["id"]: n["area"] for n in page["graph"]["nodes"]}["CheckoutRecord"] == "Order"
    assert session._element_label("area:Order") == "Object 주문"


def test_a_level_reads_the_last_check_and_never_takes_one(session, monkeypatch):
    from ontlas import bindings

    def never(*a, **kw):
        raise AssertionError("the state took a database check")

    session.flow()  # the board's measurement: the session keeps it
    monkeypatch.setattr(bindings, "check_bindings", never)
    monkeypatch.setattr(session.studio, "check_bindings", never)
    rows = {o["name"]: o for o in session.manage_state()["objects"]}
    assert (rows["Order"]["level"], rows["Order"]["level_label"]) == (3, "L3 검증")
    assert rows["Party"]["level"] == 1 and {o["level"] for o in rows.values() if o["table"]} == {3}
    session._measured["bind"]["findings"] = [{"severity": "warning", "kind": "enum", "element": "property:Order.status"}]
    rows = {o["name"]: o for o in session.manage_state()["objects"]}
    assert rows["Order"]["level"] == 2 and rows["OrderItem"]["level"] == 3
    assert session.detach("fashion")["ok"]  # another definition: the check was not of it
    assert {o["level"] for o in session.manage_state()["objects"] if o["table"]} == {2}


def test_a_type_the_unsent_edits_change_is_not_spoken_for_by_the_last_check(session):
    session.flow()
    r = session.manage_edit("update_object", {"name": "Customer", "label": "회원"})
    rows = {o["name"]: o for o in r["objects"]}
    assert rows["Customer"]["level"] == 2 and rows["Order"]["level"] == 3
    r = session.manage_edit("add_property", {"object": "Order", "name": "memo", "type": "string", "label": "메모"})
    rows = {o["name"]: o for o in r["objects"]}
    assert (rows["Order"]["level"], rows["Order"]["level_label"]) == (1, "L1 논리")  # orders holds no memo column


def test_area_edits_are_said_in_korean_and_filed_as_one_change(session):
    with pytest.raises(ValueError, match=r"Entity PriceChange, Product, Sku이\(가\) Object 'Product'에 속해 있어 제외하지 못했습니다"):
        session.manage_edit("delete_area", {"name": "Product"})
    with pytest.raises(ValueError, match=r"Object 'Nope'을\(를\) 찾지 못했습니다"):
        session.manage_edit("update_object", {"name": "Customer", "area": "Nope"})
    with pytest.raises(ValueError, match=r"Object 'Order'이\(가\) 이미 있어 추가하지 못했습니다"):
        session.manage_edit("add_area", {"name": "Order"})
    with pytest.raises(ValueError, match="이름 '1x'은 영문자로 시작하고"):
        session.manage_edit("add_area", {"name": "1x"})
    with pytest.raises(ValueError, match=r"Object Late의 상태 'gone'은\(는\) 쓸 수 없어 저장하지 못했습니다"):
        session.manage_edit("add_area", {"name": "Late", "status": "gone"})
    r = session.manage_edit("add_area", {"name": "Member", "label": "회원", "description": "회원과 등급"})
    assert r["edit"] == {"op": "add_area", "target": "area:Member", "took_out": []}
    r = session.manage_edit("update_object", {"name": "Customer", "area": "Member"})
    r = session.manage_edit("update_area", {"name": "Order", "label": "주문 관리"})
    areas = {a["name"]: a for a in r["areas"]}
    assert areas["Member"]["new"] and not areas["Member"]["pending"] and areas["Member"]["objects"] == ["Customer"]
    assert (areas["Member"]["module"], areas["Member"]["module_label"]) == ("workspace", "관리 변경")
    assert areas["Order"]["pending"] and not areas["Order"]["new"] and areas["Order"]["label"] == "주문 관리"
    assert areas["Customer"]["objects"] == []
    row = next(o for o in r["objects"] if o["name"] == "Customer")
    assert (row["area"], row["area_label"], row["pending"]) == ("Member", "회원", True)
    assert r["workspace"]["diff"] == {"added": ["area:Member"], "removed": [], "changed": ["area:Order", "object:Customer"]}
    assert not session.studio.onto.areas.get("Member")  # nothing reaches the studio before approval
    r = session.manage_undo()
    assert {a["name"]: a["label"] for a in r["areas"]}["Order"] == "주문"
    r = session.manage_redo()
    assert {a["name"]: a["label"] for a in r["areas"]}["Order"] == "주문 관리"
    r = session.manage_propose()
    assert r["ok"] and r["change"]["status"] == "approved" and not r["workspace"]["dirty"]
    onto = session.studio.onto
    assert onto.areas["Member"].label == "회원" and onto.objects["Customer"].area == "Member"
    assert onto.areas["Order"].label == "주문 관리" and session._element_label("area:Member") == "Object 회원"
    assert session.impact("workspace")["removed"] == ["area:Member"]
    assert session.impact("workspace")["changed"] == ["area:Order", "object:Customer"]


def test_areas_are_exchanged_as_skos_collections(shop):
    rdflib = pytest.importorskip("rdflib")
    from ontlas.exchange.importer import from_owl
    from ontlas.exchange.owl import to_owl

    comp = compose(shop, **KW)
    ttl, rep = to_owl(comp.ontology, origin=comp.origin)
    g = rdflib.Graph().parse(data=ttl, format="turtle")
    ns, skos = rdflib.Namespace(comp.ontology.namespace), rdflib.Namespace("http://www.w3.org/2004/02/skos/core#")
    area = ns["area-Order"]  # the class Order keeps its own IRI
    assert (area, rdflib.RDF.type, skos.Collection) in g and (ns.Order, rdflib.RDF.type, skos.Collection) not in g
    assert set(g.objects(area, skos.member)) == {ns.Order, ns.OrderItem, ns.CheckoutRecord}
    assert str(g.value(area, skos.definition)) == "주문과 주문에 담긴 주문상품"
    assert (area, skos.exactMatch, rdflib.URIRef("https://schema.org/Order")) in g
    assert (area, rdflib.RDFS.isDefinedBy, rdflib.URIRef("urn:ontlas:module:commerce")) in g
    assert "area Order" in rep.preserved
    back, read = from_owl(ttl)
    assert read.summary()["unsupported"] == 0 and "area Order" in read.preserved
    assert {a.name: a.label for a in back.areas.values()} == {a.name: a.label for a in comp.ontology.areas.values()}
    assert back.areas["Order"].description == "주문과 주문에 담긴 주문상품"
    assert back.areas["Order"].aligned == ["https://schema.org/Order"]
    assert all(back.objects[t.name].area == t.area for t in comp.ontology.objects.values())
