"""Functions: logic the ontology owns, under one contract.

Each one says what it takes and gives, which version runs, who owns it and what it depends on, and a role is given it by name,
as it is given a decision. The runtime is only how it is carried out:

    expr      an expression over the target's properties, compiled into the language of whatever store runs it
    decision  a decision table
    query     a registered query
    python    a callable the deployment registered under a name (`functions: {python: {name: package.module:callable}}`)
    http      a service the deployment allows, such as a model or a solver

A module names a callable, never code, so a definition cannot bring code in with it.
"""
from __future__ import annotations

import importlib
import re
from dataclasses import replace
from typing import Any, Callable

from xgen_space.actions import check_parameters, parameter_spec
from xgen_space.expr import check_computed, dependencies
from xgen_space.ir import Cmp, Column, Query, Ref
from xgen_space.model import (
    FUNCTION_RUNTIMES,
    FUNCTION_STATUS,
    TYPES,
    Function,
    Ontology,
    Parameter,
    Property,
    valid_name,
)
from xgen_space.roles import AccessDenied, mask_style, mask_value
from xgen_space.values import accepts, from_source, normalize

RESULT = "result__"  # the property an expression function reads as, on a view of its target
SAMPLE = {"integer": 0, "decimal": 0, "boolean": False, "date": "2026-01-01", "datetime": "2026-01-01T00:00:00"}
VERSION = re.compile(r"^\d+(\.\d+){0,2}([-.+][0-9A-Za-z.-]+)?$")


class FunctionError(ValueError):
    """The function cannot run as asked; the message says why."""


def load_entries(entries: dict[str, str]) -> dict[str, Callable]:
    """The callables a deployment offers, from `package.module:callable`."""
    out: dict[str, Callable] = {}
    for name, where in (entries or {}).items():
        module, _, attr = str(where).partition(":")
        if not attr:
            raise FunctionError(f"function entry {name}: write package.module:callable")
        out[name] = getattr(importlib.import_module(module), attr)
    return out


def _result_of(f: Function) -> tuple[str, str]:
    return next(iter(f.outputs.items()), ("value", "string"))


def _view(onto: Ontology, f: Function, values: dict[str, Any]) -> Ontology:
    """The definition as an expression function reads it: its inputs as named values, its result as a property."""
    t = onto.objects[f.target]
    named = dict(onto.parameters)
    for name, spec in f.inputs.items():
        kind = parameter_spec(spec).get("type", "string")
        named[name] = Parameter(name, values.get(name, SAMPLE.get(kind, "")), kind)
    made = Property(RESULT, _result_of(f)[1], expr=f.expr, internal=True)
    return replace(onto, parameters=named, objects={**onto.objects, t.name: replace(t, properties={**t.properties, RESULT: made})})


def function_issues(o: Ontology, f: Function) -> list[str]:
    from xgen_space.validate import _call, _parameter

    out = []
    if not valid_name(f.name):
        out.append("name is not an identifier")
    if f.runtime not in FUNCTION_RUNTIMES:
        return out + [f"runtime '{f.runtime}' is not one of {FUNCTION_RUNTIMES}"]
    if f.status not in FUNCTION_STATUS:
        out.append(f"status '{f.status}' is not one of {FUNCTION_STATUS}")
    if not VERSION.match(f.version):
        out.append(f"version '{f.version}' is not a version number")
    if f.target and f.target not in o.objects:
        return out + [f"target '{f.target}' is unknown"]
    for name, spec in f.inputs.items():
        out += [f"input '{name}': {e}" for e in _parameter(spec)]
    out += [f"output '{k}' has type '{v}', not one of {TYPES}" for k, v in f.outputs.items() if v not in TYPES]
    if f.runtime == "expr":
        if not f.target or not f.expr:
            out.append("an expression runs on a target: give both")
        elif len(f.outputs) != 1:
            out.append("an expression gives one output: name it and give its type")
        elif not out:
            out += check_computed(_view(o, f, {}), f.target, RESULT).issues
    elif f.runtime == "decision":
        table = o.decisions.get(f.decision)
        if table is None:
            out.append(f"decision '{f.decision}' is unknown")
        elif f.target and f.target != table.target:
            out.append(f"decision '{f.decision}' is about {table.target}, not {f.target}")
    elif f.runtime == "query":
        if f.query not in o.queries:
            out.append(f"query '{f.query}' is unknown")
    elif f.runtime == "python":
        if not f.entry:
            out.append("give the name the deployment registered the callable under")
    elif f.runtime == "http":
        out += _call(f.call)
    return out


