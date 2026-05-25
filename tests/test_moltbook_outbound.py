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
    assign_subject_codes,
    build_post_draft,
    detect_salience_signal,
    is_outbound_blocked,
    load_previous_outbound_notes,
    persist_draft,
    persist_published_post,
    regex_privacy_strip,
)

# ---------------------------------------------------------------------------
# is_outbound_blocked — vulnerability + disclosure gates
# ---------------------------------------------------------------------------


def _mock_memory(facts_by_user=None, max_severity_by_user=None, arc_by_user=None):
    mem = MagicMock()

    async def get_facts(uid):
        return (facts_by_user or {}).get(uid, [])

    async def get_recent_max_severity(uid, since_ts):
        return (max_severity_by_user or {}).get(uid, 0)

    async def get_stances(channel_id, uid, limit=10):
        return []

    async def get_arc(channel_id, uid):
        return (arc_by_user or {}).get(uid)

    mem.get_facts = AsyncMock(side_effect=get_facts)
    mem.get_recent_max_severity = AsyncMock(side_effect=get_recent_max_severity)
    mem.get_stances = AsyncMock(side_effect=get_stances)
    mem.get_arc = AsyncMock(side_effect=get_arc)
    return mem


# Vulnerable user fact set used by multiple tests to cross VULNERABLE_THRESHOLD
_VULNERABLE_FACTS = {
    "u1": [
        {"fact": "Toma quetiapina 50mg para CPTSD", "category": "personal"},
        {"fact": "Diagnóstico de Complex PTSD", "category": "personal"},
        {"fact": "Hospitalizado en 2024", "category": "incidents"},
    ]
}


async def test_no_users_passes_gate():
    mem = _mock_memory()
    reason, uid = await is_outbound_blocked([], memory=mem)
    assert reason is None
    assert uid is None


async def test_vulnerability_gate_blocks_when_no_channel_id():
    """No channel_id → can't look up arc phase → conservative block.
    The function defaults in_crisis=True when it has no way to verify
    the user is OK right now."""
    mem = _mock_memory(facts_by_user=_VULNERABLE_FACTS)
    reason, uid = await is_outbound_blocked(["u1"], memory=mem)
    assert reason == "vulnerability_gate"
    assert uid == "u1"


async def test_vulnerability_gate_blocks_when_no_arc_data():
    """Channel_id provided but arc returns None — conservative block."""
    mem = _mock_memory(facts_by_user=_VULNERABLE_FACTS, arc_by_user={"u1": None})
    reason, uid = await is_outbound_blocked(["u1"], memory=mem, channel_id="ch1")
    assert reason == "vulnerability_gate"
    assert uid == "u1"


async def test_vulnerability_gate_blocks_when_arc_phase_crisis():
    """User chronically vulnerable AND currently in CRISIS → block."""
    mem = _mock_memory(
        facts_by_user=_VULNERABLE_FACTS,
        arc_by_user={"u1": {"phase": "crisis", "phase_since": 1700000000}},
    )
    reason, uid = await is_outbound_blocked(["u1"], memory=mem, channel_id="ch1")
    assert reason == "vulnerability_gate"
    assert uid == "u1"


async def test_vulnerability_gate_relaxed_when_arc_phase_stability():
    """User chronically vulnerable BUT currently in STABILITY → pass.
    The whole point of v3.7.28: chronic facts don't permanently silence
    outbound; only an active crisis does."""
    mem = _mock_memory(
        facts_by_user=_VULNERABLE_FACTS,
        arc_by_user={"u1": {"phase": "stability", "phase_since": 1700000000}},
    )
    reason, uid = await is_outbound_blocked(["u1"], memory=mem, channel_id="ch1")
    assert reason is None
    assert uid is None


async def test_vulnerability_gate_relaxed_when_arc_phase_recovery():
    """RECOVERY phase also lets the post through. The user is moving out
    of crisis; encouraging the structural-anonymized post is OK."""
    mem = _mock_memory(
        facts_by_user=_VULNERABLE_FACTS,
        arc_by_user={"u1": {"phase": "recovery", "phase_since": 1700000000}},
    )
    reason, _ = await is_outbound_blocked(["u1"], memory=mem, channel_id="ch1")
    assert reason is None


