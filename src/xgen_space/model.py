"""Domain ontology metamodel: one definition, bound to source tables, read by every adapter."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TYPES = ("string", "integer", "decimal", "boolean", "date", "datetime", "enum")
CARDINALITIES = ("one_to_one", "one_to_many", "many_to_one", "many_to_many")
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ModelError(ValueError):
    """The ontology definition is inconsistent."""


KEY_SEP = "|"  # between the values of a key read from several columns
TEXT_SUFFIX = "__text"        # the stored text of a date kept as text
CURRENT_SUFFIX = "__current"  # a period row's value while the row is valid, else null
RAW_SUFFIX = "__raw"          # the stored value of a property that a transform changes on its way in
FUNCTION_RUNTIMES = ("expr", "decision", "query", "python", "http")
FUNCTION_STATUS = ("draft", "active", "retired")
STATUSES = ("draft", "active", "deprecated")  # an object, property or relation: being drafted, in use, going out of use


@dataclass
class Property:
    name: str
    type: str = "string"
    label: str = ""
    description: str = ""
    column: str = ""
    unit: str = ""
    values: list[str] = field(default_factory=list)
    required: bool = False
    cite: str = ""
    aligned: list[str] = field(default_factory=list)
    expr: str = ""   # a computed property: an expression over the object's other properties (see expr.py)
    mask: str = ""   # partial | full: hidden from every role that is not given it in clear
    labels: dict[str, str] = field(default_factory=dict)  # an allowed value's name (a code's name), by value
    columns: list[str] = field(default_factory=list)  # read from several columns: a composite key or reference
    format: str = ""  # a date stored as text in this layout, such as YYYYMMDD (see expr.date_format)
    transform: str = ""  # how the column becomes this value, over `value`: value / 100, value = 'Y'
    source_type: str = ""  # the column's own type where a transform changes it; the property's type otherwise
    status: str = "active"  # draft | active | deprecated (STATUSES)
    internal: bool = False  # made while loading, so not part of the definition: it is left out when written back

    @property
    def col(self) -> str:
        """The column to show; where SQL is written, `cols` holds each one."""
        return ", ".join(self.columns) if self.columns else self.column or self.name

    @property
    def cols(self) -> list[str]:
        return list(self.columns) or [self.column or self.name]

    @property
    def computed(self) -> bool:
        return bool(self.expr)


@dataclass
class Transition:
    source: str
    target: str
    action: str = ""
    guard: dict[str, Any] = field(default_factory=dict)  # {decision, expect} or {property}: what must hold to take it
    set: dict[str, Any] = field(default_factory=dict)    # what else it writes
    call: dict[str, Any] = field(default_factory=dict)   # an external request sent after the write
    after: dict[str, Any] = field(default_factory=dict)  # {days: 5 | "@name", since: property}: taken when that is over


@dataclass
class StateMachine:
    property: str
    states: list[str]
    initial: str = ""
    transitions: list[Transition] = field(default_factory=list)

    def allows(self, source: str | None, target: str) -> bool:
        return any(t.source == source and t.target == target for t in self.transitions)

    def find(self, source: str | None, target: str, action: str = "") -> Transition | None:
        """The transition an action takes: the one that names it, else the first between the two states."""
        found = [t for t in self.transitions if t.source == source and t.target == target]
        return next((t for t in found if t.action == action), found[0] if found else None)


@dataclass
class ObjectType:
    name: str
    key: str
    properties: dict[str, Property]
    label: str = ""
    description: str = ""
    table: str = ""
    title: str = ""
    parent: str = ""
    implements: list[str] = field(default_factory=list)
    states: StateMachine | None = None
    cite: str = ""
    aligned: list[str] = field(default_factory=list)
    series: dict[str, str] = field(default_factory=dict)  # observations over time: {time: property, of: link}
    period: dict[str, Any] = field(default_factory=dict)  # rows valid for a time: {start, end, of: link, end_exclusive}
    view: dict[str, Any] = field(default_factory=dict)  # defined by a query, not a table: {name, query} (decide.views)
    status: str = "active"  # draft | active | deprecated (STATUSES)
    area: str = ""  # the area this type is filed under (Ontology.areas); none while it is unclassified

    @property
    def abstract(self) -> bool:
        return not self.table

    @property
    def view_name(self) -> str:
        return str(self.view.get("name") or re.sub(r"(?<!^)(?=[A-Z])", "_", self.name).lower() + "_view")

    def prop(self, name: str) -> Property:
        try:
            return self.properties[name]
        except KeyError:
            raise ModelError(f"{self.name} has no property '{name}'") from None

    @property
    def key_prop(self) -> Property:
        return self.prop(self.key)


@dataclass
class Via:
    table: str
    source_column: str
    target_column: str


@dataclass
class LinkType:
    name: str
    source: str
    target: str
    cardinality: str = "many_to_many"
    on: tuple[str, str] | None = None
    via: Via | None = None
    label: str = ""
    description: str = ""
    inverse: str = ""
    transitive: bool = False
    symmetric: bool = False
    required: bool = False
    cite: str = ""
    aligned: list[str] = field(default_factory=list)
    status: str = "active"  # draft | active | deprecated (STATUSES)

    @property
    def bound(self) -> bool:
        return self.on is not None or self.via is not None


@dataclass
class Interface:
    name: str
    properties: list[str]
    label: str = ""


@dataclass
class Area:
    """The level above the object types: what a business sorts its concepts under (order, product, payment)."""

    name: str
    label: str = ""
    description: str = ""
    cite: str = ""
    aligned: list[str] = field(default_factory=list)
    status: str = "active"  # draft | active | deprecated (STATUSES)


@dataclass
class Parameter:
    """A value rules read by name, so a customer module changes it in one place."""

    name: str
    value: Any
    type: str = "integer"
    label: str = ""
    unit: str = ""
    description: str = ""
    cite: str = ""
    min: float | None = None
    max: float | None = None


@dataclass
class DecisionInput:
    name: str
    type: str
    source: dict[str, Any]


@dataclass
class DecisionRule:
    when: dict[str, str]
    then: dict[str, Any]
    id: str = ""
    note: str = ""
    cite: str = ""
    priority: int | None = None  # hit policy priority: the matching rule with the lowest number decides
    source: str = ""  # where the rule came from: two sources that disagree are a conflict (see decide.conflicts)
    overruled_by: dict[str, str] = field(default_factory=dict, repr=False, compare=False)  # rule id -> conflict, by a pick


@dataclass
class DecisionTable:
    name: str
    inputs: dict[str, DecisionInput]
    outputs: dict[str, str]
    rules: list[DecisionRule]
    target: str = ""
    label: str = ""
    hit_policy: str = "first"
    cite: str = ""
    parameters: dict[str, Parameter] = field(default_factory=dict, repr=False, compare=False)  # the ontology's

    @property
    def named(self) -> dict[str, Any]:
        return {p.name: p.value for p in self.parameters.values()}


@dataclass
class Criterion:
    decision: str = ""
    expect: dict[str, Any] = field(default_factory=dict)
    states: list[str] = field(default_factory=list)
    function: str = ""


@dataclass
class ActionType:
    name: str
    target: str
    label: str = ""
    parameters: dict[str, str] = field(default_factory=dict)
    criteria: list[Criterion] = field(default_factory=list)
    set: dict[str, Any] = field(default_factory=dict)
    transition_to: str = ""
    approval: bool = True
    cite: str = ""
    call: dict[str, Any] = field(default_factory=dict)  # an external request sent after the change is written
    undo: dict[str, Any] = field(default_factory=dict)  # the request that reverses `call`, for a rollback
    auto_within: list[dict[str, Any]] = field(default_factory=list)  # inside all of these, no person need approve
    auto_agents: bool = False  # an agent's request may run on its own too; a person's may by default


@dataclass
class Role:
    name: str
    label: str = ""
    read: list[str] = field(default_factory=list)
    row_filters: dict[str, dict] = field(default_factory=dict)
    run: list[str] = field(default_factory=list)
    request: list[str] = field(default_factory=list)
    execute: list[str] = field(default_factory=list)
    mask: dict[str, str] = field(default_factory=dict)  # "Type.prop" -> partial | full, on top of the properties' own
    unmask: list[str] = field(default_factory=list)     # "Type.prop" or "Type.*" this role sees in clear
    scope: dict[str, Any] = field(default_factory=dict)  # {attribute: seller_id, types: {Type: property | {via, property}}}
    scoped: dict[str, dict] = field(default_factory=dict)  # made from scope: the row filter each type gets
    closed: set[str] = field(default_factory=set)  # decisions that read a scoped row with no regard for the scope
    documents: list[str] | None = None  # document names, file paths or patterns (정책/*) this role reads; None reads every one

    def can_read(self, type_name: str) -> bool:
        return "*" in self.read or type_name in self.read

    def can_read_document(self, name: str, path: str = "") -> bool:
        from fnmatch import fnmatchcase

        return self.documents is None or any(fnmatchcase(str(name), p) or (path and fnmatchcase(path, p)) for p in self.documents)

    def can(self, verb: str, name: str) -> bool:
        if verb == "run" and name in self.closed:  # roles.decide_in_scope asks them inside the scope
            return False
        names = getattr(self, verb)
        return "*" in names or name in names


@dataclass
class IdentityMember:
    type: str
    fields: dict[str, str]  # match field -> property of the member type


@dataclass
class IdentityRule:
    id: str
    match: list[str]
    normalize: dict[str, str] = field(default_factory=dict)  # field -> lower | digits | trim | none


@dataclass
class Identity:
    """One real-world thing that several systems keep under their own keys; resolved into a crosswalk."""

    name: str
    members: dict[str, IdentityMember]
    rules: list[IdentityRule]
    table: str = ""
    label: str = ""

    @property
    def key(self) -> str:
        return "identity_id"

    def member_table(self, member: str) -> str:
        return f"{self.table}_{member.lower()}"

    def link_name(self, member: str) -> str:
        return f"{self.name[:1].lower()}{self.name[1:]}{member}"


@dataclass
class RegisteredQuery:
    name: str
    query: dict
    label: str = ""
    description: str = ""
    params: dict[str, str] = field(default_factory=dict)
    example: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictAnswer:
    source: str
    says: dict[str, Any]
    rule: str = ""
    cite: str = ""


@dataclass
class SourceConflict:
    """One input answered differently by two sources, for a person to pick (see decide.conflicts)."""

    id: str
    decision: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    answers: list[ConflictAnswer] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)  # short for answers: the rules that disagree
    label: str = ""
    picked: str = ""  # the source that stands; empty while the conflict is open
    by: str = ""
    at: str = ""
    reason: str = ""
    found: bool = False  # read off the rules, with no record in a module yet

    @property
    def open(self) -> bool:
        return not self.picked


@dataclass
class Metric:
    """A named number with what it means (see decide.metrics)."""

    name: str
    formula: dict[str, Any]
    owner: str = ""
    time: dict[str, Any] = field(default_factory=dict)         # {property: alias.prop, basis: in words}
    denominator: dict[str, Any] = field(default_factory=dict)  # left out for a plain total
    label: str = ""
    description: str = ""
    unit: str = ""
    scale: float = 1
    cite: str = ""
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class Function:
    """Logic with a contract: what it takes, what it gives, who owns it, which version runs (see functions.py)."""

    name: str
    runtime: str = "expr"
    target: str = ""  # the object type it is run on; none for one that takes only inputs
    label: str = ""
    description: str = ""
    version: str = "1.0.0"
    owner: str = ""
    status: str = "active"
    inputs: dict[str, Any] = field(default_factory=dict)  # as an action's parameters
    outputs: dict[str, str] = field(default_factory=dict)  # name -> type
    expr: str = ""
    decision: str = ""
    query: str = ""
    entry: str = ""  # the name a deployment registered a callable under; a module never names code itself
    call: dict[str, Any] = field(default_factory=dict)
    depends: list[str] = field(default_factory=list)  # what it needs beyond the definition: a model, a service
    cite: str = ""


@dataclass
class Question:
    id: str
    text: str
    expect: Any
    query: str = ""
    decision: str = ""
    key: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Ontology:
    name: str
    namespace: str
    objects: dict[str, ObjectType]
    links: dict[str, LinkType] = field(default_factory=dict)
    version: str = "0.1.0"
    label: str = ""
    interfaces: dict[str, Interface] = field(default_factory=dict)
    decisions: dict[str, DecisionTable] = field(default_factory=dict)
    actions: dict[str, ActionType] = field(default_factory=dict)
    roles: dict[str, Role] = field(default_factory=dict)
    queries: dict[str, RegisteredQuery] = field(default_factory=dict)
    questions: list[Question] = field(default_factory=list)
    exclusive: list[tuple[str, str]] = field(default_factory=list)
    identities: dict[str, Identity] = field(default_factory=dict)
    parameters: dict[str, Parameter] = field(default_factory=dict)
    metrics: dict[str, Metric] = field(default_factory=dict)
    conflicts: dict[str, SourceConflict] = field(default_factory=dict)  # what is recorded; rules can show more
    functions: dict[str, Function] = field(default_factory=dict)
    areas: dict[str, Area] = field(default_factory=dict)  # names of their own: an area may be called as a type is
    clock: Any = field(default=None, repr=False, compare=False)  # what today() and now() ask; the system clock if unset

    def obj(self, name: str) -> ObjectType:
        try:
            return self.objects[name]
        except KeyError:
            raise ModelError(f"unknown object type '{name}'") from None

    def link(self, name: str) -> LinkType:
        try:
            return self.links[name]
        except KeyError:
            raise ModelError(f"unknown link '{name}'") from None

    def crosswalks(self) -> set[str]:
        """The tables resolving an identity writes: absent until then, which is no fault of the source."""
        return {i.table for i in self.identities.values()} | {
            i.member_table(m) for i in self.identities.values() for m in i.members}

    def link_by_inverse(self, name: str) -> LinkType | None:
        return next((lk for lk in self.links.values() if lk.inverse == name), None)

    def property_type(self, name: str) -> str | None:
        for o in self.objects.values():
            if name in o.properties:
                return o.properties[name].type
        return None

    def validate(self) -> list[str]:
        from xgen_space.validate import validate_ontology

        return validate_ontology(self)

    def findings(self) -> list:
        """What the decision tables say twice or leave open: for a person to look at, nothing that stops them."""
        from xgen_space.decide.checks import decision_findings

        return decision_findings(self)

    def source_conflicts(self) -> list[SourceConflict]:
        """Where two sources answer one input differently, recorded or found in the rules."""
        from xgen_space.decide.conflicts import source_conflicts

        return source_conflicts(self)

    def check(self) -> Ontology:
        issues = self.validate()
        if issues:
            raise ModelError("; ".join(issues))
        return self

    @classmethod
    def from_dict(cls, d: dict) -> Ontology:
        return _from_dict(d)

    def to_dict(self) -> dict:
        return _to_dict(self)

    @classmethod
    def load(cls, path: str | Path) -> Ontology:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() in (".yaml", ".yml"):
            try:
                import yaml
            except ImportError as e:
                raise ImportError("YAML ontologies need the [yaml] extra (PyYAML)") from e
            return cls.from_dict(yaml.safe_load(text))
        return cls.from_dict(json.loads(text))

    def dump(self, path: str | Path) -> None:
        p = Path(path)
        if p.suffix.lower() in (".yaml", ".yml"):
            import yaml

            p.write_text(yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")
        else:
            p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def valid_name(name: str) -> bool:
    return bool(_NAME.match(name or ""))


def _prop(name: str, d: Any) -> Property:
    if isinstance(d, str):
        d = {"type": d}
    values = d.get("values", [])
    labels = {str(k): str(v) for k, v in (d.get("labels") or {}).items()}
    if isinstance(values, dict):  # values: {code: name} gives the values and their names at once
        labels = {**{str(k): str(v) for k, v in values.items() if v not in (None, "")}, **labels}
        values = [str(k) for k in values]
    column, columns = d.get("column", ""), list(d.get("columns") or [])
    if isinstance(column, list):
        column, columns = "", list(column)
    return Property(name=name, type=d.get("type", "string"), label=d.get("label", ""),
                    description=d.get("description", ""), column=column, unit=d.get("unit", ""),
                    values=list(values), required=bool(d.get("required", False)),
                    cite=d.get("cite", ""), aligned=list(d.get("aligned", [])), expr=str(d.get("expr", "") or ""),
                    mask=str(d.get("mask", "") or ""), labels=labels, columns=columns,
                    format=str(d.get("format", "") or ""), transform=str(d.get("transform", "") or ""),
                    source_type=str(d.get("source_type", "") or ""), status=str(d.get("status") or "active"))


def _states(d: dict | None) -> StateMachine | None:
    if not d:
        return None
    return StateMachine(property=d["property"], states=list(d.get("states", [])), initial=d.get("initial", ""),
                        transitions=[Transition(t["from"], t["to"], t.get("action", ""), dict(t.get("guard") or {}),
                                                dict(t.get("set") or {}), dict(t.get("call") or {}),
                                                dict(t.get("after") or {}))
                                     for t in d.get("transitions", [])])


def _text_dates(props: dict[str, Property]) -> None:
    """A date kept as text reads as a date everywhere: its text becomes a property of its own and the date is computed
    from it, so filters, ordering and decisions see one date form in every language."""
    for p in list(props.values()):
        if p.format and p.type in ("date", "datetime") and not p.expr:
            raw = Property(p.name + TEXT_SUFFIX, "string", description=f"{p.name} as stored", required=p.required,
                           column="" if p.columns else p.column or p.name, columns=list(p.columns), mask=p.mask,
                           internal=True)
            props[raw.name] = raw
            p.expr = f"text_date({raw.name}, '{p.format}')"


def _over(transform: str, name: str) -> str:
    """A transform with `value` read as the stored property; text in quotes stays as it is."""
    parts = re.split(r"('[^']*')", transform)
    return "".join(p if i % 2 else re.sub(r"\bvalue\b", name, p) for i, p in enumerate(parts))


def _transforms(props: dict[str, Property]) -> None:
    """A column that needs changing on its way in reads like a computed property over what is stored, so every language
    sees the changed value and a graph holds the stored one."""
    for p in list(props.values()):
        if p.transform and not p.expr and not p.columns:
            raw = Property(p.name + RAW_SUFFIX, p.source_type or p.type, description=f"{p.name} as stored",
                           required=p.required, column=p.column or p.name, mask=p.mask, internal=True)
            props[raw.name] = raw
            p.expr = _over(p.transform, raw.name)


def _object(name: str, d: dict) -> ObjectType:
    source = d.get("source") or {}
    props = {k: _prop(k, v) for k, v in d.get("properties", {}).items()}
    _text_dates(props)
    _transforms(props)
    series = dict(d.get("series") or {})
    if series.get("time", "") + TEXT_SUFFIX in props:  # a graph holds the stored text, which sorts the same
        series["time"] += TEXT_SUFFIX
    t = ObjectType(name=name, key=d["key"], properties=props,
                      label=d.get("label", ""), description=d.get("description", ""),
                      table=source.get("table", d.get("table", "")), title=d.get("title", ""),
                      parent=d.get("parent", ""), implements=list(d.get("implements", [])),
                      states=_states(d.get("states")), cite=d.get("cite", ""), aligned=list(d.get("aligned", [])),
                      series=series, period=dict(d.get("period") or {}), view=dict(d.get("view") or {}),
                      status=str(d.get("status") or "active"), area=str(d.get("area") or ""))
    if t.view and not t.table:  # bound to the view it makes, as to a table
        t.table = t.view_name
    return t


def _link(name: str, d: dict) -> LinkType:
    on = d.get("on", d.get(True))
    if isinstance(on, dict):
        if len(on) != 1:
            raise ModelError(f"link {name}: 'on' takes exactly one source: target pair")
        on = next(iter(on.items()))
    via = d.get("via")
    return LinkType(name=name, source=d["from"], target=d["to"], cardinality=d.get("cardinality", "many_to_many"),
                    on=tuple(on) if on else None,
                    via=Via(via["table"], via["source"], via["target"]) if via else None,
                    label=d.get("label", ""), description=d.get("description", ""), inverse=d.get("inverse", ""),
                    transitive=bool(d.get("transitive", False)), symmetric=bool(d.get("symmetric", False)),
                    required=bool(d.get("required", False)), cite=d.get("cite", ""),
                    aligned=list(d.get("aligned", [])), status=str(d.get("status") or "active"))


def _decision(name: str, d: dict) -> DecisionTable:
    inputs = {}
    for k, v in d.get("inputs", {}).items():
        v = dict(v)
        inputs[k] = DecisionInput(name=k, type=v.pop("type", "string"), source=v)
    rules = [DecisionRule(when={k: str(x) for k, x in (r.get("when") or {}).items()}, then=dict(r.get("then") or {}),
                          id=r.get("id", f"r{i + 1}"), note=r.get("note", ""), cite=r.get("cite", ""),
                          priority=r.get("priority"), source=str(r.get("source", "") or ""))
             for i, r in enumerate(d.get("rules", []))]
    return DecisionTable(name=name, inputs=inputs, outputs=dict(d.get("outputs", {})), rules=rules,
                         target=d.get("target", ""), label=d.get("label", ""),
                         hit_policy=d.get("hit_policy", "first"), cite=d.get("cite", ""))


def _parameter(name: str, d: Any) -> Parameter:
    if not isinstance(d, dict):  # a bare value: return_window_days: 14
        d = {"value": d}
    value = d.get("value")
    found = {bool: "boolean", int: "integer", float: "decimal", str: "string"}.get(type(value), "integer")
    return Parameter(name, value, d.get("type", found), d.get("label", ""), d.get("unit", ""), d.get("description", ""),
                     d.get("cite", ""), d.get("min"), d.get("max"))


def _area(name: str, d: dict | None) -> Area:
    d = d or {}  # a name alone is an area: Order:
    return Area(name, d.get("label", ""), d.get("description", ""), d.get("cite", ""), list(d.get("aligned", [])),
                str(d.get("status") or "active"))


def _conflict(name: str, d: dict) -> SourceConflict:
    answers = [ConflictAnswer(str(a.get("source", "")), dict(a.get("says") or {}), str(a.get("rule", "")),
                              str(a.get("cite", ""))) for a in d.get("answers") or []]
    return SourceConflict(name, d.get("decision", ""), dict(d.get("input") or {}), answers,
                          [str(r) for r in d.get("rules") or []], d.get("label", ""), str(d.get("picked", "") or ""),
                          str(d.get("by", "") or ""), str(d.get("at", "") or ""), str(d.get("reason", "") or ""))


def _settle_conflicts(onto: Ontology) -> None:
    """Fill in the answers of conflicts named by their rules, and give each pick its effect on the rules."""
    for c in onto.conflicts.values():
        table = onto.decisions.get(c.decision)
        rules = {r.id: r for r in table.rules} if table else {}
        for name in c.rules:
            if name in rules:
                r = rules[name]
                says = {k: table.named.get(v[1:], v) if isinstance(v, str) and v.startswith("@") else v
                        for k, v in r.then.items()}
                c.answers.append(ConflictAnswer(r.source, says, r.id, r.cite))
        if c.picked:
            kept = [a.rule for a in c.answers if a.source == c.picked and a.rule in rules]
            for a in c.answers:
                if a.source != c.picked and a.rule in rules:
                    rules[a.rule].overruled_by.update({k: c.id for k in kept})


def _metric(name: str, d: dict) -> Metric:
    return Metric(name, dict(d.get("formula") or {}), d.get("owner", ""), dict(d.get("time") or {}),
                  dict(d.get("denominator") or {}), d.get("label", ""), d.get("description", ""), d.get("unit", ""),
                  d.get("scale", 1), d.get("cite", ""), dict(d.get("params") or {}))


def _action(name: str, d: dict) -> ActionType:
    crit = [Criterion(decision=c.get("decision", ""), expect=dict(c.get("expect", {})),
                      states=list(c.get("states", [])), function=c.get("function", "")) for c in d.get("criteria", [])]
    approval = d.get("approval", True)
    limits = approval if isinstance(approval, dict) else {}  # {auto_within: [...], agents: true}: a person past the limits
    return ActionType(name=name, target=d["target"], label=d.get("label", ""), parameters=dict(d.get("parameters", {})),
                      criteria=crit, set=dict(d.get("set", {})), transition_to=d.get("transition_to", ""),
                      approval=True if limits else bool(approval), cite=d.get("cite", ""), call=dict(d.get("call") or {}),
                      undo=dict(d.get("undo") or {}), auto_within=[dict(x) for x in limits.get("auto_within") or []],
                      auto_agents=bool(limits.get("agents", False)))


def _function(name: str, d: dict) -> Function:
    return Function(name, str(d.get("runtime", "expr")), d.get("target", ""), d.get("label", ""), d.get("description", ""),
                    str(d.get("version", "1.0.0")), d.get("owner", ""), str(d.get("status", "active")),
                    dict(d.get("inputs") or {}), {str(k): str(v) for k, v in (d.get("outputs") or {}).items()},
                    str(d.get("expr", "") or ""), d.get("decision", ""), d.get("query", ""), d.get("entry", ""),
                    dict(d.get("call") or {}), [str(x) for x in d.get("depends") or []], d.get("cite", ""))


def _role(name: str, d: dict) -> Role:
    mask = d.get("mask") or {}
    if isinstance(mask, list):
        mask = {m: "partial" for m in mask}
    return Role(name=name, label=d.get("label", ""), read=list(d.get("read", [])),
                row_filters=dict(d.get("row_filters", {})), run=list(d.get("run", [])),
                request=list(d.get("request", [])), execute=list(d.get("execute", [])),
                mask={str(k): str(v) for k, v in mask.items()}, unmask=list(d.get("unmask", [])),
                scope=dict(d.get("scope") or {}),
                documents=None if d.get("documents") is None else
                [str(x) for x in ([d["documents"]] if isinstance(d["documents"], str) else d["documents"])])


def _identity(name: str, d: dict) -> Identity:
    members = {t: IdentityMember(t, {str(f): str(p) for f, p in (spec or {}).items()})
               for t, spec in (d.get("members") or {}).items()}
    rules = []
    for i, r in enumerate(d.get("rules") or []):
        norm = r.get("normalize") or {}
        match = [str(x) for x in (r.get("match") or [])]
        if isinstance(norm, str):
            norm = {f: norm for f in match}
        rules.append(IdentityRule(str(r.get("id") or f"rule{i + 1}"), match, {str(k): str(v) for k, v in norm.items()}))
    table = d.get("table") or re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower() + "_identity"
    return Identity(name, members, rules, table, d.get("label", ""))


def expand_identities(objects: dict[str, ObjectType], links: dict[str, LinkType],
                      identities: dict[str, Identity]) -> None:
    """Each identity becomes an object over its crosswalk table and one link to every member type."""
    for ident in identities.values():
        if ident.name in objects:
            continue
        objects[ident.name] = ObjectType(
            ident.name, ident.key, {ident.key: Property(ident.key, "string", "통합 번호", required=True),
                                    "members": Property("members", "integer", "묶인 기록 수")},
            label=ident.label or ident.name, table=ident.table, title=ident.key)
        for member in ident.members:
            name = ident.link_name(member)
            if name not in links:
                links[name] = LinkType(name, ident.name, member, "one_to_many",
                                       via=Via(ident.member_table(member), ident.key, "member_key"),
                                       label=f"{ident.label or ident.name} 구성원")


def _scope_filter(onto: Ontology, where: Any, attribute: str, who: Any = None) -> dict | None:
    """The row filter of one scoped type: its own property, or one reached over links. It compares with the signed-in
    attribute, or with `who` when a value is given."""
    who = {"principal": attribute} if who is None else who
    if isinstance(where, str):
        return {"eq": [f"$self.{where}", who]}
    if not isinstance(where, dict) or not where.get("property"):
        return None
    nodes: dict[str, str] = {}
    edges, prev = [], "$self"
    for i, step in enumerate(where.get("via") or []):
        lk = onto.links.get(step) or onto.link_by_inverse(step)
        if lk is None:
            return None
        nodes[f"s{i}"] = lk.target if lk.name == step else lk.source
        edges.append([prev, step, f"s{i}"])
        prev = f"s{i}"
    if not nodes:
        return {"eq": [f"$self.{where['property']}", who]}
    return {"exists": {"match": nodes, "edges": edges, "where": {"eq": [f"{prev}.{where['property']}", who]}}}


def _role_scopes(onto: Ontology) -> None:
    """A role's scope as a row filter on each type it names and their subtypes, so a read goes the way row_filters do.
    A decision on such a type reads its row outside any query, so the role loses it until it is asked in scope."""
    from xgen_space.check import is_a

    for r in onto.roles.values():
        for name, where in (r.scope.get("types") or {}).items():
            spec = _scope_filter(onto, where, str(r.scope.get("attribute", "")))
            if spec is not None and name in onto.objects:
                r.scoped.update({t: spec for t in onto.objects if t not in r.scoped and is_a(onto, t, name)})
        r.closed = {d.name for d in onto.decisions.values() if d.target in r.scoped}


def _valid_now(t: ObjectType) -> str:
    """The expression that says a period row is valid; an empty end stays open."""
    def clock(name: str) -> str:
        p = t.properties.get(name)
        return "now()" if p is not None and p.type == "datetime" else "today()"

    start, end = t.period.get("start", ""), t.period.get("end", "")
    text = f"{start} <= {clock(start)}"
    if end:
        text += f" and coalesce({clock(end)} {'<' if t.period.get('end_exclusive') else '<='} {end}, true)"
    return text


def _period_values(onto: Ontology) -> None:
    """For each current(link.prop), a value on the period type that is null outside the row's period: the row valid
    now is then the maximum of them, which every language can already say."""
    from xgen_space.check import _find_prop
    from xgen_space.expr import Agg, ExprError, follow, parse_expr, walk

    for t in list(onto.objects.values()):
        for p in list(t.properties.values()):
            if "current(" not in p.expr:
                continue
            try:
                found = [n for n in walk(parse_expr(p.expr)) if isinstance(n, Agg) and n.fn == "current"]
                for node in found:
                    last = onto.objects[follow(onto, t.name, node.path)[-1].type]
                    name = node.prop + CURRENT_SUFFIX
                    src = _find_prop(onto, last.name, node.prop)
                    if src is not None and last.period and name not in last.properties:
                        last.properties[name] = Property(name, src.type, internal=True,
                                                         expr=f"if({_valid_now(last)}, {src.name}, null)")
            except ExprError:
                continue  # validate names what is wrong with the expression


def _from_dict(d: dict) -> Ontology:
    objects = {k: _object(k, v) for k, v in d.get("objects", {}).items()}
    links = {k: _link(k, v) for k, v in d.get("links", {}).items()}
    identities = {k: _identity(k, v) for k, v in (d.get("identities") or {}).items()}
    expand_identities(objects, links, identities)
    parameters = {k: _parameter(k, v) for k, v in (d.get("parameters") or {}).items()}
    decisions = {k: _decision(k, v) for k, v in d.get("decisions", {}).items()}
    for dt in decisions.values():
        dt.parameters = parameters
    onto = Ontology(
        name=d.get("ontology") or d.get("name") or "ontology",
        namespace=d["namespace"],
        version=str(d.get("version", "0.1.0")),
        label=d.get("label", ""),
        objects=objects,
        links=links,
        interfaces={k: Interface(k, list(v.get("properties", [])), v.get("label", ""))
                    for k, v in d.get("interfaces", {}).items()},
        decisions=decisions,
        actions={k: _action(k, v) for k, v in d.get("actions", {}).items()},
        roles={k: _role(k, v) for k, v in d.get("roles", {}).items()},
        queries={k: RegisteredQuery(k, v["query"], v.get("label", ""), v.get("description", ""),
                                    dict(v.get("params", {})), dict(v.get("example", {})))
                 for k, v in d.get("queries", {}).items()},
        questions=[Question(id=q["id"], text=q["text"], expect=q.get("expect"), query=q.get("query", ""),
                            decision=q.get("decision", ""), key=str(q.get("key", "")),
                            params=dict(q.get("params", {}))) for q in d.get("questions", [])],
        exclusive=[tuple(x) for x in d.get("exclusive", [])],
        identities=identities,
        parameters=parameters,
        metrics={k: _metric(k, v) for k, v in (d.get("metrics") or {}).items()},
        conflicts={k: _conflict(k, v) for k, v in (d.get("conflicts") or {}).items()},
        functions={k: _function(k, v) for k, v in (d.get("functions") or {}).items()},
        areas={k: _area(k, v) for k, v in (d.get("areas") or {}).items()},
    )
    _period_values(onto)
    _role_scopes(onto)
    _settle_conflicts(onto)
    return onto


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in ("", [], {}, None, False)}


def _to_dict(o: Ontology) -> dict:
    objects = {}
    generated = set(o.identities)
    generated_links = {i.link_name(m) for i in o.identities.values() for m in i.members}
    for t in o.objects.values():
        if t.name in generated:
            continue
        props = {p.name: _clean({"type": p.type, "label": p.label, "description": p.description,
                                 "column": p.column, "unit": p.unit, "values": p.values, "required": p.required,
                                 "cite": p.cite, "aligned": p.aligned, "mask": p.mask, "labels": p.labels,
                                 "expr": "" if p.transform or p.name + TEXT_SUFFIX in t.properties else p.expr,
                                 "columns": p.columns, "format": p.format, "transform": p.transform,
                                 "source_type": p.source_type, "status": None if p.status == "active" else p.status})
                 for p in t.properties.values() if not p.internal}
        sm = None
        if t.states:
            sm = _clean({"property": t.states.property, "states": t.states.states, "initial": t.states.initial,
                         "transitions": [_clean({"from": x.source, "to": x.target, "action": x.action,
                                                 "guard": x.guard, "set": x.set, "call": x.call, "after": x.after})
                                         for x in t.states.transitions]})
        bound = t.table and not (t.view and t.table == t.view_name)
        objects[t.name] = _clean({"label": t.label, "description": t.description, "area": t.area,
                                  "source": {"table": t.table} if bound else None, "key": t.key, "title": t.title,
                                  "parent": t.parent, "implements": t.implements, "cite": t.cite,
                                  "aligned": t.aligned, "properties": props, "states": sm, "period": t.period,
                                  "view": t.view, "status": None if t.status == "active" else t.status,
                                  "series": t.series and {**t.series, "time": t.series["time"].removesuffix(TEXT_SUFFIX)}})
    links = {lk.name: _clean({"from": lk.source, "to": lk.target, "cardinality": lk.cardinality,
                              "on": {lk.on[0]: lk.on[1]} if lk.on else None,
                              "via": {"table": lk.via.table, "source": lk.via.source_column,
                                      "target": lk.via.target_column} if lk.via else None,
                              "label": lk.label, "description": lk.description, "inverse": lk.inverse,
                              "transitive": lk.transitive, "symmetric": lk.symmetric, "required": lk.required,
                              "cite": lk.cite, "aligned": lk.aligned, "status": None if lk.status == "active" else lk.status})
             for lk in o.links.values() if lk.name not in generated_links}
    decisions = {}
    for dt in o.decisions.values():
        decisions[dt.name] = _clean({
            "label": dt.label, "target": dt.target, "hit_policy": dt.hit_policy, "cite": dt.cite,
            "inputs": {i.name: {"type": i.type, **i.source} for i in dt.inputs.values()},
            "outputs": dt.outputs,
            "rules": [_clean({"id": r.id, "when": r.when, "then": r.then, "note": r.note, "cite": r.cite,
                              "source": r.source})
                      | ({} if r.priority is None else {"priority": r.priority}) for r in dt.rules]})
    actions = {a.name: _clean({"label": a.label, "target": a.target, "parameters": a.parameters,
                               "criteria": [_clean({"decision": c.decision, "expect": c.expect, "states": c.states,
                                                    "function": c.function}) for c in a.criteria],
                               "set": a.set, "transition_to": a.transition_to, "cite": a.cite,
                               "call": a.call, "undo": a.undo})
               | {"approval": _clean({"auto_within": a.auto_within, "agents": a.auto_agents}) if a.auto_within else a.approval}
               for a in o.actions.values()}
    roles = {r.name: _clean({"label": r.label, "read": r.read, "row_filters": r.row_filters, "run": r.run,
                             "request": r.request, "execute": r.execute, "mask": r.mask, "unmask": r.unmask,
                             "scope": r.scope}) | ({"documents": r.documents} if r.documents is not None else {})
             for r in o.roles.values()}
    identities = {i.name: _clean({"label": i.label, "table": i.table,
                                  "members": {m.type: m.fields for m in i.members.values()},
                                  "rules": [_clean({"id": r.id, "match": r.match, "normalize": r.normalize})
                                            for r in i.rules]}) for i in o.identities.values()}
    parameters = {p.name: _clean({"type": p.type, "label": p.label, "unit": p.unit, "description": p.description,
                                  "cite": p.cite}) | {"value": p.value}
                  | {k: v for k, v in (("min", p.min), ("max", p.max)) if v is not None}
                  for p in o.parameters.values()}
    conflicts = {c.id: _clean({"label": c.label, "decision": c.decision, "input": c.input, "rules": c.rules,
                               "answers": [_clean({"source": a.source, "says": a.says, "rule": a.rule, "cite": a.cite})
                                           for a in c.answers if a.rule not in c.rules or not a.rule],
                               "picked": c.picked, "by": c.by, "at": c.at, "reason": c.reason})
                 for c in o.conflicts.values()}
    metrics = {m.name: _clean({"label": m.label, "description": m.description, "unit": m.unit, "owner": m.owner,
                               "formula": m.formula, "denominator": m.denominator, "time": m.time, "cite": m.cite,
                               "params": m.params}) | ({} if m.scale == 1 else {"scale": m.scale})
               for m in o.metrics.values()}
    functions = {f.name: _clean({"label": f.label, "description": f.description, "runtime": f.runtime, "target": f.target,
                                 "version": f.version, "owner": f.owner, "status": f.status, "inputs": f.inputs,
                                 "outputs": f.outputs, "expr": f.expr, "decision": f.decision, "query": f.query,
                                 "entry": f.entry, "call": f.call, "depends": f.depends, "cite": f.cite})
                 for f in o.functions.values()}
    queries = {q.name: _clean({"label": q.label, "description": q.description, "params": q.params,
                               "example": q.example, "query": q.query}) for q in o.queries.values()}
    questions = [_clean({"id": q.id, "text": q.text, "query": q.query, "decision": q.decision, "key": q.key,
                         "params": q.params}) | {"expect": q.expect} for q in o.questions]
    areas = {a.name: _clean({"label": a.label, "description": a.description, "cite": a.cite, "aligned": a.aligned,
                             "status": None if a.status == "active" else a.status}) for a in o.areas.values()}
    return _clean({
        "ontology": o.name, "namespace": o.namespace, "version": o.version, "label": o.label,
        "parameters": parameters, "areas": areas, "objects": objects, "links": links,
        "interfaces": {i.name: _clean({"label": i.label, "properties": i.properties}) for i in o.interfaces.values()},
        "decisions": decisions, "actions": actions, "roles": roles, "queries": queries, "metrics": metrics,
        "functions": functions,
        "conflicts": conflicts, "questions": questions,
        "exclusive": [list(x) for x in o.exclusive], "identities": identities,
    })
