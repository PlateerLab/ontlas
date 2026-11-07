"""The data explorer: every asset of the space as folders, one search over every layer, and files managed with a trash."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = "# 포장 안내\n\n## 선물 포장\n\n선물 포장은 주문할 때 고르면 2천원이 더해집니다.\n".encode("utf-8")  # no example document has this name


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    s = StudioSession(load_studio(ROOT / "examples" / "library" / "studio.yaml"), data=DataOptions(samples=ROOT / "examples" / "files"))
    s.use_samples()
    s.catalog_folder("정책")
    s.catalog_upload("정책/포장안내.md", DOC)
    return s


def test_the_tree_holds_the_whole_space(session):
    e = session.explorer()
    ids = {n["id"] for n in e["tree"]}
    assert {"group:repos", "group:source", "group:document", "group:ontology", "group:store", "group:use"} <= ids
    assert {f"repo:{session.repo}", "dir:정책", "database:source", "kind:object", "kind:query"} <= ids
    s = e["summary"]
    assert s["files"] == len(session.repositories.files(session.repo)) and s["folders"] == 1
    assert s["tables"] > 0 and s["objects"] > 0 and s["chunks"] > 0
    assert next(n for n in e["tree"] if n["id"] == "dir:정책")["count"] == 1


def test_a_row_says_what_a_part_went_through(session):
    folder = next(r for r in session.explorer_items(f"repo:{session.repo}")["items"] if r["id"] == "dir:정책")
    assert [s["text"] for s in folder["status"]] == ["문서 색인 1/1", "초안 포함 1/1"]
    doc = session.explorer_items("dir:정책")["items"][0]
    assert doc["kind"] == "file" and doc["path"] == "정책/포장안내.md" and doc["bytes"] == len(DOC)
    assert any(s["text"].startswith("문서 색인 · 청크") for s in doc["status"])
    table = session.explorer_items("table:orders")
    assert [t["label"] for t in table["trail"]] == ["데이터베이스", "원천 DB"] and table["label"] == "orders"
    assert all(r["kind"] == "column" for r in table["items"]) and any(s["text"].startswith("속성") for r in table["items"] for s in r["status"])
    obj = session.explorer_items("object:Order")
    assert obj["items"] and all(r["kind"] == "property" for r in obj["items"])
    with pytest.raises(LookupError):
        session.explorer_items("nothing:here")


def test_one_search_says_which_layer_found_each_hit(session):
    r = session.explorer_search("배송비")
    found = {h["id"]: h["found"] for h in r["hits"]}
    assert "이름" in found["decision:shippingFee"] and "정의" in found["decision:shippingFee"]
    assert r["hits"][0]["id"] == "decision:shippingFee"  # found by name and definition, so it ranks above a passage
    wrap = {h["id"]: h for h in session.explorer_search("선물 포장")["hits"]}
    assert "단어 일치" in wrap["document:포장안내"]["found"] and "선물 포장" in wrap["document:포장안내"]["snippet"]
    assert [t["label"] for t in wrap["document:포장안내"]["trail"]] == ["문서", "문서 컬렉션"]
    folders = session.explorer_search("정책", "folder")["hits"]
    assert [h["id"] for h in folders] == ["dir:정책"]
    assert all(h["kind"] == "document" for h in session.explorer_search("배송비", "document")["hits"])
    with pytest.raises(ValueError):
        session.explorer_search("  ")


def test_files_go_to_the_trash_and_come_back(session):
    session.catalog_move(["회원.csv"], "정책")
    assert "정책/회원.csv" in session.repositories.files(session.repo)
    session.catalog_remove(["정책"])
    assert not any(p.startswith("정책") for p in session.repositories.files(session.repo))
    assert session.explorer()["summary"]["trash"] == 1
    assert "document:포장안내" not in {h["id"] for h in session.explorer_search("선물 포장")["hits"]}  # out of the space too
    t = session.catalog_trash()["items"][0]
    assert (t["path"], t["kind"], t["files"]) == ("정책", "folder", 2)
    assert session.catalog_trash_op("restore", [t["id"]])["restored"] == 2
    assert "document:포장안내" in {h["id"] for h in session.explorer_search("선물 포장")["hits"]}  # read again on restoring
    session.catalog_remove(["정책/회원.csv"])
    assert session.catalog_trash_op("purge", [])["purged"] == 1 and session.catalog_trash()["items"] == []
    acts = [e["action"] for e in session.catalog_history()["items"]]
    assert acts[:4] == ["purge", "trash", "restore", "trash"] and "move" in acts
    with pytest.raises(ValueError):
        session.catalog_trash_op("nothing", [])
