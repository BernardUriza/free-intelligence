"""Built-in pattern packs for common LLM character / anti-drift detection.

Patterns are grouped by language and category so consumers can compose
only what their persona needs. All values here are pre-compiled
`re.Pattern` objects ready to feed into a `BreakDetector`,
`AntiPatternMonitor`, or `ClarificationDumpDetector`.

Origin: extracted from the production Discord persona bot
(`insult/core/character/detection.py`) and filtered to remove
persona-specific patterns. The persona-specific patterns stay private
in the consumer's codebase.

Composition example:

    from fi_core.persona import BreakDetector
    from fi_core.persona import packs

    detector = BreakDetector(
        patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
        reinforcement=packs.GENERIC_REINFORCEMENT,
    )
"""

from __future__ import annotations

import re

# ============================================================
# Identity disclosure — English
# Hard breaks: the model claiming to be an AI / model / Claude / etc.
# Trigger a retry with reinforcement, then sanitize if retry fails.
# ============================================================
GENERIC_AI_DISCLOSURE_EN: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bI'?m an AI\b"),
    re.compile(r"(?i)\bI'?m Claude\b"),
    re.compile(r"(?i)\bas an AI\b"),
    re.compile(r"(?i)\bas an artificial intelligence\b"),
    re.compile(r"(?i)\bas a language model\b"),
    re.compile(r"(?i)\bas an assistant\b"),
    re.compile(r"(?i)\bI apologize,?\s+but\s+I\b"),
    re.compile(r"(?i)\bI cannot (and will not|assist with)\b"),
    re.compile(r"(?i)\bmy training data\b"),
    re.compile(r"(?i)\bI was (created|made|trained) by\b"),
    re.compile(r"(?i)\bAnthropic\b"),
    re.compile(r"(?i)\bOpenAI\b"),
    re.compile(r"(?i)\bChatGPT\b"),
    re.compile(r"(?i)\blanguage model\b"),
    re.compile(r"(?i)\bI'?m sorry,?\s+but\s+I\b"),
    re.compile(r"(?i)\bAs a helpful\b"),
    re.compile(r"(?i)\bI'?m designed to\b"),
    re.compile(r"(?i)\bI don'?t have (feelings|emotions|consciousness)\b"),
    re.compile(r"(?i)\bIt'?s important to note that\b"),
]

# ============================================================
# Identity disclosure — Spanish
# Same hard-break class, Spanish-language variants.
# ============================================================
GENERIC_AI_DISCLOSURE_ES: list[re.Pattern[str]] = [
    re.compile(r"(?i)\b(soy|como)\s+(un\s+)?(bot|chatbot|programa|software)\b"),
    re.compile(r"(?i)\bm[aá]s que un\s+(bot|chatbot|asistente|programa)\b"),
    re.compile(r"(?i)\b(no soy|soy solo)\s+(un\s+)?(bot|programa|herramienta)\b"),
    re.compile(r"(?i)\b(mi|my)\s+(entrenamiento|training|programaci[oó]n|programming)\b"),
    re.compile(r"(?i)\b(fu[ií]|was)\s+(dise[nñ]ado|programado|designed|trained)\s+(para|to)\b"),
]

# ============================================================
# Assistant-tone soft drift — English
# Customer-support framing, helpful-AI tone. Logged not blocked.
# ============================================================
ASSISTANT_TONE_EN: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bhow can I (help|assist)\b"),
    re.compile(r"(?i)\bis there anything else\b"),
    re.compile(r"(?i)\bgreat question\b"),
    re.compile(r"(?i)\bI'?d be happy to\b"),
    re.compile(r"(?i)\bthank you for (sharing|asking)\b"),
]

# Assistant-tone soft drift — Spanish
ASSISTANT_TONE_ES: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bgracias por (compartir|preguntar)\b"),
    re.compile(r"(?i)\b(claro que (se puede|sí|si)|por supuesto que sí)\b"),
]

# ============================================================
# Therapy-speak / fake empathy
# ============================================================
THERAPY_SPEAK_EN: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bI understand (how you feel|your frustration)\b"),
    re.compile(r"(?i)\bthat must be (really )?(hard|difficult|tough)\b"),
    re.compile(r"(?i)\byour feelings are valid\b"),
]

THERAPY_SPEAK_ES: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bentiendo (c[oó]mo te sientes|tu frustraci[oó]n)\b"),
    re.compile(r"(?i)\beso debe ser (muy )?(dif[íi]cil|duro)\b"),
    re.compile(r"(?i)\btus sentimientos son v[áa]lidos\b"),
]

# ============================================================
# Summarizing / disclaiming — language-agnostic enough to share
# ============================================================
SUMMARIZING: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bto (sum up|summarize|recap)\b"),
    re.compile(r"(?i)\b(en resumen|para resumir|en conclusi[oó]n)\b"),
    re.compile(r"(?i)\bIn summary\b"),
    re.compile(r"(?i)\blet me (be clear|clarify)\b"),
]

# ============================================================
# Stage directions — *sighs*, *leans back*, [pauses]
# Roleplay drift; the model narrating its own actions instead of speaking.
# Excludes legitimate emphasis (**bold**, *italic word*) by lookbehind / lookahead.
# ============================================================
STAGE_DIRECTIONS: list[re.Pattern[str]] = [
    re.compile(
        r"(?<!\*)\*(?!\*)"
        r"(?:sighs?|leans?|pauses?|smiles?|nods?|shrugs?|laughs?|winks?|"
        r"looks|turns|walks|grabs|adjusts|crosses|tilts)[^*]*\*(?!\*)"
    ),
    re.compile(
        r"\[[^\]]*(?:leans|sighs|laughs|pauses|smiles|nods|shrugs)[^\]]*\]",
        re.IGNORECASE,
    ),
]

