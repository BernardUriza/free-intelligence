"""Tests for `shared.text` — Discord chunking + multi-message delimiter."""

from __future__ import annotations

import pytest

from shared.text import (
    DISCORD_MAX_CHARS,
    MESSAGE_DELIMITER,
    chunk_hard,
    chunk_paragraph_aware,
    split_response,
)

# ----- chunk_hard -----


def test_chunk_hard_returns_single_chunk_when_under_cap():
    assert chunk_hard("short", max_chars=50) == ["short"]


def test_chunk_hard_slices_at_exact_cap():
    text = "x" * 5000
    out = chunk_hard(text, max_chars=1990)
    assert len(out) == 3
    assert all(len(c) <= 1990 for c in out)
    assert "".join(out) == text  # lossless


def test_chunk_hard_does_not_strip_whitespace():
    """Insult's legacy callers depend on no semantic post-processing."""
    text = "  leading and trailing  " * 100
    out = chunk_hard(text, max_chars=100)
    assert "".join(out) == text


# ----- chunk_paragraph_aware -----


def test_chunk_paragraph_aware_short_returns_single_chunk():
    out = chunk_paragraph_aware("hola", max_chars=1900)
    assert out == ["hola"]


def test_chunk_paragraph_aware_breaks_on_double_newline():
    text = ("a" * 500) + "\n\n" + ("b" * 500)
    out = chunk_paragraph_aware(text, max_chars=600)
    assert len(out) == 2
    assert all(len(c) <= 600 for c in out)


def test_chunk_paragraph_aware_breaks_on_single_newline_when_no_double_exists():
    text = ("a" * 500) + "\n" + ("b" * 500)
    out = chunk_paragraph_aware(text, max_chars=600)
    assert len(out) >= 2


def test_chunk_paragraph_aware_hard_falls_back_when_no_break_exists():
    text = "x" * 5000
    out = chunk_paragraph_aware(text, max_chars=1900)
    assert len(out) == 3
    assert all(len(c) <= 1900 for c in out)


# ----- DISCORD_MAX_CHARS -----


def test_discord_max_chars_below_hard_2000_cap():
    """Discord rejects > 2000 chars. We must leave room for version tags."""
    assert DISCORD_MAX_CHARS < 2000


# ----- split_response / MESSAGE_DELIMITER -----


def test_split_response_returns_single_part_when_no_delimiter():
    assert split_response("hola mundo") == ["hola mundo"]


def test_split_response_splits_on_delimiter():
    text = f"primero{MESSAGE_DELIMITER}segundo{MESSAGE_DELIMITER}tercero"
    assert split_response(text) == ["primero", "segundo", "tercero"]


def test_split_response_strips_empty_parts():
    text = f"primero{MESSAGE_DELIMITER}{MESSAGE_DELIMITER}segundo"
    assert split_response(text) == ["primero", "segundo"]


def test_split_response_strips_whitespace_around_parts():
    text = f"  primero  {MESSAGE_DELIMITER}  segundo  "
    assert split_response(text) == ["primero", "segundo"]


# ----- backward compat through insult.core.delivery -----


def test_insult_delivery_reexports_match_shared():
    """Insult's re-exports must stay identical so callers keep working."""
    from insult.core import delivery as insult_delivery

    assert insult_delivery.DISCORD_MAX_CHARS == DISCORD_MAX_CHARS
    assert insult_delivery.MESSAGE_DELIMITER == MESSAGE_DELIMITER
    assert insult_delivery.chunk_text is chunk_hard
    assert insult_delivery.split_response is split_response


# Parametric: every chunk strategy must respect the cap.
@pytest.mark.parametrize("fn", [chunk_hard, chunk_paragraph_aware])
@pytest.mark.parametrize("size,cap", [(50, 100), (5000, 1900), (1900, 1900)])
def test_chunk_always_respects_cap(fn, size, cap):
    text = "x" * size
    out = fn(text, max_chars=cap)
    assert all(len(c) <= cap for c in out)
