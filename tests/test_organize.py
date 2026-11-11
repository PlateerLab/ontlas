"""Sorting what comes in: a file's embedding on or off, a folder as the range of a search, a reading and a role, and a change of
embedding model that says what it embeds again before it does."""
import json
import time
from pathlib import Path

import pytest

from ontlas.embed import EmbedError, HashEmbedder
from ontlas.repository import Repositories
from ontlas.space import Space, signature
from ontlas.vectors import MemoryStore

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "examples" / "library" / "studio.yaml"
DOCS = [{"name": "반품정책", "kind": "md", "text": "", "path": "정책/반품/반품정책.md", "sections": [
            {"title": "반품 기간", "text": "배송 완료 후 7일 이내의 주문상품은 반품할 수 있습니다. 반품 승인은 고객센터가 합니다."}]},
        {"name": "쿠폰약관", "kind": "md", "text": "", "path": "정책/쿠폰약관.md", "sections": [
            {"title": "중복 사용", "text": "쿠폰 두 장은 한 주문에 같이 쓸 수 없습니다."}]},
        {"name": "배송안내", "kind": "md", "text": "", "path": "안내/배송안내.md", "sections": [
            {"title": "배송비", "text": "주문 금액이 5만원 이상이면 배송비 없이 배송합니다."}]}]


def _space(**kw) -> Space:
    s = Space(HashEmbedder(64), **kw)
    for d in DOCS:
        s.add(json.loads(json.dumps(d)))
    s.index()
    return s


def test_a_document_with_its_embedding_off_leaves_the_stores_and_stays_in_the_ontology():
    s = _space()
    assert {c.document for c in s.chunks.values()} == {"반품정책", "쿠폰약관", "배송안내"}
    s.add({**DOCS[1], "embed": False})
    r = s.index()
    assert r["removed"] == 1 and "쿠폰약관" not in {c.document for c in s.chunks.values()}
    assert s.stores["memory"].count("documents") == len(s.chunks) == 2
    assert "쿠폰약관" in {c.document for c in s.passages.values()}
    assert all(h["document"] != "쿠폰약관" for h in s.search("쿠폰 두 장", 5))
    rows = {r["name"]: r for r in s.document_rows()}
    assert rows["쿠폰약관"]["state"] == "off" and rows["쿠폰약관"]["passages"] == 1 and rows["쿠폰약관"]["indexed"] == 0
    assert rows["반품정책"]["state"] == "embedded" and rows["반품정책"]["folder"] == "정책/반품"
    s.add(DOCS[1])
    assert s.index()["added"] == 1 and {r["state"] for r in s.document_rows()} == {"embedded"}


def test_a_folder_is_the_range_of_a_search_with_the_folders_under_it():
    s = _space()
    assert s.folders() == ["안내", "정책", "정책/반품"]
    assert {h["document"] for h in s.search("주문", 5, folder="정책")} == {"반품정책", "쿠폰약관"}
    assert {h["document"] for h in s.search("주문", 5, folder="정책/반품")} == {"반품정책"}
    assert {h["folder"] for h in s.search("주문", 5)} == {"정책/반품", "정책", "안내"}
    assert s.search("주문", 5, folder="없는 폴더") == [] and s.search("주문", 5, folder="정책/반") == []
    assert s.in_folder("반품정책", "정책") and not s.in_folder("배송안내", "정책") and s.path_of("배송안내") == "안내/배송안내.md"


def test_every_vector_says_which_model_made_it():
    s = _space()
    pts = s.stores["memory"].data["documents"]
    assert {p.payload["embedder"] for p in pts.values()} == {signature(s.embedder)} == {s.model}
    assert {p.payload["folder"] for p in pts.values()} == {"정책/반품", "정책", "안내"}


def test_a_change_of_model_says_what_it_embeds_again_and_then_does_it():
    s = _space()
    s.add({**DOCS[2], "embed": False})
    new = HashEmbedder(32)
    plan = s.reembed_plan(new)
    assert not plan["same"] and plan["chunks"] == 2 and {f["document"] for f in plan["files"]} == {"반품정책", "쿠폰약관"}
    assert plan["chars"] == sum(len(c.text) for c in s.passages.values() if c.document != "배송안내") and plan["seconds"] >= 0
    assert s.embedder.dim == 64 and len(next(iter(s.stores["memory"].data["documents"].values())).vector) == 64  # nothing changed yet
    r = s.use_embedder(new)
    assert r["added"] == 2 and s.model == signature(new) and s.embedder is new
    assert {len(p.vector) for p in s.stores["memory"].data["documents"].values()} == {32}
    assert s.search("쿠폰 두 장", 1)[0]["document"] == "쿠폰약관"
    assert s.reembed_plan(new)["same"]


