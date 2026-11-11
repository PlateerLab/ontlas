"""Reasoner port: facts and shape checks from any engine, on the same projection.

A reasoner gets the ontology and the data as they stand and says what follows. `rules` is built in and needs nothing, `owlrl`
and `reasonable` are two independent OWL 2 RL engines, `shacl` checks shapes, and `http` hands the turtle to a service of
yours. `agreement` runs engines of the same logic side by side, the way conformance does for query backends.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from ontlas.model import Ontology
from ontlas.projection import Projection


@dataclass
class Inference:
    reasoner: str
    kind: str
    derived: list[tuple[str, str, str]] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    ms: int = 0
    error: str = ""

    def to_dict(self, sample: int = 20) -> dict:
        d = asdict(self)
        d["derived"] = [list(t) for t in self.derived[:sample]]
        d["count"] = len(self.derived)
        return d


class Reasoner:
    kind = ""
    name = ""
    logic = ""  # engines of the same logic should agree

    def infer(self, onto: Ontology, projection: Projection) -> tuple[list[tuple[str, str, str]], list[dict]]:
        raise NotImplementedError

    def available(self) -> str:
        """Why it cannot run here, or nothing."""
        return ""

    def run(self, onto: Ontology, projection: Projection) -> Inference:
        started = time.perf_counter()
        out = Inference(self.name, self.kind)
        try:
            out.derived, out.findings = self.infer(onto, projection)
        except ImportError as e:
            out.error = str(e)
        except (OSError, ValueError, RuntimeError) as e:
            out.error = f"{type(e).__name__}: {e}"
        out.ms = round((time.perf_counter() - started) * 1000)
        return out

    def describe(self) -> dict:
        return {"name": self.name, "kind": self.kind, "logic": self.logic, "missing": self.available()}


class RulesReasoner(Reasoner):
    kind, name, logic = "rules", "rules", "rules"

    def infer(self, onto, projection):
        from ontlas.reason.rules import run_rules

        r = run_rules(onto, projection)
        return ([(f"{e.source_type}:{e.source_key}", e.link, f"{e.target_type}:{e.target_key}") for e in r.derived],
                [asdict(f) for f in r.findings])


class OwlRlReasoner(Reasoner):
    kind, name, logic = "owlrl", "owlrl", "owl2rl"

    def available(self) -> str:
        try:
            import owlrl  # noqa: F401
            return ""
        except ImportError:
            return "owlrl 미설치"

    def infer(self, onto, projection):
        from ontlas.reason.owl_rl import materialize

        return materialize(onto, projection), []


class ReasonableReasoner(Reasoner):
    """A second OWL 2 RL engine, written in Rust. Not on the default list: `agreement` shows why. Version 0.4.4 joins every
    subject of an inverse functional property with sameAs whatever their objects, which the two-engine run caught here."""

    kind, name, logic = "reasonable", "reasonable", "owl2rl"

    def available(self) -> str:
        try:
            import reasonable  # noqa: F401
            return ""
        except ImportError:
            return "reasonable 미설치"

    def infer(self, onto, projection):
        import rdflib
        import reasonable

        from ontlas.exchange.owl import to_owl
        from ontlas.rdf import RDF_TYPE, Iris

        g = rdflib.Graph()
        g.parse(data=to_owl(onto)[0], format="turtle")
        g.parse(data=projection.ntriples(onto), format="turtle")
        engine = reasonable.PyReasoner()
        engine.from_graph(g)
        ir, out = Iris(onto), []
        before = {(str(s), str(p), str(o)) for s, p, o in g}
        for s, p, o in engine.reason():
            s, p, o = str(s), str(p), str(o)
            if (s, p, o) in before or ir.key_of(s) is None:
                continue
            if p == RDF_TYPE:
                if ir.local(o) in onto.objects:
                    out.append((s, p, o))
            elif ir.local(p) is not None and ir.key_of(o):
                out.append((s, p, o))
        return sorted(set(out)), []


class ShaclReasoner(Reasoner):
    kind, name, logic = "shacl", "shacl", "shapes"

    def available(self) -> str:
        try:
            import pyshacl  # noqa: F401
            return ""
        except ImportError:
            return "pyshacl 미설치"

    def infer(self, onto, projection):
        from ontlas.reason.shacl import validate

        r = validate(onto, projection)
        return [], [] if r.conforms else [dict(x) for x in r.results]


class HttpReasoner(Reasoner):
    """Any service that takes turtle and answers with the turtle it derived: a reasoner this package has never heard of."""

    kind, logic = "http", "external"

    def __init__(self, url: str, *, name: str = "http", timeout: float = 60.0, key: str = ""):
        self.url, self.name, self.timeout, self.key = url, name, timeout, key

    def infer(self, onto, projection):
        import rdflib

        from ontlas.exchange.owl import to_owl

        body = (to_owl(onto)[0] + "\n" + projection.turtle(onto)).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST", headers={"Content-Type": "text/turtle", "Accept": "text/turtle"})
        if self.key:
            req.add_header("Authorization", "Bearer " + self.key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                text = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"reasoner answered {e.code}") from None
        g = rdflib.Graph()
        g.parse(data=text, format="turtle")
        return sorted((str(s), str(p), str(o)) for s, p, o in g), []


_KINDS: dict[str, Callable[[dict], Reasoner]] = {
    "rules": lambda s: RulesReasoner(), "owlrl": lambda s: OwlRlReasoner(), "reasonable": lambda s: ReasonableReasoner(),
    "shacl": lambda s: ShaclReasoner(),
    "http": lambda s: HttpReasoner(s["url"], name=s.get("name", "http"), timeout=float(s.get("timeout", 60)), key=s.get("key", "")),
}


def register_reasoner(kind: str, make: Callable[[dict], Reasoner]) -> None:
    """An engine the package does not know joins by name: `reasoners: {mine: {kind: <yours>}}` in a studio file."""
    _KINDS[kind] = make


def open_reasoner(spec: dict) -> Reasoner:
    kind = spec.get("kind", "rules")
    if kind not in _KINDS:
        raise ValueError(f"unknown reasoner kind '{kind}'; known: {', '.join(sorted(_KINDS))}")
    return _KINDS[kind](spec)


def open_reasoners(spec: dict | None) -> dict[str, Reasoner]:
    """What a studio file names, or the built-in engines."""
    if spec:
        return {n: open_reasoner({**s, "name": s.get("name", n)}) for n, s in spec.items()}
    return {k: open_reasoner({"kind": k}) for k in ("rules", "owlrl", "shacl")}


def agreement(reasoners: dict[str, Reasoner], onto: Ontology, projection: Projection,
              ran: dict[str, Inference] | None = None) -> dict[str, Any]:
    """Engines of one logic on the same data: the same facts, or what each found that the other did not.
    `ran` holds inferences already made on this data, so an engine is not run twice."""
    groups: dict[str, dict[str, Inference]] = {}
    for n, r in reasoners.items():
        if r.logic and r.logic not in ("rules", "shapes", "external") and not r.available():
            groups.setdefault(r.logic, {})[n] = (ran or {}).get(n) or r.run(onto, projection)
    out = {}
    for logic, runs in groups.items():
        ok = {n: set(i.derived) for n, i in runs.items() if not i.error}
        names = sorted(ok)
        same = len({frozenset(v) for v in ok.values()}) <= 1
        only = {n: sorted(ok[n] - set.union(*(ok[m] for m in names if m != n)))[:5] for n in names} if len(names) > 1 else {}
        out[logic] = {"engines": {n: {"count": len(i.derived), "ms": i.ms, "error": i.error} for n, i in runs.items()},
                      "same": same, "only": only}
    return out
