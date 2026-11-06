"""Actions: checked requests, human approval, write-back to the source, external calls, rollback and an audit trail."""
from __future__ import annotations

import itertools
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from xgen_space.compile.sql import qi
from xgen_space.expr import encode_text_date
from xgen_space.model import KEY_SEP
from xgen_space.roles import AccessDenied, in_scope
from xgen_space.values import accepts, coerce, normalize


@dataclass
class Actor:
    id: str
    kind: str = "human"
    roles: list[str] = field(default_factory=list)
    principal: dict[str, Any] = field(default_factory=dict)  # what a scoped role reads: {seller_id: S1}


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Proposal:
    id: str
    action: str
    target: str
    key: str
    params: dict[str, Any]
    requested_by: Actor
    status: str
    checks: list[CheckResult]
    changes: dict[str, Any]
    before: dict[str, Any] = field(default_factory=dict)
    approved_by: str = ""
    call: dict[str, Any] = field(default_factory=dict)
    rolled_back_by: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditEntry:
    at: str
    actor: str
    actor_kind: str
    event: str
    action: str
    target: str
    key: str
    proposal: str
    detail: dict[str, Any] = field(default_factory=dict)


class ActionError(ValueError):
    """The action cannot go ahead as asked; the message says why."""


def _stored(prop, value: Any) -> Any:
    """A value in the form its column keeps: a date kept as text goes back in the text's layout."""
    value = coerce(value, prop.type)
    return encode_text_date(value, prop.format) if prop.format and value is not None else value


class SqlWriteback:
    """Apply an action's changes to the bound source table with one UPDATE."""

    def __init__(self, backend):
        self.backend = backend

    def apply(self, onto, type_name: str, key: str, changes: dict[str, Any]) -> int:
        obj = onto.obj(type_name)
        cols = obj.key_prop.cols
        parts = str(key).split(KEY_SEP, len(cols) - 1) if len(cols) > 1 else [key]
        if len(parts) != len(cols):
            raise ValueError(f"key {key!r} of {type_name} has {len(parts)} parts, not {len(cols)}")
        sets = ", ".join(f"{qi(obj.prop(p).col)} = ?" for p in changes)
        args = tuple(_stored(obj.prop(p), v) for p, v in changes.items()) + tuple(parts)
        where = " AND ".join(f"{qi(c)} = ?" for c in cols)
        return self.backend.run(f"UPDATE {qi(obj.table)} SET {sets} WHERE {where}", args)


def parameter_spec(spec: Any) -> dict[str, Any]:
    return {"type": spec} if isinstance(spec, str) else dict(spec or {})


