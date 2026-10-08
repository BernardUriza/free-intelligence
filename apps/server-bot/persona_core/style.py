"""Análisis de estilo de escritura del usuario — pure Python, zero deps.

Detecta: idioma, formalidad, nivel técnico, verbosidad, uso de emojis.
Usa exponential moving average (EMA) para suavizar cambios.
"""

import json
import re

# --- Language detection via stopwords ---

LANG_STOPWORDS = {
    "es": {
        "de",
        "la",
        "el",
        "en",
        "que",
        "los",
        "las",
        "por",
        "con",
        "una",
        "para",
        "del",
        "es",
        "se",
        "no",
        "un",
        "su",
        "al",
        "lo",
        "como",
        "más",
        "pero",
        "sus",
        "le",
        "ya",
        "o",
        "fue",
        "este",
        "ha",
        "sí",
        "porque",
        "esta",
        "son",
        "entre",
        "está",
        "cuando",
        "muy",
        "sin",
        "sobre",
        "ser",
        "también",
        "me",
        "hasta",
        "hay",
        "donde",
        "han",
        "quien",
        "están",
        "desde",
        "todo",
        "nos",
        "ni",
        "ese",
        "eso",
    },
    "en": {
        "the",
        "is",
        "at",
        "in",
        "on",
        "and",
        "or",
        "to",
        "of",
        "for",
        "it",
        "was",
        "are",
        "be",
        "has",
        "had",
        "have",
        "with",
        "this",
        "that",
        "from",
        "but",
        "not",
        "you",
        "all",
        "can",
        "her",
        "his",
        "one",
        "our",
        "out",
        "do",
        "if",
        "my",
        "no",
        "up",
        "so",
        "an",
    },
}

# --- Formality markers ---

INFORMAL_ES = {
    "wey",
    "we",
    "güey",
    "neta",
    "nmms",
    "chale",
    "chido",
    "verga",
    "pedo",
    "mames",
    "jaja",
    "jeje",
    "xd",
    "ntp",
    "xfa",
    "arre",
    "nel",
    "simon",
    "orale",
    "órale",
    "cabrón",
    "cabron",
    "chingón",
    "pues",
    "nah",
    "uy",
    "onda",
    "rollo",
    "morro",
    "morrita",
    "compa",
    "carnal",
    "banda",
    "pendejo",
    "pendeja",
    "pinche",
    "culero",
    "mamón",
    "mamon",
    "fregón",
}

INFORMAL_EN = {
    "lol",
    "lmao",
    "tbh",
    "ngl",
    "idk",
    "imo",
    "btw",
    "omg",
    "bruh",
    "gonna",
    "wanna",
    "gotta",
    "kinda",
    "sorta",
    "ya",
    "yep",
    "nope",
    "haha",
    "hehe",
    "nah",
    "dude",
    "bro",
    "yo",
    "cuz",
    "ain't",
    "aint",
    "tho",
    "fr",
    "smh",
    "fam",
    "goat",
    "lit",
    "sus",
    "vibe",
}

INFORMAL_MARKERS = INFORMAL_ES | INFORMAL_EN

FORMAL_MARKERS = {
    "therefore",
    "however",
    "furthermore",
    "additionally",
    "regarding",
    "consequently",
    "nevertheless",
    "accordingly",
    "whereas",
    "moreover",
    "por lo tanto",
    "sin embargo",
    "además",
    "respecto",
    "estimado",
    "atentamente",
    "mediante",
    "conforme",
    "solicito",
    "agradecer",
}

# --- Technical detection ---

TECH_PATTERNS = [
    re.compile(r"\b(api|sdk|sql|json|http|tcp|dns|ssh|git|npm|pip|docker|k8s|aws|gcp)\b", re.I),
    re.compile(r"\b(function|class|import|return|async|await|def|const|var|let|void|int|str|bool)\b", re.I),
    re.compile(r"```"),
    re.compile(r"\b\w+\(\)"),
    re.compile(r"\b(server|database|deploy|endpoint|backend|frontend|runtime|middleware|webhook)\b", re.I),
    re.compile(r"\b(framework|library|dependency|module|package|repository|branch|commit|merge)\b", re.I),
]

# --- Emoji detection ---

EMOJI_PATTERN = re.compile(
    "[\U0001f600-\U0001f64f"
    "\U0001f300-\U0001f5ff"
    "\U0001f680-\U0001f6ff"
    "\U0001f1e0-\U0001f1ff"
    "\U00002702-\U000027b0"
    "\U0001f900-\U0001f9ff"
    "]+",
    flags=re.UNICODE,
)

# EMA smoothing factor — 0.3 means recent messages weigh ~30%
EMA_ALPHA = 0.3

# Minimum messages before profile is considered reliable
CONFIDENCE_THRESHOLD = 5


