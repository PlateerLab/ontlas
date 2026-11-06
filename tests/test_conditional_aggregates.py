import pytest

from xgen_space import Ontology
from xgen_space.backends.base import Capabilities
from xgen_space.backends.graph import CallableBackend
from xgen_space.check import CheckError
from xgen_space.compile.base import compiler_for
from xgen_space.compile.pgq import graph_ddl
from xgen_space.expr import ExprError, dependencies, parse_expr
from xgen_space.ir import Agg, Column, Exists, IRError, Query, Ref
from xgen_space.roles import mask_style

from .compile_cases import COLUMNS, PARAMETER_VALUES, PARAMETERS, all_cases, studio_with_cases
from .conftest import NOW


@pytest.fixture
def cases(onto, source):
    return studio_with_cases(onto, source, lambda: NOW)


@pytest.fixture
def graph_cases(cases):
    pytest.importorskip("rdflib")
    from xgen_space.backends.rdf import RdflibBackend

    cases.add_backend("graph", RdflibBackend())
    cases.project()
    return cases


def test_an_aggregate_reads_its_condition_on_the_last_object_of_the_path():
    node = parse_expr("sum(hasItem.quantity where item_status = 'NORMAL')")
    assert (node.fn, node.path, node.prop) == ("sum", ("hasItem",), "quantity") and node.where.op == "="
    assert parse_expr("count(placed.hasItem where quantity > 1 and quantity < 5)").where.op == "and"
    assert parse_expr("sum(hasItem.quantity)").where is None
    assert parse_expr("where + 1").left.name == "where"  # only inside an aggregate is it a word of the language


def test_a_condition_is_checked_against_the_definition(onto):
    d = onto.to_dict()
    props = d["objects"]["Order"]["properties"]
    props["a"] = {"type": "integer", "expr": "count(hasItem where quantity)"}
    props["b"] = {"type": "integer", "expr": "count(hasItem where status = 'PAID')"}  # a property of Order, not its item
    props["c"] = {"type": "integer", "expr": "count(hasItem where item_status + 1 > 0)"}
    props["d"] = {"type": "integer", "expr": "count(hasItem where delivered_at > 'soon')"}
    issues = Ontology.from_dict(d).validate()
    assert any("Order.a: 'where' takes a true/false value, not integer" in i for i in issues)
    assert any("Order.b: OrderItem has no property 'status'" in i for i in issues)
    assert any("Order.c: '+' takes numbers" in i for i in issues)
    assert any("Order.d: cannot compare datetime with string" in i for i in issues)
    with pytest.raises(ExprError, match="expected"):
        parse_expr("sum(hasItem.quantity where)")


def test_a_computed_property_can_read_a_date_comparison_through_another(onto):
    d = onto.to_dict()
    items = d["objects"]["OrderItem"]["properties"]
    items["wrapped"] = {"type": "string", "expr": "if(delivered_at > '2026-10-20', 'late', 'early')"}
    items["is_late"] = {"type": "boolean", "expr": "wrapped = 'late'"}
    d["objects"]["Order"]["properties"]["lates"] = {"type": "integer", "expr": "count(hasItem where wrapped = 'late')"}
    assert Ontology.from_dict(d).validate() == []


def test_what_a_condition_reads_counts_as_a_dependency_and_masks_the_result(onto):
    d = onto.to_dict()
    customer = d["objects"]["Customer"]["properties"]
    customer["vip_order"] = {"type": "integer", "expr": "count(placedBy where status = 'PAID')"}
    d["objects"]["Order"]["properties"]["phoned"] = {
        "type": "integer", "expr": "count(placedBy where phone = '010-5550-0101')"}
    d["objects"]["Order"]["properties"]["by_grade"] = {"type": "integer", "expr": "count(placedBy where grade = 'VIP')"}
    del customer["vip_order"]
    o = Ontology.from_dict(d)
    assert dependencies(o, "Order", "by_grade") == {("Customer", "grade")}
    assert dependencies(o, "Order", "phoned") == {("Customer", "phone")}
    assert mask_style(o, o.roles["support_agent"], "Order", "phoned") == "full"
    assert mask_style(o, o.roles["support_agent"], "Order", "by_grade") == ""


