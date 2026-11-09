"""Consistency checks for an ontology definition."""
from __future__ import annotations

import re

from xgen_space.model import CARDINALITIES, RAW_SUFFIX, STATUSES, TEXT_SUFFIX, TYPES, Ontology, valid_name


def validate_ontology(o: Ontology) -> list[str]:
    issues: list[str] = []
    add = issues.append
    if not o.namespace or not o.namespace.endswith(("#", "/")):
        add("namespace must end with '#' or '/'")

    prop_types: dict[str, tuple[str, str]] = {}
    for t in o.objects.values():
        if not valid_name(t.name):
            add(f"object type name '{t.name}' is not an identifier")
        if t.key not in t.properties:
            add(f"{t.name}: key '{t.key}' is not a property")
        if t.title and t.title not in t.properties:
            add(f"{t.name}: title '{t.title}' is not a property")
        if t.parent and t.parent not in o.objects:
            add(f"{t.name}: parent '{t.parent}' is unknown")
        if t.status not in STATUSES:
            add(f"{t.name}: status '{t.status}' is not one of {STATUSES}")
        for i in t.implements:
            iface = o.interfaces.get(i)
            if iface is None:
                add(f"{t.name}: interface '{i}' is unknown")
                continue
            for p in iface.properties:
                if p not in t.properties:
                    add(f"{t.name}: implements {i} but lacks '{p}'")
                elif t.properties[p].expr:
                    add(f"{t.name}: implements {i} with '{p}' computed; an interface reads stored properties")
        for p in t.properties.values():
            if not valid_name(p.name):
                add(f"{t.name}.{p.name}: property name is not an identifier")
            if p.type not in TYPES:
                add(f"{t.name}.{p.name}: type '{p.type}' is not one of {TYPES}")
            if p.type == "enum" and not p.values:
                add(f"{t.name}.{p.name}: enum needs values")
            if p.labels and p.values and set(p.labels) - {str(v) for v in p.values}:
                add(f"{t.name}.{p.name}: labels for values it does not allow: "
                    f"{sorted(set(p.labels) - {str(v) for v in p.values})}")
            if p.mask and p.mask not in MASKS:
                add(f"{t.name}.{p.name}: mask '{p.mask}' is not one of {MASKS}")
            if p.status not in STATUSES:
                add(f"{t.name}.{p.name}: status '{p.status}' is not one of {STATUSES}")
            stored_text = p.name + TEXT_SUFFIX in t.properties or p.name + RAW_SUFFIX in t.properties  # the expression is made
            issues.extend(f"{t.name}.{p.name}: {e}" for e in _transform(t, p))
            if p.format:
                issues.extend(f"{t.name}.{p.name}: {e}" for e in _format(p, stored_text))
            if p.expr and p.column and not stored_text:
                add(f"{t.name}.{p.name}: a computed property has no column; give expr or column, not both")
            if p.expr and p.name == t.key:
                add(f"{t.name}: the key '{p.name}' cannot be computed")
            if p.columns and (p.column or (p.expr and not stored_text) or len(p.columns) < 2):
                add(f"{t.name}.{p.name}: columns takes two or more columns, in place of column or expr")
            seen = prop_types.get(p.name)
            if seen and seen[0] != p.type and {seen[0], p.type} != {"string", "enum"}:
                add(f"property '{p.name}' is {seen[0]} on {seen[1]} but {p.type} on {t.name}; one name, one type")
            prop_types.setdefault(p.name, (p.type, t.name))
        if t.states:
            sm = t.states
            if sm.property not in t.properties:
                add(f"{t.name}: state property '{sm.property}' is unknown")
            elif t.properties[sm.property].expr:
                add(f"{t.name}: the state property '{sm.property}' cannot be computed")
            else:
                sp = t.properties[sm.property]
                if sp.type == "enum" and set(sm.states) - set(sp.values):
                    add(f"{t.name}: states {sorted(set(sm.states) - set(sp.values))} are not values of {sp.name}")
            if sm.initial and sm.initial not in sm.states:
                add(f"{t.name}: initial state '{sm.initial}' is not a state")
            for tr in sm.transitions:
                for s in (tr.source, tr.target):
                    if s not in sm.states:
                        add(f"{t.name}: transition uses unknown state '{s}'")
                issues.extend(f"{t.name}: transition {tr.source} -> {tr.target}: {e}" for e in _transition(o, t, tr))
        if t.series:
            tp = t.properties.get(t.series.get("time", "").removesuffix(TEXT_SUFFIX))
            if tp is None:
                add(f"{t.name}: series needs time: a date or datetime property")
            elif tp.type not in ("date", "datetime"):
                add(f"{t.name}: series time '{tp.name}' is {tp.type}, not a date or datetime")
            elif tp.format and not _sorts(tp.format):
                add(f"{t.name}: series time '{tp.name}' is text in a form that does not sort by time ({tp.format})")
        if t.period:
            issues.extend(f"{t.name}: period: {e}" for e in _period(o, t))
        if t.view:
            from xgen_space.decide.views import view_issues

            issues.extend(f"{t.name}: view: {e}" for e in view_issues(o, t))

    for lk in o.links.values():
        if not valid_name(lk.name):
            add(f"link name '{lk.name}' is not an identifier")
        if lk.status not in STATUSES:
            add(f"link {lk.name}: status '{lk.status}' is not one of {STATUSES}")
        if lk.source not in o.objects or lk.target not in o.objects:
            add(f"link {lk.name}: endpoints {lk.source} -> {lk.target} must be object types")
            continue
        if lk.cardinality not in CARDINALITIES:
            add(f"link {lk.name}: cardinality '{lk.cardinality}' is not one of {CARDINALITIES}")
        if lk.on and lk.via:
            add(f"link {lk.name}: use 'on' or 'via', not both")
        if lk.on:
            sp, tp = lk.on
            if sp not in o.objects[lk.source].properties:
                add(f"link {lk.name}: {lk.source} has no property '{sp}'")
            if tp not in o.objects[lk.target].properties:
                add(f"link {lk.name}: {lk.target} has no property '{tp}'")
        if lk.via and lk.cardinality not in ("many_to_many", "one_to_many"):
            add(f"link {lk.name}: 'via' is for many_to_many (or one_to_many) links")
        if (lk.transitive or lk.symmetric) and lk.source != lk.target:
            add(f"link {lk.name}: transitive/symmetric links go from a type to itself")
        if lk.inverse:
            if lk.inverse in o.links or sum(x.inverse == lk.inverse for x in o.links.values()) > 1:
                add(f"link {lk.name}: inverse name '{lk.inverse}' is already taken")

    names: dict[str, str] = {}
    for kind, coll in (("object type", o.objects), ("link", o.links)):
        for n in coll:
            if n in names:
                add(f"'{n}' is both a {names[n]} and a {kind}")
            names[n] = kind
    for lk in o.links.values():
        if lk.inverse:
            if lk.inverse in names:
                add(f"inverse '{lk.inverse}' clashes with a {names[lk.inverse]}")
            names[lk.inverse] = "link"
    for p in prop_types:
        if p in names:
            add(f"property '{p}' clashes with a {names[p]} name")

    for a, b in o.exclusive:
        for n in (a, b):
            if n not in o.links:
                add(f"exclusive pair uses unknown link '{n}'")

    issues.extend(_parameters(o))
    issues.extend(_computed(o))
    for t in o.objects.values():
        of = t.series.get("of") if t.series else ""
        if of and not (of in o.links and o.links[of].source == t.name):
            add(f"{t.name}: series of '{of}' is not a link from {t.name}")
    issues.extend(_decisions(o))
    for a in o.actions.values():
        if a.target not in o.objects:
            add(f"action {a.name}: target '{a.target}' is unknown")
            continue
        t = o.objects[a.target]
        for p in a.set:
            if p not in t.properties:
                add(f"action {a.name}: sets unknown property '{p}'")
            elif t.properties[p].format and t.properties[p].columns:
                add(f"action {a.name}: '{p}' is read from several columns and cannot be set")
            elif t.properties[p].expr and not t.properties[p].format:
                add(f"action {a.name}: '{p}' is computed and cannot be set")
        for name, spec in a.parameters.items():
            issues.extend(f"action {a.name}: parameter '{name}': {e}" for e in _parameter(spec))
        written = [*a.set, *([t.states.property] if a.transition_to and t.states else [])]
        if t.view and written and not any(i.startswith(f"{t.name}: view:") for i in issues):
            from xgen_space.decide.views import write_issue

            why = write_issue(o, t, [p for p in written if p in t.properties])
            if why:
                add(f"action {a.name}: {why}")
        if a.call:
            issues.extend(f"action {a.name}: call: {e}" for e in _call(a.call))
        if a.undo:
            issues.extend(f"action {a.name}: undo: {e}" for e in _call(a.undo))
        if a.transition_to:
            if not t.states:
                add(f"action {a.name}: {t.name} has no state machine")
            elif a.transition_to not in t.states.states:
                add(f"action {a.name}: '{a.transition_to}' is not a state of {t.name}")
        for c in a.criteria:
            if c.decision and c.decision not in o.decisions:
                add(f"action {a.name}: criterion uses unknown decision '{c.decision}'")
            if c.function and c.function not in o.functions:
                add(f"action {a.name}: criterion uses unknown function '{c.function}'")
        issues.extend(f"action {a.name}: approval: {e}" for e in _auto_within(o, a, t))
        for v in a.set.values():
            if isinstance(v, str) and v.startswith("$") and v[1:] not in a.parameters and not _fills_itself(v):
                add(f"action {a.name}: '{v}' is not a parameter")

    for r in o.roles.values():
        for t in r.read:
            if t != "*" and t not in o.objects:
                add(f"role {r.name}: reads unknown type '{t}'")
        for t in r.row_filters:
            if t not in o.objects:
                add(f"role {r.name}: row filter on unknown type '{t}'")
        for a in r.request + r.execute:
            if a != "*" and a not in o.actions:
                add(f"role {r.name}: unknown action '{a}'")
        for ref, style in r.mask.items():
            if style not in MASKS:
                add(f"role {r.name}: mask '{style}' for {ref} is not one of {MASKS}")
        for ref in [*r.mask, *r.unmask]:
            tn, _, pn = ref.partition(".")
            if ref == "*":
                continue
            if tn not in o.objects or not pn or (pn != "*" and _prop_of(o, tn, pn) is None):
                add(f"role {r.name}: '{ref}' is not Type.property")
        if r.scope:
            issues.extend(f"role {r.name}: scope: {e}" for e in _scope(o, r))
    issues.extend(_identities(o))
    from xgen_space.functions import function_issues

    for f in o.functions.values():
        issues.extend(f"function {f.name}: {e}" for e in function_issues(o, f))

    from xgen_space.check import check
    from xgen_space.ir import IRError, Query

    for q in o.queries.values():
        try:
            res = check(Query.from_dict(q.query), o)
        except IRError as e:
            add(f"query {q.name}: {e}")
            continue
        for i in res.issues:
            add(f"query {q.name}: {i}")
        for p in res.param_types:
            if p not in q.params:
                add(f"query {q.name}: parameter '{p}' is not declared")
    if o.metrics:
        from xgen_space.decide.metrics import metric_issues

        for m in o.metrics.values():
            issues.extend(f"metric {m.name}: {e}" for e in metric_issues(o, m))
    if o.conflicts:
        from xgen_space.decide.conflicts import conflict_issues

        for c in o.conflicts.values():
            issues.extend(f"conflict {c.id}: {e}" for e in conflict_issues(o, c))
    for qs in o.questions:
        if bool(qs.query) == bool(qs.decision):
            add(f"question {qs.id}: give either a query or a decision")
        if qs.query and qs.query not in o.queries:
            add(f"question {qs.id}: unknown query '{qs.query}'")
        if qs.decision and qs.decision not in o.decisions:
            add(f"question {qs.id}: unknown decision '{qs.decision}'")
    return issues


