"""IR -> SQL/PGQ (ISO/IEC 9075-16 GRAPH_TABLE) and the CREATE PROPERTY GRAPH that declares the bound tables.

GRAPH_TABLE takes no subquery, so what follows links is worked out in the SQL around it: its COLUMNS give the properties
as plain columns, a link aggregate is a correlated subquery over a second GRAPH_TABLE keyed on the object, and a query
reading one gets a derived table that adds it to each row, for WHERE and GROUP BY to read as a column.
"""
from __future__ import annotations

from xgen_space import expr as ex
from xgen_space.check import aliases_of, find_prop
from xgen_space.compile.base import Compiled, CompileError, Compiler, Params
from xgen_space.compile.sql import qi
from xgen_space.ir import Agg, And, Cmp, Contains, Edge, Exists, In, IsNull, Not, Or, Query, Ref, filter_refs
from xgen_space.model import Ontology

_OP = {"eq": "=", "ne": "<>", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}


def _cols(p) -> str:
    return ", ".join(qi(c) for c in p.cols)


def graph_ddl(onto: Ontology, graph: str = "") -> str:
    """CREATE PROPERTY GRAPH over the source tables: object types are vertices, bound links are edges."""
    graph = graph or onto.name.replace("-", "_")
    verts = []
    for o in onto.objects.values():
        if not o.table:
            continue
        props = ", ".join(f"{qi(p.col)} AS {qi(p.name)}" for p in o.properties.values() if not p.expr and not p.columns)
        verts.append(f"  {qi(o.table)} AS {qi(o.name)} KEY ({_cols(o.key_prop)}) LABEL {qi(o.name)} "
                     f"PROPERTIES ({props})")
    edges = []
    for lk in onto.links.values():
        src, dst = onto.objects[lk.source], onto.objects[lk.target]
        if not (src.table and dst.table):
            continue
        if lk.via:  # the KEY spelled out: a join table often has no primary key to infer it from
            edges.append(f"  {qi(lk.via.table)} AS {qi(lk.name)} "
                         f"KEY ({qi(lk.via.source_column)}, {qi(lk.via.target_column)}) "
                         f"SOURCE KEY ({qi(lk.via.source_column)}) REFERENCES {qi(src.name)} ({_cols(src.key_prop)}) "
                         f"DESTINATION KEY ({qi(lk.via.target_column)}) REFERENCES {qi(dst.name)} "
                         f"({_cols(dst.key_prop)}) LABEL {qi(lk.name)} NO PROPERTIES")
        elif lk.on:
            sp, tp = src.prop(lk.on[0]), dst.prop(lk.on[1])
            if tp.name == dst.key:
                table, key = src, _cols(src.key_prop)
                s_key, s_ref, d_key, d_ref = key, key, _cols(sp), _cols(dst.key_prop)
            elif sp.name == src.key:
                table, key = dst, _cols(dst.key_prop)
                s_key, s_ref, d_key, d_ref = _cols(tp), _cols(src.key_prop), key, key
            else:
                continue
            edges.append(f"  {qi(table.table)} AS {qi(lk.name)} KEY ({key}) "
                         f"SOURCE KEY ({s_key}) REFERENCES {qi(src.name)} ({s_ref}) "
                         f"DESTINATION KEY ({d_key}) REFERENCES {qi(dst.name)} ({d_ref}) "
                         f"LABEL {qi(lk.name)} NO PROPERTIES")
    out = f"CREATE PROPERTY GRAPH {qi(graph)}\n VERTEX TABLES (\n" + ",\n".join(verts) + "\n )"
    if edges:
        out += "\n EDGE TABLES (\n" + ",\n".join(edges) + "\n )"
    return out


class _Rows:
    """One GRAPH_TABLE as the SQL around it reads it: a column for each value asked of it so far."""

    def __init__(self, name: str):
        self.name = name
        self.columns: dict[str, str] = {}  # output column -> value in COLUMNS

    def column(self, name: str, value: str) -> str:
        self.columns[name] = value
        return f"{self.name}.{qi(name)}"

    def clause(self) -> str:
        return ", ".join(f"{v} AS {qi(k)}" for k, v in self.columns.items())


