"""A key read from several columns: one property to everything above the columns, the columns where SQL is written."""
import pytest

from xgen_space import Ontology
from xgen_space.backends.sql import SqliteBackend
from xgen_space.bindings import check_bindings
from xgen_space.compile.pgq import graph_ddl
from xgen_space.definitions import Definitions, schema_backend
from xgen_space.draft import draft
from xgen_space.studio import Studio

from .conftest import EXAMPLE, LIB

SEED = """
CREATE TABLE ord (ord_no TEXT PRIMARY KEY, memo TEXT);
CREATE TABLE ord_line (ord_no TEXT, line_seq INTEGER, proc_seq INTEGER, status TEXT, qty INTEGER,
                       PRIMARY KEY (ord_no, line_seq, proc_seq));
CREATE TABLE ship (ship_no TEXT PRIMARY KEY, ord_no TEXT, line_seq INTEGER, proc_seq INTEGER);
INSERT INTO ord VALUES ('O1', 'a'), ('O2', 'b');
INSERT INTO ord_line VALUES ('O1', 1, 0, 'NEW', 2), ('O1', 1, 1, 'CANCEL', 2), ('O2', 1, 0, 'NEW', 5);
INSERT INTO ship VALUES ('S1', 'O1', 1, 0), ('S2', 'O2', 1, 0), ('S3', 'O9', 9, 9);
"""
DEFINITION = {
    "name": "t", "namespace": "https://example.org/t#",
    "objects": {
        "Ord": {"source": {"table": "ord"}, "key": "ord_no", "properties": {"ord_no": "string", "memo": "string"}},
        "Line": {"source": {"table": "ord_line"}, "key": "line_key", "properties": {
            "line_key": {"type": "string", "columns": ["ord_no", "line_seq", "proc_seq"], "required": True},
            "ord_no": "string", "line_seq": "integer", "proc_seq": "integer", "qty": "integer",
            "status": {"type": "enum", "values": {"NEW": "신규", "CANCEL": "취소"}}}},
        "Ship": {"source": {"table": "ship"}, "key": "ship_no", "properties": {
            "ship_no": "string", "line_ref": {"type": "string", "columns": ["ord_no", "line_seq", "proc_seq"]}}},
    },
    "links": {
        "hasLine": {"from": "Ord", "to": "Line", "cardinality": "one_to_many", "on": {"ord_no": "ord_no"}},
        "shipOf": {"from": "Ship", "to": "Line", "cardinality": "many_to_one", "on": {"line_ref": "line_key"}},
    },
    "queries": {
        "lines": {"query": {"match": {"l": "Line"}, "return": ["l.line_key", "l.status"], "order": ["line_key"]}},
        "shipped": {"query": {"match": {"s": "Ship", "l": "Line"}, "edges": [["s", "shipOf", "l"]],
                              "return": ["s.ship_no", "l.line_key", "l.qty"], "order": ["ship_no"]}},
    },
}


@pytest.fixture
def studio():
    st = Studio(Ontology.from_dict(DEFINITION).check())
    st.add_backend("source", SqliteBackend()).script(SEED)
    return st


def test_a_key_of_several_columns_reads_as_one_value(studio):
    rows = studio.run("lines").rows
    assert [r[0] for r in rows] == ["O1|1|0", "O1|1|1", "O2|1|0"]
    assert studio.fetch("Line", "O1|1|1")["status"] == "CANCEL"


def test_a_relation_on_several_columns_joins_column_by_column(studio):
    sql = studio.translate("shipped", "sql:sqlite").text
    assert 't_s."ord_no" = t_l."ord_no" AND t_s."line_seq" = t_l."line_seq"' in sql
    assert [tuple(r) for r in studio.run("shipped").rows] == [("S1", "O1|1|0", 2), ("S2", "O2|1|0", 5)]


def test_the_graph_holds_the_same_key_and_answers_the_same():
    pytest.importorskip("rdflib")
    from xgen_space.backends.rdf import RdflibBackend

    st = Studio(Ontology.from_dict(DEFINITION).check())
    st.add_backend("source", SqliteBackend()).script(SEED)
    st.add_backend("graph", RdflibBackend())
    st.project()
    assert sorted(r[0] for r in st.run("lines", backend="graph").rows) == ["O1|1|0", "O1|1|1", "O2|1|0"]
    assert sorted(tuple(r) for r in st.run("shipped", backend="graph").rows) == [("S1", "O1|1|0", 2), ("S2", "O2|1|0", 5)]


