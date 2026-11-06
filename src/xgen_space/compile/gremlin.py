"""IR -> Gremlin (Apache TinkerPop 3.8): one traversal script whose values ride as bindings, never in the text.

The pattern walks from the first alias, labelling each node with as() and returning to a known one with select()
before the next edge; filters are where() traversals over the labels; returned columns are project(); aggregates
group by the returned properties. A property that is not there gives null, as a NULL column does in SQL, and
comparisons on it are not true, also inside not(). An optional edge that finds nothing labels a null, as LEFT JOIN
does; a step on a vertex stops the traversal on a null, so an alias that may be null is tested before any such step.
A computed property is a traversal too, giving one value: see expr.GremlinRenderer.
"""
from __future__ import annotations

from dataclasses import replace

from xgen_space import expr as ex
from xgen_space.check import aliases_of, concrete_subtypes, find_prop
from xgen_space.compile.base import Compiled, CompileError, Compiler, Params
from xgen_space.ir import OPS, Agg, And, Cmp, Contains, Edge, Exists, In, IsNull, Not, Or, Query, Ref

_P = {"eq": "eq", "ne": "neq", "lt": "lt", "lte": "lte", "gt": "gt", "gte": "gte"}
_FLIP = {"eq": "eq", "ne": "neq", "lt": "gt", "lte": "gte", "gt": "lt", "gte": "lte"}
_OPPOSITE = {"eq": "ne", "ne": "eq", "lt": "gte", "lte": "gt", "gt": "lte", "gte": "lt"}
_NULL = "__.constant(null)"


def gs(text: str) -> str:
    """A Gremlin (Groovy) string literal: names only; values are bindings."""
    return "'" + str(text).replace("\\", "\\\\").replace("'", "\\'") + "'"


