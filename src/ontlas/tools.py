"""Agent-facing tools over a studio: describe, translate, query, decide, request actions. Scoped by role."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from ontlas.actions import Actor
from ontlas.studio import Studio
from ontlas.values import normalize


def _jsonable(rows: list[tuple], columns: list[str], types: dict[str, str]) -> list[dict]:
    return [{c: normalize(v, types.get(c, "")) for c, v in zip(columns, r)} for r in rows]


class StudioTools:
    def __init__(self, studio: Studio, *, role: str | None = None, principal: dict | None = None,
                 actor_id: str = "agent", read_only: bool = False, audit: bool = False):
        self.studio, self.role, self.principal = studio, role, dict(principal or {})
        self.actor = Actor(actor_id, "agent", [role] if role else [], principal=self.principal)
        self.read_only = read_only
        self.audit = audit  # an agent's decisions, answers and functions go into the audit trail with what they stood on
        self.terms: list[dict] | None = None  # the glossary, when the caller has one

    def _note(self, event: str, target: str, key: str, name: str = "", **detail) -> None:
        if self.audit:
            self.studio.actions.note(self.actor, event, name, target, str(key or ""), **_plain(detail))

    def _role(self):
        return self.studio.onto.roles[self.role] if self.role else None

    def documents_allowed(self, name: str, folder: str = "") -> bool:
        """A document this role reads, and with a folder, one of that folder or of a folder under it."""
        r, space = self._role(), self.studio.space
        path = space.path_of(name) if space is not None else ""
        return (r is None or r.can_read_document(name, path)) and (not folder or space is None or space.in_folder(name, folder))

    def describe(self) -> dict:
        d = self.studio.describe()
        if self.role:
            r = self.studio.onto.roles[self.role]
            d["objects"] = {k: v for k, v in d["objects"].items() if r.can_read(k)}
            d["queries"] = {k: v for k, v in d["queries"].items() if r.can("run", k)}
            d["decisions"] = {k: v for k, v in d["decisions"].items() if r.can("run", k)}
            d["actions"] = {k: v for k, v in d["actions"].items() if r.can("request", k)}
            d["functions"] = {k: v for k, v in d["functions"].items() if r.can("run", k)}
        return d

    def translate(self, query: Any, to: str) -> dict:
        c = self.studio.translate(_query_arg(query), to)
        return {"language": c.language, "dialect": c.dialect, "text": c.text, "params": c.params,
                "literals": c.literals}

    def run_query(self, query: Any, params: dict | None = None, backend: str | None = None) -> dict:
        res = self.studio.run(_query_arg(query), params, backend=backend, role=self.role, principal=self.principal)
        return {"backend": res.backend, "columns": res.columns,
                "rows": _jsonable(res.rows, res.columns, res.compiled.column_types), "query_text": res.compiled.text}

    def run_sparql(self, text: str, backend: str | None = None) -> dict:
        from ontlas.parse.sparql import parse_sparql

        return self.run_query(parse_sparql(text, self.studio.onto), None, backend)

    def run_cypher(self, text: str, params: dict | None = None, backend: str | None = None) -> dict:
        from ontlas.parse.cypher import parse_cypher

        return self.run_query(parse_cypher(text, self.studio.onto), params, backend)

    def record(self, type_name: str, key: str) -> dict:
        """One row of an object, under the role's limits and masks, with what each value is called."""
        from ontlas.check import all_props, find_prop

        onto = self.studio.onto
        t = onto.obj(type_name)
        self._visible(type_name, key)
        if self.role and not onto.roles[self.role].can_read(type_name):
            raise PermissionError(f"{type_name} is outside this role")
        props = [p for p in all_props(onto, type_name) if not find_prop(onto, type_name, p).expr]
        q = {"match": {"x": type_name}, "where": {"eq": [f"x.{t.key}", str(key)]}, "return": [f"x.{p}" for p in props]}
        res = self.run_query(q)
        row = res["rows"][0] if res["rows"] else {}
        return {"type": type_name, "label": t.label or type_name, "key": str(key), "query": res["query_text"],
                "values": [{"name": p, "label": find_prop(onto, type_name, p).label or p, "value": row.get(p)} for p in props]}

    def describe_object(self, name: str) -> dict:
        """One object and what touches it, for an agent that should not read a whole ontology to answer about one thing."""
        d = self.describe()
        if name not in d["objects"]:
            raise KeyError(f"unknown object '{name}'")
        onto = self.studio.onto
        t = onto.objects[name]

        def named(n: str, label: str) -> dict:
            return {"name": n, "label": label or n}

        area = onto.areas.get(t.area) if t.area else None
        parent = onto.objects.get(t.parent) if t.parent else None
        return {"object": d["objects"][name],
                # where it sits: Object (area) > Entity > its sub-Entities
                "area": named(t.area, area.label) if area is not None else None,
                "parent": named(t.parent, parent.label) if parent is not None else None,
                "children": [named(k, x.label) for k, x in onto.objects.items() if x.parent == name and k in d["objects"]],
                "links": [{"name": k, "from": lk.source, "to": lk.target, "label": lk.label, "inverse": lk.inverse}
                          for k, lk in onto.links.items() if name in (lk.source, lk.target)],
                "decisions": [k for k in d["decisions"] if onto.decisions[k].target == name],
                "actions": [k for k in d["actions"] if onto.actions[k].target == name]}

    def knowledge(self, folder: str = ""):
        """Definitions, rules and passages in one index; a role reads only the passages of its documents, and a question
        kept to a folder only those of the folder."""
        from ontlas.knowledge import build

        space = self.studio.space
        know = space.knowledge(self.studio.onto, self.terms) if space is not None else build(self.studio.onto)
        r = self._role()
        if (r is None or r.documents is None) and not folder:
            return know
        return know.only(lambda doc: self.documents_allowed(doc, folder))

    def find_definitions(self, text: str, k: int = 8) -> dict:
        """The definitions a question is about, so an agent reads these rather than all of them."""
        d = self.describe()
        allowed = {f"object:{n}" for n in d["objects"]} | {f"query:{n}" for n in d["queries"]} | \
            {f"decision:{n}" for n in d["decisions"]} | {f"action:{n}" for n in d["actions"]}
        found = self.knowledge().find(str(text), max(1, min(int(k), 30)) * 3, ("object", "rule", "query", "action"))
        return {"found": [f for f in found if f["element"] in allowed][:max(1, min(int(k), 30))]}

    def agent_context(self, text: str, k: int = 8) -> dict:
        """What a question is about, written out for a prompt: an agent gets the words, rules and sources it should go by."""
        found = self.find_definitions(text, k)["found"]
        lines = [f"- [{f.get('kind_label', '')}] {f.get('title', '')}: {' '.join(str(f.get('text', '')).split())[:300]}" for f in found]
        terms = [t for t in (self.terms or []) if str(t.get("term", "")) and str(t["term"]) in text]
        words = [f"- {t['term']}: {t.get('definition', '')}" for t in terms]
        head = "이 정의와 규칙을 기준으로 답합니다. 판정은 decide 도구로 확인합니다."
        return {"text": "\n".join([head, *lines, *words]), "found": found}

    def answer_question(self, text: str, pick: dict | None = None, folder: str = "") -> dict:
        """One question to a decision, a record, a query or the documents, with what the answer stands on. `pick` is
        what a person corrected of how the question was taken: {type, key, decision, at}; `folder` keeps the documents
        to one folder."""
        from ontlas.answer import answer_question

        out = _plain(answer_question(self, text, pick=pick, folder=str(folder or "")))
        d = (out.get("decisions") or [{}])[0]
        self._note("answered", d.get("target", ""), d.get("key", ""), question=out["question"], route=out["route"],
                   answer=out["answer"], sources=[s.get("id") for s in out.get("sources") or []])
        return out

    def _visible(self, type_name: str, key: str) -> None:
        if not self.role:
            return
        k = self.studio.onto.obj(type_name).key
        q = {"match": {"x": type_name}, "where": {"eq": [f"x.{k}", str(key)]}, "return": [f"x.{k}"]}
        if not self.studio.run(q, role=self.role, principal=self.principal).rows:
            raise PermissionError(f"{type_name} {key} is outside this role's rows")

    def decide(self, decision: str, key: str = "", params: dict | None = None, at: datetime | None = None,
               values: dict | None = None) -> dict:
        """On the record `key` reads from the source, or on the `values` a caller gives (no source needed): an input
        given as null is a value (no delivery date yet), one not given at all comes back in MissingValues."""
        from ontlas.decide.words import verdict

        if decision not in self.studio.onto.decisions:
            raise KeyError(f"unknown decision '{decision}'")
        table = self.studio.onto.decisions[decision]
        target = table.target
        if values is None and not str(key or ""):
            raise ValueError("give the record it is about (key) or the values it decides on (values)")
        if values is not None and not isinstance(values, dict):
            raise ValueError("values is an object of input or property names to values")
        if target and values is None:
            self._visible(target, key)
        res = self.studio.decide(decision, None if values is not None else key, params, role=self.role, at=at, values=values)
        out = _plain(res.to_dict())
        outs = res.outputs if isinstance(res.outputs, dict) else {"result": res.outputs}
        out["verdict"] = verdict(table, outs)[0]
        out["mode"] = "values" if values is not None else "record"
        out["decided_by"] = (out.get("path") or {}).get("source")  # the one rule that gave the answer, its layer and version
        out["decision_id"] = uuid.uuid4().hex  # the key this decision is found by in the audit trail
        out["modules"] = [{k: m[k] for k in ("module", "version", "kind")} for m in self.list_modules()]  # what decided it
        self._note("decided", target or "", key, decision, outputs=out.get("outputs"), mode=out["mode"], id=out["decision_id"],
                   rules=[f"{decision}.{r}" for r in out.get("matched") or []])
        return out

    def find_rules(self, text: str = "", layer: str = "", decision: str = "", k: int = 0) -> dict:
        """The rule cards, AXIOM first: what each says, its conditions, result and exceptions, the source it stands on,
        its owner and status, and the decision, value or function that carries it out (none: written down only)."""
        from ontlas.semantic import semantic_view

        view = semantic_view(self.studio.onto, self.studio.composition)
        cards = [c for c in view["cards"] if c.get("kind") == "stated"]
        order = {x["layer"]: i for i, x in enumerate(view["layers"])}
        if layer:
            cards = [c for c in cards if c["layer"] == layer]
        if decision:
            cards = [c for c in cards if any(r.get("ref", "").startswith(f"decision:{decision}") for r in c["implements"])]
        if text:
            words = [w for w in str(text).split() if len(w) >= 2]
            scored = [(sum(w in " ".join(map(str, (c["statement"], c["result"], *c["conditions"], c["source"], c["id"])))
                           for w in words), c) for c in cards]
            cards = [c for s, c in sorted(scored, key=lambda x: -x[0]) if s] if words else cards
        cards = sorted(cards, key=lambda c: order.get(c["layer"], 9)) if not text else cards
        if k:
            cards = cards[:max(1, min(int(k), 200))]
        keep = ("id", "layer", "layer_label", "type", "type_label", "statement", "conditions", "result", "exceptions",
                "params", "source", "owner", "status", "status_label", "legal_review", "legal_review_label", "check",
                "module", "module_label", "version")
        return {"layers": [{"layer": x["layer"], "label": x["label"], "order": x["order"], "cards": x["cards"]} for x in view["layers"]],
                "rules": [{**{f: c.get(f) for f in keep},
                           "runs": [{"ref": r.get("ref"), "label": r.get("label")} for r in c["implements"]]} for c in cards]}

    def read_terms(self, text: str = "") -> dict:
        """With text: the terms it uses in their preferred words, what each stands for (a code value as 주문 · 주문 상태 =
        배송완료), the labels to search by for each (`expansions`), the terms it must not be taken for, and the
        definitions it names by their own label though no term covers them (`defined`). Without: the whole lexicon."""
        from ontlas.lexicon import _pattern, entry, labels, read

        terms = list(self.studio.composition.terms) if self.studio.composition is not None else []
        if not text:
            return {"terms": [entry(t) for t in terms]}
        text = str(text)
        out = read(text, terms)
        onto = self.studio.onto
        by_id = {e["id"]: e for e in (entry(t) for t in terms)}
        for m in out["matched"]:
            m.update(_meaning(onto, m["concept"]))
        out["expansions"] = [{"term": m["term"], "labels": [x for x, kind in labels(by_id[m["id"]]) if kind != "hidden"]}
                             for i, m in enumerate(out["matched"]) if m["id"] not in [x["id"] for x in out["matched"][:i]]]
        taken = [False] * len(text)  # the stretches a term already read
        for m in out["matched"]:
            for hit in _pattern(m["label"]).finditer(text):
                taken[hit.start():hit.end()] = [True] * (hit.end() - hit.start())
        d = self.describe()
        out["defined"] = _defined(onto, text, taken, set(d["objects"]), set(d["decisions"]))
        return out

    def validate_values(self, type_name: str, values: dict, complete: bool = False) -> dict:
        """Whether values for one object keep to its definition and to the rule cards that bound its properties: each
        value's type and allowed codes, and the min or max a card sets (an amount is never negative). The values are the
        caller's, so no source is needed. `complete`: every required property must be given as well."""
        from ontlas.check import _find_prop, all_props
        from ontlas.semantic import LAYER_LABEL
        from ontlas.values import accepts

        if type_name not in self.describe()["objects"]:
            raise KeyError(f"unknown object '{type_name}'")
        if not isinstance(values, dict):
            raise ValueError("values is an object of property names to values")
        onto, comp = self.studio.onto, self.studio.composition
        t = onto.objects[type_name]
        chain, at = [], type_name  # a bound on a parent's property holds for its sub-Entities
        while at and at in onto.objects and at not in chain:
            chain.append(at)
            at = onto.objects[at].parent
        versions = {m.name: m.version for m in comp.modules} if comp is not None else {}
        cards = [c for c in (comp.cards if comp is not None else []) if (c.get("check") or {}).get("property")]
        known = set(all_props(onto, type_name))
        violations: list[dict] = []
        applied: list[str] = []

        def bad(name: str, label: str, value: Any, kind: str, said: str, **more) -> None:
            violations.append({"property": name, "label": label, "value": value, "kind": kind, "said": said, **more})

        for name, value in values.items():
            p = _find_prop(onto, type_name, name) if name in known else None
            if p is None or p.internal:
                bad(name, name, value, "unknown", f"정의에 없는 속성 · {t.label or type_name} {name}")
                continue
            label = p.label or name
            if value is None:
                if p.required:
                    bad(name, label, value, "missing", f"필수 값 누락 · {label}")
                continue
            if p.type == "enum" and isinstance(value, str) and p.values and value not in p.values:
                bad(name, label, value, "code", f"허용되지 않은 코드 · {label} '{value}'",
                    allowed=[{"code": v, "label": (p.labels or {}).get(v, v)} for v in p.values])
                continue
            if not accepts(p.type, value, p.values):
                bad(name, label, value, "type", f"형식 불일치 · {label} '{value}'", expected=p.type)
                continue
            for c in cards:
                chk = c["check"]
                if chk["property"] not in {f"{x}.{name}" for x in chain} or isinstance(value, bool) or \
                        not isinstance(value, (int, float)):
                    continue
                applied.append(c["id"])
                low, high = chk.get("min"), chk.get("max")
                if (low is not None and value < low) or (high is not None and value > high):
                    bound = " · ".join(x for x in (f"{low} 이상" if low is not None else "", f"{high} 이하" if high is not None else "") if x)
                    bad(name, label, value, "rule", f"규칙 위반 · {label} {value}, {bound} · {c['statement']}",
                        rule=c["id"], layer=c["layer"], layer_label=LAYER_LABEL[c["layer"]], statement=c["statement"],
                        source=c.get("source", ""), module=c.get("module", ""), version=versions.get(c.get("module", ""), ""),
                        min=low, max=high)
        if complete:
            for name in sorted(known - set(values)):
                p = _find_prop(onto, type_name, name)
                if p is not None and p.required and not p.internal and not p.expr:
                    bad(name, p.label or name, None, "missing", f"필수 값 누락 · {p.label or name}")
        self._note("validated", type_name, "", "", valid=not violations, violations=len(violations), rules=applied)
        return {"object": type_name, "label": t.label or type_name, "valid": not violations,
                "checked": [n for n in values if n in known], "rules": sorted(set(applied)), "violations": violations}

    def run_questions(self, stage: str = "") -> dict:
        """The validation questions, measured in two stages: `values` on the values each question gives (no source
        needed) and `record` on the record its key reads. Where only the record is wrong, the mapping is to look at."""
        rep = self.studio.questions().to_dict()
        rows = []
        for r in rep["results"]:
            if stage and stage not in r["stages"]:
                continue
            rows.append({k: r[k] for k in ("id", "text", "type", "holdout", "passed", "unmeasured", "expected", "got",
                                          "stages", "diagnosis", "differs", "error")})
        return _plain({"stages": rep["stages"], "accuracy": rep["accuracy"] if rep["measured"] else None,
                       "measured": rep["measured"], "unmeasured": rep["unmeasured"], "results": rows})

    def list_functions(self) -> dict:
        """The functions this role may run, with their contracts, owners and versions."""
        from ontlas.functions import describe

        onto = self.studio.onto
        return {"functions": [describe(onto, onto.functions[n]) for n in self.describe()["functions"]]}

    def run_function(self, name: str, key: str = "", params: dict | None = None) -> dict:
        out = _plain(self.studio.function(name, key or None, params, role=self.role, principal=self.principal, by=self.actor.id))
        self._note("function_ran", out.get("target") or "", key, name, version=out.get("version"), outputs=out.get("outputs"))
        return out

    def request_action(self, action: str, key: str, params: dict | None = None) -> dict:
        if self.read_only:
            raise PermissionError("this server is read-only")
        self._visible(self.studio.onto.actions[action].target, key)
        p = self.studio.actions.request(action, key, params, actor=self.actor)
        if p.status == "executed":  # inside its limits it ran at once, so the graphs follow
            self.studio.sync()
        return _plain(p.to_dict())

    def list_proposals(self) -> list[dict]:
        """The requests this caller made, and how each stands. A role's caller sees no one else's."""
        mine = [p for p in self.studio.actions.proposals.values() if not self.role or p.requested_by.id == self.actor.id]
        return [_plain(p.to_dict()) for p in mine]

    def get_record(self, type_name: str, key: str) -> dict:
        """One object's values, inside the role's rows and with its masks."""
        return self.record(type_name, key)

    def list_modules(self) -> list[dict]:
        comp = self.studio.composition
        return comp.summary() if comp else [{"module": self.studio.onto.name, "version": self.studio.onto.version,
                                             "kind": "domain", "label": self.studio.onto.label}]

    def list_backends(self) -> dict:
        return {n: b.capabilities.to_dict() for n, b in self.studio.backends.items()}

    def _space(self):
        if self.studio.space is None:
            raise ValueError("this studio has no space: documents and vectors are configured under `space:` in its file")
        return self.studio.space

    def describe_space(self) -> dict:
        """Every kind of data here and what holds it: the four things a platform asks before plugging a space in."""
        st, space = self.studio, self.studio.space
        return {"name": st.onto.name, "label": st.onto.label,
                "ontology": {"objects": len(st.onto.objects), "links": len(st.onto.links), "queries": len(st.onto.queries),
                             "decisions": len(st.onto.decisions), "modules": [m["module"] for m in self.list_modules()]},
                "backends": {n: {"language": b.capabilities.language, "dialect": b.capabilities.dialect}
                             for n, b in st.backends.items()},
                "space": space.state() if space is not None else None,
                "reasoners": [r.describe() for r in st.reasoners.values()]}

    def list_documents(self) -> dict:
        space = self._space()
        made = space.concepts(self.studio.onto)
        sections: dict[str, list[str]] = {}
        for doc, title in made["sections"]:
            sections.setdefault(doc, []).append(title)
        return {"documents": [{"name": n, "kind": d.get("kind", ""), "sections": sections.get(n, [])}
                              for n, d in space.documents().items() if self.documents_allowed(n)],
                "concepts": len(made["concepts"])}

    def search_documents(self, text: str, k: int = 5, store: str = "", where: dict | None = None, folder: str = "") -> dict:
        space = self._space()
        k = max(1, min(int(k), 50))
        r = self._role()
        hits = space.search(str(text), k if r is None or r.documents is None else k * 4, store=store, where=where,
                            folder=str(folder or ""))
        hits = [h for h in hits if self.documents_allowed(h["document"])][:k]
        return {"embedder": space.embedder.describe(), "store": hits[0]["store"] if hits else space.primary(), "hits": hits,
                "ontology": space.concepts_in(str(text), self.studio.onto)}


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return normalize(value)


