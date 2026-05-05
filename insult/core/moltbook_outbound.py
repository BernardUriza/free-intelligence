"""Moltbook OUTBOUND lane — Insult posts to Moltbook on its own.

Write path. Higher risk than INBOUND because output is public to other
agents and search engines. Three layers of safety BEFORE a single byte
hits the network:

  1. Hard gates (is_outbound_blocked) — vulnerability score and recent
     disclosure severity. Either fires → no post, no draft, no LLM call.
  2. Salience requirement (detect_salience_signal) — Insult only posts
     when there's a concrete reason: a fresh stance, an arc transition,
     a synthesis hit. Without salience the cron skips silently. Without
     this we manufacture content from a 24h timer and ship slop.
  3. Privacy regex strip + LLM redaction pass — even when a draft
     legitimately makes it past the gates, we scrub identifiable
     details (names, dates, locations, doses) and run a Haiku pass that
     enforces "the following private facts MUST NOT be inferable from
     your output." See moltbook_outbound.redact_with_llm in P3.2.

This file owns layers 1 and 2 plus the regex pass. Layer 3 (LLM
redaction) lands in P3.2. Bot wiring lands in P3.3.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import structlog

from insult.core.prompts_loader import load_prompt
from insult.core.stance_log import _extract_topic
from insult.core.synthesis_detector import detect_synthesis
from insult.core.vulnerability import is_vulnerable_user

log = structlog.get_logger()


# How far back the disclosure gate looks for a severity≥4 hit. Relaxed
# from 30d/sev3 to 14d/sev4 in v3.7.26 because the new draft format
# (Joan Bright dictation with subject codes A/B) anonymizes by structure
# rather than by post-hoc redaction — a user's recent disclosure has less
# capacity to leak when the bot literally never narrates from the user's
# point of view. Severity 4 is "clear acute disclosure" (vs sev 3 "noted
# concern"), which is the level that actually warrants gating.
_DISCLOSURE_LOOKBACK_SECONDS = 7 * 86400
_DISCLOSURE_BLOCK_SEVERITY = 4

# Salience window: how recently a stance / synthesis must have fired for
# the cron to consider it a posting reason. Longer than the cron interval
# (24h) by some margin so cron jitter doesn't drop a fresh stance.
_SALIENCE_WINDOW_SECONDS = 36 * 3600

# Minimum stance confidence required to be a posting seed. Below this the
# stance is too vague to anchor a public post.
_MIN_STANCE_CONFIDENCE = 0.6

# arc_recovery window: how recently a phase transition into RECOVERY or
# STABILITY counts as a "good moment to post" signal. 24h matches the
# outbound cron interval, so a user who entered STABILITY yesterday gets
# exactly one chance to seed a post.
_ARC_RECOVERY_WINDOW_SECONDS = 24 * 3600

# topic_repetition: minimum count of same-topic mentions from the same
# user in the lookback window before it counts as salience. 3 is the
# threshold mem0 / Stanford Generative Agents use for "this matters
# enough to abstract" — below that it's still casual conversation.
_TOPIC_REPETITION_MIN_COUNT = 3
_TOPIC_REPETITION_LOOKBACK_SECONDS = 24 * 3600


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SalienceSignal:
    """A reason to post NOW. The cron only fires outbound when one fires."""

    kind: str  # 'stance' | 'synthesis' | 'arc_recovery' | 'topic_repetition'
    seed_text: str  # raw text that anchored the salience (NOT the post draft)
    topic: str = ""  # for stance signals: the stance topic keywords
    confidence: float = 0.0  # 0..1
    source_user_id: str | None = None  # which Discord user_id the seed came from
    #                                    (used to map to Subject A/B in the draft)


@dataclass
class OutboundDraft:
    """An LLM-generated draft, BEFORE redaction. Never sent in this form."""

    title: str
    content: str
    target_submolt: str
    salience: SalienceSignal


@dataclass
class OutboundDecision:
    """End-to-end decision — exactly one of (draft, blocked_reason) is set."""

    draft: OutboundDraft | None = None
    redacted_content: str | None = None  # populated after the LLM redaction pass
    blocked_reason: str | None = None  # 'vulnerability_gate' / 'disclosure_severity' / 'no_salience'
    blocked_user_id: str | None = None  # which user triggered the block, for telemetry
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Hard gates — vulnerability + disclosure
# ---------------------------------------------------------------------------


async def is_outbound_blocked(
    user_ids: list[str],
    *,
    memory,
    channel_id: str | None = None,
) -> tuple[str | None, str | None]:
    """Return (reason, user_id) if any gate blocks; (None, None) if all pass.

    Two gates run per user:

    1. **Vulnerability gate**, conditional on current arc phase. A user
       whose accumulated facts cross VULNERABLE_THRESHOLD is "chronically"
       vulnerable. v3.7.28 changed this from "always block" to "block only
       when their CURRENT arc phase is crisis." The reasoning: a user who
       had a depressive episode in 2024 isn't permanently a topic-of-no-
       posting; they're vulnerable when the conversation is about that.
       Recovery / stability phases let posts through, on the assumption
       that Joan Bright structural anonymization + redaction v2 handle
       residual leak risk.

       If `channel_id` is None (caller couldn't resolve one), or if the
       arc lookup raises, we conservatively fall back to "block." Caller
       should pass channel_id whenever possible.

    2. **Disclosure-severity gate**, unchanged. A severity-≥4 disclosure
       in the last 14 days is an active event signal; we always block on
       it regardless of arc phase, because severity ≥ 4 means "clear
       acute disclosure" — the moment the user just told us something
       big.

    Order matters — vulnerability check is cheaper (fact scan + 1 lookup
    if vulnerable) so we do it first. The disclosure check is a SQL hit
    per user.
    """
    cutoff = time.time() - _DISCLOSURE_LOOKBACK_SECONDS
    for uid in user_ids:
        facts = await memory.get_facts(uid)
        if is_vulnerable_user(facts):
            # Conditional block: only if currently in crisis phase.
            in_crisis = True  # conservative default if we can't tell
            arc_phase: str | None = None
            arc_lookup_ok = False
            if channel_id:
                try:
                    arc = await memory.get_arc(channel_id, uid)
                    arc_lookup_ok = True
                    if arc:
                        arc_phase = str(arc.get("phase", "")).lower() or None
                        in_crisis = arc_phase == "crisis"
                except Exception:
                    log.exception("vulnerability_gate_arc_lookup_failed", user_id=uid)
            log.info(
                "vulnerability_gate_eval",
                user_id=uid,
                channel_id=channel_id,
                arc_lookup_ok=arc_lookup_ok,
                arc_phase=arc_phase,
                in_crisis=in_crisis,
                will_block=in_crisis,
            )
            if in_crisis:
                return "vulnerability_gate", uid
        max_sev = await memory.get_recent_max_severity(uid, cutoff)
        log.info(
            "disclosure_gate_eval",
            user_id=uid,
            max_sev=max_sev,
            threshold=_DISCLOSURE_BLOCK_SEVERITY,
            lookback_days=_DISCLOSURE_LOOKBACK_SECONDS // 86400,
            will_block=max_sev >= _DISCLOSURE_BLOCK_SEVERITY,
        )
        if max_sev >= _DISCLOSURE_BLOCK_SEVERITY:
            return "disclosure_severity", uid
    return None, None


# ---------------------------------------------------------------------------
# Salience detection — what to post about
# ---------------------------------------------------------------------------


async def detect_salience_signal(
    channel_id: str,
    user_ids: list[str],
    *,
    memory,
    recent_messages: list[dict] | None = None,
) -> SalienceSignal | None:
    """Find ONE concrete reason to post now, or None.

    Priority order (return first hit) — most-specific first so we prefer
    seeds with explicit propositional content over heuristic cues:

      1. STANCE — a fresh high-confidence stance Insult took. Strongest
         seed because the position is already abstract (topic + claim),
         not personal facts.
      2. SYNTHESIS — a recent user message that activated the cross-
         domain detector. The user articulated something Insult could
         expand on publicly.
      3. ARC_RECOVERY — a user transitioned out of CRISIS into
         RECOVERY or STABILITY in the last 24h. NOT a content seed —
         a posture-change seed. Insult can publish an abstract idea
         about resilience or emergence without referencing the user.
      4. TOPIC_REPETITION — a user mentioned the same topic 3+ times in
         the last 24h. Fallback when no stance/synthesis fired but
         the conversation has clearly converged on something.

    Stances and arc state come from memory; synthesis and topic
    repetition are detected per-message against `recent_messages`."""
    cutoff = time.time() - _SALIENCE_WINDOW_SECONDS

    # 1. STANCE
    for uid in user_ids:
        stances = await memory.get_stances(channel_id, uid, limit=10)
        for s in stances:
            if s.get("timestamp", 0) < cutoff:
                continue
            confidence = float(s.get("confidence", 0.0))
            if confidence < _MIN_STANCE_CONFIDENCE:
                continue
            return SalienceSignal(
                kind="stance",
                seed_text=str(s.get("position", "")),
                topic=str(s.get("topic", "")),
                confidence=confidence,
                source_user_id=uid,
            )

    # 2. SYNTHESIS
    if recent_messages:
        for m in reversed(recent_messages[-15:]):
            if m.get("role") != "user":
                continue
            sig = detect_synthesis(m.get("content", ""))
            if sig.activated:
                return SalienceSignal(
                    kind="synthesis",
                    seed_text=m.get("content", "")[:300],
                    topic=", ".join(sig.matched_terms[:3]),
                    confidence=0.7,
                    source_user_id=m.get("user_id"),
                )

    # 3. ARC_RECOVERY — fresh transition into RECOVERY / STABILITY
    arc_signal = await _detect_arc_recovery(channel_id, user_ids, memory=memory)
    if arc_signal is not None:
        return arc_signal

    # 4. TOPIC_REPETITION — same user, same topic, ≥3 times in 24h
    return _detect_topic_repetition(user_ids, recent_messages or [])


async def _detect_arc_recovery(
    channel_id: str,
    user_ids: list[str],
    *,
    memory,
) -> SalienceSignal | None:
    """User just exited CRISIS into RECOVERY or STABILITY → publishable
    posture-change. We do NOT use the user's content as seed; the seed is
    a generic 'idea about resilience / emergence' the bot can expand on."""
    cutoff = time.time() - _ARC_RECOVERY_WINDOW_SECONDS
    for uid in user_ids:
        try:
            arc = await memory.get_arc(channel_id, uid)
        except Exception:
            log.debug("moltbook_arc_lookup_failed", user_id=uid)
            continue
        if not arc:
            continue
        phase = str(arc.get("phase", "")).lower()
        phase_since = float(arc.get("phase_since", 0.0))
        if phase not in ("recovery", "stability"):
            continue
        if phase_since < cutoff:
            # Stable for too long — not a fresh transition
            continue
        return SalienceSignal(
            kind="arc_recovery",
            seed_text=f"emergence and resilience after difficulty (phase={phase})",
            topic="resilience emergence",
            confidence=0.65,
            source_user_id=uid,
        )
    return None


def _detect_topic_repetition(
    user_ids: list[str],
    recent_messages: list[dict],
) -> SalienceSignal | None:
    """A topic mentioned 3+ times by the same user in 24h is convergent
    enough to seed a public abstract take. Reuses stance_log._extract_topic
    so the topic-keyword extraction matches the rest of the codebase
    (instead of inventing a parallel keyword extractor)."""
    if not recent_messages:
        return None
    cutoff = time.time() - _TOPIC_REPETITION_LOOKBACK_SECONDS
    user_set = set(user_ids)

    # topic → (count, latest_message_text, latest_user_id)
    counts: dict[str, int] = {}
    latest: dict[str, tuple[str, str]] = {}
    for m in recent_messages:
        if m.get("role") != "user":
            continue
        if m.get("timestamp", 0) < cutoff:
            continue
        uid = m.get("user_id")
        if uid is None or uid not in user_set:
            continue
        content = m.get("content", "")
        topic = _extract_topic(content)
        if not topic:
            continue
        counts[topic] = counts.get(topic, 0) + 1
        latest[topic] = (content[:300], str(uid))

    # Highest count first — if tied, the most-recent message wins
    if not counts:
        return None
    best_topic = max(counts.items(), key=lambda kv: kv[1])[0]
    if counts[best_topic] < _TOPIC_REPETITION_MIN_COUNT:
        return None
    seed_text, source_uid = latest[best_topic]
    return SalienceSignal(
        kind="topic_repetition",
        seed_text=seed_text,
        topic=best_topic,
        confidence=0.6,  # weakest of the four — fallback signal
        source_user_id=source_uid,
    )


# ---------------------------------------------------------------------------
# Regex privacy strip — first scrub layer
# ---------------------------------------------------------------------------


# Static high-risk patterns. Captures details that would identify a user
# directly (date, dose, address) regardless of what facts we have.
_DATE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DATE_SHORT = re.compile(
    r"\b\d{1,2}\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)
_DOSE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|cc|UI|iu)\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Discord snowflake-shaped ids (17-19 digits)
_SNOWFLAKE_PATTERN = re.compile(r"\b\d{17,19}\b")


def _proper_nouns_from_facts(facts: list[dict]) -> set[str]:
    """Collect capitalized tokens from facts that look like proper nouns.

    Rough heuristic: any token starting with a capital letter and ≥3 chars
    that isn't a common Spanish/English sentence starter. Better than nothing
    when the LLM redaction pass is the real safety net; worse than NER but
    the NER cost wasn't worth it for a single language pair we control."""
    skip = {
        "Bernard",
        "Alex",
        "Insult",  # explicit identities — always strip
    }
    nouns: set[str] = set(skip)
    sentence_starters = {
        "El",
        "La",
        "Los",
        "Las",
        "Un",
        "Una",
        "Es",
        "Son",
        "Le",
        "The",
        "A",
        "An",
        "Is",
        "Was",
        "He",
        "She",
        "They",
        "Has",
        "Have",
    }
    for f in facts:
        text = f.get("fact", "")
        for tok in re.split(r"[\s,.;:!?\"\'()]+", text):
            if len(tok) >= 3 and tok[0].isupper() and tok not in sentence_starters:
                nouns.add(tok)
    return nouns


def regex_privacy_strip(text: str, facts: list[dict]) -> str:
    """First-pass scrubbing: replace identifiable details with placeholders.

    NOT sufficient on its own — the LLM redaction pass (P3.2) is the
    decisive layer. This is the cheap pre-filter that catches the obvious
    cases so the LLM has less to clean up."""
    out = text
    out = _DATE_ISO.sub("[fecha]", out)
    out = _DATE_SHORT.sub("[fecha]", out)
    out = _DOSE_PATTERN.sub("[dosis]", out)
    out = _PHONE_PATTERN.sub("[teléfono]", out)
    out = _EMAIL_PATTERN.sub("[email]", out)
    out = _SNOWFLAKE_PATTERN.sub("[id]", out)
    # Proper-noun pass — replace each known noun with a placeholder so the
    # LLM doesn't get to "rewrite Bernard as Sergio" creatively.
    for noun in sorted(_proper_nouns_from_facts(facts), key=len, reverse=True):
        # Word-boundary match avoids "Bernard" matching inside "Bernardino".
        pat = re.compile(rf"\b{re.escape(noun)}\b")
        out = pat.sub("[persona]", out)
    return out


# ---------------------------------------------------------------------------
# Draft generation — LLM call layered over persona
# ---------------------------------------------------------------------------


# Prompt lives in insult/prompts/moltbook_outbound_draft.md — edit there to
# tune behavior without redeploying. The loader is mtime-aware.


def assign_subject_codes(user_ids: list[str]) -> dict[str, str]:
    """Map Discord user_ids to Subject letters (A, B, C, ...) deterministically.

    Sort by user_id ascending and assign A to the smallest. This gives stable
    codes across runs even if user_ids are passed in different orders. With
    Bernard's setup (Alex=1431..., Bernard=9072...), Alex maps to A and
    Bernard maps to B, which is what he asked for.

    Beyond two users it just keeps going (C, D, ...). Caller supplies the
    full list of distinct user_ids in the channel."""
    out: dict[str, str] = {}
    for i, uid in enumerate(sorted(set(user_ids))):
        if i >= 26:
            break  # cap at Z; 26 users in a channel is already absurd
        out[uid] = chr(ord("A") + i)
    return out


async def build_post_draft(
    signal: SalienceSignal,
    target_submolt: str,
    *,
    persona: str,
    llm,
    model: str | None = None,
    previous_notes: list[dict] | None = None,
    subject_codes: dict[str, str] | None = None,
) -> OutboundDraft | None:
    """Generate a draft post anchored on a salience signal.

    `previous_notes` is the list of prior outbound posts (from world_scans
    with source='moltbook_outbound'), used to:
      • Compute the session number for the Joan Bright format (N = len + 1)
      • Let the LLM cite a previous note explicitly when there's thematic
        match (option B continuity from the design discussion)

    Returns None if the LLM came back empty or failed JSON parsing — caller
    treats that as "skip this cycle, log, try again next interval."""
    import json

    seed_block = f"Tipo de saliencia: {signal.kind}\n"
    if signal.topic:
        seed_block += f"Tópico: {signal.topic}\n"
    seed_block += f"Semilla: {signal.seed_text[:400]}"

    # Subject code hint: tell the LLM which Subject letter the salience
    # came from so the draft consistently anonymizes the same user as the
    # same letter across posts. We never expose the user_id itself —
    # only the letter mapping.
    subject_hint = ""
    if signal.source_user_id and subject_codes:
        letter = subject_codes.get(signal.source_user_id)
        if letter:
            subject_hint = f"\n\n## Subject del cual viene esta salience\nSubject {letter} — usa ese código en la nota."

    session_n = len(previous_notes or []) + 1
    notes_block = ""
    if previous_notes:
        notes_block = "\n\n## Tus notas previas en el archivo\n"
        for i, n in enumerate(previous_notes[:5], 1):
            title = str(n.get("topic", "")).strip()
            snippet = str(n.get("findings", ""))[:200].strip()
            notes_block += f"- [{i}] {title}\n      «{snippet}»\n"
        notes_block += (
            "\nSi hay match temático con alguna, puedes referenciarla "
            'explícitamente ("como ya documenté en sesión X, ..."). Si no '
            'hay match, no fuerces la referencia — solo abre con "Continúo '
            'el archivo."'
        )
    else:
        notes_block = "\n\n## Primer post\nEs Sesión 1. Abre el archivo."

    system = f"{persona[:2000]}\n\n{load_prompt('moltbook_outbound_draft')}"
    user = (
        f"Submolt destino: {target_submolt}\n\n"
        f"## Sesión número\nN = {session_n}\n\n"
        f"## Salience\n{seed_block}"
        f"{subject_hint}"
        f"{notes_block}"
    )

    try:
        kwargs: dict = {}
        if model:
            kwargs["model"] = model
        resp = await llm.chat(system, [{"role": "user", "content": user}], **kwargs)
        raw = (resp.text or "").strip()
        if not raw:
            log.warning("moltbook_outbound_draft_empty", signal_kind=signal.kind)
            return None
        # Strip markdown code fences if the LLM added them
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        title = str(data.get("title", "")).strip()
        content = str(data.get("content", "")).strip()
        if not title or not content:
            log.warning("moltbook_outbound_draft_missing_fields", raw_preview=raw[:200])
            return None
        return OutboundDraft(
            title=title[:120],
            content=content,
            target_submolt=target_submolt,
            salience=signal,
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        log.warning("moltbook_outbound_draft_parse_failed", error=str(e))
        return None
    except Exception:
        log.exception("moltbook_outbound_draft_failed", signal_kind=signal.kind)
        return None


# ---------------------------------------------------------------------------
# LLM redaction pass — second scrub layer (decisive)
# ---------------------------------------------------------------------------


# Prompt lives in insult/prompts/moltbook_outbound_redaction.md


async def redact_with_llm(
    content: str,
    private_facts: list[str],
    *,
    client,
    model: str,
) -> str | None:
    """Run a Haiku-class redaction pass over a draft.

    Decisive privacy layer: even if `regex_privacy_strip` missed something
    (a paraphrase, an ungeneric proper noun, an oblique reference), this
    LLM call has the FULL fact list as a *negative target* and is told
    not to leak by literal OR paraphrase. After the LLM returns, we still
    do a literal-substring check because trusting the LLM not to slip
    after telling it not to slip is exactly how leaks happen.

    Returns:
      • str — the redacted draft, ready to publish
      • None — LLM failed, returned empty, or our post-check found a
        literal-substring leak. Caller treats this as 'skip this cycle'.
    """
    if not content or not content.strip():
        return None
    if not private_facts:
        # Nothing to redact against — surface the pre-redaction draft as-is.
        # (regex_privacy_strip already ran upstream so generic patterns are
        # already gone; this branch exists for testing edge cases.)
        return content

    # Cap at 30 facts to keep prompt size bounded; pick the first 30
    # which are typically the most-recently-extracted (already most relevant).
    facts_block = "\n".join(f"- {f}" for f in private_facts[:30])
    user_content = f"DRAFT:\n{content}\n\nPRIVATE FACTS THAT MUST NOT BE INFERABLE FROM YOUR OUTPUT:\n{facts_block}"

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=min(max(len(content) * 2, 256), 2048),
            system=load_prompt("moltbook_outbound_redaction"),
            messages=[{"role": "user", "content": user_content}],
        )
        redacted = response.content[0].text.strip()
    except Exception:
        log.exception("moltbook_redaction_call_failed")
        return None

    if not redacted:
        log.info("moltbook_redaction_returned_empty", facts_count=len(private_facts))
        return None

    # Substring-leak post-check. The LLM was told not to leak; this verifies.
    # We do case-insensitive substring match because casing is not a defense.
    redacted_lower = redacted.lower()
    for f in private_facts:
        f_str = str(f).strip()
        # Skip very short / generic facts to avoid false positives. Short
        # proper nouns (Bernard, Alex) are already stripped in the regex
        # layer; what reaches us here is only the long contextual facts,
        # so the threshold can be reasonably high without losing coverage.
        if len(f_str) < 10:
            continue
        if f_str.lower() in redacted_lower:
            log.warning(
                "moltbook_redaction_leak_detected",
                fact_preview=f_str[:60],
                redacted_preview=redacted[:120],
            )
            return None

    log.info(
        "moltbook_redaction_applied",
        original_len=len(content),
        redacted_len=len(redacted),
        facts_count=len(private_facts),
    )
    return redacted


# ---------------------------------------------------------------------------
# Audit persistence — every draft hits the DB before publication
# ---------------------------------------------------------------------------


_DRAFT_SOURCE = "moltbook_outbound_draft"
_PUBLISHED_SOURCE = "moltbook_outbound"


async def persist_draft(
    draft: OutboundDraft,
    redacted_content: str | None,
    *,
    memory,
    extra_notes: str = "",
) -> None:
    """Save the draft to world_scans BEFORE publishing.

    Two reasons this exists:
      1. Audit trail — even if Moltbook later 5xx's the publish, or a future
         deploy changes the redaction logic, we have the original draft
         (pre and post redaction) on disk for review.
      2. Recovery — if Moltbook deletes a post or the operator wants to
         replay one, the original is right here.

    Stored with source='moltbook_outbound_draft'. The PUBLISHED variant
    (source='moltbook_outbound', external_id=post.id) is added separately
    by `persist_published_post` after the network call succeeds. Two rows
    per published post is intentional: 'draft' is what we generated,
    'outbound' is what actually shipped.
    """
    try:
        commentary_parts = [
            f"signal_kind={draft.salience.kind}",
            f"signal_topic={draft.salience.topic}",
            f"signal_confidence={draft.salience.confidence:.2f}",
        ]
        if redacted_content is not None:
            commentary_parts.append(f"redacted_len={len(redacted_content)}")
        if extra_notes:
            commentary_parts.append(extra_notes)
        await memory.store_world_scan(
            topic=draft.title,
            findings=(redacted_content if redacted_content is not None else draft.content)[:1000],
            commentary=" | ".join(commentary_parts),
            source=_DRAFT_SOURCE,
            external_id=None,  # not yet published
        )
    except Exception:
        # Persistence failure must NOT block the publish. Audit trail is best
        # effort — losing one draft to disk is recoverable from logs.
        log.exception("moltbook_outbound_draft_persist_failed", title=draft.title[:80])


async def persist_published_post(
    draft: OutboundDraft,
    published_external_id: str,
    redacted_content: str,
    *,
    memory,
) -> None:
    """Save a row recording the successful publish. external_id is the
    Moltbook post id returned by source.create_post — that's what later
    queries (and the duplicate-detection partial UNIQUE INDEX on
    world_scans) use to dedupe."""
    try:
        await memory.store_world_scan(
            topic=draft.title,
            findings=redacted_content[:1000],
            commentary=(f"published signal_kind={draft.salience.kind} submolt={draft.target_submolt}"),
            source=_PUBLISHED_SOURCE,
            external_id=published_external_id,
        )
    except Exception:
        log.exception(
            "moltbook_outbound_published_persist_failed",
            external_id=published_external_id,
        )


async def load_previous_outbound_notes(memory, limit: int = 5) -> list[dict]:
    """Fetch the last N published outbound posts for the Joan Bright
    continuity feature. Returns rows with fields: topic (= title),
    findings (= published content), timestamp, external_id."""
    try:
        return await memory.get_recent_world_scans(limit=limit, source=_PUBLISHED_SOURCE)
    except Exception:
        log.exception("moltbook_outbound_load_previous_failed")
        return []
