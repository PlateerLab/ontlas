import pytest

from xgen_space.backends.base import Capabilities
from xgen_space.backends.graph import CallableBackend
from xgen_space.backends.gremlin import GremlinBackend
from xgen_space.compile.base import CompileError, compiler_for
from xgen_space.expr import GremlinRenderer, parse_expr


def test_gremlin_text_carries_names_and_every_value_as_a_binding(studio):
    c = compiler_for(studio.onto, "gremlin").compile(studio.query("lowStock"))
    assert c.style == "named" and c.text.startswith("g.V().hasLabel('Sku')")
    text, binds = c.bind({"threshold": 5})
    assert "P.lt(threshold)" in text and binds["threshold"] == 5 and ["M", "L"] in binds.values()
    assert "'M'" not in text and "5)" not in text
    c = compiler_for(studio.onto, "gremlin").compile(studio.query("revenueByCategory").__class__.from_dict(
        {"match": {"k": "Category", "a": "Category"}, "edges": [{"from": "k", "link": "broader", "to": "a",
                                                                  "hops": [2, 3]}],
         "where": {"eq": ["k.name", "니트"]}, "return": ["a.name"]}))
    assert ".repeat(__.out('broader')).emit(__.loops().is(P.gte(2))).times(3)" in c.text and "니트" not in c.text


def test_gremlin_says_what_it_does_not_do(studio):
    gremlin = compiler_for(studio.onto, "gremlin")
    with pytest.raises(CompileError, match="cycle"):
        gremlin.compile({"match": {"a": "Category", "b": "Category"},
                         "edges": [["a", "broader", "b"], ["b", "narrower", "a"]], "return": ["a.name"]})
    b = CallableBackend("g", Capabilities("gremlin", "tinkerpop", optional=False, computed="none"), lambda t, a: [])
    assert b.unsupported(studio.query("orderTotals"), studio.onto) == ["computed properties"]
    assert b.unsupported(studio.query("ordersPerCustomer"), studio.onto) == ["optional"]


def test_gremlin_declares_optional_links_and_computed_properties(studio):
    b = GremlinBackend(client=object())
    assert b.unsupported(studio.query("orderTotals"), studio.onto) == []
    assert b.unsupported(studio.query("ordersPerCustomer"), studio.onto) == []
    assert all(b.unsupported(q, studio.onto) == [] for q, _ in studio.registered().values())


def test_an_optional_edge_labels_a_null_and_the_steps_after_it_test_for_one(studio):
    c = compiler_for(studio.onto, "gremlin").compile({
        "match": {"c": "Customer", "o": "Order", "i": "OrderItem"},
        "edges": [{"from": "c", "link": "placed", "to": "o", "optional": True},
                  {"from": "o", "link": "hasItem", "to": "i", "optional": True}],
        "where": {"ne": ["o.status", "PAID"]}, "return": ["c.name", "i.quantity", {"count": "o", "as": "n"}]})
    assert ".select('c').coalesce(__.out('placed').hasLabel('Order'), __.constant(null)).as('o')" in c.text
    assert ".select('o').coalesce(__.is(P.neq(null)).out('hasItem').hasLabel('OrderItem'), __.constant(null)).as('i')" in c.text
    # values(), has() and id() stop the traversal on a null, and neq alone would let one pass
    assert "__.coalesce(__.select('i').is(P.neq(null)).values('quantity'), __.constant(null))" in c.text
    assert "__.coalesce(__.select('o').is(P.neq(null)).id(), __.constant(null))" in c.text
    assert ".is(P.neq(null)).is(P.neq(_v1))" in c.text


def test_a_computed_property_is_a_traversal_with_its_literals_as_bindings(studio):
    c = compiler_for(studio.onto, "gremlin").compile(studio.query("customerValue"))
    assert "'CANCELLED'" not in c.text and "__.math('x0 * x1')" in c.text
    text, binds = c.bind({"least": 50000})
    assert "CANCELLED" in binds.values() and binds["least"] == 50000
    assert len(binds) == 3  # spent is read twice and holds the same 0 twice over; servers allow 16 bindings
    assert "__.coalesce(" in text and ".fold().choose(__.count(local).is(0), __.constant(null), __.unfold().sum())" in text


def test_gremlin_guards_every_step_that_would_stop_on_a_null(studio):
    gremlin = compiler_for(studio.onto, "gremlin")
    text = gremlin.compile({"match": {"s": "Sku"}, "return": ["s.last_price"]}).text
    assert ".has('changed_at').order().by('changed_at', desc).by(__.values('change_id').asString(), desc).limit(1)" in text
    assert text.count("__.coalesce(__.select('s')") == 1  # no price change: null, and not a row left out
    r = GremlinRenderer(lambda n: f"__.p('{n.name}')", None, lambda n: "_v")
    divide = r.render(parse_expr("a / b"))
    assert "__.choose(__.select('x1').is(P.eq(0)), __.constant(null), __.math('x0 / x1'))" in divide
    assert divide.startswith("__.project('x0', 'x1').by(__.p('a')).by(__.p('b')).choose(__.select(values).unfold().is(P.eq(null))")
    assert "__.select(values).conjoin('')" in r.render(parse_expr("concat(a, b)"))  # concat() would leave a null out
    assert ".choose(__.select(values).unfold().is(P.eq(false)), __.constant(false)," in r.render(parse_expr("a and b"))
    assert ".asString().substring(5, 7).asNumber()" in r.render(parse_expr("month(a)"))
    assert "dateDiff" not in r.render(parse_expr("days_between(a, b)"))  # its unit differs between releases
    assert "signum(_) * floor(abs(_) * 100 + 0.5) / 100" in r.render(parse_expr("round(a, 2)"))


def test_whole_numbers_from_math_come_back_whole(studio):
    class Client:
        def submit(self, text, bindings):
            return self

        def all(self):
            return self

        def result(self):
            return [{"item_id": "I1", "quantity": 3.0, "line_total": 3.5}]

    b = GremlinBackend(client=Client())
    c = b.compiler(studio.onto).compile({"match": {"i": "OrderItem"}, "return": ["i.item_id", "i.quantity", "i.line_total"]})
    assert repr(b.execute(c).rows) == "[('I1', 3, 3.5)]"