def reads(onto: Ontology, f: Function) -> list[str]:
    """What this function stands on, as element ids, so a change to any of them shows it."""
    out: list[str] = []
    if f.runtime == "expr" and f.target in onto.objects and f.expr:
        try:
            out += sorted(f"property:{t}.{p}" for t, p in dependencies(_view(onto, f, {}), f.target, RESULT))
        except ValueError:
            pass
    if f.decision:
        out.append(f"decision:{f.decision}")
    if f.query:
        out.append(f"query:{f.query}")
    return out + list(f.depends)


def describe(onto: Ontology, f: Function) -> dict:
    return {"name": f.name, "label": f.label or f.name, "description": f.description, "runtime": f.runtime, "target": f.target,
            "version": f.version, "owner": f.owner, "status": f.status, "inputs": f.inputs, "outputs": f.outputs,
            "expr": f.expr, "decision": f.decision, "query": f.query, "entry": f.entry, "call": f.call, "depends": f.depends,
            "reads": reads(onto, f), "cite": f.cite}


def _key(onto: Ontology, f: Function, key: Any) -> Any:
    from xgen_space.check import find_prop

    t = onto.obj(f.target)
    return int(key) if find_prop(onto, f.target, t.key).type == "integer" else str(key)


def _visible(studio, f: Function, key: Any, role: str, principal: dict | None) -> None:
    t = studio.onto.obj(f.target)
    q = Query(nodes={"x": t.name}, where=Cmp(Ref("x", t.key), "eq", _key(studio.onto, f, key)),
              columns=[Column(Ref("x", t.key), "k")])
    if not studio.run(q, role=role, principal=principal).rows:
        raise PermissionError(f"{f.target} {key} is outside this role's rows")


def _shown(studio, f: Function, row: dict | None, role: str | None) -> dict:
    """The row as a role sees it: code outside the ontology gets no more than the caller may read."""
    row = dict(row or {})
    if role:
        r = studio.onto.roles[role]
        for p in list(row):
            style = mask_style(studio.onto, r, f.target, p)
            if style:
                row[p] = mask_value(row[p], style)
    return row


def _expr(studio, f: Function, key, values, row, role, principal) -> tuple[dict, list, str]:
    view = _view(studio.onto, f, values)
    t = view.obj(f.target)
    b = studio.backend()
    q = Query(nodes={"x": f.target}, where=Cmp(Ref("x", t.key), "eq", _key(view, f, key)), columns=[Column(Ref("x", RESULT), "v")])
    res = b.execute(b.compiler(view).compile(q), {})
    name, kind = _result_of(f)
    seen = sorted(dependencies(view, f.target, RESULT))
    evidence = [{"property": f"{a}.{p}", "value": normalize(row.get(p)) if a == f.target and row else None} for a, p in seen]
    style = mask_style(view, studio.onto.roles[role], f.target, RESULT) if role else ""
    return {name: from_source(res.rows[0][0], kind) if res.rows else None}, evidence, style


def _decision(studio, f: Function, key, values, row, role, principal) -> tuple[dict, list, str]:
    res = studio.decide(f.decision, key, values)
    outs = res.outputs if isinstance(res.outputs, dict) else {"result": res.outputs}
    evidence = []
    for ev in res.evidence:
        style = mask_style(studio.onto, studio.onto.roles[role], ev.object_type, ev.property) if role and ev.object_type else ""
        evidence.append({"property": f"{ev.object_type}.{ev.property}" if ev.object_type else ev.input,
                         "value": mask_value(ev.value, style) if style else normalize(ev.value)})
    return ({k: outs.get(k) for k in f.outputs} if f.outputs else outs), evidence + [{"rules": res.matched}], ""