class GremlinCompiler(Compiler):
    language = "gremlin"
    dialect = "tinkerpop"

    def compile(self, q: Query | dict) -> Compiled:
        chk = self.checked(q)
        q = chk.query
        self._types = aliases_of(q)
        self._params = Params(chk.param_types)
        self._n = 0
        self._maybe: set[str] = set()  # aliases an optional edge can leave null
        self._held: dict = {}  # one binding per distinct literal of a computed property: servers cap them at 16
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
            guard = ".is(P.neq(null))" if known in self._maybe else ""
            hop = self._step(e, known) + self._label(new)
            if e.optional:
                out += [f".select({gs(known)})", f".coalesce(__{guard}{hop}, {_NULL})", f".as({gs(new)})"]
                self._maybe.add(new)
            else:
                out += [f".select({gs(known)})", guard, hop, f".as({gs(new)})"]
            bound.add(new)
        return out

    def _at(self, alias: str) -> str:
        """Back at an alias, and nowhere if it is null."""
        return f"__.select({gs(alias)})" + (".is(P.neq(null))" if alias in self._maybe else "")

    def _plain(self, ref: Ref) -> bool:
        """A stored property of an alias that is always there, which has() can read."""
        return ref.alias not in self._maybe and not find_prop(self.onto, self._types[ref.alias], ref.prop).expr

    def _ph(self, value, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        return self._params.add(value, p.type)

    def _has(self, ref: Ref, pred: str) -> str:
        if self._plain(ref):
            return f"__.select({gs(ref.alias)}).has({gs(ref.prop)}, {pred})"
        return f"{self._value(ref)}.is(P.neq(null)).is({pred})"  # neq and without alone would let a null pass

    def _filter(self, f) -> str:
        """Passes where the filter is true."""
        if isinstance(f, Cmp):
            if isinstance(f.value, Ref):
                if not (self._plain(f.ref) and self._plain(f.value)):
                    text = self._renderer(f.ref.alias).binary(OPS[f.op], self._value(f.ref), self._value(f.value))
                    return f"{text}.is(P.eq(true))"
                # a.p op b.q  <=>  b.q flip(op) a.p, the left value held under a label
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
            if self._plain(f.ref):
                return f"__.select({gs(f.ref.alias)}).{'has' if f.negate else 'hasNot'}({gs(f.ref.prop)})"
            return f"{self._value(f.ref)}.is(P.{'neq' if f.negate else 'eq'}(null))"
        if isinstance(f, And):
            return "__.and(" + ", ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "__.or(" + ", ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Not):
            return self._false(f.item)
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

    def _false(self, f) -> str:
        """Passes where the filter is false, which null is not: NOT keeps neither, and false beats null in an and."""
        if isinstance(f, Cmp):
            return self._filter(replace(f, op=_OPPOSITE[f.op]))
        if isinstance(f, (In, IsNull, Exists)):
            return self._filter(replace(f, negate=not f.negate))
        if isinstance(f, Contains):
            return f"__.and({self._filter(IsNull(f.ref, negate=True))}, __.not({self._filter(f)}))"
        if isinstance(f, And):
            return "__.or(" + ", ".join(self._false(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "__.and(" + ", ".join(self._false(x) for x in f.items) + ")"
        if isinstance(f, Not):
            return self._filter(f.item)
        raise CompileError(f"cannot compile filter {f!r}")

    def _value(self, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        if p.expr:
            return self._computed(ref.alias, p.expr)
        if ref.alias in self._maybe:
            return f"__.coalesce({self._at(ref.alias)}.values({gs(ref.prop)}), {_NULL})"
        return f"__.select({gs(ref.alias)}).coalesce(__.values({gs(ref.prop)}), {_NULL})"

    def _renderer(self, alias: str) -> ex.GremlinRenderer:
        return ex.GremlinRenderer(lambda n: self._value(Ref(alias, n.name)), lambda a: self._aggregate(alias, a),
                                  self._literal)

    def _computed(self, alias: str, text: str) -> str:
        try:
            return self._renderer(alias).render(ex.prepare(self.onto, self._types[alias], ex.parse_expr(text)))
        except ex.ExprError as e:
            raise CompileError(str(e)) from None

    def _literal(self, node: ex.Lit) -> str:
        key = (node.type, node.value)
        if key not in self._held:
            self._held[key] = self._params.add(node.value, node.type)
        return self._held[key]

    def _aggregate(self, alias: str, a: ex.Agg) -> str:
        """A walk along the aggregate's links from the alias, each row labelled so that its value can be read."""
        steps, prop = ex.resolve_agg(self.onto, self._types[alias], a)
        walk, prev = [self._at(alias)], alias
        for st in steps:
            self._n += 1
            nxt = f"g{self._n}"
            self._types[nxt] = st.type
            walk += [f".{'out' if st.forward else 'in'}({gs(st.link)})", self._label(nxt), f".as({gs(nxt)})"]
            prev = nxt
        if a.where is not None:
            walk.append(f".where({self._renderer(prev).render(a.where)}.is(P.eq(true)))")
        rows = "".join(walk)
        if a.fn in ("latest", "earliest"):
            obj = self.onto.obj(self._types[prev])
            way = "desc" if a.fn == "latest" else "asc"
            pick = (f".has({gs(obj.series['time'])}).order().by({gs(obj.series['time'])}, {way})"
                    f".by(__.values({gs(obj.key)}).asString(), {way}).limit(1)")
            return f"__.coalesce({rows}{pick}{self._value(Ref(prev, prop))[2:]}, {_NULL})"
        if a.fn == "count" and not prop:
            return f"{rows}.count()"
        present = f"{rows}{self._value(Ref(prev, prop))[2:]}.is(P.neq(null))"
        if a.fn == "count":
            return f"{present}.count()"
        fn = {"avg": "mean"}.get(a.fn, a.fn)
        return f"{present}.fold().choose(__.count(local).is(0), {_NULL}, __.unfold().{fn}())"

    def _arg(self, a: Agg) -> str | None:
        """What a row carries into the group for one aggregate: a value, the node to count, or null to be left out."""
        if a.ref is not None:
            value = self._value(a.ref)
        elif a.node:
            node = f"{self._at(a.node)}.id()"
            value = f"__.coalesce({node}, {_NULL})" if a.node in self._maybe else node
        elif a.where is not None:
            value = "__.constant(1)"
        else:
            return None
        return f"__.choose({self._filter(a.where)}, {value}, {_NULL})" if a.where is not None else value

    @staticmethod
    def _agg(a: Agg, slot: str) -> str:
        if a.func == "count" and a.ref is None and not a.node and a.where is None:
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
