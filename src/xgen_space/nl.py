"""LLM assist: a question becomes IR (or a registered query), checked against the ontology and repaired."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from xgen_space.check import all_props, check
from xgen_space.ir import IRError, Query, Ref
from xgen_space.model import Ontology

SYSTEM = ("You translate a question about business data into one JSON object in the ontology query IR. "
          "Use only the object types, properties and links listed. Answer with the JSON object only.")

IR_GUIDE = """IR format:
{"match": {"<alias>": "<ObjectType>", ...},
 "edges": [["<alias>", "<link or inverse>", "<alias>"], {"from": "a", "link": "l", "to": "b", "optional": true}],
 "where": {"and": [{"eq": ["a.prop", value]}, {"gte": ["b.prop", {"param": "name"}]},
                   {"in": ["a.prop", [v1, v2]]}, {"contains": ["a.prop", "text"]}, {"is_null": "a.prop"},
                   {"not_exists": {"match": {"c": "Type"}, "edges": [["a", "link", "c"]]}}]},
 "return": ["a.prop", {"col": "b.prop", "as": "name"}, {"count": "b", "as": "n"}, {"sum": "b.prop", "as": "total"}],
 "order": ["-total", "name"], "limit": 10}
Comparisons: eq ne lt lte gt gte. Aggregates: count count_distinct sum avg min max.
Every edge must start from an alias already matched. Dates are ISO text ("2026-10-01T00:00:00").
If a registered query answers the question, answer {"query": "<name>", "params": {...}} instead."""


TERMS_MAX = 200  # glossary lines a schema card carries


def schema_card(onto: Ontology, role: str | None = None, terms: list[dict] | None = None) -> str:
    r = onto.roles.get(role) if role else None
    lines = ["Object types:"]
    for o in onto.objects.values():
        if r and not r.can_read(o.name):
            continue
        props = []
        for p in o.properties.values():
            s = f"{p.name} {p.type}"
            if p.values:
                s += "[" + "|".join(p.values) + "]"
            if p.label:
                s += f" ({p.label})"
            if p.name == o.key:
                s += " key"
            if p.expr:
                s += f" = {p.expr}"
            if p.description:
                s += f" - {p.description}"
            props.append(s)
        lines.append(f"- {o.name}" + (f" ({o.label})" if o.label else "") + ": " + ", ".join(props))
    lines.append("Links:")
    for lk in onto.links.values():
        if r and not (r.can_read(lk.source) and r.can_read(lk.target)):
            continue
        s = f"- {lk.name}: {lk.source} -> {lk.target} ({lk.cardinality.replace('_', ' ')})"
        if lk.inverse:
            s += f" (inverse: {lk.inverse})"
        if lk.label:
            s += f" [{lk.label}]"
        lines.append(s)
    words = [f"- {t['term']}: {', '.join(t['synonyms'])}" for t in (terms or []) if t.get("synonyms")][:TERMS_MAX]
    if words:
        lines += ["Words that mean the same here:", *words]
    if onto.queries:
        lines.append("Registered queries:")
        for q in onto.queries.values():
            if r and not r.can("run", q.name):
                continue
            compared = _param_targets(onto, q.query)
            params = ", ".join(f"{k}: {v}" + (f" {compared[k]}" if k in compared else "") for k, v in q.params.items())
            lines.append(f"- {q.name}({params})" + (f": {q.label}" if q.label else ""))
    return "\n".join(lines)


def _param_targets(onto: Ontology, query: dict) -> dict[str, str]:
    """For each parameter of a registered query, the property it is compared with (e.g. 'eq Category.category_id')."""
    from xgen_space.check import _find_prop
    from xgen_space.ir import Cmp, Param, parse_filter, walk_filters

    out: dict[str, str] = {}
    try:
        f = parse_filter(query.get("where"))
    except IRError:
        return out
    nodes = dict(query.get("match") or {})
    for x in walk_filters(f):
        if isinstance(x, Cmp) and isinstance(x.value, Param) and x.ref.alias in nodes:
            t = nodes[x.ref.alias]
            p = _find_prop(onto, t, x.ref.prop)
            out[x.value.name] = f"{x.op} {t}.{x.ref.prop}" + (f" ({p.label})" if p is not None and p.label else "")
    return out


def extract_json(text: str) -> Any:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    if start < 0:
        return None
    depth, quote, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if quote:
            esc = ch == "\\" and not esc
            if ch == '"' and not esc:
                quote = False
            continue
        if ch == '"':
            quote = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


@dataclass
class Attempt:
    prompt: str
    raw: str
    issues: list[str]


@dataclass
class Generated:
    query: Query | None = None
    registered: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.query is not None or bool(self.registered)


class IRGenerator:
    def __init__(self, onto: Ontology, llm: Callable[[str, str], str], *, role: str | None = None,
                 max_repairs: int = 2, runner: Callable[[Generated], tuple[int, dict]] | None = None,
                 terms: list[dict] | None = None):
        self.onto, self.llm, self.role, self.max_repairs, self.terms = onto, llm, role, max_repairs, terms
        self.runner = runner  # runs a checked answer: (rows, {"Type.prop": sample values}) for an empty result

    def _issues(self, data: Any) -> tuple[list[str], Query | None, str, dict]:
        if not isinstance(data, dict):
            return ["the answer was not one JSON object"], None, "", {}
        if isinstance(data.get("query"), str):
            name, params = data["query"], dict(data.get("params") or {})
            rq = self.onto.queries.get(name)
            if rq is None:
                return [f"unknown registered query '{name}'"], None, "", {}
            missing = [p for p in rq.params if p not in params]
            return ([f"missing parameters {missing} for {name}"] if missing else []), None, name, params
        try:
            q = Query.from_dict(data)
        except IRError as e:
            return [str(e)], None, "", {}
        res = check(q, self.onto)
        for c in q.columns:  # a column named after another property of its object answers with the wrong values
            if isinstance(c.expr, Ref) and c.expr.alias in q.nodes and c.name != c.expr.prop \
                    and c.name in all_props(self.onto, q.nodes[c.expr.alias]):
                res.issues.append(f"{c.expr} is returned as '{c.name}', which is another property of "
                                  f"{q.nodes[c.expr.alias]}; return {c.expr.alias}.{c.name} for it")
        if self.role:
            r = self.onto.roles[self.role]
            res.issues += [f"this role cannot read {t}" for t in q.nodes.values() if not r.can_read(t)]
        return res.issues, q, "", dict(data.get("params") or {})

    def generate(self, question: str) -> Generated:
        base = f"{schema_card(self.onto, self.role, self.terms)}\n\n{IR_GUIDE}\n\nQuestion: {question}"
        prompt, out = base, Generated()
        for _ in range(self.max_repairs + 1):
            try:
                raw = self.llm(SYSTEM, prompt)
            except Exception as e:  # a model that does not answer in time is a failed attempt, not a crash
                out.attempts.append(Attempt(prompt, "", [f"the model did not answer: {type(e).__name__}"]))
                continue
            issues, q, name, params = self._issues(extract_json(raw))
            out.attempts.append(Attempt(prompt, raw, issues))
            if not issues:
                out.query, out.registered, out.params = q, name, params
                if self.runner is None or len(out.attempts) > self.max_repairs:
                    return out
                rows, samples = self.runner(out)
                if rows:
                    return out
                # it runs and finds nothing: once more, with values the compared properties hold
                seen = "; ".join(f"{k} holds values like {v}" for k, v in samples.items()) or "no compared values"
                issues = [f"it ran and returned no rows ({seen}); if a value was given in another form, use the "
                          "form the data holds, and keep a filter only if the question asks for it"]
                out.attempts[-1].issues = issues
            prompt = (base + "\n\nYour last answer:\n" + raw + "\n\nIt has these problems:\n"
                      + "\n".join(f"- {i}" for i in issues) + "\nReturn a corrected JSON object.")
        return out


def probe(studio, *, role: str | None = None, principal: dict | None = None,
          backend: str | None = None) -> Callable[[Generated], tuple[int, dict]]:
    """Run a generated answer; for an empty result, sample the values of the text properties it compared (only
    what the role may read in clear)."""
    from xgen_space.ir import Cmp, Contains, In, Param, parse_filter, walk_filters
    from xgen_space.roles import mask_style

    def run(gen: Generated) -> tuple[int, dict]:
        q = studio.query(gen.registered) if gen.registered else gen.query
        try:
            n = len(studio.run(q, gen.params, backend=backend, role=role, principal=principal).rows)
        except Exception:
            return 1, {}  # a refusal or an error is not 'no rows'; the answer stands as it is
        if n:
            return n, {}
        samples: dict[str, list] = {}
        r = studio.onto.roles.get(role) if role else None
        for f in walk_filters(q.where if not gen.registered else parse_filter(
                studio.onto.queries[gen.registered].query.get("where"))):
            if not isinstance(f, (Cmp, In, Contains)) or (isinstance(f, Cmp) and not isinstance(
                    f.value, (str, Param))):
                continue
            t = q.nodes.get(f.ref.alias)
            from xgen_space.check import _find_prop

            p = _find_prop(studio.onto, t, f.ref.prop) if t else None
            if p is None or p.type not in ("string", "enum") or (r and mask_style(studio.onto, r, t, p.name)):
                continue
            look = {"match": {"x": t}, "return": [f"x.{p.name}"], "distinct": True, "limit": 5}
            try:
                vals = [row[0] for row in studio.run(look, backend=backend, role=role, principal=principal).rows]
            except Exception:
                continue
            samples[f"{t}.{p.name}"] = [v for v in vals if v is not None]
        return 0, samples

    return run


def answer(studio, question: str, llm: Callable[[str, str], str], *, backend: str | None = None,
           role: str | None = None, principal: dict | None = None) -> dict:
    gen = IRGenerator(studio.onto, llm, role=role,
                      runner=probe(studio, role=role, principal=principal, backend=backend)).generate(question)
    if not gen.ok:
        return {"ok": False, "issues": gen.attempts[-1].issues if gen.attempts else [], "attempts": len(gen.attempts)}
    target = gen.registered or gen.query
    res = studio.run(target, gen.params, backend=backend, role=role, principal=principal)
    return {"ok": True, "attempts": len(gen.attempts), "query": gen.registered or gen.query.to_dict(),
            "columns": res.columns, "rows": [list(r) for r in res.rows], "text": res.compiled.text}


class AnswerCutOff(RuntimeError):
    """The model spent its token budget reasoning and stopped before it wrote an answer."""


def openai_chat(url: str, model: str, *, key: str = "", extra: dict | None = None,
                timeout: float = 90) -> Callable[[str, str], str]:
    """An llm(system, user) callable over any OpenAI-compatible chat completions endpoint (vLLM, Ollama, ...).
    `roomier(tokens, seconds)` on it gives the same model a larger budget, for work no page request is waiting on."""
    import urllib.request

    endpoint = url.rstrip("/") + ("" if url.rstrip("/").endswith("/chat/completions") else "/chat/completions")

    def call(system: str, user: str) -> str:
        body = {"model": model, "temperature": 0,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                **(extra or {})}
        headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})}
        req = urllib.request.Request(endpoint, data=json.dumps(body).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        choice = data["choices"][0]
        text = choice["message"].get("content") or ""
        if not text and choice.get("finish_reason") == "length":
            raise AnswerCutOff("the token budget ran out before the answer")
        return text

    def roomier(tokens: int, seconds: float) -> Callable[[str, str], str]:
        wider = {**(extra or {}), "max_tokens": max(tokens, int((extra or {}).get("max_tokens") or 0))}
        return openai_chat(url, model, key=key, extra=wider, timeout=max(seconds, timeout))

    call.roomier = roomier
    call.kind = "openai"  # what a page names the connection by
    return call


def holds(gold: list[tuple], got: list[tuple]) -> bool:
    """Do the rows a question got hold the gold rows: as many rows, and every gold column one of its columns,
    row for row (extra columns are allowed, the order is not compared)."""
    from collections import Counter

    if len(gold) != len(got):
        return False
    if not gold:
        return True
    gcols, ocols = list(zip(*gold)), list(zip(*got))
    options = [[j for j, oc in enumerate(ocols) if Counter(oc) == Counter(gc)] for gc in gcols]

    def assign(i: int, used: tuple) -> bool:
        if i == len(gcols):
            return Counter(gold) == Counter(tuple(r[j] for j in used) for r in got)
        return any(assign(i + 1, used + (j,)) for j in options[i] if j not in used)

    return assign(0, ())


def evaluate(studio, questions: list[dict], llm: Callable[[str, str], str], *, role: str | None = None,
             max_repairs: int = 2) -> dict:
    """Ask every question, run what comes back, and compare with the gold query's rows (execution match)."""
    from xgen_space.values import normalize

    def rows_of(res) -> list[tuple]:
        types = res.compiled.column_types if res.compiled else {}
        return [tuple(normalize(v, types.get(c, "")) for v, c in zip(r, res.columns)) for r in res.rows]

    results = []
    for q in questions:
        gold = rows_of(studio.run(Query.from_dict(q["gold"])))
        gen = IRGenerator(studio.onto, llm, role=role, max_repairs=max_repairs,
                          runner=probe(studio, role=role)).generate(q["text"])
        entry = {"id": q["id"], "text": q["text"], "attempts": len(gen.attempts), "passed": False, "error": "",
                 "issues": [a.issues for a in gen.attempts]}
        if not gen.ok:
            entry["error"] = "; ".join(gen.attempts[-1].issues if gen.attempts else ["no answer"])[:300]
        else:
            try:
                got = rows_of(studio.run(gen.registered or gen.query, gen.params))
                entry["passed"] = holds(gold, got)
                entry["query"] = gen.registered or gen.query.to_dict()
                if not entry["passed"]:
                    entry["error"] = f"{len(got)} rows, expected {len(gold)}: {got[:3]}"
            except Exception as e:  # a query that checks but does not run counts as a miss, with why
                entry["error"] = f"{type(e).__name__}: {e}"[:300]
        results.append(entry)
    passed = sum(r["passed"] for r in results)
    return {"questions": len(results), "passed": passed, "accuracy": passed / len(results) if results else 0.0,
            "first_try": sum(r["passed"] and r["attempts"] == 1 for r in results), "results": results}
