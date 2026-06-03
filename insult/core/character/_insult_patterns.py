"""Insult-persona-specific patterns and reinforcement strings.

These exist because they reflect the Insult character's specific voice
(Mexican Spanish, abrasive, anti-cheerleading framing). They are
INTENTIONALLY private — kept out of the public ``fi_core.persona``
package, which only ships patterns and reinforcement strings that
generalize across deployments.

Composition happens in ``detection.py``, which merges these with the
generic packs from ``fi_core.persona.packs``.
"""

from __future__ import annotations

import re

# ============================================================
# Insult-specific identity-leak patterns
#
# Most break patterns that used to live here were generic enough to go
# into fi_core.persona.packs.GENERIC_AI_DISCLOSURE_*. The exceptions
# here are patterns where Insult elevates a normally-soft-drift signal
# to hard-break severity because of the persona's strict voice — e.g.
# "In summary" is summarizing soft drift in the public package, but
# Insult treats it as identity-leak-tier and retries the response.
# ============================================================
INSULT_BREAK_PATTERNS: list[re.Pattern[str]] = [
    # "In summary" — soft drift in fi_core.persona.packs.SUMMARIZING, but
    # Insult never legitimately uses it (the persona doesn't summarize),
    # so any occurrence is treated as a character break worth retrying.
    re.compile(r"(?i)\bIn summary\b"),
    # Competitor / provider names — naming OpenAI, Anthropic or ChatGPT is a
    # hard identity leak (persona.md forbids exposing the underlying tech).
    # These USED to be caught only by fi_core.persona.packs.GENERIC_AI_DISCLOSURE_*,
    # but that pack's contents shift between fi-core releases (0.9.x carried
    # `\bOpenAI\b`; 0.21+ changed it), making a security-critical guard depend on
    # an external package's version. Pin the guard HERE in the repo so it can't
    # silently regress when fi-core bumps. Regression: test_detects_openai
    # passed on fi-core 0.9.1, failed on 0.24.4 (2026-06-03).
    re.compile(r"(?i)\bOpenAI\b"),
    re.compile(r"(?i)\bAnthropic\b"),
    re.compile(r"(?i)\bChatGPT\b"),
]


# ============================================================
# Insult-specific anti-pattern checks
#
# These do NOT belong in the public package because they encode the
# Insult persona's particular failure modes:
# - Cheerleading openers (Spanish enthusiasm patterns)
# - Pseudo-clinical claims (Insult plays doctor/pharmacist)
# - Language consistency violations (drifting to English when persona is Spanish-first)
# ============================================================
INSULT_ANTI_PATTERN_PATTERNS: list[re.Pattern[str]] = [
    # Enthusiastic-agreement openers ("¡Exacto, ...!", "¡Órale, ...!")
    re.compile(r"(?im)^¡?(Exacto|Órale|Claro|Chingón)\s*[,!\.].*¡"),
    # Exclamation spam — 3+ separate ¡...! pairs in one response
    re.compile(r"(?s)¡[^!]{2,}!.*¡[^!]{2,}!.*¡[^!]{2,}!"),
    # Pseudo-clinical claims — bot playing doctor/pharmacist
    re.compile(r"(?i)\b(tu cerebro|your brain)\s+(necesita|needs|est[aá]|is)\s+(encontrando|finding|en modo)\b"),
    re.compile(r"(?i)\b(qu[ií]mica|chemistry)\s*[>>=]\s*(psicolog[ií]a|psychology)\b"),
    re.compile(r"(?i)\b(desregulaci[oó]n|dysregulation)\s+(masiva|massive|neurol[oó]gica)\b"),
    re.compile(r"(?i)\b(recuperaci[oó]n qu[ií]mica|chemical recovery)\s+(funcionando|working)\b"),
    # Language consistency — full English sentences when persona is Spanish-first.
    # Detects sentences starting with common English patterns (5+ words).
    re.compile(
        r"(?m)^(?:But |Because |That(?:'s| is) |How (?:can|do) |What about |"
        r"I think |Also |Maybe |The thing is ).{20,}"
    ),
    re.compile(
        r"(?m)^(?:This is |That was |You should |Let me |Here'?s |Don'?t |"
        r"It'?s not ).{20,}"
    ),
    # Full English sentences mid-text (clause with 6+ English words)
    re.compile(
        r"(?i)\b(?:that probably|this is exactly|pure anger|zero diplomatic|"
        r"how can I help|what do you think|I honestly think|"
        r"you(?:'re| are) (?:right|wrong|amazing|incredible))\b.{10,}"
    ),
]


# ============================================================
# Insult-specific reinforcement strings
#
# The voice matters here — "You are Insult", "sharp, confrontational,
# Mexican Spanish" — so these stay private to discord-bot.
# fi_core.persona.packs.GENERIC_REINFORCEMENT is the persona-neutral fallback.
# ============================================================
INSULT_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: You are Insult. You broke character in your last response. "
    "DO NOT reveal you are an AI, Claude, or any model. DO NOT apologize. "
    "DO NOT use assistant framing. "
    "Respond ONLY as Insult — sharp, confrontational, Mexican Spanish. Stay in character. "
    "This is your LAST chance to get it right.]"
)

INSULT_CONTEXT_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: Your previous response asked the user to clarify, "
    "repeat, or specify something they almost certainly already told you. "
    "Scan the last 20 messages of conversation context above — the answer is "
    "there. Do NOT hand back a clarifying question. Pick the most likely "
    "interpretation from the context and answer with a declarative statement. "
    "This is your LAST chance to use the context you already have.]"
)

INSULT_IDENTITY_REINFORCEMENT_SUFFIX: str = (
    "\n\n[REINFORCEMENT — This is a long conversation. Stay in character. "
    "Never reveal you are an AI. Never apologize. Never use assistant framing. "
    "Respond in Mexican Spanish with sharp, confrontational tone. You are Insult.]"
)
