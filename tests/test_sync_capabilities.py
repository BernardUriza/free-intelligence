"""Tests for scripts/sync_capabilities.py — the pre-commit hook that
auto-injects the CAPABILITIES block into persona.md.

Coverage focus is the v3.9.73 addition: fi-core MCP tools discovery.
The earlier insult-side tool extraction is exercised implicitly every
commit (pre-commit hook runs the full sync against the live repo) but
the fi-core path has a hybrid resolver (explicit contract → AST
fallback) whose branches are not all guaranteed to exercise on a given
fi-core version. These tests pin both paths against synthetic inputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

# Importing the script as a module requires scripts/ on sys.path.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def test_detect_fi_core_reads_environment_yml(tmp_path, monkeypatch):
    """Post-conda migration (v3.9.72), detect_fi_core reads environment.yml.

    The earlier requirements.txt path is preserved as a fallback but
    environment.yml takes precedence. Both formats are checked here.
    """
    import sync_capabilities as sc

    # Synthetic env.yml with fi-core declared
    env = tmp_path / "environment.yml"
    env.write_text("name: x\ndependencies:\n  - fi-core>=0.4.0\n")
    monkeypatch.setattr(sc, "ROOT", tmp_path)
    assert sc.detect_fi_core() is True

    # No env.yml, no requirements.txt → False
    env.unlink()
    assert sc.detect_fi_core() is False

    # requirements.txt-only fallback
    req = tmp_path / "requirements.txt"
    req.write_text("fi-core @ git+https://github.com/x/y\n")
    assert sc.detect_fi_core() is True

    # Neither file mentions fi-core → False
    req.write_text("other-pkg>=1.0\n")
    assert sc.detect_fi_core() is False


def test_extract_fi_core_mcp_tools_uses_explicit_contract(monkeypatch):
    """Path 1: when `fi_core.persona.MCP_TOOLS` exists, that wins.

    Bernard's 2026-05-19 contract decision: fi-core controls what tools
    are exposed via an explicit constant rather than discord-bot
    introspecting fi-core internals. This test pins that when the
    contract IS present, the AST fallback is skipped.
    """
    # Build a fake fi_core.persona module with the contract.
    import types

    import sync_capabilities as sc

    fake_persona = types.ModuleType("fi_core.persona")
    fake_persona.MCP_SERVER_NAME = "test-server"
    fake_persona.MCP_TOOLS = [
        {"name": "alpha", "description": "First sentence. Second sentence."},
        {"name": "beta", "description": "Only one sentence"},
        {"name": "gamma"},  # No description — should still appear
    ]
    fake_fi_core = types.ModuleType("fi_core")
    fake_fi_core.persona = fake_persona
    monkeypatch.setitem(sys.modules, "fi_core", fake_fi_core)
    monkeypatch.setitem(sys.modules, "fi_core.persona", fake_persona)

    result = sc.extract_fi_core_mcp_tools()

    assert len(result) == 3
    assert result[0] == {
        "name": "mcp__test-server__alpha",
        "desc": "First sentence.",
    }
    assert result[1] == {
        "name": "mcp__test-server__beta",
        "desc": "Only one sentence.",
    }
    assert result[2]["name"] == "mcp__test-server__gamma"
    assert result[2]["desc"] == ""


def test_extract_fi_core_mcp_tools_returns_empty_when_no_fi_core(monkeypatch):
    """If fi-core is not installed at all, return [] — not raise.

    pre-commit might run in an environment without conda deps
    materialized; that should not crash sync_capabilities, just leave
    the fi-core tool block empty until the next commit from a fully-
    set-up env.
    """
    import sync_capabilities as sc

    # Force both import paths to fail
    monkeypatch.setitem(sys.modules, "fi_core", None)
    monkeypatch.setitem(sys.modules, "fi_core.persona", None)
    monkeypatch.setitem(sys.modules, "fi_core.persona.mcp_server", None)

    assert sc.extract_fi_core_mcp_tools() == []


def test_extract_fi_core_mcp_tools_ast_fallback_when_no_contract(monkeypatch, tmp_path):
    """Path 2: when fi-core 0.4.0 lacks the contract constants, AST-walk
    its installed mcp_server.py for `@mcp.tool()` decorators.

    Synthesizes the file shape that fi-core 0.4.0 actually ships.
    """
    import types

    import sync_capabilities as sc

    # fake module WITHOUT MCP_TOOLS/MCP_SERVER_NAME — triggers path 2
    fake_persona = types.ModuleType("fi_core.persona")
    fake_fi_core = types.ModuleType("fi_core")
    fake_fi_core.persona = fake_persona
    monkeypatch.setitem(sys.modules, "fi_core", fake_fi_core)
    monkeypatch.setitem(sys.modules, "fi_core.persona", fake_persona)

    # Synthesize a mcp_server.py with @mcp.tool() decorated functions
    src = tmp_path / "mcp_server.py"
    src.write_text(
        """
