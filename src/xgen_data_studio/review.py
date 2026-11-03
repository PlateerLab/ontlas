"""The studio's flow (its stages and what each must pass), decision agreement with past outcomes, and the review and
approval of a definition change before it reaches the library.

A change is a new version of one module. It is tried on a copy of the studio (the same source, a fresh graph), and
the review lists what it adds, removes and changes, the database check, whether every registered query still
answers the same on every backend, the questions' accuracy and the agreement with past decisions; the flow's pass
conditions decide whether it may be approved. Approval saves the version to the library and swaps it in.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from xgen_data_studio.modules import Module, ModuleError
from xgen_data_studio.values import from_source, normalize, parse_datetime

STAGES = ("source", "define", "bind", "project", "query", "decide", "check")
REQUIRED = ("source", "define")
GATES = {"bind": ("max_errors", "max_warnings"), "query": ("min_agree",), "decide": ("min_agreement",),
         "check": ("min_accuracy", "min_grounded")}
DEFAULT_GATES = {"bind": {"max_errors": 0}, "query": {"min_agree": 1.0}}


class ChangeError(ValueError):
    """The change cannot go ahead; the message says why."""


def tighter(condition: str, a: float, b: float) -> bool:
    """Whether limit a asks more than limit b: a lower maximum, a higher minimum."""
    return a < b if condition.startswith("max_") else a > b


def tighten(own: dict[str, dict], modules: dict[str, dict]) -> tuple[dict[str, dict], list[str]]:
    """The studio's pass conditions held to the attached modules' where those ask more (a quality module raises the
    bar and detaching it lowers it again); also which "stage.condition" the modules set."""
    out = {s: dict(c) for s, c in own.items()}
    raised = []
    for stage, conds in modules.items():
        for cond, v in conds.items():
            cur = out.get(stage, {}).get(cond)
            if cur is None or tighter(cond, v, cur):
                out.setdefault(stage, {})[cond] = v
                raised.append(f"{stage}.{cond}")
    return out, raised


@dataclass
class FlowSettings:
    off: list[str] = field(default_factory=list)
    gates: dict[str, dict[str, float]] = field(default_factory=lambda: json.loads(json.dumps(DEFAULT_GATES)))
    agreement: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict | None) -> FlowSettings:
        d = d or {}
        out = cls(off=[str(s) for s in d.get("off") or []],
                  gates={**json.loads(json.dumps(DEFAULT_GATES)), **{k: dict(v or {}) for k, v in
                                                                     (d.get("gates") or {}).items()}},
                  agreement=dict(d.get("agreement") or {}))
        issues = out.issues()
        if issues:
            raise ValueError("; ".join(issues))
        return out

    def issues(self) -> list[str]:
        out = []
        for s in self.off:
            if s not in STAGES:
                out.append(f"unknown stage '{s}'; stages are {STAGES}")
            elif s in REQUIRED:
                out.append(f"the '{s}' stage cannot be switched off")
        for s, conds in self.gates.items():
            if s not in GATES:
                out.append(f"stage '{s}' has no pass conditions; give them for {tuple(GATES)}")
                continue
            for k, v in conds.items():
                if k not in GATES[s]:
                    out.append(f"{s}: unknown condition '{k}'; use {GATES[s]}")
                elif v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
                    out.append(f"{s}.{k} must be a number")
                elif k.startswith("min_") and v is not None and not 0 <= v <= 1:
                    out.append(f"{s}.{k} is a share between 0 and 1")
                elif k.startswith("max_") and v is not None and v < 0:
                    out.append(f"{s}.{k} cannot be negative")
        a = self.agreement
        if a:
            for k in ("decision", "query", "expect"):
                if not a.get(k):
                    out.append(f"agreement needs '{k}'")
            if not a.get("inputs") and not a.get("key"):
                out.append("agreement needs 'key' (decide each case by its object) or 'inputs' (the values then)")
        return out

    def to_dict(self) -> dict:
        return {"off": list(self.off), "gates": json.loads(json.dumps(self.gates)), "agreement": dict(self.agreement)}

    def on(self, stage: str) -> bool:
        return stage not in self.off


@dataclass
class GateResult:
    stage: str
    condition: str
    limit: float
    value: float | None
    passed: bool


def agreement(studio, spec: dict[str, Any]) -> dict[str, Any]:
    """Decide every past case again and compare with what was actually decided then.

    spec: decision, query (registered, one row per case), expect {output: column}, and either key (the case's object,
    decided as the data stands; `at` names a column with the moment to decide as of) or inputs {input: column}
    (the values the case had then).
    """
    name = spec["decision"]
    table = studio.onto.decisions.get(name)
    if table is None:
        raise KeyError(f"unknown decision '{name}'")
    res = studio.run(spec["query"], dict(spec.get("params") or {}))
    rows = res.records()
    expect: dict[str, str] = dict(spec["expect"])
    inputs: dict[str, str] = dict(spec.get("inputs") or {})
    out_types = {k: v for k, v in table.outputs.items()}
    cases, mismatches = 0, []
    confusion: dict[str, dict[str, int]] = {k: {} for k in expect}
    keep_now = studio.now
    try:
        for r in rows:
            cases += 1
            if inputs:
                given = {i: from_source(r.get(c), table.inputs[i].type if i in table.inputs else "string")
                         for i, c in inputs.items()}
                got = studio.decide(name, inputs=given)
            else:
                at = r.get(spec["at"]) if spec.get("at") else None
                if at is not None:
                    moment = parse_datetime(at)
                    studio.now = lambda m=moment: m  # noqa: E731
                got = studio.decide(name, r.get(spec["key"]))
                studio.now = keep_now
            outs = got.outputs if isinstance(got.outputs, dict) else {}
            ok = True
            for o, col in expect.items():
                want, have = normalize(r.get(col), out_types.get(o, "")), normalize(outs.get(o), out_types.get(o, ""))
                cell = f"{want} → {have}"
                confusion[o][cell] = confusion[o].get(cell, 0) + 1
                ok = ok and want == have
            if not ok:
                mismatches.append({"case": {k: normalize(v) for k, v in r.items()},
                                   "expected": {o: normalize(r.get(c), out_types.get(o, "")) for o, c in expect.items()},
                                   "got": {o: normalize(outs.get(o), out_types.get(o, "")) for o in expect},
                                   "matched": got.matched,
                                   "inputs": {k: normalize(v) for k, v in got.inputs.items()}})
    finally:
        studio.now = keep_now
    agree = cases - len(mismatches)
    return {"decision": name, "cases": cases, "agree": agree, "rate": agree / cases if cases else None,
            "mismatches": mismatches, "confusion": confusion}


def measure(studio, settings: FlowSettings) -> dict[str, Any]:
    """The numbers the pass conditions read, for the stages that are on."""
    out: dict[str, Any] = {}
    if settings.on("bind") and studio.source:
        rep = studio.check_bindings()
        out["bind"] = {"ok": rep.ok, "checked": rep.checked,
                       "errors": sum(f.severity == "error" for f in rep.findings),
                       "warnings": sum(f.severity == "warning" for f in rep.findings),
                       "findings": [asdict(f) for f in rep.findings]}
    if settings.on("query") and studio.onto.queries and len(studio.backends) > 1:
        try:
            c = studio.conformance()
            s = c.summary()
            out["query"] = {"agree": s["agree"], "queries": s["queries"], "disagree": s["disagree"],
                            "share": s["agree"] / s["queries"] if s["queries"] else None}
        except Exception as e:  # a query a backend refuses is a failed condition, not a crash of the review
            out["query"] = {"error": f"{type(e).__name__}: {e}", "share": 0.0}
    if settings.on("check") and studio.onto.questions:
        q = studio.questions()
        out["check"] = {"accuracy": q.accuracy, "failed": [r.id for r in q.results if not r.passed],
                        "grounded": q.grounded, "ungrounded": {r.id: r.gaps for r in q.results if not r.grounded}}
    if settings.on("decide") and settings.agreement:
        try:
            out["decide"] = agreement(studio, settings.agreement)
        except Exception as e:
            out["decide"] = {"error": f"{type(e).__name__}: {e}", "rate": 0.0}
    return out


def gates(measured: dict[str, Any], settings: FlowSettings) -> list[GateResult]:
    values = {("bind", "max_errors"): (measured.get("bind") or {}).get("errors"),
              ("bind", "max_warnings"): (measured.get("bind") or {}).get("warnings"),
              ("query", "min_agree"): (measured.get("query") or {}).get("share"),
              ("decide", "min_agreement"): (measured.get("decide") or {}).get("rate"),
              ("check", "min_accuracy"): (measured.get("check") or {}).get("accuracy"),
              ("check", "min_grounded"): (measured.get("check") or {}).get("grounded")}
    out = []
    for stage, conds in settings.gates.items():
        if not settings.on(stage):
            continue
        for cond, limit in conds.items():
            if limit is None:
                continue
            v = values.get((stage, cond))
            if v is None:
                passed = stage not in measured  # nothing to measure (no questions, one backend): not a failure
            else:
                passed = v <= limit if cond.startswith("max_") else v >= limit
            out.append(GateResult(stage, cond, limit, v, passed))
    return out


def _elements(onto) -> dict[str, str]:
    d = onto.to_dict()
    out: dict[str, str] = {}
    for name, o in (d.get("objects") or {}).items():
        props = o.get("properties") or {}
        out[f"object:{name}"] = json.dumps({k: v for k, v in o.items() if k != "properties"}, sort_keys=True,
                                           ensure_ascii=False)
        for p, v in props.items():
            out[f"property:{name}.{p}"] = json.dumps(v, sort_keys=True, ensure_ascii=False)
    for section, kind in (("links", "link"), ("actions", "action"), ("roles", "role"), ("queries", "query"),
                          ("identities", "identity")):
        for k, v in (d.get(section) or {}).items():
            out[f"{kind}:{k}"] = json.dumps(v, sort_keys=True, ensure_ascii=False)
    for name, dt in (d.get("decisions") or {}).items():
        out[f"decision:{name}"] = json.dumps({k: v for k, v in dt.items() if k != "rules"}, sort_keys=True,
                                             ensure_ascii=False)
        for r in dt.get("rules") or []:
            out[f"rule:{name}.{r.get('id')}"] = json.dumps(r, sort_keys=True, ensure_ascii=False)
    for q in d.get("questions") or []:
        out[f"question:{q['id']}"] = json.dumps(q, sort_keys=True, ensure_ascii=False)
    return out


def element_diff(before, after) -> dict[str, list[str]]:
    a, b = _elements(before), _elements(after)
    return {"added": sorted(b.keys() - a.keys()), "removed": sorted(a.keys() - b.keys()),
            "changed": sorted(k for k in a.keys() & b.keys() if a[k] != b[k])}


def trial(studio, modules: list[Module], settings: FlowSettings):
    """A copy of the studio over other modules: the same source, read only, and a fresh in-memory graph."""
    from xgen_data_studio.studio import Studio

    copy = Studio.from_modules(modules, library=studio.library, now=studio.now, **studio._compose_kw)
    copy.settings = dict(studio.settings)
    if studio.source:
        copy.backends[studio.source] = studio.backends[studio.source]
        copy.source = studio.source
    if settings.on("project") and any(b.capabilities.load for b in studio.backends.values()):
        try:
            from xgen_data_studio.backends.rdf import RdflibBackend
        except ImportError:
            return copy
        for name, b in studio.backends.items():
            if b.capabilities.load:
                copy.add_backend(name, RdflibBackend())
        copy.project()
    return copy


def review(studio, module: Module, settings: FlowSettings | None = None, *, attach: bool = False) -> dict[str, Any]:
    """What one new module version would do, measured on a trial copy, and whether it passes the flow."""
    given = settings
    settings = settings or studio.flow
    current = list(studio.composition.modules) if studio.composition else []
    names = {m.name for m in current}
    if module.name in names:
        after = [module if m.name == module.name else m for m in current]
        mode = "replace"
    elif attach:
        after = current + [module]
        mode = "attach"
    else:
        after = None
        mode = "library"
    out: dict[str, Any] = {"module": module.name, "version": module.version, "mode": mode}
    base = None
    if studio.library is not None and studio.library.versions(module.name):
        try:
            base = studio.library.get(module.name)
        except ModuleError:
            base = None
    out["base_version"] = base.version if base else ""
    if after is None:
        out.update({"issues": [], "diff": {"added": [], "removed": [], "changed": []}, "measured": {}, "gates": [],
                    "passed": True})
        return out
    try:
        copy = trial(studio, after, settings)
    except Exception as e:  # the definition does not hold together: the review says so and cannot pass
        out.update({"issues": [str(e)], "diff": {}, "measured": {}, "gates": [], "passed": False})
        return out
    settings = given or copy.flow  # the bar the studio would have after the change (a quality module may move it)
    measured = measure(copy, settings)
    results = gates(measured, settings)
    out.update({"issues": [], "diff": element_diff(studio.onto, copy.onto), "measured": measured,
                "gates": [asdict(g) for g in results], "passed": all(g.passed for g in results)})
    return out


@dataclass
class ChangeRequest:
    id: str
    module: str
    version: str
    text: str
    requested_by: str
    status: str
    review: dict[str, Any]
    at: str
    attach: bool = False
    decided_by: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ChangeService:
    """Change requests for the definition: propose a module version, review it, approve or reject it."""

    def __init__(self, studio, *, store=None, self_approve: bool = False):
        self.studio = studio
        self.store = store  # the library approved versions are saved to; defaults to the studio's library
        self.self_approve = self_approve
        self.requests: dict[str, ChangeRequest] = {}
        self.audit: list[dict[str, Any]] = []
        self._ids = itertools.count(1)

    def _now(self) -> str:
        now = self.studio.now()
        return (now if isinstance(now, datetime) else datetime.now()).isoformat(timespec="seconds")

    def _library(self):
        lib = self.store if self.store is not None else self.studio.library
        if lib is None:
            raise ChangeError("this studio has no library to save a module to")
        return lib

    def propose(self, module: Module, *, by: str, attach: bool = False) -> ChangeRequest:
        lib = self._library()
        if module.version in lib.versions(module.name):
            same = lib.get(module.name, module.version).to_dict() == module.to_dict()
            raise ChangeError(f"{module.key} is already in the library" +
                              ("" if same else "; give the change a new version"))
        import yaml

        cr = ChangeRequest(f"C{next(self._ids)}", module.name, module.version,
                           yaml.safe_dump(module.to_dict(), allow_unicode=True, sort_keys=False), by, "pending",
                           review(self.studio, module, attach=attach), self._now(), attach)
        self.requests[cr.id] = cr
        self._log(by, "proposed", cr)
        return cr

    def _module(self, cr: ChangeRequest) -> Module:
        import yaml

        return Module.from_dict(yaml.safe_load(cr.text))

    def approve(self, change_id: str, *, by: str) -> ChangeRequest:
        cr = self._get(change_id)
        if cr.status != "pending":
            raise ChangeError(f"change {cr.id} is {cr.status}")
        if by == cr.requested_by and not self.self_approve:
            raise PermissionError("a change is approved by someone other than the person who proposed it")
        module = self._module(cr)
        cr.review = review(self.studio, module, attach=cr.attach)  # the studio may have moved since the proposal
        if not cr.review["passed"]:
            failed = [f"{g['stage']}.{g['condition']}" for g in cr.review["gates"] if not g["passed"]]
            raise ChangeError(f"change {cr.id} does not pass the flow: {failed or cr.review['issues']}")
        self._library().save(module)
        if cr.review["mode"] == "replace":
            self.studio.replace(module)
        elif cr.review["mode"] == "attach":
            self.studio.attach(module)
        cr.status, cr.decided_by = "approved", by
        self._log(by, "approved", cr)
        return cr

    def reject(self, change_id: str, *, by: str, reason: str = "") -> ChangeRequest:
        cr = self._get(change_id)
        if cr.status != "pending":
            raise ChangeError(f"change {cr.id} is {cr.status}")
        cr.status, cr.decided_by, cr.reason = "rejected", by, reason
        self._log(by, "rejected", cr, reason=reason)
        return cr

    def _get(self, change_id: str) -> ChangeRequest:
        cr = self.requests.get(change_id)
        if cr is None:
            raise KeyError(f"unknown change '{change_id}'")
        return cr

    def _log(self, by: str, event: str, cr: ChangeRequest, **detail) -> None:
        self.audit.append({"at": self._now(), "by": by, "event": event, "change": cr.id, "module": cr.module,
                           "version": cr.version, **detail})
