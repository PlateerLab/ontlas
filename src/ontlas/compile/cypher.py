"""IR -> Cypher 25 / openCypher, and ISO GQL as a dialect of the same pattern compiler."""
from __future__ import annotations

from ontlas import expr as ex
from ontlas.check import aliases_of, find_prop
from ontlas.compile.base import Compiled, CompileError, Compiler, Params
from ontlas.ir import Agg, And, Cmp, Contains, Edge, Exists, In, IsNull, Not, Or, Query, Ref

_OP = {"eq": "=", "ne": "<>", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}


def bq(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


class CypherCompiler(Compiler):
    language = "cypher"
    dialect = "neo4j"
    gql = False

    def compile(self, q: Query | dict) -> Compiled:
        chk = self.checked(q)
        q = chk.query
        self._types = aliases_of(q)
        self._params = Params(chk.param_types)
        self._n = 0
        lines = self._match(q)
        if q.where is not None:
            cond = self._filter(q.where)
            if any(e.optional for e in q.edges):
                lines += [f"FILTER {cond}"] if self.gql else ["WITH *", f"WHERE {cond}"]
            else:
                lines.append(f"WHERE {cond}")
        lines += self._return(q)
        names = list(dict.fromkeys(self._params.order))
        return Compiled(self.language, self.dialect, "\n".join(lines), "named", names, self._params.types,
                        [c.name for c in q.columns], chk.column_types, self._params.literals)

    def _node(self, alias: str, seen: set[str]) -> str:
        if alias in seen:
            return f"({alias})"
        seen.add(alias)
        return f"({alias}:{bq(self._types[alias])})"

    def _hops(self, e: Edge) -> tuple[str, str]:
        if not e.hops:
            return "", ""
        if self.gql:
            return "", f"{{{e.min_hops},{e.max_hops}}}"
        return f"*{e.min_hops}..{e.max_hops}", ""

    def _edge(self, e: Edge, seen: set[str]) -> str:
        star, quant = self._hops(e)
        rel = f"[:{bq(e.link)}{star}]"
        a, b = self._node(e.source, seen), self._node(e.target, seen)
        body = f"{a}<-{rel}-{quant}{b}" if e.reverse else f"{a}-{rel}->{quant}{b}"
        return f"ANY {body}" if self.gql and e.hops else body

    def _match(self, q: Query) -> list[str]:
        seen: set[str] = set()
        root = next(iter(q.nodes))
        required = [self._edge(e, seen) for e in q.edges if not e.optional]
        if not required:
            required = [self._node(root, seen)]
        lines = ["MATCH " + ", ".join(required)]
        if not self.gql and any(e.hops for e in q.edges):
            lines.append("WITH DISTINCT " + ", ".join(sorted(seen)))
        for e in q.edges:
            if e.optional:
                lines.append("OPTIONAL MATCH " + self._edge(e, seen))
        return lines

    def _prop(self, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        if p.expr and not self.by_name:
            return self._computed(ref.alias, p.expr)
        return f"{ref.alias}.{bq(ref.prop)}"

    def _renderer(self, alias: str) -> ex.CypherRenderer:
        return ex.CypherRenderer(lambda n: self._prop(Ref(alias, n.name)), lambda a: self._aggregate(alias, a), self.gql)

    def _computed(self, alias: str, text: str) -> str:
        try:
            return self._renderer(alias).render(ex.prepare(self.onto, self._types[alias], ex.parse_expr(text)))
        except ex.ExprError as e:
            raise CompileError(str(e)) from None

    def _value_query(self, pattern: str, prev: str, a: ex.Agg, prop: str, cond: str) -> str:
        """ISO GQL has no list comprehension; a VALUE subquery gives one value, and it reads the outer row's aliases."""
        value = self._prop(Ref(prev, prop)) if prop else ""
        wheres = [cond] if cond else []
        if a.fn in ("latest", "earliest"):
            obj = self.onto.obj(self._types[prev])
            time, key = f"{prev}.{bq(obj.series['time'])}", f"{prev}.{bq(obj.key)}"
            way = "DESC" if a.fn == "latest" else "ASC"
            test = " AND ".join([f"{time} IS NOT NULL", *wheres])
            pick = f"ORDER BY {time} {way}, {key} {way} LIMIT 1"
            return f"VALUE {{ MATCH {pattern} WHERE {test} {pick} RETURN {value} AS v }}"
        match = f"MATCH {pattern}" + (f" WHERE {cond}" if cond else "")
        return f"VALUE {{ {match} RETURN {a.fn.upper()}({value or '*'}) AS v }}"

    def _aggregate(self, alias: str, a: ex.Agg) -> str:
        """A pattern comprehension along the aggregate's links, folded with reduce."""
        steps, prop = ex.resolve_agg(self.onto, self._types[alias], a)
        pattern, prev = f"({alias})", alias
        for st in steps:
            self._n += 1
            nxt = f"g{self._n}"
            self._types[nxt] = st.type
            rel = f"[:{bq(st.link)}]"
            node = f"({nxt}:{bq(st.type)})"
            pattern += f"-{rel}->{node}" if st.forward else f"<-{rel}-{node}"
            prev = nxt
        cond = self._renderer(prev).render(a.where) if a.where is not None else ""
        if self.gql:
            return self._value_query(pattern, prev, a, prop, cond)
        keep = f" WHERE {cond}" if cond else ""
        n = self._n
        # head([l IN [list] | f(l)]) evaluates the list once and names it, so nesting stays linear in size
        if a.fn in ("latest", "earliest"):
            obj = self.onto.obj(self._types[prev])
            time, key = bq(obj.series["time"]), bq(obj.key)
            b, h, best = f"_b{n}", f"_h{n}", f"_n{n}"
            later = ">" if a.fn == "latest" else "<"
            stamp = "toString({0}.{1}) + '|' + toString({0}.{2})"
            nodes = f"[{pattern} WHERE {prev}.{time} IS NOT NULL{f' AND {cond}' if cond else ''} | {prev}]"
            pick = (f"reduce({b} = null, {h} IN {nodes} | CASE WHEN {b} IS NULL OR "
                    f"{stamp.format(h, time, key)} {later} {stamp.format(b, time, key)} THEN {h} ELSE {b} END)")
            self._types[best] = self._types[prev]
            return f"head([{best} IN [{pick}] | {self._prop(Ref(best, prop))}])"
        if a.fn == "count" and not prop:
            return f"size([{pattern}{keep} | {prev}])"
        y, lst, s, x = f"_y{n}", f"_l{n}", f"_s{n}", f"_x{n}"
        items = f"[{y} IN [{pattern}{keep} | {self._prop(Ref(prev, prop))}] WHERE {y} IS NOT NULL]"
        if a.fn == "count":
            return f"size({items})"
        if a.fn in ("sum", "avg"):
            total = f"reduce({s} = 0, {x} IN {lst} | {s} + {x})"
            value = total if a.fn == "sum" else f"toFloat({total}) / size({lst})"
            return f"head([{lst} IN [{items}] | CASE WHEN size({lst}) = 0 THEN null ELSE {value} END])"
        cmp = "<" if a.fn == "min" else ">"
        return f"reduce({s} = null, {x} IN {items} | CASE WHEN {s} IS NULL OR {x} {cmp} {s} THEN {x} ELSE {s} END)"

    def _ph(self, value, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        return "$" + self._params.add(value, p.type)

    def _filter(self, f) -> str:
        if isinstance(f, Cmp):
            rhs = self._prop(f.value) if isinstance(f.value, Ref) else self._ph(f.value, f.ref)
            return f"{self._prop(f.ref)} {_OP[f.op]} {rhs}"
        if isinstance(f, In):
            p = find_prop(self.onto, self._types[f.ref.alias], f.ref.prop)
            name = self._params.add(list(f.values), p.type)
            self._params.types[name] = p.type
            expr = f"{self._prop(f.ref)} IN ${name}"
            return f"NOT ({expr})" if f.negate else expr
        if isinstance(f, Contains):
            if self.gql:
                raise CompileError("ISO GQL has no substring predicate; register a backend query for it")
            return f"{self._prop(f.ref)} CONTAINS {self._ph(f.value, f.ref)}"
        if isinstance(f, IsNull):
            return f"{self._prop(f.ref)} IS {'NOT ' if f.negate else ''}NULL"
        if isinstance(f, And):
            return "(" + " AND ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "(" + " OR ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Not):
            return f"NOT ({self._filter(f.item)})"
        if isinstance(f, Exists):
            seen = set(self._types) - set(f.nodes)
            pats = ", ".join(self._edge(e, seen) for e in f.edges)
            body = f"MATCH {pats}" + (f" WHERE {self._filter(f.where)}" if f.where is not None else "")
            return f"{'NOT ' if f.negate else ''}EXISTS {{ {body} }}"
        raise CompileError(f"cannot compile filter {f!r}")

    def _agg(self, a: Agg) -> str:
        cond = self._filter(a.where) if a.where is not None else ""

        def kept(arg: str) -> str:
            return f"CASE WHEN {cond} THEN {arg} END" if cond else arg

        if a.func in ("count", "count_distinct"):
            arg = self._prop(a.ref) if a.ref is not None else (a.node or ("1" if cond else "*"))
            return f"count(DISTINCT {kept(arg)})" if a.func == "count_distinct" else f"count({kept(arg)})"
        value = kept(self._prop(a.ref))
        if a.func == "sum" and cond and not self.gql:  # Cypher's sum of no rows is 0, where SQL and GQL give null
            return f"CASE WHEN count({value}) = 0 THEN null ELSE sum({value}) END"
        return f"{a.func}({value})"

    def _return(self, q: Query) -> list[str]:
        items, keys = [], []
        for c in q.columns:
            if isinstance(c.expr, Ref):
                items.append(f"{self._prop(c.expr)} AS {bq(c.name)}")
                keys.append(bq(c.name))
            else:
                items.append(f"{self._agg(c.expr)} AS {bq(c.name)}")
        line = "RETURN " + ("DISTINCT " if q.distinct else "") + ", ".join(items)
        if self.gql and q.aggregated and keys:
            line += " GROUP BY " + ", ".join(keys)
        out = [line]
        if q.order:
            if self.gql:
                out.append("ORDER BY " + ", ".join(f"{bq(o.name)} {'DESC' if o.desc else 'ASC'} NULLS LAST"
                                                  for o in q.order))
            else:
                out.append("ORDER BY " + ", ".join(f"{bq(o.name)} IS NULL, {bq(o.name)}{' DESC' if o.desc else ''}"
                                                  for o in q.order))
        if q.limit is not None:
            out.append(f"LIMIT {int(q.limit)}")
        return out


class GqlCompiler(CypherCompiler):
    language = "gql"
    dialect = "iso"
    gql = True
