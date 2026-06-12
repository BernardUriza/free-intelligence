"""Language Cure — post-generation normalization of mixed-language output.

Uses a fast, cheap LLM (Haiku) to translate English fragments in
predominantly Spanish text back to Mexican Spanish, preserving brands,
acronyms, proper nouns, tech terms, and Discord/bot syntax.

This is step 7c in the post-generation pipeline, after character guard
and before delivery.
"""

import re

import structlog

from personas.insult.core.prompts_loader import load_prompt

log = structlog.get_logger()

# Matches any <output>...</output>, <response>...</response>, <input>...</input>
# wrapper that Haiku might add around its entire reply, even with leading or
# trailing whitespace / newlines. DOTALL so payload can span lines.
_FULL_WRAPPER_RE = re.compile(
    r"^\s*<(output|response|input)>(.*?)</\1>\s*$",
    re.IGNORECASE | re.DOTALL,
)

# Leftover "→ " prefix from the few-shot arrow style (bounded — will not
# consume multiple arrows in a row, just the single expected one).
_LEADING_ARROW_RE = re.compile(r"^\s*→\s*")

# Meta-preambles Haiku sometimes emits when it decides the input was already
# in Spanish or doesn't need changes. They survive the wrapper strip because
# they're plain prose, not XML. The pattern is: one line of meta-commentary
# ending in `:` or `.`, followed by the actual text on the next line OR on
# the same line after the colon. Documented from v3.9.16 prod incident where
# the visible Insult reply started with: "El texto está completamente en
# español, así que lo devuelvo sin cambios: Sospecho que hablás del..."
_META_PREAMBLE_RE = re.compile(
    r"^\s*"
    r"(?:"
    # Spanish variants
    r"(?:el\s+texto\s+(?:está|esta|es|ya\s+está)\s+(?:completamente\s+)?(?:en\s+(?:español|espanol)|sin\s+cambios)[^.\n:]*)"
    r"|(?:aquí\s+está\s+el\s+texto[^.\n:]*)"
    r"|(?:lo\s+devuelvo\s+(?:tal\s+cual|sin\s+cambios)[^.\n:]*)"
    r"|(?:no\s+hay\s+(?:nada\s+que\s+)?(?:cambiar|traducir|cambios)[^.\n:]*)"
    r"|(?:ya\s+(?:está|esta)\s+(?:completamente\s+)?en\s+(?:español|espanol)[^.\n:]*)"
    # English variants
    r"|(?:returning\s+(?:the\s+text\s+)?unchanged[^.\n:]*)"
    r"|(?:the\s+text\s+is\s+(?:already\s+)?(?:entirely\s+|fully\s+)?in\s+spanish[^.\n:]*)"
    r"|(?:no\s+changes\s+needed[^.\n:]*)"
    r"|(?:here\s+is\s+the\s+text[^.\n:]*)"
    r")"
    r"\s*[:.\n]\s*",
    re.IGNORECASE,
)

# Prompt lives in insult/prompts/language_cure.md


async def language_cure(
    client,
    model: str,
    text: str,
) -> str:
    """Normalize mixed-language chatbot output to Mexican Spanish.

    Uses a fast/cheap model (Haiku) with no conversation context —
    pure text transformation. Returns original text on any failure.
    """
    if not text or len(text) < 10:
        return text

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=min(len(text) * 3, 4096),  # ~2x input, capped
            system=load_prompt("language_cure"),
            # User content is the raw text — no wrapper tags. Previous
            # implementation used "<input>{text}</input>" which, combined with
            # XML few-shot, taught Haiku to answer with <output>...</output>
            # wrappers. Even with a strip pass, partial/stray tags leaked.
            messages=[{"role": "user", "content": text}],
        )
        cured = response.content[0].text.strip()

        # Safety: if Haiku returned something wildly different in length, keep original
        if not cured or len(cured) < len(text) * 0.5 or len(cured) > len(text) * 2.5:
            log.warning("language_cure_length_mismatch", original=len(text), cured=len(cured))
            return text

        # Strip stray wrappers Haiku sometimes adds despite the instruction.
        # Uses regex instead of startswith/endswith so leading/trailing
        # whitespace and newlines don't defeat the match — v3.4.6 used literal
        # startswith which missed "<output>X</output>\n" and similar variants.
        m = _FULL_WRAPPER_RE.match(cured)
        if m:
            cured = m.group(2).strip()
        # Leftover "→ " prefix from the few-shot arrow style.
        cured = _LEADING_ARROW_RE.sub("", cured, count=1)
        # Strip meta-preambles Haiku emits when it decides "nothing to change"
        # (e.g. "El texto está completamente en español, así que lo devuelvo
        # sin cambios: ..."). Discovered v3.9.16 prod incident on
        # @A.L.I.C.E. Porfiriato thread; visible to the user as a system
        # leak before Insult's real reply. Anchored with `count=1` so we
        # never strip more than one preamble per turn.
        before = cured
        cured = _META_PREAMBLE_RE.sub("", cured, count=1).strip()
        if cured != before:
            log.warning("language_cure_meta_preamble_stripped", chars_removed=len(before) - len(cured))

        if cured != text:
            log.info("language_cure_applied", original_len=len(text), cured_len=len(cured))
        else:
            log.debug("language_cure_no_change")

        return cured

    except Exception:
        log.exception("language_cure_failed")
        return text  # Fail-safe: return original on any error
