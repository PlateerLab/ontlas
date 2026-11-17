"""`ontlas mcp` hands every option of the MCP server on to it."""
from ontlas import mcp_server
from ontlas.cli import main


def test_the_agent_s_name_and_its_journal_reach_the_server(monkeypatch):
    got = {}
    monkeypatch.setattr(mcp_server, "main", lambda argv: got.setdefault("argv", argv))
    code = main(["mcp", "studio.yaml", "--role", "customer_agent", "--principal", "customer_id=C001", "--read-only",
                 "--agent", "고객 응대 Agent", "--journal", "records/agent.jsonl", "--transport", "sse"])
    assert code == 0
    assert got["argv"] == ["studio.yaml", "--transport", "sse", "--role", "customer_agent", "--principal", "customer_id=C001",
                           "--read-only", "--agent", "고객 응대 Agent", "--journal", "records/agent.jsonl"]


def test_with_neither_given_nothing_is_added(monkeypatch):
    got = {}
    monkeypatch.setattr(mcp_server, "main", lambda argv: got.setdefault("argv", argv))
    main(["mcp", "studio.yaml"])
    assert got["argv"] == ["studio.yaml", "--transport", "stdio"]
