"""Where approved changes are written (serve --library-write) follows the library on screen, and a library made on the
page of such a server is a studio folder of its own, found again at the next start."""
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "examples"
EXTRA = "\n".join(["module: house-rules", "version: 0.1.0", "kind: customer", "label: 우리 규칙", "objects: {}", ""])


@pytest.fixture()
def serving(tmp_path, monkeypatch):
    """A deployment that writes approved changes, offering two libraries kept in folders of their own. `start()` is the
    server starting on those folders: a visitor's studio as it builds one."""
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import ontlas.web as web

    shutil.copytree(ROOT / "library", tmp_path / "library")
    shutil.copytree(ROOT / "commerce", tmp_path / "commerce")  # the first library's data sits beside it
    shutil.copytree(ROOT / "library" / "core", tmp_path / "second" / "library" / "core")
    (tmp_path / "second" / "studio.yaml").write_text("\n".join(
        ["library: library", "name: second", "label: 둘째", "namespace: https://example.org/second#", "modules: [core]", ""]),
        encoding="utf-8")

    def start(**kw):
        got = {}
        monkeypatch.setattr(web, "serve", lambda build, **_: got.setdefault("session", build()))
        web.serve_config(tmp_path / "library" / "studio.yaml", library_write=True, libraries=[tmp_path / "second" / "studio.yaml"], **kw)
        return got["session"]

    return start, tmp_path


@pytest.fixture()
def served(serving):
    start, root = serving
    return start(), root


def written(folder: Path) -> set[str]:
    return {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}


def offered(root: Path) -> dict[str, set[str]]:
    """The files of the two libraries the deployment offers, without what was made beside the first."""
    return {"library": {f for f in written(root / "library") if not f.startswith("made/")}, "second": written(root / "second")}


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


def test_a_library_made_on_the_page_is_written_to_a_studio_folder_of_its_own(served):
    from ontlas.web.api import LIBRARIES_KEPT_MAX

    s, root = served
    before = offered(root)
    out = s.library_new("새 도메인", "empty", key="New Domain")
    home = root / "library" / "made" / "new-domain"  # beside the first studio file, unless the server names a folder
    assert out["id"] == "s1" and written(home) == {"studio.yaml"} and s.studio.changes.store.root == home / "library"
    approve(s)
    assert written(home) == {"studio.yaml", "library/house-rules/0.1.0.yaml"}
    assert offered(root) == before  # nothing of it reached the folders the deployment offers
    assert s.state()["libraries"][-1] == {"id": "s1", "label": "새 도메인", "modules": 0, "source": "", "made": True}
    assert s.library_files()["made_max"] == LIBRARIES_KEPT_MAX == s.made_max  # more than a visitor's session keeps
    s.library_use("l1")
    assert s.studio.changes.store is not None and "house-rules" not in s.studio.library.names()
    assert "made" not in s.studio.library.names()  # the folder of made ones is no module of the first library


def test_what_was_made_is_found_again_at_the_next_start(serving):
    start, root = serving
    s = start()
    first = s.libraries[0]["label"]
    made = s.library_new("우리 가게", "base", modules=["commerce"], description="가게  규칙")
    approve(s)
    s.attach("house-rules")  # what is switched on is kept beside its own modules
    home = root / "library" / "made" / "library-1"  # no key was given: named by its number
    assert (home / "library" / "applied.yaml").is_file() and (home / "library" / "fashion").is_dir()  # the rest came to switch on

    again = start()  # the server stops and starts again on the same folders
    row = next(x for x in again.libraries if x.get("made"))
    assert (row["id"], row["label"], row["description"], row["base_label"], row["modules"]) == (made["id"], "우리 가게", "가게 규칙", first, 3)
    assert again.library_id == "l1" and Path(row["path"]) == home / "studio.yaml"
    again.library_use(made["id"])
    assert {m.name for m in again.studio.composition.modules} == {"core", "commerce", "house-rules"}
    assert again.studio.onto.label == "우리 가게" and again.studio.changes.store.root == home / "library"
    assert "fashion" in again.studio.library.names()
    with pytest.raises(ValueError, match="같은 이름"):
        again.library_new("우리 가게", "empty")
    assert again.library_new("다른 가게", "empty")["id"] == "s2"