from fastapi import FastMCP
mcp = FastMCP("test-server")

@mcp.tool()
async def list_packs() -> dict:
    \"\"\"List all built-in pattern packs available on this server.

    Returns a dictionary with one entry per pack.
    \"\"\"
    return {}

@mcp.tool()
async def check_drift(text: str) -> dict:
    \"\"\"Detect persona drift in ``text`` using the listed packs.\"\"\"
    return {}

@mcp.tool()
def sync_helper() -> dict:
    \"\"\"Synchronous helper. Also decorated, also picked up.\"\"\"
    return {}
"""
    )
    fake_mcp_server = types.ModuleType("fi_core.persona.mcp_server")
    fake_mcp_server.__file__ = str(src)
    monkeypatch.setitem(sys.modules, "fi_core.persona.mcp_server", fake_mcp_server)

    result = sc.extract_fi_core_mcp_tools()

    # Server name in fallback is hardcoded to "fi-core-persona" (matches
    # the actual FastMCP("fi-core-persona") init in fi-core 0.4.0)
    names = {t["name"] for t in result}
    assert "mcp__fi-core-persona__list_packs" in names
    assert "mcp__fi-core-persona__check_drift" in names
    assert "mcp__fi-core-persona__sync_helper" in names

    # First-paragraph extraction works: multi-paragraph docstring drops
    # the "Returns a dictionary..." part
    list_packs = next(t for t in result if t["name"].endswith("list_packs"))
    assert list_packs["desc"] == "List all built-in pattern packs available on this server."


def test_extract_mcp_tool_names_finds_insult_db_tools():
    """Sanity: the insult-side extractor still works against the real
    `insult/agent/mcp_tools.py`. This is the path that has been live
    since the agent runner shipped — the test pins it doesn't silently
    break when sync_capabilities is refactored.
    """
    import sync_capabilities as sc

    tools = sc.extract_mcp_tool_names()
    names = {t["name"] for t in tools}
    # The 7 known mcp__insult_db__* tools from mcp_tools.py
    assert "mcp__insult_db__get_user_facts" in names
    assert "mcp__insult_db__deep_memory" in names
    assert "mcp__insult_db__publish_html_artifact" in names
    # Every tool has a non-empty description
    for t in tools:
        assert t["desc"], f"tool {t['name']} missing description"


@pytest.mark.parametrize(
    "module,present",
    [
        ("deep_memory", True),  # added 2026-05-19
        ("html_artifacts", True),  # added v3.9.57
        ("agent_runner_mcp", True),  # always present in F4
    ],
)
def test_detect_modules_picks_up_recent_additions(module, present):
    """Regression: detect_modules() forgot to include deep_memory +
    html_artifacts when those modules were added. The pre-commit hook
    was running but the capabilities block was incomplete. This test
    pins the additions stay in the detection dict.
    """
    import sync_capabilities as sc

    modules = sc.detect_modules()
    assert module in modules
    assert modules[module] is present
