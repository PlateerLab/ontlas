"""Policy text to a decision table draft: the model drafts the rules, the engine checks them, a person approves.

The model reads the clauses of a policy and the ontology card and answers one decision table. The engine checks it
as it checks any module (inputs it can read on the target, tests it can evaluate, outputs the rules set) and that
every rule cites a clause the text has, and sends it back with what is wrong. What comes out is a module: a person
reads it, changes it, and files it as a change request, which is tried on a copy and approved like any other.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from xgen_data_studio.modules import Module, ModuleError, compose
from xgen_data_studio.nl import Attempt, extract_json, schema_card

SYSTEM = ("You turn the clauses of a business policy into one decision table, as one JSON object. Use only the "
          "object types, properties and links listed. Answer with the JSON object only.")

GUIDE = """Decision table format:
{"name": "<camelCase name>", "label": "<short label in the policy's language>",
 "target": "<the object type each decision is about>", "hit_policy": "first",
 "inputs": {"<input>": {"type": "<integer|decimal|string|boolean|date|datetime>", "property": "<property of the target>"},
            "<input>": {"type": "integer", "days_since": "<date or datetime property>"},
            "<input>": {"type": "<type>", "path": ["<link or inverse>", ...], "property": "<property where the path ends>"},
            "<input>": {"type": "integer", "count": ["<link or inverse>", ...]}},
 "outputs": {"<output>": "<boolean|string|integer|decimal>"},
 "rules": [{"id": "<kebab-case id>", "when": {"<input>": "<test>"}, "then": {"<output>": <value>},
            "cite": "<the clause the rule comes from, as the policy numbers it>"}]}
days_since is the number of days from that date to now; it is null when the date is empty.
A path follows links from the target, one object at each step; count counts the objects a path reaches.
Tests: "<= 7", "> 0", "== 3", "\\"VIP\\"" (text in double quotes), "in [\\"A\\", \\"B\\"]", "not in [...]", "true",
"false", "null" (no value), "not null", "-" (any value).
The first rule that matches decides: put the exceptions first and end with a rule whose "when" is {} for the rest.
Give every rule the clause it comes from, in the policy's own numbering: "제3조 ②" when it has articles, "2. 반품 제한"
when it numbers its headings, the heading itself when it has no numbers. Do not invent clauses."""

CALL_TOKENS = 12000  # a model that reasons first spends over 4,000 tokens before it answers even a short policy
CALL_SECONDS = 200.0  # one drafting call, at the 70 tokens a second such a model writes

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def cites(cite: str, text: str) -> bool:
    """Whether a rule's cite names a clause the policy has: the same words, or the same article numbers."""
    c, t = re.sub(r"\s+", "", cite or ""), re.sub(r"\s+", "", text or "")
    if not c:
        return False
    if re.fullmatch(r"\d+(\.\d+)*\.?", c):  # a bare number names a heading: the 1 of 14일 is not clause 1
        return bool(re.search(rf"(?m)^\s*{re.escape(c.rstrip('.'))}[.)\s]", text or ""))
    if c in t:
        return True
    numbers = re.findall(r"(\d+(?:\.\d+)*)조", c)
    return bool(numbers) and all(re.search(rf"(?<![\d.]){re.escape(n)}조", t) for n in numbers)


@dataclass
class PolicyDraft:
    decision: dict[str, Any] | None = None
    module: Module | None = None
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def issues(self) -> list[str]:
        return self.attempts[-1].issues if self.attempts else ["the model was not asked"]

    @property
    def ok(self) -> bool:
        return self.module is not None and not self.issues