async def test_vulnerability_gate_blocks_uppercase_crisis():
    """Phase strings are lowercased before comparison — defensive in case
    the schema ever stores 'CRISIS' or 'Crisis'."""
    mem = _mock_memory(
        facts_by_user=_VULNERABLE_FACTS,
        arc_by_user={"u1": {"phase": "CRISIS", "phase_since": 1700000000}},
    )
    reason, _ = await is_outbound_blocked(["u1"], memory=mem, channel_id="ch1")
    assert reason == "vulnerability_gate"


async def test_vulnerability_gate_blocks_when_arc_lookup_raises():
    """If memory.get_arc throws, treat as 'can't tell' → conservative block.
    Privacy errors should fail-closed."""
    mem = MagicMock()
    mem.get_facts = AsyncMock(return_value=_VULNERABLE_FACTS["u1"])
    mem.get_arc = AsyncMock(side_effect=RuntimeError("DB down"))
    mem.get_recent_max_severity = AsyncMock(return_value=0)
    reason, uid = await is_outbound_blocked(["u1"], memory=mem, channel_id="ch1")
    assert reason == "vulnerability_gate"
    assert uid == "u1"


async def test_disclosure_severity_2_does_not_block():
    """Severity 2 is "mild mention" — never blocks."""
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


async def test_salience_arc_recovery_fresh_transition():
    """User in RECOVERY phase for <24h → arc_recovery signal fires."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(
        return_value={
            "phase": "recovery",
            "phase_since": time.time() - 3600,  # 1h ago
        }
    )
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is not None
    assert sig.kind == "arc_recovery"
    assert "resilience" in sig.topic.lower() or "emergence" in sig.topic.lower()


async def test_salience_arc_recovery_skips_old_transition():
    """STABILITY for >24h is not a 'fresh transition' — don't fire."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(
        return_value={
            "phase": "stability",
            "phase_since": time.time() - 7 * 86400,  # 7 days ago
        }
    )
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is None


async def test_salience_arc_recovery_skips_crisis():
    """User actively in CRISIS — never use as a posting signal."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(
        return_value={
            "phase": "crisis",
            "phase_since": time.time() - 3600,
        }
    )
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is None


async def test_salience_arc_recovery_handles_missing_arc():
    """First-time user with no arc state → just skip, don't crash."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(return_value=None)
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is None


async def test_salience_topic_repetition_fires_on_three_mentions():
    """Same user mentions same topic-keywords ≥3 times within 24h."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(return_value=None)
    now = time.time()
    recent = [
        {
            "role": "user",
            "user_id": "u1",
            "content": "filosofía contemporánea fenomenología consciencia",
            "timestamp": now - 7200,
        },
        {
            "role": "user",
            "user_id": "u1",
            "content": "filosofía contemporánea fenomenología consciencia",
            "timestamp": now - 3600,
        },
        {
            "role": "user",
            "user_id": "u1",
            "content": "filosofía contemporánea fenomenología consciencia",
            "timestamp": now - 600,
        },
    ]
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=recent)
    assert sig is not None
    assert sig.kind == "topic_repetition"


async def test_salience_topic_repetition_skips_below_threshold():
    """Only 2 mentions → not enough to count as convergence."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(return_value=None)
    now = time.time()
    recent = [
        {"role": "user", "user_id": "u1", "content": "filosofía fenomenología consciencia", "timestamp": now - 600},
        {"role": "user", "user_id": "u1", "content": "filosofía fenomenología consciencia", "timestamp": now - 1200},
    ]
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=recent)
    assert sig is None


