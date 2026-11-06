"""Computed properties: a small expression language over one object's properties, compiled into every backend.

    net_price: {type: decimal, expr: "unit_price * quantity"}
    total:     {type: decimal, expr: "coalesce(sum(hasItem.net_price), 0)"}
    last_price: {type: decimal, expr: "latest(priceChanges.price)"}
    returned:  {type: integer, expr: "count(hasItem where item_status = 'RETURNED')"}
    bulk:       {type: boolean, expr: "quantity >= @bulk_quantity"}
    open_days:  {type: integer, expr: "days_between(opened_on, today())"}
    price_now:  {type: decimal, expr: "current(prices.amount)"}

`@name` reads a named parameter (see model.Parameter), written into each language as a literal. So is `today()`, read
when the query is compiled, which gives every backend the same day. `text_date(x, 'YYYYMMDD')` reads a date kept as
text, and `current(link.prop)` the value of the row whose period (see ObjectType.period) holds today; where several
rows of one thing are valid at once it gives the highest (`xspace periods` lists them).
Nulls follow one rule everywhere: a null operand gives null, division by zero gives null, and an `if` whose
condition is null gives null. Aggregates follow a path of links from the object and ignore null values, like SQL.
An aggregate's `where` is read on the last object of the path and keeps the rows where it is true, not null or false.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Any

from xgen_space.model import CURRENT_SUFFIX

AGGREGATES = ("sum", "avg", "min", "max", "count", "latest", "earliest", "current")
# name -> (least args, most args)
FUNCTIONS = {"coalesce": (1, 8), "if": (3, 3), "abs": (1, 1), "round": (1, 2), "floor": (1, 1), "ceil": (1, 1),
             "lower": (1, 1), "upper": (1, 1), "length": (1, 1), "concat": (2, 8), "year": (1, 1),
             "month": (1, 1), "day": (1, 1), "days_between": (2, 2), "today": (0, 0), "now": (0, 0),
             "text_date": (2, 2)}
DATE_FUNCTIONS = ("year", "month", "day", "days_between")
DATE_PARTS = ("YYYY", "MM", "DD", "HH", "MI", "SS")
TIME_PARTS = ("HH", "MI", "SS")
_PART = re.compile(r"YYYY|MM|DD|HH24|HH|MI|SS")
_SEPARATORS = "-/.: _|T"
_NUMBER = ("integer", "decimal")
_TOKEN = re.compile(r"\s*(?:(\d+\.\d+|\d+)|('(?:[^'\\]|\\.)*')|([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|!=|[-+*/()=<>,.@]))")


class ExprError(ValueError):
    """The expression cannot be read or does not fit the definition."""


@dataclass(frozen=True)
class Lit:
    value: Any
    type: str  # integer, decimal, string, boolean, null


@dataclass(frozen=True)
class Prop:
    name: str


@dataclass(frozen=True)
class Named:
    name: str  # a named parameter, read when the expression is prepared


@dataclass(frozen=True)
class Unary:
    op: str  # "-" or "not"
    arg: Any


@dataclass(frozen=True)
class Bin:
    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple


@dataclass(frozen=True)
class Agg:
    fn: str
    path: tuple[str, ...]
    prop: str = ""
    where: Any = None


def _tokens(text: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ExprError(f"cannot read the expression at '{text[pos:pos + 12]}'")
        num, s, name, op = m.groups()
        if num is not None:
            out.append(("num", num))
        elif s is not None:
            out.append(("str", re.sub(r"\\(.)", r"\1", s[1:-1])))
        elif name is not None:
            out.append(("name", name))
        else:
            out.append(("op", op))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text: str):
        self.toks = _tokens(text)
        self.i = 0

    def peek(self, kind: str = "", value: str = "") -> bool:
        if self.i >= len(self.toks):
            return False
        k, v = self.toks[self.i]
        return (not kind or k == kind) and (not value or v.lower() == value)

    def take(self, kind: str = "", value: str = "") -> str:
        if not self.peek(kind, value):
            got = self.toks[self.i][1] if self.i < len(self.toks) else "the end"
            raise ExprError(f"expected {value or kind} but found {got!r}")
        self.i += 1
        return self.toks[self.i - 1][1]

    def parse(self):
        node = self.or_()
        if self.i < len(self.toks):
            raise ExprError(f"unexpected {self.toks[self.i][1]!r}")
        return node

    def or_(self):
        node = self.and_()
        while self.peek("name", "or"):
            self.take()
            node = Bin("or", node, self.and_())
        return node

    def and_(self):
        node = self.not_()
        while self.peek("name", "and"):
            self.take()
            node = Bin("and", node, self.not_())
        return node

    def not_(self):
        if self.peek("name", "not"):
            self.take()
            return Unary("not", self.not_())
        return self.cmp()

    def cmp(self):
        node = self.add()
        for op in ("=", "!=", "<=", ">=", "<", ">"):
            if self.peek("op", op):
                self.take()
                return Bin(op, node, self.add())
        return node

    def add(self):
        node = self.mul()
        while self.peek("op", "+") or self.peek("op", "-"):
            op = self.take()
            node = Bin(op, node, self.mul())
        return node

    def mul(self):
        node = self.unary()
        while self.peek("op", "*") or self.peek("op", "/"):
            op = self.take()
            node = Bin(op, node, self.unary())
        return node

    def unary(self):
        if self.peek("op", "-"):
            self.take()
            return Unary("-", self.unary())
        return self.primary()

    def primary(self):
        if self.peek("num"):
            t = self.take()
            return Lit(Decimal(t), "decimal") if "." in t else Lit(int(t), "integer")
        if self.peek("str"):
            return Lit(self.take(), "string")
        if self.peek("op", "@"):
            self.take()
            return Named(self.take("name"))
        if self.peek("op", "("):
            self.take()
            node = self.or_()
            self.take("op", ")")
            return node
        name = self.take("name")
        low = name.lower()
        if low in ("true", "false"):
            return Lit(low == "true", "boolean")
        if low == "null":
            return Lit(None, "null")
        if self.peek("op", "("):
            self.take()
            if low in AGGREGATES:
                path = [self.take("name")]
                while self.peek("op", "."):
                    self.take()
                    path.append(self.take("name"))
                where = None
                if self.peek("name", "where"):
                    self.take()
                    where = self.or_()
                self.take("op", ")")
                if low == "count":
                    return Agg(low, tuple(path), where=where)
                if len(path) < 2:
                    raise ExprError(f"{low}() takes link.property, e.g. {low}(hasItem.quantity)")
                return Agg(low, tuple(path[:-1]), path[-1], where)
            if low not in FUNCTIONS:
                raise ExprError(f"unknown function '{name}'; functions are: "
                                f"{', '.join(sorted([*FUNCTIONS, *AGGREGATES]))}")
            args = []
            if not self.peek("op", ")"):
                args.append(self.or_())
                while self.peek("op", ","):
                    self.take()
                    args.append(self.or_())
            self.take("op", ")")
            least, most = FUNCTIONS[low]
            if not least <= len(args) <= most:
                raise ExprError(f"{low}() takes {least}{'' if least == most else f' to {most}'} arguments")
            if low == "round" and len(args) == 2 and not (isinstance(args[1], Lit) and args[1].type == "integer"):
                raise ExprError("round(x, n) takes a whole number of places")
            if low == "text_date":
                if not (isinstance(args[1], Lit) and args[1].type == "string"):
                    raise ExprError("text_date(x, 'YYYYMMDD') takes the layout as text")
                date_format(args[1].value)
            return Call(low, tuple(args))
        if self.peek("op", "."):
            raise ExprError(f"'{name}.' follows a link; wrap it in an aggregate such as sum({name}.x) or count({name})")
        return Prop(name)


def date_format(text: str) -> dict[str, tuple[int, int]]:
    """Where each part of a date stands in text of this layout, as {part: (start, width)}, in the layout's order.
    Parts are YYYY MM DD HH (or HH24) MI SS; a key read from two columns has the | between them."""
    parts: dict[str, tuple[int, int]] = {}
    i = pos = 0
    while i < len(text):
        m = _PART.match(text, i)
        if m:
            part = m.group()[:2] if m.group() == "HH24" else m.group()
            if part in parts:
                raise ExprError(f"date format '{text}' gives {part} twice")
            parts[part] = (pos, len(part))
            pos += len(part)
            i = m.end()
        elif text[i] in _SEPARATORS:
            pos += 1
            i += 1
        else:
            raise ExprError(f"cannot read date format '{text}' at '{text[i:]}'; "
                            f"parts are {' '.join(DATE_PARTS)}, separators {_SEPARATORS!r}")
    missing = [p for p in DATE_PARTS[:3] if p not in parts]
    if missing:
        raise ExprError(f"date format '{text}' gives no {', '.join(missing)}")
    return parts


def format_width(parts: dict[str, tuple[int, int]]) -> int:
    return max(start + width for start, width in parts.values())


def encode_text_date(iso: str, fmt: str) -> str:
    """An ISO date or datetime in a text layout, for writing one back to its column."""
    at = {"YYYY": iso[0:4], "MM": iso[5:7], "DD": iso[8:10], "HH": iso[11:13] or "00", "MI": iso[14:16] or "00",
          "SS": iso[17:19] or "00"}
    return _PART.sub(lambda m: at[m.group()[:2] if m.group() == "HH24" else m.group()], fmt)


def _iso_pieces(fmt: str) -> tuple[dict[str, tuple[int, int]], list[str]]:
    """The parts of a layout, and what to join for the ISO form: part names and fixed text."""
    parts = date_format(fmt)
    pieces = ["YYYY", "-", "MM", "-", "DD"]
    if set(parts) & set(TIME_PARTS):
        hour, minute, second = (x if x in parts else "00" for x in TIME_PARTS)
        pieces += ["T", hour, ":", minute, ":", second]
    return parts, pieces


def parse_expr(text: str):
    if not isinstance(text, str) or not text.strip():
        raise ExprError("an expression is required")
    return _Parser(text).parse()


def walk(node):
    """Every node read on the same object; an aggregate's where is read on another, so it stops there."""
    yield node
    if isinstance(node, Unary):
        yield from walk(node.arg)
    elif isinstance(node, Bin):
        yield from walk(node.left)
        yield from walk(node.right)
    elif isinstance(node, Call):
        for a in node.args:
            yield from walk(a)


