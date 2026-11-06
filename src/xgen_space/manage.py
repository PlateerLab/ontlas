"""Edits from the management screens (objects, properties, relations, questions), kept as one overlay module.

A standard is never edited in place (see modules.py). What this module defines it changes directly; everything
else it extends or removes. Each edit also takes out what it leaves broken in the rest of the definition (a query
on a removed property, a decision reading it, a link to a removed type) and says so. The module then goes through
a change request, is tried on a copy and is approved like any other.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any

from xgen_space.modules import Module, ModuleError, Requirement, compose, settle

NAME = "workspace"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
PROP_FIELDS = ("label", "description", "type", "column", "unit", "values", "labels", "required", "mask", "expr",
               "cite")
OBJECT_FIELDS = ("label", "description", "parent", "table", "title", "cite")
LINK_FIELDS = ("label", "description", "cardinality", "inverse", "required", "cite")


class EditError(ValueError):
    """The edit cannot be made; the message says why."""


@dataclass
class Edit:
    op: str
    target: str
    took_out: list[str] = field(default_factory=list)


class Workspace:
    """Pending edits over the attached modules (`base`), with the attached workspace module as the starting point."""

    def __init__(self, base: list[Module], current: Module | None = None, *, label: str = "관리 변경",
                 compose_kw: dict | None = None):
        self.base, self.kw = [m for m in base if m.name != NAME], dict(compose_kw or {})
        self.current = current
        start = copy.deepcopy(current.to_dict()) if current else {"module": NAME, "version": "0.1.0",
                                                                   "kind": "customer", "label": label}
        start.setdefault("description", "관리 화면(객체 · 속성 · 관계 · 규칙 · 기준값 · 액션 · 권한 · 상태 전이 · 검증 질문)에서 바꾼 내용입니다. 표준 모듈은 변경하지 않고 확장 · 제외로 적용합니다.")
        self.module = Module.from_dict(start)
        self.edits: list[Edit] = []
        self._base_onto = compose(self.base, **self.kw).ontology

    # ---- reading ------------------------------------------------------------------------------------------------

    @property
    def dirty(self) -> bool:
        return self.module.to_dict() != (self.current.to_dict() if self.current else Module.from_dict(
            {"module": NAME, "kind": "customer", "label": self.module.label,
             "description": self.module.description}).to_dict())

    def composed(self):
        return compose([*self.base, self.module], **self.kw)

    def _owns_object(self, name: str) -> bool:
        return name in (self.module.body.get("objects") or {})

    def _owns_link(self, name: str) -> bool:
        return name in (self.module.body.get("links") or {})

    def _added_prop(self, obj: str, prop: str) -> bool:
        """A property this module brought in (by definition or by extension), which it may change in full."""
        if self._owns_object(obj):
            return True
        base = self._base_onto.objects.get(obj)
        return base is not None and prop not in base.properties and prop in (
            ((self.module.extend.get("objects") or {}).get(obj) or {}).get("properties") or {})

    # ---- edits --------------------------------------------------------------------------------------------------

    def apply(self, op: str, a: dict[str, Any]) -> Edit:
        fn = getattr(self, f"_{op}", None)
        if fn is None or op.startswith("_"):
            raise EditError(f"unknown edit '{op}'")
        before = copy.deepcopy(self.module.to_dict())
        known = set(self.composed().issues)  # what was already wrong is not this edit's doing
        try:
            target = fn(a)
            self._requires()
            settle(self.module, self.base, **self.kw)
            new = [i for i in compose([*self.base, self.module], **self.kw).issues if i not in known]
            if new:  # what is left broken is this module's own (settle took out the rest): the edit does not hold
                raise EditError("; ".join(new[:3]))
            took = sorted(_removals(self.module.to_dict()) - _removals(before) - {target})
        except EditError:
            self.module = Module.from_dict(before)
            raise
        except (ModuleError, KeyError, TypeError, ValueError) as e:  # the edit does not hold: nothing changes
            self.module = Module.from_dict(before)
            raise EditError(str(e)) from None
        edit = Edit(op, target, took)
        self.edits.append(edit)
        return edit

    def _section(self, part: str, section: str) -> dict:
        holder = self.module.body if part == "body" else self.module.extend
        return holder.setdefault(section, {})

    def _removed(self, section: str) -> list:
        return self.module.remove.setdefault(section, [])

    def _add_object(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if not _IDENT.match(name):
            raise EditError(f"object name '{name}' must be letters, digits and _ starting with a letter")
        if name in self.composed().ontology.objects:
            raise EditError(f"object type '{name}' already exists")
        key = str(a.get("key") or "")
        props = {str(k): _prop_spec(v) for k, v in (a.get("properties") or {}).items()}
        if not key or key not in props:
            raise EditError("give the key and the key property")
        spec: dict[str, Any] = {"key": key, "properties": props}
        for k in ("label", "description", "parent", "title"):
            if a.get(k):
                spec[k] = a[k]
        if a.get("table"):
            spec["source"] = {"table": str(a["table"])}
        self._section("body", "objects")[name] = spec
        return f"object:{name}"

    def _update_object(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if name not in self.composed().ontology.objects:
            raise EditError(f"object type '{name}' is unknown")
        fields = {k: a[k] for k in OBJECT_FIELDS if k in a}
        if self._owns_object(name):
            spec = self._section("body", "objects")[name]
            for k, v in fields.items():
                if k == "table":
                    spec["source"] = {"table": v} if v else None
                elif v in ("", None):
                    spec.pop(k, None)
                else:
                    spec[k] = v
            if a.get("key"):
                if a["key"] not in (spec.get("properties") or {}):
                    raise EditError(f"key '{a['key']}' is not a property of {name}")
                spec["key"] = a["key"]
        else:
            if a.get("key"):
                raise EditError(f"the key of {name} is set where it is defined; change it there")
            patch = self._section("extend", "objects").setdefault(name, {})
            patch.update({k: v for k, v in fields.items() if v not in (None,)})
        return f"object:{name}"

    def _delete_object(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if self._owns_object(name):
            del self._section("body", "objects")[name]
            links = self._section("body", "links")
            for lk in [k for k, v in links.items() if name in (v.get("from"), v.get("to"))]:
                del links[lk]
        else:
            if name not in self._base_onto.objects:
                raise EditError(f"object type '{name}' is unknown")
            if name not in self._removed("objects"):
                self._removed("objects").append(name)
            (self.module.extend.get("objects") or {}).pop(name, None)
            for lk in self._base_onto.links.values():  # its relations go with it
                if name in (lk.source, lk.target) and lk.name not in self._removed("links"):
                    self._removed("links").append(lk.name)
        return f"object:{name}"

    def _add_property(self, a: dict) -> str:
        obj, name = str(a.get("object") or ""), str(a.get("name") or "")
        onto = self.composed().ontology
        if obj not in onto.objects:
            raise EditError(f"object type '{obj}' is unknown")
        if not _IDENT.match(name):
            raise EditError(f"property name '{name}' must be letters, digits and _ starting with a letter")
        if name in _all_props(onto, obj):
            raise EditError(f"{obj} already has '{name}'")
        spec = _prop_spec(a)
        if self._owns_object(obj):
            self._section("body", "objects")[obj].setdefault("properties", {})[name] = spec
        else:
            self._section("extend", "objects").setdefault(obj, {}).setdefault("properties", {})[name] = spec
        return f"property:{obj}.{name}"

    def _update_property(self, a: dict) -> str:
        obj, name = str(a.get("object") or ""), str(a.get("name") or "")
        onto = self.composed().ontology
        if obj not in onto.objects or name not in _all_props(onto, obj):
            raise EditError(f"{obj}.{name} is unknown")
        fields = {k: a[k] for k in PROP_FIELDS if k in a}
        if self._added_prop(obj, name):
            holder = (self._section("body", "objects")[obj] if self._owns_object(obj)
                      else self._section("extend", "objects")[obj])
            spec = holder["properties"][name] = {**_as_dict(holder["properties"][name]), **_clean(fields)}
            for k in [k for k, v in fields.items() if v in ("", None, [], False) and k != "required"]:
                spec.pop(k, None)
        else:
            if "type" in fields and fields["type"] != _prop(onto, obj, name).type:
                raise EditError(f"the type of {obj}.{name} comes from its standard; it cannot be changed here")
            fields.pop("type", None)
            patch = self._section("extend", "objects").setdefault(obj, {}).setdefault("properties", {})
            patch[name] = {**_as_dict(patch.get(name)), **{k: v for k, v in fields.items() if v is not None}}
        return f"property:{obj}.{name}"

    def _delete_property(self, a: dict) -> str:
        obj, name = str(a.get("object") or ""), str(a.get("name") or "")
        onto = self.composed().ontology
        if obj not in onto.objects or name not in _all_props(onto, obj):
            raise EditError(f"{obj}.{name} is unknown")
        if name == onto.objects[obj].key:
            raise EditError(f"'{name}' is the key of {obj}; delete the object instead")
        if self._added_prop(obj, name):
            holder = (self._section("body", "objects")[obj] if self._owns_object(obj)
                      else self._section("extend", "objects")[obj])
            del holder["properties"][name]
        else:
            owner = next((t for t in _lineage(self._base_onto, obj) if name in self._base_onto.objects[t].properties),
                         obj)
            if owner != obj:
                raise EditError(f"'{name}' comes from {owner}, which {obj} specialises; delete it on {owner}")
            props = self.module.remove.setdefault("properties", {}).setdefault(owner, [])
            if name not in props:
                props.append(name)
            patch = ((self.module.extend.get("objects") or {}).get(obj) or {}).get("properties") or {}
            patch.pop(name, None)
        return f"property:{obj}.{name}"

    def _add_link(self, a: dict) -> str:
        name = str(a.get("name") or "")
        onto = self.composed().ontology
        if not _IDENT.match(name):
            raise EditError(f"link name '{name}' must be letters, digits and _ starting with a letter")
        if name in onto.links or onto.link_by_inverse(name):
            raise EditError(f"link '{name}' already exists")
        spec: dict[str, Any] = {"from": a.get("source"), "to": a.get("target"),
                                "cardinality": a.get("cardinality") or "many_to_one"}
        if a.get("on"):
            sp, tp = a["on"]
            spec["on"] = {str(sp): str(tp)}
        for k in ("label", "description", "inverse", "required"):
            if a.get(k):
                spec[k] = a[k]
        self._section("body", "links")[name] = spec
        return f"link:{name}"

    def _update_link(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if name not in self.composed().ontology.links:
            raise EditError(f"link '{name}' is unknown")
        fields = {k: a[k] for k in LINK_FIELDS if k in a}
        if a.get("on"):
            sp, tp = a["on"]
            fields["on"] = {str(sp): str(tp)}
        if self._owns_link(name):
            spec = self._section("body", "links")[name]
            if "source" in a:
                spec["from"] = a["source"]
            if "target" in a:
                spec["to"] = a["target"]
            spec.update(_clean(fields))
        else:
            if "source" in a or "target" in a:
                raise EditError(f"the endpoints of {name} come from its standard; add a new link instead")
            self._section("extend", "links").setdefault(name, {}).update(_clean(fields))
        return f"link:{name}"

    def _delete_link(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if self._owns_link(name):
            del self._section("body", "links")[name]
        else:
            if name not in self._base_onto.links:
                raise EditError(f"link '{name}' is unknown")
            if name not in self._removed("links"):
                self._removed("links").append(name)
            (self.module.extend.get("links") or {}).pop(name, None)
        return f"link:{name}"

    def _add_question(self, a: dict) -> str:
        qid = str(a.get("id") or "")
        onto = self.composed().ontology
        if not qid or any(q.id == qid for q in onto.questions):
            raise EditError(f"question id '{qid}' is empty or already used")
        q = {"id": qid, "text": str(a.get("text") or "")}
        if a.get("decision"):
            q.update({"decision": a["decision"], "key": str(a.get("key") or "")})
        else:
            q.update({"query": a.get("query"), "params": dict(a.get("params") or {})})
        q["expect"] = a.get("expect") or {}
        self.module.body.setdefault("questions", []).append(q)
        return f"question:{qid}"

    def _delete_question(self, a: dict) -> str:
        qid = str(a.get("id") or "")
        own = self.module.body.get("questions") or []
        if any(q.get("id") == qid for q in own):
            self.module.body["questions"] = [q for q in own if q.get("id") != qid]
        else:
            if not any(q.id == qid for q in self._base_onto.questions):
                raise EditError(f"question '{qid}' is unknown")
            if qid not in self._removed("questions"):
                self._removed("questions").append(qid)
        return f"question:{qid}"

    # ---- rules, named values, actions, roles and states ---------------------------------------------------------

    def _owns(self, section: str, name: str) -> bool:
        return name in (self.module.body.get(section) or {})

    def _rule(self, a: dict, table) -> dict:
        from xgen_space.decide.cells import CellError, parse_test
        from xgen_space.decide.words import cell_of

        rid = str(a.get("id") or "")
        if not _RULE.match(rid):
            raise EditError(f"rule id '{rid}' must be letters, digits, _ and - starting with a letter")
        when: dict[str, str] = {}
        for name, part in (a.get("when") or {}).items():
            if name not in table.inputs:
                raise EditError(f"decision {table.name} has no input '{name}'")
            cell = cell_of(str(part.get("op") or "any"), part.get("value"), table.inputs[name].type) if isinstance(part, dict) else str(part)
            if cell == "-":
                continue
            try:
                parse_test(cell, table.named)
            except CellError as e:
                raise EditError(f"{name}: {e}") from None
            when[name] = cell
        then = dict(a.get("then") or {})
        unknown = [k for k in then if k not in table.outputs]
        if unknown:
            raise EditError(f"decision {table.name} has no output '{unknown[0]}'")
        spec: dict[str, Any] = {"id": rid, "when": when, "then": then}
        if a.get("cite"):
            spec["cite"] = str(a["cite"])
        return spec

    def _table(self, name: str):
        t = self.composed().ontology.decisions.get(name)
        if t is None:
            raise EditError(f"decision '{name}' is unknown")
        return t

    def _add_rule(self, a: dict) -> str:
        name = str(a.get("decision") or "")
        t = self._table(name)
        spec = self._rule(a, t)
        if any(r.id == spec["id"] for r in t.rules):
            raise EditError(f"rule '{spec['id']}' already exists in {name}")
        first = a.get("first", True)
        if self._owns("decisions", name):
            rules = self._section("body", "decisions")[name].setdefault("rules", [])
            rules.insert(0 if first else len(rules), spec)
        else:
            patch = self._section("extend", "decisions").setdefault(name, {})
            patch.setdefault("rules_prepend" if first else "rules_append", []).append(spec)
        return f"rule:{name}.{spec['id']}"

    def _update_rule(self, a: dict) -> str:
        name = str(a.get("decision") or "")
        t = self._table(name)
        spec = self._rule(a, t)
        if not any(r.id == spec["id"] for r in t.rules):
            raise EditError(f"rule '{spec['id']}' is unknown in {name}")
        holders = [self._section("body", "decisions")[name].setdefault("rules", [])] if self._owns("decisions", name) else []
        patch = None if holders else self._section("extend", "decisions").setdefault(name, {})
        if patch is not None:
            holders = [patch[k] for k in ("rules_prepend", "rules_append") if k in patch]
        for rules in holders:
            for i, r in enumerate(rules):
                if r.get("id") == spec["id"]:
                    rules[i] = spec
                    return f"rule:{name}.{spec['id']}"
        patch.setdefault("rules_replace", {})[spec["id"]] = spec
        return f"rule:{name}.{spec['id']}"

    def _delete_rule(self, a: dict) -> str:
        name, rid = str(a.get("decision") or ""), str(a.get("id") or "")
        t = self._table(name)
        if not any(r.id == rid for r in t.rules):
            raise EditError(f"rule '{rid}' is unknown in {name}")
        if len(t.rules) == 1:
            raise EditError(f"decision {name} needs at least one rule")
        if self._owns("decisions", name):
            spec = self._section("body", "decisions")[name]
            spec["rules"] = [r for r in spec["rules"] if r.get("id") != rid]
            return f"rule:{name}.{rid}"
        patch = self._section("extend", "decisions").setdefault(name, {})
        for k in ("rules_prepend", "rules_append"):
            if any(r.get("id") == rid for r in patch.get(k) or []):
                patch[k] = [r for r in patch[k] if r.get("id") != rid]
                return f"rule:{name}.{rid}"
        (patch.get("rules_replace") or {}).pop(rid, None)
        patch.setdefault("rules_remove", []).append(rid)
        return f"rule:{name}.{rid}"

    def _add_decision(self, a: dict) -> str:
        name, target = str(a.get("name") or ""), str(a.get("target") or "")
        onto = self.composed().ontology
        if not _IDENT.match(name):
            raise EditError(f"decision name '{name}' must be letters, digits and _ starting with a letter")
        if name in onto.decisions:
            raise EditError(f"decision '{name}' already exists")
        if target not in onto.objects:
            raise EditError(f"object type '{target}' is unknown")
        inputs = {str(k): dict(v) for k, v in (a.get("inputs") or {}).items()}
        if not inputs:
            raise EditError("give at least one input")
        spec = {"label": a.get("label") or name, "target": target, "hit_policy": "first", "inputs": inputs,
                "outputs": {"result": "boolean", "reason": "string"},
                "rules": [{"id": "default", "when": {}, "then": {"result": False, "reason": str(a.get("otherwise") or "해당하는 규칙이 없습니다")}}]}
        self._section("body", "decisions")[name] = spec
        return f"decision:{name}"

    def _update_parameter(self, a: dict) -> str:
        name = str(a.get("name") or "")
        p = self.composed().ontology.parameters.get(name)
        if p is None:
            raise EditError(f"named value '{name}' is unknown")
        try:
            value: Any = {"integer": int, "decimal": float, "number": float}.get(p.type, str)(a.get("value"))
        except (TypeError, ValueError):
            raise EditError(f"{name} takes a {p.type}") from None
        if isinstance(value, (int, float)):
            if p.min is not None and value < p.min:
                raise EditError(f"{p.label or name} must be at least {p.min}")
            if p.max is not None and value > p.max:
                raise EditError(f"{p.label or name} must be at most {p.max}")
        if self._owns("parameters", name):
            self._section("body", "parameters")[name]["value"] = value
        else:
            self._section("extend", "parameters")[name] = {"value": value}
        return f"parameter:{name}"

    def _action_spec(self, a: dict) -> dict:
        spec: dict[str, Any] = {}
        for k in ("label", "parameters", "criteria", "transition_to", "approval", "cite"):
            if k in a:
                spec[k] = a[k]
        return spec

    def _add_action(self, a: dict) -> str:
        name, target = str(a.get("name") or ""), str(a.get("target") or "")
        onto = self.composed().ontology
        if not _IDENT.match(name):
            raise EditError(f"action name '{name}' must be letters, digits and _ starting with a letter")
        if name in onto.actions:
            raise EditError(f"action '{name}' already exists")
        if target not in onto.objects:
            raise EditError(f"object type '{target}' is unknown")
        self._section("body", "actions")[name] = {"target": target, "approval": True, **self._action_spec(a)}
        return f"action:{name}"

    def _update_action(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if name not in self.composed().ontology.actions:
            raise EditError(f"action '{name}' is unknown")
        if self._owns("actions", name):
            self._section("body", "actions")[name].update(self._action_spec(a))
        else:
            self._section("extend", "actions").setdefault(name, {}).update(self._action_spec(a))
        return f"action:{name}"

    def _delete_action(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if name not in self.composed().ontology.actions:
            raise EditError(f"action '{name}' is unknown")
        if self._owns("actions", name):
            del self._section("body", "actions")[name]
        else:
            self._removed("actions").append(name)
        return f"action:{name}"

    def _add_role(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if not _IDENT.match(name):
            raise EditError(f"role name '{name}' must be letters, digits and _ starting with a letter")
        if name in self.composed().ontology.roles:
            raise EditError(f"role '{name}' already exists")
        spec = {k: a[k] for k in ("label", "read", "run", "request", "execute", "mask", "row_filters") if a.get(k)}
        self._section("body", "roles")[name] = spec
        return f"role:{name}"

    def _update_role(self, a: dict) -> str:
        name = str(a.get("name") or "")
        r = self.composed().ontology.roles.get(name)
        if r is None:
            raise EditError(f"role '{name}' is unknown")
        if self._owns("roles", name):
            self._section("body", "roles")[name].update({k: a[k] for k in ("label", "read", "run", "request", "execute", "mask") if k in a})
            return f"role:{name}"
        patch = self._section("extend", "roles").setdefault(name, {})
        if "label" in a:
            patch["label"] = a["label"]
        for k in ("read", "run", "request", "execute"):
            if k not in a:
                continue
            want, have = list(a[k] or []), list(getattr(r, k))
            patch[k] = [x for x in want if x not in have] or patch.get(k, [])
            patch[f"{k}_drop"] = [x for x in have if x not in want] or patch.get(f"{k}_drop", [])
        if "mask" in a:
            want = dict(a["mask"] or {})
            patch["mask"] = {k: v for k, v in want.items() if r.mask.get(k) != v}
            patch["mask_drop"] = [k for k in r.mask if k not in want]
        for k in [k for k, v in patch.items() if v in ([], {})]:
            del patch[k]
        return f"role:{name}"

    def _delete_role(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if name not in self.composed().ontology.roles:
            raise EditError(f"role '{name}' is unknown")
        if self._owns("roles", name):
            del self._section("body", "roles")[name]
        else:
            self._removed("roles").append(name)
        return f"role:{name}"

    def _update_states(self, a: dict) -> str:
        name = str(a.get("object") or "")
        t = self.composed().ontology.objects.get(name)
        if t is None:
            raise EditError(f"object type '{name}' is unknown")
        states = [str(s).strip() for s in a.get("states") or [] if str(s).strip()]
        if len(states) < 2:
            raise EditError("a state machine has at least two states")
        moves = [{k: v for k, v in {"from": m.get("from"), "to": m.get("to"), "action": m.get("action")}.items() if v}
                 for m in a.get("transitions") or []]
        for m in moves:
            if m.get("from") not in states or m.get("to") not in states:
                raise EditError(f"a transition goes between states: {m.get('from')} to {m.get('to')}")
        spec = {"property": str(a.get("property") or ""), "states": states, "transitions": moves}
        if a.get("initial"):
            spec["initial"] = str(a["initial"])
        prop = _prop(self.composed().ontology, name, spec["property"])
        extra = [s for s in states if prop is not None and prop.values and s not in prop.values]  # a new state is a new value of its property
        if self._owns_object(name):
            body = self._section("body", "objects")[name]
            body["states"] = spec
            if extra and spec["property"] in (body.get("properties") or {}):
                body["properties"][spec["property"]]["values"] = [*prop.values, *extra]
        else:
            patch = self._section("extend", "objects").setdefault(name, {})
            patch["states_set"] = spec
            if extra:
                patch.setdefault("properties", {}).setdefault(spec["property"], {})["values_add"] = extra
        return f"states:{name}"

    def _requires(self) -> None:
        """The modules whose elements this module extends, removes or hangs from, so it composes after them."""
        comp = compose(self.base, **self.kw)
        owners: set[str] = set()
        for t, patch in (self.module.extend.get("objects") or {}).items():
            owners.add(comp.owner(f"object:{t}"))
            for p in (patch or {}).get("properties") or {}:
                owners.add(comp.owner(f"property:{t}.{p}"))
        for lk in self.module.extend.get("links") or {}:
            owners.add(comp.owner(f"link:{lk}"))
        for section, kind in (("decisions", "decision"), ("actions", "action"), ("roles", "role"), ("parameters", "parameter")):
            owners |= {comp.owner(f"{kind}:{k}") for k in self.module.extend.get(section) or {}}
        for section in ("decisions", "actions"):
            owners |= {comp.owner(f"object:{spec.get('target')}") for spec in (self.module.body.get(section) or {}).values()}
        for s, items in self.module.remove.items():
            if s == "properties":
                owners |= {comp.owner(f"property:{t}.{p}") for t, ps in items.items() for p in ps}
            elif s == "questions":
                owners |= {comp.owner(f"question:{q}") for q in items}
            elif s == "states":
                owners |= {comp.owner(f"object:{t}") for t in items}
            else:
                kind = {"objects": "object", "links": "link", "queries": "query", "decisions": "decision",
                        "actions": "action", "identities": "identity"}.get(s, s)
                owners |= {comp.owner(f"{kind}:{k}") for k in items}
        for spec in (self.module.body.get("objects") or {}).values():
            if spec.get("parent"):
                owners.add(comp.owner(f"object:{spec['parent']}"))
        for spec in (self.module.body.get("links") or {}).values():
            owners |= {comp.owner(f"object:{spec.get('from')}"), comp.owner(f"object:{spec.get('to')}")}
        for q in self.module.body.get("questions") or []:
            owners.add(comp.owner(f"query:{q.get('query')}") if q.get("query") else
                       comp.owner(f"decision:{q.get('decision')}"))
        self.module.requires = [Requirement(o) for o in sorted(o for o in owners if o and o != NAME)]


def _removals(d: dict) -> set[str]:
    """The elements a module dict takes out, as element ids (object:Claim, property:Customer.spent, ...)."""
    out: set[str] = set()
    kinds = {"objects": "object", "links": "link", "queries": "query", "decisions": "decision", "actions": "action",
             "identities": "identity", "questions": "question", "states": "states", "roles": "role",
             "interfaces": "interface"}
    for s, items in (d.get("remove") or {}).items():
        if s == "properties":
            out |= {f"property:{t}.{p}" for t, ps in (items or {}).items() for p in ps}
        else:
            out |= {f"{kinds.get(s, s)}:{k}" for k in items or []}
    return out


def _prop_spec(a: dict) -> dict:
    spec = {"type": str(a.get("type") or "string")}
    for k in ("label", "description", "column", "unit", "expr", "mask", "cite"):
        if a.get(k):
            spec[k] = a[k]
    if a.get("columns"):
        spec["columns"] = [str(c) for c in a["columns"]]
    if a.get("values"):
        spec["values"] = [str(v) for v in a["values"]]
    if a.get("labels"):
        spec["labels"] = {str(k): str(v) for k, v in dict(a["labels"]).items() if str(v).strip()}
    if a.get("required"):
        spec["required"] = True
    return spec


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None,)}


def _as_dict(v: Any) -> dict:
    return dict(v) if isinstance(v, dict) else ({"type": v} if isinstance(v, str) else {})


def _lineage(onto, name: str) -> list[str]:
    out, t = [], name
    while t and t in onto.objects and t not in out:
        out.append(t)
        t = onto.objects[t].parent
    return out


def _all_props(onto, name: str) -> dict:
    out: dict = {}
    for t in reversed(_lineage(onto, name)):
        out.update(onto.objects[t].properties)
    return out


def _prop(onto, obj: str, name: str):
    return _all_props(onto, obj)[name]
