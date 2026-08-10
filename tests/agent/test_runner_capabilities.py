"""The serving path (runner) MUST expose WebSearch — the false-green guard.

The plumbing no longer defines a web_search tool at all (the agent runner
discards plumbing-side tool definitions), so the runner allowlist here is the
ONLY place WebSearch can come from — exactly how the 2026-06-14 incident hid:
Insult could not answer "are there more novels in this saga?" because the runner
allowlist (builtin_allowed plus MCP tools) had an empty builtin_allowed,
silently stripping WebSearch.

These tests assert the REAL path so dropping builtin_allowed fails CI instead of
shipping a bot that deflects every factual question.
"""

from __future__ import annotations

import pytest

from persona_runner.engine import options as runner_options


@pytest.mark.asyncio
async def test_runner_allowlist_includes_required_builtins():
    options = await runner_options.build_options("test-persona")
    allowed = set(getattr(options, "allowed_tools", None) or [])
    for tool in runner_options.REQUIRED_BUILTIN_TOOLS:
        assert tool in allowed, f"{tool} missing from runner allowlist: {sorted(allowed)}"


class _FakeOptions:
    """The guard reads BOTH directions since 2026-08-10, so a fake that only
    carries an allowlist is no longer a valid options object — `tools` (what the
    model can reach at all) is now part of the contract. See
    tests/arch/test_persona_capability_surface_is_bounded.py."""

    def __init__(self, allowed_tools, tools=None):
        self.allowed_tools = allowed_tools
        self.tools = list(runner_options.REQUIRED_BUILTIN_TOOLS) if tools is None else tools
        self.disallowed_tools = list(runner_options.FORBIDDEN_BUILTIN_TOOLS)


def test_verify_required_tools_raises_when_missing():
    opts = _FakeOptions(["mcp__persona_memory__get_user_facts"])  # no WebSearch/WebFetch
    with pytest.raises(RuntimeError, match="required built-in tools"):
        runner_options.verify_required_tools(opts)


def test_verify_required_tools_passes_when_present():
    opts = _FakeOptions([*runner_options.REQUIRED_BUILTIN_TOOLS, "mcp__persona_memory__x"])
    runner_options.verify_required_tools(opts)  # must not raise
