"""Studio: the ontology plus its backends; every read, decision and action goes through here."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable

from ontlas.actions import ActionService, SqlWriteback
from ontlas.backends.base import Backend, NoSource, Result
from ontlas.check import all_props, check, column_of, find_prop, interface_view
from ontlas.compile.base import Compiled, CompileError, compiler_for
from ontlas.conformance import ConformanceReport
from ontlas.conformance import run as run_conformance
from ontlas.decide.table import DecisionError, DecisionResult, Evidence, evaluate_table, holding
from ontlas.ir import Cmp, Column, Edge, Query, Ref
from ontlas.model import Ontology
from ontlas.modules import Composition, Impact, Module, ModuleError, compose, removal_impact
from ontlas.projection import ChangeSet, Projection, _Reload, apply_changes, load, project
from ontlas.roles import AccessDenied, apply_role, mask_rows, mask_style, mask_value, masking
from ontlas.values import days_since, from_source, normalize


@dataclass
class QuestionResult:
    id: str
    text: str
    passed: bool
    expected: Any
    got: Any
    error: str = ""
    grounded: bool = False  # the answer carries its condition, its source and the version it was answered by
    gaps: list[str] = field(default_factory=list)  # what of those it lacks
    unmeasured: str = ""  # why it was not asked (no_source: it reads rows and none are connected); neither right nor wrong
    type: str = ""  # definition | decision | value: what it checks (Question.kind)
    holdout: bool = False  # of the held-out set: reported apart from the questions things are tuned on
    grading: str = "match"  # how it was held right (Question.graded_by)
    # measured in two stages: `values` without a source (on the values the question gives, or a definition), `record`
    # on the record its key reads once a source is connected. Each is {measured, passed, got, inputs, unmeasured}.
    stages: dict = field(default_factory=dict)
    # what a wrong answer points at: rule (wrong on the given values too) | mapping (right on them, wrong on the record)
    # | data (right on them, and the record could not be read)
    diagnosis: str = ""
    differs: list[dict] = field(default_factory=list)  # mapping: {input, given, read}, the values the record reads otherwise


STAGES = ("values", "record")


@dataclass
class QuestionReport:
    results: list[QuestionResult] = field(default_factory=list)

    @property
    def measured(self) -> list[QuestionResult]:
        """The questions that were asked: the shares below are of these."""
        return [r for r in self.results if not r.unmeasured]

    @property
    def accuracy(self) -> float:
        got = self.measured
        return sum(r.passed for r in got) / len(got) if got else 0.0

    @property
    def grounded(self) -> float:
        """The share of questions answered with condition, source and version (근거 제시율)."""
        got = self.measured
        return sum(r.grounded for r in got) / len(got) if got else 0.0

    def split(self, by: str = "holdout") -> dict[str, dict]:
        """The same shares for each set (dev, holdout) or each type: a held-out question is never read into the dev
        figure, so what was tuned on and what was kept apart are seen side by side."""
        names = {"holdout": lambda r: "holdout" if r.holdout else "dev", "type": lambda r: r.type}[by]
        groups: dict[str, list[QuestionResult]] = {"dev": [], "holdout": []} if by == "holdout" else {}
        for r in self.results:
            groups.setdefault(names(r), []).append(r)
        out = {}
        for name, rs in groups.items():
            got = [r for r in rs if not r.unmeasured]
            out[name] = {"questions": len(rs), "measured": len(got), "passed": sum(r.passed for r in got),
                         "accuracy": sum(r.passed for r in got) / len(got) if got else None,
                         "grounded": sum(r.grounded for r in got) / len(got) if got else None}
        return out

    def stages(self) -> dict[str, dict]:
        """Each stage on its own: how many questions it applies to, how many it could measure and how many passed."""
        out = {}
        for s in STAGES:
            rs = [r.stages[s] for r in self.results if s in r.stages]
            got = [x for x in rs if x["measured"]]
            out[s] = {"questions": len(rs), "measured": len(got), "passed": sum(bool(x["passed"]) for x in got),
                      "accuracy": sum(bool(x["passed"]) for x in got) / len(got) if got else None}
        out["diagnosis"] = {d: sum(r.diagnosis == d for r in self.results) for d in ("rule", "mapping", "data")}
        return out

    def to_dict(self) -> dict:
        return {"accuracy": self.accuracy, "grounded": self.grounded, "measured": len(self.measured),
                "unmeasured": len(self.results) - len(self.measured), "sets": self.split(), "types": self.split("type"),
                "stages": self.stages(), "results": [asdict(r) for r in self.results]}


class Studio:
    space = None  # documents and vectors beside the ontology (space.py); load_studio sets it
    reasoners: dict = {}  # the engines a studio file names (reason/port.py)

    def __init__(self, ontology: Ontology, *, now: Callable[[], datetime] | None = None, use_zen: bool = False):
        self.onto = ontology
        ontology.clock = now  # today() and now() in a computed property read the studio's clock, not the machine's
        self.backends: dict[str, Backend] = {}
        self.source: str = ""
        self.now = now or datetime.now
        self.use_zen = use_zen
        self.actions = ActionService(self)
        self.projection: Projection | None = None
        self._loaded: dict[str, Projection] = {}
        self.composition: Composition | None = None
        self.library = None
        self._compose_kw: dict[str, str] = {}
        self.settings: dict[str, Any] = {}
        self.last_sync: dict[str, Any] = {}
        self.entries: dict[str, Callable] = {}  # the callables a deployment offers functions (functions.py)
        self.function_log: deque = deque(maxlen=200)
        from ontlas.review import ChangeService

        self.changes = ChangeService(self)

    @classmethod
    def from_modules(cls, modules: list[Module], *, library=None, namespace: str = "", name: str = "",
                     label: str = "", **kw) -> Studio:
        """A studio over a composition of modules, which can then be attached and detached at run time. With no
        modules yet it is an empty definition under `namespace`, which the workspace module then fills."""
        comp = compose(modules, namespace=namespace, name=name, label=label)
        if comp.issues:
            raise ModuleError("; ".join(comp.issues))
        st = cls(comp.ontology, **kw)
        st.composition, st.library = comp, library
        st._compose_kw = {"namespace": comp.ontology.namespace, "name": name, **({"label": label} if label else {})}
        return st

    @classmethod
    def from_library(cls, library, wanted: list[str], **kw) -> Studio:
        return cls.from_modules(library.resolve(wanted), library=library, **kw)

    def _modules(self) -> list[Module]:
        if self.composition is None:
            raise ModuleError("this studio was built from one ontology file, not from modules")
        return list(self.composition.modules)

    def _use(self, comp: Composition) -> Composition:
        if comp.issues:
            raise ModuleError("; ".join(comp.issues))
        self.composition, self.onto = comp, comp.ontology
        self.projection, self._loaded = None, {}
        return comp

    def attach(self, module: Module | str, version: str = "") -> Composition:
        """Plug a module in (with what it requires from the library); refused if the result does not hold."""
        current = self._modules()
        names = {m.name for m in current}
        if isinstance(module, str):
            if self.library is None:
                raise ModuleError("attach by name needs a library")
            wanted = [m.name for m in current]
            picked = self.library.resolve(wanted + [f"{module}@{version}" if version else module])
            extra = [m for m in picked if m.name not in names]
        else:
            extra = [module]
        if not extra:
            raise ModuleError(f"{module} is already attached")
        return self._use(compose(current + extra, **self._compose_kw))

    def replace(self, module: Module) -> Composition:
        """Swap a plugged-in module for an edited version of it, keeping the rest; refused if the result does not hold."""
        current = self._modules()
        if module.name not in {m.name for m in current}:
            raise ModuleError(f"{module.name} is not attached")
        return self._use(compose([module if m.name == module.name else m for m in current], **self._compose_kw))

    def detach(self, name: str, *, cascade: bool = False) -> Impact:
        """Unplug a module; refused, with the impact, when something left would point at what it took away."""
        current = self._modules()
        impact = removal_impact(current, name, cascade=cascade, **self._compose_kw)
        if not impact.ok:
            err = ModuleError("; ".join(impact.broken))
            err.impact = impact
            raise err
        gone = {name, *impact.dependents} if cascade else {name}
        self._use(compose([m for m in current if m.name not in gone], **self._compose_kw))
        return impact

    def detach_impact(self, name: str, *, cascade: bool = False) -> Impact:
        return removal_impact(self._modules(), name, cascade=cascade, **self._compose_kw)

    def check_bindings(self, *, backend: str | None = None, data: bool = True):
        from ontlas.bindings import check_bindings

        return check_bindings(self.onto, self.backend(backend), data=data)

    def add_backend(self, name: str, backend: Backend, *, source: bool = False) -> Backend:
        backend.name = name
        self.backends[name] = backend
        if source or (not self.source and backend.capabilities.language == "sql"):
            self.source = name
            if backend.capabilities.write and self.actions.writeback is None:
                self.actions.writeback = SqlWriteback(backend)
        return backend

    def backend(self, name: str | None = None) -> Backend:
        if not name and not self.backends:
            raise NoSource()
        name = name or self.source or next(iter(self.backends), "")
        if name not in self.backends:
            raise KeyError(f"unknown backend '{name}'; have {sorted(self.backends)}")
        return self.backends[name]

    def source_info(self) -> dict[str, Any]:
        """Whether rows can be read at all, and from what: the backend's name and its kind as a studio file calls it
        (sqlite, postgres, gateway, rdflib, ...). A studio with no backend still defines, decides on given values,
        searches documents and takes changes."""
        if not self.backends:
            return {"connected": False, "name": "", "kind": ""}
        b = self.backend()
        dialect = {"tsql": "mssql"}.get(b.capabilities.dialect, b.capabilities.dialect)
        return {"connected": True, "name": b.name, "kind": dialect if b.kind == "dbapi" and dialect else b.kind}

    def query(self, q: Query | dict | str) -> Query:
        if isinstance(q, Query):
            return q
        if isinstance(q, str):
            rq = self.onto.queries.get(q)
            if rq is None:
                raise KeyError(f"unknown registered query '{q}'")
            return Query.from_dict(rq.query)
        return Query.from_dict(q)

    def translate(self, q: Query | dict | str, to: str) -> Compiled:
        return compiler_for(self.onto, to).compile(self.query(q))

    def run(self, q: Query | dict | str, params: dict | None = None, *, backend: str | None = None,
            role: str | None = None, principal: dict | None = None) -> Result:
        query = self.query(q)
        values = dict(params or {})
        plan: dict[str, str] = {}
        if role:
            if isinstance(q, str) and not self.onto.roles[role].can("run", q):
                raise AccessDenied(f"role {role} may not run '{q}'")
            plan = masking(self.onto, check(query, self.onto).query, role)
            query, extra = apply_role(self.onto, query, role, principal)
            values.update(extra)
        b = self.backend(backend)
        missing = b.unsupported(query, interface_view(self.onto, query))
        if missing:
            raise CompileError(f"backend {b.name} does not support {missing}")
        compiled = b.compiler(self.onto).compile(query)
        res = b.execute(compiled, values)
        hidden = check(query, self.onto).hidden
        if hidden:  # columns added only to order by
            keep = [i for i, c in enumerate(res.columns) if c not in hidden]
            res.columns = [res.columns[i] for i in keep]
            res.rows = [tuple(r[i] for i in keep) for r in res.rows]
        if plan:
            res.rows, res.masked = mask_rows(res.columns, res.rows, plan), plan
        return res

    def run_sparql(self, text: str, params: dict | None = None, **kw) -> Result:
        from ontlas.parse.sparql import parse_sparql

        return self.run(parse_sparql(text, self.onto), params, **kw)

    def run_cypher(self, text: str, params: dict | None = None, **kw) -> Result:
        from ontlas.parse.cypher import parse_cypher

        return self.run(parse_cypher(text, self.onto), params, **kw)

    def fetch(self, type_name: str, key: Any, *, backend: str | None = None) -> dict[str, Any] | None:
        obj = self.onto.obj(type_name)
        names = all_props(self.onto, type_name)
        kind = find_prop(self.onto, type_name, obj.key).type if obj.key else "string"
        wanted: Any = str(key)
        if kind == "integer":  # a number column is not equal to its digits on most stores
            try:
                wanted = int(wanted)
            except ValueError:
                return None
        q = Query(nodes={"x": type_name}, where=Cmp(Ref("x", obj.key), "eq", wanted),
                  columns=[Column(Ref("x", p), p) for p in names])
        rows = self.run(q, backend=backend).rows
        if not rows:
            return None
        return {p: from_source(v, find_prop(self.onto, type_name, p).type) for p, v in zip(names, rows[0])}

    def _follow(self, type_name: str, key: Any, path: list[str]) -> tuple[str, list[str]]:
        nodes, edges, here = {"x0": type_name}, [], type_name
        for i, step in enumerate(path):
            lk = self.onto.links.get(step) or self.onto.link_by_inverse(step)
            if lk is None:
                raise DecisionError(f"unknown link '{step}'")
            here = lk.target if lk.name == step else lk.source
            nodes[f"x{i + 1}"] = here
            edges.append(Edge(f"x{i}", step, f"x{i + 1}"))
        last = f"x{len(path)}"
        q = Query(nodes=nodes, edges=edges, where=Cmp(Ref("x0", self.onto.obj(type_name).key), "eq", str(key)),
                  columns=[Column(Ref(last, self.onto.obj(here).key), "k")], distinct=True)
        return here, [str(r[0]) for r in self.run(q).rows]

    def given(self, name: str, values: dict, params: dict | None = None, at: datetime | None = None
              ) -> tuple[dict[str, Any], list[Evidence]]:
        """A decision's inputs from values a caller gives instead of a record: each input by its own name, or by the
        property of the target it reads (a date for `days_since`), or by its parameter. With no source connected this
        is how a workflow decides. An input given none of these ways is missing (MissingValues), never taken as null."""
        from ontlas.decide.table import MissingValues
        from ontlas.decide.words import input_label
        from ontlas.values import coerce

        table = self.onto.decisions[name]
        params = dict(params or {})
        out: dict[str, Any] = {}
        evidence: list[Evidence] = []
        missing: list[dict] = []
        for inp in table.inputs.values():
            src = inp.source
            prop = src.get("property") or src.get("days_since") or ""
            own = table.target and prop and not src.get("path")  # a property of the target itself, not one a link reaches
            if inp.name in values:
                raw, said = values[inp.name], inp.name
            elif own and prop in values:
                raw, said = values[prop], prop
                if "days_since" in src and raw is not None:
                    raw = days_since(raw, at or self.now())
            elif "param" in src and (src["param"] in params or src["param"] in values):
                raw = params.get(src["param"], values.get(src["param"]))
                said = src["param"]
            else:
                missing.append({"input": inp.name, "label": input_label(self.onto, table, inp.name), "type": inp.type,
                                "property": prop if own else "", "param": src.get("param", "")})
                continue
            try:
                out[inp.name] = coerce(raw, inp.type)
            except (TypeError, ValueError):
                raise DecisionError(f"{name}.{inp.name}: '{raw}' is not {inp.type}") from None
            # what it stands on: the caller's value, for the property of the target it would otherwise be read from
            evidence.append(Evidence(inp.name, out[inp.name], table.target if own else "", "", prop if own else said, "given"))
        if missing:
            raise MissingValues(name, missing)
        return out, evidence

    def decide(self, name: str, key: Any = None, params: dict | None = None, *, role: str | None = None,
               inputs: dict | None = None, at: datetime | None = None, values: dict | None = None) -> DecisionResult:
        """`key` reads the target's record from the source; `values` decides on what the caller gives (see `given`);
        `inputs` are the table's inputs as they are, for a simulation."""
        table = self.onto.decisions.get(name)
        if table is None:
            raise KeyError(f"unknown decision '{name}'")
        if role and not self.onto.roles[role].can("run", name):
            raise AccessDenied(f"role {role} may not run decision '{name}'")
        params = dict(params or {})
        evidence: list[Evidence] = []
        if values is not None:
            inputs, evidence = self.given(name, values, params, at)
        stated = bool(inputs) or values is not None  # decided on what it was given: no record is read
        values = dict(inputs or {})
        row = None
        if table.target and not stated:
            row = self.fetch(table.target, key)
            if row is None:
                raise DecisionError(f"{table.target} {key} not found")
        for inp in ([] if stated else table.inputs.values()):
            src = inp.source
            if "param" in src:
                values[inp.name] = params.get(src["param"])
                evidence.append(Evidence(inp.name, values[inp.name], source="parameter"))
                continue
            if "count" in src:
                _, keys = self._follow(table.target, key, list(src["count"]))
                values[inp.name] = len(keys)
                evidence.append(Evidence(inp.name, len(keys), table.target, str(key),
                                         "->".join(src["count"]), "count"))
                continue
            prop = src.get("property") or src.get("days_since")
            here, obj_key, obj_row = table.target, str(key), row
            if src.get("path"):
                here, keys = self._follow(table.target, key, list(src["path"]))
                if len(keys) > 1:
                    raise DecisionError(f"{name}.{inp.name}: the path reaches {len(keys)} objects; use count")
                obj_key = keys[0] if keys else ""
                obj_row = self.fetch(here, obj_key) if keys else None
            raw = obj_row.get(prop) if obj_row else None
            if "days_since" in src:
                value = None if raw is None else days_since(raw, at or self.now())
            else:
                value = raw
            values[inp.name] = value
            obj = self.onto.obj(here)
            pdef = find_prop(self.onto, here, prop)
            where = (f"{here}.{prop} = {pdef.expr}" if pdef.expr else
                     f"{obj.table}.{column_of(self.onto, here, prop)}" if obj.table else "")
            evidence.append(Evidence(inp.name, value, here, obj_key, prop, where))
        if self.use_zen:
            from ontlas.decide.zen import evaluate_zen

            outputs, matched, notes, engine = evaluate_zen(table, values), [], [], "zen"
        else:
            outputs, matched, notes = evaluate_table(table, values)
            engine = "native"
        held = [r.id for r in holding(table, values)] if engine == "native" else []
        also = [i for i in held if i not in matched]
        path = {}
        if engine == "native":
            from ontlas.semantic import decision_path

            comp = self.composition
            path = decision_path(table, matched, held, {m.name: m.label or m.name for m in comp.modules} if comp else {})
        shown = dict(values)
        if role:  # the verdict uses the real values; what the role is shown of them follows its masks
            r = self.onto.roles[role]
            for ev in evidence:
                style = mask_style(self.onto, r, ev.object_type, ev.property) if ev.object_type else ""
                if style:
                    ev.value = mask_value(ev.value, style)
                    shown[ev.input] = ev.value
        return DecisionResult(name, outputs, matched, shown, evidence, notes, engine, table.target,
                              "" if key is None else str(key), also=also, path=path)

    def project(self, *, into: list[str] | None = None, source: str | None = None) -> dict[str, Any]:
        """Re-read the source and bring each graph backend up to date with a change set."""
        proj = project(self.onto, self.backend(source))
        self.projection = proj
        report: dict[str, Any] = {}
        targets = into if into is not None else [n for n, b in self.backends.items() if b.capabilities.load]
        for name in targets:
            b = self.backend(name)
            prev = self._loaded.get(name)
            if prev is None:
                load(self.onto, proj, b, clear=True)
                report[name] = {"loaded": {"nodes": len(proj.nodes), "edges": len(proj.edges)}}
            else:
                changes: ChangeSet = prev.diff(proj)
                try:
                    apply_changes(self.onto, changes, b)
                except _Reload:
                    load(self.onto, proj, b, clear=True)
                report[name] = {"changes": changes.summary()}
            self._loaded[name] = proj
        return report

    def registered(self, params: dict[str, dict] | None = None) -> dict[str, tuple[Query, dict]]:
        params = params or {}
        defaults = _default_params(self.onto)
        return {n: (Query.from_dict(rq.query), params.get(n, defaults.get(n, {})))
                for n, rq in self.onto.queries.items()}

    def conformance(self, backends: list[str] | None = None, queries: dict | None = None) -> ConformanceReport:
        names = backends or list(self.backends)
        return run_conformance(self.onto, {n: self.backend(n) for n in names}, queries or self.registered())

    def questions(self, *, backend: str | None = None) -> QuestionReport:
        report = QuestionReport()
        asker = None
        for qs in self.onto.questions:
            meta = {"type": qs.kind, "holdout": qs.holdout, "grading": qs.graded_by}
            if qs.graded_by == "llm":  # a model holds it right or wrong, and the check has none: not asked
                report.results.append(QuestionResult(qs.id, qs.text, False, qs.expect, None, unmeasured="needs_model", **meta))
                continue
            if qs.decision:
                report.results.append(self._decision_question(qs, meta))
                continue
            stage = "record" if qs.query else "values"  # a query reads rows; what a word means needs none
            try:
                if qs.query:
                    res = self.run(qs.query, qs.params, backend=backend)
                    got, passed = _judge(qs.expect, res, check(self.query(qs.query), self.onto).column_types)
                    gaps = []  # a registered query answers with its own definition and the source columns it reads
                    rq = self.onto.queries[qs.query]
                    said = " ".join(str(normalize(v)) for row in res.rows for v in row)
                    grounds = f"{qs.query} {rq.label} {rq.description} {res.compiled.text}"
                    if not self.version_of(f"query:{qs.query}"):
                        gaps.append("no version")
                else:  # what a word means: answered as the page answers a question, from definitions and documents
                    asker = asker or self._asker()
                    got, passed, gaps, said, grounds = _defined(asker, qs)
                passed = _graded(qs, passed, said, grounds, gaps)
                report.results.append(QuestionResult(qs.id, qs.text, passed, qs.expect, got, "", not gaps, gaps, **meta,
                                                     stages={stage: {"measured": True, "passed": passed, "got": got}}))
            except NoSource:  # it reads rows and there are none to read: not asked, rather than answered wrong
                report.results.append(QuestionResult(qs.id, qs.text, False, qs.expect, None, unmeasured="no_source", **meta,
                                                     stages={stage: {"measured": False, "passed": None, "unmeasured": "no_source"}}))
            except Exception as e:
                said = f"{type(e).__name__}: {e}"
                report.results.append(QuestionResult(qs.id, qs.text, False, qs.expect, None, said, False, ["no answer"], **meta,
                                                     stages={stage: {"measured": True, "passed": False, "error": said}}))
        return report

    def _decision_question(self, qs, meta: dict) -> QuestionResult:
        """A decision question in its two stages: on the values it gives (no source needed) and on the record its key
        reads. When both are measured and only the record is wrong, the rule held and the record reads other values
        than the question gives: the mapping is the thing to look at, and `differs` says which values."""
        from ontlas.decide.table import MissingValues

        stages: dict[str, dict] = {}
        done: dict[str, tuple] = {}  # stage -> (result or None, passed, gaps, error)
        for stage, how in (("values", {"values": qs.values} if qs.values else None),
                           ("record", {"key": qs.key} if qs.key else None)):
            if how is None:
                continue
            try:
                res = self.decide(qs.decision, params=qs.params, **how)
                got = res.outputs
                passed = isinstance(got, dict) and all(got.get(k) == v for k, v in qs.expect.items())
                gaps = self._decision_gaps(res)
                if not self.version_of(f"decision:{qs.decision}"):
                    gaps.append("no version")
                said, grounds = self._decision_words(res)
                passed = _graded(qs, passed, said, grounds, gaps)
                stages[stage] = {"measured": True, "passed": passed, "got": got, "inputs": dict(res.inputs)}
                done[stage] = (res, passed, gaps, "")
            except NoSource:  # its record is in a source that is not connected: measured once one is
                stages[stage] = {"measured": False, "passed": None, "unmeasured": "no_source"}
            except MissingValues as e:  # the question gives too few values: the question is what to fix
                stages[stage] = {"measured": True, "passed": False, "error": str(e), "missing": e.missing}
                done[stage] = (None, False, ["no answer"], f"MissingValues: {e}")
            except Exception as e:
                said = f"{type(e).__name__}: {e}"
                stages[stage] = {"measured": True, "passed": False, "error": said}
                done[stage] = (None, False, ["no answer"], said)
        pick = "record" if "record" in done else "values" if "values" in done else ""
        if not pick:
            return QuestionResult(qs.id, qs.text, False, qs.expect, None, unmeasured="no_source", **meta, stages=stages)
        res, passed, gaps, error = done[pick]
        diagnosis, differs = "", []
        if "values" in done and not done["values"][1]:
            diagnosis = "rule"  # wrong on the values the question states: the rule (or what the question expects)
        elif "values" in done and "record" in done and done["record"][0] is None:
            diagnosis = "data"  # right on its values, and its record could not be read (not found, a value it lacks)
        elif "values" in done and "record" in done and not done["record"][1]:
            diagnosis = "mapping"
            given, read = done["values"][0], done["record"][0]
            if given is not None and read is not None:
                from ontlas.decide.words import input_label

                table = self.onto.decisions[qs.decision]
                differs = [{"input": k, "label": input_label(self.onto, table, k), "given": given.inputs.get(k),
                            "read": read.inputs.get(k)} for k in given.inputs
                           if normalize(given.inputs.get(k)) != normalize(read.inputs.get(k))]
        return QuestionResult(qs.id, qs.text, passed, qs.expect, None if res is None else res.outputs, error,
                              not gaps, gaps, **meta, stages=stages, diagnosis=diagnosis, differs=differs)

    def _asker(self):
        """The tools a definition question is answered through: the page's answer, with the lexicon's words."""
        from ontlas.tools import StudioTools

        tools = StudioTools(self)
        tools.terms = list(self.composition.terms) if self.composition is not None else []
        return tools

    def _decision_words(self, res: DecisionResult) -> tuple[str, str]:
        """A verdict as a person reads it (its word and its outputs), and what it stands on (the rules, their clauses,
        the source columns), for a grading by words."""
        from ontlas.decide.words import verdict

        table = self.onto.decisions[res.decision]
        outs = res.outputs if isinstance(res.outputs, dict) else {"result": res.outputs}
        by_id = {r.id: r for r in table.rules}
        matched = res.matched or evaluate_table(table, res.inputs)[1]
        said = " ".join([verdict(table, outs)[0], *(str(v) for v in outs.values())])
        grounds = " ".join([table.label, table.cite, *matched, *(by_id[i].cite for i in matched if i in by_id),
                            *(e.source or "" for e in res.evidence)])
        return said, grounds

    def _decision_gaps(self, res: DecisionResult) -> list[str]:
        """What a verdict lacks of its grounds: a rule that matched, a cite for it (its own or its table's), a source
        column for each value."""
        table = self.onto.decisions[res.decision]
        matched = res.matched or evaluate_table(table, res.inputs)[1]  # the ZEN engine names no rules
        by_id = {r.id: r for r in table.rules}
        gaps = [] if matched else ["no rule matched"]
        gaps += [f"rule {i} has no cite" for i in matched if i in by_id and not (by_id[i].cite or table.cite)]
        gaps += [f"{e.input} has no source column" for e in res.evidence if e.object_type and not e.source]
        return gaps

    def version_of(self, element: str) -> str:
        """The version an element was defined by: its module's, or the ontology's when it has no modules."""
        if self.composition is None:
            return self.onto.version
        owner = self.composition.owner(element)
        return next((m.version for m in self.composition.modules if m.name == owner), "")

    def describe(self) -> dict:
        o = self.onto
        return {
            "ontology": o.name, "version": o.version, "label": o.label,
            "objects": {t.name: {"label": t.label, "key": t.key,
                                 "properties": {p.name: {"type": p.type, "label": p.label,
                                                         **({"values": p.values} if p.values else {})}
                                                for p in t.properties.values()}}
                        for t in o.objects.values()},
            "links": {lk.name: {"from": lk.source, "to": lk.target, "label": lk.label, "inverse": lk.inverse,
                                "cardinality": lk.cardinality} for lk in o.links.values()},
            "queries": {q.name: {"label": q.label, "params": q.params} for q in o.queries.values()},
            "decisions": {d.name: {"label": d.label, "target": d.target, "outputs": d.outputs}
                          for d in o.decisions.values()},
            "actions": {a.name: {"label": a.label, "target": a.target, "parameters": a.parameters,
                                 "approval": a.approval, **({"auto_within": a.auto_within} if a.auto_within else {})}
                        for a in o.actions.values()},
            "functions": {f.name: {"label": f.label, "target": f.target, "version": f.version, "owner": f.owner,
                                   "runtime": f.runtime, "status": f.status, "inputs": f.inputs, "outputs": f.outputs}
                          for f in o.functions.values()},
            "backends": {n: b.capabilities.to_dict() for n, b in self.backends.items()},
        }

    @property
    def own_flow(self):
        """The flow as the studio file's `flow:` (and what is saved over it) gives it, before any module raises it."""
        from ontlas.review import FlowSettings

        return FlowSettings.from_dict(self.settings.get("flow"))

    @property
    def flow(self):
        """The flow's stages and pass conditions: the studio's own, held to an attached quality module's where that
        asks more (see review.py)."""
        from ontlas.review import tighten

        s = self.own_flow
        if self.composition is not None and self.composition.gates:
            s.gates, _ = tighten(s.gates, self.composition.gates)
        return s

    def raised_gates(self) -> dict[str, str]:
        """The pass conditions an attached module sets because it asks more than the studio: {stage.condition: module}."""
        from ontlas.review import tighten

        if self.composition is None or not self.composition.gates:
            return {}
        _, raised = tighten(self.own_flow.gates, self.composition.gates)
        return {k: self.composition.gate_by[k] for k in raised}

    def gates(self) -> dict[str, Any]:
        """Measure this studio against its flow's pass conditions."""
        from dataclasses import asdict as _asdict

        from ontlas.review import gates, measure

        settings = self.flow
        measured = measure(self, settings)
        results = gates(measured, settings)
        return {"measured": measured, "gates": [_asdict(g) for g in results], "passed": all(g.passed for g in results)}

    def function(self, name: str, key: Any = None, params: dict | None = None, *, role: str | None = None,
                 principal: dict | None = None, by: str = "", trial: bool = False, log: bool = True) -> dict[str, Any]:
        """Run a registered function (see functions.py). With `trial`, a person tries out one still in draft; without
        `log`, the run is not kept in the function log."""
        from ontlas.functions import run_function

        return run_function(self, name, key, params, role=role, principal=principal, by=by, trial=trial, log=log)

    def keep_journal(self, path):
        """Keep requests, approvals, change requests and the audit trail in a file, so a restart forgets none of them.
        What the file already holds is taken back first. One process writes to one file."""
        from ontlas.journal import Journal

        journal = Journal(path)
        self.actions.keep(journal)
        self.changes.keep(journal)
        return journal

    def value_accuracy(self, specs: list[dict] | None = None) -> dict[str, Any]:
        """Hold what the ontology answers against what the transaction system shows (see review.value_accuracy)."""
        from ontlas.review import value_accuracy

        specs = self.flow.values if specs is None else specs
        if not specs:
            raise ValueError("no values are configured: give the flow a list of values to compare")
        return value_accuracy(self, specs)

    def agreement(self, spec: dict[str, Any] | None = None) -> dict[str, Any]:
        """Decide past cases again and compare with what was decided then (spec: see review.agreement)."""
        from ontlas.review import agreement

        spec = spec or self.flow.agreement
        if not spec:
            raise ValueError("no agreement is configured: give the flow an agreement with decision, query, expect")
        return agreement(self, spec)

    def sync(self) -> dict[str, Any]:
        """Read the source again and send each graph only what changed since its last load; the result is kept."""
        at = self.now().isoformat(timespec="seconds")
        graphs = list(self._loaded) or [n for n, b in self.backends.items() if b.capabilities.load]
        try:
            report = self.project(into=graphs) if graphs else {}
        except Exception as e:  # a source that is gone or a definition that no longer binds: kept as the result
            self.last_sync = {"at": at, "error": f"{type(e).__name__}: {e}", "changed": False}
            return self.last_sync
        changed = any(sum((v.get("changes") or {}).values()) for v in report.values())
        self.last_sync = {"at": at, "report": report, "changed": changed}
        return self.last_sync

    def resolve_identity(self, name: str, *, write: bool = True):
        """Join the records several systems keep for one thing (see identity.py); graphs are brought up to date."""
        from ontlas.identity import resolve

        report = resolve(self, name, write=write)
        if write and self._loaded:
            self.project(into=list(self._loaded))
        return report

    def column(self, type_name: str, prop: str) -> str:
        obj = self.onto.obj(type_name)
        return f"{obj.table}.{find_prop(self.onto, type_name, prop).col}"


