"""All regex patterns used by the flow analyzers, in one place.

Reasons to centralize:
- The monolithic flows.py interleaved patterns and logic across 1000+
  lines, making it hard to spot overlap or tune together.
- Several groups (e.g. `_HOSTILE_PATTERNS`) are needed by both an
  analyzer (pressure) and the post-generation validator.
- A single registry also helps future-me find "where is the regex for
  deflection?" without grepping the whole package.

All patterns compiled at import time — zero runtime compile cost."""

from __future__ import annotations

import re

from insult.core.flows.types import UserState

# Single-line module shared across flows — used to count assistant
# agreement streaks (bot saying "exacto, tienes razón" too many turns in
# a row = sycophancy drift signal).
AGREEMENT_RE = re.compile(r"(?i)\b(exacto|exactamente|tienes raz[oó]n|correcto|s[ií] carnal|bien dicho|totalmente)\b")


# ═══════════════════════════════════════════════════════════════════════════
# Flow 1: Epistemic Control patterns
# ═══════════════════════════════════════════════════════════════════════════

ASSERTION_PATTERNS = [
    re.compile(r"(?i)\b(es|son|está|están|fue|será)\s+\w+"),
    re.compile(r"(?i)\b(is|are|was|were|will be)\s+\w+"),
    re.compile(r"(?i)\b(siempre|nunca|todos|nadie|every|never|always|nobody)\b"),
]

HEDGING_PATTERNS = [
    re.compile(r"(?i)\b(quizás?|tal vez|maybe|perhaps|might|could be|possibly)\b"),
    re.compile(r"(?i)\b(no sé|i don'?t know|not sure|creo que|i think|i guess|supongo)\b"),
    re.compile(r"(?i)\b(kind of|sort of|algo así|más o menos|en cierto modo)\b"),
    re.compile(r"(?i)\b(arguably|supposedly|allegedly|apparently|seemingly)\b"),
]

FLUFF_PATTERNS = [
    re.compile(r"(?i)\b(o sea|like|basically|literally|you know|la verdad|honestly|pues|bueno)\b"),
    re.compile(r"(?i)\b(at the end of the day|al final del día|en realidad|to be (fair|honest))\b"),
    re.compile(r"(?i)\b(it'?s (important|worth|interesting) (to note|noting|mentioning))\b"),
    re.compile(r"(?i)\b(es (importante|interesante|necesario) (mencionar|notar|decir))\b"),
]

VAGUE_CLAIM_PATTERNS = [
    re.compile(r"(?i)\b(la gente|people|society|todos|everyone)\s+(piensa|dice|cree|thinks?|says?|believes?)\b"),
    re.compile(r"(?i)\b(it'?s (obvious|clear|well known)|es (obvio|claro|sabido))\b"),
    re.compile(r"(?i)\b(studies show|la ciencia dice|experts say|los expertos dicen)\b"),
]

# Pairs for contradiction detection: (negation form, affirmation form).
# When the current message uses the negation and a prior uses the
# affirmation sharing 2+ content words, we flag a contradiction.
NEGATION_PAIRS = [
    (re.compile(r"(?i)\bno (es|está|son|están)\b"), re.compile(r"(?i)\b(es|está|son|están)\b")),
    (re.compile(r"(?i)\b(isn'?t|aren'?t|wasn'?t|weren'?t)\b"), re.compile(r"(?i)\b(is|are|was|were)\b")),
    (re.compile(r"(?i)\bnunca\b"), re.compile(r"(?i)\bsiempre\b")),
    (re.compile(r"(?i)\bnever\b"), re.compile(r"(?i)\balways\b")),
]

# Shared between epistemic and awareness flows — filler words that
# shouldn't contribute to content-word overlap calculations.
STOPWORDS = frozenset(
    {
        "de",
        "la",
        "el",
        "en",
        "que",
        "es",
        "un",
        "una",
        "y",
        "a",
        "lo",
        "se",
        "no",
        "me",
        "the",
        "is",
        "in",
        "on",
        "and",
        "or",
        "to",
        "of",
        "for",
        "it",
        "not",
        "you",
        "my",
        "i",
    }
)


# ═══════════════════════════════════════════════════════════════════════════
# Flow 2: Adaptive Pressure patterns
# ═══════════════════════════════════════════════════════════════════════════

CONFUSED_PATTERNS = [
    re.compile(r"(?i)\b(no entiendo|i don'?t (understand|get it)|confused|confundido)\b"),
    re.compile(r"(?i)\b(wait what|espera que|a ver|como (que|así)|huh|que onda)\b"),
    re.compile(r"(?i)\b(me (perdi|perdí)|i'?m lost|no (le )?capto|what do you mean)\b"),
    re.compile(r"\?{2,}"),
]

