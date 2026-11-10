"""Ontology modules: domain knowledge packaged to plug into a composition and to unplug from it again."""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from xgen_space.model import Ontology

# quality: how a definition is checked (questions and the flow's pass conditions); method: how a draft is built from
# data (the draft rules). Both plug in and out like the rest.
KINDS = ("core", "domain", "industry", "customer", "binding", "quality", "method", "dictionary")
SECTIONS = ("interfaces", "areas", "objects", "links", "decisions", "actions", "roles", "queries", "identities",
            "parameters", "metrics", "conflicts", "functions")
SINGULAR = {"interfaces": "interface", "areas": "area", "objects": "object", "links": "link", "decisions": "decision",
            "actions": "action", "roles": "role", "queries": "query", "identities": "identity",
            "parameters": "parameter", "metrics": "metric", "conflicts": "conflict", "functions": "function"}
_REQ = re.compile(r"^\s*([A-Za-z0-9_.-]+?)\s*(?:(@|>=|==)\s*([0-9][0-9A-Za-z.\-]*))?\s*$")


class ModuleError(ValueError):
    """Modules do not fit together: a missing requirement, a conflict, or a reference left dangling."""


def version_key(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"[.\-]", v))


@dataclass(frozen=True)
class Requirement:
    name: str
    op: str = ""
    version: str = ""

    @classmethod
    def parse(cls, text: str) -> Requirement:
        m = _REQ.match(text)
        if not m:
            raise ModuleError(f"cannot read requirement '{text}'; write name, name@1.0.0 or name>=1.0")
        return cls(m.group(1), m.group(2) or "", m.group(3) or "")

    def allows(self, version: str) -> bool:
        if not self.op:
            return True
        if self.op in ("@", "=="):
            return version == self.version or version.startswith(self.version + ".")
        return version_key(version) >= version_key(self.version)

    def __str__(self) -> str:
        return f"{self.name}{self.op}{self.version}"


