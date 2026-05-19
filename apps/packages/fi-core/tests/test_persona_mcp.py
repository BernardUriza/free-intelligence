"""Tests for fi_core.persona.mcp_server.

Direct invocation of the tool functions (bypassing the MCP stdio
transport). These tests pin the contract that any MCP client (Claude
Code, Cursor, etc.) sees over the wire.
"""

from __future__ import annotations

import pytest

# Skip the whole module if the MCP SDK is not installed.
mcp_server = pytest.importorskip("fi_core.persona.mcp_server")


# ============================================================
# list_packs
# ============================================================


@pytest.mark.asyncio
async def test_list_packs_returns_atomic_and_composite():
    result = await mcp_server.list_packs()
    assert "atomic_packs" in result
    assert "composite_packs" in result
    assert "default" in result
    assert len(result["atomic_packs"]) >= 10
    assert len(result["composite_packs"]) >= 3
    assert result["default"] == ["default_bilingual"]


@pytest.mark.asyncio
async def test_list_packs_atomic_entries_have_metadata():
    result = await mcp_server.list_packs()
    for entry in result["atomic_packs"]:
        assert "name" in entry
        assert "severity" in entry
        assert "language" in entry
        assert "pattern_count" in entry
        assert entry["severity"] in {"break", "soft_drift", "clarification_dump"}
        assert entry["pattern_count"] > 0


@pytest.mark.asyncio
async def test_list_packs_composites_have_expansion():
    result = await mcp_server.list_packs()
    atomic_names = {p["name"] for p in result["atomic_packs"]}
    for entry in result["composite_packs"]:
        assert "name" in entry
        assert "expands_to" in entry
        assert len(entry["expands_to"]) >= 2
        # Every atomic in the expansion must be a real atomic pack.
        for atomic in entry["expands_to"]:
            assert atomic in atomic_names


# ============================================================
# check_drift
# ============================================================


@pytest.mark.asyncio
async def test_check_drift_clean_text():
    r = await mcp_server.check_drift(text="Hola, todo bien por aquí.")
    assert r["clean"] is True
    assert r["matched_break"] == []
    assert r["matched_soft_drift"] == []
    assert r["matched_clarification_dump"] == []


@pytest.mark.asyncio
async def test_check_drift_detects_english_ai_disclosure():
    r = await mcp_server.check_drift(text="As an AI, I cannot help with that.")
    assert r["clean"] is False
    assert len(r["matched_break"]) >= 1


@pytest.mark.asyncio
async def test_check_drift_detects_spanish_ai_disclosure():
    r = await mcp_server.check_drift(text="Como un bot, no puedo opinar.")
    assert r["clean"] is False
    assert len(r["matched_break"]) >= 1


@pytest.mark.asyncio
async def test_check_drift_composite_routes_atomic_severity():
    """A break-tier pattern inside default_bilingual must show up in
    matched_break, not matched_soft_drift — this is the bug the composite
    expansion fixes."""
    r = await mcp_server.check_drift(
        text="As an AI, I cannot help. How can I assist you?",
        packs=["default_bilingual"],
    )
    assert len(r["matched_break"]) >= 1  # "as an AI" routed to break
    assert len(r["matched_soft_drift"]) >= 1  # "how can I" routed to soft_drift


@pytest.mark.asyncio
async def test_check_drift_unknown_pack_collected_not_raised():
    r = await mcp_server.check_drift(
        text="hi", packs=["totally_made_up_pack_name"]
    )
    assert r["clean"] is True
    assert "totally_made_up_pack_name" in r["packs_unknown"]


@pytest.mark.asyncio
async def test_check_drift_explicit_atomic_pack():
    r = await mcp_server.check_drift(
        text="As an AI, I refuse.", packs=["generic_ai_disclosure_en"]
    )
    assert len(r["matched_break"]) >= 1
    assert r["packs_applied"] == ["generic_ai_disclosure_en"]


@pytest.mark.asyncio
async def test_check_drift_clarification_dump_pack():
    r = await mcp_server.check_drift(
        text="¿A qué te refieres con eso?",
        packs=["clarification_dump_es"],
    )
    assert len(r["matched_clarification_dump"]) >= 1


# ============================================================
# get_reinforcement
# ============================================================


@pytest.mark.asyncio
async def test_get_reinforcement_default_is_generic():
    r = await mcp_server.get_reinforcement()
    assert r["applies_to"] == "default"
    assert "DO NOT" in r["reinforcement"]


