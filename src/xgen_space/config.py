"""Studio configuration file: the ontology, the backends to open, and what to project at start."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from xgen_space.model import Ontology
from xgen_space.studio import Studio

_ENV = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _env(v: Any) -> Any:
    if isinstance(v, str):
        return _ENV.sub(lambda m: os.environ.get(m.group(1), ""), v)
    if isinstance(v, dict):
        return {k: _env(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_env(x) for x in v]
    return v


def open_backend(spec: dict, base: Path):
    kind = spec.get("kind")
    if kind == "sqlite":
        from xgen_space.backends.sql import SqliteBackend

        path = spec.get("path", ":memory:")
        b = SqliteBackend(path if path == ":memory:" else str(base / path))
        seeds = spec.get("seed") or []
        for s in [seeds] if isinstance(seeds, str) else seeds:
            b.script((base / s).read_text(encoding="utf-8"))
        return b
    if kind == "postgres":
        import psycopg

        from xgen_space.backends.sql import DbApiBackend

        return DbApiBackend(psycopg.connect(spec["dsn"], connect_timeout=10), "postgres", paramstyle="format")
    if kind == "mysql":
        import pymysql

        from xgen_space.backends.sql import DbApiBackend

        u = urlparse(spec["dsn"])
        conn = pymysql.connect(host=u.hostname or "localhost", port=u.port or 3306, user=unquote(u.username or ""),
                               password=unquote(u.password or ""), database=u.path.lstrip("/"), charset="utf8mb4",
                               connect_timeout=10)
        with conn.cursor() as cur:  # the studio's SQL quotes names the standard way
            cur.execute("SET SESSION sql_mode = CONCAT(@@sql_mode, ',ANSI_QUOTES')")
        return DbApiBackend(conn, "mysql", paramstyle="format")
    if kind == "oracle":
        import oracledb

        from xgen_space.backends.sql import DbApiBackend

        oracledb.defaults.fetch_lobs = False
        u = urlparse(spec["dsn"])
        conn = oracledb.connect(user=unquote(u.username or ""), password=unquote(u.password or ""),
                                dsn=f"{u.hostname or 'localhost'}:{u.port or 1521}{u.path}", tcp_connect_timeout=10)
        with conn.cursor() as cur:  # dates read as text, and ISO text bound to a date column, are ISO as elsewhere
            cur.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD\"T\"HH24:MI:SS' "
                        "NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD\"T\"HH24:MI:SS' NLS_NUMERIC_CHARACTERS = '.,' "
                        "NLS_SORT = BINARY NLS_COMP = BINARY")
        return DbApiBackend(conn, "oracle", paramstyle="numeric")
    if kind == "mssql":
        import pymssql

        from xgen_space.backends.sql import DbApiBackend

        u = urlparse(spec["dsn"])
        conn = pymssql.connect(server=u.hostname or "localhost", port=u.port or 1433, user=unquote(u.username or ""),
                               password=unquote(u.password or ""), database=u.path.lstrip("/"), charset="UTF-8",
                               login_timeout=15)
        return DbApiBackend(conn, "tsql", paramstyle="pymssql")
    if kind == "dbapi":
        import importlib

        from xgen_space.backends.sql import DbApiBackend

        mod = importlib.import_module(spec["module"])
        conn = mod.connect(**spec.get("connect", {}))
        return DbApiBackend(conn, spec.get("dialect", "postgres"), paramstyle=spec.get("paramstyle", "format"))
    if kind == "rdflib":
        from xgen_space.backends.rdf import RdflibBackend

        return RdflibBackend()
    if kind == "sparql":
        from xgen_space.backends.rdf import SparqlEndpointBackend

        return SparqlEndpointBackend(spec["query_url"], update_url=spec.get("update_url", ""),
                                     gsp_url=spec.get("gsp_url", ""), user=spec.get("user", ""),
                                     password=spec.get("password", ""))
    if kind == "gremlin":
        from xgen_space.backends.gremlin import GremlinBackend

        return GremlinBackend(spec.get("url", "ws://localhost:8182/gremlin"), source=spec.get("source", "g"))
    if kind == "gateway":
        from xgen_space.backends.gateway import GatewayBackend

        return GatewayBackend(spec["url"], connection=spec["connection"], dialect=spec.get("dialect", "postgres"),
                              token=spec.get("token", ""), token_env=spec.get("token_env", ""),
                              max_rows=spec.get("max_rows", 500), timeout=spec.get("timeout", 30), fields=spec.get("fields"))
    if kind == "neo4j":
        import neo4j

        from xgen_space.backends.graph import Neo4jBackend

        driver = neo4j.GraphDatabase.driver(spec["uri"], auth=(spec.get("user", "neo4j"), spec.get("password", "")))
        return Neo4jBackend(driver, database=spec.get("database"))
    raise ValueError(f"unknown backend kind '{kind}'")


def load_studio(path: str | Path) -> Studio:
    """A studio from its file. What was switched on and kept beside the library comes first; if that no longer loads,
    the file's own list still does, so a module that stopped fitting the source cannot keep a studio from starting."""
    try:
        return _open_studio(path, True)
    except Exception as e:  # a driver's own error: whatever a source says of a module that does not fit it
        if not _keeps_modules(path):
            raise
        print(f"the modules kept on no longer load ({e}); starting from {Path(path).name}", file=sys.stderr)
        return _open_studio(path, False)


