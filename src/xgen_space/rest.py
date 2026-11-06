"""The way in from anywhere: one small HTTP API any platform can call, described by OpenAPI and as agent tools.

The page's /api is for a browser session. This one has no session: a token, a role and JSON. Everything it does goes through
`StudioTools`, so a role's row limits and masks hold here as they do in MCP.
"""
from __future__ import annotations

import hmac
import threading
from typing import Any, Callable

from xgen_space.tools import StudioTools

Handler = Callable[[StudioTools, dict], Any]

ANY = {"description": "Any JSON value"}
STRING = {"type": "string"}
OBJECT = {"type": "object"}
INT = {"type": "integer"}

# path, method, tool name, what it does, the body it takes, the required fields, the handler
ROUTES: list[tuple[str, str, str, str, dict, list, Handler]] = [
    ("/v1/space", "GET", "describe_space", "What this space holds: documents, vector stores, embedder, graph stores, reasoners, ontology size.",
     {}, [], lambda t, b: t.describe_space()),
    ("/v1/ontology", "GET", "describe_ontology", "Object types, properties, links, registered queries, decisions and actions this token may use.",
     {}, [], lambda t, b: t.describe()),
    ("/v1/documents", "GET", "list_documents", "Documents in the space, with their sections and the concepts they mention.",
     {}, [], lambda t, b: t.list_documents()),
    ("/v1/search", "POST", "search_documents", "Search the space's documents by meaning. Returns passages with their document and section, and the ontology elements the question names.",
     {"text": STRING, "k": INT, "store": STRING, "where": OBJECT}, ["text"], lambda t, b: t.search_documents(b["text"], b.get("k", 5), b.get("store", ""), b.get("where"))),
    ("/v1/query", "POST", "run_query", "Run a registered query by name, or an IR JSON object, on a backend.",
     {"query": ANY, "params": OBJECT, "backend": STRING}, ["query"], lambda t, b: t.run_query(b["query"], b.get("params"), b.get("backend"))),
    ("/v1/translate", "POST", "translate_query", "The text of a query in a backend's language, to = sql:<dialect>, cypher, gql, sparql, pgq or gremlin.",
     {"query": ANY, "to": STRING}, ["query", "to"], lambda t, b: t.translate(b["query"], b["to"])),
    ("/v1/sparql", "POST", "run_sparql", "Run a SPARQL SELECT written against the ontology, on any backend, SQL ones included.",
     {"text": STRING, "backend": STRING}, ["text"], lambda t, b: t.run_sparql(b["text"], b.get("backend"))),
    ("/v1/cypher", "POST", "run_cypher", "Run a Cypher read query written against the ontology, on any backend, SQL ones included.",
     {"text": STRING, "params": OBJECT, "backend": STRING}, ["text"], lambda t, b: t.run_cypher(b["text"], b.get("params"), b.get("backend"))),
    ("/v1/decide", "POST", "decide", "Evaluate a decision table for one object: outputs, the rule that matched, the evidence.",
     {"decision": STRING, "key": STRING, "params": OBJECT}, ["decision", "key"], lambda t, b: t.decide(b["decision"], b["key"], b.get("params"))),
    ("/v1/actions", "POST", "request_action", "Request a declared action. Checks run now; a person approves it before anything is written.",
     {"action": STRING, "key": STRING, "params": OBJECT}, ["action", "key"], lambda t, b: t.request_action(b["action"], b["key"], b.get("params"))),
]


def openapi(version: str, server: str = "") -> dict:
    paths: dict[str, dict] = {}
    for path, method, name, summary, props, required, _ in ROUTES:
        op: dict[str, Any] = {"operationId": name, "summary": summary, "security": [{"bearer": []}],
                              "responses": {"200": {"description": "The answer", "content": {"application/json": {"schema": {"type": "object"}}}},
                                            "400": {"description": "The request cannot be answered; `error` says why"},
                                            "401": {"description": "No valid token"}, "403": {"description": "Outside this token's role"}}}
        if method == "POST":
            op["requestBody"] = {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "properties": props, "required": required}}}}
        paths[path] = {method.lower(): op}
    spec: dict[str, Any] = {"openapi": "3.1.0", "info": {"title": "XGEN Space", "version": version,
                                                        "description": "Documents, vectors, graphs and ontologies behind one API."},
                            "paths": paths, "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}}}
    if server:
        spec["servers"] = [{"url": server}]
    return spec


def tool_list() -> list[dict]:
    """The same operations as function definitions, for an agent framework that takes tools rather than OpenAPI."""
    return [{"name": name, "description": summary, "method": method, "path": path,
             "parameters": {"type": "object", "properties": props, "required": required}}
            for path, method, name, summary, props, required, _ in ROUTES]


class Rest:
    """With `source` it answers from the studio a team shares, under that studio's lock: what a person approved on the page
    is what a platform sees, and what a platform requests is what a person finds there."""

    def __init__(self, tools: StudioTools, token: str, *, source: Callable[[], Any] | None = None, lock: Any = None):
        self.tools, self.token, self.source = tools, token, source
        self.lock = lock or threading.Lock()

    def allowed(self, header: str) -> bool:
        return bool(self.token) and hmac.compare_digest(header.encode("utf-8"), f"Bearer {self.token}".encode("utf-8"))

    def answer(self, method: str, path: str, body: dict) -> tuple[int, Any]:
        if self.source is not None:
            self.tools.studio = self.source()
        for p, m, _, _, _, required, handler in ROUTES:
            if p != path:
                continue
            if m != method:
                return 405, {"error": f"{path} takes {m}"}
            missing = [k for k in required if k not in body]
            if missing:
                return 400, {"error": "missing: " + ", ".join(missing)}
            try:
                return 200, handler(self.tools, body)
            except PermissionError as e:
                return 403, {"error": str(e)}
            except (ValueError, LookupError, KeyError, TypeError, RuntimeError) as e:
                return 400, {"error": f"{type(e).__name__}: {e}"}
        return 404, {"error": "no such path"}