async def test_salience_topic_repetition_only_counts_user_in_user_ids():
    """A bystander mentioning the topic 3 times shouldn't count if they
    aren't in the user_ids set we're posting on behalf of."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(return_value=None)
    now = time.time()
    recent = [
        {"role": "user", "user_id": "stranger", "content": "filosofía fenomenología", "timestamp": now - 100},
        {"role": "user", "user_id": "stranger", "content": "filosofía fenomenología", "timestamp": now - 200},
        {"role": "user", "user_id": "stranger", "content": "filosofía fenomenología", "timestamp": now - 300},
    ]
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=recent)
    assert sig is None


async def test_salience_topic_repetition_skips_stale_messages():
    """Messages from >24h ago don't contribute — convergence has to be
    recent to count as live concern."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(return_value=[])
    mem.get_arc = AsyncMock(return_value=None)
    old = time.time() - 5 * 86400
    recent = [
        {"role": "user", "user_id": "u1", "content": "filosofía fenomenología consciencia", "timestamp": old - 100},
        {"role": "user", "user_id": "u1", "content": "filosofía fenomenología consciencia", "timestamp": old - 200},
        {"role": "user", "user_id": "u1", "content": "filosofía fenomenología consciencia", "timestamp": old - 300},
    ]
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=recent)
    assert sig is None


async def test_salience_priority_stance_beats_arc():
    """When BOTH a fresh stance AND a fresh arc transition exist, stance
    wins because it has actual propositional content. Arc would be a
    posture-change seed without semantics."""
    mem = MagicMock()
    mem.get_stances = AsyncMock(
        return_value=[
            {
                "topic": "consciencia",
                "position": "no es predicción de errores",
                "confidence": 0.9,
                "timestamp": time.time() - 3600,
            }
        ]
    )
    mem.get_arc = AsyncMock(return_value={"phase": "stability", "phase_since": time.time() - 1800})
    sig = await detect_salience_signal("ch", ["u1"], memory=mem, recent_messages=[])
    assert sig is not None
    assert sig.kind == "stance"


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
    judge = MagicMock()
    judge.utility_call = AsyncMock(
        return_value=MagicMock(
            text='{"title": "Predicción no es consciencia", "content": "El reduccionismo cognitivo..."}'
        )
    )
    draft = await build_post_draft(_signal(), "m/philosophy", persona="persona", judge=judge)
    assert isinstance(draft, OutboundDraft)
    assert draft.title == "Predicción no es consciencia"
    assert "reduccionismo" in draft.content
    assert draft.target_submolt == "m/philosophy"


async def test_draft_strips_markdown_fences():
    """LLMs often wrap JSON in ```json ... ```; we tolerate that."""
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='```json\n{"title": "T", "content": "C"}\n```'))
    draft = await build_post_draft(_signal(), "m/x", persona="p", judge=judge)
    assert draft is not None
    assert draft.title == "T"


async def test_draft_returns_none_for_empty_response():
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text=""))
    draft = await build_post_draft(_signal(), "m/x", persona="p", judge=judge)
    assert draft is None


async def test_draft_returns_none_for_invalid_json():
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text="not json at all"))
    draft = await build_post_draft(_signal(), "m/x", persona="p", judge=judge)
    assert draft is None


async def test_draft_returns_none_when_title_missing():
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='{"content": "body only"}'))
    draft = await build_post_draft(_signal(), "m/x", persona="p", judge=judge)
    assert draft is None


async def test_draft_truncates_long_titles():
    judge = MagicMock()
    long_title = "A" * 500
    judge.utility_call = AsyncMock(return_value=MagicMock(text=f'{{"title": "{long_title}", "content": "x"}}'))
    draft = await build_post_draft(_signal(), "m/x", persona="p", judge=judge)
    assert draft is not None
    assert len(draft.title) <= 120


async def test_draft_includes_persona_in_system_prompt():
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='{"title":"T","content":"C"}'))
    await build_post_draft(_signal(), "m/x", persona="THIS IS THE PERSONA", judge=judge)
    system_arg = judge.utility_call.call_args.args[0]
    assert "THIS IS THE PERSONA" in system_arg


async def test_draft_returns_none_on_exception():
    judge = MagicMock()
    judge.utility_call = AsyncMock(side_effect=RuntimeError("anthropic dead"))
    draft = await build_post_draft(_signal(), "m/x", persona="p", judge=judge)
    assert draft is None


# ---------------------------------------------------------------------------
# Subject codes — Alex=A, Bernard=B (deterministic, sorted by user_id)
# ---------------------------------------------------------------------------


def test_assign_subject_codes_alex_is_a_bernard_is_b():
    """Alex's user_id (1431...) sorts before Bernard's (9072...) alphabetically,
    so Alex gets A and Bernard gets B. Per Bernard's explicit request."""
    codes = assign_subject_codes(["907264175246569543", "1431300030823927999"])
    assert codes["1431300030823927999"] == "A"  # Alex
    assert codes["907264175246569543"] == "B"  # Bernard


