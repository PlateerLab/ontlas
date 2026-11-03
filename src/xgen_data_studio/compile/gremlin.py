"""IR -> Gremlin (Apache TinkerPop 3.8): one traversal script whose values ride as bindings, never in the text.

The pattern walks from the first alias, labelling each node with as() and returning to a known one with select()
before the next edge; filters are where() traversals over the labels; returned columns are project(); aggregates
group by the returned properties. A property that is not there gives null, as a NULL column does in SQL, and
comparisons on it are not true, also inside not().
"""
from __future__ import annotations

from xgen_data_studio.check import aliases_of, concrete_subtypes, find_prop
from xgen_data_studio.compile.base import Compiled, CompileError, Compiler, Params
from xgen_data_studio.ir import Agg, And, Cmp, Contains, Edge, Exists, In, IsNull, Not, Or, Query, Ref, filter_refs

_P = {"eq": "eq", "ne": "neq", "lt": "lt", "lte": "lte", "gt": "gt", "gte": "gte"}
_FLIP = {"eq": "eq", "ne": "neq", "lt": "gt", "lte": "gte", "gt": "lt", "gte": "lte"}


def gs(text: str) -> str:
    """A Gremlin (Groovy) string literal: names only; values are bindings."""
    return "'" + str(text).replace("\\", "\\\\").replace("'", "\\'") + "'"


