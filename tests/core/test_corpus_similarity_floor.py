"""Similarity floors — que filtren de verdad contra ada-002.

El 0.30 histórico era un no-op garantizado: ada-002 es anisotrópico y sus
cosenos viven ~[0.65, 0.95] hasta entre textos SIN relación, así que ningún
hit caía jamás bajo el floor y todo top-k entraba al turno (el failure mode de
RAG para role-play: chunks irrelevantes distraen al personaje).

Mutator rule: positivo (hits bajo el floor se CAEN) + resistencia (hits
legítimos pasan; todo-bajo-el-floor → None, no bloque vacío) + arnés (los
floors no pueden regresar al rango decorativo mientras el embedder sea
ada-002).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from khimeras_shared.corpus import references
from khimeras_shared.deep_memory import _USER_MEMORY_MIN_SIMILARITY


def _hit(similarity: float, text: str) -> dict:
    return {"source_type": "corpus", "source_ref": "x.pdf", "chunk_text": text, "similarity": similarity}


async def test_floor_drops_ada002_background_noise():
    """Un hit en 0.72 (ruido de fondo típico de ada-002 entre textos ajenos)
    se cae; el hit legítimo en 0.86 entra al bloque."""
    hits = [_hit(0.86, "Schopenhauer: estratagema 12"), _hit(0.72, "receta de aquafaba")]
    with patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)):
        block = await references.build_references_block(
            "cómo desarmo una falacia de autoridad", namespace="__corpus_insult__", header="# Refs"
        )
    assert block is not None
    assert "estratagema 12" in block
    assert "aquafaba" not in block


async def test_all_noise_returns_none_not_empty_block():
    """RESISTENCIA: si nada clarea el floor, el turno va SIN bloque (None) —
    nunca un header colgado sin contenido."""
    hits = [_hit(0.71, "ruido a"), _hit(0.69, "ruido b"), _hit(0.66, "ruido c")]
    with patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)):
        block = await references.build_references_block(
            "qué opinas del clima de hoy", namespace="__corpus_insult__", header="# Refs"
        )
    assert block is None


async def test_legit_hits_all_pass():
    """RESISTENCIA: contenido genuinamente relacionado (0.8+) no se pierde."""
    hits = [_hit(0.91, "chunk uno"), _hit(0.84, "chunk dos"), _hit(0.80, "chunk tres")]
    with patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)):
        block = await references.build_references_block(
            "análisis del tercer acto de Mulholland Drive", namespace="__corpus_film__", header="# Refs"
        )
    assert block is not None
    for text in ("chunk uno", "chunk dos", "chunk tres"):
        assert text in block


def test_floors_never_regress_to_decorative_range():
    """ARNÉS: mientras el embedder de estos paths sea ada-002 (pg_rag), un
    floor por debajo de ~0.65 no filtra NADA — es fake protection. Si esto
    truena, o alguien bajó el floor sin leer la anisotropía de ada-002, o se
    cambió el embedder (entonces recalibrar floor Y este test juntos)."""
    assert references._REF_MIN_SIMILARITY >= 0.7
    assert _USER_MEMORY_MIN_SIMILARITY >= 0.7


# --- provenance in the injected block ---------------------------------------


def test_cite_label_strips_persona_prefix():
    """`<persona_id>:<slug>` → slug. The persona prefix is noise: the model
    already knows whose corpus it is reading."""
    assert (
        references.cite_label("unborn_being:contraelamor-2023-deseo-vs-rutina") == "contraelamor-2023-deseo-vs-rutina"
    )
    assert references.cite_label("insult:larochefoucauld-maxims") == "larochefoucauld-maxims"


def test_cite_label_degrades_to_generic_never_raises():
    """RESISTANCE: a missing/empty ref must never crash the turn or emit an
    empty bracket — provenance is a nicety, the reply is not."""
    assert references.cite_label(None) == "corpus"
    assert references.cite_label("   ") == "corpus"
    assert references.cite_label("no-colon-here") == "no-colon-here"


async def test_block_carries_provenance_per_passage():
    """POSITIVE: each retrieved passage arrives labeled with where it came from.

    Retrieval always returned source_ref; the block used to render `- <text>`
    alone, so a corpus passage was indistinguishable from the persona's own
    invention and could not be cited the way a web result is.
    """
    hits = [
        {
            "source_type": "manual",
            "source_ref": "unborn_being:contraelamor-2019-el-peon-parental",
            "chunk_text": "tesis del peón",
            "similarity": 0.9,
        },
        {
            "source_type": "manual",
            "source_ref": "unborn_being:hume-dialogues-natural-religion",
            "chunk_text": "el argumento del diseño",
            "similarity": 0.83,
        },
    ]
    with patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)):
        block = await references.build_references_block(
            "por qué la familia reproduce la coacción", namespace="__corpus_unborn__", header="# Refs"
        )
    assert block is not None
    assert "- [contraelamor-2019-el-peon-parental] tesis del peón" in block
    assert "- [hume-dialogues-natural-religion] el argumento del diseño" in block


async def test_provenance_never_leaks_the_namespace_or_user_id():
    """RESISTANCE: the label is the source slug ONLY — never the synthetic
    namespace, which is internal plumbing the persona must not narrate."""
    hits = [
        {
            "source_type": "manual",
            "source_ref": "vultur:braudy-cohen-2009",
            "chunk_text": "montaje soviético",
            "similarity": 0.88,
        }
    ]
    with patch.object(references, "query_corpus", new=AsyncMock(return_value=hits)):
        block = await references.build_references_block(
            "cómo funciona el montaje de atracciones", namespace="__corpus_film__", header="# Refs"
        )
    assert block is not None
    assert "__corpus_film__" not in block
    assert "vultur:" not in block
