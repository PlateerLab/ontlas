import pytest

from xgen_data_studio.backends.sql import SqliteBackend
from xgen_data_studio.draft import draft, load_sqlite, read_csv, studio_from
from xgen_data_studio.library import Library
from xgen_data_studio.modules import compose

from .conftest import EXAMPLE
from .test_draft import _files

LIB = EXAMPLE.parent / "library"


def _library_draft():
    b = SqliteBackend()
    return draft(b, loaded=load_sqlite(_files(), b), lang="ko"), b


def test_a_history_table_gives_the_state_machine_its_transitions():
    d, b = _library_draft()
    sm = next(s for s in d.states if s.object == "Daechul")
    assert sm.why == "history" and sm.history == "대출상태이력" and sm.initial == "대출중"
    assert sm.transitions == [("대출중", "반납", 23), ("대출중", "연체", 16), ("연체", "반납", 8)]
    hist = next(o for o in d.objects if o.table == "대출상태이력")
    assert hist.series == {"time": "byeongyeongilsi", "of": "daechul"} and not any(
        s.object == hist.name for s in d.states)  # the history is a series, not a second state machine
    assert set(d.actions()) == {"setDaechulBannap", "setDaechulYeonche"}


def test_roles_and_questions_come_with_the_draft_and_hold():
    pytest.importorskip("rdflib")
    d, b = _library_draft()
    roles = d.roles()
    assert set(roles) == {"my-data-viewer", "my-data-operator", "my-data-self"}
    assert roles["my-data-self"]["row_filters"]["Daechul"] == {"eq": ["$self.hoewonbeonho",
                                                                       {"principal": "hoewonbeonho"}]}
    st = studio_from(d, b)
    rows = st.run("listDaechul", role="my-data-self", principal={"hoewonbeonho": "M003"}).rows
    assert rows and all(r[1] == "M003" for r in rows)
    rep = st.questions()
    assert len(rep.results) == len(d.questions()) == 12 and rep.accuracy == 1.0
    from xgen_data_studio.actions import Actor

    op = Actor("op", "human", ["my-data-operator"])
    p = st.actions.request("setDaechulBannap", "L0002", {}, actor=op)
    assert p.status == "pending"  # 연체 -> 반납 is a transition the history shows; a person approves it
    st.actions.approve(p.id, approver=op)
    assert p.status == "executed" and st.fetch("Daechul", "L0002")["sangtae"] == "반납"
    p = st.actions.request("setDaechulYeonche", "L0001", {}, actor=op)
    assert p.status == "rejected"  # 반납 -> 연체 never happened, so the machine refuses it
    off = draft(b, loaded=d.loaded, lang="ko", rules=d.rules.from_dict({"states": False, "roles": False,
                                                                         "questions": False}))
    assert not off.states and not off.roles() and not off.questions()


def test_a_decision_table_is_drawn_from_past_outcomes_with_its_accuracy():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_data_studio.config import load_studio
    from xgen_data_studio.induce import InduceError, induce

    st = load_studio(LIB / "studio.yaml")
    out = induce(st.backend(), st.onto, "ReturnCase.approved",
                 ["days_after_delivery", "status_then", "returnable_then", "grade_then"])
    rep, table = out["report"], out["decision"]
    assert rep["cases"] == 10 and 0 < rep["accuracy"] <= 1 and rep["cross_validated"] is not None
    assert table["rules"][-1]["id"] == "otherwise" and table["outputs"] == {"approved": "boolean"}
    assert all(r["note"] for r in table["rules"])
    with pytest.raises(InduceError, match="the result itself"):
        induce(st.backend(), st.onto, "ReturnCase.approved", ["approved"])
    with pytest.raises(InduceError, match="allowed-value or true/false"):
        induce(st.backend(), st.onto, "ReturnCase.days_after_delivery", ["grade_then"])
    # an input one relation away: the 회원 grade decides a 대출's state, through the loan's member
    d, b = _library_draft()
    lib = studio_from(d, b)
    got = induce(b, lib.onto, "Daechul.sangtae", ["hoewon.deunggeup", "doseo.bunryu"])
    assert got["decision"]["inputs"]["hoewon_deunggeup"]["path"] == ["hoewon"]
    assert got["report"]["cases"] == 40


