"""Repositories and the catalog over them: folders, what a file turned out to be, what goes into a draft."""
import gc
import json
from pathlib import Path

import pytest

from xgen_space.repository import Repositories, clean_path, is_litter

CSV = "회원번호,이름\nM1,가\nM2,나\n".encode("utf-8")
EXAMPLE = Path(__file__).parent.parent / "examples" / "library" / "studio.yaml"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    return StudioSession(load_studio(EXAMPLE), data=DataOptions())


@pytest.mark.parametrize("bad", ["../x.csv", "a/../../x.csv", "a/./b", "a\x00b", "a\nb"])
def test_a_path_cannot_leave_the_repository(bad):
    with pytest.raises(ValueError):
        clean_path(bad)


def test_a_path_is_a_name_in_an_index_and_never_reaches_the_disk(tmp_path):
    r = Repositories(tmp_path)
    assert clean_path("\\a\\\\b/ c.csv ") == "a/b/c.csv"
    r.put("r1", "C:/Windows/con.csv", b"x")  # any name is only a name here
    r.put("r1", "a:b*?.csv", b"x")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["blobs", "index.json"]
    assert len(list((tmp_path / "blobs").iterdir())) == 1  # two copies of a file cost one


def test_what_a_folder_upload_leaves_behind_is_not_brought_in():
    assert is_litter("a/.DS_Store") and is_litter("a/Thumbs.db") and is_litter("__MACOSX/a/x.csv")
    assert is_litter("a/._x.csv") and not is_litter("a/x.csv")


def test_folders_hold_what_is_in_them_and_go_with_it(tmp_path):
    r = Repositories(tmp_path)
    r.put("r1", "a/b/x.csv", b"1")
    r.put("r1", "a/y.csv", b"22")
    folders, files = r.listing("r1", "a")
    assert [(f["name"], f["files"]) for f in folders] == [("b", 1)] and [f["name"] for f in files] == ["y.csv"]
    assert r.listing("r1")[0][0]["files"] == 2 and r.listing("r1")[0][0]["bytes"] == 3
    r.move("r1", "a/b", "a/c")
    assert "a/c/x.csv" in r.files("r1") and r.listing("r1", "a/c")[1][0]["name"] == "x.csv"
    with pytest.raises(ValueError):
        r.move("r1", "a/c", "a/y.csv")
    with pytest.raises(ValueError):
        r.put("r1", "a/c", b"3")  # a file cannot take a folder's name
    with pytest.raises(ValueError):
        r.folder("r1", "a/y.csv/z")
    assert sorted(r.remove("r1", ["a"])) == ["a/c/x.csv", "a/y.csv"]
    assert r.files("r1") == {} and r.listing("r1") == ([], [])
    assert list((tmp_path / "blobs").iterdir()) == []


def test_bytes_stay_while_another_file_or_repository_uses_them(tmp_path):
    r = Repositories(tmp_path)
    other = r.create("둘째")
    r.put("r1", "x.csv", b"same")
    r.put(other, "y.csv", b"same")
    r.remove("r1", ["x.csv"])
    assert r.read(other, "y.csv") == b"same"
    r.put(other, "y.csv", b"changed")
    assert r.read(other, "y.csv") == b"changed" and len(list((tmp_path / "blobs").iterdir())) == 1


def test_repositories_in_a_folder_outlive_the_server(tmp_path):
    r = Repositories(tmp_path)
    second = r.create("둘째")
    r.put(second, "a/x.csv", b"1", facts={"kind": "data"})
    r.include(second, ["a"], False)
    again = Repositories(tmp_path)
    assert [x["label"] for x in again.rows()] == ["기본 리포지토리", "둘째"]
    assert again.entry(second, "a/x.csv")["included"] is False and again.read(second, "a/x.csv") == b"1"


def test_repositories_of_a_visitor_end_with_the_visitor():
    r = Repositories()
    r.put("r1", "x.csv", b"1")
    root = r.root
    assert root.is_dir()
    del r
    gc.collect()
    assert not root.exists()


def test_no_file_no_temporary_directory():
    assert Repositories()._root is None


def test_a_repository_needs_a_name_of_its_own_and_one_must_remain(tmp_path):
    r = Repositories(tmp_path)
    with pytest.raises(ValueError):
        r.create(" ")
    with pytest.raises(ValueError):
        r.create("기본 리포지토리")
    with pytest.raises(ValueError):
        r.delete_repo("r1")
    second = r.create("둘째")
    r.delete_repo("r1")
    assert r.create("셋째") != second


