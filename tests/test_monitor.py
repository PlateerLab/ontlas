"""The control board: floors read from the studio, a fault that crosses them, and when it measures again."""
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).parent.parent / "examples" / "library" / "studio.yaml"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import DataOptions, StudioSession

    return StudioSession(load_studio(EXAMPLE), data=DataOptions())


def tags(board):
    return {t["key"]: t for f in board["floors"] for t in f["tags"]}


def test_five_floors_read_from_the_studio(session):
    b = session.monitor()
    assert [f["id"] for f in b["floors"]] == ["source", "convert", "ontology", "use", "verify"]
    assert b["status"] == "ok" and b["passed"] and b["alerts"] == [] and b["chain"] is None
    st = session.state()["stats"]
    t = tags(b)
    assert t["ontology.objects"]["value"] == str(st["objects"]) and t["ontology.links"]["value"] == str(st["links"])
    assert t["use.queries"]["value"] == str(st["queries"]) and t["verify.accuracy"]["value"] == "100%"
    assert len(b["parts"]["use"]["targets"]) == 8 and 0 < len(b["parts"]["ontology"]["nodes"]) <= 8
    ids = {n["id"] for n in b["parts"]["ontology"]["nodes"]}
    assert all(a in ids and c in ids for a, c in b["parts"]["ontology"]["edges"])


def test_a_module_that_breaks_the_source_shows_as_a_chain_across_floors(session):
    fault = session.monitor()["faults"][0]
    assert fault == {"label": "식품 업종 모듈 적용", "module": "food", "on": False}
    session.attach("food")
    b = session.monitor()
    floors = {f["id"]: f for f in b["floors"]}
    assert b["status"] == "bad" and not b["passed"] and b["faults"][0]["on"]
    assert floors["ontology"]["status"] == "bad" and floors["use"]["status"] == "bad" and floors["verify"]["status"] == "ok"
    assert tags(b)["ontology.findings"]["value"] == "2"
    assert [s["label"] for s in b["chain"]["steps"]] == ["질의", "DB 대조", "식품 업종 확장 모듈"]
    assert b["chain"]["floors"] == 2 and "Sku.expires_on" in b["chain"]["steps"][-1]["detail"]
    session.detach("food")
    b = session.monitor()
    assert b["status"] == "ok" and b["chain"] is None and b["measured"]


def test_it_measures_when_something_changed_or_a_while_has_passed(session, monkeypatch):
    import xgen_space.web.api as api

    assert session.monitor()["measured"]
    assert not session.monitor()["measured"]
    session.catalog_upload("회원.csv", "회원번호,이름\nM1,가\nM2,나\n".encode())
    b = session.monitor()
    assert b["measured"] and tags(b)["source.data"]["value"] == "1" and tags(b)["convert.sheet"]["value"] == "1"
    monkeypatch.setattr(api, "MONITOR_EVERY", 0.0)
    assert session.monitor()["measured"]


def test_a_file_it_could_not_read_is_a_warning_on_the_convert_floor(session):
    session.catalog_upload("x.pdf", b"%PDF")
    b = session.monitor()
    assert {f["id"]: f["status"] for f in b["floors"]}["convert"] == "warn" and b["status"] == "warn"
    assert b["alerts"][0]["title"] == "읽지 못한 파일 1개" and b["alerts"][0]["detail"] == "x.pdf"
    assert b["chain"] is None  # nothing downstream failed for it


def test_what_happened_is_on_the_board(session):
    session.catalog_upload("회원.csv", "회원번호,이름\nM1,가\nM2,나\n".encode())
    session.attach("food")
    texts = [e["text"] for e in session.monitor()["events"]]
    assert texts[0].startswith("파이프라인 측정") and any(t.startswith("파일 업로드 · 회원.csv") for t in texts)
    assert any("식품 업종 확장" in t for t in texts)


def test_a_shape_changes_only_with_what_is_drawn(session):
    a = session.monitor()["shape"]
    session.catalog_upload("회원.csv", "회원번호,이름\nM1,가\nM2,나\n".encode())
    assert session.monitor()["shape"] == a  # a number moved; the picture stays
    session.detach("finance-bindings", True)
    assert session.monitor()["shape"] != a


def test_a_studio_without_a_library_has_a_board_too():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from xgen_space.config import load_studio
    from xgen_space.web import StudioSession

    s = StudioSession(load_studio(Path(__file__).parent.parent / "examples" / "commerce" / "studio.yaml"))
    b = s.monitor()
    assert b["faults"] == [] and len(b["floors"]) == 5 and b["parts"]["ontology"]["modules"] == []