def test_a_model_that_fails_leaves_the_stores_searching_what_they_held():
    s = _space()

    class Broken(HashEmbedder):
        def embed(self, texts):
            if any("새 문서" in t for t in texts):
                raise EmbedError("the model is down")
            return super().embed(texts)

    s.embedder = Broken(64)
    s.add({"name": "새 문서", "kind": "md", "text": "새 문서 본문입니다.", "path": "새 문서.md"})
    r = s.index()
    assert r["embed_error"] == "the model is down" and len(s.chunks) == 3
    rows = {r["name"]: r for r in s.document_rows()}
    assert rows["새 문서"]["state"] == "failed" and rows["반품정책"]["state"] == "embedded"
    assert s.search("쿠폰", 1)[0]["document"] == "쿠폰약관" and not s.state()["ok"]


def test_a_store_behind_is_filled_again_with_vectors_made_once():
    s = _space(stores={"a": MemoryStore("a"), "b": MemoryStore("b")})
    s.errors["b"] = "놓친 회차"
    s.add({"name": "추가", "kind": "md", "text": "추가 문서입니다.", "path": "추가.md"})
    s.index()
    assert s.stores["a"].count("documents") == s.stores["b"].count("documents") == 4 and not s.errors


def test_the_repository_keeps_each_files_embedding_and_says_it_in_its_record(tmp_path):
    r = Repositories(tmp_path)
    repo = next(iter(r.items))
    r.put(repo, "정책/a.md", b"# a")
    r.put(repo, "정책/b.md", b"# b")
    assert r.entry(repo, "정책/a.md")["embed"] is True
    r.embed(repo, ["정책"], False)
    assert not r.entry(repo, "정책/b.md")["embed"]
    r.put(repo, "정책/a.md", b"# a2")  # replacing a file keeps its setting
    assert r.entry(repo, "정책/a.md")["embed"] is False
    folders, _ = r.listing(repo)
    assert folders[0]["embedded"] == 0 and folders[0]["files"] == 2
    assert r.history(repo)[1]["action"] == "unembed"
    again = Repositories(tmp_path)
    assert again.entry(repo, "정책/a.md")["embed"] is False


def test_a_role_reads_documents_by_the_folder_of_their_file():
    from ontlas.model import Role

    r = Role("cs", documents=["정책/*"])
    assert r.can_read_document("반품정책", "정책/반품/반품정책.md") and not r.can_read_document("배송안내", "안내/배송안내.md")
    assert Role("all").can_read_document("x") and Role("named", documents=["배송안내"]).can_read_document("배송안내", "안내/배송안내.md")


# ---- the page ------------------------------------------------------------------------------------------------------------

@pytest.fixture
def session(tmp_path):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    s = StudioSession(load_studio(CFG), data=DataOptions(repositories=tmp_path), repositories=Repositories(tmp_path))
    s.catalog_upload("정책/반품/반품규정.md", "# 반품규정\n\n## 반품 승인\n\n반품 승인은 고객센터가 합니다. 고객센터는 평일에 답합니다. 반품 기간은 7일입니다.\n".encode("utf-8"))
    s.catalog_upload("안내/배송규정.md", "# 배송규정\n\n## 배송비\n\n배송비는 주문 금액이 5만원 이상이면 없습니다.\n".encode("utf-8"))
    return s


def test_the_catalog_says_how_each_file_is_embedded_and_turns_it_off(session):
    files = {f["path"]: f for f in session.catalog_state("정책/반품")["files"]}
    assert files["정책/반품/반품규정.md"]["embed"] and files["정책/반품/반품규정.md"]["index"]["state"] == "embedded"
    assert files["정책/반품/반품규정.md"]["index"]["chunks"] >= 1
    session.catalog_embed(["정책"], False)
    f = next(f for f in session.catalog_state("정책/반품")["files"])
    assert f["index"] == {"state": "off", "chunks": 0, "passages": f["index"]["passages"]} and f["index"]["passages"] >= 1
    assert all(h["document"] != "반품규정" for h in session.space_search("반품 승인", 10)["hits"])
    graph = session.space_graph()
    assert any(n["label"] == "반품규정" for n in graph["nodes"])  # still in the document ontology
    assert next(d for d in session.space_state()["items"] if d["name"] == "반품규정")["state"] == "off"
    assert session.catalog_history()["items"][0]["action"] == "unembed"