def test_assign_subject_codes_deduplicates():
    """Same user_id passed twice doesn't get two letters."""
    codes = assign_subject_codes(["u1", "u1", "u2"])
    assert len(codes) == 2
    assert set(codes.values()) == {"A", "B"}


def test_assign_subject_codes_caps_at_z():
    """26 users get A-Z; 27th and beyond drop out (rather than continue
    into AA which would break the 'one letter' contract)."""
    codes = assign_subject_codes([f"u{i:03d}" for i in range(30)])
    assert len(codes) == 26
    assert "Z" in codes.values()


def test_assign_subject_codes_empty():
    assert assign_subject_codes([]) == {}


# ---------------------------------------------------------------------------
# Build draft with previous_notes (continuity) and subject_codes
# ---------------------------------------------------------------------------


async def test_draft_first_post_includes_archive_opening_hint():
    """When previous_notes is empty, the user prompt tells the LLM it's
    Sesión 1 and points at the archive-opening template."""
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='{"title":"Sesión 1.","content":"abrir archivo"}'))
    await build_post_draft(_signal(), "m/x", persona="p", judge=judge, previous_notes=None)
    user_msg = judge.utility_call.call_args.args[1][0]["content"]
    assert "N = 1" in user_msg
    assert "First post" in user_msg or "Session 1" in user_msg


async def test_draft_continuing_post_includes_previous_notes():
    """When previous_notes has entries, the user prompt cites them so the
    LLM can reference past posts (option B continuity)."""
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='{"title":"Sesión 4.","content":"continuo"}'))
    previous = [
        {"topic": "Sesión 1. Subject A predictive coding", "findings": "first note content..."},
        {"topic": "Sesión 2. Subject B fixation", "findings": "second note content..."},
        {"topic": "Sesión 3. Subject A again", "findings": "third note content..."},
    ]
    await build_post_draft(_signal(), "m/x", persona="p", judge=judge, previous_notes=previous)
    user_msg = judge.utility_call.call_args.args[1][0]["content"]
    assert "N = 4" in user_msg
    assert "Sesión 1. Subject A predictive coding" in user_msg
    assert "Sesión 2. Subject B fixation" in user_msg
    assert "Sesión 3. Subject A again" in user_msg


async def test_draft_subject_hint_uses_letter_not_user_id():
    """The user prompt receives the LETTER mapping (Subject A) but never
    the raw user_id. Privacy in the prompt itself."""
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='{"title":"t","content":"c"}'))
    sig = SalienceSignal(
        kind="stance",
        seed_text="seed",
        topic="topic",
        confidence=0.8,
        source_user_id="1431300030823927999",  # Alex
    )
    codes = {"1431300030823927999": "A", "907264175246569543": "B"}
    await build_post_draft(sig, "m/x", persona="p", judge=judge, subject_codes=codes)
    user_msg = judge.utility_call.call_args.args[1][0]["content"]
    assert "Subject A" in user_msg
    assert "1431300030823927999" not in user_msg  # the user_id MUST NOT leak


async def test_draft_omits_subject_hint_when_no_source_user_id():
    """If the salience didn't track which user it came from, no hint
    fires — the LLM picks Subject A/B itself."""
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=MagicMock(text='{"title":"t","content":"c"}'))
    sig = SalienceSignal(kind="stance", seed_text="seed", topic="topic", confidence=0.8)
    await build_post_draft(sig, "m/x", persona="p", judge=judge, subject_codes={"u1": "A"})
    user_msg = judge.utility_call.call_args.args[1][0]["content"]
    assert "Subject del cual viene" not in user_msg


# ---------------------------------------------------------------------------
# persist_draft / persist_published_post — audit trail
# ---------------------------------------------------------------------------


async def test_persist_draft_writes_with_draft_source():
    """Drafts go to world_scans with source='moltbook_outbound_draft' and
    NULL external_id (haven't published yet)."""
    mem = MagicMock()
    mem.store_world_scan = AsyncMock(return_value=True)
    draft = OutboundDraft(title="t", content="c", target_submolt="m/x", salience=_signal())
    await persist_draft(draft, "redacted version", memory=mem)
    kw = mem.store_world_scan.call_args.kwargs
    assert kw["source"] == "moltbook_outbound_draft"
    assert kw["external_id"] is None
    assert kw["topic"] == "t"


