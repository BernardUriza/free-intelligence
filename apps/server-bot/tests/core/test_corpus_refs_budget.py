"""El presupuesto de caracteres del bloque de referencias — nunca deja el turno sin su mejor pasaje.

El loop hacía `break` en la primera línea que no cabía. Cuando esa línea era el
hit #1, el bloque salía vacío y la función devolvía None sin un solo evento: el
corpus se consultó, pasó el floor de similitud, y a la persona no le llegó nada
(Frugívoro, 2026-10-03: pasajes top de 2255 a 2589 chars contra un tope de 2200).

Mutator rule: positivo (el pasaje gordo entra truncado, y la memoria por usuario
igual) + resistencia (lo que cabe pasa intacto; el tope se respeta; un pasaje
gordo a media lista no tapa al corto que sigue).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from persona_core import deep_memory
from persona_core.corpus import references


def _hit(similarity: float, text: str, ref: str = "frugivoro:pmc-embarazo") -> dict:
    return {"source_type": "corpus", "source_ref": ref, "chunk_text": text, "similarity": similarity}


def _passage(chars: int, word: str = "folato") -> str:
    return " ".join([word] * (chars // (len(word) + 1) + 1))[:chars].strip()


async def _block(hits: list[dict]) -> str | None:
    with patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)):
        return await references.build_references_block(
            "qué suplementos necesita una embarazada vegana", namespace="__corpus_vegan__", header="# Refs"
        )


async def test_oversized_top_passage_is_truncated_not_dropped():
    """POSITIVO: el hit #1 solo ya excede el tope → entra truncado, con su
    etiqueta de procedencia, en vez de dejar el turno sin corpus."""
    block = await _block([_hit(0.88, _passage(2500))])
    assert block is not None
    body = block.split("\n", 1)[1]
    assert body.startswith("- [pmc-embarazo] folato")
    assert body.endswith("…")
    assert len(body) <= references._REF_MAX_CHARS


async def test_all_passages_oversized_still_delivers_the_best_one():
    """POSITIVO (el caso exacto del humo: 2408/2477/2589): sale el mejor, uno solo."""
    hits = [
        _hit(0.86, _passage(2408, "hierro")),
        _hit(0.84, _passage(2477, "yodo")),
        _hit(0.81, _passage(2589, "colina")),
    ]
    block = await _block(hits)
    assert block is not None
    assert "hierro" in block
    assert "yodo" not in block and "colina" not in block


async def test_truncation_backs_off_to_a_word_boundary():
    """El corte no parte una palabra a la mitad cuando hay un espacio cerca."""
    block = await _block([_hit(0.88, _passage(2500, "cianocobalamina"))])
    assert block is not None
    assert block.split("\n", 1)[1].removesuffix("…").endswith("cianocobalamina")


async def test_passages_that_fit_are_untouched():
    """RESISTENCIA: lo que cabe en el tope pasa íntegro, sin elipsis."""
    hits = [_hit(0.90, _passage(900, "uno")), _hit(0.85, _passage(900, "dos"))]
    block = await _block(hits)
    assert block is not None
    assert "…" not in block
    assert _passage(900, "uno") in block and _passage(900, "dos") in block


async def test_oversized_middle_passage_does_not_block_a_shorter_one_after_it():
    """RESISTENCIA: un pasaje que no cabe a media lista se salta — no se trunca
    (el mejor ya entró) ni le cierra la puerta al corto que viene después."""
    hits = [_hit(0.90, "pasaje corto uno"), _hit(0.86, _passage(2500, "gordo")), _hit(0.82, "pasaje corto tres")]
    block = await _block(hits)
    assert block is not None
    assert "pasaje corto uno" in block and "pasaje corto tres" in block
    assert "gordo" not in block
    assert "…" not in block


async def test_telemetry_reports_truncation_and_budget_drops():
    """Un bloque recortado se ve en KQL: `truncated` y `dropped_over_budget`."""
    hits = [_hit(0.86, _passage(2408)), _hit(0.84, _passage(2477))]
    with (
        patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)),
        patch.object(references.log, "info") as log_info,
    ):
        await references.build_references_block(
            "qué suplementos necesita una embarazada vegana", namespace="__corpus_vegan__", header="# Refs"
        )
    call = next(c for c in log_info.call_args_list if c.args and c.args[0] == "deep_memory_corpus_refs_built")
    assert call.kwargs["hits"] == 1
    assert call.kwargs["truncated"] is True
    assert call.kwargs["dropped_over_budget"] == 1
    assert call.kwargs["low_similarity"] == 0.86


async def test_user_memory_block_has_the_same_guarantee():
    """POSITIVO: `build_user_memory_block` cargaba el mismo loop; un fragmento
    de historia más largo que su tope también entra truncado."""
    hits = [_hit(0.90, _passage(2600, "larisa"))]
    with (
        patch.object(deep_memory, "query_user_memory", new=AsyncMock(return_value=hits)),
        patch.object(deep_memory, "load_prompt", return_value="# Memoria"),
    ):
        block = await deep_memory.build_user_memory_block(user_id="u1", text="qué te conté de Larisa")
    assert block is not None
    body = block.split("\n", 1)[1]
    assert body.startswith("- larisa") and body.endswith("…")
    assert len(body) <= deep_memory._USER_MEMORY_MAX_CHARS
