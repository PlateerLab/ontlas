"""IR -> SQL over the bound source tables (joins, recursive CTEs), other dialects via sqlglot."""
from __future__ import annotations

from dataclasses import dataclass

from xgen_space import expr as ex
from xgen_space.check import aliases_of, columns_of, concrete_subtypes, find_prop, stored_props
from xgen_space.compile.base import Compiled, CompileError, Compiler, Params
from xgen_space.ir import Agg, And, Cmp, Contains, Edge, Exists, In, IsNull, Not, Or, Query, Ref
from xgen_space.model import KEY_SEP

NATIVE = ("postgres", "sqlite")
_OP = {"eq": "=", "ne": "<>", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}
_NAMES = {"mssql": "tsql", "sqlserver": "tsql"}
_TESTS = ("=", "!=", "<", ">", "<=", ">=")
_BINARY = "Latin1_General_100_BIN2"  # compares code points, whatever the database's collation says


def joined(prefix: str, cols: list[str]) -> str:
    """A column, or the text of several columns joined: a key read from more than one."""
    if len(cols) == 1:
        return f"{prefix}{qi(cols[0])}"
    return "(" + f" || '{KEY_SEP}' || ".join(f"CAST({prefix}{qi(c)} AS VARCHAR(4000))" for c in cols) + ")"


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class _NoBooleans(ex.SqlRenderer):
    """SQL where a condition is not a value (SQL Server, Oracle before 23ai): a condition read as a value becomes
    1 or 0 and stays null when it cannot be told, and a true/false column read as a condition is compared to 1."""

    def render(self, node) -> str:
        if isinstance(node, ex.Call) and node.fn == "if":
            c, a, b = self.condition(node.args[0]), self.render(node.args[1]), self.render(node.args[2])
            return f"(CASE WHEN {c} THEN {a} WHEN NOT {c} THEN {b} END)"
        if (isinstance(node, ex.Bin) and node.op in (*_TESTS, "and", "or")) or (
                isinstance(node, ex.Unary) and node.op == "not"):
            c = self.condition(node)
            return f"(CASE WHEN {c} THEN 1 WHEN NOT {c} THEN 0 END)"
        return super().render(node)

    def condition(self, node) -> str:
        if isinstance(node, ex.Unary) and node.op == "not":
            return f"(NOT {self.condition(node.arg)})"
        if isinstance(node, ex.Bin) and node.op in ("and", "or"):
            return f"({self.condition(node.left)} {node.op.upper()} {self.condition(node.right)})"
        if isinstance(node, ex.Bin) and node.op in _TESTS:
            return super().render(node)
        return f"({self.render(node)} = 1)"

    def lit(self, node) -> str:
        return str(int(node.value)) if node.type == "boolean" else super().lit(node)


class _Oracle(_NoBooleans):
    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        if fn == "concat":  # || passes over a null here; the rule everywhere is that a null operand gives null
            return f"(CASE WHEN {' OR '.join(f'{a} IS NULL' for a in args)} THEN NULL ELSE {' || '.join(args)} END)"
        return super().call(fn, args, nodes)


@dataclass
class _Step:
    table: str
    alias: str
    cond: str