@dataclass
class Step:
    link: str
    forward: bool
    type: str


@dataclass
class Typed:
    """The result of checking one computed property."""

    type: str
    issues: list[str] = field(default_factory=list)


def follow(onto, type_name: str, path: tuple[str, ...]) -> list[Step]:
    """Resolve a link path from a type: a link name goes forward, an inverse name goes back."""
    from xgen_space.check import is_a

    out, here = [], type_name
    for step in path:
        lk = onto.links.get(step)
        if lk is not None and is_a(onto, here, lk.source):
            out.append(Step(lk.name, True, lk.target))
            here = lk.target
            continue
        lk = onto.link_by_inverse(step)
        if lk is not None and is_a(onto, here, lk.target):
            out.append(Step(lk.name, False, lk.source))
            here = lk.source
            continue
        raise ExprError(f"{here} has no link '{step}'")
    return out


def resolve_agg(onto, type_name: str, node: Agg) -> tuple[list[Step], str]:
    """The link steps of an aggregate and the property it reads; count(link.prop) counts the values present."""
    from xgen_space.check import _find_prop

    if node.fn == "count" and not node.prop and len(node.path) > 1:
        try:
            return follow(onto, type_name, node.path), ""
        except ExprError:
            steps = follow(onto, type_name, node.path[:-1])
            if _find_prop(onto, steps[-1].type, node.path[-1]) is None:
                raise
            return steps, node.path[-1]
    return follow(onto, type_name, node.path), node.prop


