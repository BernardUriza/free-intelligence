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


# --- _collect: text + usage/cost/session extraction (SDK-free duck types) ---
#
# _collect dispatches on ``type(message).__name__``, so these fakes are named
# exactly as the SDK's message/block classes — no SDK or network needed.


class AssistantMessage:
    def __init__(self, content):
        self.content = content


class TextBlock:
    def __init__(self, text):
        self.text = text


class ResultMessage:
    def __init__(self, *, usage, total_cost_usd=None, session_id=None):
        self.usage = usage
        self.total_cost_usd = total_cost_usd
        self.session_id = session_id


class ToolUseBlock:
    def __init__(self, name, input, id):  # noqa: A002 - mirrors the SDK block field
        self.name = name
        self.input = input
        self.id = id


class UserMessage:
    def __init__(self, content):
        self.content = content


class ToolResultBlock:
    def __init__(self, tool_use_id, is_error=False):
        self.tool_use_id = tool_use_id
        self.is_error = is_error


class _FakeClient:
    def __init__(self, messages):
        self._messages = messages

    async def receive_response(self):
        for m in self._messages:
            yield m


@pytest.mark.asyncio
async def test_collect_extracts_text_usage_and_session():
    client = _FakeClient(
        [
            AssistantMessage([TextBlock("Hola "), TextBlock("mundo")]),
            ResultMessage(
                usage={"input_tokens": 10, "output_tokens": 5},
                total_cost_usd=0.0012,
                session_id="sdk-123",
            ),
        ]
    )
    text, usage, session_id, tools = await ClaudeCodeBackend._collect(client)
    assert text == "Hola mundo"
    assert usage == {"input_tokens": 10, "output_tokens": 5, "total_cost_usd": 0.0012}
    assert session_id == "sdk-123"
    assert tools == []


@pytest.mark.asyncio
async def test_collect_handles_turn_without_result_message():
    client = _FakeClient([AssistantMessage([TextBlock("solo texto")])])
    text, usage, session_id, tools = await ClaudeCodeBackend._collect(client)
    assert text == "solo texto"
    assert usage is None
    assert session_id is None
    assert tools == []


@pytest.mark.asyncio
async def test_collect_captures_tool_trace_with_result_status():
    # An MCP tool that succeeded + a built-in that failed; results feed back as
    # ToolResultBlocks in a following UserMessage, matched by id.
    client = _FakeClient(
        [
            AssistantMessage(
                [
                    ToolUseBlock("mcp__cognitive__assess", {"q": "phi"}, "t1"),
                    TextBlock("pensando..."),
                    ToolUseBlock("Bash", {"command": "ls"}, "t2"),
                ]
            ),
            UserMessage([ToolResultBlock("t1", is_error=False), ToolResultBlock("t2", is_error=True)]),
            AssistantMessage([TextBlock("listo")]),
        ]
    )
    text, _usage, _sess, tools = await ClaudeCodeBackend._collect(client)
    assert text == "pensando...listo"
    assert [t.name for t in tools] == ["mcp__cognitive__assess", "Bash"]
    assert tools[0].server == "cognitive" and tools[0].is_error is False
    assert tools[1].server is None and tools[1].is_error is True  # built-in, failed
    assert tools[0].input == {"q": "phi"}  # input kept on the object (not in telemetry)