def test_a_library_made_on_another_takes_its_screen_edits_only_where_it_applies_them(served):
    s, root = served
    s.manage_edit("update_object", {"name": "Customer", "label": "손님"})
    assert s.manage_propose()["ok"]  # one visitor is both sides: approved at once, as the first library's workspace module
    assert (root / "library" / "workspace").is_dir()
    s.library_new("의류 몰", "base", modules=["commerce", "fashion"], key="apparel")
    assert not (root / "library" / "made" / "apparel" / "library" / "workspace").exists()
    assert s.studio.onto.objects["Customer"].label != "손님"
    s.library_use("l1")
    s.library_new("전체 사본", "base", key="whole")  # every module the first applies, its approved screen edits among them
    assert (root / "library" / "made" / "whole" / "library" / "workspace").is_dir() and s.studio.onto.objects["Customer"].label == "손님"


def test_one_taken_away_is_moved_aside_whole_and_comes_back_as_it_was(serving):
    start, root = serving
    shelf = root / "library" / "made"
    s = start()
    one = s.library_new("하나", "empty", key="one")
    approve(s)
    with pytest.raises(ValueError, match="같은 키"):
        s.library_new("또 하나", "empty", key="one")
    s.library_drop(one["id"])
    assert s.library_id == "l1" and not (shelf / "one").exists() and [x["id"] for x in s.libraries] == ["l1", "l2"]
    gone = [p.name for p in (shelf / ".deleted").iterdir()]
    assert len(gone) == 1 and gone[0].startswith("one.") and (shelf / ".deleted" / gone[0] / "library" / "house-rules" / "0.1.0.yaml").is_file()
    assert [(d["id"], d["label"], d["by"]) for d in s.library_deleted()] == [(one["id"], "하나", "방문자")] and s.library_deleted()[0]["at"]
    two = s.library_new("둘", "empty", key="one")  # the key is free again; the number is not given twice
    assert two["id"] == "s2"
    with pytest.raises(ValueError, match="같은 키"):
        s.library_restore(one["id"])
    s.library_drop(two["id"])
    assert s.library_restore(one["id"]) == {"ok": True, "id": one["id"], "label": "하나"} and s.library_deleted()[0]["id"] == "s2"
    with pytest.raises(LookupError):
        s.library_restore(one["id"])  # it is back: there is none such taken away

    again = start()
    assert [x["id"] for x in again.libraries if x.get("made")] == [one["id"]]
    again.library_use(one["id"])
    assert "house-rules" in again.studio.library.names()


def test_the_server_says_how_many_it_keeps_and_reads_only_what_it_made(serving, capsys):
    yaml = pytest.importorskip("yaml")
    start, root = serving
    shelf = root / "library" / "made"
    for name in ("by-hand", ".new-cut-off"):  # a studio folder put there by hand; a write that was cut off
        (shelf / name).mkdir(parents=True)
        (shelf / name / "studio.yaml").write_text(yaml.safe_dump({"library": "library", "name": name, "modules": []}), encoding="utf-8")
    s = start(made_max=2)
    assert [x["id"] for x in s.libraries] == ["l1", "l2"] and "by-hand" in capsys.readouterr().err
    s.library_new("하나", "empty")
    s.library_new("둘", "empty")
    with pytest.raises(ValueError, match="2개 한도"):
        s.library_new("셋", "empty")
    s.library_drop("s2")
    s.library_new("셋", "empty")
    with pytest.raises(ValueError, match="2개 한도"):
        s.library_restore("s2")


def test_the_folder_of_made_libraries_is_the_one_the_server_names(tmp_path, monkeypatch):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    import ontlas.web as web
    from ontlas.cli import main

    shutil.copytree(ROOT / "library", tmp_path / "library")
    shutil.copytree(ROOT / "commerce", tmp_path / "commerce")
    got = {}
    monkeypatch.setattr(web, "serve", lambda build, **_: got.setdefault("session", build()))
    config = str(tmp_path / "library" / "studio.yaml")
    main(["serve", config, "--library-write", "--libraries", str(tmp_path / "kept"), "--libraries-max", "7"])
    s = got["session"]
    s.library_new("하나", "empty", key="one")
    assert (tmp_path / "kept" / "one" / "studio.yaml").is_file() and s.made_max == 7 and not (tmp_path / "library" / "made").exists()
    for flags in (["--libraries", str(tmp_path / "kept")], ["--libraries-max", "7"]):
        with pytest.raises(SystemExit, match="--library-write"):
            main(["serve", config, *flags])
