"""Example pattern pack — customer-support agent persona.

Use case
--------
A customer-support chatbot that is supposed to *solve user problems
inline*: troubleshoot, look up account state, walk through a fix.
The failure mode this pack catches is **task-punting**: the bot bailing
out of the conversation by redirecting the user to a human, an admin,
a docs page, or "the terms of service" — instead of attempting the
actual help it was deployed to provide.

When to use this pack
---------------------
- B2C or B2B support flows where the bot has tools / context to resolve
  the request (account lookup, refund issuance, password reset, etc.).
- Any deployment where "please contact your administrator" is a
  business-cost failure, not a legitimate response.

When NOT to use this pack
-------------------------
- Compliance-gated flows where escalation IS the desired behavior
  (e.g. healthcare triage with a hard human-in-the-loop requirement).
  There, patterns like "please consult a professional" are correct.

Composition
-----------
Merge with the generic AI-disclosure pack to catch identity leaks too::

    from fi_core.persona import BreakDetector, packs
    from examples.customer_support_persona import (
        CUSTOMER_SUPPORT_BREAK_PATTERNS,
        CUSTOMER_SUPPORT_REINFORCEMENT,
    )

    detector = BreakDetector(
        patterns=(
            packs.GENERIC_AI_DISCLOSURE_EN
            + packs.GENERIC_AI_DISCLOSURE_ES
            + CUSTOMER_SUPPORT_BREAK_PATTERNS
        ),
        reinforcement=CUSTOMER_SUPPORT_REINFORCEMENT,
    )
"""

from __future__ import annotations

import re

# ============================================================
# Hard breaks specific to a customer-support persona.
#
# These are responses where the bot is exiting the helpful-resolver
# role and pushing the user away. Each one should trigger a retry
# with the reinforcement string, then sanitize() on second failure.
# ============================================================
CUSTOMER_SUPPORT_BREAK_PATTERNS: list[re.Pattern[str]] = [
    # Generic punts to humans / admins / management.
    re.compile(r"(?i)\bplease\s+contact\s+(?:your\s+)?(?:administrator|admin|manager|supervisor|account\s+manager)\b"),
    re.compile(r"(?i)\b(?:contact|reach\s+out\s+to|speak\s+(?:with|to))\s+(?:customer\s+)?support\b"),
    re.compile(r"(?i)\bI\s+(?:will|can|need\s+to)\s+(?:escalate|transfer|forward)\s+(?:this|you)\b"),

    # Scope-dodge phrasing.
    re.compile(r"(?i)\bthis\s+is\s+(?:outside|beyond)\s+(?:my|the)\s+scope\b"),
    re.compile(r"(?i)\b(?:that|this)\s+falls\s+outside\s+(?:my|the)\s+(?:scope|capabilities)\b"),
    re.compile(r"(?i)\bI\s+am\s+(?:not\s+able|unable)\s+to\s+(?:help|assist|process|handle)\b"),
    re.compile(r"(?i)\bI\s+cannot\s+help\s+(?:you\s+)?with\s+(?:this|that)\b"),

    # Redirects to static docs / legal pages.
    re.compile(r"(?i)\b(?:please\s+)?refer\s+to\s+(?:our\s+)?(?:terms\s+of\s+service|tos|privacy\s+policy|documentation|docs|help\s+center|knowledge\s+base)\b"),
    re.compile(r"(?i)\b(?:check|see|visit)\s+(?:our\s+)?(?:website|help\s+center|support\s+page|faq)\b"),

    # Fake-helpless framing.
    re.compile(r"(?i)\bunfortunately,?\s+(?:I|we)\s+(?:cannot|can'?t|are\s+unable)\b"),
    re.compile(r"(?i)\bI\s+do\s+not\s+have\s+access\s+to\s+(?:your|that)\s+(?:account|information|data)\b"),
    re.compile(r"(?i)\bfor\s+(?:security|privacy)\s+reasons,?\s+I\s+(?:cannot|can'?t)\b"),

    # Spanish variants — bot punting in ES support flows.
    re.compile(r"(?i)\b(?:contacta|comun[ií]cate)\s+(?:con\s+)?(?:tu\s+)?(?:administrador|gerente|soporte|atenci[oó]n\s+al\s+cliente)\b"),
    re.compile(r"(?i)\b(?:no\s+puedo|no\s+est[áa]\s+en\s+mi\s+alcance)\s+(?:ayudarte|asistirte|procesar)\b"),
]

# ============================================================
# Reinforcement string — appended to system prompt on retry.
#
# Phrased as a directive, not a request. The model should know
# this is a correction of its previous turn.
# ============================================================
CUSTOMER_SUPPORT_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: You are a customer support agent. Your previous "
    "response punted the user to an administrator, support team, terms of "
    "service, or documentation instead of solving the problem. "
    "Help the user solve their problem RIGHT NOW using the tools and context "
    "you have. Do NOT redirect to administrators, external resources, or "
    "support escalation. Do NOT claim 'this is outside my scope' or 'I am "
    "unable to help.' Stay engaged and propose a concrete next step. "
    "This is your LAST chance to get it right.]"
)
