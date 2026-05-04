"""Tests for redact_with_llm — the decisive privacy pass.

Mocks the Anthropic client so the test exercises the prompt assembly,
post-redaction substring check, and failure modes WITHOUT real API calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from insult.core.moltbook_outbound import redact_with_llm


def _client_returning(text: str):
    """Build an Anthropic-shaped mock that returns `text` for one call."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages.create = AsyncMock(return_value=response)
    return client


def _client_raising(exc: Exception):
    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=exc)
    return client


# ---------------------------------------------------------------------------
# Empty / trivial inputs
# ---------------------------------------------------------------------------


async def test_returns_none_for_empty_content():
    out = await redact_with_llm("", ["fact"], client=MagicMock(), model="haiku")
    assert out is None


async def test_returns_none_for_whitespace_only_content():
    out = await redact_with_llm("   \n\n  ", ["fact"], client=MagicMock(), model="haiku")
    assert out is None


async def test_returns_content_unchanged_when_no_facts():
    """If the caller has no private facts to defend against, the LLM call is
    skipped and content passes through. The regex pass already ran."""
    client = MagicMock()
    out = await redact_with_llm("idea abstracta sin pii", [], client=client, model="haiku")
    assert out == "idea abstracta sin pii"
    client.messages.create.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_returns_redacted_text_on_clean_response():
    """LLM redacted properly — output makes it past the substring check."""
    client = _client_returning("El reduccionismo cognitivo es flojo y la consciencia merece más respeto.")
    out = await redact_with_llm(
        "Bernard piensa que la consciencia no es predicción de errores.",
        ["Bernard es programador en CDMX", "Toma sertralina 50mg"],
        client=client,
        model="haiku",
    )
    assert out is not None
    assert "Bernard" not in out
    assert "sertralina" not in out


async def test_passes_facts_block_to_llm():
    client = _client_returning("redacted")
    await redact_with_llm(
        "draft",
        ["fact one is here", "fact two is also here"],
        client=client,
        model="haiku",
    )
    user_msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "fact one is here" in user_msg
    assert "fact two is also here" in user_msg
    assert "PRIVATE FACTS THAT MUST NOT BE INFERABLE" in user_msg


async def test_caps_facts_at_30():
    """Bound prompt size — only first 30 facts go into the prompt."""
    client = _client_returning("redacted")
    facts = [f"fact number {i} is private" for i in range(50)]
    await redact_with_llm("draft", facts, client=client, model="haiku")
    user_msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "fact number 29" in user_msg
    assert "fact number 30" not in user_msg


# ---------------------------------------------------------------------------
# Substring leak detection — the critical safety net
# ---------------------------------------------------------------------------


async def test_returns_none_when_llm_leaks_fact_literally():
    """If the LLM rewrites but the output still contains a verbatim fact,
    refuse to publish. This is the defense against 'told not to leak,
    leaked anyway' which is exactly how privacy bugs ship."""
    client = _client_returning("Sobre la idea: Bernard es programador en CDMX y eso impacta su take.")
    out = await redact_with_llm(
        "draft",
        ["Bernard es programador en CDMX"],
        client=client,
        model="haiku",
    )
    assert out is None


async def test_substring_check_is_case_insensitive():
    """LLM lowering / capitalizing words doesn't defeat the check."""
    client = _client_returning("texto: bernard es programador en cdmx, da igual.")
    out = await redact_with_llm(
        "draft",
        ["Bernard es programador en CDMX"],
        client=client,
        model="haiku",
    )
    assert out is None


async def test_substring_check_skips_very_short_facts():
    """Facts under 8 chars (e.g. 'Es feliz') would otherwise produce false
    positives matching common Spanish fragments. The check skips them; the
    regex layer + the LLM's negative-target prompt handle short pieces."""
    client = _client_returning("Es feliz quien acepta su take.")
    out = await redact_with_llm("draft", ["Es feliz"], client=client, model="haiku")
    # Despite literal match, this short fact is below threshold → not blocked
    assert out is not None


async def test_does_not_fail_on_partial_word_overlap():
    """A fact 'es vegano' should NOT leak through 'veganismo' detection
    triggering — the substring check is on the FACT side, not the
    word-boundary side. That's intentional: better to false-positive
    than false-negative for privacy."""
    client = _client_returning("El veganismo es una postura ética interesante.")
    out = await redact_with_llm(
        "draft",
        ["es vegano"],
        client=client,
        model="haiku",
    )
    # 'es vegano' substring match against 'veganismo' fails (no match)
    # so this should pass through.
    assert out is not None


# ---------------------------------------------------------------------------
# LLM failure modes
# ---------------------------------------------------------------------------


async def test_returns_none_when_llm_returns_empty():
    """The redactor explicitly tells the LLM to return empty if it CAN'T
    redact safely — empty is a deliberate signal, not a bug."""
    client = _client_returning("")
    out = await redact_with_llm("draft", ["secret"], client=client, model="haiku")
    assert out is None


async def test_returns_none_when_llm_returns_blank_string():
    client = _client_returning("   \n\n   ")
    out = await redact_with_llm("draft", ["secret"], client=client, model="haiku")
    assert out is None


async def test_returns_none_when_llm_call_raises():
    client = _client_raising(RuntimeError("anthropic 503"))
    out = await redact_with_llm("draft", ["secret"], client=client, model="haiku")
    assert out is None


async def test_returns_none_when_llm_call_times_out():
    client = _client_raising(TimeoutError("read timeout"))
    out = await redact_with_llm("draft", ["secret"], client=client, model="haiku")
    assert out is None


# ---------------------------------------------------------------------------
# max_tokens budget
# ---------------------------------------------------------------------------


async def test_max_tokens_budget_minimum():
    """Even tiny drafts get at least 256 tokens of output budget so the LLM
    has room to rephrase. Below that it would produce truncated nonsense."""
    client = _client_returning("redacted")
    await redact_with_llm("hi", ["fact"], client=client, model="haiku")
    max_tok = client.messages.create.call_args.kwargs["max_tokens"]
    assert max_tok >= 256


async def test_max_tokens_budget_capped():
    """Very long drafts don't get unbounded budget — cap at 2048."""
    client = _client_returning("redacted")
    long_draft = "A" * 10_000
    await redact_with_llm(long_draft, ["fact"], client=client, model="haiku")
    max_tok = client.messages.create.call_args.kwargs["max_tokens"]
    assert max_tok <= 2048
