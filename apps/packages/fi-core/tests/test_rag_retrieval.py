"""Tests for fi_core.rag.retrieval — LexicalRetriever + SemanticRetriever."""

from __future__ import annotations

from fi_core.rag import (
    LexicalRetriever,
    ScoredText,
    SemanticRetriever,
    cosine_similarity,
    fold_accents,
    tokenize,
)

CHUNKS = [
    "## Welfarism\nEl bienestarismo regula la explotación pero no la abole.",
    "## Omnívoro\nComer carne es una elección cultural, no una necesidad.",
    "## Religión\nMuchas tradiciones religiosas justifican el uso de animales.",
]


def test_fold_accents():
    assert fold_accents("Religión") == "religion"
    assert fold_accents("Omnívoro") == "omnivoro"
    assert fold_accents("ÁÉÍÓÚñ") == "aeioun"


def test_tokenize_is_accent_folded_set():
    assert tokenize("Religión religión") == {"religion"}


def test_lexical_accent_insensitive_recall():
    """A query typed WITHOUT tildes still matches an accented corpus."""
    r = LexicalRetriever()
    hits = r.rank("que dice la religion sobre los animales", CHUNKS, top_k=1)
    assert hits and "Religión" in hits[0].text


def test_lexical_floor_filters_offtopic():
    r = LexicalRetriever()
    assert r.rank("configuración de kubernetes", CHUNKS, top_k=2) == []


def test_lexical_stopwords_dont_manufacture_matches():
    """A query made only of stopwords scores 0 (no content terms)."""
    r = LexicalRetriever()
    assert r.score("de la el los", CHUNKS[0]) == 0.0


def test_lexical_empty_inputs():
    r = LexicalRetriever()
    assert r.rank("", CHUNKS) == []
    assert r.rank("algo", []) == []


def test_lexical_respects_top_k_and_order():
    r = LexicalRetriever(min_score=0.0)
    hits = r.rank("comer carne religion animales", CHUNKS, top_k=2)
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score


def test_custom_min_score_override():
    r = LexicalRetriever(min_score=0.0)
    # A partially-overlapping query (1 of 3 content terms hits any chunk → ~0.33).
    query = "religion kubernetes docker"
    assert r.rank(query, CHUNKS, top_k=3)  # default floor 0.0 keeps it
    # Raise the floor above the partial score → nothing qualifies.
    assert r.rank(query, CHUNKS, top_k=3, min_score=0.99) == []


def test_cosine_similarity():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0  # zero vector safe


def test_semantic_ranks_by_cosine():
    sr = SemanticRetriever(min_score=0.1)
    hits = sr.rank([1.0, 0.0], ["a", "b"], [[1.0, 0.0], [0.0, 1.0]], top_k=2)
    assert hits == [ScoredText("a", 1.0)]


def test_semantic_length_mismatch_returns_empty():
    sr = SemanticRetriever()
    assert sr.rank([1.0], ["a", "b"], [[1.0]], top_k=2) == []