MASKS = ("partial", "full")
PARAMETER_TYPES = ("integer", "decimal", "string", "boolean")
PARAM_KEYS = {"default", "type", "label", "required", "min", "max", "values", "pattern", "max_length"}
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


def _prop_of(o: Ontology, type_name: str, name: str):
    from xgen_space.check import _find_prop

    return _find_prop(o, type_name, name)


def _fills_itself(value: str) -> bool:
    return value in ("$today", "$now") or value.startswith("$principal.")


def _transition(o: Ontology, t, tr) -> list[str]:
    out = []
    g = tr.guard
    if g:
        unknown = set(g) - {"decision", "expect", "property"}
        if unknown:
            out.append(f"guard: unknown keys {sorted(unknown)}")
        if bool(g.get("decision")) == bool(g.get("property")):
            out.append("guard: give a decision or a property")
        if g.get("decision") and g["decision"] not in o.decisions:
            out.append(f"guard: unknown decision '{g['decision']}'")
        if g.get("decision") and o.decisions.get(g["decision"]) and o.decisions[g["decision"]].target != t.name:
            out.append(f"guard: decision '{g['decision']}' is not about {t.name}")
        if g.get("property"):
            p = _prop_of(o, t.name, g["property"])
            if p is None:
                out.append(f"guard: {t.name} has no property '{g['property']}'")
            elif p.type != "boolean":
                out.append(f"guard: property '{g['property']}' is {p.type}, not a true/false value")
    action = o.actions.get(tr.action)
    for name, v in tr.set.items():
        p = _prop_of(o, t.name, name)
        if p is None:
            out.append(f"sets unknown property '{name}'")
        elif p.expr and not p.format:
            out.append(f"'{name}' is computed and cannot be set")
        elif p.format and p.columns:
            out.append(f"'{name}' is read from several columns and cannot be set")
        if isinstance(v, str) and v.startswith("$") and not _fills_itself(v) and \
                (action is None or v[1:] not in action.parameters):
            out.append(f"'{v}' is not a parameter of {tr.action or 'any action'}")
    if tr.call:
        out.extend(f"call: {e}" for e in _call(tr.call))
        if action is not None and action.call:
            out.append(f"action {action.name} makes its own call; give one of them")
    if tr.after:
        out.extend(_after(o, t, tr))
    return out


