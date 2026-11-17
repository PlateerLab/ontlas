"""The frame the screens sit in: the page is put together from the areas' files, an area registers its own routes, and
an item's history and readers are answered whatever kind the item is."""
from pathlib import Path

import pytest

from ontlas.config import load_studio
from ontlas.web import routes
from ontlas.web.api import StudioSession
from ontlas.web.server import STATIC, page
from ontlas.web.team import NEEDS, User

ROOT = Path(__file__).resolve().parent.parent
SHOP = ROOT / "examples" / "library" / "studio.yaml"


@pytest.fixture()
def session():
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")  # the example studio projects a graph
    routes.load()
    return StudioSession(load_studio(SHOP))


def test_the_page_holds_the_kit_and_every_area_file_inside_the_script():
    html = page().decode("utf-8")
    assert "/*PARTS*/" not in html and "/*CSS*/" not in html and "/*JS*/" not in html
    assert ".k-main" in html and "const V2 = {};" in html
    for part in sorted((STATIC / "v2").glob("*.js")):
        first = next(line for line in part.read_text(encoding="utf-8").splitlines() if line.strip())
        assert first.strip() in html, part.name
    # the areas' code runs before the address is read: a link to a registered screen is known when the page starts
    assert html.index("const V2 = {};") < html.rindex("readHash();")


def test_an_area_registers_a_route_and_what_a_post_needs():
    @routes.get("frame-test/read")
    def read(s, a, who):
        return {"ok": True}

    @routes.post("frame-test/write", needs="approver")
    def write(s, a, who):
        return {"ok": True}

    try:
        assert routes.find("GET", "frame-test/read") is read and routes.find("POST", "frame-test/write") is write
        assert routes.find("POST", "frame-test/read") is None
        assert NEEDS["frame-test/write"] == "approver"
        with pytest.raises(ValueError):
            routes.get("frame-test/read")(read)
        with pytest.raises(ValueError):
            routes.post("frame-test/other", needs="owner")
    finally:
        routes.GET.pop("frame-test/read", None)
        routes.POST.pop("frame-test/write", None)
        NEEDS.pop("frame-test/write", None)


def test_require_lets_everyone_through_where_nobody_signs_in_and_checks_a_team_user():
    routes.require(None, "admin")
    routes.require(User("kim", "김", "", ["admin"]), "admin")
    with pytest.raises(PermissionError):
        routes.require(User("lee", "이", "", ["viewer"]), "editor")


def test_who_reads_an_item_is_grouped_by_what_the_reader_is(session):
    out = routes.find("GET", "item/uses")(session, {"element": "object:OrderItem"}, None)
    assert out["exists"] and out["label"] == "주문상품"
    kinds = {u["kind"]: u for u in out["uses"]}
    assert "반품 가능 여부" in kinds["규칙"]["names"] and kinds["규칙"]["screen"] == "semrules"
    assert kinds["질의"]["screen"] == "query" and kinds["Action"]["names"] == ["반품 신청"]
    with pytest.raises(ValueError):
        routes.find("GET", "item/uses")(session, {"element": ""}, None)


def test_an_items_history_starts_with_the_edit_not_yet_sent_and_keeps_why(session):
    history = routes.find("GET", "item/history")
    before = history(session, {"element": "property:Order.status"}, None)
    assert before["now"] is not None and before["entries"] == []

    session.manage_edit("update_property", {"object": "Order", "name": "status", "label": "주문 진행 상태"})
    session.element_comment("property:Order.status", "화면 말과 맞춤")
    out = history(session, {"element": "property:Order.status"}, None)
    draft = out["entries"][0]
    assert draft["status"] == "draft" and draft["kind"] == "changed" and not draft["deployed"]
    assert any(f["field"] == "label" and f["after"] == "주문 진행 상태" for f in draft["fields"])
    assert [n["text"] for n in draft["notes"]] == ["화면 말과 맞춤"]

    res = session.manage_propose()  # one visitor is both sides: the change is approved as it is filed
    assert res["ok"] and not res["pending"]
    out = history(session, {"element": "property:Order.status"}, None)
    filed = out["entries"][0]
    assert filed["status"] == "approved" and filed["deployed"] and filed["change"] == res["change"]["id"]
    assert out["now"]["label"] == "주문 진행 상태"
    assert history(session, {"element": "object:Customer"}, None)["entries"] == []


def test_no_two_files_of_the_page_declare_the_same_name():
    """The areas' files share app.js's scope: a name declared twice stops the whole page before it draws."""
    import re

    seen: dict[str, str] = {}
    twice = []
    for part in [STATIC / "app.js", *sorted((STATIC / "v2").glob("*.js"))]:
        for line in part.read_text(encoding="utf-8").splitlines():
            m = re.match(r"  (?:const|let|class|async function|function)\s+([A-Za-z_$][\w$]*)", line)
            if m is None:
                continue
            if m.group(1) in seen:
                twice.append(f"{m.group(1)}: {seen[m.group(1)]} and {part.name}")
            seen[m.group(1)] = part.name
    assert not twice, twice


def test_the_script_of_the_page_parses(tmp_path):
    """Every file of the page put together as the server does it is one script a browser can read."""
    import re
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = re.search(r"<script>(.*)</script>", page().decode("utf-8"), re.S).group(1)
    path = tmp_path / "page.js"
    path.write_text(script, encoding="utf-8")
    out = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr[-800:]