def test_a_row_says_what_each_file_turned_out_to_be(session):
    session.catalog_upload("원천/회원.csv", CSV)
    session.catalog_upload("원천/정책/규정.md", "# 반품\n\n7일 이내 반품합니다.\n".encode())
    session.catalog_upload("정의/shop.sql", b"CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(10));")
    session.catalog_upload("사진.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    top = session.catalog_state()
    assert [f["name"] for f in top["folders"]] == ["원천", "정의"] and top["included"] == 3 and top["unread"] == 1
    png = top["files"][0]
    assert png["ext"] == "png" and png["error"] and not png["error"].startswith("사진.png")
    rows = session.catalog_state("원천")["files"]
    assert rows[0]["facts"] == {"kind": "data", "tables": 1, "rows": 2, "columns": 2}
    assert session.catalog_state("원천/정책")["files"][0]["facts"]["kind"] == "document"
    assert session.catalog_state("정의")["files"][0]["facts"]["kind"] == "definition"
    with pytest.raises(LookupError):
        session.catalog_state("없는 폴더")


def test_what_goes_into_a_draft_follows_the_catalog(session):
    session.catalog_upload("a/회원.csv", CSV)
    session.catalog_upload("b/도서.csv", "도서번호,제목\nB1,가\nB2,나\n".encode())
    assert [f["source"] for f in session.files_state()["files"]] == ["a/회원.csv", "b/도서.csv"]
    assert session.make_draft("둘")["pending"]
    session.catalog_include(["b"], False)
    assert session.pending is None
    assert [f["source"] for f in session.files_state()["files"]] == ["a/회원.csv"]
    session.catalog_include(["b/도서.csv"], True)
    assert len(session.files_state()["files"]) == 2
    session.catalog_rename("b", "c")
    assert [f["source"] for f in session.files_state()["files"]] == ["a/회원.csv", "c/도서.csv"]
    session.catalog_remove(["a"])
    assert [f["source"] for f in session.files_state()["files"]] == ["c/도서.csv"]


def test_a_file_that_cannot_be_read_stays_out_of_the_draft(session):
    session.catalog_upload("x.pdf", b"%PDF")
    assert session.files_state()["files"] == [] and session.catalog_state()["included"] == 0
    assert session.catalog_file("x.pdf")["error"] and session.catalog_file("x.pdf")["json"] == ""
    assert session.catalog_download("x.pdf")[1] == b"%PDF"


def test_a_repository_is_a_set_of_files_of_its_own(session):
    session.catalog_upload("회원.csv", CSV)
    session.catalog_repository("create", label="둘째")
    assert session.files_state()["files"] == [] and session.state()["repository"]["label"] == "둘째"
    session.catalog_upload("도서.csv", "도서번호,제목\nB1,가\nB2,나\n".encode())
    session.catalog_repository("use", "r1")
    assert [f["source"] for f in session.files_state()["files"]] == ["회원.csv"]
    session.catalog_repository("rename", label="첫째")
    assert session.state()["repository"]["label"] == "첫째"
    session.catalog_repository("delete")
    assert session.state()["repository"]["label"] == "둘째"
    assert [f["source"] for f in session.files_state()["files"]] == ["도서.csv"]
    with pytest.raises(LookupError):
        session.catalog_repository("use", "r9")


def test_the_limits_count_every_repository(session):
    from xgen_space.web import DataOptions

    session.data = DataOptions(files=2, total_bytes=100)
    session.catalog_upload("a.csv", CSV)
    session.catalog_repository("create", label="둘째")
    session.catalog_upload("b.csv", b"a,b\n1,2\n3,4\n")
    with pytest.raises(ValueError):
        session.catalog_upload("c.csv", b"a,b\n1,2\n3,4\n")
    assert session.catalog_upload("b.csv", b"a,b\n1,2\n3,5\n")["ok"]  # a new copy takes the old one's place
    with pytest.raises(ValueError):
        session.catalog_upload("b.csv", b"x" * 101)


def test_litter_is_skipped_and_an_empty_name_refused(session):
    assert session.catalog_upload("a/.DS_Store", b"x")["skipped"] and session.catalog_state()["folders"] == []
    with pytest.raises(ValueError):
        session.catalog_upload("/", b"x")
    with pytest.raises(ValueError):
        session.catalog_folder(" ")
    with pytest.raises(ValueError):
        session.catalog_rename("a", "b/c")


def test_everything_rolls_up_into_one_json(session):
    assert session.catalog_convert()["counts"] == {}
    with pytest.raises(ValueError):
        session.catalog_json()
    session.catalog_upload("회원.csv", CSV)
    session.catalog_upload("t.sql", b"CREATE TABLE t (id INT PRIMARY KEY);")
    session.catalog_upload("규정.md", "# 반품\n\n7일 이내 반품합니다.\n".encode())
    session.catalog_upload("x.pdf", b"%PDF")
    r = session.catalog_convert()
    assert r["counts"]["tables"] == 2 and r["counts"]["documents"] == 1 and len(r["rows"]) == 4
    one = json.loads(session.catalog_json()[1].decode("utf-8"))
    assert {t["name"] for t in one["tables"]} >= {"t"} and one["documents"][0]["name"] == "규정"
    column = next(t for t in one["tables"] if t["name"] != "t")["columns"][0]
    assert column["type"] == "string" and "rows" not in column  # rows bring their columns and types, not the rows
    assert json.loads(session.catalog_file("회원.csv")["json"])["tables"]
    session.catalog_include(["t.sql"], False)
    assert session.catalog_convert()["counts"]["tables"] == 1


def test_a_server_folder_comes_in_only_where_the_install_allows_it(session, tmp_path):
    from xgen_space.web import DataOptions

    (tmp_path / "자료" / "하위").mkdir(parents=True)
    (tmp_path / "자료" / "하위" / "회원.csv").write_bytes(CSV)
    (tmp_path / "자료" / ".DS_Store").write_bytes(b"x")
    with pytest.raises(PermissionError):
        session.catalog_import(str(tmp_path / "자료"))
    session.data = DataOptions(allow_connect=True)
    assert session.catalog_import(str(tmp_path / "자료"))["imported"] == 1
    assert "자료/하위/회원.csv" in session.repositories.files(session.repo)
    with pytest.raises(ValueError):
        session.catalog_import(str(tmp_path / "없음"))


def test_visitors_share_a_kept_folder_and_each_reads_it(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    kept = Repositories(tmp_path)
    first = StudioSession(load_studio(EXAMPLE), data=DataOptions(), repositories=kept)
    first.catalog_upload("회원.csv", CSV)
    second = StudioSession(load_studio(EXAMPLE), data=DataOptions(), repositories=Repositories(tmp_path))
    assert [f["source"] for f in second.files_state()["files"]] == ["회원.csv"]
    assert second.state()["data"]["files"] == 1