def test_conditional_aggregates_answer_alike_from_sql_and_the_graph(graph_cases):
    st = graph_cases
    orders = st.run({"match": {"o": "Order"}, "return": ["o.order_id", "o.normal_qty", "o.returning", "o.not_normal", "o.dear",
                                                         "o.cheap", "o.late", "o.balance", "o.any_return"],
                     "order": ["order_id"]}).rows
    assert orders[0] == ("O1", 1, 1, 1, 59000.0, 59000.0, 2, 21000.0, 1)
    assert orders[5] == ("O6", None, 0, 0, None, None, 0, 0, 0)  # no items: a sum of nothing is null, a count is 0
    assert st.run({"match": {"s": "Sku"}, "return": ["s.sku_id", "s.low_last", "s.high_first", "s.recent"],
                   "order": ["sku_id"]}).rows[:2] == [("S1", 59000.0, 69000.0, 1), ("S2", 59000.0, 69000.0, 1)]
    assert st.run({"match": {"c": "Customer"}, "return": ["c.customer_id", "c.big", "c.nested"],
                   "order": ["customer_id"]}).rows[:2] == [("C001", 1, 0), ("C002", 1, 1)]


def test_every_case_agrees_between_sql_and_the_graph(graph_cases):
    st = graph_cases
    rep = st.conformance(queries={n: (Query.from_dict(q), p) for n, (q, p) in all_cases().items()})
    assert rep.passed, rep.summary()
    assert all(o.rows is not None for r in rep.queries for o in r.outcomes.values())


def test_a_column_aggregates_only_the_rows_its_where_keeps(cases):
    rows = cases.run(COLUMNS["every aggregate"]).rows
    assert rows[:3] == [("CANCELLED", 1, 19000.0, 19000.0, 19000.0, 1, 1, 1, 1, 1),
                        ("DELIVERED", 3, pytest.approx(44333.33, abs=0.01), 15000.0, 59000.0, 3, 3, 3, 3, 4),
                        ("SHIPPED", 1, 59000.0, 59000.0, 59000.0, 1, 1, 1, 1, 1)]
    assert cases.run(COLUMNS["no group key"]).rows == [(8, 8, None, 0)]
    assert cases.run(COLUMNS["no row at all"]).rows == [(None, 0)]


def test_a_columns_parameters_bind_before_the_querys_own(cases, onto):
    assert cases.run(PARAMETERS, PARAMETER_VALUES).rows == [("DELIVERED", 3, 1), ("SHIPPED", 1, 0)]
    for lang in ("sql:sqlite", "sqlpgq"):
        c = compiler_for(onto, lang).compile(PARAMETERS)
        assert c.params == ["state", "least", "skip"], lang
        assert c.text.index("i__item_status" if lang == "sqlpgq" else '"item_status"') < c.text.rindex("?")


def test_a_conditional_column_survives_the_document_form():
    q = Query.from_dict(COLUMNS["every aggregate"])
    assert Query.from_dict(q.to_dict()) == q
    assert isinstance(q.columns[1].expr.where.ref, Ref) and q.columns[-1].expr.where is None


def test_a_columns_where_is_checked_like_the_querys(onto):
    sql = compiler_for(onto, "sql:sqlite")

    def query(where):
        return {"match": {"i": "OrderItem"}, "return": [{"count": "*", "where": where, "as": "n"}]}

    with pytest.raises(CheckError, match="unknown alias 'x'"):
        sql.compile(query({"eq": ["x.quantity", 1]}))
    with pytest.raises(CheckError, match="has no property 'nope'"):
        sql.compile(query({"eq": ["i.nope", 1]}))
    with pytest.raises(CheckError, match="not a valid integer"):
        sql.compile(query({"eq": ["i.quantity", "many"]}))
    with pytest.raises(IRError):
        Query.from_dict(query({"bogus": ["i.quantity", 1]}))