def check_parameters(parameters: dict[str, Any], given: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Coerce the given values to their declared types and test them; returns (values, problems)."""
    out, problems = dict(given), []
    for name, raw in parameters.items():
        spec = parameter_spec(raw)
        t = spec.get("type", "string")
        v = given.get(name)
        if v is None or v == "":
            if spec.get("required", True):
                problems.append(f"{name}: required")
            continue
        if isinstance(v, str) and t in ("integer", "decimal", "boolean"):
            try:
                v = coerce(v.strip(), t)
            except (TypeError, ValueError):
                problems.append(f"{name}: {v!r} is not {t}")
                continue
        if not accepts("string" if t == "enum" else t, v):
            problems.append(f"{name}: {v!r} is not {t}")
            continue
        values = spec.get("values")
        if values and v not in values:
            problems.append(f"{name}: {v!r} is not one of {values}")
        if t in ("integer", "decimal"):
            if "min" in spec and v < spec["min"]:
                problems.append(f"{name}: {v} is below {spec['min']}")
            if "max" in spec and v > spec["max"]:
                problems.append(f"{name}: {v} is above {spec['max']}")
        if isinstance(v, str):
            if "max_length" in spec and len(v) > spec["max_length"]:
                problems.append(f"{name}: longer than {spec['max_length']} characters")
            if "pattern" in spec and not re.fullmatch(str(spec["pattern"]), v):
                problems.append(f"{name}: {v!r} does not match {spec['pattern']}")
        out[name] = v
    return out, problems


_TOKEN = re.compile(r"\$(\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)")


def render(template: Any, context: dict[str, Any], *, env: bool = False) -> Any:
    """Fill $key, $param, $after.prop, $before.prop (and ${ENV}, in headers) into a request template."""
    if isinstance(template, dict):
        return {k: render(v, context, env=env) for k, v in template.items()}
    if isinstance(template, list):
        return [render(v, context, env=env) for v in template]
    if not isinstance(template, str):
        return template
    whole = _TOKEN.fullmatch(template)
    if whole and not whole.group(1).startswith("{"):
        return _lookup(whole.group(1), context)  # a lone token keeps its type in a JSON body

    def one(m: re.Match) -> str:
        name = m.group(1)
        if name.startswith("{"):
            if not env:
                raise ActionError(f"environment values like {m.group(0)} are only filled into headers")
            value = os.environ.get(name[1:-1])
            if value is None:
                raise ActionError(f"environment variable {name[1:-1]} is not set")
            return value
        v = _lookup(name, context)
        return "" if v is None else str(v)

    return _TOKEN.sub(one, template)


def _lookup(name: str, context: dict[str, Any]) -> Any:
    head, _, tail = name.partition(".")
    if tail:
        scope = context.get(head)
        if not isinstance(scope, dict) or tail not in scope:
            raise ActionError(f"${name} is not known to this action")
        return scope[tail]
    if name not in context:
        raise ActionError(f"${name} is not known to this action")
    return context[name]


@dataclass
class HttpCaller:
    """Sends an action's external request, only to the hosts it is told to trust."""

    allow_hosts: list[str]
    timeout: float = 10.0
    opener: Callable | None = None

    def allowed(self, url: str) -> bool:
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        return any(host == h.lower() or (h.startswith(".") and host.endswith(h.lower())) for h in self.allow_hosts)

    def send(self, spec: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        def quoted(v):
            return {k: quoted(x) for k, x in v.items()} if isinstance(v, dict) else urllib.parse.quote(str(v), safe="")

        url = render(str(spec["url"]), {k: quoted(v) for k, v in context.items()})
        if not self.allowed(url):
            raise ActionError(f"{urllib.parse.urlsplit(url).hostname} is not an allowed host for action calls")
        method = str(spec.get("method", "POST")).upper()
        headers = {str(k): str(v) for k, v in render(spec.get("headers") or {}, context, env=True).items()}
        data = None
        if method != "GET" and spec.get("body") is not None:
            body = render(spec["body"], context)
            data = (json.dumps(body, ensure_ascii=False, default=str) if not isinstance(body, str) else body).encode()
            headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        opener = self.opener or urllib.request.urlopen
        try:
            with opener(req, timeout=float(spec.get("timeout", self.timeout))) as resp:
                status, text = resp.status, resp.read(2000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read(2000).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ActionError(f"the call to {url} failed: {getattr(e, 'reason', e)}") from None
        if status >= 400:
            raise ActionError(f"the call to {url} answered {status}: {text[:200]}")
        return {"url": url, "method": method, "status": status, "body": text[:500]}


class ActionService:
    def __init__(self, studio, writeback=None, caller: HttpCaller | None = None):
        self.studio = studio
        self.writeback = writeback
        self.caller = caller
        self.proposals: dict[str, Proposal] = {}
        self.audit: list[AuditEntry] = []
        self._ids = itertools.count(1)

    def _log(self, actor: Actor, event: str, p: Proposal, **detail) -> None:
        self.audit.append(AuditEntry(self.studio.now().isoformat(timespec="seconds"), actor.id, actor.kind, event,
                                     p.action, p.target, p.key, p.id, detail))

    def _allowed(self, actor: Actor, verb: str, action: str) -> bool:
        roles = [self.studio.onto.roles[r] for r in actor.roles if r in self.studio.onto.roles]
        return any(r.can(verb, action) for r in roles)

    def _scoped_roles(self, actor: Actor, verb: str, a) -> list:
        """The roles an actor reaches this type through, or none where one of them reaches every row."""
        roles = [self.studio.onto.roles[r] for r in actor.roles if r in self.studio.onto.roles]
        allowed = [r for r in roles if r.can(verb, a.name)]
        return allowed if allowed and all(a.target in r.scoped for r in allowed) else []

    def _outside(self, actor: Actor, verb: str, a, key: str) -> str:
        """Why this object is beyond the actor's scope, if it is."""
        roles = self._scoped_roles(actor, verb, a)
        why = f"{a.target} {key} is outside the scope of {actor.id}"
        for r in roles:
            try:
                if in_scope(self.studio, r, a.target, key, actor.principal):
                    return ""
            except AccessDenied as e:
                why = str(e)
        return why if roles else ""

    def _fill_scope(self, actor: Actor, a, params: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        """What a scoped actor does not choose: a parameter named after the scope's attribute, and any property a
        write would set that holds it. Returns (params, fixed properties, problems)."""
        params, fixed, problems = dict(params), {}, []
        for r in self._scoped_roles(actor, "request", a):
            attr = r.scope.get("attribute", "")
            value = actor.principal.get(attr)
            if value is None:
                continue
            if attr in a.parameters:
                if params.get(attr) not in (None, "", value):
                    problems.append(f"{attr}: {params[attr]!r} is not {actor.id}'s own")
                params[attr] = value
            where = (r.scope.get("types") or {}).get(a.target)
            if isinstance(where, str):
                fixed[where] = value
        return params, fixed, problems

    def request(self, action: str, key: str, params: dict | None = None, *, actor: Actor) -> Proposal:
        onto = self.studio.onto
        a = onto.actions.get(action)
        if a is None:
            raise KeyError(f"unknown action '{action}'")
        filled, fixed, foreign = self._fill_scope(actor, a, dict(params or {}))
        params, problems = check_parameters(a.parameters, filled)
        problems += foreign
        checks = [CheckResult("role", self._allowed(actor, "request", action), f"{actor.id} roles {actor.roles}"),
                  CheckResult("parameters", not problems, "; ".join(problems))]
        outside = self._outside(actor, "request", a, str(key))
        if outside:  # nothing more is read, so an answer says nothing of a row beyond the scope
            checks.append(CheckResult("scope", False, outside))
            p = Proposal(f"P{next(self._ids)}", action, a.target, str(key), params, actor, "rejected", checks, {})
            self.proposals[p.id] = p
            self._log(actor, "rejected", p, failed=[c.name for c in checks if not c.passed])
            return p
        obj = onto.obj(a.target)
        current = self.studio.fetch(a.target, key)
        checks.append(CheckResult("target", current is not None, f"{a.target} {key}"))
        changes: dict[str, Any] = {}
        for p, v in a.set.items():
            if isinstance(v, str) and v.startswith("$principal."):
                attr = v.split(".", 1)[1]
                changes[p] = actor.principal.get(attr)
                if changes[p] is None:
                    checks.append(CheckResult("principal", False, f"{actor.id} has no {attr}"))
            else:
                changes[p] = params.get(v[1:]) if isinstance(v, str) and v.startswith("$") else v
        changes.update({p: v for p, v in fixed.items() if p in changes})
        if a.transition_to and current is not None:
            sm = obj.states
            state = current.get(sm.property)
            ok = sm.allows(state, a.transition_to)
            checks.append(CheckResult("state", ok, f"{state} -> {a.transition_to}"))
            changes[sm.property] = a.transition_to
        for c in a.criteria:
            if c.decision and current is not None:
                res = self.studio.decide(c.decision, key)
                outs = res.outputs if isinstance(res.outputs, dict) else {}
                ok = all(outs.get(k) == v for k, v in c.expect.items())
                checks.append(CheckResult(f"decision:{c.decision}", ok, str(outs)))
            if c.states and current is not None:
                state = current.get(obj.states.property) if obj.states else None
                checks.append(CheckResult("states", state in c.states, f"{state} in {c.states}"))
        if a.call:
            url = str(a.call.get("url", ""))
            ok = self.caller is not None and self.caller.allowed(url.split("$", 1)[0] if "$" in url else url)
            checks.append(CheckResult("call", ok, url if ok else f"{url}: no allowed host is configured for it"))
        before = {p: current.get(p) for p in changes} if current else {}
        p = Proposal(f"P{next(self._ids)}", action, a.target, str(key), params, actor, "pending", checks, changes,
                     before)
        self.proposals[p.id] = p
        self._log(actor, "requested", p, params=params)
        if not all(c.passed for c in checks):
            p.status = "rejected"
            self._log(actor, "rejected", p, failed=[c.name for c in checks if not c.passed])
            return p
        auto = not a.approval and actor.kind == "human" and self._allowed(actor, "execute", action) \
            and not self._outside(actor, "execute", a, str(key))
        if auto:
            self._execute(p, actor)
        return p

    def approve(self, proposal_id: str, *, approver: Actor) -> Proposal:
        p = self.proposals[proposal_id]
        if p.status != "pending":
            raise ValueError(f"proposal {p.id} is {p.status}")
        if approver.kind != "human":
            raise PermissionError("only a person approves an action")
        if not self._allowed(approver, "execute", p.action):
            raise PermissionError(f"{approver.id} may not execute {p.action}")
        outside = self._outside(approver, "execute", self.studio.onto.actions[p.action], p.key)
        if outside:
            raise PermissionError(outside)
        p.approved_by = approver.id
        self._log(approver, "approved", p)
        self._execute(p, approver)
        return p

    def reject(self, proposal_id: str, *, approver: Actor, reason: str = "") -> Proposal:
        p = self.proposals[proposal_id]
        p.status = "rejected"
        self._log(approver, "rejected", p, reason=reason)
        return p

    def _context(self, p: Proposal) -> dict[str, Any]:
        return {**p.params, "key": p.key, "action": p.action, "target": p.target, "proposal": p.id,
                "before": dict(p.before), "after": dict(p.changes)}

    def _execute(self, p: Proposal, actor: Actor) -> None:
        if self.writeback is None:
            raise RuntimeError("no write-back configured for actions")
        a = self.studio.onto.actions[p.action]
        current = self.studio.fetch(p.target, p.key) or {}
        p.before = {k: current.get(k) for k in p.changes}  # what a rollback restores: the values just before
        n = self.writeback.apply(self.studio.onto, p.target, p.key, p.changes)
        if a.call:
            self._log(actor, "written", p, before=p.before, after=p.changes, rows=n)
            try:
                p.call = self.caller.send(a.call, self._context(p))
            except ActionError as e:
                self.writeback.apply(self.studio.onto, p.target, p.key, p.before)
                p.status, p.call = "failed", {"error": str(e)}
                self._log(actor, "call_failed", p, error=str(e), reverted=p.before)
                return
            self._log(actor, "called", p, **p.call)
        p.status = "executed"
        self._log(actor, "executed", p, before=p.before, after=p.changes, rows=n)

    def rollback(self, proposal_id: str, *, actor: Actor, reason: str = "") -> Proposal:
        """Put back the values an executed action replaced, if nothing has changed them since."""
        p = self.proposals.get(proposal_id)
        if p is None:
            raise KeyError(f"unknown proposal '{proposal_id}'")
        if p.status != "executed":
            raise ActionError(f"proposal {p.id} is {p.status}; only an executed action can be rolled back")
        if actor.kind != "human":
            raise PermissionError("only a person rolls back an action")
        if not self._allowed(actor, "execute", p.action):
            raise PermissionError(f"{actor.id} may not execute {p.action}")
        a = self.studio.onto.actions[p.action]
        outside = self._outside(actor, "execute", a, p.key)
        if outside:
            raise PermissionError(outside)
        if a.call and not a.undo:
            raise ActionError(f"{p.action} sent an external request and declares no undo request, so it cannot "
                              "be rolled back here")
        obj = self.studio.onto.obj(p.target)
        current = self.studio.fetch(p.target, p.key) or {}
        moved = {k: current.get(k) for k, v in p.changes.items()
                 if normalize(current.get(k), obj.prop(k).type) != normalize(v, obj.prop(k).type)}
        if moved:
            raise ActionError(f"{p.target} {p.key} has changed since {p.id} ran ({moved}); roll back by hand")
        if a.undo:
            p.call = {**p.call, "undo": self.caller.send(a.undo, self._context(p))}
        self.writeback.apply(self.studio.onto, p.target, p.key, p.before)
        p.status, p.rolled_back_by = "rolled_back", actor.id
        self._log(actor, "rolled_back", p, restored=p.before, reason=reason)
        return p