@dataclass
class Module:
    name: str
    version: str = "0.1.0"
    kind: str = "domain"
    label: str = ""
    description: str = ""
    namespace: str = ""
    requires: list[Requirement] = field(default_factory=list)
    body: dict[str, Any] = field(default_factory=dict)
    extend: dict[str, Any] = field(default_factory=dict)
    remove: dict[str, Any] = field(default_factory=dict)
    flow: dict[str, Any] = field(default_factory=dict)  # {gates: {stage: {condition: value}}}, held to the stricter
    draft_rules: dict[str, Any] = field(default_factory=dict)  # what a draft decides by (draft.DraftRules)
    terms: list[dict] = field(default_factory=list)  # {term, synonyms, avoid, definition, ...}: a system's words
    messages: list[dict] = field(default_factory=list)  # {code, text, kind, screen}: what a system says

    @property
    def key(self) -> str:
        return f"{self.name}@{self.version}"

    @classmethod
    def from_dict(cls, d: dict) -> Module:
        if d.get("kind", "domain") not in KINDS:
            raise ModuleError(f"module {d.get('module')}: kind must be one of {KINDS}")
        body = {s: copy.deepcopy(d.get(s) or {}) for s in SECTIONS}
        body["questions"] = copy.deepcopy(d.get("questions") or [])
        body["exclusive"] = copy.deepcopy(d.get("exclusive") or [])
        return cls(name=d["module"], version=str(d.get("version", "0.1.0")), kind=d.get("kind", "domain"),
                   label=d.get("label", ""), description=d.get("description", ""), namespace=d.get("namespace", ""),
                   requires=[Requirement.parse(r) for r in d.get("requires", [])], body=body,
                   extend=copy.deepcopy(d.get("extend") or {}), remove=copy.deepcopy(d.get("remove") or {}),
                   flow=copy.deepcopy(d.get("flow") or {}), draft_rules=copy.deepcopy(d.get("draft_rules") or {}),
                   terms=copy.deepcopy(d.get("terms") or []), messages=copy.deepcopy(d.get("messages") or []))

    def to_dict(self) -> dict:
        out: dict[str, Any] = {"module": self.name, "version": self.version, "kind": self.kind}
        for k in ("label", "description", "namespace"):
            if getattr(self, k):
                out[k] = getattr(self, k)
        if self.requires:
            out["requires"] = [str(r) for r in self.requires]
        for s in (*SECTIONS, "questions", "exclusive"):
            if self.body.get(s):
                out[s] = copy.deepcopy(self.body[s])
        if self.extend:
            out["extend"] = copy.deepcopy(self.extend)
        if self.remove:
            out["remove"] = copy.deepcopy(self.remove)
        for k in ("flow", "draft_rules", "terms", "messages"):
            if getattr(self, k):
                out[k] = copy.deepcopy(getattr(self, k))
        return out

    @classmethod
    def load(cls, path: str | Path) -> Module:
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() in (".yaml", ".yml"):
            import yaml

            return cls.from_dict(yaml.safe_load(text))
        return cls.from_dict(json.loads(text))

    def dump(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() in (".yaml", ".yml"):
            import yaml

            p.write_text(yaml.safe_dump(self.to_dict(), allow_unicode=True, sort_keys=False), encoding="utf-8")
        else:
            p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def elements(self) -> list[str]:
        """Ids of what this module defines, extends or removes."""
        out = []
        for s in SECTIONS:
            for k, v in self.body.get(s, {}).items():
                out.append(f"{SINGULAR[s]}:{k}")
                if s == "objects":
                    out += [f"property:{k}.{p}" for p in (v.get("properties") or {})]
        for s, items in self.extend.items():
            for k, v in (items or {}).items():
                out.append(f"{SINGULAR.get(s, s)}:{k}")
                if s == "objects":
                    out += [f"property:{k}.{p}" for p in ((v or {}).get("properties") or {})]
        out += [f"question:{q['id']}" for q in self.body.get("questions", [])]
        return out

    def counts(self) -> dict[str, int]:
        c = {s: len(self.body.get(s, {})) for s in SECTIONS}
        c["properties"] = sum(len((v.get("properties") or {})) for v in self.body.get("objects", {}).values())
        c["questions"] = len(self.body.get("questions", []))
        c["extends"] = sum(len(v or {}) for v in self.extend.values())
        c["gates"] = sum(len(v or {}) for v in (self.flow.get("gates") or {}).values())
        c["draft_rules"] = len(self.draft_rules)
        c["terms"] = len(self.terms)
        c["messages"] = len(self.messages)
        return c


@dataclass
class Composition:
    ontology: Ontology
    modules: list[Module]
    origin: dict[str, str]
    touched: dict[str, list[str]]
    removed: dict[str, str]
    issues: list[str]
    gates: dict[str, dict[str, float]] = field(default_factory=dict)  # the modules' pass conditions, strictest kept
    gate_by: dict[str, str] = field(default_factory=dict)  # "stage.condition" -> the module that set it
    draft_rules: dict[str, Any] = field(default_factory=dict)  # the modules' draft rules, later modules last
    rules_by: list[str] = field(default_factory=list)  # the modules that gave draft rules
    terms: list[dict] = field(default_factory=list)  # the dictionary modules' words
    messages: list[dict] = field(default_factory=list)  # the dictionary modules' messages
    findings: list = field(default_factory=list)  # what the decision tables say twice or leave open (decide.checks)
    conflicts: list = field(default_factory=list)  # where two sources answer one input differently (decide.conflicts)

    def owner(self, element: str) -> str:
        return self.origin.get(element, "")

    def by_module(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {m.name: [] for m in self.modules}
        for e, m in self.origin.items():
            out.setdefault(m, []).append(e)
        for e, ms in self.touched.items():
            for m in ms:
                out.setdefault(m, []).append(e)
        return {m: sorted(set(v)) for m, v in out.items()}

    def summary(self) -> list[dict]:
        rows = self.by_module()
        return [{"module": m.name, "version": m.version, "kind": m.kind, "label": m.label,
                 "requires": [str(r) for r in m.requires], "elements": len(rows.get(m.name, []))}
                for m in self.modules]


def order(modules: list[Module]) -> list[Module]:
    by = {}
    for m in modules:
        if m.name in by:
            raise ModuleError(f"module '{m.name}' is listed twice ({by[m.name].version}, {m.version})")
        by[m.name] = m
    for m in modules:
        for r in m.requires:
            dep = by.get(r.name)
            if dep is None:
                raise ModuleError(f"{m.key} requires '{r}', which is not attached")
            if not r.allows(dep.version):
                raise ModuleError(f"{m.key} requires '{r}', but {dep.key} is attached")
    out, state = [], {}

    def visit(m: Module, path: list[str]) -> None:
        if state.get(m.name) == "done":
            return
        if state.get(m.name) == "open":
            raise ModuleError(f"modules require each other in a cycle: {' -> '.join(path + [m.name])}")
        state[m.name] = "open"
        for r in m.requires:
            visit(by[r.name], path + [m.name])
        state[m.name] = "done"
        out.append(m)

    for m in modules:
        visit(m, [])
    return out


def _props_of(acc: dict, type_name: str) -> dict:
    """The property definitions a type sees, own first, then up its parent chain."""
    out, t, seen = {}, type_name, set()
    while t and t in acc["objects"] and t not in seen:
        seen.add(t)
        for k, v in (acc["objects"][t].get("properties") or {}).items():
            out.setdefault(k, v)
        t = acc["objects"][t].get("parent", "")
    return out


def _as_prop(v: Any) -> dict:
    return {"type": v} if isinstance(v, str) else dict(v or {})


def _extend_object(acc: dict, m: Module, name: str, patch: dict, touched: dict, origin: dict) -> None:
    obj = acc["objects"].get(name)
    if obj is None:
        raise ModuleError(f"{m.key} extends object type '{name}', which no attached module defines")
    for k in ("label", "description", "title", "parent", "cite", "series", "period", "view", "status", "area"):
        if k in patch:
            obj[k] = copy.deepcopy(patch[k])
    if "table" in patch or "source" in patch:
        obj["source"] = {"table": patch.get("table") or (patch.get("source") or {}).get("table", "")}
    for k in ("aligned", "implements"):
        if patch.get(k):
            obj[k] = list(dict.fromkeys(list(obj.get(k) or []) + list(patch[k])))
    if patch.get("implements_drop"):
        obj["implements"] = [i for i in obj.get("implements") or [] if i not in patch["implements_drop"]]
    props = obj.setdefault("properties", {})
    for p, pd in (patch.get("properties") or {}).items():
        pd = _as_prop(pd)
        if p in props:
            cur = _as_prop(props[p])
        elif p in _props_of(acc, name):
            cur = copy.deepcopy(_as_prop(_props_of(acc, name)[p]))
        else:
            if "type" not in pd and "values_add" not in pd:
                pd.setdefault("type", "string")
            cur = {}
            origin[f"property:{name}.{p}"] = m.name
        text_date = cur.get("type") == "string" and pd.get("format")  # text a binding says holds a date
        if "type" in pd and cur.get("type") and pd["type"] != cur["type"] and not text_date:
            raise ModuleError(f"{m.key} changes the type of {name}.{p} from {cur['type']} to {pd['type']}")
        add = pd.pop("values_add", [])
        names = pd.pop("labels", None)
        if isinstance(pd.get("values"), dict) or isinstance(add, dict):  # {code: name}: the values and their names
            got = {**(pd["values"] if isinstance(pd.get("values"), dict) else {}), **(add if isinstance(add, dict)
                                                                                     else {})}
            names = {**{str(k): v for k, v in got.items() if v not in (None, "")}, **(names or {})}
            if isinstance(pd.get("values"), dict):
                pd["values"] = [str(k) for k in pd["values"]]
            if isinstance(add, dict):
                add = [str(k) for k in add]
        if isinstance(cur.get("values"), dict):
            cur["labels"] = {**{str(k): v for k, v in cur["values"].items() if v not in (None, "")},
                             **(cur.get("labels") or {})}
            cur["values"] = [str(k) for k in cur["values"]]
        cur.update(pd)
        if add:
            cur["values"] = list(dict.fromkeys(list(cur.get("values") or []) + list(add)))
        if names:  # a value's name is added to the names already given, not in place of them
            cur["labels"] = {**(cur.get("labels") or {}), **{str(k): str(v) for k, v in names.items()}}
        props[p] = cur
        touched.setdefault(f"property:{name}.{p}", []).append(m.name)
    for p, col in (patch.get("columns") or {}).items():
        base = props.get(p)
        if base is None:
            inherited = _props_of(acc, name).get(p)
            if inherited is None:
                raise ModuleError(f"{m.key} binds {name}.{p}, which is not a property of {name}")
            base = copy.deepcopy(_as_prop(inherited))
        base = _as_prop(base)
        if isinstance(col, list):  # a key read from several columns of this system
            base.pop("column", None)
            base["columns"] = list(col)
        else:
            base.pop("columns", None)
            base["column"] = col
        props[p] = base
        touched.setdefault(f"property:{name}.{p}", []).append(m.name)
    if patch.get("states_set"):  # the whole machine, from the screen that edits it
        obj["states"] = copy.deepcopy(patch["states_set"])
    if patch.get("transitions_add"):
        sm = obj.get("states")
        if not sm:
            raise ModuleError(f"{m.key} adds transitions to {name}, which has no state machine")
        sm["transitions"] = list(sm.get("transitions") or []) + list(patch["transitions_add"])
        for tr in patch["transitions_add"]:
            for s in (tr.get("from"), tr.get("to")):
                if s and s not in sm["states"]:
                    sm["states"].append(s)
    touched.setdefault(f"object:{name}", []).append(m.name)


def _extend_link(acc: dict, m: Module, name: str, patch: dict, touched: dict) -> None:
    lk = acc["links"].get(name)
    if lk is None:
        raise ModuleError(f"{m.key} extends link '{name}', which no attached module defines")
    for k in ("on", "via", "label", "description", "cite", "required", "inverse", "cardinality", "status"):
        if k in patch:
            lk[k] = copy.deepcopy(patch[k])
    if True in patch:
        lk["on"] = copy.deepcopy(patch[True])
    if patch.get("aligned"):
        lk["aligned"] = list(dict.fromkeys(list(lk.get("aligned") or []) + list(patch["aligned"])))
    touched.setdefault(f"link:{name}", []).append(m.name)


def _extend_decision(acc: dict, m: Module, name: str, patch: dict, touched: dict) -> None:
    d = acc["decisions"].get(name)
    if d is None:
        raise ModuleError(f"{m.key} extends decision '{name}', which no attached module defines")
    d.setdefault("inputs", {}).update(copy.deepcopy(patch.get("inputs") or {}))
    d.setdefault("outputs", {}).update(copy.deepcopy(patch.get("outputs") or {}))
    gone, changed = set(patch.get("rules_remove") or []), dict(patch.get("rules_replace") or {})
    known = {r.get("id") for r in d.get("rules") or []}
    missing = sorted((gone | set(changed)) - known)
    if missing:
        raise ModuleError(f"{m.key} changes rule '{missing[0]}' of decision '{name}', which it does not have")
    rules = [copy.deepcopy(changed.get(r.get("id"), r)) for r in d.get("rules") or [] if r.get("id") not in gone]
    d["rules"] = copy.deepcopy(list(patch.get("rules_prepend") or [])) + rules + \
        copy.deepcopy(list(patch.get("rules_append") or []))
    for k in ("label", "cite", "hit_policy"):
        if k in patch:
            d[k] = patch[k]
    touched.setdefault(f"decision:{name}", []).append(m.name)


def _extend_role(acc: dict, m: Module, name: str, patch: dict, touched: dict) -> None:
    r = acc["roles"].get(name)
    if r is None:
        raise ModuleError(f"{m.key} extends role '{name}', which no attached module defines")
    if "label" in patch:
        r["label"] = patch["label"]
    for k in ("read", "run", "request", "execute", "unmask"):
        if patch.get(k):
            r[k] = list(dict.fromkeys(list(r.get(k) or []) + list(patch[k])))
        if patch.get(f"{k}_drop"):
            r[k] = [x for x in r.get(k) or [] if x not in patch[f"{k}_drop"]]
    if patch.get("row_filters"):
        r.setdefault("row_filters", {}).update(copy.deepcopy(patch["row_filters"]))
    if patch.get("scope"):
        scope = r.setdefault("scope", {})
        scope.update({k: copy.deepcopy(v) for k, v in patch["scope"].items() if k != "types"})
        scope.setdefault("types", {}).update(copy.deepcopy(patch["scope"].get("types") or {}))
    if "scope_set" in patch:  # the whole scope, from the screen that edits it
        if patch["scope_set"]:
            r["scope"] = copy.deepcopy(patch["scope_set"])
        else:
            r.pop("scope", None)
    if patch.get("mask"):
        mask = patch["mask"]
        cur = r.get("mask") or {}
        cur = {x: "partial" for x in cur} if isinstance(cur, list) else dict(cur)
        cur.update({x: "partial" for x in mask} if isinstance(mask, list) else mask)
        r["mask"] = cur
    if patch.get("mask_drop"):
        cur = r.get("mask") or {}
        cur = {x: "partial" for x in cur} if isinstance(cur, list) else dict(cur)
        r["mask"] = {k: v for k, v in cur.items() if k not in patch["mask_drop"]}
    for t in patch.get("row_filters_drop") or []:
        (r.get("row_filters") or {}).pop(t, None)
    if r.get("documents") is not None:  # a role that reads every document has no list to add to or take from
        if patch.get("documents"):
            r["documents"] = list(dict.fromkeys([*r["documents"], *patch["documents"]]))
        if patch.get("documents_drop"):
            r["documents"] = [x for x in r["documents"] if x not in patch["documents_drop"]]
    if "documents_set" in patch:  # the whole list, from the screen that edits it; null reads every document
        if patch["documents_set"] is None:
            r.pop("documents", None)
        else:
            r["documents"] = list(patch["documents_set"])
    touched.setdefault(f"role:{name}", []).append(m.name)


def _extend_action(acc: dict, m: Module, name: str, patch: dict, touched: dict) -> None:
    a = acc["actions"].get(name)
    if a is None:
        raise ModuleError(f"{m.key} extends action '{name}', which no attached module defines")
    for k in ("label", "parameters", "criteria", "set", "transition_to", "approval", "cite", "call", "undo"):
        if k in patch:
            a[k] = copy.deepcopy(patch[k])
    touched.setdefault(f"action:{name}", []).append(m.name)


def _extend_parameter(acc: dict, m: Module, name: str, patch: Any, touched: dict) -> None:
    if name not in acc["parameters"]:
        raise ModuleError(f"{m.key} extends parameter '{name}', which no attached module defines")
    patch = dict(patch) if isinstance(patch, dict) else {"value": patch}  # return_window_days: 30 is enough
    cur = acc["parameters"][name]
    cur = dict(cur) if isinstance(cur, dict) else {"value": cur}
    if "type" in patch and "type" in cur and patch["type"] != cur["type"]:
        raise ModuleError(f"{m.key} changes the type of parameter {name} from {cur['type']} to {patch['type']}")
    acc["parameters"][name] = {**cur, **copy.deepcopy(patch)}
    touched.setdefault(f"parameter:{name}", []).append(m.name)


def _extend_entry(acc: dict, m: Module, section: str, name: str, patch: dict, touched: dict) -> None:
    """A metric, a conflict, a function or an area takes what the patch gives; a customer redefines one or picks in
    one."""
    kind = SINGULAR[section]
    if name not in acc[section]:
        raise ModuleError(f"{m.key} extends {kind} '{name}', which no attached module defines")
    acc[section][name].update(copy.deepcopy(patch))
    touched.setdefault(f"{kind}:{name}", []).append(m.name)


def compose(modules: list[Module], *, name: str = "", namespace: str = "", version: str = "",
            label: str = "") -> Composition:
    """Apply modules in requirement order: define, then extend, then remove; record who did what."""
    ordered = order(modules)
    acc: dict[str, Any] = {s: {} for s in SECTIONS}
    acc["questions"], acc["exclusive"] = [], []
    origin: dict[str, str] = {}
    touched: dict[str, list[str]] = {}
    removed: dict[str, str] = {}
    for m in ordered:
        for s in SECTIONS:
            for k, v in (m.body.get(s) or {}).items():
                eid = f"{SINGULAR[s]}:{k}"
                if k in acc[s]:
                    if acc[s][k] == v:
                        continue
                    raise ModuleError(f"{m.key} defines {SINGULAR[s]} '{k}', already defined by {origin[eid]}; "
                                      "extend it instead")
                acc[s][k] = copy.deepcopy(v)
                origin[eid] = m.name
                if s == "objects":
                    for p in (v.get("properties") or {}):
                        origin[f"property:{k}.{p}"] = m.name
        for q in m.body.get("questions") or []:
            acc["questions"].append(copy.deepcopy(q))
            origin[f"question:{q['id']}"] = m.name
        acc["exclusive"] += copy.deepcopy(m.body.get("exclusive") or [])
        for s, items in (m.extend or {}).items():
            for k, patch in (items or {}).items():
                if s == "objects":
                    _extend_object(acc, m, k, patch or {}, touched, origin)
                elif s == "links":
                    _extend_link(acc, m, k, patch or {}, touched)
                elif s == "decisions":
                    _extend_decision(acc, m, k, patch or {}, touched)
                elif s == "roles":
                    _extend_role(acc, m, k, patch or {}, touched)
                elif s == "actions":
                    _extend_action(acc, m, k, patch or {}, touched)
                elif s == "parameters":
                    _extend_parameter(acc, m, k, patch, touched)
                elif s in ("metrics", "conflicts", "functions", "identities", "areas"):
                    _extend_entry(acc, m, s, k, patch or {}, touched)
                else:
                    raise ModuleError(f"{m.key}: cannot extend '{s}'; extend objects, links, decisions, actions, roles, "
                                      "parameters, metrics, conflicts, functions, identities or areas")
        for s, items in (m.remove or {}).items():
            if s == "properties":
                for t, props in (items or {}).items():
                    for p in props:
                        if p not in (acc["objects"].get(t, {}).get("properties") or {}):
                            raise ModuleError(f"{m.key} removes {t}.{p}, which is not there")
                        del acc["objects"][t]["properties"][p]
                        removed[f"property:{t}.{p}"] = m.name
                        _forget_in_roles(acc, prop=f"{t}.{p}")
                continue
            if s == "questions":
                own = {q.get("id") for q in m.body.get("questions") or []}  # one it takes over and writes itself stays
                last = {q["id"]: i for i, q in enumerate(acc["questions"])}
                acc["questions"] = [q for i, q in enumerate(acc["questions"]) if q["id"] not in items or (q["id"] in own and last[q["id"]] == i)]
                removed.update({f"question:{q}": m.name for q in items})
                continue
            if s == "states":  # a type's state machine, when the source has no state column
                for t in items:
                    if not (acc["objects"].get(t) or {}).get("states"):
                        raise ModuleError(f"{m.key} removes the states of {t}, which has none")
                    del acc["objects"][t]["states"]
                    removed[f"states:{t}"] = m.name
                continue
            if s not in SECTIONS:
                raise ModuleError(f"{m.key}: cannot remove '{s}'")
            for k in items:
                if k not in acc[s]:
                    raise ModuleError(f"{m.key} removes {SINGULAR[s]} '{k}', which is not there")
                del acc[s][k]
                removed[f"{SINGULAR[s]}:{k}"] = m.name
                if s == "objects":
                    for e in [e for e in origin if e.startswith(f"property:{k}.")]:
                        removed[e] = m.name
                    _forget_in_roles(acc, type_name=k)
                if s == "actions":  # a role cannot keep the right to an action that is gone
                    for r in acc["roles"].values():
                        for grant in ("request", "execute"):
                            if k in (r.get(grant) or []):
                                r[grant] = [x for x in r[grant] if x != k]
    for obj in acc["objects"].values():  # an area that is not attached (or was removed) leaves its types unclassified
        if obj.get("area") and obj["area"] not in acc["areas"]:
            del obj["area"]
    namespace = namespace or next((m.namespace for m in reversed(ordered) if m.namespace), "")
    if not namespace:
        raise ModuleError("no namespace: give one, or set it on a module")
    domains = [m.name for m in ordered if m.kind == "domain"] or [m.name for m in ordered]
    d = {"ontology": name or "+".join(domains), "namespace": namespace,
         "version": version or " ".join(m.key for m in ordered),
         "label": label or " + ".join(m.label or m.name for m in ordered if m.kind in ("domain", "industry")), **acc}
    onto = Ontology.from_dict(d)
    for iname, ident in onto.identities.items():  # the object and links an identity expands into are its module's
        who = origin.get(f"identity:{iname}")
        if who:
            origin.setdefault(f"object:{iname}", who)
            for p in onto.objects[iname].properties:
                origin.setdefault(f"property:{iname}.{p}", who)
            for member in ident.members:
                origin.setdefault(f"link:{ident.link_name(member)}", who)
    for e in list(removed):
        origin.pop(e, None)
        touched.pop(e, None)
    gates, gate_by, rules, rules_by = _methods(ordered)
    return Composition(onto, ordered, origin, touched, removed, onto.validate(), gates, gate_by, rules, rules_by,
                       [t for m in ordered for t in m.terms], [x for m in ordered for x in m.messages],
                       onto.findings(), onto.source_conflicts())


def _forget_in_roles(acc: dict, *, type_name: str = "", prop: str = "") -> None:
    """A role cannot keep reading, filtering or masking a type or a property that is gone."""
    for r in acc["roles"].values():
        if type_name:
            r["read"] = [x for x in r.get("read") or [] if x != type_name]
            (r.get("row_filters") or {}).pop(type_name, None)
            # a property that goes stays named: validate refuses it, where dropping it would open the rows
            ((r.get("scope") or {}).get("types") or {}).pop(type_name, None)
        gone = (lambda ref: ref.startswith(f"{type_name}.")) if type_name else (lambda ref: ref == prop)
        if isinstance(r.get("mask"), dict):
            r["mask"] = {k: v for k, v in r["mask"].items() if not gone(k)}
        elif isinstance(r.get("mask"), list):
            r["mask"] = [k for k in r["mask"] if not gone(k)]
        r["unmask"] = [k for k in r.get("unmask") or [] if not gone(k)]


def settle(module: Module, base: list[Module], **compose_kw) -> list[str]:
    """Take out of `module`'s reach what its removals leave broken in `base` (a query on a removed property, a
    decision reading it, a link to a removed type, a state machine without its column), so the composition holds
    again; what the module defines itself is left for a person to fix. Returns the elements it took out."""
    taken: list[str] = []
    own = {f"{SINGULAR[s]}:{k}" for s in SECTIONS for k in (module.body.get(s) or {})}
    own |= {f"question:{q.get('id')}" for q in module.body.get("questions") or []}
    for _ in range(30):
        comp = compose([*base, module], **compose_kw)
        progress = False
        for issue in comp.issues:
            head = issue.split(":", 1)[0]
            kind, _, ident = head.partition(" ")
            section = {"query": "queries", "question": "questions", "decision": "decisions", "action": "actions",
                       "link": "links", "identity": "identities", "metric": "metrics",
                       "conflict": "conflicts", "function": "functions"}.get(kind)
            if kind == "decision":
                ident = ident.split(".", 1)[0].split(" ", 1)[0]  # an input's or a rule's issue: the decision cannot be fed
            if section and f"{SINGULAR.get(section, 'question')}:{ident}" not in own:
                if ident not in module.remove.get(section, []):
                    module.remove.setdefault(section, []).append(ident)
                    taken.append(f"{SINGULAR.get(section, 'question')}:{ident}")
                    progress = True
            elif head in comp.ontology.objects and f"object:{head}" not in own and ": series " in issue:
                patch = module.extend.setdefault("objects", {}).setdefault(head, {})
                if patch.get("series") != {}:
                    patch["series"] = {}
                    progress = True
            elif head in comp.ontology.objects and f"object:{head}" not in own and (
                    drop := re.match(r"\S+: (?:title '[^']*' is not a property|implements (\S+) but lacks )", issue)):
                patch = module.extend.setdefault("objects", {}).setdefault(head, {})
                if drop.group(1):  # what its properties no longer fill: a title, an interface
                    if drop.group(1) not in patch.setdefault("implements_drop", []):
                        patch["implements_drop"].append(drop.group(1))
                        progress = True
                elif patch.get("title") != "":
                    patch["title"] = ""
                    progress = True
            elif head in comp.ontology.objects and "state property" in issue and f"object:{head}" not in own:
                if head not in module.remove.get("states", []):
                    module.remove.setdefault("states", []).append(head)
                    taken.append(f"states:{head}")
                    progress = True
            elif "." in head and " " not in head and f"object:{head.split('.', 1)[0]}" not in own:
                t, prop = head.split(".", 1)
                props = module.remove.setdefault("properties", {}).setdefault(t, [])
                if prop not in props:
                    props.append(prop)
                    taken.append(f"property:{t}.{prop}")
                    progress = True
        if not progress:
            break
    gone = set(module.remove.get("queries", [])) | set(module.remove.get("decisions", []))
    for q in compose(base, **compose_kw).ontology.questions:  # a question on what is gone goes with it
        if (q.query in gone or q.decision in gone) and q.id not in module.remove.get("questions", []):
            module.remove.setdefault("questions", []).append(q.id)
            taken.append(f"question:{q.id}")
    return taken


def _methods(ordered: list[Module]) -> tuple[dict, dict, dict, list]:
    """The pass conditions (the strictest of each) and the draft rules (later modules last) the modules carry."""
    from dataclasses import fields

    from xgen_space.draft import DraftRules
    from xgen_space.review import FlowSettings, tighter

    gates: dict[str, dict[str, float]] = {}
    gate_by: dict[str, str] = {}
    rules: dict[str, Any] = {}
    rules_by: list[str] = []
    known = {f.name for f in fields(DraftRules)}
    for m in ordered:
        extra = set(m.flow) - {"gates"}
        if extra:
            raise ModuleError(f"{m.key}: a module's flow gives only gates, not {sorted(extra)}")
        given = {s: dict(c or {}) for s, c in (m.flow.get("gates") or {}).items()}
        bad = FlowSettings(gates=given).issues()
        if bad:
            raise ModuleError(f"{m.key} flow: " + "; ".join(bad))
        for stage, conds in given.items():
            for cond, v in conds.items():
                cur = gates.get(stage, {}).get(cond)
                if v is not None and (cur is None or tighter(cond, v, cur)):
                    gates.setdefault(stage, {})[cond] = v
                    gate_by[f"{stage}.{cond}"] = m.name
        unknown = set(m.draft_rules) - known
        if unknown:
            raise ModuleError(f"{m.key}: unknown draft rules {sorted(unknown)}; use {sorted(known)}")
        if m.draft_rules:
            rules.update(copy.deepcopy(m.draft_rules))
            rules_by.append(m.name)
    return gates, gate_by, rules, rules_by


@dataclass
class Impact:
    module: str
    dependents: list[str]
    removed: list[str]
    changed: list[str]
    broken: list[str]

    @property
    def ok(self) -> bool:
        return not self.broken

    def to_dict(self) -> dict:
        return {"module": self.module, "dependents": self.dependents, "removed": self.removed,
                "changed": self.changed, "broken": self.broken, "ok": self.ok}


def dependents_of(modules: list[Module], name: str) -> list[str]:
    out, frontier = [], {name}
    while frontier:
        nxt = {m.name for m in modules if m.name not in out and m.name not in frontier
               and any(r.name in frontier for r in m.requires)}
        out += sorted(nxt - set(out))
        frontier = nxt
    return out


def removal_impact(modules: list[Module], module: str, *, cascade: bool = False, **kw) -> Impact:
    """What unplugging a module takes away, and what it would leave pointing at nothing."""
    name = module
    if name not in {m.name for m in modules}:
        raise ModuleError(f"module '{name}' is not attached")
    deps = dependents_of(modules, name)
    full = compose(modules, **kw)
    gone = {name, *deps} if cascade or not deps else {name}
    rest = [m for m in modules if m.name not in gone]
    need = f"{', '.join(deps)} require {name}; detach them too (cascade) or keep {name}"
    try:
        reduced = compose(rest, **kw) if rest else None
    except ModuleError as e:
        return Impact(name, deps, [], [], ([need] if deps and not cascade else []) + [str(e)])
    if reduced is None:
        return Impact(name, deps, sorted(full.origin), [], [])
    removed = sorted(set(full.origin) - set(reduced.origin))
    unfiled = {f"object:{n}" for n, t in reduced.ontology.objects.items()  # types whose area goes with the module
               if n in full.ontology.objects and full.ontology.objects[n].area != t.area}
    changed = sorted({e for e, ms in full.touched.items() if gone & set(ms) and e not in removed} | unfiled)
    before = set(full.issues)
    broken = [i for i in reduced.issues if i not in before]
    if deps and not cascade:
        broken.insert(0, need)
    return Impact(name, deps, removed, changed, broken)
