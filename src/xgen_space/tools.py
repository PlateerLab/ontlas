"""Agent-facing tools over a studio: describe, translate, query, decide, request actions. Scoped by role."""
from __future__ import annotations

import json
from typing import Any

from xgen_space.actions import Actor
from xgen_space.studio import Studio
from xgen_space.values import normalize


def _jsonable(rows: list[tuple], columns: list[str], types: dict[str, str]) -> list[dict]:
    return [{c: normalize(v, types.get(c, "")) for c, v in zip(columns, r)} for r in rows]


class StudioTools:
    def __init__(self, studio: Studio, *, role: str | None = None, principal: dict | None = None,
                 actor_id: str = "agent", read_only: bool = False):
        self.studio, self.role, self.principal = studio, role, dict(principal or {})
        self.actor = Actor(actor_id, "agent", [role] if role else [], principal=self.principal)
        self.read_only = read_only
        self.terms: list[dict] | None = None  # the glossary, when the caller has one

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
        from xgen_space.parse.sparql import parse_sparql

        return self.run_query(parse_sparql(text, self.studio.onto), None, backend)

    def run_cypher(self, text: str, params: dict | None = None, backend: str | None = None) -> dict:
        from xgen_space.parse.cypher import parse_cypher

        return self.run_query(parse_cypher(text, self.studio.onto), params, backend)

    def record(self, type_name: str, key: str) -> dict:
        """One row of an object, under the role's limits and masks, with what each value is called."""
        from xgen_space.check import all_props, find_prop

        onto = self.studio.onto
        t = onto.obj(type_name)
        self._visible(type_name, key)
        props = [p for p in all_props(onto, type_name) if not find_prop(onto, type_name, p).expr]
        if self.role:
            r = onto.roles[self.role]
            props = [p for p in props if r.can_read(type_name)]
        q = {"match": {"x": type_name}, "where": {"eq": [f"x.{t.key}", str(key)]}, "return": [f"x.{p}" for p in props]}
        res = self.run_query(q)
        row = res["rows"][0] if res["rows"] else {}
        return {"type": type_name, "label": t.label or type_name, "key": str(key),
                "values": [{"name": p, "label": find_prop(onto, type_name, p).label or p, "value": row.get(p)} for p in props]}

    def describe_object(self, name: str) -> dict:
        """One object and what touches it, for an agent that should not read a whole ontology to answer about one thing."""
        d = self.describe()
        if name not in d["objects"]:
            raise KeyError(f"unknown object '{name}'")
        onto = self.studio.onto
        return {"object": d["objects"][name],
                "links": [{"name": k, "from": lk.source, "to": lk.target, "label": lk.label, "inverse": lk.inverse}
                          for k, lk in onto.links.items() if name in (lk.source, lk.target)],
                "decisions": [k for k in d["decisions"] if onto.decisions[k].target == name],
                "actions": [k for k in d["actions"] if onto.actions[k].target == name]}

    def knowledge(self):
        """Definitions, rules and passages in one index."""
        from xgen_space.knowledge import build

        space = self.studio.space
        return space.knowledge(self.studio.onto, self.terms) if space is not None else build(self.studio.onto)

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

    def answer_question(self, text: str) -> dict:
        """One question to a decision, a record, a query or the documents, with what the answer stands on."""
        from xgen_space.answer import answer_question

        return _plain(answer_question(self, text))

    def _visible(self, type_name: str, key: str) -> None:
        if not self.role:
            return
        k = self.studio.onto.obj(type_name).key
        q = {"match": {"x": type_name}, "where": {"eq": [f"x.{k}", str(key)]}, "return": [f"x.{k}"]}
        if not self.studio.run(q, role=self.role, principal=self.principal).rows:
            raise PermissionError(f"{type_name} {key} is outside this role's rows")

    def decide(self, decision: str, key: str, params: dict | None = None) -> dict:
        target = self.studio.onto.decisions[decision].target
        if target:
            self._visible(target, key)
        return _plain(self.studio.decide(decision, key, params, role=self.role).to_dict())

    def list_functions(self) -> dict:
        """The functions this role may run, with their contracts, owners and versions."""
        from xgen_space.functions import describe

        onto = self.studio.onto
        return {"functions": [describe(onto, onto.functions[n]) for n in self.describe()["functions"]]}

    def run_function(self, name: str, key: str = "", params: dict | None = None) -> dict:
        return _plain(self.studio.function(name, key or None, params, role=self.role, principal=self.principal, by=self.actor.id))

    def request_action(self, action: str, key: str, params: dict | None = None) -> dict:
        if self.read_only:
            raise PermissionError("this server is read-only")
        self._visible(self.studio.onto.actions[action].target, key)
        p = self.studio.actions.request(action, key, params, actor=self.actor)
        if p.status == "executed":  # inside its limits it ran at once, so the graphs follow
            self.studio.sync()
        return _plain(p.to_dict())

    def list_proposals(self) -> list[dict]:
        return [_plain(p.to_dict()) for p in self.studio.actions.proposals.values()]

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
                              for n, d in space.documents().items()],
                "concepts": len(made["concepts"])}

    def search_documents(self, text: str, k: int = 5, store: str = "", where: dict | None = None) -> dict:
        space = self._space()
        hits = space.search(str(text), max(1, min(int(k), 50)), store=store, where=where)
        return {"embedder": space.embedder.describe(), "store": hits[0]["store"] if hits else space.primary(), "hits": hits,
                "ontology": space.concepts_in(str(text), self.studio.onto)}


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return normalize(value)


def _query_arg(query: Any) -> Any:
    if isinstance(query, str) and query.strip().startswith("{"):
        return json.loads(query)
    return query
