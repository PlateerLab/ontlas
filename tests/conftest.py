import atexit
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from xgen_space import Ontology
from xgen_space.backends.sql import SqliteBackend
from xgen_space.studio import Studio

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "commerce"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BOOKS = FIXTURES / "books"
NOW = datetime(2026, 10, 30, 12, 0)


def _two_domains() -> Path:
    """The example library with a second domain on it: what only two domains together can show stays tested, while the
    library people get holds commerce alone."""
    root = Path(tempfile.mkdtemp(prefix="xspace-tests-"))
    atexit.register(shutil.rmtree, root, ignore_errors=True)
    shutil.copytree(EXAMPLE, root / "commerce")
    shutil.copytree(EXAMPLE.parent / "library", root / "library")
    shutil.copytree(FIXTURES / "second-domain", root / "library", dirs_exist_ok=True)
    return root / "library"


LIB = _two_domains()


@pytest.fixture
def onto() -> Ontology:
    return Ontology.load(EXAMPLE / "ontology.yaml")


@pytest.fixture
def source() -> SqliteBackend:
    b = SqliteBackend()
    b.script((EXAMPLE / "seed.sql").read_text(encoding="utf-8"))
    return b


@pytest.fixture
def studio(onto, source) -> Studio:
    st = Studio(onto, now=lambda: NOW)
    st.add_backend("source", source)
    return st


@pytest.fixture
def graph_studio(studio) -> Studio:
    pytest.importorskip("rdflib")
    from xgen_space.backends.rdf import RdflibBackend

    studio.add_backend("graph", RdflibBackend())
    studio.project()
    return studio
