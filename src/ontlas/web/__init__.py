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
                 libraries: list[str | Path] | None = None, made: str | Path | None = None, made_max: int = 0, **kw) -> None:
    """Serve a studio file; every visitor gets a studio of their own, built from the same file (or, with
    `users`, the studios a team shares, one a library). With `library_write`, approved changes are saved to the
    library folder, and a library made on the page is kept as a studio folder under `made` (made/ beside the studio
    file unless given), up to `made_max` of them; with `journal`, requests, approvals and the audit trail are kept in
    that file across restarts."""
    if journal is not None and not kw.get("users"):
        raise ValueError("a journal keeps the records of one studio a team shares; serve it with users")
    if made is not None and not library_write:
        raise ValueError("a folder for the libraries made on the page is written with library_write")
    from ontlas.config import load_studio
    from ontlas.library import Library, Shelf
    from ontlas.repository import Repositories
    from ontlas.web.api import LIBRARIES_KEPT_MAX, made_entries

    first = load_studio(config)  # fail at start, not on the first visitor
    origin = config_origin(config)
    # the other studio files a visitor may switch to, each read once here so a broken one fails at start
    offered = [library_entry("l1", config, first)] + [library_entry(f"l{i + 2}", p, load_studio(p)) for i, p in enumerate(libraries or [])]
    kept = Repositories(data.repositories) if data is not None and data.repositories else None
    store = shelf = None
    if library_write:
        if first.library is None:
            raise ValueError("--library-write needs a studio file built from a library (modules: ...)")
        store = Library(first.library.root)
        shelf = Shelf(made if made is not None else Path(config).parent / "made")
    # where the server writes them, the libraries made on the page are the server's: one list every studio shares,
    # found again here at each start. Elsewhere each visitor's list is their own, and what they make ends with them
    listed = [*offered, *made_entries(shelf)] if shelf is not None else None

    def build() -> StudioSession:
        studio = load_studio(config)
        if journal is not None:
            studio.keep_journal(journal)
        s = StudioSession(studio, llm=llm, data=data, origin=dict(origin), repositories=kept)
        s.libraries = listed if listed is not None else [dict(x) for x in offered]
        if store is not None:
            s.store, s.shelf, s.made_max = store, shelf, made_max or LIBRARIES_KEPT_MAX
            s._adopt(s.studio)
        if journal is not None:
            s.restore_pending()  # the edits being written when it stopped
        return s

    # /v1 answers from the first library unless a caller names another; each of the others is built when first asked
    paths = [config, *(libraries or [])]
    serve(build, data=data, libraries=[{**x, "load": (lambda p=paths[i]: load_studio(p))} for i, x in enumerate(offered)], **kw)
