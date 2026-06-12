"""Tests for _build_system_blocks — the prompt-cache segmentation helper in llm.py."""

from personas.insult.core.character import CACHE_BOUNDARY
from personas.insult.core.llm import _build_system_blocks


class TestBuildSystemBlocks:
    def test_no_boundary_returns_raw_string(self):
        """Simple prompts without the marker pass through unchanged."""
        result = _build_system_blocks("You are helpful.")
        assert result == "You are helpful."

    def test_boundary_produces_two_blocks(self):
        prompt = f"STABLE PERSONA{CACHE_BOUNDARY}DYNAMIC TIME: 12:34"
        result = _build_system_blocks(prompt)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["text"] == "STABLE PERSONA"
        assert result[0]["cache_control"] == {"type": "ephemeral"}
        assert result[1]["text"] == "DYNAMIC TIME: 12:34"
        assert "cache_control" not in result[1]

    def test_stable_only_still_caches(self):
        """If marker present but dynamic section empty, still produce one cached block."""
        prompt = f"PERSONA{CACHE_BOUNDARY}"
        result = _build_system_blocks(prompt)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["text"] == "PERSONA"
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    def test_empty_stable_falls_back_to_dynamic_string(self):
        prompt = f"{CACHE_BOUNDARY}only dynamic"
        result = _build_system_blocks(prompt)
        # No stable content → no cache block, return plain string
        assert result == "only dynamic"

    def test_multiple_boundaries_only_split_on_first(self):
        """If the marker accidentally appears twice, we split once and keep the rest dynamic."""
        prompt = f"STABLE{CACHE_BOUNDARY}DYN1{CACHE_BOUNDARY}DYN2"
        result = _build_system_blocks(prompt)
        assert isinstance(result, list)
        assert result[0]["text"] == "STABLE"
        assert CACHE_BOUNDARY in result[1]["text"]