class SqlCompiler(Compiler):
    language = "sql"

    def __init__(self, onto, dialect: str = "postgres"):
        super().__init__(onto)
        self.dialect = _NAMES.get(dialect, dialect)
        self.native = self.dialect if self.dialect in NATIVE else "postgres"

    def compile(self, q: Query | dict) -> Compiled:
        chk = self.checked(q)
        q = chk.query
        self._types = aliases_of(q)
        self._params = Params(chk.param_types)
        self._ctes: list[str] = []
        self._n = 0
        sql = self._select(q)
        if self._ctes:  # Oracle refuses the word: a WITH that names itself is recursive there
            sql = ("WITH " if self.dialect == "oracle" else "WITH RECURSIVE ") + ",\n".join(self._ctes) + "\n" + sql
        if self.dialect not in NATIVE:
            sql = _transpile(sql, self.dialect)
        return Compiled("sql", self.dialect, sql, "positional", list(self._params.order), self._params.types,
                        [c.name for c in q.columns], chk.column_types, self._params.literals)

    def _table(self, alias: str) -> str:
        obj = self.onto.obj(self._types[alias])
        if obj.table:
            return qi(obj.table)
        subs = concrete_subtypes(self.onto, obj.name)
        if not subs:
            raise CompileError(f"{obj.name} has no source table and no bound subtype")
        names = stored_props(self.onto, obj.name)
        parts = []
        for s in subs:
            cols = ", ".join(f"{joined('', columns_of(self.onto, s, n))} AS {qi(n)}" for n in names)
            parts.append(f"SELECT {cols}, '{s}' AS {qi('__type')} FROM {qi(self.onto.objects[s].table)}")
        return "(" + " UNION ALL ".join(parts) + ")"

    def _col(self, ref: Ref) -> str:
        t = self._types[ref.alias]
        p = find_prop(self.onto, t, ref.prop)
        if p.expr:
            return self._computed(ref.alias, p.expr)
        if not self.onto.objects[t].table:
            return f"t_{ref.alias}.{qi(ref.prop)}"
        return joined(f"t_{ref.alias}.", columns_of(self.onto, t, ref.prop))

    def _computed(self, alias: str, text: str) -> str:
        kind = {"oracle": _Oracle, "tsql": _NoBooleans}.get(self.dialect, ex.SqlRenderer)
        r = kind(lambda n: self._col(Ref(alias, n.name)), lambda a: self._aggregate(alias, a), self.native)
        try:
            return r.render(ex.prepare(self.onto, self._types[alias], ex.parse_expr(text)))
        except ex.ExprError as e:
            raise CompileError(str(e)) from None

    def _aggregate(self, alias: str, a: ex.Agg) -> str:
        """A correlated subquery that follows the aggregate's links from the alias."""
        steps, prop = ex.resolve_agg(self.onto, self._types[alias], a)
        edges, prev = [], alias
        for st in steps:
            self._n += 1
            nxt = f"g{self._n}"
            self._types[nxt] = st.type
            edges.append(Edge(prev, st.link, nxt, reverse=not st.forward))
            prev = nxt
        path, extra = self._pattern(edges, {alias})
        first, rest = path[0][0], path[1:]
        body = [f"FROM {first.table} {first.alias}", *(f"JOIN {s.table} {s.alias} ON {s.cond}" for s, _ in rest)]
        conds = [first.cond, *extra]
        if a.fn in ("latest", "earliest"):
            obj = self.onto.obj(self._types[prev])
            time, key = self._col(Ref(prev, obj.series["time"])), self._key(prev)
            way = "DESC" if a.fn == "latest" else "ASC"
            conds.append(f"{time} IS NOT NULL")
            return (f"(SELECT {self._col(Ref(prev, prop))} {' '.join(body)} WHERE {' AND '.join(conds)} "
                    f"ORDER BY {time} {way}, CAST({key} AS VARCHAR) {way} LIMIT 1)")
        if a.fn == "count" and not prop:
            return f"(SELECT COUNT(*) {' '.join(body)} WHERE {' AND '.join(conds)})"
        val = self._col(Ref(prev, prop))
        if self.dialect == "tsql" and "(SELECT" in val:  # it takes no aggregate over a subquery, only over a named value
            return f"(SELECT {a.fn.upper()}(t_v.v) FROM (SELECT {val} AS v {' '.join(body)} " \
                   f"WHERE {' AND '.join(conds)}) t_v)"
        return f"(SELECT {a.fn.upper()}({val}) {' '.join(body)} WHERE {' AND '.join(conds)})"

    def _key(self, alias: str) -> str:
        obj = self.onto.obj(self._types[alias])
        return joined(f"t_{alias}.", obj.key_prop.cols if obj.table else [obj.key])

    def _closure(self, lk, e: Edge) -> str:
        self._n += 1
        r, src = f"r_{self._n}", self.onto.obj(lk.source)
        if not src.table:
            raise CompileError(f"hops on '{lk.name}' need {src.name} bound to a table")
        if lk.via:
            base = (f"SELECT {qi(lk.via.source_column)} AS s, {qi(lk.via.target_column)} AS t "
                    f"FROM {qi(lk.via.table)}")
        elif lk.on:
            sp, tp = src.prop(lk.on[0]), src.prop(lk.on[1])
            key = src.key_prop.cols
            base = (f"SELECT {joined('a.', key)} AS s, {joined('b.', key)} AS t FROM {qi(src.table)} a "
                    f"JOIN {qi(src.table)} b ON {joined('a.', sp.cols)} = {joined('b.', tp.cols)}")
        else:
            raise CompileError(f"link {lk.name} has no source binding (on/via)")
        self._ctes.append(f"{r}(s, t, d) AS (SELECT s, t, 1 FROM ({base}) b0 UNION ALL "
                          f"SELECT {r}.s, b1.t, {r}.d + 1 FROM {r} JOIN ({base}) b1 ON b1.s = {r}.t "
                          f"WHERE {r}.d < {e.max_hops})")
        return f"(SELECT DISTINCT s, t FROM {r} WHERE d >= {e.min_hops})"

    def _steps(self, e: Edge, known: str, new: str) -> list[_Step]:
        lk = self.onto.link(e.link)
        ls, lt = (e.target, e.source) if e.reverse else (e.source, e.target)
        known_is_source = known == ls
        if e.hops:
            self._n += 1
            c = f"c_{self._n}"
            closure = self._closure(lk, e)
            near, far = ("s", "t") if known_is_source else ("t", "s")
            return [_Step(closure, c, f"{c}.{near} = {self._key(known)}"),
                    _Step(self._table(new), f"t_{new}", f"{self._key(new)} = {c}.{far}")]
        if lk.via:
            self._n += 1
            j = f"j_{self._n}"
            sc, tc = qi(lk.via.source_column), qi(lk.via.target_column)
            near, far = (sc, tc) if known_is_source else (tc, sc)
            return [_Step(qi(lk.via.table), j, f"{j}.{near} = {self._key(known)}"),
                    _Step(self._table(new), f"t_{new}", f"{self._key(new)} = {j}.{far}")]
        if lk.on:
            return [_Step(self._table(new), f"t_{new}", self._on_cond(lk, ls, lt))]
        raise CompileError(f"link {lk.name} has no source binding (on/via)")

    def _on_cond(self, lk, ls: str, lt: str) -> str:
        st, tt = self._types[ls], self._types[lt]
        if self.onto.objects[st].table and self.onto.objects[tt].table:
            a, b = columns_of(self.onto, st, lk.on[0]), columns_of(self.onto, tt, lk.on[1])
            if len(a) > 1 and len(a) == len(b):  # column by column, so the database can use its keys
                return " AND ".join(f"t_{ls}.{qi(x)} = t_{lt}.{qi(y)}" for x, y in zip(a, b))
        return f"{self._col(Ref(ls, lk.on[0]))} = {self._col(Ref(lt, lk.on[1]))}"

    def _pattern(self, edges: list[Edge], known: set[str]) -> tuple[list[tuple[_Step, bool]], list[str]]:
        steps: list[tuple[_Step, bool]] = []
        extra: list[str] = []
        known = set(known)
        for e in edges:
            if e.source in known and e.target in known:
                lk = self.onto.link(e.link)
                if not lk.on or e.hops:
                    raise CompileError(f"a cycle through '{lk.name}' needs an 'on' link without hops")
                ls, lt = (e.target, e.source) if e.reverse else (e.source, e.target)
                extra.append(self._on_cond(lk, ls, lt))
                continue
            k, n = (e.source, e.target) if e.source in known else (e.target, e.source)
            steps += [(s, e.optional) for s in self._steps(e, k, n)]
            known.add(n)
        return steps, extra

    def _select(self, q: Query) -> str:
        root = next(iter(q.nodes))
        steps, extra = self._pattern(q.edges, {root})
        sql = [f"FROM {self._table(root)} t_{root}"]
        for s, opt in steps:
            sql.append(f"{'LEFT JOIN' if opt else 'JOIN'} {s.table} {s.alias} ON {s.cond}")
        conds = extra + ([self._filter(q.where)] if q.where is not None else [])
        cols, group, read = [], [], []
        for c in q.columns:
            if isinstance(c.expr, Ref):
                expr = self._col(c.expr)
                group.append(expr)
                read.append(expr)
            else:
                read.append(self._agg_arg(c.expr))
                expr = self._agg(c.expr, read[-1])
            cols.append(f"{expr} AS {qi(c.name)}")
        head = "SELECT " + ("DISTINCT " if q.distinct else "") + ", ".join(cols)
        out = [head, *sql]
        if conds:
            out.append("WHERE " + " AND ".join(conds))
        if q.aggregated:
            if any("(SELECT" in x for x in {"tsql": read, "oracle": group}.get(self.dialect, ())):
                out = self._group_outside(q, out[1:], read)
            elif group:
                out.append("GROUP BY " + ", ".join(group))
        if q.order:
            outer = ""
            if self.dialect == "tsql":  # NULLS LAST becomes a CASE there, and a CASE cannot see the names of a SELECT
                outer = "t_out."
                out = ["SELECT * FROM (" + "\n".join(out) + ") t_out"]
            out.append("ORDER BY " + ", ".join(f"{outer}{qi(o.name)} {'DESC' if o.desc else 'ASC'} NULLS LAST"
                                              for o in q.order))
        if q.limit is not None:
            out.append(f"LIMIT {int(q.limit)}")
        return "\n".join(out)

    def _group_outside(self, q: Query, body: list[str], read: list[str]) -> list[str]:
        """Oracle and SQL Server cannot group by a subquery, nor SQL Server aggregate one, and a computed property that
        follows a link is one: give the values names in a SELECT of their own, and work on those."""
        inner, outer, names = [], [], []
        for i, (c, text) in enumerate(zip(q.columns, read)):
            name = qi(c.name if isinstance(c.expr, Ref) else f"__v{i}")
            if text != "*":
                inner.append(f"{text} AS {name}")
            if isinstance(c.expr, Ref):
                names.append(f"t_in.{name}")
                outer.append(f"t_in.{name} AS {name}")
            else:
                outer.append(f"{self._agg(c.expr, text if text == '*' else f't_in.{name}')} AS {qi(c.name)}")
        return ["SELECT " + ("DISTINCT " if q.distinct else "") + ", ".join(outer),
                "FROM (SELECT " + ", ".join(inner) + "\n" + "\n".join(body) + ") t_in",
                *(["GROUP BY " + ", ".join(names)] if names else [])]

    def _agg_arg(self, a: Agg) -> str:
        if a.func in ("count", "count_distinct") and a.ref is None:
            return self._key(a.node) if a.node else "*"
        return self._col(a.ref)

    def _agg(self, a: Agg, arg: str) -> str:
        if a.func == "count_distinct":
            return f"COUNT(DISTINCT {arg})"
        return f"{a.func.upper()}({arg})"

    def _ph(self, value, ref: Ref) -> str:
        p = find_prop(self.onto, self._types[ref.alias], ref.prop)
        self._params.add(value, p.type)
        return "?"

    def _filter(self, f) -> str:
        if isinstance(f, Cmp):
            if self.dialect == "oracle" and f.op in ("eq", "ne") and f.value == "":  # Oracle stores no empty text
                return self._filter(IsNull(f.ref, negate=f.op == "ne"))
            rhs = self._col(f.value) if isinstance(f.value, Ref) else self._ph(f.value, f.ref)
            return f"{self._col(f.ref)} {_OP[f.op]} {rhs}"
        if isinstance(f, In):
            if not f.values:
                return "1 = 1" if f.negate else "1 = 0"
            if self.dialect == "oracle" and "" in f.values:  # NOT IN with a null in the list would refuse every row
                rest = self._filter(In(f.ref, [v for v in f.values if v != ""], f.negate))
                return f"({rest} {'AND' if f.negate else 'OR'} {self._filter(IsNull(f.ref, negate=f.negate))})"
            marks = ", ".join(self._ph(v, f.ref) for v in f.values)
            return f"{self._col(f.ref)} {'NOT IN' if f.negate else 'IN'} ({marks})"
        if isinstance(f, Contains):
            col = self._col(f.ref)
            if self.dialect in ("oracle", "tsql") and f.value == "":  # INSTR gives null there, CHARINDEX 0
                return f"{col} IS NOT NULL"
            ph = self._ph(f.value, f.ref)
            if self.native == "sqlite":
                return f"instr({col}, {ph}) > 0"
            if self.dialect == "tsql":  # the usual collation ignores case, and the search does not elsewhere
                col = f"{col} COLLATE {_BINARY}"
            return f"strpos({col}, {ph}) > 0"
        if isinstance(f, IsNull):
            return f"{self._col(f.ref)} IS {'NOT ' if f.negate else ''}NULL"
        if isinstance(f, And):
            return "(" + " AND ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Or):
            return "(" + " OR ".join(self._filter(x) for x in f.items) + ")"
        if isinstance(f, Not):
            return f"NOT ({self._filter(f.item)})"
        if isinstance(f, Exists):
            return self._exists(f)
        raise CompileError(f"cannot compile filter {f!r}")

    def _exists(self, f: Exists) -> str:
        outer = set(self._types) - set(f.nodes)
        steps, extra = self._pattern(f.edges, outer)
        if not steps:
            raise CompileError("exists needs an edge to a new alias")
        first, rest = steps[0][0], steps[1:]
        parts = [f"SELECT 1 FROM {first.table} {first.alias}"]
        for s, opt in rest:
            parts.append(f"{'LEFT JOIN' if opt else 'JOIN'} {s.table} {s.alias} ON {s.cond}")
        conds = [first.cond, *extra]
        if f.where is not None:
            conds.append(self._filter(f.where))
        parts.append("WHERE " + " AND ".join(conds))
        return f"{'NOT ' if f.negate else ''}EXISTS ({' '.join(parts)})"


