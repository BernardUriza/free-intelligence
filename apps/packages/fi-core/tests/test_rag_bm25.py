from __future__ import annotations

from fi_core.rag import Bm25Index, lexical_terms, reciprocal_rank_fusion

TEXTS = [
    "Frijol de ojo negro, seco. Hierro 5 mg.",
    "Lenteja seca (lentils, dry). Hierro 7 mg.",
    "Frijol negro en lata. Hierro 1 mg.",
    "Cilantro (coriander): huele a jabón y a cítrico.",
]


def test_exact_name_beats_the_word_every_card_shares():
    assert Bm25Index(TEXTS).rank("¿cuánto hierro tienen las lentejas?", limit=1) == [1]


def test_accents_and_plurals_do_not_matter():
    assert lexical_terms("Nopales RÁBANOS") == lexical_terms("nopal rabano")


def test_texts_sharing_no_term_are_left_out():
    assert Bm25Index(TEXTS).rank("capital de Australia", limit=10) == []


def test_limit_and_empty_corpus():
    assert len(Bm25Index(TEXTS).rank("hierro", limit=2)) == 2
    assert Bm25Index([]).rank("hierro", limit=3) == []


def test_fusion_recovers_a_chunk_the_dense_arm_never_returned():
    dense = [0, 2]
    fused = reciprocal_rank_fusion([dense, Bm25Index(TEXTS).rank("lentejas", limit=5)])
    assert 1 in fused
