"""MCP server: the studio's tools for agents in any MCP client, over stdio or HTTP."""
from __future__ import annotations

import contextlib
import functools
import sys
from pathlib import Path
from typing import Any, Callable

from xgen_space.studio import Studio
from xgen_space.tools import StudioTools

with contextlib.redirect_stdout(sys.stderr):
    try:
        import rdflib.plugins.sparql  # noqa: F401
    except ImportError:
        pass


def _server_class():
    try:
        from mcp.server.mcpserver import MCPServer

        return MCPServer
    except ImportError:
        pass
    try:
        from mcp.server.fastmcp import FastMCP

        return FastMCP
    except ImportError as e:
        raise ImportError("the MCP server needs the [mcp] extra") from e


def _tool_error():
    for mod in ("mcp.server.mcpserver.exceptions", "mcp.server.fastmcp.exceptions"):
        try:
            return __import__(mod, fromlist=["ToolError"]).ToolError
        except ImportError:
            continue
    return RuntimeError


def _guard(fn):
    err = _tool_error()

    @functools.wraps(fn)
    def run(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (PermissionError, KeyError, ValueError) as e:
            raise err(f"{type(e).__name__}: {e}") from e

    return run


def following(config: str | Path, studio: Studio, journal: str | Path | None = None) -> Callable[[], Studio]:
    """The studio of a file, read again once an approved change reaches its library: a running agent goes by the rules in force.
    A library that cannot be read keeps the studio it had, and says so. With a journal, the studio read again takes back
    the requests and audit trail the one before kept."""
    import yaml

    from xgen_space.config import load_studio

    root = studio.library.root if studio.library is not None else None

    def stamp() -> list:
        return sorted((str(p), p.stat().st_mtime_ns) for p in Path(root).rglob("*.yaml")) if root else []

    seen = stamp()

    def current() -> Studio:
        nonlocal studio, seen
        now = stamp()
        if now != seen:
            seen = now
            try:
                studio = load_studio(config)
                if journal:
                    studio.keep_journal(journal)
            except (OSError, ValueError, yaml.YAMLError) as e:
                print(f"library changed but could not be read: {e}", file=sys.stderr)
        return studio

    return current


def build_server(studio: Studio, *, role: str | None = None, principal: dict | None = None,
                 read_only: bool = False, name: str = "xgen-space", fresh: Callable[[], Studio] | None = None,
                 agent: str = ""):
    tools = StudioTools(studio, role=role, principal=principal, read_only=read_only, actor_id=agent or "agent", audit=True)
    raw = _server_class()(name)

    def current(fn):
        @functools.wraps(fn)
        def run(*args, **kwargs):
            if fresh is not None:
                tools.studio = fresh()
            return fn(*args, **kwargs)

        return run

    class _Server:
        def tool(self):
            return lambda fn: raw.tool()(_guard(current(fn)))

    server = _Server()

    @server.tool()
    def describe_ontology() -> dict:
        """Object types, properties, links, registered queries, decisions and actions this agent may use."""
        return tools.describe()

    @server.tool()
    def answer_question(text: str, folder: str = "") -> dict:
        """Answer one question from the decisions, the data and the documents, with the rule, the source values and the clause.
        With a folder, only the documents of that folder are read."""
        return tools.answer_question(text, folder)

    @server.tool()
    def agent_context(text: str, k: int = 8) -> dict:
        """The definitions and rules a question is about, as text to put in a prompt."""
        return tools.agent_context(text, k)

    @server.tool()
    def find_definitions(text: str, k: int = 8) -> dict:
        """The object types, rules, queries and actions a question is about. Read these rather than the whole ontology."""
        return tools.find_definitions(text, k)

    @server.tool()
    def describe_object(name: str) -> dict:
        """One object type with its properties, links, decisions and actions."""
        return tools.describe_object(name)

    @server.tool()
    def list_modules() -> list[dict]:
        """The ontology modules plugged into this studio: core concepts, domains, industry and customer layers."""
        return tools.list_modules()

    @server.tool()
    def list_backends() -> dict:
        """Backends this studio can run queries on, with what each supports."""
        return tools.list_backends()

    @server.tool()
    def translate_query(query: Any, to: str) -> dict:
        """Show the backend text for a query (registered name or IR JSON); to = sql:<dialect>|cypher|gql|sparql|sqlpgq."""
        return tools.translate(query, to)

    @server.tool()
    def run_query(query: Any, params: dict | None = None, backend: str | None = None) -> dict:
        """Run a registered query by name, or an IR JSON object, on a backend (default: the source database)."""
        return tools.run_query(query, params, backend)

    @server.tool()
    def run_sparql(text: str, backend: str | None = None) -> dict:
        """Run a SPARQL SELECT written against the ontology on any backend, including SQL databases."""
        return tools.run_sparql(text, backend)

    @server.tool()
    def run_cypher(text: str, params: dict | None = None, backend: str | None = None) -> dict:
        """Run a Cypher read query written against the ontology on any backend, including SQL databases."""
        return tools.run_cypher(text, params, backend)

    @server.tool()
    def decide(decision: str, key: str, params: dict | None = None) -> dict:
        """Evaluate a decision table for one object; returns the outputs, the rule that matched and the evidence."""
        return tools.decide(decision, key, params)

    @server.tool()
    def list_functions() -> dict:
        """The functions this agent may run, with what they take and give, their versions and owners."""
        return tools.list_functions()

    @server.tool()
    def run_function(name: str, key: str = "", params: dict | None = None) -> dict:
        """Run a registered function on one object, or on its inputs alone."""
        return tools.run_function(name, key, params)

    if not read_only:
        @server.tool()
        def request_action(action: str, key: str, params: dict | None = None) -> dict:
            """Request a declared action; checks run now, and a person approves it before anything is written."""
            return tools.request_action(action, key, params)

    @server.tool()
    def describe_space() -> dict:
        """What this space holds: documents, vector stores, embedder, graph stores, reasoners, ontology size."""
        return tools.describe_space()

    @server.tool()
    def list_documents() -> dict:
        """Documents in the space with their sections."""
        return tools.list_documents()

    @server.tool()
    def search_documents(text: str, k: int = 5, store: str = "", folder: str = "") -> dict:
        """Search the space's documents by meaning: passages with their document and section, and the ontology elements
        the question names, so an answer can go on to run_query or decide. With a folder, only that folder's documents."""
        return tools.search_documents(text, k, store, folder=folder)

    @server.tool()
    def list_proposals() -> list[dict]:
        """The action requests this agent made and their status (pending, rejected, executed, rolled back)."""
        return tools.list_proposals()

    @server.tool()
    def get_record(type_name: str, key: str) -> dict:
        """One object's values by its key, inside this agent's rows and with its masks."""
        return tools.get_record(type_name, key)

    return raw


def main(argv: list[str] | None = None) -> None:
    import argparse

    from xgen_space.config import load_studio

    ap = argparse.ArgumentParser(prog="xspace mcp")
    ap.add_argument("config")
    ap.add_argument("--role")
    ap.add_argument("--principal", action="append", default=[], help="key=value")
    ap.add_argument("--read-only", action="store_true")
    ap.add_argument("--agent", default="", help="the name the audit trail gives this agent")
    ap.add_argument("--journal", default="", help="a file of this process's own that keeps its requests and audit trail")
    ap.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    a = ap.parse_args(argv)
    principal = dict(x.split("=", 1) for x in a.principal)
    studio = load_studio(a.config)
    if a.journal:
        studio.keep_journal(a.journal)
    server = build_server(studio, role=a.role, principal=principal, read_only=a.read_only, agent=a.agent,
                          fresh=following(a.config, studio, a.journal or None))
    server.run(a.transport)