class PolicyDrafter:
    def __init__(self, modules: list[Module], llm: Callable[[str, str], str], *, max_repairs: int = 2,
                 compose_kw: dict | None = None):
        self.modules, self.llm, self.max_repairs, self.kw = list(modules), llm, max_repairs, dict(compose_kw or {})
        comp = compose(self.modules, **self.kw)
        self.onto, self.comp, self.base_issues = comp.ontology, comp, set(comp.issues)

    def draft(self, text: str, *, target: str = "", name: str = "") -> PolicyDraft:
        ask = f"{schema_card(self.onto)}\n\n{GUIDE}\n\n"
        if target:
            ask += f"The decision is about {target}.\n"
        if name:
            ask += f"Name the decision {name}.\n"
        base = ask + "Policy:\n" + text
        prompt, out = base, PolicyDraft()
        for _ in range(self.max_repairs + 1):
            try:
                raw = self.llm(SYSTEM, prompt)
            except Exception as e:  # a model that does not answer in time is a failed attempt, not a crash
                out.attempts.append(Attempt(prompt, "", [f"the model did not answer: {type(e).__name__}"]))
                continue
            data = extract_json(raw)
            issues, module = self.check(data, text)
            out.attempts.append(Attempt(prompt, raw, issues))
            if module is not None:  # the latest that reads as a module, for a person to finish if it is not clean
                out.decision, out.module = data, module
            if not issues:
                return out
            prompt = (base + "\n\nYour last answer:\n" + raw + "\n\nIt has these problems:\n"
                      + "\n".join(f"- {i}" for i in issues) + "\nReturn a corrected JSON object.")
        return out

    def check(self, data: Any, text: str) -> tuple[list[str], Module | None]:
        """What is wrong with a drafted decision table, and the module it makes (None when it makes none)."""
        if not isinstance(data, dict):
            return ["the answer was not one JSON object"], None
        missing = [k for k in ("name", "target", "inputs", "outputs", "rules") if not data.get(k)]
        if missing:
            return [f"give {', '.join(missing)}"], None
        name = str(data["name"])
        if not _NAME.match(name):
            return [f"name '{name}' must be letters and digits, starting with a letter"], None
        if name in self.onto.decisions:
            return [f"decision '{name}' already exists; give the new one another name"], None
        if data["target"] not in self.onto.objects:
            return [f"target '{data['target']}' is not an object type"], None
        table = {k: v for k, v in data.items() if k != "name"}
        table.setdefault("hit_policy", "first")
        try:
            m = Module.from_dict({
                "module": "policy-" + re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower(), "version": "0.1.0",
                "kind": "customer", "label": f"정책 규칙 · {data.get('label') or name}",
                "description": "정책서에서 만든 결정표 초안입니다. 규칙과 출처 조항을 확인한 뒤 변경 요청으로 검토합니다.",
                "requires": self._requires(table), "decisions": {name: table}})
            comp = compose([*self.modules, m], **self.kw)
        except (ModuleError, KeyError, TypeError, ValueError, AttributeError) as e:
            return [f"the decision table does not read: {e}"], None
        issues = [i for i in comp.issues if i not in self.base_issues]
        ids = [str(r.get("id") or "") for r in table.get("rules") or [] if isinstance(r, dict)]
        if len(set(ids)) != len(ids) or "" in ids:
            issues.append("every rule needs its own id")
        for r in table.get("rules") or []:
            if not isinstance(r, dict):
                continue
            if not r.get("cite"):
                issues.append(f"rule {r.get('id')} has no cite; give the clause it comes from")
            elif not cites(str(r["cite"]), text):
                issues.append(f"rule {r.get('id')} cites '{r['cite']}', which the policy does not number")
        return issues, m

    def _requires(self, table: dict) -> list[str]:
        """The modules the table reads from: the target's, and each link's along the paths."""
        owners = {self.comp.owner(f"object:{table['target']}")}
        for spec in (table.get("inputs") or {}).values():
            for step in (spec or {}).get("path") or (spec or {}).get("count") or []:
                lk = self.onto.links.get(step) or self.onto.link_by_inverse(step)
                if lk is not None:
                    owners.add(self.comp.owner(f"link:{lk.name}"))
        return sorted(o for o in owners if o)