def test_tables_are_matched_onto_the_standard_the_way_a_person_bound_them():
    pytest.importorskip("yaml")
    from xgen_data_studio.mapping import binding, suggest

    b = SqliteBackend()
    b.script((EXAMPLE / "seed.sql").read_text(encoding="utf-8"))
    d = draft(b, name="shop")
    std = Library(LIB).resolve(["commerce"])
    onto = compose(std, namespace="https://example.org/studio#").ontology
    s = suggest(d, onto, ["commerce"])
    assert {m.object: m.table for m in s.objects} == {
        "Customer": "customers", "Order": "orders", "OrderItem": "order_items", "Sku": "skus",
        "Product": "products", "Category": "categories", "Claim": "claims", "PriceChange": "price_changes"}
    order = next(m for m in s.objects if m.object == "Order")
    assert next(c for c in order.columns if c.property == "agreed_at").column == "ordered_at"
    gold = Library(LIB).get("commerce-bindings").extend["links"]
    assert {k: {kk: vv for kk, vv in v.items() if kk != "why"} for k, v in s.links.items()} == gold
    assert s.unmatched_tables == ["return_cases"] and "gift_wrap" in next(
        m for m in s.objects if m.object == "OrderItem").extra
    mod = binding(s, onto, name="shop-bindings", base=std)
    assert not compose(std + [mod], namespace="https://example.org/studio#").issues


def test_korean_headers_bind_a_subset_of_the_standard():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_data_studio.mapping import binding, suggest
    from xgen_data_studio.studio import Studio

    files = [read_csv("고객 번호,이름,등급\nK1,한별,VIP\nK2,누리,BASIC\nK3,가람,VIP\n".encode(), "고객.csv"),
             read_csv(("주문 번호,고객 번호,주문 일시,주문 상태\nR1,K1,2026-10-01 10:00,PAID\nR2,K1,2026-10-02 11:00,"
                       "DELIVERED\nR3,K2,2026-10-03 12:00,PAID\n").encode(), "주문.csv")]
    b = SqliteBackend()
    d = draft(b, loaded=load_sqlite(files, b), lang="ko")
    std = Library(LIB).resolve(["commerce"])
    onto = compose(std, namespace="https://example.org/studio#").ontology
    s = suggest(d, onto, ["commerce"])
    assert {m.object: m.table for m in s.objects} == {"Customer": "고객", "Order": "주문"}
    cust = next(m for m in s.objects if m.object == "Customer")
    assert {c.property: c.column for c in cust.columns}["customer_id"] == "고객 번호"
    assert s.links["placed"] == {"on": {"customer_id": "customer_id"}, "why": s.links["placed"]["why"]}
    mod = binding(s, onto, name="kr-bindings", base=std)
    assert "myOrders" in mod.remove["queries"] and "revenueByCategory" in mod.remove["queries"]
    st = Studio.from_modules(std + [mod], namespace="https://example.org/studio#")
    st.add_backend("source", b, source=True)
    from xgen_data_studio.backends.rdf import RdflibBackend

    st.add_backend("graph", RdflibBackend())
    st.project()
    assert st.check_bindings().ok
    assert len(st.run("ordersOfCustomer", {"customer": "K1"}).rows) == 2 and st.conformance().passed


def test_the_page_draws_a_decision_and_binds_files_onto_the_standard():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from .test_web import _build

    s = _build()
    for name, text in (("고객.csv", "고객 번호,이름,등급\nK1,한별,VIP\nK2,누리,BASIC\n"),
                       ("주문.csv", "주문 번호,고객 번호,주문 일시,주문 상태\nR1,K1,2026-10-01 10:00,PAID\n"
                                    "R2,K1,2026-10-02 11:00,DELIVERED\nR3,K2,2026-10-03 12:00,PAID\n"
                                    "R4,K2,2026-10-04 12:00,PAID\nR5,K1,2026-10-05 12:00,DELIVERED\n")):
        assert name in {f["source"] for f in s.upload(name, text.encode("utf-8"))["files"]}
    s.make_draft("주문 파일")
    got = s.induce_decision("Jumun.jumun_sangtae", ["gogaek.deunggeup"])
    assert got["ok"] and got["report"]["cases"] == 5
    view = s.preview_draft({})
    assert view["counts"]["decisions"] == 1
    assert {r["name"] for r in s.standards()["standards"]} >= {"commerce", "finance", "fashion"}
    sug = s.suggest_mapping(["commerce"])
    assert {o["object"]: o["table"] for o in sug["objects"]} == {"Customer": "고객", "Order": "주문"}
    out = s.apply_mapping(["commerce"], mapping={})
    assert out["ok"] and s.studio.onto.objects["Customer"].table == "고객"
    rows = s.run_query("ordersOfCustomer", {"customer": "K1"})
    assert rows["ok"] and rows["agree"] and len(rows["results"][0]["rows"]) == 3
    assert s.bindings()["ok"]


