"""The studio as a web page: library, ontology, queries, decisions and approvals, checks."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from xgen_data_studio.web.api import DataOptions, StudioSession
from xgen_data_studio.web.server import serve

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


def serve_config(config: str | Path, *, llm: Callable[[str, str], str] | None = None,
                 data: DataOptions | None = None, library_write: bool = False, **kw) -> None:
    """Serve a studio file; every visitor gets a studio of their own, built from the same file (or, with
    `users`, one studio a team shares). With `library_write`, approved changes are saved to the library folder."""
    from xgen_data_studio.config import load_studio
    from xgen_data_studio.library import Library

    first = load_studio(config)  # fail at start, not on the first visitor
    origin = config_origin(config)
    store = None
    if library_write:
        if first.library is None:
            raise ValueError("--library-write needs a studio file built from a library (modules: ...)")
        store = Library(first.library.root)

    def build() -> StudioSession:
        s = StudioSession(load_studio(config), llm=llm, data=data, origin=dict(origin))
        if store is not None:
            s.store = store
            s._adopt(s.studio)
        return s

    serve(build, data=data, **kw)
