"""El ingestor de corpus no pierde fuentes en silencio.

Un documento entero más corto que el `min_chunk_size` del chunker (50 tokens)
vuelve como CERO chunks. Antes eso se evaporaba sin una palabra: la fuente
contaba como "procesada", no se insertaba nada y no sonaba ninguna alarma —
así desaparecieron los 14 posts más cortos del corpus de contraelamor
(2026-07-27), detectados solo al diffear Postgres contra los archivos en disco.

Mutator rule: positivo (el doc corto se rescata) + resistencia (el doc normal
chunkea igual que siempre; lo verdaderamente vacío se reporta como dropped,
nunca se traga).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ingest_corpus.py"
_spec = importlib.util.spec_from_file_location("ingest_corpus", _SCRIPT)
assert _spec and _spec.loader
ingest_corpus = importlib.util.module_from_spec(_spec)
sys.modules["ingest_corpus"] = ingest_corpus
_spec.loader.exec_module(ingest_corpus)


def _floor_chunker(min_chars: int = 400):
    """Un chunker que, como el real, devuelve [] cuando el doc no alcanza su piso."""

    def chunk(doc: str, *, chunk_size: int, overlap: int) -> list[str]:
        return [doc] if len(doc) >= min_chars else []

    return chunk


def test_short_document_is_salvaged_not_swallowed():
    """POSITIVO: un post corto pero real entra como UN chunk entero.

    El piso del chunker existe para rechazar un FRAGMENTO de un documento
    grande, no para descartar un documento corto COMPLETO.
    """
    doc = "x" * 300
    chunks, status = ingest_corpus.prepare_chunks(doc, chunker=_floor_chunker(), chunk_size=400, overlap=50)
    assert status == "salvaged"
    assert chunks == [doc]


def test_normal_document_still_chunks_normally():
    """RESISTENCIA: el rescate no toca el camino feliz."""
    doc = "y" * 5000
    chunks, status = ingest_corpus.prepare_chunks(doc, chunker=_floor_chunker(), chunk_size=400, overlap=50)
    assert status == "chunked"
    assert chunks == [doc]


def test_stub_below_salvage_floor_is_reported_dropped():
    """RESISTENCIA: lo que de verdad no tiene nada que recuperar se DESCARTA —
    pero con estado explícito, para que el llamador pueda gritarlo. Un cap
    silencioso que se lee como cobertura total es el fake-green que esto mata."""
    chunks, status = ingest_corpus.prepare_chunks("hola", chunker=_floor_chunker(), chunk_size=400, overlap=50)
    assert status == "dropped"
    assert chunks == []


def test_empty_source_is_distinguished_from_dropped():
    """Un PDF ilegible ("no_text") no es lo mismo que un stub demasiado corto
    ("dropped"): distinguirlos es lo que permite diagnosticar cuál falló."""
    chunks, status = ingest_corpus.prepare_chunks("   \n  ", chunker=_floor_chunker(), chunk_size=400, overlap=50)
    assert status == "no_text"
    assert chunks == []


def test_salvage_floor_is_low_enough_for_a_real_short_post():
    """ARNÉS: el piso de rescate no puede subir al rango donde un post corto
    legítimo del blog (≈200-370 chars) volvería a perderse."""
    assert ingest_corpus._MIN_SALVAGE_CHARS <= 200
