import pytest

from xgen_space.backends.base import Capabilities
from xgen_space.backends.graph import CallableBackend
from xgen_space.compile.base import CompileError, compiler_for


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
    with pytest.raises(CompileError, match="optional"):
        gremlin.compile(studio.query("ordersPerCustomer"))
    with pytest.raises(CompileError, match="computed"):
        gremlin.compile(studio.query("orderTotals"))
    b = CallableBackend("g", Capabilities("gremlin", "tinkerpop", optional=False, computed="none"), lambda t, a: [])
    assert b.unsupported(studio.query("orderTotals"), studio.onto) == ["computed properties"]
    assert b.unsupported(studio.query("ordersPerCustomer"), studio.onto) == ["optional"]