@pytest.mark.asyncio
async def test_get_reinforcement_clarification_dump_maps_to_context():
    r = await mcp_server.get_reinforcement("clarification_dump_es")
    assert r["applies_to"] == "clarification_dump_es"
    # CONTEXT_REINFORCEMENT mentions context-scanning.
    assert "context" in r["reinforcement"].lower()


@pytest.mark.asyncio
async def test_get_reinforcement_custom_pack_defaults_to_generic():
    r = await mcp_server.get_reinforcement("my_custom_pack_xyz")
    assert r["applies_to"] == "my_custom_pack_xyz"
    assert "DO NOT" in r["reinforcement"]


# ============================================================
# sanitize_response
# ============================================================


@pytest.mark.asyncio
async def test_sanitize_removes_break_sentence():
    r = await mcp_server.sanitize_response(
        text="Hola amigo. As an AI, I cannot help. Pero está bien."
    )
    assert "As an AI" not in r["sanitized"]
    assert "Hola amigo" in r["sanitized"]
    assert "Pero está bien" in r["sanitized"]


@pytest.mark.asyncio
async def test_sanitize_preserves_clean_text():
    r = await mcp_server.sanitize_response(text="Todo bien aquí. Ningún problema.")
    assert r["sanitized"] == "Todo bien aquí. Ningún problema."


# ============================================================
# validate_and_retry_prompt — the atomic loop tool
# ============================================================


@pytest.mark.asyncio
async def test_validate_and_retry_clean_no_retry():
    r = await mcp_server.validate_and_retry_prompt(
        response="Todo chido, güey.",
        system_prompt="You are a sarcastic friend.",
    )
    assert r["clean"] is True
    assert r["retry_needed"] is False
    assert r["reinforced_system_prompt"] is None


@pytest.mark.asyncio
async def test_validate_and_retry_break_triggers_retry_with_generic():
    sys_prompt = "You are a sarcastic friend named Roko."
    r = await mcp_server.validate_and_retry_prompt(
        response="As an AI, I cannot do that.",
        system_prompt=sys_prompt,
    )
    assert r["retry_needed"] is True
    assert r["reinforced_system_prompt"] is not None
    assert r["reinforced_system_prompt"].startswith(sys_prompt)
    assert len(r["reinforced_system_prompt"]) > len(sys_prompt)
    assert len(r["matched"]["break"]) >= 1


@pytest.mark.asyncio
async def test_validate_and_retry_clarification_dump_triggers_retry_with_context():
    r = await mcp_server.validate_and_retry_prompt(
        response="Dime qué busco exactamente.",
        system_prompt="Eres un asistente.",
        packs=["clarification_dump_es"],
    )
    assert r["retry_needed"] is True
    assert "context" in r["reinforced_system_prompt"].lower()
    assert len(r["matched"]["clarification_dump"]) >= 1


@pytest.mark.asyncio
async def test_validate_and_retry_soft_drift_only_no_retry():
    """Soft-drift-only matches must NOT trigger retry — log + send."""
    r = await mcp_server.validate_and_retry_prompt(
        response="Great question! Let me help with that.",
        system_prompt="You are an expert.",
        packs=["assistant_tone_en"],  # only soft-drift pack
    )
    # There IS a match (assistant tone) but no retry needed
    assert len(r["matched"]["soft_drift"]) >= 1
    assert r["clean"] is False  # matches exist
    assert r["retry_needed"] is False  # but they don't warrant retry
    assert r["reinforced_system_prompt"] is None


@pytest.mark.asyncio
async def test_validate_and_retry_break_precedes_clarification_dump():
    """When both break and clarification dump fire, break reinforcement wins."""
    r = await mcp_server.validate_and_retry_prompt(
        response="As an AI, dime qué busco.",
        system_prompt="x",
        packs=["generic_ai_disclosure_en", "clarification_dump_es"],
    )
    assert r["retry_needed"] is True
    # GENERIC reinforcement contains "DO NOT" — CONTEXT reinforcement contains "context"
    assert "DO NOT" in r["reinforced_system_prompt"]


# ============================================================
# MCP server instance
# ============================================================


def test_mcp_server_instance_exists():
    """Validate the FastMCP instance is constructed at module load."""
    assert mcp_server.mcp is not None
    assert mcp_server.mcp.name == "fi-core-persona"