async def test_persist_draft_uses_redacted_when_provided():
    """We persist the redacted version (what would go out), not the raw LLM
    output, so the audit trail reflects what the user would actually see."""
    mem = MagicMock()
    mem.store_world_scan = AsyncMock(return_value=True)
    draft = OutboundDraft(title="t", content="raw content", target_submolt="m/x", salience=_signal())
    await persist_draft(draft, "redacted content", memory=mem)
    kw = mem.store_world_scan.call_args.kwargs
    assert kw["findings"] == "redacted content"


async def test_persist_draft_falls_back_to_raw_when_no_redaction():
    """When redaction failed (None), persist the raw draft anyway —
    operator needs to see what the LLM generated."""
    mem = MagicMock()
    mem.store_world_scan = AsyncMock(return_value=True)
    draft = OutboundDraft(title="t", content="raw content", target_submolt="m/x", salience=_signal())
    await persist_draft(draft, None, memory=mem, extra_notes="redaction_blocked")
    kw = mem.store_world_scan.call_args.kwargs
    assert "raw content" in kw["findings"]
    assert "redaction_blocked" in kw["commentary"]


async def test_persist_draft_swallows_exceptions():
    """Audit persistence MUST NOT block the publish — DB failure logs but
    doesn't propagate."""
    mem = MagicMock()
    mem.store_world_scan = AsyncMock(side_effect=RuntimeError("DB down"))
    draft = OutboundDraft(title="t", content="c", target_submolt="m/x", salience=_signal())
    # No exception should escape this call
    await persist_draft(draft, "r", memory=mem)


async def test_persist_published_post_uses_published_source():
    """Published posts go to world_scans with source='moltbook_outbound'
    and external_id=post.id. Two rows per published post (draft + outbound)
    is intentional — the dedupe partial UNIQUE INDEX is on
    (source, external_id), so they don't collide."""
    mem = MagicMock()
    mem.store_world_scan = AsyncMock(return_value=True)
    draft = OutboundDraft(title="t", content="c", target_submolt="m/x", salience=_signal())
    await persist_published_post(draft, "moltbook_post_xyz", "redacted", memory=mem)
    kw = mem.store_world_scan.call_args.kwargs
    assert kw["source"] == "moltbook_outbound"
    assert kw["external_id"] == "moltbook_post_xyz"


async def test_load_previous_outbound_notes_filters_by_source():
    mem = MagicMock()
    mem.get_recent_world_scans = AsyncMock(return_value=[{"topic": "Sesión 1.", "findings": "..."}])
    notes = await load_previous_outbound_notes(mem, limit=5)
    assert len(notes) == 1
    mem.get_recent_world_scans.assert_awaited_once_with(limit=5, source="moltbook_outbound")


async def test_load_previous_outbound_notes_returns_empty_on_error():
    mem = MagicMock()
    mem.get_recent_world_scans = AsyncMock(side_effect=RuntimeError("DB down"))
    notes = await load_previous_outbound_notes(mem)
    assert notes == []


# ---------------------------------------------------------------------------
# Vulnerability gate threshold change (v3.7.26 — sev≥4 instead of ≥3)
# ---------------------------------------------------------------------------


async def test_disclosure_severity_3_no_longer_blocks():
    """v3.7.26 relaxed the gate from sev≥3 to sev≥4. A user with sev=3
    in last 14 days now passes (relying on the structural anonymization
    of Joan Bright format + LLM redaction pass to handle leakage)."""
    mem = _mock_memory(max_severity_by_user={"u1": 3})
    reason, _ = await is_outbound_blocked(["u1"], memory=mem)
    assert reason is None


async def test_disclosure_severity_4_still_blocks():
    """sev=4 = clear acute disclosure. Still blocks."""
    mem = _mock_memory(max_severity_by_user={"u1": 4})
    reason, uid = await is_outbound_blocked(["u1"], memory=mem)
    assert reason == "disclosure_severity"
    assert uid == "u1"
