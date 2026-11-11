"""The control board: floors read from the studio, a fault that crosses them, and when it measures again."""
from pathlib import Path

import pytest

from .conftest import LIB

EXAMPLE = LIB / "studio.yaml"


@pytest.fixture
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    return StudioSession(load_studio(EXAMPLE), data=DataOptions())


def tags(board):
    return {t["key"]: t for f in board["floors"] for t in f["tags"]}


def test_five_floors_read_from_the_studio(session):
    b = session.monitor()
    assert [f["id"] for f in b["floors"]] == ["source", "convert", "ontology", "store", "use", "verify"]
    assert b["status"] == "ok" and b["passed"] and b["alerts"] == [] and b["chain"] is None
    st = session.state()["stats"]
    t = tags(b)
    assert t["ontology.objects"]["value"] == str(st["objects"]) and t["ontology.links"]["value"] == str(st["links"])
    assert t["use.queries"]["value"] == str(st["queries"]) and t["verify.accuracy"]["value"] == "100%"
    assert len(b["parts"]["use"]["targets"]) == 9 and 0 < len(b["parts"]["ontology"]["nodes"]) <= 8
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
    import ontlas.web.api as api

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
    assert b["alerts"][0]["title"] == "읽기 실패 파일 1개" and b["alerts"][0]["detail"] == "x.pdf"
    assert b["chain"] is None  # nothing downstream failed for it


def test_what_happened_is_on_the_board(session):
    session.catalog_upload("회원.csv", "회원번호,이름\nM1,가\nM2,나\n".encode())
    session.attach("food")
    texts = [e["text"] for e in session.monitor()["events"]]
    assert texts[0].startswith("파이프라인 점검 완료") and any(t.startswith("파일 업로드 · 회원.csv") for t in texts)
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
    from ontlas.config import load_studio
    from ontlas.web import StudioSession

    s = StudioSession(load_studio(Path(__file__).parent.parent / "examples" / "commerce" / "studio.yaml"))
    b = s.monitor()
    assert b["faults"] == [] and len(b["floors"]) == 6 and b["parts"]["ontology"]["modules"] == []


CSV = "회원번호,이름\nM1,가\nM2,나\n".encode("utf-8")


def applied(session, label):
    session.catalog_upload(f"{label}.csv", CSV)
    session.make_draft(label)
    session.apply_draft({})


def test_an_applied_draft_is_a_pipeline_and_the_one_before_stays(session):
    objects = session.state()["stats"]["objects"]
    applied(session, "도서관")
    st = session.state()
    assert [p["label"] for p in st["pipelines"]] == ["기본 파이프라인", "도서관"] and st["pipeline"] == "p2"
    assert st["stats"]["objects"] != objects and st["origin"]["label"] == "도서관"
    session.pipeline_use("p1")
    st = session.state()
    assert st["stats"]["objects"] == objects and st["origin"]["kind"] == "config" and st["pipeline"] == "p1"
    assert session.run_query("revenueByCategory")["agree"]
    session.pipeline_use("p2")
    assert session.state()["title"] == "도서관" and session.monitor()["measured"]


def test_each_pipeline_keeps_what_was_done_on_it(session):
    session.attach("food")
    assert session.monitor()["status"] == "bad"
    applied(session, "도서관")
    assert session.monitor()["status"] == "ok" and session.state()["log"][0]["text"].startswith("도서관")
    session.pipeline_use("p1")
    b = session.monitor()
    assert b["status"] == "bad" and b["faults"][0]["on"]
    assert any("식품 업종 확장" in x["text"] for x in session.state()["log"])


def test_a_draft_applied_again_under_its_name_takes_its_place(session):
    applied(session, "도서관")
    applied(session, "도서관")
    assert [p["id"] for p in session.state()["pipelines"]] == ["p1", "p2"]


def test_pipelines_keep_to_their_limit_and_the_first_stays(session):
    from ontlas.web.api import PIPELINES_MAX

    for i in range(PIPELINES_MAX - 1):
        applied(session, f"초안{i}")
    with pytest.raises(ValueError):
        applied(session, "하나 더")
    assert len(session.state()["pipelines"]) == PIPELINES_MAX
    with pytest.raises(ValueError):
        session.pipeline_delete("p1")
    with pytest.raises(LookupError):
        session.pipeline_use("p99")
    current = session.state()["pipeline"]
    session.pipeline_delete(current)  # the one on screen: back to the first
    st = session.state()
    assert st["pipeline"] == "p1" and len(st["pipelines"]) == PIPELINES_MAX - 1


@pytest.mark.parametrize("text,word", [
    ("module: t\nversion: 1.0.0\nkind: domain\nrequires: [nothing]\n", "의존 모듈"),
    ("module: t\nversion: 1.0.0\nkind: domain\nobjects: {A: {key: id, properties: {id: {type: nope}}}}\n", "타입"),
    ("module: t\nversion: 1.0.0\nkind: domain\ndecisions: {d: {target: Zed, rules: []}}\n", "대상 Entity"),
])
def test_a_module_check_speaks_the_product_language(session, text, word):
    issues = session.check_module(text)["issues"]
    assert word in issues[0] and not any("satisfies" in x or "is not one of" in x or "is unknown" in x for x in issues)


@pytest.mark.parametrize("text", ["module: t\nversion: 1.0.0\nkind: domain\nobjects: {A: {table: t, properties: {x: {type: string}}}}\n",
                                  "module: t\nversion: 1.0.0\nkind: domain\nlinks: {l: {source: A, target: B}}\n"])
def test_a_module_with_a_field_missing_says_which(session, text):
    try:
        out = session.check_module(text)["issues"][0]
    except ValueError as e:
        out = str(e)
    assert "항목이 없어" in out


def test_a_database_that_does_not_answer_is_told_plainly(session, monkeypatch):
    import ontlas.config as config
    from ontlas.web import DataOptions

    session.data = DataOptions(allow_connect=True)

    def down(spec, base):
        raise OSError("connection to server at 10.0.0.1 failed for user admin password secret")

    monkeypatch.setattr(config, "open_backend", down)
    with pytest.raises(ValueError) as e:
        session.connect("postgresql://admin:secret@10.0.0.1/shop")
    assert "연결하지 못했습니다" in str(e.value) and "secret" not in str(e.value) and "admin" not in str(e.value)


def test_a_typed_query_error_says_what_to_fix(session):
    assert "Entity를 찾지 못했습니다" in session.run_text("cypher", "MATCH (n:Nope) RETURN n")["error"]
    assert "JSON 형식" in session.run_text("ir", "{bad")["error"]
