"""xspace: validate, translate, export and import ontologies; run, decide, test and serve a studio."""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

from xgen_space.model import Ontology


def _out(data: Any) -> None:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2, default=str)
    sys.stdout.buffer.write((text.rstrip("\n") + "\n").encode("utf-8"))


def _params(items: list[str]) -> dict:
    out = {}
    for x in items:
        k, v = x.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def _query(arg: str) -> Any:
    p = Path(arg)
    if p.suffix == ".json" and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if arg.strip().startswith("{"):
        return json.loads(arg)
    return arg


def _text(arg: str) -> str:
    p = Path(arg)
    return p.read_text(encoding="utf-8") if p.exists() else arg


def _ingested(files: list[str], adapters: list[str]):
    """Files of any format as one definitions object, or None without files."""
    from xgen_space.ingest import IngestError, ingest, load_adapters

    out = None
    try:
        load_adapters(adapters)
        for f in files:
            got = ingest(Path(f).read_bytes(), Path(f).name)
            out = got if out is None else out.merge(got)
    except IngestError as e:
        raise SystemExit(str(e)) from None
    return out


def _policy_text(path: str) -> str:
    """Policy text from any document the adapters read."""
    from xgen_space.ingest import ingest

    defs = ingest(Path(path).read_bytes(), Path(path).name)
    return "\n\n".join(d.get("text", "") for d in defs.documents) or Path(path).read_text(encoding="utf-8")


def _ingest(a) -> int:
    """Write the canonical JSON of the files given and print what it holds."""
    defs = _ingested([x for f in a.files for x in (sorted(glob.glob(f)) or [f])], a.adapter)
    text = json.dumps(defs.to_dict(), ensure_ascii=False, indent=1)
    if a.output:
        Path(a.output).write_text(text + "\n", encoding="utf-8")
        _out({**defs.counts(), "written": a.output})
    else:
        _out(text)
        print(json.dumps(defs.counts()), file=sys.stderr)
    return 0


