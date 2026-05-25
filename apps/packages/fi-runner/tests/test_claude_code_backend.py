"""Unit tests for ClaudeCodeBackend.

The allowlist and MCP-dict builders are SDK-free and tested directly. The
``build_options`` env passthrough (the explicit subscription/API mode knob)
needs ``claude_agent_sdk``, so those tests skip when the extra is absent.
"""

from __future__ import annotations

import os

import pytest

from fi_runner import ClaudeCodeBackend, MCPServerSpec, PermissionMode, ToolPolicy

# --- _allowlist (SDK-free) -------------------------------------------------


def test_allowlist_expands_named_mcp_tools():
    specs = [MCPServerSpec(name="cognitive", command="python", args=[], tools=("triage", "soap"))]
    policy = ToolPolicy(builtin_allowed=["Read"])
    assert ClaudeCodeBackend()._allowlist(specs, policy) == [
        "Read",
        "mcp__cognitive__triage",
        "mcp__cognitive__soap",
    ]


def test_allowlist_whole_server_when_no_tools_named():
    specs = [MCPServerSpec(name="persona", command="python", args=[])]
    assert ClaudeCodeBackend()._allowlist(specs, ToolPolicy()) == ["mcp__persona"]


# --- _mcp_dict (SDK-free) --------------------------------------------------


def test_mcp_dict_stdio_spec_carries_env_when_passthrough():
    specs = [MCPServerSpec(name="cognitive", command="python", args=["-m", "x"])]
    out = ClaudeCodeBackend()._mcp_dict(specs)
    assert out["cognitive"]["command"] == "python"
    assert out["cognitive"]["args"] == ["-m", "x"]
    assert out["cognitive"]["env"] == dict(os.environ)


def test_mcp_dict_stdio_spec_omits_env_when_disabled():
    specs = [MCPServerSpec(name="cognitive", command="python", args=[], env_passthrough=False)]
    out = ClaudeCodeBackend()._mcp_dict(specs)
    assert "env" not in out["cognitive"]


def test_mcp_dict_in_process_server_passed_through():
    sentinel = object()
    specs = [MCPServerSpec(name="insult_db", server=sentinel)]
    out = ClaudeCodeBackend()._mcp_dict(specs)
    assert out["insult_db"] is sentinel


# --- env passthrough (the subscription/API mode knob; needs the SDK) -------


def test_build_options_includes_env_when_provided():
    pytest.importorskip("claude_agent_sdk")
    backend = ClaudeCodeBackend(env={"ANTHROPIC_API_KEY": "sk-test", "CLAUDE_CODE_USE_BEDROCK": "0"})
    opts = backend.build_options(system_prompt="hi", mcp_servers=[], tool_policy=ToolPolicy())
    assert opts.env == {"ANTHROPIC_API_KEY": "sk-test", "CLAUDE_CODE_USE_BEDROCK": "0"}


def test_build_options_env_defaults_empty_for_subscription_mode():
    pytest.importorskip("claude_agent_sdk")
    # No env → rely on ambient OAuth (subscription mode). SDK default is {}.
    backend = ClaudeCodeBackend()
    opts = backend.build_options(system_prompt="hi", mcp_servers=[], tool_policy=ToolPolicy())
    assert opts.env == {}


def test_build_options_reflects_model_and_permission_mode():
    pytest.importorskip("claude_agent_sdk")
    backend = ClaudeCodeBackend(default_model="claude-sonnet-4-5")
    opts = backend.build_options(
        system_prompt="hi",
        mcp_servers=[],
        tool_policy=ToolPolicy(permission_mode=PermissionMode.ACCEPT_EDITS),
    )
    assert opts.model == "claude-sonnet-4-5"
    assert opts.permission_mode == "acceptEdits"