def _sized(exp, tree) -> None:
    """Text needs a stated size: a bare VARCHAR is an error on Oracle and 30 letters on SQL Server."""
    for c in tree.find_all(exp.Cast):
        if c.to.is_type("varchar") and not c.to.expressions:
            c.set("to", exp.DataType.build("VARCHAR(4000)"))


def _tsql(exp, tree) -> None:
    """What the writer leaves as PostgreSQL has it, and SQL Server takes otherwise or not at all."""
    for n in list(tree.find_all(exp.DPipe)):  # older writers keep ||
        n.replace(exp.Add(this=n.this, expression=n.expression))
    for n in list(tree.find_all(exp.Length)):  # LEN leaves out trailing spaces, unless something follows them
        ended = exp.Add(this=exp.cast(n.this, "VARCHAR"), expression=exp.Literal.string("."))
        n.replace(exp.Paren(this=exp.Sub(this=exp.Length(this=ended), expression=exp.Literal.number(1))))
    for n in list(tree.find_all(exp.Sub)):
        days = [x for x in (n.this, n.expression) if isinstance(x, exp.Cast) and x.to.is_type("date")]
        if len(days) == 2:  # dates do not subtract
            n.replace(exp.Anonymous(this="DATEDIFF", expressions=[exp.var("DAY"), n.expression, n.this]))
    for n in list(tree.find_all(exp.Avg)):  # the average of whole numbers is cut to a whole number
        n.set("this", exp.cast(n.this, "FLOAT"))
    _sized(exp, tree)
    for n in list(tree.find_all(exp.Cast)):
        if n.to.is_type("varchar"):  # style 126 is ISO for every date type; a plain cast of DATETIME gives 'Oct 25 2026'
            size = exp.DataType.build("NVARCHAR(4000)", dialect="tsql")
            n.replace(exp.Anonymous(this="CONVERT", expressions=[size, n.this, exp.Literal.number(126)]))
        elif n.to.is_type("decimal") and not n.to.expressions:  # a bare DECIMAL has no places here
            n.set("to", exp.DataType.build("DECIMAL(38, 10)"))
    for n in list(tree.find_all(exp.Literal)):
        if n.is_string:  # text without N is read in the database's code page, and Korean comes back as ?
            n.replace(exp.National(this=n.this))


def _transpile(sql: str, dialect: str) -> str:
    try:
        import sqlglot
        from sqlglot import exp
        from sqlglot.errors import ErrorLevel
    except ImportError as e:
        raise CompileError(f"SQL dialect '{dialect}' needs the [sql] extra (sqlglot)") from e
    try:
        tree = sqlglot.parse_one(sql, read="postgres")
        if dialect == "oracle":
            _sized(exp, tree)
        elif dialect == "tsql":
            _tsql(exp, tree)
        return tree.sql(dialect=dialect, unsupported_level=ErrorLevel.RAISE, pretty=True)
    except sqlglot.errors.SqlglotError as e:
        raise CompileError(f"cannot translate to {dialect}: {e}") from e
    except ValueError as e:
        raise CompileError(f"unknown SQL dialect '{dialect}': {e}") from e