def _draft(a) -> int:
    """Draft from files (loaded into data.sqlite), a SQLite file or PostgreSQL; write a studio folder or print."""
    import yaml

    from xgen_space.draft import DraftRules, draft, load_sqlite, read_file

    rules = DraftRules.from_dict(json.loads(_text(a.rules)) if a.rules else None)
    a.files = [x for f in a.files for x in (sorted(glob.glob(f)) or [f])]  # PowerShell leaves wildcards as they are
    out = Path(a.out) if a.out else None
    if out is not None and (out / "studio.yaml").exists():
        raise SystemExit(f"{out / 'studio.yaml'} already exists; give another --out")
    loaded, origin = None, {}
    defs = _ingested(a.definitions, a.adapter)
    if defs is not None and not defs.tables and not (a.files or a.sqlite or a.dsn):
        raise SystemExit("the definitions hold no tables; give a table definition or data files")
    if defs is not None and not (a.files or a.sqlite or a.dsn):  # the schema alone
        import fnmatch
        import sqlite3

        from xgen_space.definitions import schema_backend

        pats = [x.strip() for x in a.tables.split(",") if x.strip()]
        names = [t for t in defs.tables if not pats or any(fnmatch.fnmatch(t.lower(), x.lower()) for x in pats)]
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
        path = str(out / "data.sqlite") if out is not None else ":memory:"
        backend = schema_backend(defs, names, conn=sqlite3.connect(path, check_same_thread=False))
        source = {"kind": "sqlite", "path": "data.sqlite", "source": True}
        origin = {"kind": "definitions", "detail": f"{', '.join(Path(f).name for f in a.definitions)} "
                                                   f"({len(names)} tables, no rows)"}
    elif a.files:
        import sqlite3

        from xgen_space.backends.sql import SqliteBackend

        tables = [t for f in a.files for t in read_file(Path(f).read_bytes(), Path(f).name)]
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
        path = str(out / "data.sqlite") if out is not None else ":memory:"
        backend = SqliteBackend(conn=sqlite3.connect(path, check_same_thread=False))
        loaded = load_sqlite(tables, backend, row_keys=rules.row_keys)
        source = {"kind": "sqlite", "path": "data.sqlite", "source": True}
        origin = {"kind": "files", "detail": ", ".join(Path(f).name for f in a.files)}
    elif a.sqlite:
        import sqlite3

        from xgen_space.backends.sql import SqliteBackend

        db = Path(a.sqlite).resolve()
        backend = SqliteBackend(conn=sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True, check_same_thread=False))
        source = {"kind": "sqlite", "path": str(db), "source": True}
        origin = {"kind": "database", "detail": f"SQLite {db.name}"}
    elif a.dsn:
        from urllib.parse import urlparse

        from xgen_space.config import open_backend

        u = urlparse(a.dsn)
        kind = {"mysql": "mysql", "oracle": "oracle"}.get(u.scheme, "postgres")
        backend = open_backend({"kind": kind, "dsn": a.dsn}, Path("."))
        source = {"kind": kind, "dsn": "${XSPACE_DSN}", "source": True}  # the password stays out of the file
        word = {"mysql": "MySQL", "oracle": "Oracle"}.get(kind, "PostgreSQL")
        origin = {"kind": "database", "detail": f"{word} {u.hostname or 'localhost'}{u.path}"}
    else:
        raise SystemExit("give files, --sqlite, --dsn or --definitions")
    d = draft(backend, name=a.name, label=a.label, loaded=loaded, origin=origin, lang=a.lang, rules=rules,
              definitions=defs).revise(drop=a.drop)
    modules = d.modules()
    summary = {"objects": [o.name for o in d.objects], "links": [f"{lk.source} -{lk.name}-> {lk.target}"
                                                                  for lk in d.links],
               "skipped": d.skipped, "queries": len(d.queries())}
    if out is None:
        _out("\n---\n".join(yaml.safe_dump(m.to_dict(), allow_unicode=True, sort_keys=False) for m in modules))
        return 0
    from xgen_space.library import Library

    lib = Library(out / "library")
    written = [str(lib.save(m)) for m in modules]
    studio = {"library": "library", "name": a.name, "modules": [m.name for m in modules],
              "backends": {"source": source, "graph": {"kind": "rdflib"}}, "project": ["graph"]}
    (out / "studio.yaml").write_text(yaml.safe_dump(studio, allow_unicode=True, sort_keys=False), encoding="utf-8")
    written.append(str(out / "studio.yaml"))
    _out({**summary, "written": written, "next": f"xspace serve {out / 'studio.yaml'}" +
          ("  (set XSPACE_DSN first)" if a.dsn else "")})
    return 0