def test_a_columns_where_stays_on_its_row_and_off_what_a_role_sees_masked(studio):
    """Neither passes through the role checks on the query's where, so a role could count its way to a hidden value."""
    masked = {"match": {"c": "Customer"}, "return": [{"count": "*", "where": {"eq": ["c.phone", "010-5550-0101"]}, "as": "n"}]}
    with pytest.raises(CheckError, match="masked for customer_agent, support_agent"):
        studio.run(masked, role="support_agent")
    with pytest.raises(CheckError, match="masked"):
        studio.run(masked)
    outside = {"exists": {"match": {"o": "Order"}, "edges": [["c", "placed", "o"]]}}
    with pytest.raises(CheckError, match="exists belongs in the query's where"):
        studio.run({"match": {"c": "Customer"}, "return": [{"count": "*", "where": outside, "as": "n"}]})
    q = Query(nodes={"c": "Customer"}, columns=[Column(Agg("count", where=Exists({"o": "Order"}, [])), "n")])
    with pytest.raises(CheckError):
        compiler_for(studio.onto, "cypher").compile(q)
    assert studio.run({"match": {"c": "Customer"}, "return": [{"count": "*", "where": {"eq": ["c.grade", "VIP"]}, "as": "n"}]},
                      role="support_agent").rows == [(1,)]


def test_a_backend_refuses_what_a_columns_where_uses(studio):
    q = studio.query({"match": {"p": "Product"}, "return": [{"count": "*", "where": {"contains": ["p.name", "니트"]}, "as": "n"}]})
    b = CallableBackend("g", Capabilities("gql", "iso", contains=False), lambda t, a: [])
    assert b.unsupported(q, studio.onto) == ["contains"]
    i = studio.query({"match": {"i": "OrderItem"}, "return": [{"count": "*", "where": {"gt": ["i.line_total", 1]}, "as": "n"}]})
    none = CallableBackend("n", Capabilities("gremlin", computed="none"), lambda t, a: [])
    assert none.unsupported(i, studio.onto) == ["computed properties"]


def test_every_language_writes_a_conditional_column(onto):
    q = COLUMNS["no row kept"]
    sql = compiler_for(onto, "sql:sqlite").compile(q).text
    assert 'SUM(CASE WHEN t_i."item_status" = ? THEN t_i."quantity" END)' in sql
    assert 'COUNT(CASE WHEN t_i."item_status" = ? THEN 1 END)' in sql
    cypher = compiler_for(onto, "cypher").compile(q).text
    assert "count(CASE WHEN i.`item_status` = $_v2 THEN 1 END)" in cypher
    # sum() of no rows is 0 in Cypher and null everywhere else
    assert "CASE WHEN count(CASE WHEN i.`item_status` = $_v1 THEN i.`quantity` END) = 0 THEN null ELSE sum(" in cypher
    gql = compiler_for(onto, "gql").compile(q).text
    assert "sum(CASE WHEN i.`item_status` = $_v1 THEN i.`quantity` END) AS `s`" in gql and "GROUP BY `status`" in gql
    pgq = compiler_for(onto, "sqlpgq").compile(q).text
    assert 'SUM(CASE WHEN gt."i__item_status" = ? THEN gt."i__quantity" END) AS "s"' in pgq
    assert 'i."item_status" AS "i__item_status"' in pgq and 'GROUP BY gt."status"' in pgq
    sparql = compiler_for(onto, "sparql").compile(q).text
    assert " UNION " in sparql and "SUM(?i__quantity)" in sparql and "IF(" not in sparql.split("WHERE")[1]
    gremlin = compiler_for(onto, "gremlin").compile(q).text
    assert "__.choose(__.select('i').has('item_status', P.eq(_v1))" in gremlin


@pytest.mark.parametrize("dialect", ["mysql", "oracle", "tsql", "snowflake", "bigquery"])
def test_a_conditional_column_reaches_other_sql_dialects(onto, dialect):
    pytest.importorskip("sqlglot")
    assert "CASE WHEN" in compiler_for(onto, f"sql:{dialect}").compile(COLUMNS["no row kept"]).text