def test_the_database_check_reads_each_column():
    from xgen_space.bindings import check_bindings as check

    onto = Ontology.from_dict(DEFINITION).check()
    b = SqliteBackend()
    b.script(SEED)
    rep = check(onto, b)
    assert [f.kind for f in rep.findings if f.severity == "error"] == []
    assert any(f.kind == "orphan" and "1 Ship" in f.detail for f in rep.findings)  # S3 points at no line
    assert rep.checked["columns"] >= 12
    bad = SqliteBackend()
    bad.script(SEED.replace("PRIMARY KEY (ord_no, line_seq, proc_seq)", "UNIQUE (ord_no, line_seq, proc_seq, qty)")
               .replace("('O2', 1, 0, 'NEW', 5)", "('O1', 1, 0, 'NEW', 5)"))
    assert any(f.kind == "key" and "O1|1|0" in f.detail for f in check(onto, bad).findings)
    gone = SqliteBackend()
    gone.script(SEED.replace("proc_seq INTEGER, status", "status").replace(", proc_seq)", ")")
                .replace("'O1', 1, 0, 'NEW', 2), ('O1', 1, 1, 'CANCEL', 2), ('O2', 1, 0, 'NEW', 5)",
                         "'O1', 1, 'NEW', 2)"))
    assert any(f.kind == "column" and "proc_seq" in f.detail for f in check(onto, gone).findings)


def test_a_write_finds_its_row_by_each_key_column(studio):
    from xgen_space.actions import SqlWriteback

    w = SqlWriteback(studio.backends["source"])
    assert w.apply(studio.onto, "Line", "O1|1|1", {"status": "NEW"}) == 1
    assert studio.fetch("Line", "O1|1|1")["status"] == "NEW"
    assert studio.fetch("Line", "O1|1|0")["status"] == "NEW"
    with pytest.raises(ValueError, match="parts"):
        w.apply(studio.onto, "Line", "O1|1", {"status": "NEW"})


def test_exports_name_every_column():
    from xgen_space.exchange.r2rml import to_r2rml

    onto = Ontology.from_dict(DEFINITION).check()
    ddl = graph_ddl(onto)
    assert 'KEY ("ord_no", "line_seq", "proc_seq")' in ddl
    r2 = to_r2rml(onto)
    assert "{ord_no}%7C{line_seq}%7C{proc_seq}" in r2
    assert r2.count('rr:child "line_seq"') == 1


def test_columns_need_two_and_replace_column():
    d = {"name": "t", "namespace": "https://example.org/t#", "objects": {"A": {
        "key": "k", "properties": {"k": {"type": "string", "column": "x", "columns": ["a", "b"]}}}}}
    with pytest.raises(Exception, match="columns takes two"):
        Ontology.from_dict(d).check()


def _defs() -> Definitions:
    return Definitions.from_dict({"tables": [
        {"name": "ORD", "label": "주문", "columns": [{"name": "ORD_NO", "label": "주문번호", "pk": True, "type": "varchar"}]},
        {"name": "ORD_LINE", "label": "주문상세", "primary_key": ["ORD_NO", "LINE_SEQ"], "columns": [
            {"name": "ORD_NO", "label": "주문번호", "type": "varchar"}, {"name": "LINE_SEQ", "type": "numeric"},
            {"name": "QTY", "type": "numeric"}],
         "references": [{"columns": ["ORD_NO"], "table": "ORD", "ref_columns": ["ORD_NO"]}]},
        {"name": "SHIP", "label": "배송", "columns": [
            {"name": "SHIP_NO", "pk": True}, {"name": "L_ORD", "type": "varchar"}, {"name": "L_SEQ", "type": "numeric"}],
         "references": [{"columns": ["L_SEQ", "L_ORD"], "table": "ORD_LINE", "ref_columns": ["LINE_SEQ", "ORD_NO"]}]},
        {"name": "LINE_DETAIL", "label": "상세부가", "primary_key": ["ORD_NO", "LINE_SEQ"], "columns": [
            {"name": "ORD_NO"}, {"name": "LINE_SEQ", "type": "numeric"}, {"name": "NOTE"}],
         "references": [{"columns": ["ORD_NO", "LINE_SEQ"], "table": "ORD_LINE",
                         "ref_columns": ["ORD_NO", "LINE_SEQ"]}]},
        {"name": "WISH", "primary_key": ["ORD_NO", "SHIP_NO"], "columns": [{"name": "ORD_NO"}, {"name": "SHIP_NO"}],
         "references": [{"columns": ["ORD_NO"], "table": "ORD", "ref_columns": ["ORD_NO"]},
                        {"columns": ["SHIP_NO"], "table": "SHIP", "ref_columns": ["SHIP_NO"]}]},
    ]})


def test_a_draft_keeps_composite_keys_and_their_references():
    pytest.importorskip("yaml")
    from xgen_space.modules import compose

    d = _defs()
    dr = draft(schema_backend(d), name="shop", lang="ko", definitions=d)
    assert dr.skipped == []
    objs = {o.table: o for o in dr.objects}
    assert set(objs) == {"ORD", "ORD_LINE", "SHIP", "LINE_DETAIL"}  # the two-reference table is a relation
    line = objs["ORD_LINE"]
    key = next(p for p in line.properties if p.name == line.key)
    assert key.columns == ["ORD_NO", "LINE_SEQ"] and key.label == "주문상세 키"
    links = {(lk.source, lk.target): lk for lk in dr.links}
    ship = links[(objs["SHIP"].name, line.name)]
    ref = next(p for p in objs["SHIP"].properties if p.name == ship.on[0])
    assert ref.columns == ["L_ORD", "L_SEQ"] and ship.on[1] == line.key  # in the order of the key it points at
    same = links[(objs["LINE_DETAIL"].name, line.name)]
    assert same.cardinality == "one_to_one" and same.on == (objs["LINE_DETAIL"].key, line.key)
    assert any(lk.via for lk in dr.links)
    comp = compose(dr.modules(), name="shop")
    assert comp.issues == []
    assert comp.ontology.objects[line.name].properties[line.key].columns == ["ORD_NO", "LINE_SEQ"]