def _after(o: Ontology, t, tr) -> list[str]:
    out = [f"after: unknown keys {sorted(set(tr.after) - {'days', 'since'})}"] if set(tr.after) - {"days", "since"} else []
    days = tr.after.get("days")
    if isinstance(days, str) and days.startswith("@"):
        p = o.parameters.get(days[1:])
        if p is None:
            out.append(f"after: unknown parameter '{days}'")
        elif p.type != "integer":
            out.append(f"after: parameter '{days}' is {p.type}, not a whole number")
    elif isinstance(days, bool) or not isinstance(days, int) or days < 0:
        out.append("after: days takes a whole number or @parameter")
    since = _prop_of(o, t.name, tr.after.get("since", ""))
    if since is None:
        out.append("after: since takes a date or datetime property")
    elif since.type not in ("date", "datetime"):
        out.append(f"after: since '{since.name}' is {since.type}, not a date or datetime")
    if tr.action:
        out.append("after: a transition on the clock is taken by no action")
    return out


def _scope(o: Ontology, r) -> list[str]:
    from xgen_space.check import is_a

    out = [f"unknown key '{k}'" for k in r.scope if k not in ("attribute", "types")]
    if not r.scope.get("attribute"):
        out.append("needs attribute: what the principal says it belongs to")
    if not r.scope.get("types"):
        out.append("needs types: the property that holds it on each type")
    for name, where in (r.scope.get("types") or {}).items():
        if name not in o.objects:
            out.append(f"unknown type '{name}'")
            continue
        spec = {"property": where} if isinstance(where, str) else where if isinstance(where, dict) else {}
        here = name
        for step in spec.get("via") or []:
            lk = o.links.get(step) or o.link_by_inverse(step)
            if lk is None:
                out.append(f"{name}: unknown link '{step}' in via")
                here = ""
                break
            here = lk.target if lk.name == step else lk.source
        if not spec.get("property"):
            out.append(f"{name}: give a property, or {{via: [links], property}}")
        elif here and _prop_of(o, here, spec["property"]) is None:
            out.append(f"{name}: {here} has no property '{spec['property']}'")
    for t in o.objects:  # a parent read in full would show the rows of its scoped subtypes
        if t not in r.scoped and r.can_read(t) and any(is_a(o, s, t) for s in r.scoped):
            out.append(f"it reads {t} in full, whose subtypes are scoped; scope {t} or do not read it")
    return out


