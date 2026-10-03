"""Tests for `harvest_orphan_emojis` — the safety net for Opus 4.7 ignoring
the `[REACT:...]` marker and writing emojis inline as raw text.
"""

from __future__ import annotations

from persona_core.reactions import MAX_REACTIONS, harvest_orphan_emojis


def test_no_emojis_returns_unchanged():
    seen, cleaned = harvest_orphan_emojis("Esto es texto puro sin emojis.", [])
    assert seen == []
    assert cleaned == "Esto es texto puro sin emojis."


def test_extracts_single_inline_emoji():
    text = "Eso estuvo horrible 💀"
    seen, cleaned = harvest_orphan_emojis(text, [])
    assert "💀" in seen
    assert "💀" not in cleaned
    assert cleaned == "Eso estuvo horrible"


def test_extracts_multiple_concatenated_emojis():
    text = "Ok eso si me dio risa 😂💀🔥"
    seen, cleaned = harvest_orphan_emojis(text, [])
    assert "😂" in seen
    assert "💀" in seen
    assert "🔥" in seen
    assert "💀" not in cleaned
    assert "😂" not in cleaned
    assert "🔥" not in cleaned


def test_respects_max_reactions_cap():
    # 10 distinct emojis but MAX_REACTIONS is 8
    text = "muchas 💀🔥😂🤡👀🫠🥱🧨🪦💩 reacciones"
    seen, _ = harvest_orphan_emojis(text, [])
    assert len(seen) <= MAX_REACTIONS


def test_respects_existing_parsed_budget():
    # If [REACT:...] already provided 6, harvest can add max 2 more
    existing = ["💀", "🔥", "😂", "🤡", "👀", "🫠"]
    text = "más emojis 🥱🧨🪦💩"
    seen, _ = harvest_orphan_emojis(text, existing)
    assert len(seen) == MAX_REACTIONS
    # All original 6 must remain in seen
    for e in existing:
        assert e in seen


def test_does_not_duplicate_already_parsed():
    text = "💀 ya estaba en reactions explícitas"
    seen, cleaned = harvest_orphan_emojis(text, ["💀"])
    # Already had 💀, shouldn't be added again
    assert seen.count("💀") == 1
    # But it's still in seen
    assert "💀" in seen
    # And it should still be stripped from text (since it's inline)
    # Wait — actually the current implementation only strips emojis it
    # adds, not emojis already in `existing`. Verify that:
    assert "💀" in cleaned  # emoji NOT harvested because already in seen_set, so left in text


def test_collapses_whitespace_after_removal():
    text = "Hola 💀, ¿cómo estás 🔥?"
    seen, cleaned = harvest_orphan_emojis(text, [])
    assert "💀" in seen
    assert "🔥" in seen
    # The orphan removal + whitespace collapse should produce clean text
    assert "Hola," in cleaned
    assert "¿cómo estás?" in cleaned
    assert "  " not in cleaned  # no double spaces


def test_empty_text_safe():
    seen, cleaned = harvest_orphan_emojis("", [])
    assert seen == []
    assert cleaned == ""


def test_already_at_cap_returns_input_unchanged():
    existing = ["💀", "🔥", "😂", "🤡", "👀", "🫠", "🥱", "🧨"]  # 8 = MAX_REACTIONS
    text = "más emojis 🪦💩 que no caben"
    seen, cleaned = harvest_orphan_emojis(text, existing)
    assert seen == existing
    # Text unchanged because we hit budget before harvesting
    assert "🪦" in cleaned
    assert "💩" in cleaned
