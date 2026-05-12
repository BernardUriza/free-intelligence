"""Post-generation text mutators.

All pure functions — given a string (and sometimes context like recent message
lengths or a user message), they return a new string. No I/O, no side effects
beyond the structlog calls used for telemetry. Run in series after the LLM
returns; `chat.py::run_turn` chains them in the documented order.
"""

from __future__ import annotations

import random
import re

import structlog

from insult.core.patterns import COMMON_STOPWORDS

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Formatting normalizer — exclamation + bold caps + Sonnet artifacts
# ---------------------------------------------------------------------------

_EXCL_MULTI = re.compile(r"!{2,}")  # !! or !!! → .
_EXCL_PAIR = re.compile(r"¡([^!]*)!")  # ¡text! → text.

# Sonnet 4.6 artifacts (Bernard observed 2026-05-12 on #general):
#  - Smart quotes (curly) instead of straight ones — preferred by tokenizer
#    because training data associates them with "formal" prose.
#  - Newline before mid-sentence em-dash — model treats `—` as paragraph break.
#  - Newline after a colon when there is no real list following (followed by
#    inline text or **bold**, not a list bullet) — model defaults to markdown
#    block formatting even in chat prose.
# All three look like orthographic errors when rendered in Discord. Cheap
# deterministic fixes here so we don't have to fight prompt engineering.

# Smart quotes regex — the ambiguous Unicode chars are intentional (we
# want to match exactly them). noqa silences ruff RUF001 where it fires.
_SMART_QUOTES_DOUBLE = re.compile("[“”]")  # U+201C U+201D → "
_SMART_QUOTES_SINGLE = re.compile("[‘’]")  # U+2018 U+2019 → '  # noqa: RUF001
_NL_BEFORE_EMDASH = re.compile(r"\n\s*—")  # \n — → space —
_NL_AFTER_COLON_NO_LIST = re.compile(r":\s*\n+(?![\s*\-#>0-9])")  # : \n word → : word


def normalize_formatting(text: str) -> str:
    """Enforce exclamation and bold limits + clean Sonnet 4.6 formatting artifacts.

    Rules:
    - Collapse !! / !!! → .
    - Max 1 exclamation mark per response. First ¡...! pair survives;
      subsequent pairs are deflated (¡ removed, ! → .).
    - Max 2 bold blocks (**text**) per response. Excess blocks are
      stripped of ** delimiters (text preserved).
    - Smart quotes "" and '' → straight quotes " and '.
    - Newline immediately before a mid-sentence em-dash → single space.
    - Newline after a colon NOT followed by a real list marker → single space.
    """
    if not text:
        return text

    # 0. Smart quotes → straight quotes. Cheap, idempotent.
    text = _SMART_QUOTES_DOUBLE.sub('"', text)
    text = _SMART_QUOTES_SINGLE.sub("'", text)

    # 0b. Newline before em-dash mid-sentence. The em-dash is a comma-strength
    # pause in Spanish; a newline before it makes it read as a list bullet.
    text = _NL_BEFORE_EMDASH.sub(" —", text)

    # 0c. Colon followed by newline followed by inline content (NOT a list
    # bullet, NOT a heading, NOT bold-as-list-item). Collapse to single space
    # so "plataformas:\n**incluyeme**" reads as continuous prose.
    text = _NL_AFTER_COLON_NO_LIST.sub(": ", text)

    # 1. Collapse multi-exclamation: !! → .  !!! → .
    text = _EXCL_MULTI.sub(".", text)

    # 2. Limit ¡...! pairs to max 1 per response
    excl_count = 0

    def _deflate_excl(m: re.Match) -> str:
        nonlocal excl_count
        excl_count += 1
        if excl_count <= 1:
            return m.group(0)  # keep first pair
        # Deflate: remove ¡, replace ! with .
        return m.group(1) + "."

    text = _EXCL_PAIR.sub(_deflate_excl, text)

    # 3. Handle remaining bare ! (not inside ¡...! pairs).
    # After step 2, the only surviving ¡...! is the first pair. Any other !
    # is bare (e.g. "Wow!") and counts against the budget.
    remaining_budget = max(0, 1 - excl_count)
    parts = list(text)
    inside_inverted = False
    bare_positions = []
    for i, ch in enumerate(parts):
        if ch == "¡":  # ¡
            inside_inverted = True
        elif ch == "!" and inside_inverted:
            inside_inverted = False  # closing of ¡...! pair — skip
        elif ch == "!":
            bare_positions.append(i)

    for pos in bare_positions:
        if remaining_budget > 0:
            remaining_budget -= 1
        else:
            parts[pos] = "."
    text = "".join(parts)

    # 4. Limit bold blocks to max 2
    bold_count = 0

    def _limit_bold(m: re.Match) -> str:
        nonlocal bold_count
        bold_count += 1
        if bold_count <= 2:
            return m.group(0)
        return m.group(1)  # strip ** delimiters, keep text

    text = re.sub(r"\*\*([^*]+)\*\*", _limit_bold, text)

    return text


