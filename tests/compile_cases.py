"""Computed properties, conditional aggregates and optional links to run on every engine at hand, over rows that hold
what is easy to get wrong: a customer with no orders, an order with no items, null values and null group keys."""
from xgen_space import Ontology
from xgen_space.studio import Studio

COMPUTED = {
    "Order": {
        "normal_qty": ("integer", "sum(hasItem.quantity where item_status = 'NORMAL')"),
        "returning": ("integer", "count(hasItem where item_status != 'NORMAL')"),
        "not_normal": ("integer", "count(hasItem where not (item_status = 'NORMAL'))"),
        "dear": ("decimal", "max(hasItem.unit_price where quantity >= 1)"),
        "cheap": ("decimal", "min(hasItem.unit_price where item_status = 'NORMAL')"),
        "mean_line": ("decimal", "avg(hasItem.line_total where quantity > 0)"),
        "late": ("integer", "count(hasItem.delivered_at where delivered_at > '2026-10-20')"),
        "balance": ("decimal", "coalesce(sum(hasItem.line_total where item_status = 'NORMAL'), 0) "
                               "- coalesce(sum(hasItem.line_total where item_status != 'NORMAL'), 0)"),
        "any_return": ("boolean", "count(hasItem where item_status = 'RETURN_REQUESTED') > 0"),
    },
    "Customer": {
        "big": ("integer", "count(placed where total > 60000)"),
        "delivered_sum": ("decimal", "sum(placed.total where status = 'DELIVERED')"),
        "deep": ("integer", "sum(placed.hasItem.quantity where item_status = 'NORMAL')"),
        "nested": ("integer", "count(placed where count(hasItem where item_status = 'NORMAL') > 1)"),
    },
    "Sku": {
        "low_last": ("decimal", "latest(priceChanges.price where price < 60000)"),
        "high_first": ("decimal", "earliest(priceChanges.price where price > 60000)"),
        "recent": ("integer", "count(priceChanges where changed_at >= '2026-10-01')"),
    },
    "OrderItem": {
        "per_unit": ("decimal", "line_total / (quantity - quantity)"),
        "wrapped": ("string", "if(delivered_at > '2026-10-20', 'late', 'early')"),
        "days": ("integer", "days_between(delivered_at, '2026-10-30')"),
        "shown": ("string", "concat(lower(item_status), '/', upper(item_id))"),
        "yr": ("integer", "year(delivered_at)"),
        "mo": ("integer", "month(delivered_at)"),
        "dy": ("integer", "day(delivered_at)"),
        "neg": ("integer", "-quantity"),
        "third": ("decimal", "unit_price / 3"),
        "rnd": ("decimal", "round(unit_price / 7, 2)"),
        "rnd0": ("integer", "round(unit_price / 7)"),
        "fl": ("integer", "floor(unit_price / 7)"),
        "ce": ("integer", "ceil(unit_price / 7)"),
        "ab": ("integer", "abs(0 - quantity)"),
        "ln": ("integer", "length(item_status)"),
        "both": ("boolean", "quantity > 1 and item_status = 'NORMAL'"),
        "either": ("boolean", "quantity > 1 or item_status = 'NORMAL'"),
        "neither": ("boolean", "not (quantity > 1)"),
        "fallback": ("string", "coalesce(item_status, 'NONE')"),
    },
}

ROWS = """
INSERT INTO customers VALUES ('C004', NULL, NULL, NULL), ('C005', '정우진', 'BASIC', NULL);
INSERT INTO orders VALUES ('O5', 'C003', NULL, NULL), ('O6', 'C004', '2026-10-29T00:00:00', 'PAID');
INSERT INTO order_items (item_id, order_id, sku_id, quantity, unit_price, delivered_at, item_status) VALUES
  ('I1007', 'O5', 'S1', NULL, NULL, NULL, NULL), ('I1008', 'O5', 'S1', 3, 1000, '2024-02-28T23:00:00', 'NORMAL');
"""


