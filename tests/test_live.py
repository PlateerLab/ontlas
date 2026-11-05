"""The same studio on live servers. Each part runs when its address is given, and touches only what it creates:

    XSPACE_LIVE_PG=postgresql://user:pw@host:port/db     (works in schema xspace_live, dropped and made again)
    XSPACE_LIVE_FUSEKI=http://host:3030/ds               (+ XSPACE_LIVE_FUSEKI_AUTH=user:pw; the dataset is cleared)
    XSPACE_LIVE_NEO4J=bolt://host:7687                   (+ XSPACE_LIVE_NEO4J_AUTH=user:pw; the database is cleared)
    XSPACE_LIVE_GREMLIN=ws://host:8182/gremlin           (the graph is cleared)
    XSPACE_LIVE_MYSQL=mysql://user:pw@host:port/db       (tables xspace_ord, xspace_line, xspace_ship are dropped and made again)
    XSPACE_LIVE_ORACLE=oracle://user:pw@host:port/service (the same tables)
"""
import os
from datetime import datetime

import pytest

from xgen_space import Ontology
from xgen_space.backends.sql import SqliteBackend
from xgen_space.studio import Studio

from .conftest import EXAMPLE

NOW = datetime(2026, 10, 30, 12, 0)
LIB = EXAMPLE.parent / "library"
SEEDS = [(EXAMPLE / "seed.sql").read_text(encoding="utf-8"), (LIB / "seed_finance.sql").read_text(encoding="utf-8")]


def _need(var: str) -> str:
    v = os.environ.get(var, "")
    if not v:
        pytest.skip(f"{var} is not set")
    return v


def _pg():
    dsn = _need("XSPACE_LIVE_PG")  # before the import: without the address the test skips, wherever it runs
    psycopg = pytest.importorskip("psycopg")

    from xgen_space.backends.sql import DbApiBackend

    admin = psycopg.connect(dsn, autocommit=True)
    admin.execute("DROP SCHEMA IF EXISTS xspace_live CASCADE")
    admin.execute("CREATE SCHEMA xspace_live")
    admin.close()
    conn = psycopg.connect(dsn, options="-c search_path=xspace_live")
    b = DbApiBackend(conn, "postgres", paramstyle="format")
    for seed in SEEDS:
        for stmt in [s for s in seed.split(";") if s.strip()]:
            b.run(stmt)
    return b


def _commerce(source) -> Studio:
    st = Studio(Ontology.load(EXAMPLE / "ontology.yaml").check(), now=lambda: NOW)
    st.add_backend("source", source, source=True)
    return st


def _sqlite():
    b = SqliteBackend()
    for seed in SEEDS:
        b.script(seed)
    return b


def test_postgres_answers_like_sqlite_including_computed_properties_and_decisions():
    pytest.importorskip("rdflib")
    from xgen_space.backends.rdf import RdflibBackend

    pg = _pg()
    st = _commerce(pg)
    st.add_backend("lite", _sqlite())
    st.add_backend("graph", RdflibBackend())
    st.project()
    rep = st.conformance()
    assert rep.passed, rep.summary()
    assert rep.summary()["queries"] == len(st.onto.queries)
    assert st.run("orderTotals").rows[0][-1] == 97000.0
    assert st.decide("returnEligibility", "I1001").matched == ["in-window"]
    assert st.check_bindings().ok and st.questions().accuracy == 1.0


def test_postgres_takes_writes_in_one_transaction_and_rolls_back_a_failed_one():
    from xgen_space.actions import Actor

    pg = _pg()
    st = _commerce(pg)
    p = st.actions.request("requestReturn", "I1001", {"reason": "size"}, actor=Actor("a", "agent", ["customer_agent"]))
    st.actions.approve(p.id, approver=Actor("op", "human", ["operator"]))
    assert st.fetch("OrderItem", "I1001")["item_status"] == "RETURN_REQUESTED"
    st.actions.rollback(p.id, actor=Actor("op", "human", ["operator"]))
    assert st.fetch("OrderItem", "I1001")["item_status"] == "NORMAL"
    with pytest.raises(Exception):
        pg.run_many([("UPDATE customers SET grade = 'X' WHERE customer_id = 'C001'", ()),
                     ("UPDATE no_such_table SET a = 1", ())])
    assert pg.fetch("SELECT grade FROM customers WHERE customer_id = 'C001'") == [("VIP",)]
    with pytest.raises(Exception):
        st.run({"match": {"c": "Customer"}, "where": {"eq": ["c.grade", 1]}, "return": ["c.name"]})
    assert st.run("ordersOfCustomer", {"customer": "C001"}).rows  # a failed query leaves the connection usable