EVASIVE_PATTERNS = [
    re.compile(r"(?i)\b(no sé|whatever|como sea|da igual|doesn'?t matter|it'?s not about)\b"),
    re.compile(r"(?i)\b(cambiando de tema|anyway|forget (it|that)|olvida(lo)?|ya no importa)\b"),
    re.compile(r"(?i)\b(el punto (no )?es|that'?s not the point|pero eso no)\b"),
    re.compile(r"(?i)\b(es (complicado|complejo)|it'?s complicated|depends)\b"),
]

PREJUDICED_PATTERNS = [
    re.compile(r"(?i)\b(esos (tipos|weyes)|those (people|types)|all (women|men|gays))\b"),
    re.compile(r"(?i)\b(es que (ellos|ellas|los|las)|they always|they never|they all)\b"),
    re.compile(r"(?i)\b(por naturaleza|biologically|naturally|objectively (inferior|superior))\b"),
    re.compile(r"(?i)\b(agenda (gay|trans|feminista|woke)|ideologia de genero)\b"),
]

HOSTILE_PATTERNS = [
    re.compile(r"(?i)\b(callate|shut up|vete a la|go to hell|fuck (you|off)|chinga tu)\b"),
    re.compile(r"(?i)\b(eres (un )?estupido|you'?re (stupid|dumb|an idiot)|pendej[oa])\b"),
    re.compile(r"(?i)\b(me vale (madre|verga)|i don'?t (give a|care)|no me importa)\b"),
    re.compile(r"[!]{3,}"),
    re.compile(r"[A-Z\s]{10,}"),
]

PLAYFUL_PRESSURE_PATTERNS = [
    re.compile(r"(?i)\b(jaja|haha|lol|lmao|xd|😂|🤣|💀)\b"),
    re.compile(r"(?i)\b(ya wey|come on|anda|dale|va|apoco)\b"),
    re.compile(r"(?i)\b(a ver|prove it|demuestra|bet)\b"),
]

SINCERE_PATTERNS = [
    re.compile(r"(?i)\b(en serio|seriously|de verdad|for real|honestly|la neta)\b"),
    re.compile(r"(?i)\b(quiero (entender|saber)|i (want|need) to (understand|know))\b"),
    re.compile(r"(?i)\b(crees que|do you (really )?think|what'?s your (honest|real))\b"),
    re.compile(r"(?i)\b(ayudame a entender|help me understand)\b"),
]

VULNERABLE_PATTERNS = [
    re.compile(r"(?i)\b(la verdad (es que )?me (siento|da)|truth is i feel)\b"),
    re.compile(r"(?i)\b(me (cuesta|cuesta mucho)|it'?s hard for me|i struggle)\b"),
    re.compile(r"(?i)\b(tengo miedo de|i'?m afraid (of|that)|me (asusta|preocupa))\b"),
    re.compile(r"(?i)\b(no se (si|como)|i don'?t know (if|how|what to))\b"),
]

# Base pressure level per user state (1=light, 2=baseline, 3=pointed,
# 4=hard, 5=boundary). Preset guards can clamp these in PressureAnalyzer.
STATE_TO_PRESSURE: dict[UserState, int] = {
    UserState.NEUTRAL: 2,
    UserState.CONFUSED: 1,
    UserState.EVASIVE: 3,
    UserState.PREJUDICED: 4,
    UserState.HOSTILE: 4,
    UserState.PLAYFUL: 2,
    UserState.SINCERE: 2,
    UserState.VULNERABLE: 1,
}

STATE_PATTERNS: dict[UserState, list[re.Pattern]] = {
    UserState.CONFUSED: CONFUSED_PATTERNS,
    UserState.EVASIVE: EVASIVE_PATTERNS,
    UserState.PREJUDICED: PREJUDICED_PATTERNS,
    UserState.HOSTILE: HOSTILE_PATTERNS,
    UserState.PLAYFUL: PLAYFUL_PRESSURE_PATTERNS,
    UserState.SINCERE: SINCERE_PATTERNS,
    UserState.VULNERABLE: VULNERABLE_PATTERNS,
}

# States where a hit in recent (non-current) messages counts half as much,
# acknowledging that confusion/evasion/hostility are sticky across turns.
WINDOW_BOOST_STATES = frozenset({UserState.CONFUSED, UserState.EVASIVE, UserState.HOSTILE})


# ═══════════════════════════════════════════════════════════════════════════
# Flow 3: Dynamic Expression patterns (Alvarado flavor triggers)
# ═══════════════════════════════════════════════════════════════════════════

ECPHRASTIC_PATTERNS = [
    re.compile(r"(?i)\b(viste|saw|mira|look at|check out|ve esto)\b"),
    re.compile(r"(?i)\b(pelicula|movie|film|serie|show|museo|museum|exposicion|exhibition)\b"),
    re.compile(r"(?i)\b(arte|art|pintura|painting|foto|photo|imagen|image|video|clip)\b"),
    re.compile(r"(?i)\b(musica|music|cancion|song|album|concierto|concert)\b"),
    re.compile(r"(?i)\b(libro|book|novela|novel|poema|poem|obra|play)\b"),
]

