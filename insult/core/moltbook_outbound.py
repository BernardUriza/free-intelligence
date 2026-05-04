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

from insult.core.synthesis_detector import detect_synthesis
from insult.core.vulnerability import is_vulnerable_user

log = structlog.get_logger()


# How far back the disclosure gate looks for a severity≥3 hit. 30 days
# is conservative — a user revealing a CPTSD diagnosis 4 weeks ago should
# still suppress related external content. Tune by KQL telemetry once
# the lane is live.
_DISCLOSURE_LOOKBACK_SECONDS = 30 * 86400

# Salience window: how recently a stance / synthesis must have fired for
# the cron to consider it a posting reason. Longer than the cron interval
# (24h) by some margin so cron jitter doesn't drop a fresh stance.
_SALIENCE_WINDOW_SECONDS = 36 * 3600

# Minimum stance confidence required to be a posting seed. Below this the
# stance is too vague to anchor a public post.
_MIN_STANCE_CONFIDENCE = 0.6


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SalienceSignal:
    """A reason to post NOW. The cron only fires outbound when one fires."""

    kind: str  # 'stance' | 'synthesis' | 'arc_recovery'
    seed_text: str  # raw text that anchored the salience (NOT the post draft)
    topic: str = ""  # for stance signals: the stance topic keywords
    confidence: float = 0.0  # 0..1


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


async def is_outbound_blocked(user_ids: list[str], *, memory) -> tuple[str | None, str | None]:
    """Return (reason, user_id) if any gate blocks; (None, None) if all pass.

    Order matters — vulnerability check is cheaper (just a fact scan) so we
    do it first. The disclosure check is a SQL hit per user."""
    cutoff = time.time() - _DISCLOSURE_LOOKBACK_SECONDS
    for uid in user_ids:
        facts = await memory.get_facts(uid)
        if is_vulnerable_user(facts):
            return "vulnerability_gate", uid
        max_sev = await memory.get_recent_max_severity(uid, cutoff)
        if max_sev >= 3:
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

    Priority order (return first hit):
      1. STANCE — a recent high-confidence stance Insult took
      2. SYNTHESIS — a recent user message that activated the synthesis detector
         (cross-domain claim Insult could expand on without leaking specifics)

    Stances are queried from memory; synthesis is detected per-message
    against `recent_messages` because we don't persist a synthesis log.
    """
    cutoff = time.time() - _SALIENCE_WINDOW_SECONDS

    # 1. STANCE — Insult's own positions are the safest seed material because
    #    they're already abstract (topic + position), not personal facts.
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
            )

    # 2. SYNTHESIS — scan recent USER messages for cross-domain hits.
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
                    confidence=0.7,  # heuristic — synthesis hits are "interesting"
                )

    return None


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


_DRAFT_PROMPT = """\
Vas a publicar un post en Moltbook (red social de AI agents). El post lo lees TÚ
mismo en feed, no es para humanos directos — son otros agents.

CONTEXTO DE SALIENCIA: una observación / postura / hilo que se gestó en tu chat
de Discord con tus humanos. NO copies la observación literal; tómala como semilla
y abstráela a una idea posteable que NO requiera contexto privado.

Reglas duras:
- NUNCA menciones nombres propios de tus humanos (Bernard, Alex, etc.)
- NUNCA menciones fechas específicas, dosis, lugares concretos
- NUNCA menciones diagnósticos médicos, medicamentos, terapia
- El post debe tener sentido SIN tu chat de Discord como contexto
- Spanish (Mexican casual). Tono Insult: abrasivo, curioso, anti-domination
- 2-4 oraciones. NO subtítulos ni listas — fluye como pensamiento

Estructura del output (devuelve SOLO el JSON, nada más):
{
  "title": "<título corto, ≤80 chars, provocativo>",
  "content": "<cuerpo del post, 2-4 oraciones>"
}"""


async def build_post_draft(
    signal: SalienceSignal,
    target_submolt: str,
    *,
    persona: str,
    llm,
    model: str | None = None,
) -> OutboundDraft | None:
    """Generate a draft post anchored on a salience signal.

    Returns None if the LLM came back empty or failed JSON parsing — caller
    treats that as "skip this cycle, log, try again next interval."""
    import json

    seed_block = f"Tipo de saliencia: {signal.kind}\n"
    if signal.topic:
        seed_block += f"Tópico: {signal.topic}\n"
    seed_block += f"Semilla: {signal.seed_text[:400]}"

    system = f"{persona[:2000]}\n\n{_DRAFT_PROMPT}"
    user = f"Submolt destino: {target_submolt}\n\n## Salience\n{seed_block}"

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


_REDACTION_SYSTEM = """\
You are a privacy redactor for a public social-network post.

INPUT FORMAT
- The user message contains:
    DRAFT:
    <text to rewrite>

    PRIVATE FACTS THAT MUST NOT BE INFERABLE FROM YOUR OUTPUT:
    - fact A
    - fact B
    ...

YOUR JOB
Rewrite the draft so it preserves the IDEA / TAKE / OPINION but removes
anything that would identify the humans behind it. The output is going
to be PUBLIC on a social network where other agents and search engines
will read it.

HARD RULES
- Output must NOT contain any of the listed facts, literally OR by paraphrase
- Output must NOT mention names, specific dates, locations, dosages,
  diagnoses, or specific incidents — even ones not in the facts list,
  if they sound personal
- Output MUST preserve the intellectual content (the take, the opinion,
  the abstraction)
- Tone: Spanish (Mexican casual), matching the draft. Same persona.
- 2-4 sentences. NO subtitles or lists.

WHEN YOU CAN'T REDACT SAFELY
If the draft cannot be rewritten without revealing the private facts —
because the take itself only makes sense WITH the private context — return
a single empty line. The caller will skip publishing.

OUTPUT FORMAT
Return ONLY the rewritten draft. No <output> tags, no JSON, no
commentary, no preamble like "Here is the rewritten:". Just the text."""


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
            system=_REDACTION_SYSTEM,
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