_ISO = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?")


def _as_time(node: Lit, kind: str) -> Lit:
    from xgen_space.values import coerce, parse_datetime

    try:  # whole, seconds and all: "2026-10-20"^^xsd:dateTime is no dateTime, and a strict engine drops what meets it
        return Lit(coerce(parse_datetime(node.value), kind), kind)
    except ValueError:
        raise ExprError(f"{node.value!r} is not a {kind}") from None


def _named(onto, node: Named) -> Lit:
    p = onto.parameters.get(node.name)
    if p is None:
        raise ExprError(f"unknown parameter '@{node.name}'")
    return Lit(Decimal(str(p.value)) if p.type == "decimal" else p.value, p.type)


def _clock(onto) -> datetime:
    return (onto.clock or datetime.now)()


def _current(onto, type_name: str, node: Agg) -> Agg:
    """The aggregate current(link.prop) stands for: the highest of the values only a valid row has."""
    from xgen_space.check import _find_prop

    last = follow(onto, type_name, node.path)[-1].type
    if not onto.objects[last].period:
        raise ExprError(f"current() needs {last} to give its period (period: {{start: ..., end: ...}})")
    if _find_prop(onto, last, node.prop) is None:
        raise ExprError(f"{last} has no property '{node.prop}'")
    return replace(node, fn="max", prop=node.prop + CURRENT_SUFFIX)


def prepare(onto, type_name: str, node):
    """Give date-like text literals the type of what they meet: a date or datetime operand, a date function; and
    named parameters and the clock their value."""
    if isinstance(node, Named):
        return _named(onto, node)
    if isinstance(node, Agg) and node.fn == "current":
        return _current(onto, type_name, node)
    if isinstance(node, Unary):
        return Unary(node.op, prepare(onto, type_name, node.arg))
    if isinstance(node, Agg) and node.where is not None:
        last = resolve_agg(onto, type_name, node)[0][-1].type
        return replace(node, where=prepare(onto, last, node.where))
    if isinstance(node, Call) and node.fn == "today":
        return Lit(_clock(onto).date().isoformat(), "date")
    if isinstance(node, Call) and node.fn == "now":
        return Lit(_clock(onto).replace(microsecond=0).isoformat(), "datetime")
    if isinstance(node, Call):
        args = tuple(prepare(onto, type_name, a) for a in node.args)
        if node.fn in DATE_FUNCTIONS:
            args = tuple(_as_time(a, "date") if isinstance(a, Lit) and a.type == "string" else a for a in args)
        return Call(node.fn, args)
    if isinstance(node, Bin):
        left, right = prepare(onto, type_name, node.left), prepare(onto, type_name, node.right)
        if node.op in ("=", "!=", "<", "<=", ">", ">="):
            typer = _Typer(onto)
            for lit, other in ((left, right), (right, left)):
                if isinstance(lit, Lit) and lit.type == "string" and _ISO.fullmatch(str(lit.value)):
                    t = typer.type_of(other, type_name)
                    if t in ("date", "datetime"):
                        fixed = _as_time(lit, t)
                        left, right = (fixed, right) if lit is left else (left, fixed)
        return Bin(node.op, left, right)
    return node


def _arith(a: str, b: str) -> str:
    return "integer" if a == b == "integer" else "decimal"


