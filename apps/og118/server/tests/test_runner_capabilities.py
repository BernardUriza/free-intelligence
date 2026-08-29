"""proj-tracer — the og118 Runner wires the rag_store capability so the agent can
search uploaded project corpora (the Projects-for-the-papelería canary).

Two layers:
  * Contract — build_runner() declares rag_store, and the name resolves to a real
    MCP server spec (not just a string that silently no-ops at run time).
  * Store smoke — fi-runner's RagStoreClient round-trips text (ingest -> search)
    offline (hdf5 backend + hashing zero-model embedder), proving the store the
    agent's rag_store tool reads/writes actually works without an LLM.

No pytest-asyncio in this venv (anyio only), so async is driven via asyncio.run,
mirroring test_stt.py.
"""

from __future__ import annotations

import asyncio

from runner import PERSONA_PATH, build_runner
from fi_runner import capabilities as fi_caps
from fi_runner import load_prompt
from fi_runner.rag_store import RagStoreClient


def test_persona_declares_it_is_not_a_coding_agent() -> None:
    """og118 is a thinking companion, NOT an agentic coding tool (Claude Code /
    Codex). The persona must say so explicitly: the ClaudeCodeBackend's default
    'I operate in a repo' framing otherwise leaks — asked to 'show its code' it
    Glob+Read its own deployment source. It must disclaim repo/codebase/filesystem."""
    p = load_prompt(PERSONA_PATH).lower()
    assert "thinking companion" in p
    assert "not an agentic coding" in p or "not a coding" in p
    assert "no repository" in p or "no repo" in p or "no codebase" in p
    assert "filesystem" in p or "files" in p


def test_el_modo_de_la_puerta_no_concede_builtins() -> None:
    """El cerco de filesystem ya NO lo pone este proceso: lo pone la puerta.

    Antes se afirmaba sobre `tool_policy.builtin_disallowed`, que era una lista
    que el backend local leía. Con la consolidación en AIRE (2026-08-29) el
    tool_policy no se reenvía —AIRE configura sus tools server-side— así que
    seguir afirmando sobre esa lista habría sido verificar una garantía escrita
    y no ejercida. Lo que de verdad acota ahora es el MODO: `complete` no
    concede NINGÚN builtin, y `Bash` no existe en ninguno de los dos modos del
    dial, más la jaula de AIRE que confina los de archivo a la casita del chat.
    """
    assert build_runner().backend.default_mode == "complete"


def test_build_runner_wires_rag_store() -> None:
    """The Runner declares rag_store (project search) alongside task_tracker."""
    runner = build_runner()
    assert "rag_store" in runner.backend.registry_tools
    # task_tracker stays — the glass-box plan/step events come from it.
    assert "task_tracker" in runner.backend.registry_tools


def test_rag_store_capability_resolves_to_mcp_spec() -> None:
    """The wired name must resolve to a real MCP server spec, not a dead string."""
    specs = fi_caps.resolve(["rag_store"])
    assert len(specs) == 1


def test_rag_store_ingest_then_search_roundtrips(tmp_path, monkeypatch) -> None:
    """Smoke: text ingested under a corpus_id is searchable back through the same
    store the agent's rag_store tool uses (hdf5 + hashing embedder, no network)."""
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "proj_rag.h5"))

    text = (
        "La papelería de la mamá de Bernard vende cuadernos profesionales, "
        "lápices de colores, plumas de gel y mochilas escolares. En la temporada "
        "de regreso a clases de agosto los precios de los cuadernos suben porque "
        "la demanda de útiles escolares se dispara. El margen más alto está en "
        "las mochilas y los estuches, no en los lápices sueltos."
    )

    async def _run() -> list[dict]:
        client = RagStoreClient()
        # min_chunk_size lowered: the chunker measures TOKENS, so a short doc would
        # produce 0 chunks at the default 100 (the documented fi-core gotcha).
        n = await client.ingest(
            "project-papeleria", "inventario.md", text, min_chunk_size=20
        )
        assert n > 0, "short text must still chunk when min_chunk_size is lowered"
        return await client.search(
            "project-papeleria", "¿qué productos tienen el mejor margen?"
        )

    hits = asyncio.run(_run())
    assert hits, "search returned no hits for an ingested corpus"
    # Only one document lives in this corpus, so every hit traces back to it.
    assert all(h["doc_id"] == "inventario.md" for h in hits)
    joined = " ".join(h["text"].lower() for h in hits)
    assert "mochila" in joined or "margen" in joined
