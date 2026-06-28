"""Tests for the port-level MCP tool-id convention — the single source of truth
both backends and the tool-trace share (``mcp__<server>__<tool>``)."""

from __future__ import annotations

from fi_runner import (
    COMPANION_BLOCKED_BUILTINS,
    PermissionMode,
    ToolCall,
    ToolPolicy,
    mcp_server_of,
    mcp_server_token,
    mcp_tool_id,
)


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


# --- ToolPolicy.companion() — the framework-level non-coding profile -----------


def test_companion_blocks_every_filesystem_and_shell_builtin():
    """A companion must never reach the host's shell, files, or repo — the og118
    #277 exposure raised to the framework so every companion inherits it."""
    policy = ToolPolicy.companion()
    blocked = set(policy.builtin_disallowed)
    for tool in ("Bash", "Write", "Edit", "NotebookEdit", "Read", "Grep", "Glob", "LS", "Task"):
        assert tool in blocked, f"{tool} must be blocked for a companion"


def test_companion_defaults_to_bypass_so_the_blocklist_is_what_bites():
    """BYPASS grants every builtin EXCEPT the disallowed list — that inversion is
    exactly why the blocked builtins must be named, and why the profile pairs them."""
    assert ToolPolicy.companion().permission_mode is PermissionMode.BYPASS


def test_companion_allows_opting_extra_builtins_in():
    policy = ToolPolicy.companion(builtin_allowed=["WebSearch"])
    assert policy.builtin_allowed == ["WebSearch"]
    # opting one in never un-blocks the filesystem set
    assert "Read" in policy.builtin_disallowed


def test_companion_profile_matches_the_exported_constant():
    assert set(ToolPolicy.companion().builtin_disallowed) == set(COMPANION_BLOCKED_BUILTINS)


def test_companion_returns_independent_lists_per_call():
    """Mutating one policy's lists must not leak into the shared constant or another
    policy (the classmethod copies, never aliases the module tuple)."""
    a = ToolPolicy.companion()
    a.builtin_disallowed.append("Mutated")
    b = ToolPolicy.companion()
    assert "Mutated" not in b.builtin_disallowed
    assert "Mutated" not in COMPANION_BLOCKED_BUILTINS