def _commerce_upload():
    from .test_web import _build

    s = _build()
    for name, text in (("고객.csv", "고객 번호,이름,등급,연락처\nK1,한별,VIP,010-5550-0011\nK2,누리,BASIC,010-5550-0012\n"),
                       ("주문.csv", "주문 번호,고객 번호,주문 일시,주문 상태\nR1,K1,2026-10-01 10:00,PAID\n"
                                    "R2,K1,2026-10-02 11:00,DELIVERED\nR3,K2,2026-10-03 12:00,CANCELLED\n"),
                       ("주문상품.csv", "주문상품 번호,주문 번호,수량,결제 단가\nI1,R1,2,10000\nI2,R2,1,5000\n"
                                        "I3,R3,1,7000\n")):
        s.upload(name, text.encode("utf-8"))
    s.make_draft("주문 파일")
    return s


def test_a_lone_column_goes_only_to_an_inherited_property_and_links_join_on_the_matched_one():
    pytest.importorskip("rdflib")
    s = _commerce_upload()
    sug = s.suggest_mapping(["commerce"])
    cols = {o["object"]: {c["property"]: c["column"] for c in o["columns"]} for o in sug["objects"]}
    assert cols["Order"]["agreed_at"] == "주문 일시"  # an agreement's date is the order's date
    assert "agreement_id" not in cols["Order"]  # an ancestor's key reads the own key, not the one other text column
    item = next(o for o in sug["objects"] if o["object"] == "OrderItem")
    assert "sku_id" not in cols["OrderItem"] and "sku_id" in {m["property"] for m in item["missing"]}
    assert sug["links"]["placed"]["on"] == {"customer_id": "customer_id"}
    assert sug["links"]["hasItem"]["on"] == {"order_id": "order_id"}


def test_tables_without_the_state_and_delivery_columns_still_bind_and_drop_what_needs_them():
    pytest.importorskip("rdflib")
    s = _commerce_upload()
    out = s.apply_mapping(["commerce"], mapping={})
    assert out["ok"]
    assert out["module"]["remove"]["states"] == ["OrderItem"]
    assert "returnEligibility" in out["module"]["remove"]["decisions"]
    assert "requestReturn" in out["module"]["remove"]["actions"]
    onto = s.studio.onto
    assert onto.objects["OrderItem"].states is None and "returnEligibility" not in onto.decisions
    assert all("requestReturn" not in r.request for r in onto.roles.values())  # the grant goes with the action
    assert not any(q.decision == "returnEligibility" for q in onto.questions)
    # the standard's C001 answer was for its example data: asked again with the answer these tables give
    assert "Q1" in out["module"]["remove"]["questions"]
    again = next(q for q in onto.questions if q.text.startswith("C001"))
    assert again.params == {"customer": "C001"} and again.expect == {"rows": 0}
    assert {q.query for q in onto.questions} >= {"allParties", "orderTotals", "ordersOfCustomer"}
    assert s.studio.questions().accuracy == 1.0
    assert not s.studio.conformance().summary()["disagree"]  # every query still has values to compare with
    r = s.run_query("customerValue", {"least": 0})
    assert r["ok"] and r["agree"]
    assert {row[0]: row[-1] for row in r["results"][0]["rows"]} == {"K1": 25000, "K2": 0}  # cancelled is 0
    assert s.bindings()["ok"]


def test_a_module_removes_a_state_machine_only_where_there_is_one():
    from xgen_data_studio.modules import Module, ModuleError

    mods = Library(LIB).resolve(["commerce"])
    ns = "https://example.org/studio#"
    drop = Module.from_dict({"module": "no-item-states", "kind": "customer", "requires": ["commerce"],
                             "remove": {"states": ["OrderItem"]}})
    assert compose([*mods, drop], namespace=ns).ontology.objects["OrderItem"].states is None
    bad = Module.from_dict({"module": "no-states", "kind": "customer", "requires": ["commerce"],
                            "remove": {"states": ["Customer"]}})
    with pytest.raises(ModuleError, match="has none"):
        compose([*mods, bad], namespace=ns)