def _format(p, stored_text: bool) -> list[str]:
    from xgen_space.expr import TIME_PARTS, ExprError, date_format

    try:
        parts = date_format(p.format)
    except ExprError as e:
        return [str(e)]
    if p.type not in ("date", "datetime"):
        return [f"format reads text as a date; declare it date or datetime, not {p.type}"]
    if p.type == "date" and set(parts) & set(TIME_PARTS):
        return [f"format {p.format} carries a time; declare it datetime"]
    return [] if stored_text else ["format reads a stored column and takes no expr"]


def _sorts(fmt: str) -> bool:
    from xgen_space.expr import DATE_PARTS, date_format

    parts = list(date_format(fmt))
    return parts == [x for x in DATE_PARTS if x in parts]


def _period(o: Ontology, t) -> list[str]:
    out = [f"unknown key '{k}'" for k in t.period if k not in ("start", "end", "of", "end_exclusive")]
    if not t.period.get("start"):
        out.append("needs start: a date or datetime property")
    for k in ("start", "end"):
        name = t.period.get(k)
        if not name:
            continue
        p = _prop_of(o, t.name, name)
        if p is None:
            out.append(f"{k} '{name}' is not a property")
        elif p.type not in ("date", "datetime"):
            out.append(f"{k} '{name}' is {p.type}, not a date or datetime")
    of = t.period.get("of")
    if of and not (of in o.links and o.links[of].source == t.name):
        out.append(f"of '{of}' is not a link from {t.name}")
    return out


