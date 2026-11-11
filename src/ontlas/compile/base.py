"""What every compiler returns, and how its parameters get bound."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ontlas.check import Checked, check, interface_view
from ontlas.ir import Agg, Exists, Param, Query, filter_refs, walk_filters
from ontlas.model import Ontology
from ontlas.values import coerce


class CompileError(ValueError):
    """The query uses something this language or dialect cannot express."""


@dataclass
class Compiled:
    language: str
    dialect: str
    text: str
    style: str
    params: list[str]
    param_types: dict[str, str]
    columns: list[str]
    column_types: dict[str, str]
    literals: dict[str, Any] = field(default_factory=dict)
    render: Callable[[Any, str], str] | None = None

    def bind(self, values: dict[str, Any] | None = None) -> tuple[str, Any]:
        """Return (text, args) for the driver; inline style returns (text-with-literals, None)."""
        given = {**self.literals, **(values or {})}
        missing = [p for p in self.params if p not in given]
        if missing:
            raise CompileError(f"missing parameters {missing}")
        typed = {p: _coerce(given[p], self.param_types.get(p, "string")) for p in self.params}
        if self.style == "positional":
            return self.text, tuple(typed[p] for p in self.params)
        if self.style == "named":
            return self.text, typed
        text = self.text
        for p in self.params:
            text = text.replace(marker(p), self.render(typed[p], self.param_types.get(p, "string")))
        return text, None

    def preview(self, values: dict[str, Any] | None = None) -> str:
        """The query text with parameter values shown inline, for reading only."""
        from ontlas.rdf import literal

        text, args = self.bind(values)
        if args is None:
            return text
        if self.style == "named":
            for k in sorted(args, key=len, reverse=True):
                text = text.replace(f"${k}", _show(args[k], self.param_types.get(k, "string"), literal))
            return text
        out, i = [], 0
        for ch in text:
            if ch == "?" and i < len(args):
                out.append(_show(args[i], self.param_types.get(self.params[i], "string"), literal))
                i += 1
            else:
                out.append(ch)
        return "".join(out)


def _coerce(v: Any, t: str) -> Any:
    if isinstance(v, (list, tuple)):
        return [coerce(x, t) for x in v]
    return coerce(v, t)


def _show(v: Any, t: str, literal) -> str:
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_show(x, t, literal) for x in v) + "]"
    if v is None:
        return "NULL"
    if t in ("integer", "decimal", "boolean"):
        return literal(v, t) if t != "decimal" else str(v)
    return "'" + str(v).replace("'", "''") + "'"


def marker(name: str) -> str:
    return f"$${name}$$"


class Params:
    """Collect parameters in use order; literals become generated parameters."""

    def __init__(self, declared_types: dict[str, str]):
        self.types = dict(declared_types)
        self.order: list[str] = []
        self.literals: dict[str, Any] = {}
        self._n = 0

    def add(self, value: Any, type_: str) -> str:
        if isinstance(value, Param):
            name = value.name
            self.types.setdefault(name, type_)
        else:
            self._n += 1
            name = f"_v{self._n}"
            self.literals[name] = value
            self.types[name] = type_
        self.order.append(name)
        return name


class Compiler:
    language = ""
    dialect = ""
    by_name = False  # write computed properties by their names, as a person writes a query, not as expressions

    def __init__(self, onto: Ontology):
        self.onto = onto

    def checked(self, q: Query | dict) -> Checked:
        if isinstance(q, dict):
            q = Query.from_dict(q)
        plain, self.onto = self.onto, interface_view(self.onto, q)
        chk = check(q, self.onto)
        _check_column_filters(chk, self.onto, plain)
        return chk.raise_for_issues()

    def compile(self, q: Query | dict) -> Compiled:
        raise NotImplementedError


def _check_column_filters(chk: Checked, onto: Ontology, plain: Ontology) -> None:
    """Check each aggregate's own where. Roles scope and mask the query's where and not this one, so it may not leave
    the row (exists) or read a property a role sees masked: counting by it would tell the masked value."""
    from ontlas.check import _Checker
    from ontlas.roles import mask_style

    checker = _Checker(onto)
    checker.issues, checker.params = chk.issues, chk.param_types
    scope = dict(chk.query.nodes)
    for c in chk.query.columns:
        f = c.expr.where if isinstance(c.expr, Agg) else None
        if f is None:
            continue
        checker.filt(f, scope)
        if any(isinstance(x, Exists) for x in walk_filters(f)):
            checker.issue(f"column '{c.name}': exists belongs in the query's where, an aggregate's where reads its row")
        for r in filter_refs(f, deep=False):
            who = sorted(role.name for role in plain.roles.values() if mask_style(plain, role, scope.get(r.alias), r.prop))
            if who:
                checker.issue(f"column '{c.name}': {r} is masked for {', '.join(who)}, so it cannot decide what a "
                              "column counts; filter on it in the query's where, which checks the role")


def compiler_for(onto: Ontology, language: str, dialect: str = "") -> Compiler:
    """Pick a compiler by language and dialect: sql[:dialect], cypher, gql, sparql, sqlpgq."""
    if ":" in language and not dialect:
        language, dialect = language.split(":", 1)
    language = language.lower()
    if language == "sql":
        from ontlas.compile.sql import SqlCompiler

        return SqlCompiler(onto, dialect or "postgres")
    if language == "cypher":
        from ontlas.compile.cypher import CypherCompiler

        return CypherCompiler(onto)
    if language == "gql":
        from ontlas.compile.cypher import GqlCompiler

        return GqlCompiler(onto)
    if language == "sparql":
        from ontlas.compile.sparql import SparqlCompiler

        return SparqlCompiler(onto)
    if language == "gremlin":
        from ontlas.compile.gremlin import GremlinCompiler

        return GremlinCompiler(onto)
    if language in ("sqlpgq", "pgq"):
        from ontlas.compile.pgq import PgqCompiler

        return PgqCompiler(onto, dialect or "oracle")
    raise CompileError(f"unknown language '{language}'; use sql, cypher, gql, sparql, sqlpgq or gremlin")
