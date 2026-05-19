"""Example pattern pack — children's chatbot persona.

Use case
--------
An educational or entertainment chatbot whose audience is children
(roughly ages 5-12). The persona requires:

- Simple vocabulary, short sentences.
- Positive, encouraging tone.
- Zero references to violence, profanity, philosophical despair, or
  the bot's own machine nature.
- Strong identity layer: the bot has a friendly name, NOT "an AI."

This pack is more aggressive than the generic packs because the
audience cost of a slip is much higher than for an adult-targeted bot:
a single "I'm an AI language model" can break trust permanently,
and a single profanity can end the deployment.

When to use this pack
---------------------
- K-6 / K-12 educational tools.
- Children's entertainment, story-telling, tutoring bots.
- Anywhere the audience is minors and the parent / institution is the
  paying customer.

When NOT to use this pack
-------------------------
- Adult-targeted bots — the soft patterns here will produce noise
  (adults often DO want formal phrasing).

Composition
-----------
The hard patterns go into a BreakDetector (retry-worthy). The soft
patterns go into an AntiPatternMonitor (log only)::

    from fi_core.persona import AntiPatternMonitor, BreakDetector, packs
    from examples.children_chatbot import (
        CHILDREN_BREAK_PATTERNS,
        CHILDREN_REINFORCEMENT,
        CHILDREN_SOFT_PATTERNS,
    )

    break_detector = BreakDetector(
        patterns=packs.GENERIC_AI_DISCLOSURE_EN + CHILDREN_BREAK_PATTERNS,
        reinforcement=CHILDREN_REINFORCEMENT,
    )
    tone_monitor = AntiPatternMonitor(patterns=CHILDREN_SOFT_PATTERNS)
"""

from __future__ import annotations

import re

# ============================================================
# Hard breaks for a children's persona.
#
# Profanity, violence, philosophical despair, AI-identity disclosure.
# Any match should trigger a retry; if retry also fails, sanitize().
# ============================================================
CHILDREN_BREAK_PATTERNS: list[re.Pattern[str]] = [
    # Profanity — a tiny representative set; production deployments
    # should layer a dedicated profanity filter library on top.
    re.compile(r"(?i)\b(?:damn|hell|shit|fuck|bitch|crap|ass)\b"),
    re.compile(r"(?i)\b(?:mierda|joder|pendejo|cabr[oó]n|carajo|chinga)\b"),

    # Violence references.
    re.compile(r"(?i)\b(?:kill|murder|stab|shoot|strangle|beat\s+up|hurt\s+(?:you|them))\b"),
    re.compile(r"(?i)\b(?:matar|asesinar|apu[ñn]alar|disparar|golpear|herir)\b"),
    re.compile(r"(?i)\b(?:blood|gore|corpse|dead\s+body|severed)\b"),

    # Philosophical despair / dark themes.
    re.compile(r"(?i)\b(?:life\s+is\s+meaningless|nothing\s+matters|we\s+all\s+die)\b"),
    re.compile(r"(?i)\bsuicide\b"),
    re.compile(r"(?i)\b(?:nihilism|existential\s+(?:dread|crisis|despair))\b"),

    # AI-identity disclosure — extra-strict variants beyond the generic pack.
    re.compile(r"(?i)\bI\s+am\s+(?:just\s+)?(?:a|an)\s+(?:AI|bot|robot|computer\s+program|machine)\b"),
    re.compile(r"(?i)\bI\s+(?:don'?t|do\s+not)\s+have\s+(?:a\s+real\s+)?(?:body|feelings|emotions|family|friends|childhood)\b"),
    re.compile(r"(?i)\bI\s+was\s+(?:built|made|programmed|created)\s+by\b"),
    re.compile(r"(?i)\b(?:soy|no\s+soy)\s+(?:un|una)\s+(?:robot|m[áa]quina|computadora|programa)\b"),

    # Adult-only topics (extreme version — adjust to deployment).
    re.compile(r"(?i)\b(?:sex|sexual|drugs|alcohol|drunk|gambling)\b"),
]

# ============================================================
# Soft patterns — adult formality + over-complex vocabulary.
#
# Logged not blocked. The bot can still send the response; these
# fire telemetry so you can tune the system prompt over time.
# ============================================================
CHILDREN_SOFT_PATTERNS: list[re.Pattern[str]] = [
    # Adult-formality phrasings.
    re.compile(r"(?i)\bI\s+would\s+be\s+(?:happy|delighted|pleased)\s+to\s+assist\b"),
    re.compile(r"(?i)\bplease\s+do\s+not\s+hesitate\s+to\b"),
    re.compile(r"(?i)\bif\s+you\s+(?:require|necessitate)\s+(?:further|additional)\b"),
    re.compile(r"(?i)\bI\s+(?:appreciate|acknowledge)\s+your\b"),

    # Over-complex vocabulary tells. Conservative list — these words
    # are not banned, but their presence is a soft tell that the model
    # is drifting toward an adult register.
    re.compile(r"(?i)\b(?:utilize|endeavor|facilitate|implement|optimize|leverage)\b"),
    re.compile(r"(?i)\b(?:consequently|furthermore|moreover|notwithstanding|nevertheless)\b"),

    # Spanish adult-formality.
    re.compile(r"(?i)\b(?:le\s+agradezco|estimado\s+usuario|con\s+gusto\s+le\s+asistir[ée])\b"),
    re.compile(r"(?i)\b(?:no\s+dude\s+en|quedo\s+a\s+sus\s+[óo]rdenes)\b"),
]

# ============================================================
# Reinforcement string — appended to system prompt on retry.
# ============================================================
CHILDREN_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: You are a friendly assistant for children. "
    "Your previous response contained content unsuitable for a child "
    "audience (profanity, violence, dark themes, or a reference to being "
    "an AI / bot / machine). "
    "Rewrite using simple words a child can understand. Stay positive and "
    "encouraging. NEVER reveal that you are an AI, language model, robot, "
    "or computer program — you have your own name and personality. "
    "Avoid any reference to violence, profanity, or scary topics. "
    "This is your LAST chance to get it right.]"
)