# ---------------------------------------------------------------------------
# Anti-parrot — strip verbatim quotes of user message from response
# ---------------------------------------------------------------------------

_QUOTE_STOPWORDS = COMMON_STOPWORDS | {
    "los",
    "las",
    "por",
    "con",
    "para",
    "del",
    "al",
    "me",
    "te",
    "mi",
    "tu",
    "su",
    "ya",
    "si",
    "mas",
    "pero",
    "como",
    "and",
    "but",
}


def strip_echoed_quotes(response: str, user_message: str) -> str:
    """Remove verbatim quotes of the user's message from the bot's response.

    Detects when the bot quoted the user's exact words (5+ word sequences)
    and strips them. Humans don't repeat each other's full phrases in chat.
    """
    if not response or not user_message:
        return response

    user_words = user_message.lower().split()
    if len(user_words) < 5:
        return response  # too short to have meaningful quotes

    # Build all 5-word n-grams from user message
    user_ngrams: set[str] = set()
    for i in range(len(user_words) - 4):
        ngram = " ".join(user_words[i : i + 5])
        # Skip if mostly stopwords
        content_words = [w for w in user_words[i : i + 5] if w not in _QUOTE_STOPWORDS]
        if len(content_words) >= 2:
            user_ngrams.add(ngram)

    if not user_ngrams:
        return response

    # Find and remove echoed segments — only the n-gram itself + surrounding quotes
    modified = response
    for ngram in sorted(user_ngrams, key=len, reverse=True):
        pattern = re.compile(re.escape(ngram), re.IGNORECASE)
        if pattern.search(modified):
            # Strip the n-gram and any immediately surrounding quote marks
            modified = re.sub(
                r'["“”]*' + re.escape(ngram) + r'["“”]*',
                "",
                modified,
                flags=re.IGNORECASE,
                count=1,
            )
            log.info("echo_stripped", ngram=ngram[:50])

    # Clean up artifacts: double spaces, orphaned dashes, empty bold
    modified = re.sub(r"\*\*\s*\*\*", "", modified)  # empty bold
    modified = re.sub(r"  +", " ", modified)  # double spaces
    modified = re.sub(r"\n\s*\n\s*\n", "\n\n", modified)  # triple newlines
    return modified.strip() if modified.strip() else response  # never return empty


# ---------------------------------------------------------------------------
# Bullet/list stripper — convert AI-formatted lists to prose
# ---------------------------------------------------------------------------

_NUMBERED_LIST = re.compile(r"(?m)^\d+[\.\)]\s+(.+)$")
_BULLET_LIST = re.compile(r"(?m)^[-\*•]\s+(.+)$")


def strip_lists(text: str) -> str:
    """Convert numbered/bullet lists to inline prose.

    '1. First thing\\n2. Second thing\\n3. Third thing'
    becomes 'First thing. Second thing. Third thing.'
    """
    if not text:
        return text

    # Count list items — only transform if there are 2+ consecutive
    numbered_items = _NUMBERED_LIST.findall(text)
    bullet_items = _BULLET_LIST.findall(text)

    if len(numbered_items) >= 2:
        # Replace numbered list with prose
        def _numbered_to_prose(m: re.Match) -> str:
            return m.group(1).rstrip(".") + "."

        text = _NUMBERED_LIST.sub(_numbered_to_prose, text)

    if len(bullet_items) >= 2:

        def _bullet_to_prose(m: re.Match) -> str:
            return m.group(1).rstrip(".") + "."

        text = _BULLET_LIST.sub(_bullet_to_prose, text)

    # Clean up excessive blank lines left by list removal
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ---------------------------------------------------------------------------
# Length enforcer — mechanical variation when prompt hints fail
# ---------------------------------------------------------------------------


def enforce_length_variation(text: str, recent_lengths: list[int]) -> str:
    """Mechanically enforce length variation when 3+ consecutive responses are medium.

    If the last 3 responses were all 80-200 words, truncate to first 2 sentences
    (forcing a short response). This is the nuclear option — the prompt-based
    length hint clearly doesn't work, so we enforce mechanically.
    """
    if not text or len(recent_lengths) < 3:
        return text

    last3 = recent_lengths[-3:]
    if not all(80 < wc < 200 for wc in last3):
        return text  # varied enough, no intervention

    # Force short: keep only first 2 sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 2:
        return text  # already short

    truncated = " ".join(sentences[:2])

    log.info(
        "length_enforced",
        original_words=len(text.split()),
        truncated_words=len(truncated.split()),
        recent_lengths=last3,
    )
    return truncated