class _Typer:
    def __init__(self, onto):
        self.onto = onto

    def prop_type(self, type_name: str, name: str, stack: tuple) -> str:
        from xgen_space.check import _find_prop

        p = _find_prop(self.onto, type_name, name)
        if p is None:
            raise ExprError(f"{type_name} has no property '{name}'")
        if p.expr and stack is not None:
            key = (type_name, name)
            if key in stack:
                raise ExprError("computed properties refer to each other in a loop: "
                                + " -> ".join(f"{t}.{n}" for t, n in (*stack, key)))
            self.type_of(prepare(self.onto, type_name, parse_expr(p.expr)), type_name, (*stack, key))
        return p.type

    def type_of(self, node, type_name: str, stack: tuple | None = None) -> str:
        """The type of an expression; `stack` (the computed properties being typed) also checks for loops."""
        if isinstance(node, Lit):
            return node.type
        if isinstance(node, Named):
            return _named(self.onto, node).type
        if isinstance(node, Prop):
            return self.prop_type(type_name, node.name, stack)
        if isinstance(node, Unary):
            t = self.type_of(node.arg, type_name, stack)
            if node.op == "-":
                self._num(t, "-")
                return t
            self._bool(t, "not")
            return "boolean"
        if isinstance(node, Bin):
            a, b = self.type_of(node.left, type_name, stack), self.type_of(node.right, type_name, stack)
            if node.op in ("+", "-", "*", "/"):
                self._num(a, node.op)
                self._num(b, node.op)
                return "decimal" if node.op == "/" else _arith(a if a != "null" else b, b if b != "null" else a)
            if node.op in ("and", "or"):
                self._bool(a, node.op)
                self._bool(b, node.op)
                return "boolean"
            if "null" not in (a, b) and not _comparable(a, b):
                raise ExprError(f"cannot compare {a} with {b}")
            return "boolean"
        if isinstance(node, Call):
            ts = [self.type_of(x, type_name, stack) for x in node.args]
            fn = node.fn
            if fn == "coalesce":
                known = [t for t in ts if t != "null"]
                if any(not _comparable(known[0], t) for t in known[1:]):
                    raise ExprError(f"coalesce() mixes {', '.join(ts)}")
                return known[0] if known else "null"
            if fn == "if":
                self._bool(ts[0], "if")
                if "null" not in (ts[1], ts[2]) and not _comparable(ts[1], ts[2]):
                    raise ExprError(f"if() gives {ts[1]} or {ts[2]}; give both branches one type")
                return ts[1] if ts[1] != "null" else ts[2]
            if fn in ("abs", "round", "floor", "ceil"):
                self._num(ts[0], fn)
                return "integer" if fn in ("floor", "ceil") or (fn == "round" and len(ts) == 1) else ts[0]
            if fn in ("lower", "upper", "length", "concat"):
                for t in ts:
                    if t not in ("string", "enum", "null"):
                        raise ExprError(f"{fn}() takes text, not {t}")
                return "integer" if fn == "length" else "string"
            if fn in ("today", "now"):
                return "date" if fn == "today" else "datetime"
            if fn == "text_date":
                if ts[0] not in ("string", "enum", "null"):
                    raise ExprError(f"text_date() takes text, not {ts[0]}")
                return "datetime" if set(date_format(node.args[1].value)) & set(TIME_PARTS) else "date"
            for t in ts:
                if t not in ("date", "datetime", "null"):
                    raise ExprError(f"{fn}() takes a date, not {t}")
            return "integer"
        if isinstance(node, Agg):
            if node.fn == "current":
                node = _current(self.onto, type_name, node)
            steps, prop = resolve_agg(self.onto, type_name, node)
            last = steps[-1].type
            if node.where is not None:
                self._bool(self.type_of(node.where, last, stack), "where")
            if node.fn == "count":
                if prop:
                    self.prop_type(last, prop, stack)
                return "integer"
            t = self.prop_type(last, prop, stack)
            if node.fn in ("sum", "avg"):
                self._num(t, node.fn)
                return "decimal" if node.fn == "avg" else t
            if node.fn in ("latest", "earliest"):
                series = self.onto.objects[last].series
                if not series:
                    raise ExprError(f"{node.fn}() needs {last} to be a series (series: {{time: ...}})")
            return t
        raise ExprError(f"cannot type {node!r}")

    @staticmethod
    def _num(t: str, op: str) -> None:
        if t not in (*_NUMBER, "null"):
            raise ExprError(f"'{op}' takes numbers, not {t}")

    @staticmethod
    def _bool(t: str, op: str) -> None:
        if t not in ("boolean", "null"):
            raise ExprError(f"'{op}' takes a true/false value, not {t}")


def _comparable(a: str, b: str) -> bool:
    groups = [{"string", "enum"}, {"integer", "decimal"}, {"date", "datetime"}, {"boolean"}]
    return a == b or any(a in g and b in g for g in groups)


def check_computed(onto, type_name: str, name: str) -> Typed:
    """Type one computed property against the definition: names, links, functions, loops and the declared type."""
    from xgen_space.check import _find_prop

    p = _find_prop(onto, type_name, name)
    try:
        got = _Typer(onto).type_of(prepare(onto, type_name, parse_expr(p.expr)), type_name, ((type_name, name),))
    except ExprError as e:
        return Typed("", [str(e)])
    if got != "null" and not _comparable(p.type, got) and not (p.type == "decimal" and got == "integer"):
        return Typed(got, [f"the expression gives {got}, the property is declared {p.type}"])
    return Typed(got)