def _default_params(onto: Ontology) -> dict[str, dict]:
    out: dict[str, dict] = {n: dict(q.example) for n, q in onto.queries.items() if q.example}
    for qs in onto.questions:
        if qs.query and qs.query not in out:
            out[qs.query] = dict(qs.params)
    return out


def _words(text: Any) -> str:
    return "".join(str(text or "").split()).lower()


def _graded(qs, matched: bool, said: str, grounds: str, gaps: list[str]) -> bool:
    """Whether an answer is right by the question's grading: as expected (match), when it says every keyword
    (keywords), or when it stands on its grounds and they name every keyword (evidence). Spaces and case aside."""
    by = qs.graded_by
    if by == "keywords":
        return all(_words(k) in _words(said) for k in qs.keywords)
    if by == "evidence":
        expected = qs.expect not in (None, "", [], {})
        return (matched or not expected) and not gaps and all(_words(k) in _words(grounds) for k in qs.keywords)
    return matched


def _defined(tools, qs) -> tuple[Any, bool, list[str], str, str]:
    """A question on what a word means, answered as the page answers it (no model): what was said, whether it says
    what was expected, what it lacks, the words to grade and the grounds it stands on."""
    from ontlas.answer import answer_question

    out = answer_question(tools, qs.text)
    words = (out.get("lexicon") or {}).get("matched") or []
    said = " ".join([out["answer"], *(f"{w['term']} {w['definition']}" for w in words),
                     *(d["title"] for d in out.get("definitions") or [])])
    grounds = " ".join([*(f"{s['title']} {s['text']}" for s in out.get("sources") or []),
                        *(f"{w['term']} {w['definition']}" for w in words if w["definition"])])
    gaps = [] if out.get("sources") or any(w["definition"] for w in words) else ["no answer"]
    want = qs.expect if isinstance(qs.expect, list) else [qs.expect] if qs.expect not in (None, "", {}) else []
    passed = bool(want) and all(_words(x) in _words(said) for x in want)
    return said[:400], passed, gaps, said, grounds


def _judge(expect: Any, res: Result, types: dict[str, str]) -> tuple[Any, bool]:
    rows = [{c: normalize(v, types.get(c, "")) for c, v in zip(res.columns, r)} for r in res.rows]
    if not isinstance(expect, dict):
        return rows, rows == expect
    if "rows" in expect:
        return len(rows), len(rows) == expect["rows"]
    if "column" in expect:
        got = [r[expect["column"]] for r in rows]
        return got, got == [normalize(v) for v in expect["values"]]
    if "first" in expect:
        first = rows[0] if rows else {}
        return first, all(first.get(k) == normalize(v) for k, v in expect["first"].items())
    return rows, False
