"""Tests for the port-level MCP tool-id convention — the single source of truth
both backends and the tool-trace share (``mcp__<server>__<tool>``)."""

from __future__ import annotations

from fi_runner import ToolCall, mcp_server_of, mcp_server_token, mcp_tool_id


def test_mcp_tool_id_and_server_token_build_the_convention():
    assert mcp_tool_id("cognitive", "assess") == "mcp__cognitive__assess"
    assert mcp_server_token("cognitive") == "mcp__cognitive"


def test_mcp_server_of_is_the_inverse():
    assert mcp_server_of("mcp__cognitive__assess") == "cognitive"
    assert mcp_server_of(mcp_tool_id("persona", "tone")) == "persona"
    assert mcp_server_of("mcp__cognitive") == "cognitive"  # whole-server token


def test_mcp_server_of_none_for_builtin_or_garbage():
    assert mcp_server_of("Bash") is None
    assert mcp_server_of("Read") is None
    assert mcp_server_of("mcp__") is None  # degenerate prefix → no server


def test_tool_call_make_parses_server_via_convention():
    mcp = ToolCall.make("mcp__cognitive__assess", input={"q": "x"}, is_error=False)
    assert mcp.server == "cognitive" and mcp.is_error is False
    builtin = ToolCall.make("Bash", is_error=True)
    assert builtin.server is None and builtin.is_error is True