def stored(prop) -> bool:
    """A property read from a column, as opposed to one computed from others."""
    return not prop.expr


def dependencies(onto, type_name: str, name: str, seen: set | None = None) -> set[tuple[str, str]]:
    """Every (type, stored property) a computed property reads, through other computed properties and links."""
    from xgen_space.check import _find_prop

    seen = set() if seen is None else seen
    p = _find_prop(onto, type_name, name)
    if p is None or (type_name, name) in seen:
        return set()
    seen.add((type_name, name))
    if not p.expr:
        return {(type_name, name)}
    return _reads(onto, type_name, parse_expr(p.expr), seen)


def _reads(onto, type_name: str, tree, seen: set) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for node in walk(tree):
        if isinstance(node, Prop):
            out |= dependencies(onto, type_name, node.name, seen)
        elif isinstance(node, Agg):
            steps, prop = resolve_agg(onto, type_name, node)
            last = steps[-1].type
            if prop:
                out |= dependencies(onto, last, prop, seen)
            if node.where is not None:  # a condition shapes the answer, so masking must see what it reads
                out |= _reads(onto, last, node.where, seen)
            series = onto.objects[last].series
            if node.fn in ("latest", "earliest") and series:
                out.add((last, series["time"]))
                out.add((last, onto.objects[last].key))
            if node.fn == "current":  # the row is chosen by its period
                for k in ("start", "end"):
                    if onto.objects[last].period.get(k):
                        out |= dependencies(onto, last, onto.objects[last].period[k], seen)
    return out


# --- rendering --------------------------------------------------------------------------------------------------

class Renderer:
    """Turns an expression into one language's text; the compiler supplies property access and aggregates."""

    language = ""

    def __init__(self, prop, aggregate):
        self.prop = prop            # (Prop node) -> text
        self.aggregate = aggregate  # (Agg node) -> text

    def render(self, node) -> str:
        if isinstance(node, Lit):
            return self.lit(node)
        if isinstance(node, Prop):
            return self.prop(node)
        if isinstance(node, Agg):
            return self.aggregate(node)
        if isinstance(node, Unary):
            arg = self.render(node.arg)
            return self.neg(arg) if node.op == "-" else self.not_(arg)
        if isinstance(node, Bin):
            a, b = self.render(node.left), self.render(node.right)
            if node.op == "/":
                return self.divide(a, b)
            return self.binary(node.op, a, b)
        if isinstance(node, Call):
            return self.call(node.fn, [self.render(a) for a in node.args], node.args)
        raise ExprError(f"cannot render {node!r}")

    def binary(self, op: str, a: str, b: str) -> str:
        raise NotImplementedError

    def not_(self, a: str) -> str:
        return f"(NOT {a})"

    def neg(self, a: str) -> str:
        return f"(-{a})"

    def lit(self, node: Lit) -> str:
        raise NotImplementedError

    def divide(self, a: str, b: str) -> str:
        raise NotImplementedError

    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        raise NotImplementedError


def _places(nodes: tuple) -> int:
    return int(nodes[1].value) if len(nodes) > 1 else 0


def day_number(y: str, m: str, d: str, floor: str = "FLOOR") -> str:
    """Julian day number from a date's parts. Each language here has this arithmetic, not all have date subtraction;
    all the divisions are of positive numbers, so a language that truncates agrees with one that does not."""
    k = f"{floor}((14 - {m}) / 12)"
    yy = f"({y} + 4800 - {k})"
    mm = f"({m} + 12 * {k} - 3)"
    return (f"({d} + {floor}((153 * {mm} + 2) / 5) + 365 * {yy} + {floor}({yy} / 4) - {floor}({yy} / 100) "
            f"+ {floor}({yy} / 400) - 32045)")


