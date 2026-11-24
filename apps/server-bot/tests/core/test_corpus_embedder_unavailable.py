"""Un apagón del embedder se ve como apagón, nunca como "no hubo hits".

Del 2026-10-20 al 2026-11-19 la llave de ada-002 dio 401 en cada turno y el KQL
dijo `deep_memory_corpus_no_hits` 28 de 28 veces: un mes sin biblioteca leído
como un mes de preguntas fuera de tema. La única alarma vivía en el gateway, que
estaba apagado. Y la tool `deep_memory` le decía al modelo "no hay nada de este
usuario", invitándolo a negar recuerdos.

Positivo (cada capa distingue "no pudo buscar" de "buscó y no encontró") +
resistencia (el camino normal sigue igual).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from persona_core import deep_memory
from persona_core.corpus import pg_rag, references
from persona_runner.api import turn_pipeline
from persona_runner.mcp_tools.memory_reads import deep_memory as deep_memory_tool
from persona_runner.mcp_tools.turn_context import bind_turn_principal, reset_turn_principal


async def test_query_corpus_is_none_when_the_embedder_is_down():
    with patch.object(references, "embed_query", new=AsyncMock(return_value=None)):
        assert (
            await references.query_corpus("torta ahogada vegana", namespace="__corpus_vegan__", top_k=3, fusion_pool=0)
            is None
        )


async def test_query_corpus_is_none_when_postgres_is_down():
    with (
        patch.object(references, "embed_query", new=AsyncMock(return_value=[0.1] * 384)),
        patch.object(references, "connect", new=AsyncMock(return_value=None)),
    ):
        assert (
            await references.query_corpus("torta ahogada vegana", namespace="__corpus_vegan__", top_k=3, fusion_pool=0)
            is None
        )


async def test_unavailable_corpus_logs_unavailable_not_no_hits():
    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=None)),
        patch.object(references.log, "info") as info,
        patch.object(references.log, "warning") as warning,
    ):
        block = await references.build_references_block(
            "cómo hago una torta ahogada", namespace="__corpus_vegan__", header="# Refs"
        )
    assert block is None
    assert [c.args[0] for c in warning.call_args_list] == ["deep_memory_corpus_unavailable"]
    assert "deep_memory_corpus_no_hits" not in [c.args[0] for c in info.call_args_list]


async def test_empty_search_still_logs_no_hits():
    """RESISTENCIA: buscó y no encontró sigue siendo `no_hits`."""
    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=[])),
        patch.object(references.log, "info") as info,
    ):
        await references.build_references_block(
            "cómo hago una torta ahogada", namespace="__corpus_vegan__", header="# R"
        )
    assert "deep_memory_corpus_no_hits" in [c.args[0] for c in info.call_args_list]


async def _call_tool(results):
    token = bind_turn_principal(user_id="907264175246569543", channel_id="c1")
    try:
        with patch.object(deep_memory, "query_user_memory", new=AsyncMock(return_value=results)):
            return await deep_memory_tool.handler({"query": "lo que te conté de Larisa", "top_k": 3})
    finally:
        reset_turn_principal(token)


async def test_tool_tells_the_model_memory_is_unavailable_not_empty():
    out = await _call_tool(None)
    text = str(out)
    assert "unavailable" in text
    assert "do not claim you have no record" in text


async def test_tool_still_reports_an_honest_empty_search():
    """RESISTENCIA: sin resultados reales, el mensaje de vacío de siempre."""
    out = await _call_tool([])
    assert "No deep memory chunks found" in str(out)


async def test_embedder_applies_the_e5_role_prefix():
    seen: list[str] = []
    embedder = pg_rag.get_corpus_embedder()
    with patch.object(embedder, "_encode", side_effect=lambda t: seen.append(t) or [0.0] * 384):
        await pg_rag.encode("pozole rojo", role="query")
        await pg_rag.encode("Pozole rojo vegano: maíz pozolero", role="passage")
    assert seen == ["query: pozole rojo", "passage: Pozole rojo vegano: maíz pozolero"]
    assert embedder.normalize is True


async def test_embedder_refuses_a_vector_of_the_wrong_size():
    embedder = pg_rag.get_corpus_embedder()
    with (
        patch.object(embedder, "_encode", return_value=[0.0] * 1536),
        pytest.raises(pg_rag.EmbeddingDimensionError),
    ):
        await pg_rag.encode("x", role="passage")


async def test_warm_reports_dead_embedder_loudly():
    with (
        patch.object(pg_rag, "embed_query", new=AsyncMock(return_value=None)),
        patch.object(pg_rag.log, "error") as error,
    ):
        assert await pg_rag.warm_corpus_embedder() is False
    assert error.call_args.args[0] == "corpus_embedder_unavailable"


async def test_shutdown_waits_for_fact_extraction_then_cancels_stragglers():
    """Positivo: la extracción en vuelo termina antes de cerrar el pool; la que
    no cabe en el tope se cancela en vez de colgar el apagado."""
    quick = asyncio.create_task(asyncio.sleep(0.01))
    slow = asyncio.create_task(asyncio.sleep(30))
    turn_pipeline._bg_tasks.update({quick, slow})
    try:
        await turn_pipeline.drain_background(0.2)
        await asyncio.sleep(0)
        assert quick.done() and not quick.cancelled()
        assert slow.cancelled()
    finally:
        turn_pipeline._bg_tasks.difference_update({quick, slow})