def _meaning(onto, element: str) -> dict:
    """What a definition is, to read: its kind and label and where it sits (a code value: 주문 · 주문 상태 = 배송완료)."""
    from ontlas.lexicon import concept_of

    c = concept_of(onto, element) if element else None
    if c is None:
        return {"concept_kind": "", "concept_label": "", "meaning": ""}
    sep = " = " if c["kind"] == "value" else " · "
    return {"concept_kind": c["kind_label"], "concept_label": c["label"],
            "meaning": f"{c['of']}{sep}{c['label']}" if c["of"] else c["label"]}


def _defined(onto, text: str, taken: list[bool], objects: set[str], decisions: set[str]) -> list[dict]:
    """The definitions a text names by their own label (an Object, an Entity, a property, a code value, a decision),
    outside the stretches already read, longest label first; a label several definitions share lists each of them."""
    from ontlas.lexicon import _pattern, concepts, norm

    def visible(element: str) -> bool:
        kind, _, name = element.partition(":")
        owner = name.split("=")[0].split(".")[0]
        return owner in objects if kind in ("object", "property", "value") else owner in decisions if kind == "decision" else True

    by_label: dict[str, list[dict]] = {}
    for c in concepts(onto):
        if len(norm(c["label"])) >= 2 and visible(c["concept"]):
            by_label.setdefault(c["label"], []).append(c)
    out = []
    for label in sorted(by_label, key=lambda x: -len(norm(x))):
        for hit in _pattern(label).finditer(text):
            if any(taken[hit.start():hit.end()]):
                continue
            taken[hit.start():hit.end()] = [True] * (hit.end() - hit.start())
            if not any(x["label"] == label for x in out):
                out.append({"label": label, "concepts": [{"concept": c["concept"], **_meaning(onto, c["concept"])}
                                                         for c in by_label[label]]})
    return out


def _query_arg(query: Any) -> Any:
    if isinstance(query, str) and query.strip().startswith("{"):
        return json.loads(query)
    return query
