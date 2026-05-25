"""Tests for capability → MCP-server-spec resolution.

This is the framework's headline feature: declare ``capabilities=["persona"]``
and get the fi-core MCP server wired automatically. The env_passthrough
forwarding is what lets a real consumer (insult) adopt it without changing
behavior.
"""

from __future__ import annotations

import sys

import pytest

from fi_runner import capabilities


def test_resolve_persona_points_at_fi_core_server():
    (spec,) = capabilities.resolve(["persona"])
    assert spec.name == "fi-core-persona"
    assert spec.command == sys.executable
    assert spec.args == ["-m", "fi_core.persona.mcp_server"]


def test_resolve_persona_reads_real_tools_from_contract():
    # fi_core is installed in this env, so the zero-dep contract supplies tools.
    (spec,) = capabilities.resolve(["persona"])
    assert "sanitize_response" in spec.tools  # a known persona tool
    assert "check_drift" in spec.tools


def test_resolve_defaults_env_passthrough_true():
    (spec,) = capabilities.resolve(["persona"])
    assert spec.env_passthrough is True


def test_resolve_forwards_env_passthrough_false():
    # insult drives the stdio server in its own pool and wants env_passthrough=False.
    (spec,) = capabilities.resolve(["persona"], env_passthrough=False)
    assert spec.env_passthrough is False


def test_resolve_cognitive_points_at_cognitive_server():
    (spec,) = capabilities.resolve(["cognitive"])
    assert spec.name == "fi-core-cognitive"
    assert spec.args == ["-m", "fi_core.cognitive.mcp_server"]
    assert "classify_urgency" in spec.tools


def test_resolve_multiple_capabilities_preserves_order():
    specs = capabilities.resolve(["cognitive", "persona"])
    assert [s.name for s in specs] == ["fi-core-cognitive", "fi-core-persona"]


def test_resolve_unknown_capability_raises():
    with pytest.raises(KeyError, match="unknown capability"):
        capabilities.resolve(["nonexistent"])
