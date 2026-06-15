"""Universal values corpora — shared, bot-agnostic frames.

A *corpus* here is a body of values/doctrine that applies to ANY conversation
on its topic, for BOTH bots, regardless of which user is talking. It is a
distinct level from:

  - persona (identity, per-bot, immutable)
  - user facts (per-user, "what I know about this person")

This module is the Phase-A delivery: a topic detector + an mtime-aware loader
that lets a bot inject the values frame into a turn when the topic is present.
The Phase-B fine layer (per-objection RAG over the full document via
`fi_core.rag`) is a separate, later addition; this on/off overlay covers the
always-relevant values core.

Design choice — high precision over recall: a false positive inflates every
turn's payload and is jarring; a false negative just means the frame stays
silent on a borderline message. We bias toward NOT firing. The detector keys
on terms that are unambiguously about animal *use/consumption*, not mere
mention of an animal ("tengo un perro" must NOT fire).
"""

from __future__ import annotations

import re
import threading
from pathlib import Path

import structlog

log = structlog.get_logger()

_CORPUS_DIR = Path(__file__).parent

# Animal-liberation topic detector. Each alternative is specific enough to the
# use/consumption/ethics axis that a bare animal mention won't trip it.
_ANIMAL_TOPIC_PATTERN = re.compile(
    r"\b("
    # explicit movement / framework vocabulary
    r"vegan[oa]?s?|veganism[o]?|vegetarian[oa]?s?|plant[\s-]?based|"
    r"abolicion(ist[ao]s?|ismo)?|abolitionis[mt]|"
    r"especis(ta|mo)|speciesis[mt]|carnis[mt]|welfaris[mt]|"
    r"animal\s+(liberation|rights|exploitation|use|welfare)|"
    r"derechos\s+animales|explotaci[oó]n\s+animal|liberaci[oó]n\s+animal|"
    r"matadero|slaughter(house)?|factory\s+farm|granja\s+industrial|"
    # animal-derived foods in a consumption/order context
    r"carne|pollo|res|cerdo|puerco|pescado|marisco|jam[oó]n|tocino|"
    r"chorizo|l[aá]cteo|gelatina|"
    r"origen\s+animal|producto[s]?\s+animal|ingrediente[s]?\s+animal"
    r")\b",
    re.IGNORECASE,
)


def detect_animal_topic(text: str | None) -> bool:
    """True when the message is on the animal-use / veganism axis.

    Tuned for precision: fires on movement vocabulary and animal-derived
    foods, not on neutral animal mentions. Empty / None → False.
    """
    if not text:
        return False
    return _ANIMAL_TOPIC_PATTERN.search(text) is not None


# Film-criticism topic detector. Same precision-over-recall bias as the animal
# detector: a false positive forces the forensic frame onto an off-topic turn
# (jarring), a false negative just leaves it silent. Each alternative is
# specific enough to the *film-as-work / analysis* axis that a casual "vi una
# peli" or a bare "actor" won't trip it — we require vocabulary that signals
# the conversation is ABOUT a film or its craft, not a passing mention.
_FILM_TOPIC_PATTERN = re.compile(
    r"\b("
    # the work itself (require enough specificity)
    r"pel[ií]cula[s]?|filme[s]?|largometraje[s]?|cortometraje[s]?|"
    r"cinta\s+(cinematogr[aá]fica|de\s+cine)|filme?\b|movie[s]?|film[s]?|"
    # craft / analysis vocabulary — unambiguous about cinema
    r"cinematogr[aá]fic[oa]s?|cinematography|"
    r"director[ae]?\s+de\s+cine|direcci[oó]n\s+(de\s+)?(cine|fotograf[ií]a)|"
    r"mise[\s-]?en[\s-]?sc[eè]ne|puesta\s+en\s+escena|"
    r"plano[\s-]?(secuencia|detalle|general|americano|contrapicado|picado|"
    r"cenital|holand[eé]s|largo|corto|medio|fijo|abierto|cerrado|maestro)|"
    r"long\s+take|"
    r"montaje|monta(je|r)\s+cinematogr|editing|"
    r"ritmo\s+dieg[eé]tico|dieg[eé]tic[oa]|"
    r"gui[oó]n(ista)?|screenplay|"
    r"fotograf[ií]a\s+de\s+(la\s+pel[ií]cula|cine)|"
    r"secuela|precuela|tr[aá]iler|trailer|"
    r"rese[ñn]a\s+de\s+(la\s+)?(pel[ií]cula|cine|filme)|"
    r"filmograf[ií]a|cineasta[s]?|el\s+cine\s+de|"
    r"escena\s+(final|de\s+apertura|clave|de\s+la\s+pel[ií]cula)"
    r")\b",
    re.IGNORECASE,
)


