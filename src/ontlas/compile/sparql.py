"""IR -> SPARQL 1.1 over the projected graph (same IRIs as the projection and R2RML export)."""
from __future__ import annotations

import re
from dataclasses import replace

from ontlas import expr as ex
from ontlas.check import aliases_of, find_prop
from ontlas.compile.base import Compiled, CompileError, Compiler, Params, marker
from ontlas.ir import Agg, And, Cmp, Contains, Edge, Exists, In, IsNull, Not, Or, Query, Ref, filter_refs
from ontlas.rdf import RDF_TYPE, Iris, iri, literal

_OP = {"eq": "=", "ne": "!=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}
NO_VALUE = "urn:ontlas:no-value"  # as an IRI it sorts before every literal, and no property's value is an IRI


def var(ref: Ref) -> str:
    return f"?{ref.alias}__{ref.prop}"


def _optional(block: list) -> str:
    return "OPTIONAL { " + " ".join(_optional(x) if isinstance(x, list) else x for x in block) + " }"


def _loose(q: Query) -> set[str]:
    """The aliases an OPTIONAL may leave unbound."""
    out, bound = set(), {next(iter(q.nodes))}
    for e in q.edges:
        if e.optional:
            out |= {e.source, e.target} - bound
        bound |= {e.source, e.target}
    return out


class SparqlCompiler(Compiler):
    language = "sparql"
    dialect = "1.1"

    def compile(self, q: Query | dict) -> Compiled:
        chk = self.checked(q)
        q = chk.query
        self._types = aliases_of(q)
        self._iris = Iris(self.onto)
        self._params = Params(chk.param_types)
        self._n = 0
        self._bound: set[str] = set()
        self._maybe = _loose(q)
        where = self._filter(q.where) if q.where is not None else None
        body = self._group(q, where)
        group = [var(c.expr) for c in q.columns if isinstance(c.expr, Ref)]
        picked: dict[str, str] = {}
        if any(isinstance(c.expr, Agg) and c.expr.where is not None for c in q.columns):
            body, picked = self._branches(q, body, group)
        # `?x AS ?x` is refused by the standard: a column named like an alias keeps its name, and the alias steps aside
        clash = {c.name for c in q.columns} & set(q.nodes)

        def aside(text: str) -> str:
            for a in clash:
                text = re.sub(rf"\?{re.escape(a)}\b", f"?node_{a}", text)
            return text

        body = [aside(x) for x in body]
        cols = []
        for c in q.columns:
            if isinstance(c.expr, Ref):
                cols.append(f"({var(c.expr)} AS ?{c.name})")
            else:
                cols.append(f"({aside(picked.get(c.name) or self._agg(c.expr))} AS ?{c.name})")
        lines = ["SELECT " + ("DISTINCT " if q.distinct else "") + " ".join(cols), "WHERE {", *body, "}"]
        if q.aggregated and group:
            lines.append("GROUP BY " + " ".join(group))
        if q.order:
            by = {c.name: c.expr for c in q.columns}
            keys = []
            for o in q.order:
                e = by[o.name]
                if q.aggregated:  # after GROUP BY order by the selected names; rdflib loses grouped variables
                    expr = f"?{o.name}"
                    if isinstance(e, Ref) or e.where is not None:
                        keys.append(f"(IF(BOUND({expr}), 0, 1))")
                elif isinstance(e, Ref):
                    keys.append(f"(IF(BOUND({var(e)}), 0, 1))")
                    expr = var(e)
                else:
                    expr = self._agg(e)
                keys.append(f"DESC({expr})" if o.desc else f"ASC({expr})")
            lines.append("ORDER BY " + " ".join(keys))
        if q.limit is not None:
            lines.append(f"LIMIT {int(q.limit)}")
        names = list(dict.fromkeys(self._params.order))
        return Compiled("sparql", self.dialect, "\n".join(lines), "inline", names, self._params.types,
                        [c.name for c in q.columns], chk.column_types, self._params.literals, render=literal)

    def _branches(self, q: Query, body: list[str], group: list[str]) -> tuple[list[str], dict[str, str]]:
        """Columns that aggregate only some of the rows. A row can't be blanked inside a shared group: an unbound value
        is an error to SUM, MIN and the like, and Jena then leaves the whole group unbound. So each such column gets its
        own SELECT over the same pattern, as a branch of a UNION; the query's GROUP BY puts the branches back together,
        also for a null key, which a join on the keys would match to everything."""
        keys, rows = " ".join(group), " ".join(x.strip() for x in body)
        plain, branches, picked = ["(COUNT(*) AS ?_rows)"], [], {}
        for c in q.columns:
            a = c.expr
            if not isinstance(a, Agg):
                continue
            self._n += 1
            out = f"?_c{self._n}"
            if a.where is None:
                plain.append(f"({self._agg(a)} AS {out})")
            else:
                bound = f" FILTER(BOUND({var(a.ref)}))" if a.ref is not None else ""
                # a group of no rows is no answer: null, and not the 0 that SUM of nothing gives without a GROUP BY
                by = "" if group else " BIND(0 AS ?_all)"
                # rdflib answers a GROUP BY over no rows with one empty row, hence the test on the way out
                branches.append(f"{{ {{ SELECT {keys} ({self._agg(replace(a, where=None))} AS {out}) WHERE {{ {rows} "
                                f"FILTER({self._filter(a.where)}){bound}{by} }} GROUP BY {keys or '?_all'} }} "
                                f"FILTER(BOUND({out})) }}")
            # one row of the group holds the value; MAX can't skip the unbound others, so they stand aside as an IRI
            most = f"MAX(COALESCE({out}, <{NO_VALUE}>))"
            whole = a.func in ("count", "count_distinct")  # 1/0 is an error, which leaves the column unbound
            picked[c.name] = f"MAX(COALESCE({out}, 0))" if whole else f'IF(STR({most}) = "{NO_VALUE}", 1/0, {most})'
        first = f"{{ SELECT {keys} {' '.join(plain)} WHERE {{ {rows} }}{f' GROUP BY {keys}' if group else ''} }}"
        return ["  " + " UNION ".join([f"{{ {first} FILTER(BOUND(?_rows)) }}", *branches])], picked

    def _type(self, alias: str) -> str:
        return f"?{alias} {iri(RDF_TYPE)} {iri(self._iris.cls(self._types[alias]))} ."

    def _edge(self, e: Edge) -> str:
        p = iri(self._iris.link(e.link))
        s, t = (e.target, e.source) if e.reverse else (e.source, e.target)
        if not e.hops:
            return f"?{s} {p} ?{t} ."
        path = "|".join("/".join([p] * k) for k in range(e.min_hops, e.max_hops + 1))
        return f"{{ SELECT DISTINCT ?{s} ?{t} WHERE {{ ?{s} ({path}) ?{t} . }} }}"

    def _props(self, alias: str, props: set[str]) -> list[str]:
        """Patterns that bind each property's variable: a stored one by its triple, a computed one by BIND."""
        stored, binds = set(), []
        for p in sorted(props):
            prop = find_prop(self.onto, self._types[alias], p)
            if not prop.expr or self.by_name:
                stored.add(p)
                continue
            v = var(Ref(alias, p))
            if v in self._bound:
                continue
            text, needed, blocks = self._computed(alias, prop.expr)
            stored |= needed
            binds += [*blocks, f"BIND({text} AS {v})"]
            self._bound.add(v)
        out = [f"OPTIONAL {{ ?{alias} {iri(self._iris.prop(p))} {var(Ref(alias, p))} . }}" for p in sorted(stored)]
        return out + binds

    def _computed(self, alias: str, text: str) -> tuple[str, set[str], list[str]]:
        try:
            return self._expr(alias, ex.prepare(self.onto, self._types[alias], ex.parse_expr(text)))
        except ex.ExprError as e:
            raise CompileError(str(e)) from None

    def _expr(self, alias: str, node) -> tuple[str, set[str], list[str]]:
        """The expression over the alias's variables, the stored properties it reads, and its aggregate blocks."""
        needed: set[str] = set()
        blocks: list[str] = []

        def prop(n: ex.Prop) -> str:
            p = find_prop(self.onto, self._types[alias], n.name)
            if p.expr:
                inner, more, extra = self._computed(alias, p.expr)
                needed.update(more)
                blocks.extend(extra)
                return inner
            needed.add(n.name)
            return var(Ref(alias, n.name))

        def aggregate(a: ex.Agg) -> str:
            value, block = self._aggregate(alias, a)
            blocks.extend(block)
            return value

        return ex.SparqlRenderer(prop, aggregate).render(node), needed, blocks

    def _path(self, alias: str, steps: list[ex.Step]) -> tuple[list[str], str]:
        lines, prev = [], alias
        for st in steps:
            self._n += 1
            nxt = f"g{self._n}"
            self._types[nxt] = st.type
            p = iri(self._iris.link(st.link))
            lines.append(f"?{prev} {p} ?{nxt} ." if st.forward else f"?{nxt} {p} ?{prev} .")
            lines.append(self._type(nxt))
            prev = nxt
        return lines, prev

    def _value(self, alias: str, prop: str) -> tuple[list[str], str]:
        """Patterns that bind a property of alias to a fresh variable, leaving out the rows without a value."""
        self._n += 1
        v = f"?_v{self._n}"
        p = find_prop(self.onto, self._types[alias], prop)
        if not p.expr:
            return [f"?{alias} {iri(self._iris.prop(prop))} {v} ."], v
        text, needed, blocks = self._computed(alias, p.expr)
        return [*self._stored(alias, needed), *blocks, f"BIND({text} AS {v})", f"FILTER(BOUND({v}))"], v

    def _stored(self, alias: str, names: set[str]) -> list[str]:
        return [f"OPTIONAL {{ ?{alias} {iri(self._iris.prop(n))} {var(Ref(alias, n))} . }}" for n in sorted(names)]

    def _aggregate(self, alias: str, a: ex.Agg) -> tuple[str, list[str]]:
        steps, prop = ex.resolve_agg(self.onto, self._types[alias], a)
        path, last = self._path(alias, steps)
        keep: list[str] = []
        if a.where is not None:  # a false condition or an error leaves the row out, as WHERE does in SQL
            text, needed, blocks = self._expr(last, a.where)
            keep = [*self._stored(last, needed), *blocks, f"FILTER({text})"]
        self._n += 1
        out = f"?_a{self._n}"
        if a.fn in ("latest", "earliest"):
            obj = self.onto.obj(self._types[last])
            tv = f"?_t{self._n}"
            kv = f"?_k{self._n}"
            pick = "MAX" if a.fn == "latest" else "MIN"
            stamp = f'CONCAT(STR({tv}), "|", STR({kv}))'
            first = (f"OPTIONAL {{ SELECT ?{alias} ({pick}({stamp}) AS {out}_s) WHERE {{ {' '.join(path)} "
                     f"?{last} {iri(self._iris.prop(obj.series['time']))} {tv} . "
                     f"?{last} {iri(self._iris.prop(obj.key))} {kv} . {' '.join(keep)} }} GROUP BY ?{alias} }}")
            again, hit = self._path(alias, steps)
            t2, k2 = f"?_t{self._n}b", f"?_k{self._n}b"
            value, v = self._value(hit, prop)
            value = [x for x in value if not x.startswith("FILTER(BOUND")]
            if value and value[0].startswith(f"?{hit} ") and not value[0].startswith("OPTIONAL"):
                value[0] = f"OPTIONAL {{ {value[0]} }}"
            second = (f"OPTIONAL {{ {' '.join(again)} ?{hit} {iri(self._iris.prop(obj.series['time']))} {t2} . "
                      f"?{hit} {iri(self._iris.prop(obj.key))} {k2} . "
                      f'FILTER(CONCAT(STR({t2}), "|", STR({k2})) = {out}_s) {" ".join(value)} BIND({v} AS {out}) }}')
            return out, [first, second]
        if a.fn == "count" and not prop:
            body, arg = [*path, *keep], f"?{last}"
        else:
            lines, arg = self._value(last, prop)
            body = [*path, *lines, *keep]
        fn = "COUNT" if a.fn == "count" else a.fn.upper()
        block = f"OPTIONAL {{ SELECT ?{alias} ({fn}({arg}) AS {out}) WHERE {{ {' '.join(body)} }} GROUP BY ?{alias} }}"
        return (f"COALESCE({out}, 0)" if a.fn == "count" else out), [block]

    def _needed(self, q: Query) -> dict[str, set[str]]:
        need: dict[str, set[str]] = {}
        refs = list(filter_refs(q.where, deep=False))
        for c in q.columns:
            if isinstance(c.expr, Ref):
                refs.append(c.expr)
            elif isinstance(c.expr, Agg):
                if c.expr.ref is not None:
                    refs.append(c.expr.ref)
                refs += filter_refs(c.expr.where, deep=False)
        for r in refs:
            need.setdefault(r.alias, set()).add(r.prop)
        return need

    def _group(self, q: Query, where: str | None) -> list[str]:
        root = next(iter(q.nodes))
        need = self._needed(q)
        lines: list = ["  " + self._type(root)]
        blocks: dict = {}  # optional alias -> the OPTIONAL it is bound in
        after: list[str] = []
        bound = {root}
        for e in q.edges:
            new = None if {e.source, e.target} <= bound else (e.target if e.source in bound else e.source)
            types = [self._type(new)] if new else []
            if e.optional:
                parts = self._props(new, need.get(new, set()))
                block = [self._edge(e), *types, *(x for x in parts if not x.startswith("BIND("))]
                # outside the OPTIONAL: an object that isn't there still gives coalesce(count(...), 0) its 0, as in SQL
                after += [x for x in parts if x.startswith("BIND(")]
                # inside the OPTIONAL it hangs from: side by side, an unbound alias would match every object there is
                holder = next((blocks[a] for a in (e.source, e.target) if a in blocks and a != new), lines)
                holder.append(block)
                blocks[new] = block
            else:
                lines += ["  " + self._edge(e)] + ["  " + t for t in types]
            bound |= {e.source, e.target}
        lines = ["  " + _optional(x) if isinstance(x, list) else x for x in lines]
        for a in q.nodes:
            if a not in blocks:
                lines += ["  " + x for x in self._props(a, need.get(a, set()))]
        lines += ["  " + x for x in after]
        if where:
            lines.append(f"  FILTER({where})")
        return lines

    def _ph(self, value, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        return marker(self._params.add(value, p.type))

    def _filter(self, f) -> str:
        if isinstance(f, Cmp):
            rhs = var(f.value) if isinstance(f.value, Ref) else self._ph(f.value, f.ref)
            return f"{var(f.ref)} {_OP[f.op]} {rhs}"
        if isinstance(f, In):
            if not f.values:
                return "true" if f.negate else "false"
            items = ", ".join(self._ph(v, f.ref) for v in f.values)
            return f"{var(f.ref)} {'NOT IN' if f.negate else 'IN'} ({items})"
        if isinstance(f, Contains):
            return f"CONTAINS(STR({var(f.ref)}), {self._ph(f.value, f.ref)})"
        if isinstance(f, IsNull):
            return f"{'' if f.negate else '!'}BOUND({var(f.ref)})"
        if isinstance(f, And):
            return "(" + " && ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "(" + " || ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Not):
            return f"!({self._filter(f.item)})"
        if isinstance(f, Exists):
            return self._exists(f)
        raise CompileError(f"cannot compile filter {f!r}")

    def _exists(self, f: Exists) -> str:
        parts = []
        known = set(self._types) - set(f.nodes)
        for e in f.edges:
            parts.append(self._edge(e))
            for a in (e.source, e.target):
                if a not in known:
                    parts.append(self._type(a))
                    known.add(a)
        need: dict[str, set[str]] = {}
        for r in filter_refs(f.where, deep=False):
            need.setdefault(r.alias, set()).add(r.prop)
        for a, props in need.items():
            parts += self._props(a, props)
        if f.where is not None:
            parts.append(f"FILTER({self._filter(f.where)})")
        text = f"{'NOT ' if f.negate else ''}EXISTS {{ {' '.join(parts)} }}"
        # an alias an optional edge left unbound would match anything here, where in SQL it matches nothing
        loose = " && ".join(f"BOUND(?{a})" for a in dict.fromkeys(a for e in f.edges for a in (e.source, e.target))
                            if a in self._maybe)
        if not loose:
            return text
        return f"(!({loose}) || {text})" if f.negate else f"({loose} && {text})"

    def _agg(self, a: Agg) -> str:
        if a.func in ("count", "count_distinct"):
            arg = var(a.ref) if a.ref is not None else (f"?{a.node}" if a.node else "*")
            return f"COUNT(DISTINCT {arg})" if a.func == "count_distinct" else f"COUNT({arg})"
        return f"{a.func.upper()}({var(a.ref)})"