def test_a_conditional_aggregate_in_each_language(onto):
    d = onto.to_dict()
    d["objects"]["Order"]["properties"]["kept"] = {"type": "integer", "expr": "sum(hasItem.quantity where item_status = 'NORMAL')"}
    d["objects"]["Sku"]["properties"]["low"] = {"type": "decimal", "expr": "latest(priceChanges.price where price < 60000)"}
    o = Ontology.from_dict(d).check()
    q = {"match": {"o": "Order"}, "return": ["o.kept"]}
    assert """AND (t_g1."item_status" = 'NORMAL')""" in compiler_for(o, "sql:sqlite").compile(q).text
    assert "(o)-[:`hasItem`]->(g1:`OrderItem`) WHERE (g1.`item_status` = 'NORMAL') |" in compiler_for(o, "cypher").compile(q).text
    assert "WHERE (g1.`item_status` = 'NORMAL') RETURN SUM(g1.`quantity`) AS v }" in compiler_for(o, "gql").compile(q).text
    assert """AND (s1."g2__item_status" = 'NORMAL'))""" in compiler_for(o, "sqlpgq").compile(q).text
    assert 'FILTER((?g1__item_status = "NORMAL"))' in compiler_for(o, "sparql").compile(q).text
    assert ".where(__.project('x0', 'x1')" in compiler_for(o, "gremlin").compile(q).text
    latest = {"match": {"s": "Sku"}, "return": ["s.low"]}
    gql = compiler_for(o, "gql").compile(latest).text
    assert "WHERE g1.`changed_at` IS NOT NULL AND (g1.`price` < 60000) ORDER BY g1.`changed_at` DESC" in gql
    assert "LIMIT 1 RETURN g1.`price` AS v }" in gql
    pgq = compiler_for(o, "sqlpgq").compile(latest).text
    assert "FETCH FIRST 1 ROW ONLY)" in pgq and 'ORDER BY s1."g2__changed_at" DESC' in pgq


def test_gql_follows_links_in_a_value_subquery(onto):
    gql = compiler_for(onto, "gql")
    text = gql.compile({"match": {"o": "Order"}, "return": ["o.order_id", "o.total", "o.item_count"]}).text
    assert "coalesce(VALUE { MATCH (o)-[:`hasItem`]->(g1:`OrderItem`) RETURN SUM((g1.`unit_price` * g1.`quantity`)) AS v }, 0)" in text
    assert "VALUE { MATCH (o)-[:`hasItem`]->(g2:`OrderItem`) RETURN COUNT(*) AS v }" in text
    assert "VALUE { MATCH (o)<-[:`priceOf`]-" not in text
    nested = gql.compile({"match": {"c": "Customer"}, "return": ["c.spent"]}).text
    assert nested.count("VALUE {") == 2  # billed reads total, itself over links
    prices = gql.compile({"match": {"s": "Sku"}, "return": ["s.last_price", "s.first_price"]}).text
    assert "(s)<-[:`priceOf`]-(g1:`PriceChange`)" in prices and "`change_id` DESC LIMIT 1" in prices and " ASC LIMIT 1" in prices


def test_pgq_works_out_link_aggregates_around_graph_table(onto):
    pgq = compiler_for(onto, "sqlpgq")
    text = pgq.compile({"match": {"o": "Order"}, "return": ["o.order_id", "o.total"]}).text
    assert "FROM (SELECT b.*, COALESCE((SELECT SUM((s1.\"g2__unit_price\" * s1.\"g2__quantity\")) FROM GRAPH_TABLE (" in text
    assert 'MATCH (k1 IS "Order")-[e2 IS "hasItem"]->(g2 IS "OrderItem") COLUMNS (' in text
    assert 's1."k1__order_id" = b."o__order_id"), 0) AS "total"' in text and ") b) gt" in text
    # no subquery inside the graph pattern: a filter on it moves out, and it is written once for both uses
    value = pgq.compile({"match": {"c": "Customer"}, "where": {"gte": ["c.spent", {"param": "least"}]},
                         "return": ["c.customer_id", "c.spent"]})
    assert 'WHERE gt."spent" >= ?' in value.text and value.text.count('AS "spent"') == 2  # the derived column, the select
    assert value.text.count('MATCH (c IS "Customer")\n  COLUMNS') == 1 and value.params == ["least"]
    group = pgq.compile({"match": {"o": "Order"}, "return": ["o.total", {"count": "*", "as": "n"}]}).text
    assert 'GROUP BY gt."total"' in group  # a column, as GROUP BY needs, not the subquery
    plain = pgq.compile({"match": {"i": "OrderItem"}, "where": {"gt": ["i.line_total", 1]}, "return": ["i.item_id"]}).text
    assert 'WHERE (i."unit_price" * i."quantity") > ?' in plain and "SELECT b.*" not in plain


