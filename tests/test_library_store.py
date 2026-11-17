"""Where approved changes are written (serve --library-write) follows the library on screen."""
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "examples"
EXTRA = "\n".join(["module: house-rules", "version: 0.1.0", "kind: customer", "label: 우리 규칙", "objects: {}", ""])


@pytest.fixture()
def served(tmp_path, monkeypatch):
    """A deployment that writes approved changes, offering two libraries kept in folders of their own."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import ontlas.web as web

    shutil.copytree(ROOT / "library", tmp_path / "library")
    shutil.copytree(ROOT / "commerce", tmp_path / "commerce")  # the first library's data sits beside it
    shutil.copytree(ROOT / "library" / "core", tmp_path / "second" / "library" / "core")
    (tmp_path / "second" / "studio.yaml").write_text("\n".join(
        ["library: library", "name: second", "label: 둘째", "namespace: https://example.org/second#", "modules: [core]", ""]),
        encoding="utf-8")
    got = {}
    monkeypatch.setattr(web, "serve", lambda build, **kw: got.setdefault("session", build()))
    web.serve_config(tmp_path / "library" / "studio.yaml", library_write=True, libraries=[tmp_path / "second" / "studio.yaml"])
    return got["session"], tmp_path


def written(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def approve(session) -> None:
    change = session.propose_module(EXTRA, False)["change"]
    assert session.decide_change(change["id"], True)["change"]["status"] == "approved"


def test_a_change_approved_in_the_second_library_is_written_to_its_own_folder(served):
    s, root = served
    before = {k: written(root / k) for k in ("library", "second")}
    s.library_use("l2")
    approve(s)
    assert written(root / "second") - before["second"] == {"library/house-rules/0.1.0.yaml"}
    assert written(root / "library") == before["library"]  # nothing of it reached the first library's folder
    s.library_use("l1")
    approve(s)
    assert "house-rules/0.1.0.yaml" in written(root / "library") - before["library"]


def test_what_is_switched_on_in_one_library_is_not_kept_as_the_other_s(served):
    s, root = served
    s.library_use("l2")
    approve(s)
    s.attach("house-rules")
    assert s.studio.changes.store.applied() == ["core", "house-rules"]
    s.library_use("l1")
    assert "house-rules" not in s.studio.changes.store.applied()


def test_a_library_made_on_the_page_is_written_to_no_folder(served):
    s, root = served
    before = {k: written(root / k) for k in ("library", "second")}
    s.library_new("새 도메인", "empty")
    assert s.studio.changes.store is None
    approve(s)
    assert "house-rules" in s.studio.library.names()  # kept with the session
    assert {k: written(root / k) for k in ("library", "second")} == before
    s.library_use("l1")
    assert s.studio.changes.store is not None and "house-rules" not in s.studio.library.names()