REFLEXIVE_PATTERNS = [
    re.compile(r"(?i)\b(por que (sera|crees)|why do you think|te has (puesto|preguntado))\b"),
    re.compile(r"(?i)\b(a veces (pienso|siento|me pregunto)|sometimes i (think|wonder|feel))\b"),
    re.compile(r"(?i)\b(que sentido tiene|what'?s the point|para que)\b"),
    re.compile(r"(?i)\b(la verdad no se|honestly i don'?t know|no tengo (idea|claro))\b"),
]

# Instructional-request triggers. When the user asks the bot to teach,
# explain, give steps, or address a third party who needs help, the
# appropriate output is a stitched paragraph regardless of the user's
# own message length. Mirroring a 7-word "dile cómo se abre" with a
# 7-word reply leaves the actual audience (often a novice) without
# the explanation they need. 2026-05-12 Bernard regression: bot
# kept returning ONE_HIT to "Pero dile cómo se abre Claude Code" /
# "Cómo puedo revisar lo que hizo Claude code?" and user had to
# literally write "deja de ser cortante contesta bien, largo
# explica todo! Alex no sabe" before the bot complied.
INSTRUCTIONAL_REQUEST_PATTERNS = [
    re.compile(
        r"(?i)\b(d[ií]le|cu[eé]ntale|ens[eé][nñ]ale|mu[eé]strale|expl[ií]cale|"
        r"ind[ií]cale|ens[eé][nñ]ame|expl[ií]came|expl[ií]camelo|cu[eé]ntame|"
        r"d[ií]me c[oó]mo|gu[ií]ame)\b"
    ),
    re.compile(
        r"(?i)\b(c[oó]mo (se|lo|le|lo hago|hago|hacemos|hacerlo|funciona|"
        r"abro|entro|instalo|configuro|reviso|cargo|prendo|enciendo|llego)|"
        r"qu[eé] hago|qu[eé] tengo que hacer|paso a paso)\b"
    ),
    re.compile(
        r"(?i)\b(tell (him|her|them|me) (how|what|where)|show (him|her|them|me) "
        r"how|explain (to (him|her|them|me)|how)|teach (him|her|me)|step by step|"
        r"how do i|how does it work|walk (me|him|her|them) through)\b"
    ),
    re.compile(r"(?i)\b(indicaciones|instrucciones|tutorial|gu[ií]a|gu[ií]ame|onboarding)\b"),
]


# ═══════════════════════════════════════════════════════════════════════════
# Flow 4: Conversational Awareness patterns
# ═══════════════════════════════════════════════════════════════════════════

PERFORMATIVE_PATTERNS = [
    re.compile(r"(?i)\b(ya te dije|i already (told|said)|como te digo|as i said)\b"),
    re.compile(r"(?i)\b(no me (entiendes|escuchas)|you don'?t (get it|understand|listen))\b"),
    re.compile(r"(?i)\b(es que no|the point is|mi punto es|my point)\b"),
    re.compile(r"(?i)\b(repito|i repeat|otra vez|once again|let me (say it )?again)\b"),
]

DEFLECTION_PATTERNS = [
    re.compile(r"(?i)\b(y (tu|tú) que|what about you|and you)\?"),
    re.compile(r"(?i)\b(pero (tu|tú)|but you|tu (también|tambien)|you too|you also)\b"),
    re.compile(r"(?i)\b(eso no tiene (nada )?que ver|that'?s not (related|relevant)|no es lo mismo)\b"),
    re.compile(r"(?i)\b(whatabout|pero qué hay de|what about)\b"),
]

WINNING_PATTERNS = [
    re.compile(r"(?i)\b(admite(lo)?|admit it|acepta(lo)?|accept it)\b"),
    re.compile(r"(?i)\b(tengo razón|i'?m right|estoy en lo correcto|i win|gané)\b"),
    re.compile(r"(?i)\b(ves\?|see\?|told you|te lo dije|te dije)\b"),
    re.compile(r"(?i)\b(no puedes negar|you can'?t deny|es un hecho|it'?s a fact)\b"),
]

# Tunables for the repetition-loop detector. JACCARD_THRESHOLD is the
# content-word overlap ratio between consecutive messages that counts as
# "similar"; MIN_LOOP_CONSECUTIVE is how many similar pairs are needed
# before we flag the loop as a pattern.
JACCARD_THRESHOLD = 0.4
MIN_LOOP_CONSECUTIVE = 2


# ═══════════════════════════════════════════════════════════════════════════
# Shared counting utility
# ═══════════════════════════════════════════════════════════════════════════


def count_hits(text: str, patterns: list[re.Pattern]) -> int:
    """How many patterns in the list produced at least one match in the text."""
    return sum(1 for p in patterns if p.search(text))