def _parameters(o: Ontology) -> list[str]:
    from xgen_space.values import accepts

    issues = []
    for p in o.parameters.values():
        head = f"parameter {p.name}"
        if not valid_name(p.name):
            issues.append(f"{head}: the name is not an identifier")
        if p.type not in PARAMETER_TYPES:
            issues.append(f"{head}: type '{p.type}' is not one of {PARAMETER_TYPES}")
        elif p.value is None:
            issues.append(f"{head}: needs a value")
        elif not accepts(p.type, p.value):
            issues.append(f"{head}: {p.value!r} is not {p.type}")
        elif p.type in ("integer", "decimal"):
            if p.min is not None and p.value < p.min:
                issues.append(f"{head}: {p.value} is below {p.min}")
            if p.max is not None and p.value > p.max:
                issues.append(f"{head}: {p.value} is above {p.max}")
    return issues


def _transform(t, p) -> list[str]:
    out = []
    if p.source_type and p.source_type not in TYPES:
        out.append(f"source_type '{p.source_type}' is not one of {TYPES}")
    if not p.transform:
        return out + (["source_type goes with a transform"] if p.source_type else [])
    if p.name == t.key:
        out.append("a key is read as it is stored, without a transform")
    if p.columns:
        out.append("a transform reads one column, not several")
    if p.format:
        out.append("a date kept as text takes format, not a transform")
    if p.name + RAW_SUFFIX not in t.properties and not p.columns:
        out.append("give a transform or an expression, not both")
    return out


