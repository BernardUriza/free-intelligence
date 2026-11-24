"""The relevance gate: the cross-encoder decides what reaches the turn, not the cosine.

e5 cosines are compressed. Measured 2026-11-19 on 21 real queries, on-topic hits
scored 0.784-0.888 and off-topic ones 0.780-0.834: the old ada-era floor of 0.78
would have let every off-topic shortlist into the turn ("qué opinas del clima"
fetched a pozole recipe at 0.834). The gate is now the cross-encoder relevance.

Mutator rule: positive (a high-cosine, low-relevance hit is dropped) + resistance
(relevant hits pass in relevance order; all-below-floor gives None, never an empty
header) + harness (the floor stays inside the measured gap).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from persona_core.corpus import references
from persona_core.corpus.rules import load_rules


def _hit(similarity: float, text: str, ref: str = "x:y") -> dict:
    return {"source_type": "manual", "source_ref": ref, "chunk_text": text, "similarity": similarity}


async def _block(
    hits: list[dict],
    relevance: dict[str, float],
    query: str = "cómo hago pozole rojo sin carne",
    min_passages: int = 0,
):
    async def _score(q, passages):
        return [relevance[p] for p in passages]

    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)),
        patch.object(references, "score_relevance", new=_score),
    ):
        return await references.build_references_block(
            query, namespace="__corpus_vegan__", header="# Refs", min_passages=min_passages
        )


async def test_ammunition_corpus_keeps_its_best_passage_below_the_floor():
    """POSITIVE: Insult's maxims reach the turn even when nothing is on topic."""
    hits = [_hit(0.83, "máxima b"), _hit(0.82, "máxima a")]
    with patch.object(references.log, "info") as info:
        block = await _block(hits, {"máxima a": -3.7, "máxima b": -5.0}, query="qué opinas del deploy", min_passages=1)
    assert block is not None
    assert "máxima a" in block
    assert "máxima b" not in block
    call = next(c for c in info.call_args_list if c.args and c.args[0] == "deep_memory_corpus_refs_built")
    assert call.kwargs["forced"] is True


async def test_forced_minimum_does_not_cap_relevant_passages():
    texts = [f"pasaje {i}" for i in range(4)]
    block = await _block([_hit(0.85, t) for t in texts], dict.fromkeys(texts, 1.0), min_passages=1)
    assert block is not None
    assert block.count("pasaje") == load_rules().references.top_k


def test_only_insult_forces_its_corpus():
    """RESISTANCE: a corpus of facts (Frugi's recipes) keeps the floor."""
    from shared.personas.registry import PERSONAS

    forced = {pid for pid, p in PERSONAS.items() if p.corpus_min_passages}
    assert forced == {"insult"}


async def test_high_cosine_but_irrelevant_hit_is_dropped():
    """POSITIVE, the measured case: the off-topic chunk wins on cosine, loses on relevance."""
    hits = [_hit(0.834, "receta de birria"), _hit(0.80, "pozole rojo vegano")]
    block = await _block(hits, {"receta de birria": -5.3, "pozole rojo vegano": 0.38})
    assert block is not None
    assert "pozole rojo vegano" in block
    assert "birria" not in block


async def test_passages_are_ordered_by_relevance_not_cosine():
    hits = [_hit(0.88, "intro del recetario"), _hit(0.86, "receta de pozole")]
    block = await _block(hits, {"intro del recetario": -1.0, "receta de pozole": 2.0})
    assert block is not None
    assert block.index("receta de pozole") < block.index("intro del recetario")


async def test_only_top_k_relevant_passages_enter():
    texts = [f"pasaje {i}" for i in range(6)]
    block = await _block([_hit(0.85, t) for t in texts], {t: 1.0 - i for i, t in enumerate(texts)})
    assert block is not None
    assert block.count("\n- ") + block.startswith("- ") == load_rules().references.top_k


async def test_all_irrelevant_returns_none_and_logs_no_hits():
    """RESISTANCE: nothing clears the floor → no block, and KQL says why."""
    hits = [_hit(0.83, "ruido a"), _hit(0.82, "ruido b")]
    with patch.object(references.log, "info") as info:
        block = await _block(hits, {"ruido a": -5.3, "ruido b": -6.0}, query="qué opinas del clima de hoy")
    assert block is None
    call = next(c for c in info.call_args_list if c.args and c.args[0] == "deep_memory_corpus_no_hits")
    assert call.kwargs["top_relevance"] == -5.3
    assert call.kwargs["queried"] == 2
    assert call.kwargs["floor"] == load_rules().references.floor("__corpus_vegan__")


