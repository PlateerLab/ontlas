"""The same studio on live servers. Each part runs when its address is given, and touches only what it creates:

    ONTLAS_LIVE_PG=postgresql://user:pw@host:port/db     (works in schema ontlas_live, dropped and made again)
    ONTLAS_LIVE_FUSEKI=http://host:3030/ds               (+ ONTLAS_LIVE_FUSEKI_AUTH=user:pw; the dataset is cleared)
    ONTLAS_LIVE_NEO4J=bolt://host:7687                   (+ ONTLAS_LIVE_NEO4J_AUTH=user:pw; the database is cleared)
    ONTLAS_LIVE_GREMLIN=ws://host:8182/gremlin           (the graph is cleared)
    ONTLAS_LIVE_MYSQL=mysql://user:pw@host:port/db       (tables ontlas_ord, ontlas_line, ontlas_ship are dropped and made again)
    ONTLAS_LIVE_ORACLE=oracle://user:pw@host:port/service (the same tables and the example's, so give it an empty user; also SQL/PGQ)
    ONTLAS_LIVE_MSSQL=mssql://user:pw@host:port/db       (the same tables and the example's, so give it an empty database)
"""
import os
from datetime import datetime

import pytest

from ontlas import Ontology
from ontlas.backends.sql import SqliteBackend
from ontlas.studio import Studio

from .conftest import EXAMPLE, LIB

NOW = datetime(2026, 10, 30, 12, 0)
SEEDS = [(EXAMPLE / "seed.sql").read_text(encoding="utf-8"), (LIB / "seed_finance.sql").read_text(encoding="utf-8")]
# the example's columns in each server's own types: what a real schema there has, not SQLite's text for dates
SERVERS = {
    "oracle": ("ONTLAS_LIVE_ORACLE", "oracledb", {"TEXT": "VARCHAR2(400)", "INTEGER": "NUMBER(10)", "REAL": "NUMBER(14, 4)",
                                                  "at": "TIMESTAMP", "claimed_at": "DATE"}),
    "mssql": ("ONTLAS_LIVE_MSSQL", "pymssql", {"TEXT": "NVARCHAR(400)", "INTEGER": "INT", "REAL": "DECIMAL(14, 4)",
                                               "at": "DATETIME", "claimed_at": "DATETIME2(0)"}),
}
ON_SERVERS = pytest.mark.parametrize("kind", list(SERVERS))


def _need(var: str) -> str:
    v = os.environ.get(var, "")
    if not v:
        pytest.skip(f"{var} is not set")
    return v


