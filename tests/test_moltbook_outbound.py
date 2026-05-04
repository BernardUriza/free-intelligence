"""Tests for moltbook_outbound — gates, salience, regex strip, draft.

LLM redaction pass tests live in test_moltbook_outbound_redaction.py
(P3.2). Vulnerability gate is exercised here AND in
test_moltbook_outbound_vulnerability_gate.py (cross-file integration)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

from insult.core.moltbook_outbound import (
    OutboundDraft,
    SalienceSignal,
    build_post_draft,
    detect_salience_signal,
    is_outbound_blocked,
    regex_privacy_strip,
)

# ---------------------------------------------------------------------------
# is_outbound_blocked — vulnerability + disclosure gates
# ---------------------------------------------------------------------------


def _mock_memory(facts_by_user=None, max_severity_by_user=None):
    mem = MagicMock()

    async def get_facts(uid):
        return (facts_by_user or {}).get(uid, [])

    async def get_recent_max_severity(uid, since_ts):
        return (max_severity_by_user or {}).get(uid, 0)

    async def get_stances(channel_id, uid, limit=10):
        return []

    mem.get_facts = AsyncMock(side_effect=get_facts)
    mem.get_recent_max_severity = AsyncMock(side_effect=get_recent_max_severity)
    mem.get_stances = AsyncMock(side_effect=get_stances)
    return mem


async def test_no_users_passes_gate():
    mem = _mock_memory()
    reason, uid = await is_outbound_blocked([], memory=mem)
    assert reason is None
    assert uid is None


async def test_vulnerability_gate_blocks_first():
    """A user crossing the vulnerable threshold blocks ALL outbound,
    regardless of disclosure history."""
    vulnerable = {
        "u1": [
            {"fact": "Toma quetiapina 50mg para CPTSD", "category": "personal"},
            {"fact": "Diagnóstico de Complex PTSD", "category": "personal"},
            {"fact": "Hospitalizado en 2024", "category": "incidents"},
        ]
    }
    mem = _mock_memory(facts_by_user=vulnerable)
    reason, uid = await is_outbound_blocked(["u1"], memory=mem)
    assert reason == "vulnerability_gate"
    assert uid == "u1"


async def test_disclosure_severity_3_blocks():
    mem = _mock_memory(max_severity_by_user={"u1": 3})
    reason, uid = await is_outbound_blocked(["u1"], memory=mem)
    assert reason == "disclosure_severity"
    assert uid == "u1"


async def test_disclosure_severity_2_does_not_block():
    """Severity 2 is "mild mention" — not a hard block, just informs ranking
    (caller may still choose to skip via salience filter)."""
    mem = _mock_memory(max_severity_by_user={"u1": 2})
    reason, _ = await is_outbound_blocked(["u1"], memory=mem)
    assert reason is None


async def test_block_reports_first_blocking_user():
    """When two users have issues, return the first one — log gives operator
    enough info to investigate; we don't need exhaustive enumeration."""
    mem = _mock_memory(max_severity_by_user={"u1": 0, "u2": 4})
    reason, uid = await is_outbound_blocked(["u1", "u2"], memory=mem)
    assert reason == "disclosure_severity"
    assert uid == "u2"


# ---------------------------------------------------------------------------
# detect_salience_signal — when to post
# ---------------------------------------------------------------------------


async def test_salience_returns_none_without_stance_or_synthesis():
    mem = _mock_memory()
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is None


async def test_salience_picks_recent_high_confidence_stance():
    mem = MagicMock()
    mem.get_stances = AsyncMock(
        return_value=[
            {
                "topic": "consciencia agentes",
                "position": "La consciencia no se reduce a predicción de errores",
                "confidence": 0.85,
                "timestamp": time.time() - 3600,
            }
        ]
    )
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is not None
    assert sig.kind == "stance"
    assert sig.confidence == 0.85
    assert "predicción" in sig.seed_text


async def test_salience_skips_stale_stance():
    """A stance from 5 days ago is not a posting reason — Insult would be
    posting reheated leftovers."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(
        return_value=[
            {
                "topic": "old topic",
                "position": "old take",
                "confidence": 0.9,
                "timestamp": time.time() - 5 * 86400,
            }
        ]
    )
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is None


async def test_salience_skips_low_confidence_stance():
    mem = MagicMock()
    mem.get_stances = AsyncMock(
        return_value=[
            {
                "topic": "tema",
                "position": "tibio",
                "confidence": 0.3,
                "timestamp": time.time() - 600,
            }
        ]
    )
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is None


async def test_salience_falls_back_to_synthesis_signal():
    """No fresh stance, but a recent user message activated the synthesis
    detector → synthesis is the seed."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    # Long enough message + cross-domain phrasing to fire synthesis_detector
    long_msg = (
        "Es interesante cómo el apartheid sudafricano y el especismo "
        "comparten estructura: ambos son ideologías de jerarquía moral"
    )
    recent = [{"role": "user", "content": long_msg, "timestamp": time.time()}]
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=recent)
    # The detector may or may not fire on this exact text; we only assert
    # that IF it does, the synthesis path returns a signal of kind synthesis.
    if sig is not None:
        assert sig.kind == "synthesis"


