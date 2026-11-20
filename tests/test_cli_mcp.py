import asyncio
import json

import pytest

from ontlas.cli import main
from ontlas.tools import StudioTools

from .conftest import BOOKS, EXAMPLE


def _run(capsys, *args) -> tuple[int, str]:
    code = main([str(a) for a in args])
    return code, capsys.readouterr().out


def test_cli_validate_translate_export(capsys):
    pytest.importorskip("yaml")
    code, out = _run(capsys, "validate", EXAMPLE / "ontology.yaml")
    assert code == 0 and json.loads(out)["ok"]
    code, out = _run(capsys, "translate", EXAMPLE / "ontology.yaml", "lowStock", "--to", "cypher",
                     "--param", "threshold=5")
    data = json.loads(out)
    assert data["language"] == "cypher" and "s.`stock` < 5" in data["preview"]
    code, out = _run(capsys, "translate", EXAMPLE / "ontology.yaml",
                     "MATCH (o:Order) RETURN o.status, count(o) AS n", "--from", "cypher", "--to", "sql:sqlite")
    assert "GROUP BY" in json.loads(out)["text"]
    code, out = _run(capsys, "export", EXAMPLE / "ontology.yaml", "--format", "pgq")
    assert out.startswith("CREATE PROPERTY GRAPH")


def test_cli_studio_commands(capsys):
    pytest.importorskip("yaml")
    pytest.importorskip("rdflib")
    cfg = EXAMPLE / "studio.yaml"
    code, out = _run(capsys, "questions", cfg)
    assert code == 0 and json.loads(out)["accuracy"] == 1.0
    code, out = _run(capsys, "conformance", cfg)
    assert code == 0 and json.loads(out)["summary"]["disagree"] == []
    code, out = _run(capsys, "decide", cfg, "returnEligibility", "I1004")
    assert json.loads(out)["outputs"]["reason"] == "반품할 수 없는 카테고리입니다"
    code, out = _run(capsys, "cypher", cfg, "MATCH (p:Product) WHERE p.name CONTAINS '니트' RETURN p.name",
                     "--backend", "graph")
    assert json.loads(out)["rows"] == [{"name": "울 니트 스웨터"}]


def test_tools_are_role_scoped(studio):
    t = StudioTools(studio, role="customer_agent", principal={"customer_id": "C001"})
    assert "Customer" not in t.describe()["objects"]
    assert t.decide("returnEligibility", "I1001")["outputs"]["eligible"] is True
    with pytest.raises(PermissionError):
        t.decide("returnEligibility", "I1003")
    p = t.request_action("requestReturn", "I1001", {"reason": "사이즈"})
    assert p["status"] == "pending" and p["requested_by"]["kind"] == "agent"
    assert [r["item_id"] for r in t.run_query("myOrders")["rows"]] == ["I1001", "I1002", "I1005"]
    with pytest.raises(PermissionError):
        StudioTools(studio, read_only=True).request_action("requestReturn", "I1001", {})


def test_preview_page(graph_studio):
    from ontlas.preview import render

    html = render(graph_studio, query="revenueByCategory", decision="returnEligibility", key="I1001")
    for sid in ("ontology", "query", "decision", "map"):
        assert f'id="{sid}"' in html
    assert "Backend 결과 일치" in html and "order_items.delivered_at" in html


def test_preview_page_names_the_product_as_the_page_does_and_says_what_an_approved_request_does(graph_studio):
    """The logo is the name alone. Writing to the data source is off unless the studio turns it on: the request card
    says which, and a request approved while it is off shows as recorded."""
    from ontlas.actions import Actor
    from ontlas.preview import render

    kw = {"query": "revenueByCategory", "decision": "returnEligibility", "key": "I1001"}
    html = render(graph_studio, **kw)
    assert '<div class="brand">Ontlas</div>' in html and 'class="logo"' not in html and "원천" not in html
    assert "승인 대기" in html and "Agent 요청 · 데이터 소스 쓰기 꺼짐 · 승인 후 실행 결과만 기록" in html
    ask = graph_studio.actions.request

    def approved(*a, **k):  # the request the page makes, approved by a person before the page shows it
        p = ask(*a, **k)
        return graph_studio.actions.approve(p.id, approver=Actor("operator", "human", ["operator"]))

    graph_studio.actions.request = approved
    assert '<span class="chip warn">쓰기 꺼짐 · 실행 결과만 기록</span>' in render(graph_studio, **kw)
    graph_studio.actions.request = ask
    graph_studio.actions.write = True
    assert "Agent 요청 · 승인 후 데이터 소스 반영" in render(graph_studio, **kw)


def test_mcp_server_lists_and_calls_tools(studio):
    pytest.importorskip("mcp")
    from ontlas.mcp_server import build_server

    srv = build_server(studio, role="customer_agent", principal={"customer_id": "C001"}, read_only=True)
    names = {t.name for t in asyncio.run(srv.list_tools())}
    assert {"describe_ontology", "run_query", "run_sparql", "run_cypher", "decide", "translate_query"} <= names
    assert "request_action" not in names
    res = asyncio.run(srv.call_tool("translate_query", {"query": "lowStock", "to": "sql:mysql"}))
    assert "`skus`" in str(res)


def test_draft_expands_a_wildcard_the_shell_left_as_it_is(tmp_path):
    pytest.importorskip("yaml")
    out = tmp_path / "studio"
    assert main(["draft", str(BOOKS / "*.csv"), "--name", "books", "-o", str(out)]) == 0
    assert (out / "studio.yaml").is_file() and (out / "data.sqlite").is_file()
