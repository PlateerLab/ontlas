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


def following(config: str | Path, studio: Studio) -> Callable[[], Studio]:
    """The studio of a file, read again once an approved change reaches its library: a running agent goes by the rules in force.
    A library that cannot be read keeps the studio it had, and says so."""
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
            except (OSError, ValueError, yaml.YAMLError) as e:
                print(f"library changed but could not be read: {e}", file=sys.stderr)
        return studio

    return current


def build_server(studio: Studio, *, role: str | None = None, principal: dict | None = None,
                 read_only: bool = False, name: str = "xgen-space", fresh: Callable[[], Studio] | None = None):
    tools = StudioTools(studio, role=role, principal=principal, read_only=read_only)
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
    def answer_question(text: str) -> dict:
        """Answer one question from the decisions, the data and the documents, with the rule, the source values and the clause."""
        return tools.answer_question(text)

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
    def search_documents(text: str, k: int = 5, store: str = "") -> dict:
        """Search the space's documents by meaning: passages with their document and section, and the ontology elements
        the question names, so an answer can go on to run_query or decide."""
        return tools.search_documents(text, k, store)

    @server.tool()
    def list_proposals() -> list[dict]:
        """Action requests and their status (pending, rejected, executed)."""
        return tools.list_proposals()

    return raw


def main(argv: list[str] | None = None) -> None:
    import argparse

    from xgen_space.config import load_studio

    ap = argparse.ArgumentParser(prog="xspace mcp")
    ap.add_argument("config")
    ap.add_argument("--role")
    ap.add_argument("--principal", action="append", default=[], help="key=value")
    ap.add_argument("--read-only", action="store_true")
    ap.add_argument("--transport", default="stdio", choices=["stdio", "sse", "streamable-http"])
    a = ap.parse_args(argv)
    principal = dict(x.split("=", 1) for x in a.principal)
    studio = load_studio(a.config)
    server = build_server(studio, role=a.role, principal=principal, read_only=a.read_only, fresh=following(a.config, studio))
    server.run(a.transport)