def test_gql_and_pgq_read_dates_by_the_means_each_standard_has(onto):
    d = onto.to_dict()
    p = d["objects"]["OrderItem"]["properties"]
    p["yr"] = {"type": "integer", "expr": "year(delivered_at)"}
    p["mo"] = {"type": "integer", "expr": "month(delivered_at)"}
    p["days"] = {"type": "integer", "expr": "days_between(delivered_at, '2026-10-30')"}
    o = Ontology.from_dict(d).check()
    q = {"match": {"i": "OrderItem"}, "return": ["i.yr", "i.mo", "i.days"]}
    gql = compiler_for(o, "gql").compile(q).text
    assert "CAST(LEFT(CAST(i.`delivered_at` AS STRING), 4) AS INT)" in gql
    assert "CAST(RIGHT(LEFT(CAST(i.`delivered_at` AS STRING), 7), 2) AS INT)" in gql and "32045" in gql
    pgq = compiler_for(o, "sqlpgq").compile(q).text
    assert 'EXTRACT(YEAR FROM CAST(i."delivered_at" AS TIMESTAMP))' in pgq
    assert "EXTRACT(MONTH FROM CAST(DATE '2026-10-30' AS TIMESTAMP))" in pgq and "32045" in pgq


def test_pgq_writes_what_oracle_needs_written_out(onto):
    """Each of these ran on Oracle 23 and failed there, or gave another answer, before it was written this way."""
    assert 'KEY ("customer_id", "product_id") SOURCE KEY ("customer_id")' in graph_ddl(onto)  # a join table has no key
    d = onto.to_dict()
    p = d["objects"]["OrderItem"]["properties"]
    p["late"] = {"type": "boolean", "expr": "delivered_at > '2026-10-20'"}
    p["days"] = {"type": "integer", "expr": "days_between(delivered_at, '2026-10-30')"}
    p["rnd"] = {"type": "decimal", "expr": "round(unit_price / 7, 2)"}
    p["shown"] = {"type": "string", "expr": "concat(item_status, '/')"}
    o = Ontology.from_dict(d).check()
    text = compiler_for(o, "sqlpgq").compile({"match": {"i": "OrderItem"}, "return": ["i.late", "i.days", "i.rnd", "i.shown"]}).text
    assert "TIMESTAMP '2026-10-20 00:00:00'" in text and "CAST(DATE '2026-10-30' AS TIMESTAMP)" in text
    assert "AS DECIMAL(38, 18)), 2)" in text  # NUMERIC alone is a whole number there
    assert """(CASE WHEN i."item_status" IS NULL OR '/' IS NULL THEN NULL ELSE i."item_status" || '/' END)""" in text
    q = {"match": {"p": "Product"}, "where": {"contains": ["p.name", {"param": "t"}]}, "return": ["p.name"]}
    assert 'INSTR(p."name", ?) > 0' in compiler_for(o, "sqlpgq").compile(q).text
    assert 'POSITION(? IN p."name") > 0' in compiler_for(o, "sqlpgq:postgres").compile(q).text


def test_a_date_literal_is_whole_where_it_meets_a_datetime(onto):
    d = onto.to_dict()
    d["objects"]["OrderItem"]["properties"]["late"] = {"type": "boolean", "expr": "delivered_at > '2026-10-20'"}
    d["objects"]["OrderItem"]["properties"]["bad"] = {"type": "integer", "expr": "year('2026-13-40')"}
    assert any("OrderItem.bad: '2026-13-40' is not a date" in i for i in Ontology.from_dict(d).validate())
    del d["objects"]["OrderItem"]["properties"]["bad"]
    q = {"match": {"i": "OrderItem"}, "return": ["i.late"]}
    text = compiler_for(Ontology.from_dict(d).check(), "sparql").compile(q).text
    assert '"2026-10-20T00:00:00"^^<http://www.w3.org/2001/XMLSchema#dateTime>' in text  # without the time it is not one


def test_sparql_nests_an_optional_inside_the_one_it_hangs_from(onto):
    edges = [{"from": "c", "link": "placed", "to": "o", "optional": True},
             {"from": "o", "link": "hasItem", "to": "i", "optional": True}]
    q = {"match": {"c": "Customer", "o": "Order", "i": "OrderItem"}, "edges": edges, "return": ["c.name", "i.item_id"]}
    text = compiler_for(onto, "sparql").compile(q).text
    placed, items = "OPTIONAL { ?c <https://example.org/commerce#placed>", "OPTIONAL { ?o <https://example.org/commerce#hasItem>"
    assert text.index(placed) < text.index(items)
    assert f"\n  {items}" not in text  # not beside it: an unbound ?o would match every order's items
