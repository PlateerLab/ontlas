"""Backend port: what a backend can do, how it compiles, and how it runs a compiled query."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from xgen_space.compile.base import Compiled, Compiler, compiler_for
from xgen_space.model import Ontology


@dataclass
class Capabilities:
    language: str
    dialect: str = ""
    optional: bool = True
    exists: bool = True
    hops: bool = True
    contains: bool = True
    aggregates: bool = True
    load: bool = False
    write: bool = False
    reasoning: list[str] = field(default_factory=list)
    computed: str = "all"  # computed properties it compiles: all, simple (no links or dates), none

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Result:
    columns: list[str]
    rows: list[tuple]
    backend: str = ""
    compiled: Compiled | None = None
    masked: dict[str, str] = field(default_factory=dict)
    truncated: bool = False  # the service stopped at its row limit: there may be more than these

    def records(self) -> list[dict[str, Any]]:
        return [dict(zip(self.columns, r)) for r in self.rows]


class NoSource(KeyError):
    """No backend to read rows from: the studio holds its definition only. What needs rows raises this, so a page, a
    tool or a review answers "no source" in its own shape instead of failing."""

    def __init__(self, message: str = "no source is connected: this studio holds its definition only"):
        super().__init__(message)

    def __str__(self) -> str:  # a KeyError shows its message quoted
        return str(self.args[0])


class Backend:
    name = ""
    kind = ""  # what the configuration calls it (sqlite, rdflib, neo4j, ...), for a page to name
    capabilities = Capabilities("sql")

    def compiler(self, onto: Ontology) -> Compiler:
        return compiler_for(onto, self.capabilities.language, self.capabilities.dialect)

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        raise NotImplementedError

    def unsupported(self, query, onto: Ontology | None = None) -> list[str]:
        """Features the query uses that this backend does not declare."""
        from xgen_space.ir import Agg, Contains, Exists, walk_filters

        caps, out = self.capabilities, []
        if not caps.optional and any(e.optional for e in query.edges):
            out.append("optional")
        if not caps.hops and any(e.hops for e in query.edges):
            out.append("hops")
        filters = [query.where, *(c.expr.where for c in query.columns if isinstance(c.expr, Agg))]
        kinds = {type(f) for w in filters for f in walk_filters(w)}
        if not caps.exists and Exists in kinds:
            out.append("exists")
        if not caps.contains and Contains in kinds:
            out.append("contains")
        if not caps.aggregates and query.aggregated:
            out.append("aggregates")
        if onto is not None and caps.computed != "all" and _computed_kinds(onto, query) - {
                "simple" if caps.computed == "simple" else ""} - {""}:
            out.append("computed properties")
        return out


def _computed_kinds(onto: Ontology, query) -> set[str]:
    """simple / linked (aggregates or dates) for each computed property the query reads."""
    from xgen_space import expr as ex
    from xgen_space.check import _find_prop, aliases_of
    from xgen_space.ir import Agg, Ref, filter_refs

    types = aliases_of(query)
    refs = list(filter_refs(query.where))
    for c in query.columns:
        e = c.expr
        r = e if isinstance(e, Ref) else (e.ref if isinstance(e, Agg) else None)
        if r is not None:
            refs.append(r)
        if isinstance(e, Agg):
            refs += filter_refs(e.where)
    out = set()
    for r in refs:
        p = _find_prop(onto, types.get(r.alias), r.prop) if r.alias in types else None
        if p is None or not p.expr:
            continue
        nodes = list(ex.walk(ex.parse_expr(p.expr)))
        linked = any(isinstance(n, ex.Agg) or (isinstance(n, ex.Call) and n.fn in ex.DATE_FUNCTIONS) for n in nodes)
        out.add("linked" if linked else "simple")
    return out