def studio_with_cases(onto: Ontology, source, now) -> Studio:
    """The commerce studio with the properties above and the rows above. Without its roles: a column's where refuses
    what a role sees masked, which is tried on its own."""
    d = onto.to_dict()
    for t, props in COMPUTED.items():
        for name, (type_, expr) in props.items():
            d["objects"][t]["properties"][name] = {"type": type_, "expr": expr}
    source.script(ROWS)
    st = Studio(Ontology.from_dict(d).check(), now=now)
    st.add_backend("source", source)
    return st


KEEP = {"eq": ["i.item_status", "NORMAL"]}
NONE = {"eq": ["i.item_status", "RETURNED"]}
ITEMS = {"o": "Order", "i": "OrderItem"}
OPTIONAL = {"from": "c", "link": "placed", "to": "o", "optional": True}
OPTIONAL_ITEM = {"from": "o", "link": "hasItem", "to": "i", "optional": True}


def _computed() -> dict:
    out = {}
    for t, alias, key in (("Order", "o", "order_id"), ("Customer", "c", "customer_id"), ("Sku", "s", "sku_id"),
                          ("OrderItem", "i", "item_id")):
        out[f"computed {t}"] = {"match": {alias: t}, "return": [f"{alias}.{key}", *(f"{alias}.{n}" for n in COMPUTED[t])],
                                "order": [key]}
    return out


READ_COMPUTED = {
    "filter on a link aggregate": {"match": {"o": "Order"}, "where": {"gt": ["o.normal_qty", 1]},
                                   "return": ["o.order_id"], "order": ["order_id"]},
    "not of a null": {"match": {"o": "Order"}, "where": {"not": {"gt": ["o.normal_qty", 1]}},
                      "return": ["o.order_id"], "order": ["order_id"]},
    "in on a computed": {"match": {"i": "OrderItem"}, "where": {"in": ["i.wrapped", ["late"]]},
                         "return": ["i.item_id"], "order": ["item_id"]},
    "not in on a computed": {"match": {"i": "OrderItem"}, "where": {"not_in": ["i.wrapped", ["late"]]},
                             "return": ["i.item_id"], "order": ["item_id"]},
    "null on a computed": {"match": {"i": "OrderItem"}, "where": {"is_null": "i.wrapped"},
                           "return": ["i.item_id"], "order": ["item_id"]},
    "computed against a property": {"match": {"i": "OrderItem", "s": "Sku"}, "edges": [["i", "ofSku", "s"]],
                                    "where": {"lt": ["i.line_total", {"ref": "s.price"}]}, "return": ["i.item_id"],
                                    "order": ["item_id"]},
    "group on a computed": {"match": {"i": "OrderItem"}, "return": ["i.wrapped", {"count": "*", "as": "n"}],
                            "order": ["wrapped"]},
    # no null in a group: SPARQL's plain SUM and MAX do not skip one (Jena leaves the group unbound), see _branches
    "aggregate of a computed": {"match": {"i": "OrderItem"}, "where": {"not_null": "i.delivered_at"},
                                "return": ["i.item_status", {"sum": "i.line_total", "as": "t"}, {"max": "i.days", "as": "d"}],
                                "order": ["item_status"]},
    "not over an and with a null": {"match": {"i": "OrderItem"},
                                    "where": {"not": {"and": [{"eq": ["i.quantity", 1]}, {"eq": ["i.item_status", "RETURNED"]}]}},
                                    "return": ["i.item_id"], "order": ["item_id"]},
    "not over an or with a null": {"match": {"i": "OrderItem"},
                                   "where": {"not": {"or": [{"eq": ["i.quantity", 2]}, {"eq": ["i.item_status", "NORMAL"]}]}},
                                   "return": ["i.item_id"], "order": ["item_id"]},
}