class SqlRenderer(Renderer):
    language = "sql"

    def __init__(self, prop, aggregate, native: str = "postgres"):
        super().__init__(prop, aggregate)
        self.native = native

    def lit(self, node: Lit) -> str:
        if node.type == "null":
            return "NULL"
        if node.type == "boolean":
            return "TRUE" if node.value else "FALSE"
        if node.type in ("string", "date", "datetime"):
            return "'" + str(node.value).replace("'", "''") + "'"
        return str(node.value)

    def binary(self, op: str, a: str, b: str) -> str:
        ops = {"=": "=", "!=": "<>", "and": "AND", "or": "OR"}
        return f"({a} {ops.get(op, op)} {b})"

    def divide(self, a: str, b: str) -> str:
        real = "REAL" if self.native == "sqlite" else "DOUBLE PRECISION"
        return f"(CAST({a} AS {real}) / NULLIF({b}, 0))"

    def _date(self, a: str) -> str:
        return f"SUBSTR(CAST({a} AS VARCHAR), 1, 10)"

    def _text_date(self, a: str, fmt: str) -> str:
        parts, pieces = _iso_pieces(fmt)
        text = f"CAST({a} AS VARCHAR)"

        def cut(part: str) -> str:
            start, width = parts[part]
            return f"SUBSTR({text}, {start + 1}, {width})"

        joined = " || ".join(cut(x) if x in parts else f"'{x}'" for x in pieces)
        return (f"(CASE WHEN LENGTH({text}) >= {format_width(parts)} AND {cut('MM')} BETWEEN '01' AND '12' "
                f"AND {cut('DD')} BETWEEN '01' AND '31' THEN {joined} END)")

    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        if fn == "coalesce":
            return f"COALESCE({', '.join(args)})"
        if fn == "if":
            return f"(CASE WHEN {args[0]} THEN {args[1]} WHEN NOT ({args[0]}) THEN {args[2]} END)"
        if fn == "abs":
            return f"ABS({args[0]})"
        if fn == "round":
            n = _places(nodes)
            return f"ROUND({args[0]}, {n})" if self.native == "sqlite" else f"ROUND(CAST({args[0]} AS NUMERIC), {n})"
        if fn in ("floor", "ceil"):
            if self.native == "sqlite":  # the math functions are a compile-time option of SQLite
                x = args[0]
                sign = "-" if fn == "floor" else "+"
                cmp = ">" if fn == "floor" else "<"
                return f"(CAST({x} AS INTEGER) {sign} (CAST({x} AS INTEGER) {cmp} {x}))"
            return f"{fn.upper()}({args[0]})"
        if fn in ("lower", "upper", "length"):
            return f"{fn.upper()}({args[0]})"
        if fn == "concat":  # the test is for Oracle, whose || reads a null as empty text
            return f"(CASE WHEN {' OR '.join(f'{a} IS NULL' for a in args)} THEN NULL ELSE {' || '.join(args)} END)"
        if fn in ("year", "month", "day"):
            start, n = {"year": (1, 4), "month": (6, 2), "day": (9, 2)}[fn]
            return f"CAST(SUBSTR(CAST({args[0]} AS VARCHAR), {start}, {n}) AS INTEGER)"
        if fn == "days_between":
            a, b = self._date(args[0]), self._date(args[1])
            if self.native == "sqlite":
                return f"CAST(julianday({b}) - julianday({a}) AS INTEGER)"
            return f"(CAST({b} AS DATE) - CAST({a} AS DATE))"
        if fn == "text_date":
            return self._text_date(args[0], nodes[1].value)
        raise ExprError(f"SQL has no rendering for {fn}()")


class PgqRenderer(SqlRenderer):
    """ISO SQL around and inside GRAPH_TABLE. A date is read with EXTRACT, not by its text: Oracle casts a date to text
    by session settings, so cutting the text could give a wrong number where EXTRACT stops with an error."""

    language = "sqlpgq"

    def lit(self, node: Lit) -> str:
        if node.type == "date":
            return f"DATE '{node.value}'"
        if node.type == "datetime":
            return f"TIMESTAMP '{str(node.value).replace('T', ' ')}'"
        return super().lit(node)

    @staticmethod
    def _part(a: str, fn: str) -> str:
        return f"EXTRACT({fn.upper()} FROM CAST({a} AS TIMESTAMP))"

    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        if fn in ("year", "month", "day"):
            return self._part(args[0], fn)
        if fn == "days_between":
            a, b = (day_number(*(self._part(x, p) for p in ("year", "month", "day"))) for x in args)
            return f"({b} - {a})"
        if fn == "round":  # a NUMERIC with no scale is a whole number on Oracle, which would round to 0 places first
            return f"ROUND(CAST({args[0]} AS DECIMAL(38, 18)), {_places(nodes)})"
        return super().call(fn, args, nodes)


class SparqlRenderer(Renderer):
    language = "sparql"
    NULL = "?__null"  # never bound: evaluating it is an error, which leaves the result unbound

    def lit(self, node: Lit) -> str:
        from xgen_space.rdf import literal

        if node.type == "null":
            return self.NULL
        if node.type == "boolean":
            return "true" if node.value else "false"
        if node.type in ("string", "date", "datetime"):
            return literal(node.value, node.type)
        return str(node.value)

    def binary(self, op: str, a: str, b: str) -> str:
        ops = {"and": "&&", "or": "||"}
        return f"({a} {ops.get(op, op)} {b})"

    def not_(self, a: str) -> str:
        return f"(!{a})"

    def divide(self, a: str, b: str) -> str:
        return f"IF({b} = 0, {self.NULL}, ({a} / {b}))"

    @staticmethod
    def _part(a: str, start: int, n: int) -> str:
        return f"<http://www.w3.org/2001/XMLSchema#integer>(SUBSTR(STR({a}), {start}, {n}))"

    def _day_number(self, a: str) -> str:
        return day_number(self._part(a, 1, 4), self._part(a, 6, 2), self._part(a, 9, 2))

    def _text_date(self, a: str, fmt: str) -> str:
        parts, pieces = _iso_pieces(fmt)
        text = f"STR({a})"

        def cut(part: str) -> str:
            start, width = parts[part]
            return f"SUBSTR({text}, {start + 1}, {width})"

        joined = ", ".join(cut(x) if x in parts else f'"{x}"' for x in pieces)
        kind = "dateTime" if "T" in pieces else "date"
        fits = (f'STRLEN({text}) >= {format_width(parts)} && {cut("MM")} >= "01" && {cut("MM")} <= "12" '
                f'&& {cut("DD")} >= "01" && {cut("DD")} <= "31"')
        return f"IF({fits}, STRDT(CONCAT({joined}), <http://www.w3.org/2001/XMLSchema#{kind}>), {self.NULL})"

    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        if fn == "coalesce":
            return f"COALESCE({', '.join(args)})"
        if fn == "if":
            return f"IF({args[0]}, {args[1]}, {args[2]})"
        if fn in ("abs", "floor", "ceil"):
            return f"{fn.upper()}({args[0]})"
        if fn == "round":
            n = _places(nodes)
            if not n:
                return f"ROUND({args[0]})"
            scale = 10 ** n
            return f"(ROUND({args[0]} * {scale}) / {scale})"
        if fn in ("lower", "upper"):
            return f"{'LCASE' if fn == 'lower' else 'UCASE'}({args[0]})"
        if fn == "length":
            return f"STRLEN({args[0]})"
        if fn == "concat":
            return f"CONCAT({', '.join(args)})"
        if fn in ("year", "month", "day"):
            start, n = {"year": (1, 4), "month": (6, 2), "day": (9, 2)}[fn]
            return self._part(args[0], start, n)
        if fn == "days_between":
            return f"({self._day_number(args[1])} - {self._day_number(args[0])})"
        if fn == "text_date":
            return self._text_date(args[0], nodes[1].value)
        raise ExprError(f"SPARQL has no rendering for {fn}()")


