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

from xgen_data_studio.modules import Module, ModuleError, Requirement, compose, settle

NAME = "workspace"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PROP_FIELDS = ("label", "description", "type", "column", "unit", "values", "required", "mask", "expr", "cite")
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

    def __init__(self, base: list[Module], current: Module | None = None, *, label: str = "내 변경",
                 compose_kw: dict | None = None):
        self.base, self.kw = [m for m in base if m.name != NAME], dict(compose_kw or {})
        self.current = current
        start = copy.deepcopy(current.to_dict()) if current else {"module": NAME, "version": "0.1.0",
                                                                   "kind": "customer", "label": label}
        start.setdefault("description", "관리 화면(객체 · 속성 · 관계 · 검증 질문)에서 바꾼 내용입니다. 표준 모듈은 그대로 두고 확장 · 제외로 얹습니다.")
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
    if a.get("values"):
        spec["values"] = [str(v) for v in a["values"]]
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