def _query(studio, f: Function, key, values, row, role, principal) -> tuple[dict, list, str]:
    res = studio.run(studio.query(f.query), values, role=role, principal=principal)
    return {"rows": [{k: normalize(v) for k, v in r.items()} for r in res.records()]}, [], ""


def _python(studio, f: Function, key, values, row, role, principal) -> tuple[dict, list, str]:
    fn = studio.entries.get(f.entry)
    if fn is None:
        raise FunctionError(f"{f.name}: this deployment has registered no callable '{f.entry}'")
    out = fn(_shown(studio, f, row, role), dict(values))
    if not isinstance(out, dict):
        raise FunctionError(f"{f.name}: the callable returned {type(out).__name__}, not its outputs")
    return out, [], ""


def _http(studio, f: Function, key, values, row, role, principal) -> tuple[dict, list, str]:
    caller = studio.actions.caller
    if caller is None:
        raise FunctionError(f"{f.name}: no allowed host is configured for calls")
    got = caller.ask(f.call, {**values, "key": key, "row": _shown(studio, f, row, role), "function": f.name, "version": f.version})
    for step in [s for s in str(f.call.get("path", "")).split(".") if s]:
        got = got.get(step) if isinstance(got, dict) else None
    if not isinstance(got, dict):
        raise FunctionError(f"{f.name}: the service did not answer with its outputs")
    return got, [], ""


RUN = {"expr": _expr, "decision": _decision, "query": _query, "python": _python, "http": _http}


def _typed(f: Function, outputs: dict) -> dict:
    """The contract's other half: what comes back has the declared names and types."""
    out = dict(outputs)
    for name, kind in f.outputs.items():
        if name not in out:
            raise FunctionError(f"{f.name} gave no output '{name}'")
        v = out[name]
        if v is not None and not accepts("string" if kind == "enum" else kind, v):
            raise FunctionError(f"{f.name}: output '{name}' is {v!r}, not {kind}")
    return out


def run_function(studio, name: str, key: Any = None, params: dict | None = None, *, role: str | None = None,
                 principal: dict | None = None, by: str = "", trial: bool = False, log: bool = True) -> dict[str, Any]:
    onto = studio.onto
    f = onto.functions.get(name)
    if f is None:
        raise KeyError(f"unknown function '{name}'")
    if role and not onto.roles[role].can("run", name):
        raise AccessDenied(f"role {role} may not run function '{name}'")
    if f.status == "retired":
        raise FunctionError(f"{name} {f.version} is retired")
    if f.status == "draft" and not trial:
        raise FunctionError(f"{name} {f.version} is a draft: only a person trying it out runs it")
    values, problems = check_parameters(f.inputs, dict(params or {}))
    if problems:
        raise FunctionError("; ".join(problems))
    for k, spec in f.inputs.items():
        d = parameter_spec(spec).get("default")
        if k not in values or values[k] in (None, ""):
            values[k] = d
        if values[k] is None and f.runtime == "expr":
            raise FunctionError(f"{name}: input '{k}' has no value and no default")
    row = None
    if f.target:
        if key in (None, ""):
            raise FunctionError(f"{name} runs on one {f.target}: give its key")
        row = studio.fetch(f.target, key)
        if row is None:
            raise FunctionError(f"{f.target} {key} not found")
        if role:
            _visible(studio, f, key, role, principal)
    outputs, evidence, style = RUN[f.runtime](studio, f, key, values, row, role, principal)
    outputs = _typed(f, outputs)
    if style:
        outputs = {k: mask_value(v, style) for k, v in outputs.items()}
    outputs = {k: normalize(v) if not isinstance(v, (list, dict)) else v for k, v in outputs.items()}
    out = {"function": name, "label": f.label or name, "version": f.version, "owner": f.owner, "runtime": f.runtime,
           "target": f.target, "key": "" if key is None else str(key), "inputs": values, "outputs": outputs, "evidence": evidence}
    if log:  # a page that only shows a value it computes keeps no record of having computed it
        studio.function_log.append({"at": studio.now().isoformat(timespec="seconds"), "by": by or role or "", **{
            k: out[k] for k in ("function", "version", "key", "inputs", "outputs")}})
    return out


__all__ = ["FunctionError", "describe", "function_issues", "load_entries", "reads", "run_function"]