COLUMNS = {
    "every aggregate": {"match": ITEMS, "edges": [["o", "hasItem", "i"]],
                        "return": ["o.status", {"sum": "i.quantity", "where": KEEP, "as": "s"},
                                   {"avg": "i.unit_price", "where": KEEP, "as": "a"},
                                   {"min": "i.unit_price", "where": KEEP, "as": "lo"},
                                   {"max": "i.unit_price", "where": KEEP, "as": "hi"},
                                   {"count": "*", "where": KEEP, "as": "n"}, {"count": "i", "where": KEEP, "as": "ni"},
                                   {"count": "i.quantity", "where": KEEP, "as": "nq"},
                                   {"count_distinct": "i.sku_id", "where": KEEP, "as": "nd"},
                                   {"count": "*", "as": "all_rows"}], "order": ["status"]},
    "no row kept": {"match": ITEMS, "edges": [["o", "hasItem", "i"]],
                    "return": ["o.status", {"sum": "i.quantity", "where": NONE, "as": "s"},
                               {"count": "*", "where": NONE, "as": "n"}, {"avg": "i.quantity", "where": NONE, "as": "a"}],
                    "order": ["-s", "status"]},
    "no group key": {"match": {"i": "OrderItem"},
                     "return": [{"sum": "i.quantity", "where": KEEP, "as": "s"}, {"count": "*", "as": "n"},
                                {"sum": "i.quantity", "where": NONE, "as": "none"},
                                {"count": "*", "where": NONE, "as": "zero"}]},
    "no row at all": {"match": {"i": "OrderItem"}, "where": {"eq": ["i.item_id", "nope"]},
                      "return": [{"sum": "i.quantity", "where": KEEP, "as": "s"},
                                 {"count": "*", "where": KEEP, "as": "n"}]},
    "null group keys": {"match": {"c": "Customer", "o": "Order"}, "edges": [["c", "placed", "o"]],
                        "return": ["c.grade", "o.status", {"count": "o", "where": {"gt": ["o.total", 0]}, "as": "n"},
                                   {"sum": "o.total", "where": {"gt": ["o.total", 60000]}, "as": "s"}],
                        "order": ["grade", "status"]},
    "a computed in the where": {"match": {"i": "OrderItem"},
                                "return": ["i.item_status", {"sum": "i.line_total", "where": {"gt": ["i.line_total", 30000]}, "as": "s"},
                                           {"count": "*", "where": {"eq": ["i.wrapped", "late"]}, "as": "n"}],
                                "order": ["item_status"]},
    "a link aggregate in the where": {"match": {"o": "Order"},
                                      "return": ["o.status", {"count": "*", "where": {"gt": ["o.total", 60000]}, "as": "n"},
                                                 {"sum": "o.total", "where": {"gt": ["o.item_count", 1]}, "as": "s"}],
                                      "order": ["status"]},
    "every filter": {"match": {"i": "OrderItem"},
                     "return": ["i.order_id",
                                {"count": "*", "where": {"or": [{"contains": ["i.item_status", "RETURN"]},
                                                                {"is_null": "i.quantity"}]}, "as": "a"},
                                {"count": "*", "where": {"not": {"in": ["i.item_status", ["NORMAL"]]}}, "as": "b"},
                                {"count": "*", "where": {"not_null": "i.delivered_at"}, "as": "c"},
                                {"count": "*", "where": {"and": [{"eq": ["i.quantity", 1]},
                                                                 {"lt": ["i.unit_price", {"ref": "i.unit_price"}]}]}, "as": "d"}],
                     "order": ["order_id"]},
}

PARAMETERS = {"match": {"i": "OrderItem", "o": "Order"}, "edges": [["i", "itemOf", "o"]],
              "where": {"ne": ["o.status", {"param": "skip"}]},
              "return": ["o.status", {"sum": "i.quantity", "where": {"eq": ["i.item_status", {"param": "state"}]}, "as": "s"},
                         {"count": "*", "where": {"gte": ["i.quantity", {"param": "least"}]}, "as": "n"}],
              "order": ["status"]}