def _auto_within(o: Ontology, a, t) -> list[str]:
    from xgen_space.check import _find_prop

    out = []
    for spec in a.auto_within:
        prop, param = spec.get("property"), spec.get("parameter")
        kinds = [k for k in ("delta", "percent", "max", "min") if k in spec]
        if bool(prop) == bool(param):
            out.append("each limit names a property or a parameter")
            continue
        if not kinds:
            out.append(f"{prop or param}: give delta, percent, max or min")
        if param:
            if param not in a.parameters:
                out.append(f"'{param}' is not a parameter of the action")
            if "delta" in kinds or "percent" in kinds:
                out.append(f"{param}: a parameter has no before, so it takes max or min")
        else:
            found = _find_prop(o, t.name, prop)
            if found is None:
                out.append(f"'{prop}' is not a property of {t.name}")
            elif found.type not in ("integer", "decimal"):
                out.append(f"'{prop}' is {found.type}; a limit reads a number")
            elif prop not in a.set:
                out.append(f"the action does not set '{prop}'")
        for k in kinds:
            v = spec[k]
            if isinstance(v, str) and v.startswith("@"):
                if v[1:] not in o.parameters:
                    out.append(f"{k}: unknown named value '{v}'")
            elif isinstance(v, bool) or not isinstance(v, (int, float)):
                out.append(f"{k} is a number or @name")
    return out


def _computed(o: Ontology) -> list[str]:
    from xgen_space.expr import check_computed

    issues = []
    for t in o.objects.values():
        for p in t.properties.values():
            if p.expr:
                issues += [f"{t.name}.{p.name}: {e}" for e in check_computed(o, t.name, p.name).issues]
    return issues


def _parameter(spec) -> list[str]:
    if isinstance(spec, str):
        spec = {"type": spec}
    if not isinstance(spec, dict):
        return ["give a type name or {type, required, min, max, values, pattern, max_length}"]
    out = [f"unknown key '{k}'" for k in spec if k not in PARAM_KEYS]
    if spec.get("type", "string") not in TYPES:
        out.append(f"type '{spec.get('type')}' is not one of {TYPES}")
    for k in ("min", "max", "max_length"):
        if k in spec and (isinstance(spec[k], bool) or not isinstance(spec[k], (int, float))):
            out.append(f"{k} must be a number")
    if "values" in spec and not isinstance(spec["values"], list):
        out.append("values must be a list")
    if "pattern" in spec:
        try:
            re.compile(str(spec["pattern"]))
        except re.error as e:
            out.append(f"pattern does not compile: {e}")
    return out


def _call(spec: dict) -> list[str]:
    out = []
    url = str(spec.get("url", ""))
    if not url.startswith(("http://", "https://")):
        out.append("url must start with http:// or https://")
    if str(spec.get("method", "POST")).upper() not in METHODS:
        out.append(f"method must be one of {METHODS}")
    unknown = set(spec) - {"url", "method", "headers", "body", "timeout", "label", "path"}  # path: where a JSON answer holds its value
    if unknown:
        out.append(f"unknown keys {sorted(unknown)}")
    return out