async def test_reranker_failure_is_unavailable_not_no_hits():
    async def _broken(q, passages):
        return None

    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=[_hit(0.9, "x")])),
        patch.object(references, "score_relevance", new=_broken),
        patch.object(references.log, "warning") as warning,
        patch.object(references.log, "info") as info,
    ):
        block = await references.build_references_block(
            "cómo hago pozole rojo", namespace="__corpus_vegan__", header="# R"
        )
    assert block is None
    assert warning.call_args.args[0] == "deep_memory_corpus_unavailable"
    assert "deep_memory_corpus_no_hits" not in [c.args[0] for c in info.call_args_list]


async def test_empty_query_stays_silent_no_false_signal():
    """RESISTANCE: a trivial query is never even retrieved."""
    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=[])) as qc,
        patch.object(references.log, "info") as info,
    ):
        block = await references.build_references_block("  ", namespace="__corpus_vegan__", header="# Refs")
    assert block is None
    qc.assert_not_awaited()
    assert "deep_memory_corpus_no_hits" not in [c.args[0] for c in info.call_args_list if c.args]


def test_floor_stays_above_every_measured_off_topic_query():
    """HARNESS: the worst off-topic query scored -2.61 over 8 candidates (2026-11-20).
    Lowering the floor past it, or swapping RERANK_MODEL, means re-measuring."""
    assert load_rules().references.min_relevance > -2.608


def test_a_persona_floor_overrides_the_general_one_only_for_its_corpus():
    hits = [{"relevance": -1.5}]
    assert references.above_floor(hits, namespace="__corpus_vegan__") == []
    assert references.above_floor(hits, namespace="__corpus_insult__") == hits


def test_every_floor_override_names_a_live_corpus():
    from shared.personas.registry import PERSONAS

    assert set(load_rules().references.min_relevance_for) <= {p.corpus_namespace for p in PERSONAS.values()}


def test_cite_label_strips_persona_prefix():
    assert (
        references.cite_label("unborn_being:contraelamor-2023-deseo-vs-rutina") == "contraelamor-2023-deseo-vs-rutina"
    )
    assert references.cite_label("insult:larochefoucauld-maxims") == "larochefoucauld-maxims"


def test_cite_label_degrades_to_generic_never_raises():
    assert references.cite_label(None) == "corpus"
    assert references.cite_label("   ") == "corpus"
    assert references.cite_label("no-colon-here") == "no-colon-here"


async def test_block_carries_provenance_per_passage():
    hits = [
        _hit(0.9, "tesis del peón", "unborn_being:contraelamor-2019-el-peon-parental"),
        _hit(0.83, "el argumento del diseño", "unborn_being:hume-dialogues-natural-religion"),
    ]
    block = await _block(hits, {"tesis del peón": 2.0, "el argumento del diseño": 1.0})
    assert block is not None
    assert "- [contraelamor-2019-el-peon-parental] tesis del peón" in block
    assert "- [hume-dialogues-natural-religion] el argumento del diseño" in block


async def test_refs_built_log_names_the_sources_it_injected():
    """KQL must say which document fed the turn, not just how many hits."""
    hits = [_hit(0.9, "salsa ahogada", "frugivoro:loveveg-sabores-tapatios-2026"), _hit(0.8, "ruido", "frugivoro:x")]
    with patch.object(references.log, "info") as info:
        await _block(hits, {"salsa ahogada": 3.2, "ruido": -6.0})
    call = next(c for c in info.call_args_list if c.args and c.args[0] == "deep_memory_corpus_refs_built")
    assert call.kwargs["sources"] == ["loveveg-sabores-tapatios-2026"]


async def test_provenance_never_leaks_the_namespace_or_user_id():
    block = await _block([_hit(0.88, "montaje soviético", "vultur:braudy-cohen-2009")], {"montaje soviético": 4.8})
    assert block is not None
    assert "__corpus_" not in block
    assert "vultur:" not in block
