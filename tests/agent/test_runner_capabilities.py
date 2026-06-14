"""The serving path (runner) MUST expose WebSearch — the false-green guard.

tests/chat/test_chat_cog.py asserts ``web_search_20250305`` on the LEGACY
stages.py path, which does NOT serve prod (LEGACY_LLM_ENABLED=false). That test
is green while the real path is blind — exactly how the 2026-06-14 incident hid:
Insult could not answer "are there more novels in this saga?" because the runner
allowlist (builtin_allowed plus MCP tools) had an empty builtin_allowed,
silently stripping WebSearch.

These tests assert the REAL path so dropping builtin_allowed fails CI instead of
shipping a bot that deflects every factual question.
"""

from __future__ import annotations

import pytest

from personas.insult.agent import runner


@pytest.mark.asyncio
async def test_runner_allowlist_includes_required_builtins():
    options = await runner._build_options("test-persona")
    allowed = set(getattr(options, "allowed_tools", None) or [])
    for tool in runner._REQUIRED_BUILTIN_TOOLS:
        assert tool in allowed, f"{tool} missing from runner allowlist: {sorted(allowed)}"


class _FakeOptions:
    def __init__(self, allowed_tools):
        self.allowed_tools = allowed_tools


def test_verify_required_tools_raises_when_missing():
    opts = _FakeOptions(["mcp__insult_db__get_user_facts"])  # no WebSearch/WebFetch
    with pytest.raises(RuntimeError, match="required built-in tools"):
        runner._verify_required_tools(opts)


def test_verify_required_tools_passes_when_present():
    opts = _FakeOptions([*runner._REQUIRED_BUILTIN_TOOLS, "mcp__insult_db__x"])
    runner._verify_required_tools(opts)  # must not raise