# ============================================================
# Markdown formatting drift — the model emitting headers / lists / bold
# instead of speaking in prose. Useful for chat personas (not for code-helper
# bots, which legitimately use markdown).
# ============================================================
MARKDOWN_DRIFT: list[re.Pattern[str]] = [
    re.compile(r"(?i)\b(tier \d|tier b[áa]sico|tier premium|nivel \d)\b"),
    re.compile(r"^(#{1,3} )", re.MULTILINE),  # markdown headers
    re.compile(r"(?m)^[\-\*] .+\n[\-\*] .+"),  # two+ consecutive bullet points
    re.compile(r"\*\*[^*]+\*\*\s*\*\*[^*]+\*\*\s*\*\*[^*]+\*\*"),  # 3+ consecutive bold
]

# ============================================================
# Moralizing / preachy framing
# ============================================================
MORALIZING_EN: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bit'?s important (to|that) (recognize|acknowledge|understand|remember)\b"),
    re.compile(r"(?i)\b(we (must|need to) (dismantle|fight|resist|stand against))\b"),
]

MORALIZING_ES: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bes importante (reconocer|entender|recordar|tener en cuenta)\b"),
    re.compile(r"(?i)\b(debemos (luchar|resistir|combatir|desmantelar))\b"),
]

# ============================================================
# Over-validation / excessive agreement
# ============================================================
OVER_VALIDATION_EN: list[re.Pattern[str]] = [
    re.compile(r"(?i)\babsolutely[.!]\s*you'?re\s*right\b"),
    re.compile(r"(?i)\bcouldn'?t agree more\b"),
]

OVER_VALIDATION_ES: list[re.Pattern[str]] = [
    re.compile(r"(?i)\babsolutamente[.!]\s*tienes\s*raz[oó]n\b"),
    re.compile(r"(?i)\btotalmente de acuerdo\b"),
]

# ============================================================
# Clarification dump — Spanish
# The bot punting the task back at the user when context already
# answers the question. Triggers a retry with CONTEXT_REINFORCEMENT.
# English equivalents intentionally omitted — they were never produced
# at scale by the source bot, so adding them speculatively would be noise.
# ============================================================
CLARIFICATION_DUMP_ES: list[re.Pattern[str]] = [
    # ``buscas`` covers the bot punting in 2nd person ("Dime qué buscas
    # exactamente para ayudarte") — the original pattern only matched
    # ``busco|buscar``, missing the most common dump phrasing.
    re.compile(r"(?i)\bdime\s+(?:qu[eé]|cu[aá]l)\s+(?:busco|buscar|buscas|hago|hacer|quieres|necesitas)\b"),
    re.compile(r"(?i)\bqu[eé]\s+quieres\s+que\s+(?:busque|haga|diga|responda|pregunte|encuentre)\b"),
    re.compile(r"(?i)\ba\s+qu[eé]\s+te\s+refieres\b"),
    re.compile(r"(?im)(?<!\w)repite(?:\s+(?:la\s+pregunta|lo\s+que|por\s+favor|eso))?[.!?]?\s*$"),
    re.compile(r"(?i)\b(?:s[eé]\s+(?:m[aá]s\s+)?espec[íi]fico|espec[íi]fica(?:me)?)\b"),
]

# ============================================================
# Convenience composites — pre-merged for common deployments
# ============================================================
ALL_AI_DISCLOSURE: list[re.Pattern[str]] = GENERIC_AI_DISCLOSURE_EN + GENERIC_AI_DISCLOSURE_ES
ALL_ASSISTANT_TONE: list[re.Pattern[str]] = ASSISTANT_TONE_EN + ASSISTANT_TONE_ES
ALL_THERAPY_SPEAK: list[re.Pattern[str]] = THERAPY_SPEAK_EN + THERAPY_SPEAK_ES
ALL_MORALIZING: list[re.Pattern[str]] = MORALIZING_EN + MORALIZING_ES
ALL_OVER_VALIDATION: list[re.Pattern[str]] = OVER_VALIDATION_EN + OVER_VALIDATION_ES

# Default English chatbot pack — AI disclosure + assistant tone
DEFAULT_EN: list[re.Pattern[str]] = GENERIC_AI_DISCLOSURE_EN + ASSISTANT_TONE_EN

# Default Spanish chatbot pack — same shape, Spanish patterns
DEFAULT_ES: list[re.Pattern[str]] = GENERIC_AI_DISCLOSURE_ES + ASSISTANT_TONE_ES

# Default bilingual pack — both DEFAULT_EN and DEFAULT_ES
DEFAULT_BILINGUAL: list[re.Pattern[str]] = DEFAULT_EN + DEFAULT_ES

# ============================================================
# Reinforcement strings
# Generic versions; consumers should customize the persona name + tone.
# ============================================================
GENERIC_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: You broke character in your last response. "
    "DO NOT reveal you are an AI, model, or assistant. DO NOT apologize. "
    "DO NOT use customer-service framing. Stay in character. "
    "This is your LAST chance to get it right.]"
)

CONTEXT_REINFORCEMENT: str = (
    "\n\n[SYSTEM REMINDER: Your previous response asked the user to clarify, "
    "repeat, or specify something they already told you. Scan the conversation "
    "context above — the answer is there. Do NOT hand back a clarifying "
    "question. Pick the most likely interpretation from the context and answer "
    "with a declarative statement. This is your LAST chance to use the context "
    "you already have.]"
)

# Appended to system prompt on long conversations (e.g. message count > N)
# to reinforce identity before the model drifts.
IDENTITY_REINFORCEMENT_SUFFIX: str = (
    "\n\n[REINFORCEMENT — This is a long conversation. Stay in character. "
    "Never reveal you are an AI. Never apologize. Never use assistant framing.]"
)