PARAMETER_VALUES = {"skip": "CANCELLED", "state": "NORMAL", "least": 2}

OPTIONALS = {
    "count over a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                    "return": ["c.customer_id", {"count": "o", "as": "n"}, {"count": "*", "as": "all_rows"}],
                                    "order": ["customer_id"]},
    "rows with a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                   "return": ["c.customer_id", "o.order_id", "o.status"],
                                   "order": ["customer_id", "order_id"]},
    "a chain": {"match": {"c": "Customer", "o": "Order", "i": "OrderItem"}, "edges": [OPTIONAL, OPTIONAL_ITEM],
                "return": ["c.customer_id", "o.order_id", "i.item_id", "i.quantity"],
                "order": ["customer_id", "order_id", "item_id"]},
    "aggregates over a chain": {"match": {"c": "Customer", "o": "Order", "i": "OrderItem"}, "edges": [OPTIONAL, OPTIONAL_ITEM],
                                "return": ["c.customer_id", {"count": "i.quantity", "as": "q"}, {"count": "*", "as": "m"}],
                                "order": ["customer_id"]},
    "filter on its value": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                            "where": {"eq": ["o.status", "DELIVERED"]}, "return": ["c.customer_id", "o.order_id"],
                            "order": ["order_id"]},
    "filter on its absence": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                              "where": {"is_null": "o.order_id"}, "return": ["c.customer_id"], "order": ["customer_id"]},
    "filter on its presence": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                               "where": {"not_null": "o.status"}, "return": ["c.customer_id", "o.order_id"],
                               "order": ["order_id"]},
    "not equal drops a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                         "where": {"ne": ["o.status", "DELIVERED"]},
                                         "return": ["c.customer_id", "o.order_id"], "order": ["order_id"]},
    "not drops a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                   "where": {"not": {"eq": ["o.status", "DELIVERED"]}},
                                   "return": ["o.order_id"], "order": ["order_id"]},
    "not in drops a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                      "where": {"not_in": ["o.status", ["DELIVERED"]]},
                                      "return": ["o.order_id"], "order": ["order_id"]},
    "with a conditional aggregate": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                     "return": ["c.customer_id", {"count": "o", "where": {"eq": ["o.status", "DELIVERED"]}, "as": "n"},
                                                {"sum": "o.total", "where": {"ne": ["o.status", "CANCELLED"]}, "as": "s"}],
                                     "order": ["customer_id"]},
    "not exists from a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                         "where": {"not_exists": {"match": {"x": "OrderItem"}, "edges": [["o", "hasItem", "x"]]}},
                                         "return": ["c.customer_id", "o.order_id"], "order": ["customer_id"]},
    "exists from a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                     "where": {"exists": {"match": {"x": "OrderItem"}, "edges": [["o", "hasItem", "x"]]}},
                                     "return": ["c.customer_id", "o.order_id"], "order": ["order_id"]},
    "with hops": {"match": {"k": "Category", "a": "Category"},
                  "edges": [{"from": "k", "link": "broader", "to": "a", "optional": True, "hops": [1, 2]}],
                  "return": ["k.category_id", "a.category_id"], "order": ["k.category_id", "a.category_id"]},
    "computed on a missing object": {"match": {"c": "Customer", "o": "Order"}, "edges": [OPTIONAL],
                                     "return": ["c.customer_id", "o.order_id", "o.item_count", "o.total", "o.normal_qty"],
                                     "order": ["customer_id", "order_id"]},
}


def all_cases() -> dict[str, tuple[dict, dict]]:
    """name -> (query, parameters), for Studio.conformance after Query.from_dict."""
    out = {name: (q, {}) for name, q in {**_computed(), **READ_COMPUTED, **COLUMNS, **OPTIONALS}.items()}
    out["parameters by position"] = (PARAMETERS, PARAMETER_VALUES)
    return out
