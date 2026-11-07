"""Decision-table export to GoRules JDM, and evaluation on the ZEN engine when it is installed."""
from __future__ import annotations

import json
from typing import Any

from xgen_space.decide.cells import parse_test, to_zen
from xgen_space.decide.table import DecisionError, answer
from xgen_space.model import DecisionTable


def _in_order(table: DecisionTable) -> list:
    """The rules as ZEN should try them: by priority, and a rule set aside by a pick after the rule it yields to."""
    rules = sorted(table.rules, key=lambda r: r.priority) if table.hit_policy == "priority" else list(table.rules)
    for r in [x for x in rules if x.overruled_by]:
        after = max((i for i, x in enumerate(rules) if x.id in r.overruled_by), default=-1)
        if rules.index(r) < after:
            rules.remove(r)
            rules.insert(after, r)
    return rules


def to_jdm(table: DecisionTable) -> dict:
    if table.hit_policy not in ("first", "collect", "priority"):
        raise DecisionError(f"ZEN decision tables take hit policy first, collect or priority, not "
                            f"'{table.hit_policy}'")
    # ZEN has no priority policy; the first match of the rules in priority order is the same answer
    ordered = _in_order(table)
    inputs = [{"id": f"in_{n}", "name": n, "field": n} for n in table.inputs]
    outputs = [{"id": f"out_{n}", "name": n, "field": n} for n in table.outputs]
    rules = []
    for r in ordered:
        row: dict[str, str] = {"_id": r.id, "_description": r.note}
        then = answer(table, r)
        for n in table.inputs:
            row[f"in_{n}"] = to_zen(parse_test(r.when.get(n, ""), table.named))
        for n in table.outputs:
            row[f"out_{n}"] = json.dumps(then[n], ensure_ascii=False) if n in then else ""
        rules.append(row)
    return {
        "contentType": "application/vnd.gorules.decision",
        "nodes": [
            {"id": "request", "name": "request", "type": "inputNode", "position": {"x": 0, "y": 0}},
            {"id": "table", "name": table.name, "type": "decisionTableNode", "position": {"x": 320, "y": 0},
             "content": {"hitPolicy": "collect" if table.hit_policy == "collect" else "first", "inputs": inputs,
                         "outputs": outputs, "rules": rules}},
            {"id": "response", "name": "response", "type": "outputNode", "position": {"x": 640, "y": 0}},
        ],
        "edges": [{"id": "e1", "sourceId": "request", "targetId": "table", "type": "edge"},
                  {"id": "e2", "sourceId": "table", "targetId": "response", "type": "edge"}],
    }


def evaluate_zen(table: DecisionTable, inputs: dict[str, Any]) -> Any:
    try:
        import zen
    except ImportError as e:
        raise ImportError("ZEN evaluation needs the [zen] extra (zen-engine)") from e
    engine = zen.ZenEngine()
    decision = engine.create_decision(json.dumps(to_jdm(table), ensure_ascii=False))
    from xgen_space.values import normalize

    out = decision.evaluate({k: normalize(v) for k, v in inputs.items()})  # an amount from a database is a Decimal
    result = out.get("result", out)
    if table.hit_policy == "collect":
        return [{k: r.get(k) for k in table.outputs} for r in (result or [])]
    if not result:
        return {k: None for k in table.outputs}
    return {k: result.get(k) for k in table.outputs}