class PgqCompiler(Compiler):
    language = "sqlpgq"

    def __init__(self, onto: Ontology, dialect: str = "oracle", graph: str = ""):
        super().__init__(onto)
        self.dialect = dialect
        self.graph = graph or onto.name.replace("-", "_")

    def compile(self, q: Query | dict) -> Compiled:
        chk = self.checked(q)
        q = chk.query
        if any(e.optional for e in q.edges):
            raise CompileError("SQL/PGQ GRAPH_TABLE has no OPTIONAL MATCH; drop 'optional' or use another backend")
        self._types = aliases_of(q)
        self._params = Params(chk.param_types)
        self._n = 0
        self._rows = _Rows("b")
        self._added: dict[str, str] = {}  # columns the derived table adds to each row
        self._named: dict[str, str] = {}  # property -> its column
        self._around = True  # a filter reads the columns of the rows, not the graph inside GRAPH_TABLE
        pattern = self._pattern(q)
        outer, group = [], []
        for c in q.columns:  # before the where: parameters bind by position and the select list comes first
            if isinstance(c.expr, Ref):
                col = self._column(c.expr, c.name)
                outer.append(f"{col} AS {qi(c.name)}")
                group.append(col)
            else:
                outer.append(f"{self._agg(c.expr)} AS {qi(c.name)}")
        inside = around = ""
        if q.where is not None:
            self._around = any(self._linked(r) for r in filter_refs(q.where, deep=False))
            cond = self._filter(q.where)
            around, inside = (f"WHERE {cond}", "") if self._around else ("", f"\n  WHERE {cond}")
        table = [f"GRAPH_TABLE ({qi(self.graph)}", f"  MATCH {pattern}{inside}", f"  COLUMNS ({self._rows.clause()})"]
        lines = ["SELECT " + ("DISTINCT " if q.distinct else "") + ", ".join(outer)]
        if self._added:
            added = ", ".join(f"{v} AS {qi(k)}" for k, v in self._added.items())
            lines += [f"FROM (SELECT b.*, {added} FROM {table[0]}", *table[1:], ") b) gt"]
        else:
            lines += [f"FROM {table[0]}", *table[1:], ") gt"]
        if around:
            lines.append(around)
        if q.aggregated and group:
            lines.append("GROUP BY " + ", ".join(group))
        if q.order:
            lines.append("ORDER BY " + ", ".join(f"{qi(o.name)} {'DESC' if o.desc else 'ASC'} NULLS LAST"
                                                  for o in q.order))
        if q.limit is not None:
            lines.append(f"FETCH FIRST {int(q.limit)} ROWS ONLY")
        return Compiled("sqlpgq", self.dialect, "\n".join(lines), "positional", list(self._params.order),
                        self._params.types, [c.name for c in q.columns], chk.column_types, self._params.literals)

    def _agg(self, e: Agg) -> str:
        cond = self._filter(e.where) if e.where is not None else ""

        def kept(arg: str) -> str:
            return f"CASE WHEN {cond} THEN {arg} END" if cond else arg

        ref = e.ref
        if ref is None and e.node:
            ref = Ref(e.node, self.onto.obj(self._types[e.node]).key)
        if ref is None:
            return f"COUNT({kept('1')})" if cond else "COUNT(*)"
        arg = kept(self._column(ref))
        return f"COUNT(DISTINCT {arg})" if e.func == "count_distinct" else f"{e.func.upper()}({arg})"

    def _node(self, alias: str, seen: set[str]) -> str:
        if alias in seen:
            return f"({alias})"
        seen.add(alias)
        return f"({alias} IS {qi(self._types[alias])})"

    def _edge(self, e: Edge, seen: set[str]) -> str:
        self._n += 1
        rel = f"[e{self._n} IS {qi(e.link)}]"
        quant = f"{{{e.min_hops},{e.max_hops}}}" if e.hops else ""
        a, b = self._node(e.source, seen), self._node(e.target, seen)
        return f"{a}<-{rel}-{quant}{b}" if e.reverse else f"{a}-{rel}->{quant}{b}"

    def _pattern(self, q: Query) -> str:
        seen: set[str] = set()
        if not q.edges:
            return self._node(next(iter(q.nodes)), seen)
        return ", ".join(self._edge(e, seen) for e in q.edges)

    def _stored(self, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        if p.columns:
            raise CompileError(f"SQL/PGQ reads one column per property; {ref.prop} is read from {len(p.columns)}")
        return f"{ref.alias}.{qi(ref.prop)}"

    def _prop(self, ref: Ref) -> str:
        """A property inside GRAPH_TABLE, where a computed one reads the graph's properties."""
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        return self._computed(ref.alias, p.expr) if p.expr else self._stored(ref)

    def _computed(self, alias: str, text: str) -> str:
        return self._render(ex.PgqRenderer(lambda n: self._prop(Ref(alias, n.name)), None), self._parsed(alias, text))

    def _parsed(self, alias: str, text: str):
        try:
            return ex.prepare(self.onto, self._types[alias], ex.parse_expr(text))
        except ex.ExprError as e:
            raise CompileError(str(e)) from None

    @staticmethod
    def _render(renderer: ex.PgqRenderer, node) -> str:
        try:
            return renderer.render(node)
        except ex.ExprError as e:
            raise CompileError(str(e)) from None

    def _reads_links(self, type_name: str, text: str) -> bool:
        for n in ex.walk(ex.parse_expr(text)):
            if isinstance(n, ex.Agg):
                return True
            if isinstance(n, ex.Prop):
                p = find_prop(self.onto, type_name, n.name)
                if p.expr and self._reads_links(type_name, p.expr):
                    return True
        return False

    def _linked(self, ref: Ref) -> bool:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        return bool(p.expr) and self._reads_links(self._types[ref.alias], p.expr)

    def _column(self, ref: Ref, name: str = "") -> str:
        """A property as a column of the rows the outer SELECT reads, worked out once however often it is read."""
        name = self._named.setdefault(str(ref), name or f"{ref.alias}__{ref.prop}")
        if name in self._added or name in self._rows.columns:
            pass
        elif self._linked(ref):
            p = find_prop(self.onto, self._types[ref.alias], ref.prop)
            self._added[name] = self._over(self._rows, ref.alias, self._parsed(ref.alias, p.expr))
        else:
            self._rows.columns[name] = self._prop(ref)
        return f"gt.{qi(name)}"

    def _over(self, rows: _Rows, alias: str, node) -> str:
        """An expression in the SQL around a GRAPH_TABLE, over the columns of its rows."""
        def prop(n: ex.Prop) -> str:
            p = find_prop(self.onto, self._types[alias], n.name)
            if p.expr:
                return self._over(rows, alias, self._parsed(alias, p.expr))
            return rows.column(f"{alias}__{n.name}", self._stored(Ref(alias, n.name)))

        return self._render(ex.PgqRenderer(prop, lambda a: self._subquery(rows, alias, a)), node)

    def _subquery(self, rows: _Rows, alias: str, a: ex.Agg) -> str:
        """A link aggregate: a second GRAPH_TABLE from the same type along the links, matched to the row by its key."""
        steps, prop = ex.resolve_agg(self.onto, self._types[alias], a)
        self._n += 1
        start, sub = f"k{self._n}", _Rows(f"s{self._n}")
        self._types[start] = self._types[alias]
        pattern, prev = self._node(start, set()), start
        for st in steps:
            self._n += 1
            nxt = f"g{self._n}"
            self._types[nxt] = st.type
            rel = f"[e{self._n} IS {qi(st.link)}]"
            node = f"({nxt} IS {qi(st.type)})"
            pattern += f"-{rel}->{node}" if st.forward else f"<-{rel}-{node}"
            prev = nxt
        key = ex.Prop(self.onto.obj(self._types[alias]).key)
        conds = [f"{self._over(sub, start, key)} = {self._over(rows, alias, key)}"]
        if a.where is not None:
            conds.append(self._over(sub, prev, a.where))
        value = self._over(sub, prev, ex.Prop(prop)) if prop else ""
        tail = ""
        if a.fn in ("latest", "earliest"):
            obj = self.onto.obj(self._types[prev])
            time, stamp = self._over(sub, prev, ex.Prop(obj.series["time"])), self._over(sub, prev, ex.Prop(obj.key))
            way = "DESC" if a.fn == "latest" else "ASC"
            conds.append(f"{time} IS NOT NULL")
            tail = f" ORDER BY {time} {way}, CAST({stamp} AS VARCHAR(4000)) {way} FETCH FIRST 1 ROW ONLY"
        else:
            value = f"{a.fn.upper()}({value or '*'})"
        table = f"GRAPH_TABLE ({qi(self.graph)} MATCH {pattern} COLUMNS ({sub.clause()})) {sub.name}"
        return f"(SELECT {value} FROM {table} WHERE {' AND '.join(conds)}{tail})"

    def _value(self, ref: Ref) -> str:
        return self._column(ref) if self._around else self._prop(ref)

    def _ph(self, value, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        self._params.add(value, p.type)
        return "?"

    def _filter(self, f) -> str:
        if isinstance(f, Cmp):
            rhs = self._value(f.value) if isinstance(f.value, Ref) else self._ph(f.value, f.ref)
            return f"{self._value(f.ref)} {_OP[f.op]} {rhs}"
        if isinstance(f, In):
            if not f.values:
                return "1 = 1" if f.negate else "1 = 0"
            marks = ", ".join(self._ph(v, f.ref) for v in f.values)
            return f"{self._value(f.ref)} {'NOT IN' if f.negate else 'IN'} ({marks})"
        if isinstance(f, Contains):
            ph = self._ph(f.value, f.ref)
            if self.dialect == "oracle":  # the one engine here without ISO's POSITION
                return f"INSTR({self._value(f.ref)}, {ph}) > 0"
            return f"POSITION({ph} IN {self._value(f.ref)}) > 0"
        if isinstance(f, IsNull):
            return f"{self._value(f.ref)} IS {'NOT ' if f.negate else ''}NULL"
        if isinstance(f, And):
            return "(" + " AND ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "(" + " OR ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Not):
            return f"NOT ({self._filter(f.item)})"
        if isinstance(f, Exists):
            raise CompileError("SQL/PGQ GRAPH_TABLE has no EXISTS sub-pattern; use another backend")
        raise CompileError(f"cannot compile filter {f!r}")