def test_postgres_drafts_the_relations_from_its_catalog_and_resolves_identities():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.draft import draft

    pg = _pg()
    d = draft(pg, name="shop", tables=["customers", "orders", "order_items", "skus", "products", "categories",
                                       "claims", "wishlists", "price_changes"])
    assert {(lk.source, lk.target, lk.cardinality) for lk in d.links} >= {
        ("Order", "Customer", "many_to_one"), ("OrderItem", "Order", "many_to_one"),
        ("PriceChange", "Skus", "many_to_one"), ("Customer", "Product", "many_to_many")}
    lib = load_studio(LIB / "studio.yaml")
    lib.backends.pop("source")
    lib.add_backend("source", pg, source=True)
    rep = lib.resolve_identity("Person")
    assert [c.members for c in rep.joined] == [["Borrower:B03", "Customer:C003"]]
    assert lib.run("customersWhoBorrow").rows == [("Borrower:B03", "C003", "B03", "박서연")]
    lib.project()
    assert lib.conformance().passed and lib.gates()["passed"]


def test_fuseki_answers_like_sqlite():
    from xgen_space.backends.rdf import SparqlEndpointBackend

    url = _need("XSPACE_LIVE_FUSEKI").rstrip("/")
    user, _, pw = os.environ.get("XSPACE_LIVE_FUSEKI_AUTH", ":").partition(":")
    st = _commerce(_sqlite())
    st.add_backend("fuseki", SparqlEndpointBackend(f"{url}/query", update_url=f"{url}/update", gsp_url=f"{url}/data",
                                                   user=user, password=pw))
    st.project()
    rep = st.conformance()
    assert rep.passed, rep.summary()
    st.backends["source"].run("UPDATE customers SET grade = 'SILVER' WHERE customer_id = 'C002'")
    report = st.project()  # the second time only the change set goes
    assert report["fuseki"]["changes"]["changed"] == 1
    assert st.conformance().passed


def test_neo4j_answers_like_sqlite_including_computed_properties():
    pytest.importorskip("neo4j")
    import neo4j

    from xgen_space.backends.graph import Neo4jBackend

    uri = _need("XSPACE_LIVE_NEO4J")
    user, _, pw = os.environ.get("XSPACE_LIVE_NEO4J_AUTH", "neo4j:").partition(":")
    driver = neo4j.GraphDatabase.driver(uri, auth=(user, pw))
    try:
        st = _commerce(_sqlite())
        st.add_backend("neo", Neo4jBackend(driver))
        st.project()
        rep = st.conformance()
        assert rep.passed, rep.summary()
        assert st.run("skuPrices", backend="neo").rows[0][1:3] == (69000.0, 59000.0)
        assert st.run_cypher("MATCH (o:Order) WHERE o.total > 60000 RETURN o.order_id ORDER BY order_id",
                             backend="neo").rows == [("O1",), ("O3",)]
    finally:
        driver.close()


def test_gremlin_server_answers_like_sqlite():
    pytest.importorskip("gremlin_python")
    from xgen_space.backends.gremlin import GremlinBackend

    g = GremlinBackend(_need("XSPACE_LIVE_GREMLIN"))
    try:
        st = _commerce(_sqlite())
        st.add_backend("gremlin", g)
        st.project()
        rep = st.conformance()
        assert rep.passed, rep.summary()
        from xgen_space.compile.base import CompileError, compiler_for

        def takes(q) -> bool:  # the rest use what Gremlin here declares it does not do (optional, computed)
            try:
                compiler_for(st.onto, "gremlin").compile(q)
                return True
            except CompileError:
                return False

        ran = {q.name for q in rep.queries if q.outcomes["gremlin"].rows is not None}
        assert ran == {n for n, (q, _) in st.registered().items() if takes(q)} and len(ran) >= 7
        assert st.run("categoryAncestors", {"category": "K3"}, backend="gremlin").rows == [("상의",), ("의류",)]
        from xgen_space.ir import Query

        more = {
            "twoUp": {"match": {"k": "Category", "a": "Category"},
                      "edges": [{"from": "k", "link": "broader", "to": "a", "hops": [2, 3]}],
                      "return": ["k.category_id", "a.name"], "order": ["category_id", "name"]},
            "down": {"match": {"a": "Category", "k": "Category"},
                     "edges": [{"from": "a", "link": "narrower", "to": "k", "hops": [1, 2]}],
                     "return": ["a.category_id", {"count": "k", "as": "n"}], "order": ["category_id"]},
            "notIn": {"match": {"o": "Order"}, "where": {"not": {"in": ["o.status", ["PAID", "SHIPPED"]]}},
                      "return": ["o.order_id"], "order": ["-order_id"]},
            "belowList": {"match": {"i": "OrderItem", "s": "Sku"}, "edges": [["i", "ofSku", "s"]],
                          "where": {"lt": ["i.unit_price", {"ref": "s.price"}]}, "return": ["i.item_id"]},
            "overall": {"match": {"s": "Sku"}, "return": [{"avg": "s.price", "as": "a"}, {"min": "s.stock", "as": "m"},
                                                          {"count_distinct": "s.color", "as": "c"}]},
            "text": {"match": {"p": "Product"}, "where": {"contains": ["p.name", "니트"]}, "return": ["p.product_id"]},
        }
        extra = st.conformance(queries={n: (Query.from_dict(q), {}) for n, q in more.items()})
        assert extra.passed and all(r.outcomes["gremlin"].rows is not None for r in extra.queries), extra.summary()
    finally:
        g.close()


