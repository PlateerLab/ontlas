"""A draft reviewed table by table: English names for what it found, a sample beside each table, and some tables bound
to a standard while the others stay new objects beside it."""
from pathlib import Path

import pytest

from xgen_space.naming import english, vocabulary

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    s = StudioSession(load_studio(ROOT / "examples" / "library" / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))
    s.use_samples()
    s.make_draft("가상 쇼핑몰")
    return s


def test_a_korean_name_reads_as_english_only_when_every_part_is_a_known_word():
    words = vocabulary(terms=[{"term": "고객", "synonyms": ["회원"]}])
    assert english("주문상태이력", words)[0] == "OrderStatusHistory"
    assert english("주문 상태", words)[1] == [["주문", "Order"], ["상태", "Status"]]
    assert english("회원", words)[0] == "Member"  # the base word stands; a synonym only fills a gap
    assert english("까치둥지", words) is None  # a word nobody knows stays for a person to name
    assert english("order", words) is None  # nothing Korean to read


def test_the_draft_offers_english_names_and_takes_them(session):
    view = session._draft_view()
    names = {k: v["name"] for k, v in view["names"].items()}
    assert names["Jumunsangtaeiryeok"] == "OrderStatusHistory" and names["Gyeolje"] == "Payment"
    d = session._edit(session.pending[0], {"names": names})
    assert {o.name for o in d.objects} == set(names.values())
    hist = next(lk for lk in d.links if lk.source == "OrderStatusHistory")
    assert hist.target == "Order"  # the relations follow the new names
    with pytest.raises(ValueError):
        session._edit(session.pending[0], {"names": {"Gyeolje": "Order", "Jumun": "Order"}})  # two objects one name
    with pytest.raises(ValueError):
        session._edit(session.pending[0], {"names": {"Gyeolje": "payment"}})


def test_a_table_is_shown_with_its_rows_its_key_and_what_to_hide(session):
    t = session.draft_table("회원")
    assert t["rows"] == 24 and len(t["sample"]) == 3 and t["columns"][0] == "회원번호"
    assert t["key"]["column"] == "회원번호" and t["key"]["distinct"] == 24 and t["key"]["nulls"] == 0
    assert t["personal"] == ["연락처"]


def test_some_tables_bind_to_the_standard_and_the_rest_stay_new(session):
    std = [r["name"] for r in session.standards()["standards"] if r["kind"] == "domain"]
    names = {k: v["name"] for k, v in session._draft_view()["names"].items() if v["name"]}
    m = session.suggest_mapping(std, {"names": names})
    order = next(o for o in m["objects"] if o["table"] == "주문")
    assert order["object"] == "Order" and order["module_label"] and 0 < order["cover"] <= 1 and order["name_score"] == 1
    choices = {o["table"]: "standard" for o in m["objects"] if o["table"] != "회원"} | {"회원": "new", "주문상태이력": "new"}
    plan = session.review_preview(std, {"names": names}, choices)
    assert plan["ok"] and not plan["issues"] and any("OrderStatusHistory" in x["yaml"] for x in plan["modules"])
    session.apply_review(std, {"names": names}, choices)
    onto = session.studio.onto
    assert {"Order", "OrderItem", "Member", "OrderStatusHistory"} <= set(onto.objects)
    assert any(lk.source == "OrderStatusHistory" and lk.target == "Order" for lk in onto.links.values())
    key = onto.objects["OrderStatusHistory"].key
    assert session.studio.run({"match": {"h": "OrderStatusHistory"}, "return": [f"h.{key}"]}).rows


def test_a_new_object_cannot_take_a_standard_name(session):
    std = [r["name"] for r in session.standards()["standards"] if r["kind"] == "domain"]
    with pytest.raises(ValueError, match="표준 Entity와 같아"):
        session.apply_review(std, {"names": {"Jumun": "Order"}}, {"결제": "standard", "주문": "new"})