class CypherRenderer(Renderer):
    language = "cypher"

    def __init__(self, prop, aggregate, gql: bool = False):
        super().__init__(prop, aggregate)
        self.gql = gql

    def lit(self, node: Lit) -> str:
        if node.type == "null":
            return "null"
        if node.type == "boolean":
            return "true" if node.value else "false"
        if node.type in ("string", "date", "datetime"):
            return "'" + str(node.value).replace("\\", "\\\\").replace("'", "\\'") + "'"
        return str(node.value)

    def binary(self, op: str, a: str, b: str) -> str:
        ops = {"=": "=", "!=": "<>", "and": "AND", "or": "OR"}
        return f"({a} {ops.get(op, op)} {b})"

    def divide(self, a: str, b: str) -> str:
        num = f"CAST({a} AS FLOAT)" if self.gql else f"toFloat({a})"
        return f"(CASE WHEN {b} = 0 THEN null ELSE {num} / {b} END)"

    def _text_date(self, a: str, fmt: str) -> str:
        parts, pieces = _iso_pieces(fmt)
        text = f"toString({a})"

        def cut(part: str) -> str:
            start, width = parts[part]
            return f"substring({text}, {start}, {width})"

        joined = " + ".join(cut(x) if x in parts else f"'{x}'" for x in pieces)
        return (f"(CASE WHEN size({text}) >= {format_width(parts)} AND {cut('MM')} >= '01' AND {cut('MM')} <= '12' "
                f"AND {cut('DD')} >= '01' AND {cut('DD')} <= '31' THEN {joined} END)")

    @staticmethod
    def _gql_part(a: str, fn: str) -> str:
        """ISO GQL names no field of a date, so read it from the text; LEFT and RIGHT are its only substrings."""
        text = f"CAST({a} AS STRING)"
        if fn == "year":
            return f"CAST(LEFT({text}, 4) AS INT)"
        return f"CAST(RIGHT(LEFT({text}, {7 if fn == 'month' else 10}), 2) AS INT)"

    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        if self.gql and fn == "text_date":
            raise ExprError("ISO GQL has no portable form of text_date(); register a backend query for it")
        if self.gql and fn in ("year", "month", "day"):
            return self._gql_part(args[0], fn)
        if self.gql and fn == "days_between":
            a, b = (day_number(*(self._gql_part(x, p) for p in ("year", "month", "day"))) for x in args)
            return f"({b} - {a})"
        if fn == "coalesce":
            return f"coalesce({', '.join(args)})"
        if fn == "if":
            return f"(CASE WHEN {args[0]} THEN {args[1]} WHEN NOT ({args[0]}) THEN {args[2]} END)"
        if fn in ("abs", "floor", "ceil"):
            return f"{fn.upper() if self.gql else fn}({args[0]})"
        if fn == "round":
            n = _places(nodes)
            if self.gql:
                return f"ROUND({args[0]})" if not n else f"(ROUND({args[0]} * {10 ** n}) / {10 ** n})"
            return f"round({args[0]}, {n})" if n else f"round({args[0]})"
        if fn in ("lower", "upper"):
            if self.gql:
                return f"{fn.upper()}({args[0]})"
            return f"{'toLower' if fn == 'lower' else 'toUpper'}({args[0]})"
        if fn == "length":
            return f"CHAR_LENGTH({args[0]})" if self.gql else f"size({args[0]})"
        if fn == "concat":
            return "(" + (" || " if self.gql else " + ").join(args) + ")"
        if fn in ("year", "month", "day"):
            start, n = {"year": (0, 4), "month": (5, 2), "day": (8, 2)}[fn]
            return f"toInteger(substring(toString({args[0]}), {start}, {n}))"
        if fn == "days_between":
            a, b = (f"date(substring(toString({x}), 0, 10))" for x in args)
            return f"duration.inDays({a}, {b}).days"
        if fn == "text_date":
            return self._text_date(args[0], nodes[1].value)
        raise ExprError(f"Cypher has no rendering for {fn}()")