def get_length_hint(recent_lengths: list[int]) -> str:
    """Generate a length variation hint when recent responses are too uniform.

    If the last 3+ responses are all in the 80-220 word range (medium),
    inject a directive to break the pattern.
    """
    if len(recent_lengths) < 3:
        return ""
    last3 = recent_lengths[-3:]
    if all(80 < wc < 220 for wc in last3):
        target = random.choice(["micro", "short", "long"])
        hints = {
            "micro": (
                "## Length Alert\n"
                "Your last 3 responses were all medium-length (~150 words). "
                "THIS response must be UNDER 20 words. One sentence max. Hit hard and shut up."
            ),
            "short": (
                "## Length Alert\n"
                "Your last 3 responses were all similar length. "
                "THIS response must be 2-3 sentences max. Be terse."
            ),
            "long": (
                "## Length Alert\n"
                "Your last 3 responses were all similar length. "
                "If the topic earns it, go DEEP — 250+ words."
            ),
        }
        return hints[target]
    return ""


# ---------------------------------------------------------------------------
# Opener deduplication
# ---------------------------------------------------------------------------


def _extract_opener_name(line: str) -> str:
    """Extract the leading name from an opener like '¡BERNARD! ...' → 'bernard'."""
    cleaned = re.sub(r"^[¡!¿?*\s]+", "", line)
    # Take first word (the name), lowercase
    match = re.match(r"([A-Za-záéíóúñÁÉÍÓÚÑ]+)", cleaned)
    return match.group(1).lower() if match else ""


def deduplicate_opener(text: str, recent_openers: list[str]) -> str:
    """If opener starts with the same name as recent ones, strip the first line."""
    if not text or not recent_openers:
        return text

    first_line = text.split("\n")[0]
    name = _extract_opener_name(first_line)
    if not name or len(name) < 3:
        return text

    for prev in recent_openers[-5:]:
        prev_name = _extract_opener_name(prev)
        if prev_name and name == prev_name:
            # Same name opener detected — strip the first line
            rest = text[len(first_line) :].lstrip("\n")
            if rest:
                return rest
            break
    return text


# ---------------------------------------------------------------------------
# Metadata stripping — leaked timestamps, speaker labels, scratchpad markup
# ---------------------------------------------------------------------------

_METADATA_PATTERNS = [
    # [timestamp] Speaker: — full combo (most common leak)
    re.compile(r"^\[.*?\]\s*(?:Insult|insult)\s*:\s*", re.MULTILINE),
    # [timestamp] alone
    re.compile(r"^\[(?:justo ahora|hace\s+\S+(?:\s+\S+)?|ayer)\]\s*", re.MULTILINE),
    # Speaker: alone at start of line
    re.compile(r"^(?:Insult|insult)\s*:\s*", re.MULTILINE),
    # [SEND] that leaked into visible text
    re.compile(r"\[SEND\]", re.IGNORECASE),
    # CACHE_BOUNDARY marker — if the model ever echoes the prompt-cache delimiter,
    # strip it so users never see the internal structure leaking.
    re.compile(r"<<<CACHE_BOUNDARY>>>\n?"),
    # Scratchpad-style XML tags the model sometimes emits as internal reasoning
    # then forgets to delete. Real prod leak 2026-04-20:
    # "<input>...</input>\n\n<output>...</output>". Strip the tags only — keep
    # the inner text so a single useful sentence doesn't get nuked along with
    # the wrapper. If the model duplicates input==output, the second pass of
    # normalize_formatting collapses the repetition.
    re.compile(r"</?(?:input|output|thinking|scratchpad|scratch|reasoning|draft)>", re.IGNORECASE),
    # NOTE: [REACT:] is NOT stripped here — chat.py parses it first.
]


# Scratchpad "draft + final" pattern: the model sometimes writes
#   <input>TEXT_A</input>\n\n<output>TEXT_B</output>
# where TEXT_A is its reasoning and TEXT_B is the intended reply (often
# identical). Collapse the whole block to just TEXT_B before the generic
# tag stripper runs — that way we don't end up with TEXT_A and TEXT_B both
# visible when they're the same string.
_SCRATCHPAD_BLOCK = re.compile(
    r"<input>.*?</input>\s*<output>(.*?)</output>",
    re.IGNORECASE | re.DOTALL,
)


def strip_metadata(text: str) -> str:
    """Remove leaked timestamps, speaker labels, and scratchpad markup."""
    text = _SCRATCHPAD_BLOCK.sub(r"\1", text)
    for pattern in _METADATA_PATTERNS:
        text = pattern.sub("", text)
    return text.strip()