class GremlinCompiler(Compiler):
    language = "gremlin"
    dialect = "tinkerpop"

    def compile(self, q: Query | dict) -> Compiled:
        chk = self.checked(q)
        q = chk.query
        if any(e.optional for e in q.edges):
            raise CompileError("Gremlin here has no optional edge; drop 'optional' or use another backend")
        self._types = aliases_of(q)
        for r in [*filter_refs(q.where), *(c.expr if isinstance(c.expr, Ref) else c.expr.ref for c in q.columns)]:
            if r is not None and find_prop(self.onto, self._types[r.alias], r.prop).expr:
                raise CompileError(f"{r} is a computed property; Gremlin computes no expressions here")
        self._params = Params(chk.param_types)
        self._n = 0
        root = next(iter(q.nodes))
        parts = ["g.V()", self._label(root), f".as({gs(root)})"]
        parts += self._walk(q.edges, {root})
        if any(e.hops for e in q.edges):  # many paths to one node count once, as SELECT DISTINCT does in SQL
            parts.append(".dedup(" + ", ".join(gs(a) for a in q.nodes) + ")")
        if q.where is not None:
            parts.append(f".where({self._filter(q.where)})")
        parts += self._columns(q)
        if q.order:  # one order() with a pair of keys per column: nulls last, then the value
            keys = []
            for o in q.order:
                c = gs(o.name)
                keys.append(f".by(__.coalesce(__.select({c}).is(P.neq(null)).constant(0), __.constant(1)))"
                            f".by(__.select({c}), {'desc' if o.desc else 'asc'})")
            parts.append(".order()" + "".join(keys))
        if q.limit is not None:
            parts.append(f".limit({int(q.limit)})")
        names = list(dict.fromkeys(self._params.order))
        return Compiled("gremlin", self.dialect, "".join(parts), "named", names, self._params.types,
                        [c.name for c in q.columns], chk.column_types, self._params.literals)

    def _label(self, alias: str) -> str:
        t = self.onto.obj(self._types[alias])
        if t.table:
            return f".hasLabel({gs(t.name)})"
        subs = concrete_subtypes(self.onto, t.name)
        if not subs:
            raise CompileError(f"{t.name} has no bound subtype to stand for it in the graph")
        return ".hasLabel(" + ", ".join(gs(s) for s in subs) + ")"

    def _step(self, e: Edge, known: str) -> str:
        source_side = e.target if e.reverse else e.source
        way = "out" if known == source_side else "in"
        step = f"__.{way}({gs(e.link)})"
        if not e.hops:
            return f".{way}({gs(e.link)})"
        if e.min_hops == 1:
            return f".repeat({step}).emit().times({e.max_hops})"
        return f".repeat({step}).emit(__.loops().is(P.gte({e.min_hops}))).times({e.max_hops})"

    def _walk(self, edges: list[Edge], bound: set[str]) -> list[str]:
        out = []
        for e in edges:
            if e.source in bound and e.target in bound:
                raise CompileError(f"a cycle through '{e.link}' is not compiled to Gremlin here")
            known, new = (e.source, e.target) if e.source in bound else (e.target, e.source)
            out += [f".select({gs(known)})", self._step(e, known), self._label(new), f".as({gs(new)})"]
            bound.add(new)
        return out

    def _ph(self, value, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        return self._params.add(value, p.type)

    def _has(self, ref: Ref, pred: str) -> str:
        return f"__.select({gs(ref.alias)}).has({gs(ref.prop)}, {pred})"

    def _present(self, f) -> list[str]:
        return [f"__.select({gs(r.alias)}).has({gs(r.prop)})" for r in filter_refs(f, deep=False)]

    def _filter(self, f) -> str:
        if isinstance(f, Cmp):
            if isinstance(f.value, Ref):  # a.p op b.q  <=>  b.q flip(op) a.p, the left value held under a label
                self._n += 1
                hold = gs(f"_l{self._n}")
                return (f"__.select({gs(f.ref.alias)}).values({gs(f.ref.prop)}).as({hold})"
                        f".select({gs(f.value.alias)}).values({gs(f.value.prop)}).where(P.{_FLIP[f.op]}({hold}))")
            return self._has(f.ref, f"P.{_P[f.op]}({self._ph(f.value, f.ref)})")
        if isinstance(f, In):
            p = find_prop(self.onto, self._types[f.ref.alias], f.ref.prop)
            name = self._params.add(list(f.values), p.type)
            return self._has(f.ref, f"P.{'without' if f.negate else 'within'}({name})")
        if isinstance(f, Contains):
            return self._has(f.ref, f"TextP.containing({self._ph(f.value, f.ref)})")
        if isinstance(f, IsNull):
            return f"__.select({gs(f.ref.alias)}).{'has' if f.negate else 'hasNot'}({gs(f.ref.prop)})"
        if isinstance(f, And):
            return "__.and(" + ", ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "__.or(" + ", ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Not):
            inner = self._filter(f.item)
            need = self._present(f.item) if not isinstance(f.item, (IsNull, Exists)) else []
            return "__.and(" + ", ".join([*need, f"__.not({inner})"]) + ")" if need else f"__.not({inner})"
        if isinstance(f, Exists):
            outer = set(self._types) - set(f.nodes)
            first = next((a for e in f.edges for a in (e.source, e.target) if a in outer), None)
            if first is None:
                raise CompileError("exists needs an edge from an outer alias")
            body = ["__.select(" + gs(first) + ")"] + self._walk(f.edges, set(outer))[1:]
            if f.where is not None:
                body.append(f".where({self._filter(f.where)})")
            elif body[-1].startswith(".as("):  # a last as() in a where() child would test equality with that label
                body.pop()
            text = "".join(body)
            return f"__.not({text})" if f.negate else text
        raise CompileError(f"cannot compile filter {f!r}")

    def _value(self, ref: Ref) -> str:
        return f"__.select({gs(ref.alias)}).coalesce(__.values({gs(ref.prop)}), __.constant(null))"

    def _arg(self, a: Agg) -> str | None:
        """What a row carries into the group for one aggregate: a value, or the node itself to count."""
        if a.ref is not None:
            return self._value(a.ref)
        if a.node:
            return f"__.select({gs(a.node)}).id()"
        return None

    @staticmethod
    def _agg(a: Agg, slot: str) -> str:
        if a.func == "count" and a.ref is None and not a.node:
            return "__.count(local)"
        present = f"__.unfold().select({gs(slot)}).is(P.neq(null))"
        if a.func == "count":
            return present + ".count()"
        if a.func == "count_distinct":
            return present + ".dedup().count()"
        fn = {"avg": "mean"}.get(a.func, a.func)
        return f"{present}.fold().choose(__.count(local).is(0), __.constant(null), __.unfold().{fn}())"

    def _columns(self, q: Query) -> list[str]:
        keys = [c for c in q.columns if isinstance(c.expr, Ref)]
        aggs = [c for c in q.columns if isinstance(c.expr, Agg)]
        names = ", ".join(gs(c.name) for c in q.columns)
        if not aggs:
            out = [f".project({names})" + "".join(f".by({self._value(c.expr)})" for c in keys)]
            return out + ([".dedup()"] if q.distinct else [])
        # each row becomes a map of what the groups need, since fold() leaves the path labels behind
        slots = [(c, f"__a{i}", self._arg(c.expr)) for i, c in enumerate(aggs)]
        row = [(c.name, self._value(c.expr)) for c in keys] + [(slot, arg) for _, slot, arg in slots if arg]
        prep = (f".project({', '.join(gs(n) for n, _ in row)})" + "".join(f".by({t})" for _, t in row)) if row else ""
        agg_part = f"__.fold().project({', '.join(gs(c.name) for c in aggs)})" + "".join(
            f".by({self._agg(c.expr, slot)})" for c, slot, _ in slots)
        if not keys:
            return [prep, f".fold().project({', '.join(gs(c.name) for c in aggs)})" +
                    "".join(f".by({self._agg(c.expr, slot)})" for c, slot, _ in slots)]
        key_part = f"__.project({', '.join(gs(c.name) for c in keys)})" + "".join(
            f".by(__.select({gs(c.name)}))" for c in keys)
        pick = "".join(f".by(__.select(keys).select({gs(c.name)}))" if isinstance(c.expr, Ref)
                       else f".by(__.select(values).select({gs(c.name)}))" for c in q.columns)
        return [prep, f".group().by({key_part}).by({agg_part})", f".unfold().project({names}){pick}"] +             ([".dedup()"] if q.distinct else [])