def _embedder(a) -> dict | None:
    if not a.embedder:
        return None
    spec = {"kind": a.embedder}
    if a.embedder_url:
        spec["url"] = a.embedder_url
    if a.embedder_model:
        spec["model"] = a.embedder_model
    return spec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="xspace", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="check an ontology definition")
    s.add_argument("ontology")

    s = sub.add_parser("translate", help="compile a query for a backend language")
    s.add_argument("ontology")
    s.add_argument("query", help="registered query name, IR JSON, or a .json file")
    s.add_argument("--to", required=True, help="sql[:dialect] | cypher | gql | sparql | sqlpgq")
    s.add_argument("--param", action="append", default=[])
    s.add_argument("--from", dest="source", choices=["ir", "sparql", "cypher"], default="ir")

    s = sub.add_parser("export", help="write the ontology in another format")
    s.add_argument("ontology")
    s.add_argument("--format", required=True, choices=["owl", "shacl", "r2rml", "pgq", "json", "yaml", "jdm",
                                                       "report"])
    s.add_argument("--decision", help="decision table for --format jdm")
    s.add_argument("-o", "--output")

    s = sub.add_parser("import-owl", help="start a definition from an OWL/RDFS vocabulary")
    s.add_argument("file")
    s.add_argument("--namespace", default="")
    s.add_argument("--format", default="turtle")
    s.add_argument("-o", "--output")

    for name, help_ in (("run", "run a query"), ("sparql", "run a SPARQL SELECT on any backend"),
                        ("cypher", "run a Cypher read query on any backend")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("config")
        s.add_argument("query")
        s.add_argument("--backend")
        s.add_argument("--param", action="append", default=[])
        s.add_argument("--role")
        s.add_argument("--principal", action="append", default=[])

    s = sub.add_parser("decide", help="evaluate a decision table for one object")
    s.add_argument("config")
    s.add_argument("decision")
    s.add_argument("key")
    s.add_argument("--param", action="append", default=[])

    for name, help_ in (("questions", "score the validation questions"),
                        ("rules", "derive links and list rule findings"),
                        ("shacl", "validate the projection with generated SHACL")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("config")

    s = sub.add_parser("conformance", help="run registered queries on several backends and compare")
    s.add_argument("config")
    s.add_argument("--backends", help="comma-separated; default all")

    s = sub.add_parser("gates", help="measure the studio against its flow's pass conditions")
    s.add_argument("config")
    s = sub.add_parser("agreement", help="decide past cases again and compare with what was decided then")
    s.add_argument("config")
    s = sub.add_parser("identity", help="join the records several systems keep for one thing")
    s.add_argument("config")
    s.add_argument("name")
    s.add_argument("--write", action="store_true", help="write the crosswalk into the source")
    s = sub.add_parser("review", help="review a new module version against the studio before it is approved")
    s.add_argument("config")
    s.add_argument("module", help="the module file (.yaml or .json)")
    s.add_argument("--attach", action="store_true", help="review it as plugged in, for a module not attached")
    s = sub.add_parser("nl-eval", help="ask a language model each question of a file and score its answers")
    s.add_argument("config")
    s.add_argument("questions", help="YAML list of {id, text, gold}")
    s.add_argument("--llm-url", required=True)
    s.add_argument("--llm-model", required=True)
    s.add_argument("--llm-key-env", default="")
    s.add_argument("--llm-extra", default="", help="JSON merged into each chat request")
    s.add_argument("--repairs", type=int, default=2)
    s = sub.add_parser("policy-draft", help="draft a decision table module from policy text with a language model")
    s.add_argument("config")
    s.add_argument("policy", help="the policy text (.md or .txt)")
    s.add_argument("--target", default="", help="the object type the decision is about")
    s.add_argument("--name", default="", help="the decision's name")
    s.add_argument("--out", default="", help="write the module here (.yaml); otherwise print it")
    s.add_argument("--llm-url", required=True)
    s.add_argument("--llm-model", required=True)
    s.add_argument("--llm-key-env", default="")
    s.add_argument("--llm-extra", default="", help="JSON merged into each chat request")
    s.add_argument("--repairs", type=int, default=2)
    s = sub.add_parser("sync", help="bring the graphs up to date with the source, once or every N seconds")
    s.add_argument("config")
    s.add_argument("--every", type=float, default=0)
    s.add_argument("--times", type=int, default=0, help="stop after this many rounds (0: keep going)")
    s = sub.add_parser("users", help="the people of a team studio (xspace serve --users)")
    us = s.add_subparsers(dest="ucmd", required=True)
    x = us.add_parser("add")
    x.add_argument("file")
    x.add_argument("id")
    x.add_argument("--name", default="")
    x.add_argument("--roles", default="viewer", help="viewer, editor, approver, admin (comma-separated)")
    x.add_argument("--password-env", default="XSPACE_PASSWORD",
                   help="environment variable holding the password; asked for when it is not set")
    x = us.add_parser("list")
    x.add_argument("file")

    s = sub.add_parser("catalog", help="the asset graph: what an agent sees, what a change touches")
    s.add_argument("config")
    s.add_argument("--impact")
    s.add_argument("--agent", action="append", default=[], help="name=role1,role2")
    s.add_argument("--sees")

    s = sub.add_parser("library", help="the ontology library: list, show, create, import, diff, delete")
    lib = s.add_subparsers(dest="lib_cmd", required=True)
    x = lib.add_parser("list")
    x.add_argument("root")
    x = lib.add_parser("show")
    x.add_argument("root")
    x.add_argument("name")
    x.add_argument("--version", default="")
    x = lib.add_parser("create")
    x.add_argument("root")
    x.add_argument("name")
    x.add_argument("--kind", default="domain")
    x.add_argument("--label", default="")
    x.add_argument("--description", default="")
    x.add_argument("--namespace", default="")
    x.add_argument("--requires", action="append", default=[])
    x = lib.add_parser("import-owl")
    x.add_argument("root")
    x.add_argument("file")
    x.add_argument("name")
    x.add_argument("--kind", default="domain")
    x.add_argument("--label", default="")
    x.add_argument("--requires", action="append", default=[])
    x = lib.add_parser("diff")
    x.add_argument("root")
    x.add_argument("name")
    x.add_argument("a")
    x.add_argument("b")
    x = lib.add_parser("delete")
    x.add_argument("root")
    x.add_argument("name")
    x.add_argument("--version", default="")
    x = lib.add_parser("compose")
    x.add_argument("root")
    x.add_argument("modules", nargs="+")
    x.add_argument("--namespace", default="")
    x.add_argument("-o", "--output")

    s = sub.add_parser("modules", help="the modules plugged into a studio, and what unplugging one would do")
    s.add_argument("config")
    s.add_argument("--impact", help="module to check before detaching")
    s.add_argument("--cascade", action="store_true")

    s = sub.add_parser("bindings", help="check the definition against the actual database")
    s.add_argument("config")
    s.add_argument("--backend")
    s.add_argument("--no-data", action="store_true")

    s = sub.add_parser("preview", help="write a studio page built from live results")
    s.add_argument("config")
    s.add_argument("-o", "--output", default="studio.html")
    s.add_argument("--query", default="")
    s.add_argument("--decision", default="")
    s.add_argument("--key", default="")
    s.add_argument("--target", default="cypher")

    s = sub.add_parser("mcp", help="serve the studio to agents over MCP")
    s.add_argument("config")
    s.add_argument("--role")
    s.add_argument("--principal", action="append", default=[])
    s.add_argument("--read-only", action="store_true")
    s.add_argument("--transport", default="stdio")

    s = sub.add_parser("draft", help="draft modules from files or a database: objects, keys, types, relations")
    s.add_argument("files", nargs="*", help=".csv, .tsv or .xlsx files, one table each (a workbook, one per sheet)")
    s.add_argument("--sqlite", default="", help="a SQLite database file, opened read-only")
    s.add_argument("--dsn", default="", help="a database: postgresql://..., mysql://... or oracle://user:pw@host/service")
    s.add_argument("--name", default="my-data")
    s.add_argument("--label", default="")
    s.add_argument("--lang", default="en", choices=["en", "ko"], help="language of the generated query labels")
    s.add_argument("--drop", action="append", default=[], help="leave out object:Name, link:name, property:X.p, query:q")
    s.add_argument("--rules", default="", help='draft rules as JSON or a .json file, e.g. {"enum_max": 10, "infer_links": false}')
    s.add_argument("--definitions", action="append", default=[],
                   help="definitions in any format xspace ingest reads: names and code values; alone, the schema")
    s.add_argument("--adapter", action="append", default=[], help="a python file that registers another format")
    s.add_argument("--tables", default="", help="with --definitions alone: the tables to draft, e.g. 'TB_*,ORDERS'")
    s.add_argument("-o", "--out", default="", help="write library/, studio.yaml (and data.sqlite for files) here")

    s = sub.add_parser("ingest", help="read definitions and documents of any format into one JSON")
    s.add_argument("files", nargs="+", help="SQL, DBML, PowerDesigner, MySQL Workbench, Office, HWPX, HTML, text, PDF, "
                                            "CSV, Excel or JSON files")
    s.add_argument("-o", "--output", default="", help="write the JSON here and print the counts")
    s.add_argument("--adapter", action="append", default=[], help="a python file that registers another format")

    s = sub.add_parser("search", help="search the space's documents by meaning")
    s.add_argument("config")
    s.add_argument("text")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--store", default="", help="a vector store by name; default the first that is up to date")
    s = sub.add_parser("documents", help="what the space holds: documents, chunks, stores, embedder")
    s.add_argument("config")
    s = sub.add_parser("vectors", help="vector stores against exact search on the space's own documents")
    s.add_argument("config")
    s.add_argument("-k", type=int, default=5)
    s = sub.add_parser("reasoners", help="the reasoners of a studio, and whether engines of one logic agree")
    s.add_argument("config")
    s = sub.add_parser("openapi", help="the REST API as OpenAPI, for a platform that imports it")
    s.add_argument("--server", default="", help="the address it will be reached at")
    s = sub.add_parser("serve", help="serve the studio page; every visitor gets a studio of their own")
    s.add_argument("--embedder", default="", help="hash, fastembed, or openai with --embedder-url and --embedder-model")
    s.add_argument("--embedder-url", default="")
    s.add_argument("--embedder-model", default="")
    s.add_argument("--api-token-env", default="", help="turns /v1 on: the environment variable that holds its bearer token")
    s.add_argument("--api-role", default="", help="the role /v1 runs as; with none it reads everything")
    s.add_argument("--api-principal", action="append", default=[], help="key=value, for a role's row scope")
    s.add_argument("--api-write", action="store_true", help="let /v1 request actions; a person still approves them")
    s.add_argument("config")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=7710)
    s.add_argument("--sessions", type=int, default=24, help="studios kept at once; the least recent goes first")
    s.add_argument("--idle", type=int, default=3600, help="seconds before an unused studio is dropped")
    s.add_argument("--llm-url", default="", help="OpenAI-compatible base URL for natural-language questions")
    s.add_argument("--llm-model", default="")
    s.add_argument("--llm-key-env", default="", help="environment variable that holds the API key")
    s.add_argument("--llm-extra", default="", help="JSON merged into each chat request")
    s.add_argument("--samples", default="", help="folder of example files a visitor can load with one click")
    s.add_argument("--policies", default="", help="folder of example policy texts for drafting rules from policy")
    s.add_argument("--allow-connect", action="store_true",
                   help="let visitors connect a database by address (for a studio inside your own network)")
    s.add_argument("--file-kb", type=int, default=1024, help="largest file a visitor may upload")
    s.add_argument("--max-files", type=int, default=30, help="files a visitor's repositories may hold")
    s.add_argument("--total-mb", type=int, default=0, help="bytes they may hold in all (default: four of the largest file)")
    s.add_argument("--repositories", default="", help="folder that keeps repositories across restarts, for all visitors; "
                                                      "without it they end with the visitor")
    s.add_argument("--video", default="", help="a demo .mp4 shown beside the manual (chapters from x.chapters.json)")
    s.add_argument("--rows", type=int, default=10_000, help="rows read from each uploaded table")
    s.add_argument("--users", default="", help="a users file: one studio the team shares, behind a sign-in")
    s.add_argument("--library-write", action="store_true", help="save approved module versions to the library folder")
    s.add_argument("--sync", type=float, default=0, help="re-read the source every N seconds and update the graphs")
    s.add_argument("--quiet", action="store_true")

    a = ap.parse_args(argv)

    if a.cmd == "validate":
        issues = Ontology.load(a.ontology).validate()
        _out({"ok": not issues, "issues": issues})
        return 0 if not issues else 1

    if a.cmd == "translate":
        from xgen_space.compile.base import compiler_for

        onto = Ontology.load(a.ontology)
        if a.source == "sparql":
            from xgen_space.parse.sparql import parse_sparql

            q = parse_sparql(_text(a.query), onto)
        elif a.source == "cypher":
            from xgen_space.parse.cypher import parse_cypher

            q = parse_cypher(_text(a.query), onto)
        else:
            from xgen_space.studio import Studio

            q = Studio(onto).query(_query(a.query))
        c = compiler_for(onto, a.to).compile(q)
        params = _params(a.param)
        _out({"language": c.language, "dialect": c.dialect, "text": c.text, "params": c.params,
              "preview": c.preview(params) if set(c.params) <= set(params) | set(c.literals) else None})
        return 0

    if a.cmd == "export":
        onto = Ontology.load(a.ontology)
        if a.format in ("owl", "report"):
            from xgen_space.exchange.owl import to_owl

            ttl, rep = to_owl(onto)
            text = ttl if a.format == "owl" else json.dumps(rep.to_dict(), ensure_ascii=False, indent=2)
        elif a.format == "shacl":
            from xgen_space.reason.shacl import to_shacl

            text = to_shacl(onto)
        elif a.format == "r2rml":
            from xgen_space.exchange.r2rml import to_r2rml

            text = to_r2rml(onto)
        elif a.format == "pgq":
            from xgen_space.compile.pgq import graph_ddl

            text = graph_ddl(onto)
        elif a.format == "jdm":
            from xgen_space.decide.zen import to_jdm

            name = a.decision or next(iter(onto.decisions))
            text = json.dumps(to_jdm(onto.decisions[name]), ensure_ascii=False, indent=2)
        elif a.format == "json":
            text = json.dumps(onto.to_dict(), ensure_ascii=False, indent=2)
        else:
            import yaml

            text = yaml.safe_dump(onto.to_dict(), allow_unicode=True, sort_keys=False)
        if a.output:
            Path(a.output).write_text(text, encoding="utf-8")
            _out({"written": a.output})
        else:
            _out(text)
        return 0

    if a.cmd == "import-owl":
        from xgen_space.exchange.importer import from_owl

        onto, rep = from_owl(Path(a.file).read_text(encoding="utf-8"), namespace=a.namespace, fmt=a.format)
        if a.output:
            onto.dump(a.output)
        _out({"written": a.output, "report": rep.to_dict(), **({} if a.output else {"ontology": onto.to_dict()})})
        return 0

    if a.cmd == "library":
        from xgen_space.library import Library

        lib = Library(a.root)
        if a.lib_cmd == "list":
            _out(lib.list())
        elif a.lib_cmd == "show":
            m = lib.get(a.name, a.version)
            _out({"module": m.to_dict(), "versions": lib.versions(a.name), "elements": m.elements()})
        elif a.lib_cmd == "create":
            m = lib.create(a.name, kind=a.kind, label=a.label, description=a.description, namespace=a.namespace,
                           requires=a.requires)
            _out({"created": m.key, "path": str(lib.root / m.name)})
        elif a.lib_cmd == "import-owl":
            m, rep = lib.import_owl(Path(a.file).read_text(encoding="utf-8"), a.name, kind=a.kind, label=a.label,
                                    requires=a.requires)
            _out({"created": m.key, "report": rep.to_dict()})
        elif a.lib_cmd == "diff":
            _out(lib.diff(a.name, a.a, a.b))
        elif a.lib_cmd == "delete":
            lib.delete(a.name, a.version)
            _out({"deleted": f"{a.name}{'@' + a.version if a.version else ''}"})
        else:
            from xgen_space.modules import compose

            comp = compose(lib.resolve(a.modules), namespace=a.namespace)
            if a.output:
                comp.ontology.dump(a.output)
            _out({"modules": comp.summary(), "issues": comp.issues, "written": a.output})
            return 0 if not comp.issues else 1
        return 0

    if a.cmd == "mcp":
        from xgen_space.mcp_server import main as mcp_main

        args = [a.config, "--transport", a.transport] + (["--role", a.role] if a.role else [])
        args += sum((["--principal", p] for p in a.principal), []) + (["--read-only"] if a.read_only else [])
        mcp_main(args)
        return 0

    if a.cmd == "draft":
        return _draft(a)

    if a.cmd == "ingest":
        return _ingest(a)

    if a.cmd == "openapi":
        from xgen_space import __version__
        from xgen_space.rest import openapi

        _out(openapi(__version__, a.server))
        return 0

    if a.cmd == "serve":
        from xgen_space.web import serve_config

        llm = None
        if a.llm_url:
            from xgen_space.nl import openai_chat

            llm = openai_chat(a.llm_url, a.llm_model, key=os.environ.get(a.llm_key_env, "") if a.llm_key_env else "",
                              extra=json.loads(a.llm_extra) if a.llm_extra else None)
        from xgen_space.web import DataOptions

        data = DataOptions(file_bytes=a.file_kb << 10, files=a.max_files,
                           total_bytes=a.total_mb << 20 if a.total_mb else max(4 << 20, a.file_kb << 12), rows=a.rows,
                           samples=Path(a.samples) if a.samples else None, allow_connect=a.allow_connect,
                           policies=Path(a.policies) if a.policies else None,
                           repositories=Path(a.repositories) if a.repositories else None,
                           embedder=_embedder(a), rest=bool(a.api_token_env))
        api = None
        if a.api_token_env:
            token = os.environ.get(a.api_token_env, "")
            if not token:
                raise SystemExit(f"--api-token-env: {a.api_token_env} is empty")
            api = {"token": token, "role": a.api_role, "principal": dict(x.split("=", 1) for x in a.api_principal), "write": a.api_write}
        serve_config(a.config, llm=llm, data=data, host=a.host, port=a.port, limit=a.sessions, idle=a.idle,
                     quiet=a.quiet, video=Path(a.video) if a.video else None, users=Path(a.users) if a.users else None,
                     sync=a.sync, library_write=a.library_write, api=api)
        return 0
    if a.cmd == "users":
        from xgen_space.web.team import Users

        users = Users.load(a.file)
        if a.ucmd == "list":
            _out([{"id": u.id, "name": u.name, "roles": u.roles} for u in users.users.values()])
            return 0
        password = os.environ.get(a.password_env) or ""
        if not password:
            import getpass

            password = getpass.getpass(f"password for {a.id}: ")
        u = users.add(a.id, password, name=a.name, roles=[r.strip() for r in a.roles.split(",") if r.strip()])
        _out({"added": u.id, "name": u.name, "roles": u.roles, "file": a.file})
        return 0

    from xgen_space.config import load_studio

    studio = load_studio(a.config)
    if a.cmd in ("run", "sparql", "cypher"):
        kw = {"backend": a.backend, "role": a.role, "principal": _params(a.principal)}
        if a.cmd == "run":
            res = studio.run(_query(a.query), _params(a.param), **kw)
        elif a.cmd == "sparql":
            res = studio.run_sparql(_text(a.query), _params(a.param), **kw)
        else:
            res = studio.run_cypher(_text(a.query), _params(a.param), **kw)
        from xgen_space.tools import _jsonable

        _out({"backend": res.backend, "text": res.compiled.text,
              "rows": _jsonable(res.rows, res.columns, res.compiled.column_types)})
    elif a.cmd == "decide":
        _out(studio.decide(a.decision, a.key, _params(a.param)).to_dict())
    elif a.cmd == "questions":
        rep = studio.questions()
        _out(rep.to_dict())
        return 0 if rep.accuracy == 1.0 else 1
    elif a.cmd == "search":
        from xgen_space.tools import StudioTools

        _out(StudioTools(studio).search_documents(a.text, a.k, a.store))
    elif a.cmd == "documents":
        from xgen_space.tools import StudioTools

        _out(StudioTools(studio).describe_space())
    elif a.cmd == "vectors":
        from xgen_space.vectors import Point, conformance

        sp = studio.space
        sp.index()
        chunks = list(sp.chunks.values())
        vectors = sp.embedder.embed([c.text for c in chunks])
        points = [Point(c.id, v, {"document": c.document}) for c, v in zip(chunks, vectors)]
        rep = conformance(sp.stores, points, [(c.text[:80], v) for c, v in list(zip(chunks, vectors))[:: max(len(chunks) // 8, 1)]], k=a.k)
        _out(rep.to_dict())
        return 0 if all(s.get("agree") for s in rep.stores.values()) else 1
    elif a.cmd == "reasoners":
        from xgen_space.reason.port import agreement

        rows = {n: r.run(studio.onto, studio.projection).to_dict(5) for n, r in studio.reasoners.items()} if studio.projection else {}
        rep = {"reasoners": rows, "agreement": agreement(studio.reasoners, studio.onto, studio.projection) if studio.projection else {}}
        _out(rep)
        return 0 if all(g["same"] for g in rep["agreement"].values()) else 1
    elif a.cmd == "conformance":
        rep = studio.conformance(a.backends.split(",") if a.backends else None)
        _out(rep.to_dict())
        return 0 if rep.passed else 1
    elif a.cmd == "rules":
        from xgen_space.projection import project
        from xgen_space.reason.rules import run_rules

        _out(run_rules(studio.onto, studio.projection or project(studio.onto, studio.backend())).to_dict())
    elif a.cmd == "shacl":
        from xgen_space.projection import project
        from xgen_space.reason.shacl import validate

        rep = validate(studio.onto, studio.projection or project(studio.onto, studio.backend()))
        _out(rep.to_dict())
        return 0 if rep.conforms else 1
    elif a.cmd == "gates":
        rep = studio.gates()
        _out(rep)
        return 0 if rep["passed"] else 1
    elif a.cmd == "agreement":
        _out(studio.agreement())
    elif a.cmd == "identity":
        _out(studio.resolve_identity(a.name, write=a.write).to_dict())
    elif a.cmd == "review":
        from xgen_space.modules import Module
        from xgen_space.review import review

        rep = review(studio, Module.load(a.module), attach=a.attach)
        _out(rep)
        return 0 if rep["passed"] else 1
    elif a.cmd == "nl-eval":
        import yaml

        from xgen_space.nl import evaluate, openai_chat

        llm = openai_chat(a.llm_url, a.llm_model, key=os.environ.get(a.llm_key_env, "") if a.llm_key_env else "",
                          extra=json.loads(a.llm_extra) if a.llm_extra else None)
        rep = evaluate(studio, yaml.safe_load(Path(a.questions).read_text(encoding="utf-8")), llm,
                       max_repairs=a.repairs)
        _out(rep)
    elif a.cmd == "policy-draft":
        import yaml

        from xgen_space.nl import openai_chat
        from xgen_space.policy import CALL_SECONDS, CALL_TOKENS, PolicyDrafter

        if studio.composition is None:
            print("policy-draft needs a studio made of modules", file=sys.stderr)
            return 2
        llm = openai_chat(a.llm_url, a.llm_model, key=os.environ.get(a.llm_key_env, "") if a.llm_key_env else "",
                          extra=json.loads(a.llm_extra) if a.llm_extra else None).roomier(CALL_TOKENS, CALL_SECONDS)
        d = PolicyDrafter(list(studio.composition.modules), llm, max_repairs=a.repairs,
                          compose_kw=studio._compose_kw).draft(_policy_text(a.policy), target=a.target, name=a.name)
        for i in d.issues:
            print(f"issue: {i}", file=sys.stderr)
        if d.module is None:
            return 1
        text = yaml.safe_dump(d.module.to_dict(), allow_unicode=True, sort_keys=False, default_flow_style=None,
                              width=110)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
            print(a.out)
        else:
            print(text)
        return 0 if d.ok else 1
    elif a.cmd == "sync":
        import time

        n = 0
        while True:
            _out(studio.sync())
            n += 1
            if not a.every or (a.times and n >= a.times):
                break
            time.sleep(a.every)
    elif a.cmd == "modules":
        if a.impact:
            imp = studio.detach_impact(a.impact, cascade=a.cascade)
            _out(imp.to_dict())
            return 0 if imp.ok else 1
        _out(studio.composition.summary() if studio.composition else [])
    elif a.cmd == "bindings":
        rep = studio.check_bindings(backend=a.backend, data=not a.no_data)
        _out(rep.to_dict())
        return 0 if rep.ok else 1
    elif a.cmd == "preview":
        from xgen_space.preview import render

        html = render(studio, query=a.query, decision=a.decision, key=a.key, target=a.target)
        Path(a.output).write_text(html, encoding="utf-8")
        _out({"written": a.output})
    elif a.cmd == "catalog":
        from xgen_space.catalog import from_ontology

        cat = from_ontology(studio.onto, database=studio.source)
        for spec in a.agent:
            n, roles = spec.split("=", 1)
            cat.add_agent(n, roles=roles.split(","))
        if a.impact:
            _out([x.id for x in cat.impact(a.impact)])
        elif a.sees:
            _out([x.id for x in cat.sees(a.sees)])
        else:
            _out(cat.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