def _identities(o: Ontology) -> list[str]:
    from xgen_space.model import valid_name

    issues = []
    for i in o.identities.values():
        if not valid_name(i.name):
            issues.append(f"identity '{i.name}' is not an identifier")
        if len(i.members) < 1:
            issues.append(f"identity {i.name}: needs members")
        if not i.rules:
            issues.append(f"identity {i.name}: needs at least one rule")
        fields = {f for r in i.rules for f in r.match}
        for m in i.members.values():
            if m.type not in o.objects:
                issues.append(f"identity {i.name}: member '{m.type}' is not an object type")
                continue
            for f in sorted(fields - set(m.fields)):
                issues.append(f"identity {i.name}: {m.type} does not say which property is '{f}'")
            for f, p in m.fields.items():
                if _prop_of(o, m.type, p) is None:
                    issues.append(f"identity {i.name}: {m.type} has no property '{p}' for '{f}'")
        for r in i.rules:
            if not r.match:
                issues.append(f"identity {i.name} rule {r.id}: match lists no fields")
            for f, how in r.normalize.items():
                if how not in NORMALIZERS:
                    issues.append(f"identity {i.name} rule {r.id}: normalize '{how}' is not one of {NORMALIZERS}")
    return issues


NORMALIZERS = ("none", "trim", "lower", "digits", "alnum")
HIT_POLICIES = ("first", "collect", "unique", "priority")
NAMED = re.compile(r"@[A-Za-z_][A-Za-z0-9_]*")


def _decisions(o: Ontology) -> list[str]:
    from xgen_space.decide.cells import CellError, parse_test, resolve
    from xgen_space.decide.checks import table_findings

    issues = []
    for d in o.decisions.values():
        if d.hit_policy not in HIT_POLICIES:
            issues.append(f"decision {d.name}: hit policy '{d.hit_policy}' is not {'/'.join(HIT_POLICIES)}")
        target = o.objects.get(d.target) if d.target else None
        if d.target and target is None:
            issues.append(f"decision {d.name}: target '{d.target}' is unknown")
        for i in d.inputs.values():
            src = i.source
            kinds = [k for k in ("property", "days_since", "count", "param") if k in src]
            if len(kinds) != 1:
                issues.append(f"decision {d.name}.{i.name}: give one of property/days_since/count/param")
                continue
            if kinds[0] == "param" or target is None:
                continue
            here = d.target
            for step in src.get("path", []):
                lk = o.links.get(step) or o.link_by_inverse(step)
                if lk is None:
                    issues.append(f"decision {d.name}.{i.name}: unknown link '{step}' in path")
                    here = None
                    break
                here = lk.target if lk.name == step else lk.source
            if here is None or kinds[0] == "count":
                continue
            name = src[kinds[0]]
            if name not in o.objects[here].properties:
                issues.append(f"decision {d.name}.{i.name}: {here} has no property '{name}'")
        for r in d.rules:
            for k, v in r.when.items():
                if k not in d.inputs:
                    issues.append(f"decision {d.name} rule {r.id}: unknown input '{k}'")
                try:
                    parse_test(v, d.named)
                except CellError as e:
                    issues.append(f"decision {d.name} rule {r.id}: {k}: {e}")
            for k, v in r.then.items():
                if k not in d.outputs:
                    issues.append(f"decision {d.name} rule {r.id}: unknown output '{k}'")
                # only where parameters are in use: without them, "@text" has always been plain text
                if d.named and isinstance(v, str) and resolve(v, d.named) is v and NAMED.fullmatch(v):
                    issues.append(f"decision {d.name} rule {r.id}: {k}: unknown parameter '{v}'")
            if (d.hit_policy == "priority") != (r.priority is not None):
                issues.append(f"decision {d.name} rule {r.id}: "
                              + ("hit policy priority needs a priority on every rule" if d.hit_policy == "priority"
                                 else "priority is read only under hit policy priority"))
            elif r.priority is not None and (isinstance(r.priority, bool) or not isinstance(r.priority, int)):
                issues.append(f"decision {d.name} rule {r.id}: priority must be a whole number")
        if d.hit_policy == "priority" and all(isinstance(r.priority, int) for r in d.rules):
            issues += [str(f) for f in table_findings(d, o) if f.kind == "tie"]
    return issues