def _server(kind: str):
    """A backend on that server, with the example copied there: names as a plain CREATE TABLE leaves them."""
    var, driver, types = SERVERS[kind]
    dsn = _need(var)
    pytest.importorskip(driver)
    pytest.importorskip("sqlglot")
    from pathlib import Path

    from ontlas.compile.sql import qi
    from ontlas.config import open_backend

    b, lite = open_backend({"kind": kind, "dsn": dsn}, Path(".")), _sqlite()
    held = str.upper if kind == "oracle" else str
    for (t,) in lite.fetch("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
        cols = lite.fetch(f"PRAGMA table_info({qi(t)})")
        try:
            b.run(f"DROP TABLE {qi(held(t))}")
        except Exception:  # not there yet
            pass

        def typed(name: str, sql: str) -> str:
            return types.get(name) or types["at" if name.endswith("_at") else sql]

        b.run(f"CREATE TABLE {qi(held(t))} (" + ", ".join(
            f"{qi(held(c[1]))} {typed(c[1], c[2].upper())}{' PRIMARY KEY' if c[5] else ''}" for c in cols) + ")")
        insert = f"INSERT INTO {qi(held(t))} VALUES ({', '.join('?' * len(cols))})"
        b.run_many([(insert, tuple(datetime.fromisoformat(v) if c[1].endswith("_at") and v else v
                                   for c, v in zip(cols, r))) for r in lite.fetch(f"SELECT * FROM {qi(t)}")])
    return b


def _pg():
    dsn = _need("ONTLAS_LIVE_PG")  # before the import: without the address the test skips, wherever it runs
    psycopg = pytest.importorskip("psycopg")

    from ontlas.backends.sql import DbApiBackend

    admin = psycopg.connect(dsn, autocommit=True)
    admin.execute("DROP SCHEMA IF EXISTS ontlas_live CASCADE")
    admin.execute("CREATE SCHEMA ontlas_live")
    admin.close()
    conn = psycopg.connect(dsn, options="-c search_path=ontlas_live")
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
    from ontlas.backends.rdf import RdflibBackend

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
    from ontlas.actions import Actor

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
    from ontlas.config import load_studio
    from ontlas.draft import draft

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


@ON_SERVERS
def test_a_server_answers_like_sqlite_including_computed_properties_and_decisions(kind):
    pytest.importorskip("rdflib")
    from ontlas.backends.rdf import RdflibBackend

    b = _server(kind)
    st = _commerce(b)
    st.add_backend("lite", _sqlite())
    st.add_backend("graph", RdflibBackend())
    st.project()
    rep = st.conformance()
    assert rep.passed, rep.summary()
    assert rep.summary()["queries"] == len(st.onto.queries)
    assert all(q.outcomes["source"].rows is not None for q in rep.queries)
    assert st.run("orderTotals").rows[0][-1] == 97000.0
    assert st.decide("returnEligibility", "I1001").matched == ["in-window"]
    assert st.check_bindings().ok and st.questions().accuracy == 1.0
    assert not [f for f in st.check_bindings().findings if f.kind == "type"]  # NUMBER is a whole number where it says so


def _every_function() -> Ontology:
    """The example with a computed property for each function of the expression language."""
    import yaml

    spec = yaml.safe_load((EXAMPLE / "ontology.yaml").read_text(encoding="utf-8"))
    spec["objects"]["Sku"]["properties"].update({
        "cents": {"type": "decimal", "expr": "round(price / 7, 2)"},
        "whole": {"type": "integer", "expr": "round(price / 7)"},
        "down": {"type": "integer", "expr": "floor(price / 7)"},
        "up": {"type": "integer", "expr": "ceil(price / 7)"},
        "gap": {"type": "integer", "expr": "abs(stock - 10)"},
        "none": {"type": "decimal", "expr": "price / (stock - stock)"},
        "tag": {"type": "string", "expr": "concat(color, '-', size)"},
        "letters": {"type": "integer", "expr": "length(concat(size, ' '))"},
        "cased": {"type": "string", "expr": "concat(lower(size), upper(lower(size)))"},
        "scarce": {"type": "boolean", "expr": "stock < 5"},
        "wanted": {"type": "boolean", "expr": "stock < 5 and not (price < 20000) or size = 'L'"},
        "word": {"type": "string", "expr": "if(scarce, '부족', '충분')"},
        "mark": {"type": "string", "expr": "if(stock < 5 and scarce, concat(color, ' 품절 임박'), coalesce(color, '없음'))"},
    })
    spec["objects"]["OrderItem"]["properties"].update({
        "in_year": {"type": "integer", "expr": "year(delivered_at)"},
        "in_month": {"type": "integer", "expr": "month(delivered_at)"},
        "on_day": {"type": "integer", "expr": "day(delivered_at)"},
        "waited": {"type": "integer", "expr": "days_between('2026-10-01', delivered_at)"},
    })
    spec["objects"]["Category"]["properties"].update({
        "policy": {"type": "string", "expr": "if(returnable, '가능', '불가')"},
        "path": {"type": "string", "expr": "concat(name, '/', parent_id)"},  # null at the top, which has no parent
    })
    return Ontology.from_dict(spec).check()


@ON_SERVERS
def test_every_function_and_clause_answers_like_sqlite(kind):
    from ontlas.ir import Query

    skus = "cents whole down up gap none tag letters cased scarce wanted word mark".split()
    more = {
        "functions": {"match": {"s": "Sku"}, "return": ["s.sku_id", *[f"s.{p}" for p in skus]], "order": ["sku_id"]},
        "dates": {"match": {"i": "OrderItem"}, "order": ["item_id"],
                  "return": ["i.item_id", "i.in_year", "i.in_month", "i.on_day", "i.waited"]},
        "storedFlag": {"match": {"k": "Category"}, "return": ["k.category_id", "k.returnable", "k.policy", "k.path"],
                       "order": ["category_id"]},
        "flagTrue": {"match": {"k": "Category"}, "where": {"eq": ["k.returnable", True]}, "return": ["k.category_id"]},
        "flagFalse": {"match": {"k": "Category"}, "where": {"eq": ["k.returnable", False]}, "return": ["k.category_id"]},
        "computedFlag": {"match": {"s": "Sku"}, "where": {"eq": ["s.scarce", True]}, "return": ["s.sku_id"]},
        "top": {"match": {"s": "Sku"}, "return": ["s.sku_id", "s.stock"], "order": ["-stock"], "limit": 2},
        "bare": {"match": {"s": "Sku"}, "return": [{"count": "*", "as": "n"}], "limit": 1},
        "distinct": {"match": {"s": "Sku"}, "return": ["s.color"], "distinct": True, "order": ["color"]},
        "distinctTop": {"match": {"s": "Sku"}, "return": ["s.color"], "distinct": True, "order": ["-color"], "limit": 2},
        "nullsLast": {"match": {"i": "OrderItem"}, "return": ["i.item_id", "i.delivered_at"],
                      "order": ["delivered_at", "item_id"]},
        "nullsLastDown": {"match": {"i": "OrderItem"}, "return": ["i.item_id", "i.delivered_at"],
                          "order": ["-delivered_at", "item_id"]},
        "orderComputed": {"match": {"o": "Order"}, "return": ["o.order_id", "o.total"], "order": ["-total", "order_id"]},
        "overall": {"match": {"s": "Sku"}, "return": [
            {"avg": "s.stock", "as": "a"}, {"min": "s.stock", "as": "lo"}, {"max": "s.stock", "as": "hi"},
            {"sum": "s.stock", "as": "t"}, {"count_distinct": "s.color", "as": "c"}, {"count": "s", "as": "n"}]},
        "perProduct": {"match": {"s": "Sku"}, "return": ["s.product_id", {"avg": "s.stock", "as": "a"}],
                       "order": ["product_id"]},
        "perFlag": {"match": {"s": "Sku"}, "return": ["s.scarce", {"count": "s", "as": "n"}], "order": ["scarce"]},
        "perCount": {"match": {"o": "Order"}, "return": ["o.item_count", {"count": "o", "as": "n"}],
                     "order": ["item_count"]},
        "sumOfComputed": {"match": {"c": "Customer"}, "return": [{"sum": "c.spent", "as": "t"}, {"count": "*", "as": "n"}]},
        "perGrade": {"match": {"c": "Customer"}, "return": ["c.grade", {"max": "c.spent", "as": "m"}, {"avg": "c.order_count", "as": "a"}],
                     "order": ["grade"]},
        "moment": {"match": {"o": "Order"}, "where": {"eq": ["o.ordered_at", "2026-10-20T10:00:00"]},
                   "return": ["o.order_id", "o.ordered_at"]},
        "since": {"match": {"i": "OrderItem"}, "where": {"gte": ["i.delivered_at", "2026-10-20T00:00:00"]},
                  "return": ["i.item_id"]},
        "sinceDay": {"match": {"i": "OrderItem"}, "where": {"gte": ["i.delivered_at", "2026-10-20"]},
                     "return": ["i.item_id"]},
        "claimedOn": {"match": {"c": "Claim"}, "where": {"gte": ["c.claimed_at", "2026-10-26T09:00:00"]},
                      "return": ["c.claim_id", "c.claimed_at"]},
        "search": {"match": {"p": "Product"}, "where": {"contains": ["p.name", "니트"]}, "return": ["p.product_id"]},
        "searchCase": {"match": {"s": "Sku"}, "where": {"contains": ["s.size", "m"]}, "return": ["s.sku_id"]},
        "notIn": {"match": {"o": "Order"}, "where": {"not_in": ["o.status", ["PAID", "SHIPPED"]]}, "return": ["o.order_id"]},
        "isNull": {"match": {"i": "OrderItem"}, "where": {"is_null": "i.delivered_at"}, "return": ["i.item_id"]},
        "either": {"match": {"o": "Order"}, "return": ["o.order_id"], "where": {
            "or": [{"eq": ["o.status", "SHIPPED"]}, {"not": {"gt": ["o.ordered_at", "2026-10-16T00:00:00"]}}]}},
        "optional": {"match": {"c": "Customer", "o": "Order"}, "return": ["c.customer_id", "o.order_id"],
                     "edges": [{"from": "c", "link": "placed", "to": "o", "optional": True}],
                     "order": ["customer_id", "order_id"]},
        "exists": {"match": {"c": "Customer"}, "return": ["c.customer_id"], "where": {
            "exists": {"match": {"o": "Order"}, "edges": [["c", "placed", "o"]]}}},
        "down": {"match": {"a": "Category", "k": "Category"}, "return": ["a.category_id", {"count": "k", "as": "n"}],
                 "edges": [{"from": "a", "link": "narrower", "to": "k", "hops": [1, 2]}], "order": ["category_id"]},
        "blank": {"match": {"p": "Product"}, "where": {"eq": ["p.brand", ""]}, "return": ["p.product_id"]},
        "notBlank": {"match": {"p": "Product"}, "where": {"ne": ["p.brand", ""]}, "return": ["p.product_id"]},
        "blankAmong": {"match": {"p": "Product"}, "where": {"in": ["p.brand", ["", "바람직물"]]}, "return": ["p.product_id"]},
        "notAmongBlank": {"match": {"p": "Product"}, "where": {"not_in": ["p.brand", ["", "바람직물"]]},
                          "return": ["p.product_id"]},
        "holdsBlank": {"match": {"p": "Product"}, "where": {"contains": ["p.name", ""]}, "return": ["p.product_id"]},
    }
    b, lite = _server(kind), _sqlite()
    for x in (b, lite):  # Oracle has no empty text: it keeps a null
        x.run("UPDATE products SET brand = '' WHERE product_id = 'P3'")
    st = Studio(_every_function(), now=lambda: NOW)
    st.add_backend("source", b, source=True)
    st.add_backend("lite", lite)
    rep = st.conformance(queries={n: (Query.from_dict(q), {}) for n, q in more.items()})
    assert rep.passed, [(q.name, q.detail) for q in rep.queries if not q.agree]
    ran = {q.name: q.outcomes["source"].rows for q in rep.queries}
    assert all(r is not None for r in ran.values()) and len(ran["functions"]) == 4
    assert ran["overall"][0][0] == 14.25  # not cut to a whole number
    assert ran["functions"][0][1:3] == (8428.57, 8429)
    assert [r[0] for r in ran["nullsLast"]][-2:] == ["I1005", "I1006"]
    assert sorted(r[0] for r in ran["blank"]) == ["P3"] and ran["searchCase"] == []


@ON_SERVERS
def test_a_server_takes_writes_in_one_transaction_and_rolls_back_a_failed_one(kind):
    from ontlas.actions import Actor

    b = _server(kind)
    st = _commerce(b)
    p = st.actions.request("requestReturn", "I1001", {"reason": "size"}, actor=Actor("a", "agent", ["customer_agent"]))
    st.actions.approve(p.id, approver=Actor("op", "human", ["operator"]))
    assert st.fetch("OrderItem", "I1001")["item_status"] == "RETURN_REQUESTED"
    st.actions.rollback(p.id, actor=Actor("op", "human", ["operator"]))
    assert st.fetch("OrderItem", "I1001")["item_status"] == "NORMAL"
    with pytest.raises(Exception):
        b.run_many([("UPDATE customers SET grade = 'X' WHERE customer_id = 'C001'", ()),
                     ("UPDATE no_such_table SET a = 1", ())])
    assert b.fetch("SELECT grade FROM customers WHERE customer_id = 'C001'") == [("VIP",)]
    with pytest.raises(Exception):
        b.fetch("SELECT no_such_column FROM customers")
    assert st.run("ordersOfCustomer", {"customer": "C001"}).rows  # a failed query leaves the connection usable


@ON_SERVERS
def test_a_draft_from_a_server_runs_its_queries_like_sqlite(kind):
    pytest.importorskip("yaml")
    from ontlas.draft import _catalog, draft, studio_from

    b = _server(kind)
    shop = ("customers", "orders", "order_items", "skus", "products", "categories", "claims", "wishlists", "price_changes")
    d = draft(b, name="shop", tables=[t[0] for t in _catalog(b) if t[0].lower() in shop])
    assert d.skipped == [] and len(d.objects) == 8
    assert {(lk.source, lk.target, lk.cardinality) for lk in d.links} >= {
        ("Order", "Customer", "many_to_one"), ("OrderItem", "Order", "many_to_one"),
        ("PriceChange", "Skus", "many_to_one"), ("Customer", "Product", "many_to_many")}
    prop = {p.column.lower(): p.type for o in d.objects for p in o.properties}
    assert (prop["ordered_at"], prop["quantity"], prop["unit_price"]) == ("datetime", "integer", "decimal")
    assert prop["claimed_at"] == "datetime"  # an Oracle DATE holds a time too
    st = studio_from(d, b, graph=False)
    st.add_backend("lite", _sqlite())
    assert st.check_bindings().ok and st.onto.queries
    rep = st.conformance()
    assert rep.passed, [(q.name, q.detail) for q in rep.queries if not q.agree]
    assert all(q.outcomes["source"].rows is not None for q in rep.queries)


@ON_SERVERS
def test_ontlas_draft_dsn_makes_a_space_that_opens_and_keeps_the_password_out(kind, tmp_path, monkeypatch):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.cli import main
    from ontlas.config import load_studio

    _server(kind)
    dsn = os.environ[SERVERS[kind][0]]
    out = tmp_path / "space"
    assert main(["draft", "--dsn", dsn, "--out", str(out), "--name", "shop"]) == 0
    written = "\n".join(p.read_text(encoding="utf-8") for p in out.rglob("*.yaml"))
    assert dsn not in written and f"kind: {kind}" in written and "${ONTLAS_DSN}" in written
    monkeypatch.setenv("ONTLAS_DSN", dsn)
    st = load_studio(out / "studio.yaml")
    assert st.check_bindings().ok
    rep = st.conformance()
    assert rep.queries and rep.passed, [(q.name, q.detail) for q in rep.queries if not q.agree]


def _page():
    pytest.importorskip("yaml")
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(_commerce(_sqlite()), data=DataOptions(allow_connect=True))


@ON_SERVERS
def test_the_page_connects_and_says_where_without_the_user_or_the_password(kind):
    from urllib.parse import urlparse

    _server(kind)
    dsn = os.environ[SERVERS[kind][0]]
    u = urlparse(dsn)
    page = _page()
    page.connect(dsn)
    d = page.pending[0]
    assert d.objects and d.origin["detail"].split(" ")[-1] == f"{u.hostname}{u.path}"
    with pytest.raises(Exception) as refused:
        page.connect(dsn.replace(f":{u.password}@", ":wrong-Secret9@"))
    assert "wrong-Secret9" not in str(refused.value)


@pytest.mark.parametrize("dsn", ["mssql://me:pa/ss@host:1433/db", "oracle://me:pa?ss@host/svc",
                                 "sqlserver://me:12/34@host/db", "mssql://me:12#34@host/db"])
def test_an_address_cut_short_by_its_password_is_refused_without_repeating_it(dsn):
    with pytest.raises(ValueError) as refused:
        _page().connect(dsn)
    assert not any(x in str(refused.value) for x in ("pa", "ss", "12", "34", "host"))


def test_a_driver_that_repeats_the_address_does_not_repeat_the_password(monkeypatch):
    page = _page()

    def fails(spec, base):
        raise OSError(f"cannot reach {spec['dsn']} as se/cret")

    monkeypatch.setattr("ontlas.config.open_backend", fails)
    with pytest.raises(Exception) as refused:
        page.connect("mssql://me:se%2Fcret@host/db")
    assert "cret" not in str(refused.value)


def test_oracle_and_sql_server_get_the_text_their_servers_took():
    """What the live parts proved on real servers, held here for runs without one."""
    pytest.importorskip("sqlglot")
    pytest.importorskip("yaml")
    from ontlas.compile.base import compiler_for

    onto = _every_function()

    def sql(dialect: str, q) -> str:
        return compiler_for(onto, f"sql:{dialect}").compile(q).text

    down = onto.queries["categoryAncestors"].query
    assert "RECURSIVE" not in sql("oracle", down).upper() and "RECURSIVE" not in sql("mssql", down).upper()
    prices = onto.queries["skuPrices"].query
    assert "VARCHAR2(4000)" in sql("oracle", prices) and "CONVERT(NVARCHAR(4000)" in sql("tsql", prices)
    assert sql("sqlserver", prices) == sql("tsql", prices)  # the names people use for it
    flag = {"match": {"s": "Sku"}, "return": ["s.word"], "order": ["-word"], "limit": 3}
    assert "N'부족'" in sql("tsql", flag) and "TOP 3" in sql("tsql", flag) and "FETCH FIRST 3" in sql("oracle", flag)
    assert "THEN 1 WHEN NOT" in sql("oracle", flag) and "TRUE" not in sql("oracle", flag)
    days = {"match": {"i": "OrderItem"}, "return": ["i.waited"]}
    assert "DATEDIFF(" in sql("tsql", days).replace("\n", "")
    mean = {"match": {"s": "Sku"}, "return": [{"avg": "s.stock", "as": "a"}]}
    assert "AVG(CAST(" in sql("tsql", mean)
    blank = {"match": {"p": "Product"}, "where": {"eq": ["p.brand", ""]}, "return": ["p.product_id"]}
    assert "IS NULL" in sql("oracle", blank) and "IS NULL" not in sql("tsql", blank)
    grouped = {"match": {"o": "Order"}, "return": ["o.item_count", {"count": "o", "as": "n"}]}
    assert "GROUP BY" in sql("oracle", grouped) and "t_in" in sql("tsql", grouped) and "t_in" not in sql("postgres", grouped)


def test_sql_server_leaves_percent_signs_and_quotes_as_they_are():
    b = _server("mssql")
    assert b.fetch("SELECT 7 % 3") == [(1,)]
    assert b.fetch("SELECT 7 % 3 + ?", (1,)) == [(2,)]
    text = "it's 100% \ub2c8\ud2b8 ? %s"
    assert b.fetch("SELECT ?", (text,)) == [(text,)]
    assert b.fetch("SELECT 'a?b' + ?", ("c",)) == [("a?bc",)]
    assert b.fetch("SELECT 1 WHERE ? IS NULL", (None,)) == [(1,)]


def test_oracle_keeps_a_name_really_made_in_small_letters():
    pytest.importorskip("yaml")
    from ontlas.draft import _catalog, draft, studio_from

    b = _server("oracle")
    cur = b.conn.cursor()  # the backend would fold these to capitals, as it does any name it does not find
    for stmt in ('DROP TABLE "ontlas_small"', 'DROP TABLE ONTLAS_BOTH', 'DROP TABLE "ontlas_both"'):
        try:
            cur.execute(stmt)
        except Exception:  # not there yet
            pass
    cur.execute('CREATE TABLE "ontlas_small" ("id" VARCHAR2(20) PRIMARY KEY, "Label" VARCHAR2(20), PLAIN NUMBER(4))')
    cur.execute("""INSERT INTO "ontlas_small" VALUES ('a', 'x', 1)""")
    b.conn.commit()
    b.run("CREATE TABLE ontlas_note (note_id VARCHAR2(20) PRIMARY KEY)")  # the backend looks at the catalog again
    d = draft(b, name="small", tables=[t[0] for t in _catalog(b) if t[0].lower() == "ontlas_small"])
    assert [o.table for o in d.objects] == ["ontlas_small"]
    st = studio_from(d, b, graph=False)
    o = d.objects[0]
    assert st.fetch(o.name, "a")[o.key] == "a" and st.check_bindings().ok
    b.run("DROP TABLE ontlas_note")
    cur.execute('DROP TABLE "ontlas_small"')


def test_fuseki_answers_like_sqlite():
    from ontlas.backends.rdf import SparqlEndpointBackend

    url = _need("ONTLAS_LIVE_FUSEKI").rstrip("/")
    user, _, pw = os.environ.get("ONTLAS_LIVE_FUSEKI_AUTH", ":").partition(":")
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

    from ontlas.backends.graph import Neo4jBackend

    uri = _need("ONTLAS_LIVE_NEO4J")
    user, _, pw = os.environ.get("ONTLAS_LIVE_NEO4J_AUTH", "neo4j:").partition(":")
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
    from ontlas.backends.gremlin import GremlinBackend

    g = GremlinBackend(_need("ONTLAS_LIVE_GREMLIN"))
    try:
        st = _commerce(_sqlite())
        st.add_backend("gremlin", g)
        st.project()
        rep = st.conformance()
        assert rep.passed, rep.summary()
        assert all(q.outcomes["gremlin"].rows is not None for q in rep.queries)  # optional and computed included
        assert st.run("orderTotals", backend="gremlin").rows == st.run("orderTotals").rows
        assert st.run("categoryAncestors", {"category": "K3"}, backend="gremlin").rows == [("상의",), ("의류",)]
        from ontlas.ir import Query

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


def _agrees_on_every_case(backend, name: str) -> None:
    """The cases with their null values and missing objects, on this server beside SQLite."""
    from ontlas.ir import Query

    from .compile_cases import all_cases, studio_with_cases

    st = studio_with_cases(Ontology.load(EXAMPLE / "ontology.yaml"), _sqlite(), lambda: NOW)
    st.add_backend(name, backend)
    st.project()
    rep = st.conformance(queries={n: (Query.from_dict(q), p) for n, (q, p) in all_cases().items()})
    assert rep.passed, rep.summary()
    assert all(r.outcomes[name].rows is not None for r in rep.queries)


def test_gremlin_server_agrees_on_optional_links_and_computed_properties():
    pytest.importorskip("gremlin_python")
    from ontlas.backends.gremlin import GremlinBackend

    g = GremlinBackend(_need("ONTLAS_LIVE_GREMLIN"))
    try:
        _agrees_on_every_case(g, "gremlin")
    finally:
        g.close()


def test_neo4j_agrees_on_conditional_aggregates():
    pytest.importorskip("neo4j")
    import neo4j

    from ontlas.backends.graph import Neo4jBackend

    uri = _need("ONTLAS_LIVE_NEO4J")
    user, _, pw = os.environ.get("ONTLAS_LIVE_NEO4J_AUTH", "neo4j:").partition(":")
    driver = neo4j.GraphDatabase.driver(uri, auth=(user, pw))
    try:
        _agrees_on_every_case(Neo4jBackend(driver), "neo")
    finally:
        driver.close()


def test_fuseki_agrees_on_conditional_aggregates():
    from ontlas.backends.rdf import SparqlEndpointBackend

    url = _need("ONTLAS_LIVE_FUSEKI").rstrip("/")
    user, _, pw = os.environ.get("ONTLAS_LIVE_FUSEKI_AUTH", ":").partition(":")
    _agrees_on_every_case(SparqlEndpointBackend(f"{url}/query", update_url=f"{url}/update", gsp_url=f"{url}/data",
                                                user=user, password=pw), "fuseki")


def test_oracle_runs_sql_pgq_like_sqlite():
    """Oracle 23 has GRAPH_TABLE, so the compiled text and CREATE PROPERTY GRAPH run as they are; dates are real
    TIMESTAMP columns here, where SQLite keeps text."""
    from collections import Counter
    from datetime import datetime as dt
    from urllib.parse import urlsplit

    u = urlsplit(_need("ONTLAS_LIVE_ORACLE"))
    oracledb = pytest.importorskip("oracledb")

    from ontlas.compile.base import CompileError, compiler_for
    from ontlas.compile.pgq import graph_ddl
    from ontlas.conformance import normalize_rows
    from ontlas.ir import Query

    from .compile_cases import OPTIONALS, all_cases, studio_with_cases

    source = _sqlite()
    st = studio_with_cases(Ontology.load(EXAMPLE / "ontology.yaml"), source, lambda: NOW)
    conn = oracledb.connect(user=u.username, password=u.password, dsn=f"{u.hostname}:{u.port}{u.path}")
    cur = conn.cursor()
    tables = [o.table for o in st.onto.objects.values() if o.table] + [lk.via.table for lk in st.onto.links.values() if lk.via]
    for drop in ['PROPERTY GRAPH "commerce_sample"', *(f'TABLE "{t}" CASCADE CONSTRAINTS' for t in tables)]:
        try:
            cur.execute(f"DROP {drop}")
        except oracledb.Error:  # not there yet
            pass
    for t in tables:
        cols = source.conn.execute(f'pragma table_info("{t}")').fetchall()
        when = {c[1] for c in cols if c[1].endswith("_at")}
        kinds = {"INTEGER": "NUMBER", "REAL": "NUMBER", "TEXT": "VARCHAR2(400)"}
        cur.execute(f'CREATE TABLE "{t}" (' + ", ".join(
            f'"{c[1]}" {"TIMESTAMP" if c[1] in when else kinds[c[2]]}' for c in cols) + ")")
        rows = [tuple(dt.fromisoformat(v) if c[1] in when and v else v for c, v in zip(cols, r))
                for r in source.conn.execute(f'SELECT * FROM "{t}"').fetchall()]
        if rows:
            cur.executemany(f'INSERT INTO "{t}" VALUES ({", ".join(f":{i + 1}" for i in range(len(cols)))})', rows)
    conn.commit()
    cur.execute(graph_ddl(st.onto))
    ran = 0
    try:
        for name, (d, params) in all_cases().items():
            q = Query.from_dict(d)
            try:
                c = compiler_for(st.onto, "sqlpgq").compile(q)
            except CompileError:
                assert name in OPTIONALS, name  # no OPTIONAL MATCH in GRAPH_TABLE
                continue
            parts = c.text.split("?")
            text = parts[0] + "".join(f":{i}{p}" for i, p in enumerate(parts[1:], 1))
            cur.execute(text, list(c.bind(params)[1]))
            got = Counter(normalize_rows(cur.fetchall(), c.columns, c.column_types))
            want = Counter(normalize_rows(st.run(q, params).rows, c.columns, c.column_types))
            assert got == want, (name, list((got - want))[:3], list((want - got))[:3])
            ran += 1
        assert ran >= 20
    finally:
        cur.execute('DROP PROPERTY GRAPH "commerce_sample"')
        for t in tables:
            cur.execute(f'DROP TABLE "{t}" CASCADE CONSTRAINTS')
        conn.close()


@pytest.mark.parametrize(("kind", "var", "driver"), [("postgres", "ONTLAS_LIVE_PG", "psycopg"),
                                                     ("mysql", "ONTLAS_LIVE_MYSQL", "pymysql"),
                                                     ("oracle", "ONTLAS_LIVE_ORACLE", "oracledb"),
                                                     ("mssql", "ONTLAS_LIVE_MSSQL", "pymssql")])
def test_a_studio_is_drafted_from_the_catalog_and_runs(kind, var, driver):
    dsn = _need(var)
    pytest.importorskip(driver)
    pytest.importorskip("sqlglot")
    from pathlib import Path

    from ontlas.actions import SqlWriteback
    from ontlas.bindings import check_bindings
    from ontlas.config import open_backend
    from ontlas.draft import _catalog, draft, studio_from
    from ontlas.ir import Column, Edge, Query, Ref

    b = open_backend({"kind": kind, "dsn": dsn}, Path("."))
    for t in ("ontlas_ship", "ontlas_line", "ontlas_ord"):
        try:
            b.run(f"DROP TABLE {t}")
        except Exception:  # not there yet
            pass
    text, big = {"oracle": ("VARCHAR2(20)", "CLOB"), "postgres": ("VARCHAR(20)", "JSON"),
                 "mssql": ("NVARCHAR(20)", "NVARCHAR(MAX)")}.get(kind, ("VARCHAR(20)", "TEXT"))
    for stmt in [
        f"CREATE TABLE ontlas_ord (ord_no {text} PRIMARY KEY, memo {big}, status {text})",
        f"CREATE TABLE ontlas_line (ord_no {text} NOT NULL, line_seq INTEGER NOT NULL, proc_seq INTEGER NOT NULL, "
        "qty INTEGER, PRIMARY KEY (ord_no, line_seq, proc_seq), FOREIGN KEY (ord_no) REFERENCES ontlas_ord (ord_no))",
        f"CREATE TABLE ontlas_ship (ship_no {text} PRIMARY KEY, ord_no {text}, line_seq INTEGER, proc_seq INTEGER, "
        "FOREIGN KEY (ord_no, line_seq, proc_seq) REFERENCES ontlas_line (ord_no, line_seq, proc_seq))",
        "INSERT INTO ontlas_ord VALUES ('O1', '{}', 'NEW')", "INSERT INTO ontlas_ord VALUES ('O2', '{}', 'NEW')",
        "INSERT INTO ontlas_line VALUES ('O1', 1, 0, 2)", "INSERT INTO ontlas_line VALUES ('O1', 1, 1, 3)",
        "INSERT INTO ontlas_ship VALUES ('S1', 'O1', 1, 1)",
    ]:
        b.run(stmt)
    d = draft(b, name="live", lang="ko", tables=[t[0] for t in _catalog(b) if t[0].lower().startswith("ontlas_")])
    assert d.skipped == []
    st = studio_from(d, b, graph=False)
    objs = {o.table.lower(): o for o in st.onto.objects.values()}
    line, ship = objs["ontlas_line"], objs["ontlas_ship"]
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
    for t in ("ontlas_ship", "ontlas_line", "ontlas_ord"):
        b.run(f"DROP TABLE {t}")