def test_a_drafted_composite_table_runs_end_to_end():
    pytest.importorskip("yaml")
    from xgen_space.draft import studio_from

    d = _defs()
    b = schema_backend(d)
    dr = draft(b, name="shop", lang="ko", definitions=d)
    st = studio_from(dr, b, graph=False)
    b.script("INSERT INTO ORD VALUES ('O1'); INSERT INTO ORD_LINE VALUES ('O1', 1, 2);"
             "INSERT INTO SHIP VALUES ('S1', 'O1', 1);")
    assert check_bindings(st.onto, b).ok
    line = next(o for o in st.onto.objects.values() if o.table == "ORD_LINE")
    assert st.fetch(line.name, "O1|1")["qty"] == 2


def _standard():
    from xgen_space.library import Library
    from xgen_space.modules import compose

    base = Library(LIB).resolve(["core", "commerce"])
    return base, compose(base, namespace="https://example.org/s#", name="s").ontology


def _shop():
    from xgen_space.definitions import read_definitions

    out = None
    for f in ("테이블정의서.csv", "코드정의서.csv"):
        d = read_definitions((EXAMPLE.parent / "definitions" / f).read_bytes(), f)
        out = d if out is None else out.merge(d)
    return draft(schema_backend(out), name="shop", lang="ko", definitions=out)


def test_a_glossary_finds_a_systems_words_and_a_standards_key_reads_all_its_columns():
    pytest.importorskip("yaml")
    from xgen_space.mapping import binding, suggest
    from xgen_space.modules import compose

    base, onto = _standard()
    d = _shop()
    assert "Customer" not in {m.object for m in suggest(d, onto, ["commerce"]).objects}
    s = suggest(d, onto, ["commerce"], [{"term": "고객", "synonyms": ["회원"]}])
    tables = {m.object: m.table for m in s.objects}
    assert tables["Customer"] == "TB_MEMBER" and tables["Order"] == "TB_ORDER" and tables["OrderItem"] == "TB_ORDER_ITEM"
    item = next(m for m in s.objects if m.object == "OrderItem")
    assert next(c for c in item.columns if c.property == "item_id").columns == ["ORDER_NO", "ITEM_SEQ"]
    m = binding(s, onto, name="shop-standard", base=base)
    comp = compose([*base, m], namespace="https://example.org/s#", name="s")
    assert comp.issues == [] and comp.ontology.objects["OrderItem"].key_prop.cols == ["ORDER_NO", "ITEM_SEQ"]


def test_a_table_chosen_by_hand_is_matched_column_by_column_again():
    pytest.importorskip("yaml")
    from xgen_space.mapping import binding, retarget, suggest

    base, onto = _standard()
    d = _shop()
    s = suggest(d, onto, ["commerce"])
    moved = retarget(s, d, onto, {"Order": "TB_ORDER_ITEM", "Customer": "TB_MEMBER"})
    tables = {m.object: m.table for m in moved.objects}
    assert tables["Order"] == "TB_ORDER_ITEM" and tables["Customer"] == "TB_MEMBER"
    order = next(m for m in moved.objects if m.object == "Order")
    assert "ORDER_STAT_CD" not in {c.column for c in order.columns}  # no column of the table it left stays
    m = binding(s, onto, name="x", base=base, draft=d, edits={"objects": {"Customer": "TB_MEMBER"}})
    assert m.extend["objects"]["Customer"]["table"] == "TB_MEMBER"


def test_a_relation_no_table_joins_goes_with_what_needs_it():
    pytest.importorskip("yaml")
    from xgen_space.mapping import binding, suggest
    from xgen_space.modules import compose

    base, onto = _standard()
    defs = Definitions.from_dict({"tables": [
        {"name": "TB_MEMBER", "label": "회원", "columns": [{"name": "MEMBER_NO", "label": "고객 번호", "pk": True}]},
        {"name": "TB_PRODUCT", "label": "상품기본", "columns": [{"name": "PRODUCT_NO", "label": "상품 번호", "pk": True}]}]})
    d = draft(schema_backend(defs), name="x", lang="ko", definitions=defs)
    s = suggest(d, onto, ["commerce"], [{"term": "고객", "synonyms": ["회원"]}])
    assert {"Customer", "Product"} <= {m.object for m in s.objects}
    m = binding(s, onto, name="x-standard", base=base)
    assert "wishes" in m.remove["links"]  # both ends are bound and no table joins them
    comp = compose([*base, m], namespace="https://example.org/s#", name="s")
    assert comp.issues == [] and "wishes" not in comp.ontology.links
