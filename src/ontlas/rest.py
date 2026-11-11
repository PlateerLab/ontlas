"""The way in from anywhere: one small HTTP API any platform can call, described by OpenAPI and as agent tools.

The page's /api is for a browser session. This one has no session: a token, a role and JSON. Everything it does goes through
`StudioTools`, so a role's row limits and masks hold here as they do in MCP.
"""
from __future__ import annotations

import hmac
import threading
from typing import Any, Callable

from ontlas.backends.base import NoSource
from ontlas.tools import StudioTools

Handler = Callable[[StudioTools, dict], Any]

ANY = {"type": "string", "description": "The name of a registered query, or an IR query as JSON text"}
STRING = {"type": "string"}
OBJECT = {"type": "object"}
INT = {"type": "integer"}

# path, method, tool name, what it does, the body it takes, the required fields, the handler
ROUTES: list[tuple[str, str, str, str, dict, list, Handler]] = [
    ("/v1/space", "GET", "describe_space", "What this space holds: documents, vector stores, embedder, graph stores, reasoners, ontology size.",
     {}, [], lambda t, b: t.describe_space()),
    ("/v1/ontology", "GET", "describe_ontology", "Object types, properties, links, registered queries, decisions and actions this token may use.",
     {}, [], lambda t, b: t.describe()),
    ("/v1/answer", "POST", "answer_question", "Answer one question from the decisions, the data and the documents, with the rule, the source values and the clause it stands on.",
     {"text": STRING, "folder": STRING}, ["text"], lambda t, b: t.answer_question(b["text"], folder=b.get("folder", ""))),
    ("/v1/context", "POST", "agent_context", "The definitions and rules a question is about, as text to put in an agent's prompt.",
     {"text": STRING, "k": INT}, ["text"], lambda t, b: t.agent_context(b["text"], b.get("k", 8))),
    ("/v1/find", "POST", "find_definitions", "The object types, rules, queries and actions a question is about. Read these rather than the whole ontology.",
     {"text": STRING, "k": INT}, ["text"], lambda t, b: t.find_definitions(b["text"], b.get("k", 8))),
    ("/v1/object", "POST", "describe_object", "One object type with its properties, links, decisions and actions.",
     {"name": STRING}, ["name"], lambda t, b: t.describe_object(b["name"])),
    ("/v1/documents", "GET", "list_documents", "Documents in the space, with their sections and the concepts they mention.",
     {}, [], lambda t, b: t.list_documents()),
    ("/v1/search", "POST", "search_documents", "Search the space's documents by meaning. Returns passages with their document and section, and the ontology elements the question names.",
     {"text": STRING, "k": INT, "store": STRING, "where": OBJECT, "folder": STRING}, ["text"],
     lambda t, b: t.search_documents(b["text"], b.get("k", 5), b.get("store", ""), b.get("where"), b.get("folder", ""))),
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
    ("/v1/functions", "GET", "list_functions", "The functions this token may run, with what they take and give, their versions and owners.",
     {}, [], lambda t, b: t.list_functions()),
    ("/v1/function", "POST", "run_function", "Run a registered function on one object, or on its inputs alone.",
     {"name": STRING, "key": STRING, "params": OBJECT}, ["name"], lambda t, b: t.run_function(b["name"], b.get("key", ""), b.get("params"))),
    ("/v1/actions", "POST", "request_action", "Request a declared action. Checks run now; a person approves it before anything is written, unless the change is inside the action's limits.",
     {"action": STRING, "key": STRING, "params": OBJECT}, ["action", "key"], lambda t, b: t.request_action(b["action"], b["key"], b.get("params"))),
    ("/v1/proposals", "GET", "list_proposals", "The action requests this token made and how each stands: pending, executed, rejected, rolled back.",
     {}, [], lambda t, b: {"proposals": t.list_proposals()}),
    ("/v1/record", "POST", "get_record", "One object's values by its key, inside this token's rows and with its masks.",
     {"object": STRING, "key": STRING}, ["object", "key"], lambda t, b: t.get_record(b["object"], b["key"])),
]


def openapi(version: str, server: str = "") -> dict:
    paths: dict[str, dict] = {}
    for path, method, name, summary, props, required, _ in ROUTES:
        op: dict[str, Any] = {"operationId": name, "summary": summary, "security": [{"bearer": []}],
                              "responses": {"200": {"description": "The answer", "content": {"application/json": {"schema": {"type": "object"}}}},
                                            "400": {"description": "The request cannot be answered; `error` says why"},
                                            "409": {"description": "It reads rows and no source is connected (`no_source`)"},
                                            "401": {"description": "No valid token"}, "403": {"description": "Outside this token's role"}}}
        if method == "POST":
            op["requestBody"] = {"required": True, "content": {"application/json": {"schema": {
                "type": "object", "properties": props, "required": required}}}}
        paths[path] = {method.lower(): op}
    spec: dict[str, Any] = {"openapi": "3.1.0", "info": {"title": "Ontlas", "version": version,
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
    is what a platform sees, and what a platform requests is what a person finds there.

    Each token is one caller with its own name, role and rows: the audit trail says which agent asked, and one agent's
    requests are not another's to read."""

    def __init__(self, clients: list[tuple[str, StudioTools]] | StudioTools, token: str = "", *,
                 source: Callable[[], Any] | None = None, lock: Any = None):
        self.clients = [(token, clients)] if isinstance(clients, StudioTools) else list(clients)
        self.source = source
        self.lock = lock or threading.Lock()

    @property
    def tools(self) -> StudioTools:
        return self.clients[0][1]

    def caller(self, header: str) -> StudioTools | None:
        """The tools of the client whose token this is. Every token is compared, so the time taken says nothing."""
        found = None
        for token, tools in self.clients:
            if token and hmac.compare_digest(header.encode("utf-8"), f"Bearer {token}".encode("utf-8")):
                found = tools
        return found

    def allowed(self, header: str) -> bool:
        return self.caller(header) is not None

    def answer(self, method: str, path: str, body: dict, tools: StudioTools | None = None) -> tuple[int, Any]:
        tools = tools or self.tools
        if self.source is not None:
            tools.studio = self.source()
        for p, m, _, _, _, required, handler in ROUTES:
            if p != path:
                continue
            if m != method:
                return 405, {"error": f"{path} takes {m}"}
            missing = [k for k in required if k not in body]
            if missing:
                return 400, {"error": "missing: " + ", ".join(missing)}
            try:
                return 200, handler(tools, body)
            except PermissionError as e:
                return 403, {"error": str(e)}
            except NoSource as e:  # the space holds its definition only: a caller tells this from a bad request
                return 409, {"error": str(e), "no_source": True}
            except (ValueError, LookupError, KeyError, TypeError, RuntimeError) as e:
                return 400, {"error": f"{type(e).__name__}: {e}"}
        return 404, {"error": "no such path"}
