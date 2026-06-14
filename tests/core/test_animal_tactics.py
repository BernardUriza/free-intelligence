"""Fine animal-liberation tactics — RAG retrieval (Phase B, in-memory).

Bernard's call: in-memory, fi_core for chunking, no store. Semantic retrieval
when an embedder is available (Insult), lexical fallback otherwise (ALICE @1Gi,
no embedder). Each behavior gets a positive + a resistance case.
"""

from __future__ import annotations

import khimeras_shared.corpus.rag as rag
from khimeras_shared.corpus import animal_tactics_guidance
from khimeras_shared.corpus.rag import _load_chunks, retrieve_tactics


def test_corpus_chunks_one_per_objection():
    """Structure-aware split: one ## objection block per chunk, none fused
    (the post-histerical-search pulido — fi_core token chunking fused 2/chunk)."""
    chunks = _load_chunks()
    assert len(chunks) >= 10
    assert all(c.count("## ") == 1 for c in chunks)  # no fused objections


def test_lexical_folds_accents():
    """Spanish users type without tildes: 'religion'/'omnivoros' must still hit
    the accented chunks ('religión'/'omnívoros'). This was 5/6 before folding."""
    rel = retrieve_tactics("y la religion? Dios puso a los animales", top_k=1)
    assert rel and "religi" in rel[0].lower()
    omn = retrieve_tactics("dicen que somos omnivoros", top_k=1)
    assert omn and "omn" in omn[0].lower()


# --- lexical retrieval (ALICE path: embed=None) ----------------------------


def test_lexical_retrieves_omnivore_block():
    out = retrieve_tactics("me dijo que los humanos somos omnívoros, ¿comer carne entonces?", top_k=2)
    assert any("omn" in c.lower() for c in out)


def test_lexical_retrieves_good_farms_block():
    out = retrieve_tactics("pero las buenas granjas tratan bien a los animales", top_k=2)
    assert any("granja" in c.lower() for c in out)


def test_lexical_off_topic_returns_nothing_relevant():
    """Resistance: a query with no overlap to any tactic clears nothing."""
    out = retrieve_tactics("el clima de hoy y mi rutina de ejercicio matutina", top_k=2)
    assert out == []


def test_empty_query_returns_empty():
    assert retrieve_tactics("", top_k=2) == []
    assert retrieve_tactics(None, top_k=2) == []


# --- semantic retrieval (Insult path: embed callable) ----------------------


def _mock_embed(text: str) -> list[float]:
    """Deterministic keyword-presence vector — lets us exercise the cosine path
    without loading sentence-transformers. Each dim = a topic marker."""
    t = text.lower()
    markers = ["omnívoro", "granja", "welfarism", "ganado", "religión", "plantas"]
    return [1.0 if m in t else 0.0 for m in markers]


def test_semantic_path_selects_by_cosine(monkeypatch):
    # reset the cached chunk embeddings so the mock embedder is used fresh
    monkeypatch.setattr(rag, "_chunk_embeddings", None)
    out = retrieve_tactics("eso es puro welfarism, debaten condiciones", embed=_mock_embed, top_k=1)
    assert out  # something cleared the cosine floor
    assert "welfarism" in out[0].lower()


# --- gate integration: animal_tactics_guidance -----------------------------


def test_guidance_empty_when_topic_absent():
    """The topic gate fronts retrieval — no animal topic, no tactics."""
    assert animal_tactics_guidance("oye qué tal tu día, todo bien?") == ""


def test_guidance_returns_tactics_on_topic():
    """On-topic message (carries a topic signal) surfaces relevant tactics."""
    out = animal_tactics_guidance("me vendieron carne diciendo que los humanos somos omnívoros")
    assert out != ""
    assert "omn" in out.lower()