_NULL = "__.constant(null)"
_ANY_NULL = "__.select(values).unfold().is(P.eq(null))"
_PRED = {"=": "eq", "!=": "neq", "<": "lt", "<=": "lte", ">": "gt", ">=": "gte"}


class GremlinRenderer(Renderer):
    """Every expression is a traversal giving exactly one value, null included, whatever the traverser it starts from.

    Gremlin's own null rules are not SQL's: math() and asString() stop on a null, neq and without let one pass, and
    concat() leaves one out, so each of those is guarded here. Operands are held in a map under x0, x1, ... for math()
    and where() to read; only steps that read no alias follow, since a map key would win over a label of that name.
    """

    language = "gremlin"

    def __init__(self, prop, aggregate, literal):
        super().__init__(prop, aggregate)
        self.literal = literal  # (Lit node) -> the name of its binding

    def lit(self, node: Lit) -> str:
        return _NULL if node.type == "null" else f"__.constant({self.literal(node)})"

    @staticmethod
    def _hold(items: list[str]) -> str:
        keys = ", ".join(f"'x{i}'" for i in range(len(items)))
        return f"__.project({keys})" + "".join(f".by({t})" for t in items)

    def _strict(self, items: list[str], then: str) -> str:
        return f"{self._hold(items)}.choose({_ANY_NULL}, {_NULL}, {then})"

    @staticmethod
    def _unless_null(a: str, then: str) -> str:
        return f"{a}.choose(__.is(P.eq(null)), {_NULL}, {then})"

    def binary(self, op: str, a: str, b: str) -> str:
        if op in ("+", "-", "*"):
            return self._strict([a, b], f"__.math('x0 {op} x1')")
        if op in ("and", "or"):  # false decides an and, true an or, even beside a null
            decides, other = ("false", "true") if op == "and" else ("true", "false")
            either = f"__.select(values).unfold().is(P.eq({decides}))"
            return (f"{self._hold([a, b])}.choose({either}, __.constant({decides}), "
                    f"__.choose({_ANY_NULL}, {_NULL}, __.constant({other})))")
        test = f"__.where('x0', P.{_PRED[op]}('x1'))"
        return self._strict([a, b], f"__.choose({test}, __.constant(true), __.constant(false))")

    def not_(self, a: str) -> str:
        return (f"{a}.choose(__.is(P.eq(true)), __.constant(false), "
                f"__.choose(__.is(P.eq(false)), __.constant(true), {_NULL}))")

    def neg(self, a: str) -> str:
        return self._unless_null(a, "__.math('0 - _')")

    def divide(self, a: str, b: str) -> str:
        return self._strict([a, b], f"__.choose(__.select('x1').is(P.eq(0)), {_NULL}, __.math('x0 / x1'))")

    def _date_part(self, a: str, fn: str) -> str:
        start, end = {"year": (0, 4), "month": (5, 7), "day": (8, 10)}[fn]
        return f"{a}.asString().substring({start}, {end}).asNumber()"

    def call(self, fn: str, args: list[str], nodes: tuple) -> str:
        if fn == "coalesce":
            return "__.coalesce(" + ", ".join(f"{a}.is(P.neq(null))" for a in args) + f", {_NULL})"
        if fn == "if":
            c, a, b = args
            return f"__.choose({c}.is(P.eq(true)), {a}, __.choose({c}.is(P.eq(false)), {b}, {_NULL}))"
        if fn in ("abs", "floor", "ceil"):
            return self._unless_null(args[0], f"__.math('{fn}(_)')")
        if fn == "round":  # half away from zero, as SQL does; math() has no round
            scale = 10 ** _places(nodes)
            return self._unless_null(args[0], f"__.math('signum(_) * floor(abs(_) * {scale} + 0.5) / {scale}')")
        if fn in ("lower", "upper"):  # these two pass a null along
            return f"{args[0]}.to{fn.title()}()"
        if fn == "length":
            return f"{args[0]}.length()"
        if fn == "concat":
            return self._strict(args, "__.select(values).conjoin('')")
        if fn in ("year", "month", "day"):
            return self._unless_null(args[0], f"__{self._date_part('', fn)}")
        if fn == "days_between":  # dateDiff() changed its unit between releases, so count days by the calendar
            names = [f"{p}{i}" for i in (0, 1) for p in "ymd"]
            parts = [self._date_part(f"__.select('x{i}')", p) for i in (0, 1) for p in ("year", "month", "day")]
            days = f"{day_number('y1', 'm1', 'd1', 'floor')} - {day_number('y0', 'm0', 'd0', 'floor')}"
            read = (f"__.project({', '.join(repr(n) for n in names)})" + "".join(f".by({t})" for t in parts)
                    + f".math('{days}')")
            return self._strict(args, read)
        raise ExprError(f"Gremlin has no rendering for {fn}()")
