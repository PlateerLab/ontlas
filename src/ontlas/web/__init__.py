"""The studio as a web page: library, ontology, queries, decisions and approvals, checks."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from ontlas.web.api import DataOptions, StudioSession
from ontlas.web.server import serve

__all__ = ["DataOptions", "StudioSession", "serve", "serve_config"]


def config_origin(config: str | Path) -> dict:
    """Where a studio file's data comes from, as the flow page tells it: backends, seed files, a notice."""
    import yaml

    p = Path(config)
    spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    backends = spec.get("backends") or {}
    seeds = [Path(s).name for b in backends.values() for s in ([b["seed"]] if isinstance(b.get("seed"), str)
                                                                else b.get("seed") or [])]
    return {"kind": "config", "config": p.name, "notice": str(spec.get("notice", "")),
            "backends": {n: b.get("kind", "") for n, b in backends.items()}, "seeds": seeds}


def library_entry(lid: str, config: str | Path, studio) -> dict:
    """A studio file as a library to choose: its name (the domain modules it applies, else the studio's own name), how
    many modules it applies and what it reads."""
    comp = studio.composition
    domains = [m.label or m.name for m in comp.modules if m.kind == "domain"] if comp else []
    origin = config_origin(config)
    return {"id": lid, "label": " · ".join(domains) or studio.onto.label or studio.onto.name, "path": str(config),
            "origin": origin, "modules": len(comp.modules) if comp else 0,
            "source": origin["backends"].get(studio.source, "") if studio.source else ""}


def serve_config(config: str | Path, *, llm: Callable[[str, str], str] | None = None,
                 data: DataOptions | None = None, library_write: bool = False, journal: Path | None = None,
                 libraries: list[str | Path] | None = None, **kw) -> None:
    """Serve a studio file; every visitor gets a studio of their own, built from the same file (or, with
    `users`, one studio a team shares). With `library_write`, approved changes are saved to the library folder;
    with `journal`, requests, approvals and the audit trail are kept in that file across restarts."""
    if journal is not None and not kw.get("users"):
        raise ValueError("a journal keeps the records of one studio a team shares; serve it with users")
    from ontlas.config import load_studio
    from ontlas.library import Library
    from ontlas.repository import Repositories

    first = load_studio(config)  # fail at start, not on the first visitor
    origin = config_origin(config)
    # the other studio files a visitor may switch to, each read once here so a broken one fails at start
    offered = [library_entry("l1", config, first)] + [library_entry(f"l{i + 2}", p, load_studio(p)) for i, p in enumerate(libraries or [])]
    kept = Repositories(data.repositories) if data is not None and data.repositories else None
    store = None
    if library_write:
        if first.library is None:
            raise ValueError("--library-write needs a studio file built from a library (modules: ...)")
        store = Library(first.library.root)

    def build() -> StudioSession:
        studio = load_studio(config)
        if journal is not None:
            studio.keep_journal(journal)
        s = StudioSession(studio, llm=llm, data=data, origin=dict(origin), repositories=kept)
        s.libraries = [dict(x) for x in offered]
        if store is not None:
            s.store = store
            s._adopt(s.studio)
        return s

    serve(build, data=data, **kw)