def detect_film_topic(text: str | None) -> bool:
    """True when the message is on the film / film-criticism axis.

    Tuned for precision: fires on cinema-craft vocabulary and explicit
    references to a film as a work, not on neutral mentions ("vi una peli"
    alone, a bare "actor"). Empty / None → False.
    """
    if not text:
        return False
    return _FILM_TOPIC_PATTERN.search(text) is not None


class _CorpusLoader:
    """mtime-aware loader for a single corpus markdown file.

    Mirrors `alice.core.persona_loader` and `insult.core.prompts_loader`:
    editing the .md in a running container updates the injected text on the
    NEXT turn — no redeploy. Thread-safe stat+read under a lock.
    """

    def __init__(self, filename: str):
        self._path = _CORPUS_DIR / filename
        self._lock = threading.Lock()
        self._cached_text = ""
        self._cached_mtime = 0.0

    def load(self) -> str:
        try:
            current_mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            log.error("corpus_missing", path=str(self._path))
            return ""
        with self._lock:
            if current_mtime != self._cached_mtime:
                self._cached_text = self._path.read_text(encoding="utf-8")
                self._cached_mtime = current_mtime
                log.info("corpus_loaded", path=str(self._path), chars=len(self._cached_text))
            return self._cached_text


_animal_liberation_loader = _CorpusLoader("animal_liberation.md")


def load_animal_liberation_values() -> str:
    """Return the curated animal-liberation values frame (mtime-cached).

    Strips the leading HTML authoring comment so only the frame itself
    reaches the model.
    """
    raw = _animal_liberation_loader.load()
    return re.sub(r"^<!--.*?-->\s*", "", raw, count=1, flags=re.DOTALL)


def animal_liberation_guidance(text: str | None) -> str:
    """Convenience: return the values frame iff the topic is detected, else "".

    Both bots call this with the current user message. Empty string means
    "topic absent, inject nothing" — caller appends unconditionally.
    """
    if not detect_animal_topic(text):
        return ""
    return load_animal_liberation_values()


_film_criticism_loader = _CorpusLoader("film_criticism.md")


def load_film_criticism_values() -> str:
    """Return the curated film-criticism (Vultur) method frame (mtime-cached).

    Strips the leading HTML authoring comment so only the frame itself
    reaches the model.
    """
    raw = _film_criticism_loader.load()
    return re.sub(r"^<!--.*?-->\s*", "", raw, count=1, flags=re.DOTALL)


def film_criticism_guidance(text: str | None) -> str:
    """Convenience: return the Vultur method frame iff the topic is detected.

    Both bots call this with the current user message. Empty string means
    "topic absent, inject nothing" — caller appends unconditionally. The
    theoretical RAG layer (Braudy & Cohen / Language of Film Criticism) is a
    separate retrieval the caller adds underneath this frame when present.
    """
    if not detect_film_topic(text):
        return ""
    return load_film_criticism_values()


def animal_tactics_guidance(text: str | None, *, embed=None, top_k: int = 2) -> str:
    """Phase B: return relevant fine-tactic blocks iff the topic is detected.

    Combines the topic gate with semantic/lexical retrieval (see
    `khimeras_shared.corpus.rag`). `embed` is the caller's sentence-transformers
    `EmbeddingModel.embed` (Insult) — omit for lexical fallback (ALICE).
    Returns "" when off-topic OR when nothing clears the relevance floor.
    """
    if not detect_animal_topic(text):
        return ""
    from khimeras_shared.corpus.rag import retrieve_tactics

    blocks = retrieve_tactics(text, embed=embed, top_k=top_k)
    if not blocks:
        return ""
    return "Tácticas relevantes para este punto (úsalas en tu voz, no las cites literal):\n\n" + "\n\n".join(blocks)
