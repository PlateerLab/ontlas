"""The studio as a web page: library, ontology, queries, decisions and approvals, checks."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from xgen_data_studio.web.api import StudioSession
from xgen_data_studio.web.server import serve

__all__ = ["StudioSession", "serve", "serve_config"]


def serve_config(config: str | Path, *, llm: Callable[[str, str], str] | None = None, **kw) -> None:
    """Serve a studio file; every visitor gets a studio of their own, built from the same file."""
    from xgen_data_studio.config import load_studio

    load_studio(config)  # fail at start, not on the first visitor
    serve(lambda: StudioSession(load_studio(config), llm=llm), **kw)
