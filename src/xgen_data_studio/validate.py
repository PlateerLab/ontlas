"""Consistency checks for an ontology definition."""
from __future__ import annotations

from xgen_data_studio.model import CARDINALITIES, TYPES, Ontology, valid_name


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
        for i in t.implements:
            iface = o.interfaces.get(i)
            if iface is None:
                add(f"{t.name}: interface '{i}' is unknown")
                continue
            for p in iface.properties:
                if p not in t.properties:
                    add(f"{t.name}: implements {i} but lacks '{p}'")
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
            if p.expr and p.column:
                add(f"{t.name}.{p.name}: a computed property has no column; give expr or column, not both")
            if p.expr and p.name == t.key:
                add(f"{t.name}: the key '{p.name}' cannot be computed")
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
        if t.series:
            tp = t.properties.get(t.series.get("time", ""))
            if tp is None:
                add(f"{t.name}: series needs time: a date or datetime property")
            elif tp.type not in ("date", "datetime"):
                add(f"{t.name}: series time '{tp.name}' is {tp.type}, not a date or datetime")

    for lk in o.links.values():
        if not valid_name(lk.name):
            add(f"link name '{lk.name}' is not an identifier")
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
            elif t.properties[p].expr:
                add(f"action {a.name}: '{p}' is computed and cannot be set")
        for name, spec in a.parameters.items():
            issues.extend(f"action {a.name}: parameter '{name}': {e}" for e in _parameter(spec))
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
        for v in a.set.values():
            if isinstance(v, str) and v.startswith("$") and v[1:] not in a.parameters:
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
    issues.extend(_identities(o))

    from xgen_data_studio.check import check
    from xgen_data_studio.ir import IRError, Query

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
    for qs in o.questions:
        if bool(qs.query) == bool(qs.decision):
            add(f"question {qs.id}: give either a query or a decision")
        if qs.query and qs.query not in o.queries:
            add(f"question {qs.id}: unknown query '{qs.query}'")
        if qs.decision and qs.decision not in o.decisions:
            add(f"question {qs.id}: unknown decision '{qs.decision}'")
    return issues


MASKS = ("partial", "full")
PARAM_KEYS = {"type", "label", "required", "min", "max", "values", "pattern", "max_length"}
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


def _prop_of(o: Ontology, type_name: str, name: str):
    from xgen_data_studio.check import _find_prop

    return _find_prop(o, type_name, name)


def _computed(o: Ontology) -> list[str]:
    from xgen_data_studio.expr import check_computed

    issues = []
    for t in o.objects.values():
        for p in t.properties.values():
            if p.expr:
                issues += [f"{t.name}.{p.name}: {e}" for e in check_computed(o, t.name, p.name).issues]
    return issues


def _parameter(spec) -> list[str]:
    import re

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
    unknown = set(spec) - {"url", "method", "headers", "body", "timeout", "label"}
    if unknown:
        out.append(f"unknown keys {sorted(unknown)}")
    return out


def _identities(o: Ontology) -> list[str]:
    from xgen_data_studio.model import valid_name

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


def _decisions(o: Ontology) -> list[str]:
    from xgen_data_studio.decide.cells import CellError, parse_test

    issues = []
    for d in o.decisions.values():
        if d.hit_policy not in ("first", "collect", "unique"):
            issues.append(f"decision {d.name}: hit policy '{d.hit_policy}' is not first/collect/unique")
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
                    parse_test(v)
                except CellError as e:
                    issues.append(f"decision {d.name} rule {r.id}: {k}: {e}")
            for k in r.then:
                if k not in d.outputs:
                    issues.append(f"decision {d.name} rule {r.id}: unknown output '{k}'")
    return issues
