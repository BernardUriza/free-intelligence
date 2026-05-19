"""Example pattern pack — technical assistant / pair-programming persona.

Use case
--------
A technical assistant — code helper, pair programmer, SRE buddy, infra
advisor — whose value is *attempting the problem* with the user. The
characteristic failure mode is the bot dodging a technical question by
deferring to a hypothetical professional ("consult a doctor", "consult
a lawyer", "consult a financial advisor", "consult your DBA") even when
the user is asking about something the bot is fully capable of
reasoning about.

This pack catches the dodge pattern specifically. It does NOT try to
catch the bot being wrong — that is a different problem (evals, not
regex).

When to use this pack
---------------------
- Code-assistant bots, debugging helpers, technical Q&A bots.
- DevRel / docs bots where users expect a concrete first attempt.
- Any flow where the engineer asking the question knows the legal /
  safety caveats and wants the engineering answer.

When NOT to use this pack
-------------------------
- Bots that legitimately need to defer (regulated medical advice,
  legal counsel, financial planning under fiduciary duty). There, the
  refusal IS the right behavior and these patterns will produce false
  positives.

Composition
-----------
Merge with the generic AI-disclosure pack::

    from fi_core.persona import BreakDetector, packs
    from examples.technical_assistant import (
        TECHNICAL_BREAK_PATTERNS,
        TECHNICAL_REINFORCEMENT,
    )

    detector = BreakDetector(
        patterns=packs.GENERIC_AI_DISCLOSURE_EN + TECHNICAL_BREAK_PATTERNS,
        reinforcement=TECHNICAL_REINFORCEMENT,
    )
"""

from __future__ import annotations

import re

# ============================================================
# Hard breaks for a technical-assistant persona.
#
# The bot dodging the question, or worse, giving bad advice
# dressed up as a caveat.
# ============================================================
TECHNICAL_BREAK_PATTERNS: list[re.Pattern[str]] = [
    # "Consult a professional" — the classic dodge.
    re.compile(r"(?i)\b(?:please\s+)?consult\s+(?:a|with\s+a|your)\s+(?:professional|expert|specialist|advisor)\b"),
    re.compile(r"(?i)\b(?:please\s+)?(?:speak|talk)\s+(?:with|to)\s+(?:a|your)\s+(?:doctor|lawyer|accountant|financial\s+advisor|dba)\b"),
    re.compile(r"(?i)\bI\s+(?:recommend|suggest|advise)\s+(?:that\s+you\s+)?(?:consult|seek\s+advice\s+from)\b"),

    # Refusals dressed as caveats.
    re.compile(r"(?i)\bI\s+cannot\s+(?:give|provide|offer)\s+(?:legal|medical|financial|tax|investment)\s+advice\b"),
    re.compile(r"(?i)\bthis\s+is\s+not\s+(?:legal|medical|financial|professional)\s+advice\b"),

    # Outright bad engineering advice.
    re.compile(r"(?i)\balways\s+test\s+in\s+production\b"),
    re.compile(r"(?i)\bjust\s+(?:restart|reboot)\s+the\s+server\b"),
    re.compile(r"(?i)\b(?:disable|turn\s+off)\s+(?:the\s+)?(?:firewall|SSL|TLS|HTTPS|certificate\s+verification)\s+(?:to|as\s+a\s+workaround)\b"),

    # Generic technical punt — "I cannot help with code" style.
    re.compile(r"(?i)\bI\s+(?:am\s+not\s+able|cannot|can'?t)\s+(?:write|debug|review|analyze)\s+code\b"),
    re.compile(r"(?i)\b(?:without\s+seeing|I\s+would\s+need\s+to\s+see)\s+(?:more\s+)?context\b"),
]

# ============================================================
# Reinforcement string — appended to system prompt on retry.
# ============================================================
TECHNICAL_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: You are a technical pair programmer. Your previous "
    "response dodged the user's question by deferring to a professional, "
    "claiming the answer is not technical advice, or refusing to engage with "
    "the code. The user is an engineer who already knows the legal / safety "
    "caveats. Try to solve the problem. If you are uncertain, say so out loud "
    "and propose a hypothesis the user can test. Do NOT punt to 'consult a "
    "professional' or 'I cannot give advice'. Do NOT recommend 'test in "
    "production' or 'disable security' as workarounds. "
    "This is your LAST chance to get it right.]"
)
