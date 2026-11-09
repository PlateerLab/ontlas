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

from xgen_space.model import TYPES, _scope_filter
from xgen_space.modules import Module, ModuleError, Requirement, compose, settle

NAME = "workspace"
HIT_POLICIES = ("first", "priority", "collect", "unique")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_RULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
PROP_FIELDS = ("label", "description", "type", "column", "unit", "values", "labels", "required", "mask", "expr",
               "cite", "transform", "source_type")
OBJECT_FIELDS = ("label", "description", "parent", "table", "title", "cite")
LINK_FIELDS = ("label", "description", "cardinality", "inverse", "required", "cite")
PARAMETER_FIELDS = ("label", "unit", "description", "cite", "min", "max")
METRIC_FIELDS = ("label", "description", "unit", "owner", "scale", "cite", "formula", "denominator", "time", "params")
IDENTITY_FIELDS = ("label", "table", "members", "rules")
FUNCTION_FIELDS = ("label", "description", "runtime", "target", "version", "owner", "status", "inputs", "outputs", "expr",
                   "decision", "query", "entry", "call", "depends", "cite")


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
        self._before: list[dict] = []  # the module before each edit, to take the last one back
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
        self._before.append(before)
        return edit

    def undo(self) -> Edit | None:
        """Take back the last edit: the module is as it was before it."""
        if not self.edits:
            return None
        self.module = Module.from_dict(self._before.pop())
        return self.edits.pop()

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
        _known_type(a)
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
        _known_type(fields)
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

    def _update_decision(self, a: dict) -> str:
        """A table's label, its clause, or how it picks among the rules that hold."""
        name = str(a.get("decision") or a.get("name") or "")
        t = self._table(name)
        fields = {k: a[k] for k in ("label", "cite", "hit_policy") if k in a}
        if fields.get("hit_policy") and fields["hit_policy"] not in HIT_POLICIES:
            raise EditError(f"hit policy '{fields['hit_policy']}' is not one of {', '.join(HIT_POLICIES)}")
        bare = [r.id for r in t.rules if r.priority is None]
        if fields.get("hit_policy") == "priority" and bare:
            raise EditError(f"hit policy priority needs a priority on every rule; {', '.join(bare)} have none")
        holder = (self._section("body", "decisions")[name] if self._owns("decisions", name)
                  else self._section("extend", "decisions").setdefault(name, {}))
        holder.update(fields)
        return f"decision:{name}"

    def _move_rule(self, a: dict) -> str:
        """A rule to another place in its table. Where the table is another module's, this module writes the whole
        order: it takes the table's rules out and puts them back first, in the new order."""
        name, rid = str(a.get("decision") or ""), str(a.get("id") or "")
        t = self._table(name)
        ids = [r.id for r in t.rules]
        if rid not in ids:
            raise EditError(f"rule '{rid}' is unknown in {name}")
        order = [i for i in ids if i != rid]
        order.insert(max(0, min(int(a.get("to", 0)), len(order))), rid)
        if order == ids:
            return f"rule:{name}.{rid}"
        specs = {r["id"]: r for r in self.composed().ontology.to_dict()["decisions"][name].get("rules") or []}
        if self._owns("decisions", name):
            self._section("body", "decisions")[name]["rules"] = [specs[i] for i in order]
            return f"rule:{name}.{rid}"
        patch = self._section("extend", "decisions").setdefault(name, {})
        mine = {r.get("id") for k in ("rules_prepend", "rules_append") for r in patch.get(k) or []}
        patch["rules_remove"] = sorted(set(patch.get("rules_remove") or []) | {i for i in ids if i not in mine})
        patch.pop("rules_append", None)
        patch.pop("rules_replace", None)
        patch["rules_prepend"] = [specs[i] for i in order]
        return f"rule:{name}.{rid}"

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

    def _parameter_value(self, name: str, kind: str, raw: Any, low: Any, high: Any, label: str = "") -> Any:
        try:
            value: Any = {"integer": int, "decimal": float, "number": float}.get(kind, str)(raw)
        except (TypeError, ValueError):
            raise EditError(f"{name} takes a {kind}") from None
        if kind == "boolean":
            value = str(raw).strip().lower() in ("true", "1", "y", "yes")
        elif isinstance(value, (int, float)):
            if low not in (None, "") and value < float(low):
                raise EditError(f"{label or name} must be at least {low}")
            if high not in (None, "") and value > float(high):
                raise EditError(f"{label or name} must be at most {high}")
        return value

    def _add_parameter(self, a: dict) -> str:
        name = str(a.get("name") or "")
        if not _IDENT.match(name):
            raise EditError(f"named value '{name}' must be letters, digits and _ starting with a letter")
        if name in self.composed().ontology.parameters:
            raise EditError(f"named value '{name}' already exists")
        kind = str(a.get("type") or "integer")
        spec: dict[str, Any] = {"type": kind, "value": self._parameter_value(name, kind, a.get("value"), a.get("min"), a.get("max"))}
        spec.update({k: a[k] for k in PARAMETER_FIELDS if a.get(k) not in (None, "")})
        self._section("body", "parameters")[name] = spec
        return f"parameter:{name}"

    def _update_parameter(self, a: dict) -> str:
        name = str(a.get("name") or "")
        p = self.composed().ontology.parameters.get(name)
        if p is None:
            raise EditError(f"named value '{name}' is unknown")
        low, high = a.get("min", p.min), a.get("max", p.max)
        value = self._parameter_value(name, p.type, a.get("value", p.value), low, high, p.label)
        meta = {k: a[k] for k in PARAMETER_FIELDS if k in a}
        if self._owns("parameters", name):
            spec = self._section("body", "parameters")[name]
            spec.update({"value": value, **meta})
            for k in [k for k, v in spec.items() if v in ("", None)]:
                del spec[k]
        else:
            patch = self._section("extend", "parameters")
            cur = patch.get(name)
            patch[name] = {**(cur if isinstance(cur, dict) else {}), "value": value, **meta}
        return f"parameter:{name}"

    def _delete_parameter(self, a: dict) -> str:
        name = str(a.get("name") or "")
        onto = self.composed().ontology
        if name not in onto.parameters:
            raise EditError(f"named value '{name}' is unknown")
        rest = {k: v for k, v in onto.to_dict().items() if k != "parameters"}
        if re.search(rf"@{re.escape(name)}\b", str(rest)):  # a rule reading it would go with it otherwise
            raise EditError(f"'{name}' is read by rules or expressions; change those first")
        if self._owns("parameters", name):
            del self._section("body", "parameters")[name]
        else:
            (self.module.extend.get("parameters") or {}).pop(name, None)
            self._removed("parameters").append(name)
        return f"parameter:{name}"

    def _entry(self, section: str, kind: str, a: dict, fields: tuple) -> str:
        """Add or change one entry of a section that takes what it is given: its fields, over what was there."""
        name = str(a.get("name") or "")
        spec = {k: copy.deepcopy(a[k]) for k in fields if k in a}
        if self._owns(section, name):
            held = self._section("body", section)[name]
            held.update(spec)
            for k in [k for k, v in held.items() if v in ("", None, [], {})]:
                del held[k]
        else:
            self._section("extend", section).setdefault(name, {}).update(spec)
        return f"{kind}:{name}"

    def _new_entry(self, section: str, kind: str, a: dict, fields: tuple, known) -> str:
        name = str(a.get("name") or "")
        if not _IDENT.match(name):
            raise EditError(f"{kind} name '{name}' must be letters, digits and _ starting with a letter")
        if name in known:
            raise EditError(f"{kind} '{name}' already exists")
        self._section("body", section)[name] = {k: copy.deepcopy(a[k]) for k in fields if a.get(k) not in (None, "", [], {})}
        return f"{kind}:{name}"

    def _gone_entry(self, section: str, kind: str, a: dict, known) -> str:
        name = str(a.get("name") or "")
        if name not in known:
            raise EditError(f"{kind} '{name}' is unknown")
        if self._owns(section, name):
            del self._section("body", section)[name]
        else:
            (self.module.extend.get(section) or {}).pop(name, None)
            self._removed(section).append(name)
        return f"{kind}:{name}"

    def _add_metric(self, a: dict) -> str:
        return self._new_entry("metrics", "metric", a, METRIC_FIELDS, self.composed().ontology.metrics)

    def _update_metric(self, a: dict) -> str:
        if str(a.get("name") or "") not in self.composed().ontology.metrics:
            raise EditError(f"metric '{a.get('name')}' is unknown")
        return self._entry("metrics", "metric", a, METRIC_FIELDS)

    def _delete_metric(self, a: dict) -> str:
        return self._gone_entry("metrics", "metric", a, self.composed().ontology.metrics)

    def _add_identity(self, a: dict) -> str:
        return self._new_entry("identities", "identity", a, IDENTITY_FIELDS, self.composed().ontology.identities)

    def _update_identity(self, a: dict) -> str:
        if str(a.get("name") or "") not in self.composed().ontology.identities:
            raise EditError(f"identity '{a.get('name')}' is unknown")
        return self._entry("identities", "identity", a, IDENTITY_FIELDS)

    def _delete_identity(self, a: dict) -> str:
        return self._gone_entry("identities", "identity", a, self.composed().ontology.identities)

    def _add_function(self, a: dict) -> str:
        return self._new_entry("functions", "function", a, FUNCTION_FIELDS, self.composed().ontology.functions)

    def _update_function(self, a: dict) -> str:
        if str(a.get("name") or "") not in self.composed().ontology.functions:
            raise EditError(f"function '{a.get('name')}' is unknown")
        return self._entry("functions", "function", a, FUNCTION_FIELDS)

    def _delete_function(self, a: dict) -> str:
        return self._gone_entry("functions", "function", a, self.composed().ontology.functions)

    def _action_spec(self, a: dict) -> dict:
        spec: dict[str, Any] = {}
        for k in ("label", "parameters", "criteria", "set", "transition_to", "approval", "cite", "call", "undo"):
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
        if a.get("rows"):
            spec["row_filters"] = self._rows(a["rows"])
        if (a.get("scope") or {}).get("attribute"):
            spec["scope"] = self._scope(a["scope"])
        if a.get("documents") is not None:  # an empty list is a role that reads no document
            spec["documents"] = self._documents(a["documents"])
        self._section("body", "roles")[name] = spec
        return f"role:{name}"

    @staticmethod
    def _documents(names: Any) -> list[str]:
        if not isinstance(names, list):
            raise EditError("documents must be a list of document names or patterns")
        return [str(x).strip() for x in names if str(x).strip()]

    def _rows(self, rows: list) -> dict:
        """Row rules from the form as row filters. One it cannot say is carried as it came."""
        from xgen_space.check import _find_prop

        onto, out = self.composed().ontology, {}
        for r in rows:
            t = str(r.get("type") or "")
            if t not in onto.objects:
                raise EditError(f"object type '{t}' is unknown")
            if r.get("raw"):
                out[t] = r["raw"]
                continue
            who = {"principal": str(r["principal"])} if r.get("principal") else r.get("value")
            if who in (None, ""):
                raise EditError(f"{t}: say what the rows are compared with")
            via = [str(x) for x in r.get("via") or [] if x]
            spec = _scope_filter(onto, {"via": via, "property": str(r.get("property") or "")}, "", who)
            if spec is None:
                raise EditError(f"{t}: the row rule does not reach a property")
            here = t
            for step in via:
                lk = onto.links.get(step) or onto.link_by_inverse(step)
                if lk is None:
                    raise EditError(f"link '{step}' is unknown")
                here = lk.target if lk.name == step else lk.source
            if _find_prop(onto, here, str(r.get("property") or "")) is None:
                raise EditError(f"{here} has no property '{r.get('property')}'")
            out[t] = spec
        return out

    def _scope(self, scope: dict) -> dict:
        """An organisation's scope from the form: the signed-in attribute and where each type holds it."""
        types: dict[str, Any] = {}
        for r in scope.get("types") or []:
            via = [str(x) for x in r.get("via") or [] if x]
            types[str(r.get("type"))] = {"via": via, "property": str(r.get("property"))} if via else str(r.get("property"))
        return {"attribute": str(scope.get("attribute") or ""), "types": types}

    def _update_role(self, a: dict) -> str:
        name = str(a.get("name") or "")
        r = self.composed().ontology.roles.get(name)
        if r is None:
            raise EditError(f"role '{name}' is unknown")
        rows = self._rows(a["rows"]) if "rows" in a else None
        scope = self._scope(a["scope"]) if (a.get("scope") or {}).get("attribute") else ({} if "scope" in a else None)
        if self._owns("roles", name):
            spec = self._section("body", "roles")[name]
            spec.update({k: a[k] for k in ("label", "read", "run", "request", "execute", "mask") if k in a})
            if rows is not None:
                spec["row_filters"] = rows
            if scope is not None:
                spec["scope"] = scope
            if "documents" in a:
                if a["documents"] is None:
                    spec.pop("documents", None)
                else:
                    spec["documents"] = self._documents(a["documents"])
            for k in ("row_filters", "scope"):
                if not spec.get(k):
                    spec.pop(k, None)
            return f"role:{name}"
        patch = self._section("extend", "roles").setdefault(name, {})
        if rows is not None:
            patch["row_filters"] = {t: v for t, v in rows.items() if r.row_filters.get(t) != v}
            patch["row_filters_drop"] = [t for t in r.row_filters if t not in rows]
        if scope is not None and scope != r.scope:
            patch["scope_set"] = scope
        if "documents" in a:
            want = None if a["documents"] is None else self._documents(a["documents"])
            if want != r.documents:
                patch["documents_set"] = want
            else:
                patch.pop("documents_set", None)
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
        for k in [k for k, v in patch.items() if v in ([], {}) and k != "documents_set"]:
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
        for section, kind in (("decisions", "decision"), ("actions", "action"), ("roles", "role"), ("parameters", "parameter"),
                              ("metrics", "metric"), ("identities", "identity"), ("functions", "function")):
            owners |= {comp.owner(f"{kind}:{k}") for k in self.module.extend.get(section) or {}}
        for section in ("decisions", "actions", "functions"):
            owners |= {comp.owner(f"object:{spec.get('target')}") for spec in (self.module.body.get(section) or {}).values()}
        for spec in (self.module.body.get("metrics") or {}).values():
            owners |= {comp.owner(f"object:{t}") for t in ((spec.get("formula") or {}).get("match") or {}).values()}
        for spec in (self.module.body.get("identities") or {}).values():
            owners |= {comp.owner(f"object:{t}") for t in spec.get("members") or {}}
        for s, items in self.module.remove.items():
            if s == "properties":
                owners |= {comp.owner(f"property:{t}.{p}") for t, ps in items.items() for p in ps}
            elif s == "questions":
                owners |= {comp.owner(f"question:{q}") for q in items}
            elif s == "states":
                owners |= {comp.owner(f"object:{t}") for t in items}
            else:
                kind = {"objects": "object", "links": "link", "queries": "query", "decisions": "decision",
                        "actions": "action", "identities": "identity", "parameters": "parameter", "metrics": "metric",
                        "functions": "function", "roles": "role"}.get(s, s)
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


