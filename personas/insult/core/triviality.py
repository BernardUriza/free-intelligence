"""Detect trivial messages that don't warrant an LLM call.

Insult receives every message in a channel. Many are throwaways ("ok", "si",
"gracias", a solo emoji, "xd") that don't benefit from a full LLM response and
just burn tokens. This module filters them so the bot can skip LLM generation
while still storing the message in memory for context.
"""

import re

# Messages <= this many visible chars (after stripping) are candidates for triviality.
_MIN_SUBSTANTIVE_LEN = 4

# Short words that LOOK trivial but aren't — attention-callers, greetings, or
# pronouns that demand a response. Checked before the length-based fallback.
_SHORT_NON_TRIVIAL = frozenset(
    {
        "oye",
        "ey",
        "eh",
        "hey",
        "che",
        "wey",
        "vato",
        "yo",
        "mira",
        "pues",
        "sale",
        "dime",
        "vale",
        "bien",  # "bien" alone — could be "bien?" meaning "you ok?"
    }
)

# Case-insensitive exact-match tokens that convey no new information.
_TRIVIAL_TOKENS = frozenset(
    {
        "ok",
        "okay",
        "oka",
        "okey",
        "okok",
        "k",
        "kk",
        "si",
        "sí",
        "no",
        "nop",
        "nope",
        "yep",
        "yeah",
        "ya",
        "yes",
        "ah",
        "aha",
        "ajá",
        "aja",
        "mmm",
        "mm",
        "hmm",
        "uff",
        "ufff",
        "eso",
        "buena",
        "bueno",
        # NOTE: "bien" intentionally NOT here — it's in _SHORT_NON_TRIVIAL because
        # a solo "bien" (especially as "¿bien?") is often a check-in that deserves
        # a response. The trivial-token check runs BEFORE the allowlist, so
        # having "bien" here would make the allowlist useless for it.
        "gracias",
        "thx",
        "ty",
        "thanks",
        "xd",
        "xdd",
        "xddd",
        "lol",
        "jaja",
        "jajaja",
        "jajajaja",
        "jeje",
        "jejeje",
        "jiji",
        "jijiji",
        "😂",
        "🤣",
        "💀",
        "👍",
        "👎",
        "🔥",
        "🙏",
    }
)

# Invariant: these two sets must be disjoint, or the allowlist is dead code.
assert not (_TRIVIAL_TOKENS & _SHORT_NON_TRIVIAL), (
    f"Tokens in both TRIVIAL and SHORT_NON_TRIVIAL lists — allowlist can't win: {_TRIVIAL_TOKENS & _SHORT_NON_TRIVIAL}"
)

_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_EMOJI_RANGE = re.compile(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF]")


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = _PUNCTUATION.sub(" ", text.lower())
    s = _WHITESPACE.sub(" ", s).strip()
    return s


def is_trivial(text: str) -> bool:
    """Return True if the message is not worth an LLM call.

    Criteria (any triggers trivial):
    - Empty after strip
    - Only emoji characters (any length) — a reaction suffices
    - Normalized text is in the trivial-token allowlist
    - <=3 chars AND contains no digits AND not in an explicit allow pattern
    """
    if not text:
        return True

    stripped = text.strip()
    if not stripped:
        return True

    # Only emojis (possibly repeated) → trivial
    no_emoji = _EMOJI_RANGE.sub("", stripped)
    if not _WHITESPACE.sub("", no_emoji):
        return True

    norm = _normalize(stripped)
    if not norm:
        return True
    if norm in _TRIVIAL_TOKENS:
        return True

    # Multi-word but every word trivial (e.g., "ok gracias", "si ya")
    parts = norm.split(" ")
    if len(parts) <= 3 and all(p in _TRIVIAL_TOKENS for p in parts):
        return True

    # Short-word allowlist overrides the length-fallback below — attention-callers
    # like "oye", "che", "hey" etc. must always get a response, even though they
    # are <4 chars and without digits.
    if len(parts) == 1 and norm in _SHORT_NON_TRIVIAL:
        return False

    # Single "word" too short to contain intent, no digits (questions like "2+2?" survive)
    return len(parts) == 1 and len(norm) < _MIN_SUBSTANTIVE_LEN and not any(c.isdigit() for c in norm)
