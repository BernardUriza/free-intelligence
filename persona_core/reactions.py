"""Emoji reaction contract — [REACT:] parsing, stripping, and async execution.

Shared across every persona host (Insult's chat pipeline, ALICE's cog, the
persona gateway). Handles [REACT:emoji1,emoji2] markers in LLM responses:
- parse_reactions(): extract emoji list from response text
- strip_reactions(): remove [REACT:] markers from response text
- harvest_orphan_emojis(): opt-in safety net for models that emit emojis inline
- add_reactions(): async background task to add emojis to Discord messages
"""

import asyncio
import random
import re

import discord
import structlog

log = structlog.get_logger()

REACTION_PATTERN = re.compile(r"\[REACT:([^\]]*)\]", re.IGNORECASE)
MAX_REACTIONS = 8
REACTION_DELAY_MIN = 0.5
REACTION_DELAY_MAX = 2.0
REACTION_INTERVAL = 0.35

_EMOJI_GRAPHEME = re.compile(
    r"(?:"
    r"[\U0001F1E6-\U0001F1FF]{2}"
    r"|[\U0001F000-\U0001FFFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF]"
    r"(?:[\U0001F3FB-\U0001F3FF])?"
    r"(?:\uFE0F)?"
    r"(?:\u200D"
    r"[\U0001F000-\U0001FFFF\u2600-\u27BF][\U0001F3FB-\U0001F3FF]?\uFE0F?)*"
    r")"
)
_MAX_EMOJI_LEN = 16


def _split_emoji_token(token: str) -> list[str]:
    """Split a token that may contain multiple concatenated unicode emojis.

    Matches one emoji grapheme at a time (base + optional skin tone, variation
    selector, ZWJ sequences, regional-indicator flags), so "🦷🪬🫧" → three
    reactions instead of one Discord-rejected token. Custom Discord emojis
    (<:name:id>) and single short emojis pass through unchanged.
    """
    if token.startswith("<") and token.endswith(">"):
        return [token]
    matches = _EMOJI_GRAPHEME.findall(token)
    if len(matches) >= 2:
        return matches
    return [token]


def parse_reactions(response: str) -> list[str]:
    """Extract emoji reactions from LLM response.

    Parses [REACT:emoji1,emoji2] markers and returns a list of emoji strings.
    Returns at most MAX_REACTIONS emojis. Returns empty list if no marker found.
    """
    match = REACTION_PATTERN.search(response)
    if not match:
        return []

    raw = match.group(1).strip()
    if not raw:
        return []

    tokens = [e.strip() for e in raw.split(",") if e.strip()]
    emojis: list[str] = []
    for tok in tokens:
        for piece in _split_emoji_token(tok):
            if piece and len(piece) <= _MAX_EMOJI_LEN:
                emojis.append(piece)
    return emojis[:MAX_REACTIONS]


def strip_reactions(response: str) -> str:
    """Remove [REACT:...] markers from the response text."""
    return REACTION_PATTERN.sub("", response).strip()


def harvest_orphan_emojis(
    response_without_markers: str,
    already_parsed: list[str],
) -> tuple[list[str], str]:
    """Find emojis emitted inline (not wrapped in [REACT:...]) and convert them
    to reactions.

    Opus 4.7 (and likely future models) sometimes ignores the `[REACT:...]`
    instruction and writes emojis straight into the response text. Those
    emojis render as plain characters in Discord chat bubbles instead of
    firing as reactions on the user's message — exactly the wrong UX.

    This harvester is the safety net: it scans the post-`strip_reactions`
    text, extracts unique emoji graphemes up to the per-turn cap, appends
    them to the reactions list, and strips them from the visible text.

    Opt-in per persona: Insult enforces it (his DNA forbids inline emojis);
    personas whose voice legitimately writes emojis inline must NOT call it.

    Args:
        response_without_markers: text after `strip_reactions` ran on it.
        already_parsed: emojis already extracted from explicit `[REACT:...]`
            markers. Used to dedupe AND to respect the MAX_REACTIONS cap.

    Returns:
        tuple of (combined_reactions, cleaned_text) where combined_reactions
        respects MAX_REACTIONS and cleaned_text has the harvested emojis
        removed.
    """
    if not response_without_markers:
        return already_parsed, response_without_markers

    seen = list(already_parsed)
    seen_set = set(already_parsed)
    remaining_budget = MAX_REACTIONS - len(seen)
    if remaining_budget <= 0:
        return seen, response_without_markers

    found: list[tuple[int, int, str]] = []
    for m in _EMOJI_GRAPHEME.finditer(response_without_markers):
        token = m.group(0)
        if not token or len(token) > _MAX_EMOJI_LEN:
            continue
        if token not in seen_set:
            found.append((m.start(), m.end(), token))
            seen_set.add(token)
            seen.append(token)
            remaining_budget -= 1
            if remaining_budget <= 0:
                break

    if not found:
        return seen, response_without_markers

    cleaned = response_without_markers
    for start, end, _ in reversed(found):
        cleaned = cleaned[:start] + cleaned[end:]

    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +([.,;:!?])", r"\1", cleaned)
    cleaned = cleaned.strip()

    return seen, cleaned


async def add_reactions(message: discord.Message, emojis: list[str]) -> None:
    """Add emoji reactions to a Discord message with human-like delay.

    Sleeps REACTION_DELAY_MIN..MAX before the first reaction and
    REACTION_INTERVAL between reactions (rate-limit safety). Stops at the
    first failed emoji. Designed to run as a background task via
    asyncio.create_task().
    """
    try:
        await asyncio.sleep(random.uniform(REACTION_DELAY_MIN, REACTION_DELAY_MAX))

        for i, emoji in enumerate(emojis):
            try:
                await message.add_reaction(emoji)
                log.info("reaction_added", emoji=emoji, message_id=message.id)
            except (discord.HTTPException, discord.NotFound) as e:
                log.warning("reaction_failed", emoji=emoji, error=str(e))
                break
            if i < len(emojis) - 1:
                await asyncio.sleep(REACTION_INTERVAL)
    except Exception:
        log.exception("reaction_task_failed", message_id=message.id)