def row_rule(type_name: str, spec: dict) -> dict:
    """A row filter as the form reads it. One it cannot say comes back as it is, to be kept."""
    def side(who: Any) -> dict | None:
        if isinstance(who, dict):
            return {"principal": who["principal"]} if set(who) == {"principal"} else None
        return {"value": who}

    if set(spec) == {"eq"} and str(spec["eq"][0]).startswith("$self.") and side(spec["eq"][1]):
        return {"type": type_name, "via": [], "property": spec["eq"][0].split(".", 1)[1], **side(spec["eq"][1])}
    body = spec.get("exists") if set(spec) == {"exists"} else None
    if body and set((body.get("where") or {})) == {"eq"}:
        ref, who = body["where"]["eq"]
        edges, here, via = body.get("edges") or [], "$self", []
        for e in edges:
            if len(e) != 3 or e[0] != here:
                return {"type": type_name, "raw": spec}
            via.append(e[1])
            here = e[2]
        if str(ref).startswith(f"{here}.") and side(who):
            return {"type": type_name, "via": via, "property": str(ref).split(".", 1)[1], **side(who)}
    return {"type": type_name, "raw": spec}


def _removals(d: dict) -> set[str]:
    """The elements a module dict takes out, as element ids (object:Claim, property:Customer.spent, ...)."""
    out: set[str] = set()
    kinds = {"objects": "object", "links": "link", "queries": "query", "decisions": "decision", "actions": "action",
             "identities": "identity", "questions": "question", "states": "states", "roles": "role",
             "interfaces": "interface", "parameters": "parameter", "metrics": "metric", "functions": "function"}
    for s, items in (d.get("remove") or {}).items():
        if s == "properties":
            out |= {f"property:{t}.{p}" for t, ps in (items or {}).items() for p in ps}
        else:
            out |= {f"{kinds.get(s, s)}:{k}" for k in items or []}
    return out


def _known_type(a: dict) -> None:
    if a.get("type") and a["type"] not in TYPES:
        raise EditError(f"type '{a['type']}' is not one of {', '.join(TYPES)}")


def _prop_spec(a: dict) -> dict:
    spec = {"type": str(a.get("type") or "string")}
    for k in ("label", "description", "column", "unit", "expr", "mask", "cite", "transform", "source_type"):
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