def test_a_question_and_a_search_keep_to_a_folder(session):
    hits = session.space_search("반품", 10, folder="안내")["hits"]
    assert hits and {h["document"] for h in hits} == {"배송규정"}
    out = session.space_ask("반품 승인은 누가 하나요", folder="정책")
    assert out["sources"] and {s.get("document") for s in out["sources"] if s.get("document")} <= {"반품규정"}
    assert {"정책", "정책/반품", "안내"} <= set(session.space_state()["folders"])
    g = session.space_graph("안내")
    assert {n["label"] for n in g["nodes"] if n["module"] == "document"} == {"배송규정"} and g["folder"] == "안내"


def test_a_role_kept_to_a_folder_answers_from_that_folder_only(session):
    session.studio.onto.roles["customer_agent"].documents = ["정책/*"]
    out = session.space_ask("반품 기간은 며칠인가요", role="customer_agent")
    docs = {s.get("document") for s in out["sources"] if s.get("document")}
    assert docs and docs <= {"반품규정"}
    assert {s.get("document") for s in session.space_ask("반품 기간은 며칠인가요")["sources"] if s.get("document")} - {"반품규정"}


def test_the_page_lists_the_models_and_plans_a_change(session):
    st = session.space_state()
    kinds = {e["kind"] for e in st["embedders"]}
    assert "hash" in kinds
    plan = session.space_embedder("plan", {"kind": "hash", "dim": 512})
    assert plan["ok"] and plan["chunks"] >= 2 and any(f["path"] == "정책/반품/반품규정.md" for f in plan["files"])
    with pytest.raises(PermissionError):
        session.space_embedder("plan", {"kind": "fastembed", "model": "any/model"})  # not one the server has open
    out = session.space_embedder("use", {"kind": "hash", "dim": 512})
    assert out["embedder"]["dim"] == 512 and any("임베딩 모델 변경" in e["text"] for e in session.events)


def test_relations_are_read_on_the_server_and_kept_with_the_repositories(session, tmp_path):
    from ontlas.config import load_studio
    from ontlas.web import DataOptions, StudioSession

    def llm(system, user):
        import re

        rows = []
        for u, names in re.findall(r"^\[(\d+)\] .*\n  개념: (.+)$", user, re.M):
            named = {m.strip(): int(k) for k, m in re.findall(r"(\d+)=(.+?)(?= \d+=|$)", names)}
            if "반품" in named and "고객센터" in named:
                rows.append({"u": int(u), "s": named["반품"], "p": "approvedBy", "o": named["고객센터"], "label": "승인 주체"})
        return json.dumps(rows, ensure_ascii=False)

    session.llm = llm
    assert session.relations_start("정책", "basic")["ok"]
    job = session._reading["id"]
    for _ in range(100):
        st = session.relations_status(job)
        if not st["running"]:
            break
        time.sleep(0.05)
    assert st["result"]["ok"] and st["result"]["found"] >= 1 and st["read"] == st["passages"] and st["folder"] == "정책"
    listed = session.relations_list("정책")
    assert listed["relations"][0]["predicate"] == "approvedBy" and "고객센터" in listed["relations"][0]["evidence"]
    assert session.relations_list("안내")["relations"] == []
    assert (tmp_path / "relations.json").is_file()
    again = StudioSession(load_studio(CFG), data=DataOptions(repositories=tmp_path), repositories=Repositories(tmp_path))
    assert again.relations_list("정책")["total"] == listed["total"]
    assert again.relations_forget("정책")["forgot"] >= 1 and again.relations_list("정책")["total"] == 0
    session.llm = None
    assert not session.relations_start("정책")["ok"]


def test_rest_and_tools_take_a_folder(session):
    from ontlas.rest import ROUTES
    from ontlas.tools import StudioTools

    session.space_state()  # a page request brings the catalog's documents into the space
    t = StudioTools(session.studio)
    assert {h["document"] for h in t.search_documents("반품", 10, folder="안내")["hits"]} == {"배송규정"}
    route = next(r for r in ROUTES if r[0] == "/v1/search")
    assert "folder" in route[4] and {h["document"] for h in route[6](t, {"text": "반품", "folder": "안내"})["hits"]} == {"배송규정"}
    answer = next(r for r in ROUTES if r[0] == "/v1/answer")
    assert "folder" in answer[4]