class UserStyleProfile:
    """Per-user style fingerprint, updated incrementally via EMA."""

    # How many consecutive messages in a different language are needed before
    # the profile switches. Single pasted snippets (e.g. an English email
    # Bernard quotes in chat) must NOT flip the profile — see
    # `_LANG_SWITCH_STREAK_REQUIRED` rationale in `update()`.
    _LANG_SWITCH_STREAK_REQUIRED = 3

    def __init__(
        self,
        avg_word_count: float = 15.0,
        emoji_ratio: float = 0.0,
        formality: float = 0.5,
        technical_level: float = 0.5,
        detected_language: str = "es",
        message_count: int = 0,
        lang_switch_streak: int = 0,
    ):
        self.avg_word_count = avg_word_count
        self.emoji_ratio = emoji_ratio
        self.formality = formality
        self.technical_level = technical_level
        self.detected_language = detected_language
        self.message_count = message_count
        # Counts how many consecutive recent messages have been detected
        # in a language OTHER than the current `detected_language`. Reset
        # to 0 whenever a message matches the current language. Switch
        # only when streak >= _LANG_SWITCH_STREAK_REQUIRED.
        self.lang_switch_streak = lang_switch_streak

    def update(self, text: str):
        """Update profile with a new message using EMA smoothing."""
        self.message_count += 1
        alpha = EMA_ALPHA

        # Verbosity
        word_count = len(text.split())
        self.avg_word_count = alpha * word_count + (1 - alpha) * self.avg_word_count

        # Emoji
        emoji_count = len(EMOJI_PATTERN.findall(text))
        new_emoji_ratio = emoji_count / max(word_count, 1)
        self.emoji_ratio = alpha * new_emoji_ratio + (1 - alpha) * self.emoji_ratio

        # Formality
        new_formality = _compute_formality(text)
        self.formality = alpha * new_formality + (1 - alpha) * self.formality

        # Technical level
        new_tech = _compute_technical_level(text)
        self.technical_level = alpha * new_tech + (1 - alpha) * self.technical_level

        # Language — sticky with streak ONCE confident. Single off-language
        # messages (a pasted email, a quoted snippet) must NOT flip an
        # established profile.
        # Bug 2026-05-18 18:44: Bernard pasted an English email and the
        # bot started responding in English to the next turn.
        # Two regimes:
        #   - Profile still learning (count < CONFIDENCE_THRESHOLD): switch
        #     immediately. A brand-new user who writes English in turn #1
        #     should be detected as English right away.
        #   - Profile confident (count >= CONFIDENCE_THRESHOLD): require
        #     _LANG_SWITCH_STREAK_REQUIRED consecutive other-language
        #     messages before switching. Pasted snippets get absorbed.
        detected_now = _detect_language(text)
        if self.message_count < CONFIDENCE_THRESHOLD:
            self.detected_language = detected_now
            self.lang_switch_streak = 0
        elif detected_now == self.detected_language:
            self.lang_switch_streak = 0
        else:
            self.lang_switch_streak += 1
            if self.lang_switch_streak >= self._LANG_SWITCH_STREAK_REQUIRED:
                self.detected_language = detected_now
                self.lang_switch_streak = 0

    @property
    def is_confident(self) -> bool:
        """True if we have enough data to adapt reliably."""
        return self.message_count >= CONFIDENCE_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "avg_word_count": round(self.avg_word_count, 1),
            "emoji_ratio": round(self.emoji_ratio, 3),
            "formality": round(self.formality, 2),
            "technical_level": round(self.technical_level, 2),
            "detected_language": self.detected_language,
            "message_count": self.message_count,
            "lang_switch_streak": self.lang_switch_streak,
        }

    @classmethod
    def from_dict(cls, data: dict) -> UserStyleProfile:
        return cls(
            avg_word_count=data.get("avg_word_count", 15.0),
            emoji_ratio=data.get("emoji_ratio", 0.0),
            formality=data.get("formality", 0.5),
            technical_level=data.get("technical_level", 0.5),
            detected_language=data.get("detected_language", "es"),
            message_count=data.get("message_count", 0),
            # Default 0 for profiles persisted before v3.9.49 — they get
            # streak counting from the next message onwards.
            lang_switch_streak=data.get("lang_switch_streak", 0),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, raw: str) -> UserStyleProfile:
        return cls.from_dict(json.loads(raw))


def _detect_language(text: str) -> str:
    """Detect es/en from stopword frequency."""
    words = set(text.lower().split())
    scores = {lang: len(words & stops) for lang, stops in LANG_STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "es"


def _compute_formality(text: str) -> float:
    """0.0 = very casual, 1.0 = very formal."""
    words = set(text.lower().split())
    informal_hits = len(words & INFORMAL_MARKERS)

    # Contractions are informal
    informal_hits += len(re.findall(r"\w+n't|\w+'re|\w+'ve|\w+'ll", text.lower()))

    formal_hits = len(words & FORMAL_MARKERS)

    # Proper punctuation and capitalization lean formal
    if text and text[-1:] in ".!?" and text[0].isupper():
        formal_hits += 1

    total = informal_hits + formal_hits
    if total == 0:
        return 0.5
    return formal_hits / total


def _compute_technical_level(text: str) -> float:
    """0.0 = non-technical, 1.0 = highly technical."""
    hits = sum(len(p.findall(text)) for p in TECH_PATTERNS)
    word_count = max(len(text.split()), 1)
    ratio = hits / word_count
    return min(ratio * 10, 1.0)
