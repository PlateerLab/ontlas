"""RDF backends: an in-process rdflib graph, or any SPARQL 1.1 endpoint over HTTP."""
from __future__ import annotations

import base64
import json
import threading
import urllib.parse
import urllib.request
from typing import Any

from ontlas.backends.base import Backend, Capabilities, Result
from ontlas.compile.base import Compiled

# pyparsing, which reads SPARQL for rdflib, works out how many arguments each parse action takes the first time it calls
# it. Two threads doing that at once leave it wrong for the life of the process, and every later query then fails with
# "<lambda>() missing 1 required positional argument: 'x'" (a server whose first visitors arrive together). Reading a
# query or an update is therefore one thread at a time; running it is not.
_READING = threading.Lock()


def prepare_query(text: str, **kw: Any) -> Any:
    from rdflib.plugins.sparql import prepareQuery

    with _READING:
        return prepareQuery(text, **kw)


def prepare_update(text: str, **kw: Any) -> Any:
    from rdflib.plugins.sparql import prepareUpdate

    with _READING:
        return prepareUpdate(text, **kw)


def connected(triples: list[tuple], bound=lambda term: False) -> list[tuple]:
    """A triple pattern order where each pattern shares a variable with what is bound before it, wherever one does."""
    from rdflib import BNode, Variable

    def free(term) -> bool:
        return isinstance(term, (Variable, BNode))

    left, out = list(triples), []
    seen = {x for t in left for x in t if free(x) and bound(x)}
    while left:
        best = max(left, key=lambda t: (sum(free(x) and x in seen for x in t), sum(not free(x) for x in t)))
        left.remove(best)
        out.append(best)
        seen.update(x for x in best if free(x))
    return out


def _walk(ctx, part):
    """rdflib runs the patterns with the fewest free terms first, so every `?x a :Type` goes first and a path of n hops
    becomes the product of n classes: 70 orders and 115 items along five hops took minutes. Here a basic graph pattern
    walks along what it has bound."""
    from rdflib.plugins.sparql.evaluate import evalBGP

    if part.name != "BGP":
        raise NotImplementedError
    return evalBGP(ctx, connected(part.triples, lambda term: ctx[term] is not None))


class RdflibBackend(Backend):
    kind = "rdflib"

    def __init__(self, graph: Any = None, name: str = "rdflib"):
        try:
            import rdflib
        except ImportError as e:
            raise ImportError("RdflibBackend needs the [rdf] extra (rdflib)") from e
        from rdflib.plugins.sparql import CUSTOM_EVALS

        CUSTOM_EVALS["ontlas-walk"] = _walk
        self.graph = graph if graph is not None else rdflib.Graph()
        self.name = name
        self.capabilities = Capabilities("sparql", "1.1", load=True, reasoning=["owlrl"])

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        text, _ = compiled.bind(values)
        res = self.graph.query(prepare_query(text, initNs=dict(self.graph.namespaces())))  # the prefixes a text query gets
        rows = []
        for r in res:
            rows.append(tuple(_py(r[c]) if c in r.labels else None for c in compiled.columns))
        return Result(compiled.columns, rows, self.name, compiled)

    def load_turtle(self, ttl: str, *, clear: bool = False) -> None:
        if clear:
            self.graph.remove((None, None, None))
        self.graph.parse(data=ttl, format="turtle")

    def update(self, sparql_update: str) -> None:
        self.graph.update(prepare_update(sparql_update, initNs=dict(self.graph.namespaces())))


def _py(v: Any) -> Any:
    if v is None:
        return None
    return v.toPython() if hasattr(v, "toPython") else v


class SparqlEndpointBackend(Backend):
    """Fuseki, GraphDB, Stardog, Virtuoso, Oxigraph server, Neptune RDF: anything speaking SPARQL 1.1 over HTTP."""
    kind = "sparql"

    def __init__(self, query_url: str, *, update_url: str = "", gsp_url: str = "", user: str = "",
                 password: str = "", timeout: float = 60, name: str = "sparql"):
        self.query_url, self.update_url, self.gsp_url = query_url, update_url, gsp_url
        self.timeout = timeout
        self.name = name
        self._auth = ("Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()) if user else ""
        self.capabilities = Capabilities("sparql", "1.1", load=bool(update_url or gsp_url))

    def _post(self, url: str, body: bytes, ctype: str, accept: str = "") -> bytes:
        headers = {"Content-Type": ctype}
        if accept:
            headers["Accept"] = accept
        if self._auth:
            headers["Authorization"] = self._auth
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return r.read()

    def execute(self, compiled: Compiled, values: dict[str, Any] | None = None) -> Result:
        text, _ = compiled.bind(values)
        raw = self._post(self.query_url, urllib.parse.urlencode({"query": text}).encode(),
                         "application/x-www-form-urlencoded", "application/sparql-results+json")
        data = json.loads(raw)
        rows = [tuple(_term(b.get(c)) for c in compiled.columns) for b in data["results"]["bindings"]]
        return Result(compiled.columns, rows, self.name, compiled)

    def load_turtle(self, ttl: str, *, clear: bool = False) -> None:
        if self.gsp_url:
            url = self.gsp_url + ("&" if "?" in self.gsp_url else "?") + "default"
            req = urllib.request.Request(url, data=ttl.encode(), method="PUT" if clear else "POST",
                                         headers={"Content-Type": "text/turtle",
                                                  **({"Authorization": self._auth} if self._auth else {})})
            with urllib.request.urlopen(req, timeout=self.timeout):
                return
        if not self.update_url:
            raise RuntimeError(f"{self.name}: no update or graph store URL to load into")
        from ontlas.projection import turtle_to_insert

        if clear:
            self.update("CLEAR DEFAULT")
        self.update(turtle_to_insert(ttl))

    def update(self, sparql_update: str) -> None:
        if not self.update_url:
            raise RuntimeError(f"{self.name}: no update URL")
        self._post(self.update_url, urllib.parse.urlencode({"update": sparql_update}).encode(),
                   "application/x-www-form-urlencoded")


_XSD = "http://www.w3.org/2001/XMLSchema#"


def _term(b: dict | None) -> Any:
    if b is None:
        return None
    v, dt = b.get("value"), b.get("datatype", "")
    if dt in (_XSD + "integer", _XSD + "int", _XSD + "long"):
        return int(v)
    if dt in (_XSD + "decimal", _XSD + "double", _XSD + "float"):
        return float(v)
    if dt == _XSD + "boolean":
        return v == "true"
    return v