def _keeps_modules(path: str | Path) -> bool:
    import yaml

    from xgen_space.library import Library

    p = Path(path)
    spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return bool(spec.get("modules")) and bool(Library(p.parent / spec.get("library", ".")).applied())


def _open_studio(path: str | Path, applied: bool) -> Studio:
    import yaml

    p = Path(path)
    spec = _env(yaml.safe_load(p.read_text(encoding="utf-8")))
    base = p.parent
    now = None
    if spec.get("now"):
        fixed = datetime.fromisoformat(str(spec["now"]))
        now = lambda: fixed  # noqa: E731
    kw = {"now": now, "use_zen": bool(spec.get("zen", False))}
    if spec.get("modules"):
        from xgen_space.library import Library
        from xgen_space.manage import NAME

        lib = Library(base / spec.get("library", "."))
        kept = lib.applied() if applied else []
        wanted = kept or list(spec["modules"])
        if NAME in lib.names() and NAME not in wanted:  # what the management screens approved belongs to this studio
            wanted.append(NAME)
        studio = Studio.from_library(lib, wanted, namespace=spec.get("namespace", ""), name=spec.get("name", ""), **kw)
    else:
        studio = Studio(Ontology.load(base / spec["ontology"]).check(), **kw)
    for name, b in (spec.get("backends") or {}).items():
        studio.add_backend(name, open_backend(b, base), source=bool(b.get("source", False)))
    calls = (spec.get("actions") or {}).get("call_hosts")
    if calls:
        from xgen_space.actions import HttpCaller

        studio.actions.caller = HttpCaller(list(calls), float((spec.get("actions") or {}).get("timeout", 10)))
    studio.settings = {k: spec[k] for k in ("flow", "sync", "notice", "monitor") if k in spec}
    if (spec.get("functions") or {}).get("python"):
        from xgen_space.functions import load_entries

        studio.entries = load_entries(spec["functions"]["python"])
    from xgen_space.reason.port import open_reasoners
    from xgen_space.space import open_space

    studio.space = open_space(spec.get("space"), base)
    studio.reasoners = open_reasoners(spec.get("reasoners"))
    for name in spec.get("resolve") or []:  # written into the source only when the studio file asks for it
        studio.resolve_identity(str(name))
    if spec.get("project"):
        studio.project(into=list(spec["project"]))
    return studio