@pytest.mark.parametrize(("kind", "var", "driver"), [("postgres", "XSPACE_LIVE_PG", "psycopg"),
                                                     ("mysql", "XSPACE_LIVE_MYSQL", "pymysql"),
                                                     ("oracle", "XSPACE_LIVE_ORACLE", "oracledb")])
def test_a_studio_is_drafted_from_the_catalog_and_runs(kind, var, driver):
    dsn = _need(var)
    pytest.importorskip(driver)
    pytest.importorskip("sqlglot")
    from pathlib import Path

    from xgen_space.actions import SqlWriteback
    from xgen_space.bindings import check_bindings
    from xgen_space.config import open_backend
    from xgen_space.draft import _catalog, draft, studio_from
    from xgen_space.ir import Column, Edge, Query, Ref

    b = open_backend({"kind": kind, "dsn": dsn}, Path("."))
    for t in ("xspace_ship", "xspace_line", "xspace_ord"):
        try:
            b.run(f"DROP TABLE {t}")
        except Exception:  # not there yet
            pass
    text, big = {"oracle": ("VARCHAR2(20)", "CLOB"), "postgres": ("VARCHAR(20)", "JSON")}.get(kind, ("VARCHAR(20)", "TEXT"))
    for stmt in [
        f"CREATE TABLE xspace_ord (ord_no {text} PRIMARY KEY, memo {big}, status {text})",
        f"CREATE TABLE xspace_line (ord_no {text} NOT NULL, line_seq INTEGER NOT NULL, proc_seq INTEGER NOT NULL, "
        "qty INTEGER, PRIMARY KEY (ord_no, line_seq, proc_seq), FOREIGN KEY (ord_no) REFERENCES xspace_ord (ord_no))",
        f"CREATE TABLE xspace_ship (ship_no {text} PRIMARY KEY, ord_no {text}, line_seq INTEGER, proc_seq INTEGER, "
        "FOREIGN KEY (ord_no, line_seq, proc_seq) REFERENCES xspace_line (ord_no, line_seq, proc_seq))",
        "INSERT INTO xspace_ord VALUES ('O1', '{}', 'NEW')", "INSERT INTO xspace_ord VALUES ('O2', '{}', 'NEW')",
        "INSERT INTO xspace_line VALUES ('O1', 1, 0, 2)", "INSERT INTO xspace_line VALUES ('O1', 1, 1, 3)",
        "INSERT INTO xspace_ship VALUES ('S1', 'O1', 1, 1)",
    ]:
        b.run(stmt)
    d = draft(b, name="live", lang="ko", tables=[t[0] for t in _catalog(b) if t[0].lower().startswith("xspace_")])
    assert d.skipped == []
    st = studio_from(d, b, graph=False)
    objs = {o.table.lower(): o for o in st.onto.objects.values()}
    line, ship = objs["xspace_line"], objs["xspace_ship"]
    assert [c.lower() for c in line.key_prop.cols] == ["ord_no", "line_seq", "proc_seq"]
    assert check_bindings(st.onto, b).ok
    assert st.fetch(line.name, "O1|1|1")[line.key] == "O1|1|1"
    link = next(lk for lk in st.onto.links.values() if lk.source == ship.name and lk.target == line.name)
    q = Query(nodes={"s": ship.name, "l": line.name}, edges=[Edge("s", link.name, "l")],
              columns=[Column(Ref("s", ship.key), "ship"), Column(Ref("l", line.key), "line")])
    assert [tuple(r) for r in st.run(q).rows] == [("S1", "O1|1|1")]
    qty = next(p.name for p in line.properties.values() if p.col.lower() == "qty")
    assert SqlWriteback(b).apply(st.onto, line.name, "O1|1|1", {qty: 9}) == 1
    assert st.questions().accuracy == 1.0
    for t in ("xspace_ship", "xspace_line", "xspace_ord"):
        b.run(f"DROP TABLE {t}")
