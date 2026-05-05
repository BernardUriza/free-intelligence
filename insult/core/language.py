"""Language Cure — post-generation normalization of mixed-language output.

Uses a fast, cheap LLM (Haiku) to translate English fragments in
predominantly Spanish text back to Mexican Spanish, preserving brands,
acronyms, proper nouns, tech terms, and Discord/bot syntax.

This is step 7c in the post-generation pipeline, after character guard
and before delivery.
"""

import re

import structlog

from insult.core.prompts_loader import load_prompt

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

        if cured != text:
            log.info("language_cure_applied", original_len=len(text), cured_len=len(cured))
        else:
            log.debug("language_cure_no_change")

        return cured

    except Exception:
        log.exception("language_cure_failed")
        return text  # Fail-safe: return original on any error