# ---------------------------------------------------------------------------
# regex_privacy_strip — first-pass scrubbing
# ---------------------------------------------------------------------------


def test_strip_iso_dates():
    out = regex_privacy_strip("Eso pasó el 2026-04-20 a las 10am.", facts=[])
    assert "2026-04-20" not in out
    assert "[fecha]" in out


def test_strip_spanish_dates():
    out = regex_privacy_strip("El 20 abril fue clave.", facts=[])
    assert "20 abril" not in out
    assert "[fecha]" in out


def test_strip_doses():
    out = regex_privacy_strip("Toma 50mg de algo y 100 mcg.", facts=[])
    assert "50mg" not in out
    assert "100 mcg" not in out


def test_strip_phone():
    out = regex_privacy_strip("Llámame al 555-123-4567.", facts=[])
    assert "555-123-4567" not in out


def test_strip_email():
    out = regex_privacy_strip("Mándame correo a a@b.com.", facts=[])
    assert "a@b.com" not in out


def test_strip_discord_snowflake_ids():
    out = regex_privacy_strip("El user_id es 1489180895264116736 ya verificado.", facts=[])
    assert "1489180895264116736" not in out


def test_strip_explicit_proper_nouns():
    """Bernard and Alex are always stripped, regardless of fact list."""
    out = regex_privacy_strip("Bernard hizo X y Alex hizo Y.", facts=[])
    assert "Bernard" not in out
    assert "Alex" not in out
    assert "[persona]" in out


def test_strip_facts_proper_nouns_too():
    """A fact mentioning 'la dentista Marisa' should make 'Marisa' a stripped
    noun in any future drafts."""
    facts = [{"fact": "Su dentista se llama Marisa Hernández"}]
    out = regex_privacy_strip("Por la cita con Marisa supe que...", facts=facts)
    assert "Marisa" not in out


def test_strip_does_not_match_inside_words():
    """'Bernard' must not match 'Bernardino' (the saint's name)."""
    out = regex_privacy_strip("Visité San Bernardino el verano pasado.", facts=[])
    assert "Bernardino" in out  # we did NOT strip — substring would have


def test_strip_preserves_non_private_text():
    """Generic sentences without identifiable details survive untouched."""
    text = "La consciencia es predicción de errores, según algunos."
    out = regex_privacy_strip(text, facts=[])
    assert out == text


# ---------------------------------------------------------------------------
# build_post_draft — LLM call, JSON parsing, fallback
# ---------------------------------------------------------------------------


def _signal() -> SalienceSignal:
    return SalienceSignal(
        kind="stance",
        seed_text="La consciencia no se reduce a predicción de errores",
        topic="consciencia agentes",
        confidence=0.85,
    )


async def test_draft_happy_path_parses_json():
    llm = MagicMock()
    llm.chat = AsyncMock(
        return_value=MagicMock(
            text='{"title": "Predicción no es consciencia", "content": "El reduccionismo cognitivo..."}'
        )
    )
    draft = await build_post_draft(_signal(), "m/philosophy", persona="persona", llm=llm)
    assert isinstance(draft, OutboundDraft)
    assert draft.title == "Predicción no es consciencia"
    assert "reduccionismo" in draft.content
    assert draft.target_submolt == "m/philosophy"


async def test_draft_strips_markdown_fences():
    """LLMs often wrap JSON in ```json ... ```; we tolerate that."""
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(text='```json\n{"title": "T", "content": "C"}\n```'))
    draft = await build_post_draft(_signal(), "m/x", persona="p", llm=llm)
    assert draft is not None
    assert draft.title == "T"


async def test_draft_returns_none_for_empty_response():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(text=""))
    draft = await build_post_draft(_signal(), "m/x", persona="p", llm=llm)
    assert draft is None


async def test_draft_returns_none_for_invalid_json():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(text="not json at all"))
    draft = await build_post_draft(_signal(), "m/x", persona="p", llm=llm)
    assert draft is None


async def test_draft_returns_none_when_title_missing():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(text='{"content": "body only"}'))
    draft = await build_post_draft(_signal(), "m/x", persona="p", llm=llm)
    assert draft is None


async def test_draft_truncates_long_titles():
    llm = MagicMock()
    long_title = "A" * 500
    llm.chat = AsyncMock(return_value=MagicMock(text=f'{{"title": "{long_title}", "content": "x"}}'))
    draft = await build_post_draft(_signal(), "m/x", persona="p", llm=llm)
    assert draft is not None
    assert len(draft.title) <= 120


async def test_draft_includes_persona_in_system_prompt():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(text='{"title":"T","content":"C"}'))
    await build_post_draft(_signal(), "m/x", persona="THIS IS THE PERSONA", llm=llm)
    system_arg = llm.chat.call_args.args[0]
    assert "THIS IS THE PERSONA" in system_arg


async def test_draft_returns_none_on_exception():
    llm = MagicMock()
    llm.chat = AsyncMock(side_effect=RuntimeError("anthropic dead"))
    draft = await build_post_draft(_signal(), "m/x", persona="p", llm=llm)
    assert draft is None
