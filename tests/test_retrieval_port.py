"""PR-D RetrievalPort — positive (delegation) + resistance (boundary + gate).

First capability seam (`.claude/plans/capability_seams_retrieval_preset.md`):
the pipeline consumes semantic retrieval through the ``RetrievalPort``
Protocol (``insult/cogs/chat/capability_ports.py``) — finished blocks in,
zero knowledge of ``insult.core.deep_memory``. The rendering policy lives in
the domain service (``build_user_memory_block`` mirrors
``build_film_references_block``); the adapter in ``insult.composition`` owns
only the best-effort boundary and the lexical film gate.

Each behavior gets a positive case AND a resistance case per
.claude/rules/robustness.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from insult.composition import default_retrieval_port

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = REPO_ROOT / "insult" / "cogs" / "chat" / "stages.py"

pytestmark = pytest.mark.asyncio


# --- Resistance: the boundary holds at the AST level -------------------------


def test_stages_does_not_import_deep_memory() -> None:
    """The seam's whole point: stages consumes retrieval through the port and
    never reaches into the domain service — not even via a function-local
    import (which the module-level ratchet in test_arch_import_boundaries
    also catches, but this pins the specific edge PR-D removed)."""
    tree = ast.parse(STAGES.read_text(encoding="utf-8"), filename=str(STAGES))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "deep_memory" in node.module:
            offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            offenders.extend(f"line {node.lineno}: import {a.name}" for a in node.names if "deep_memory" in a.name)
    assert not offenders, "stages.py reaches into deep_memory again:\n" + "\n".join(offenders)


# --- user_memory_block: delegation to the domain-service builder -------------


async def test_user_memory_block_delegates_to_core_builder(monkeypatch) -> None:
    """Positive: the adapter returns exactly what the core builder renders."""
    from insult.core.deep_memory import build_user_memory_block

    async def _fake(*, user_id, query, top_k):
        return [{"chunk_text": "Larisa es la terapeuta de Alex", "similarity": 0.82}]

    monkeypatch.setattr("insult.core.deep_memory.query_user_memory", _fake)
    port = default_retrieval_port()
    via_port = await port.user_memory_block(user_id="U1", text="cuéntame de Larisa Guerrero")
    via_core = await build_user_memory_block(user_id="U1", text="cuéntame de Larisa Guerrero")
    assert via_port == via_core
    assert via_port is not None and "Larisa es la terapeuta de Alex" in via_port


# --- film_references_block: the lexical gate lives INSIDE the port -----------


async def test_film_block_on_topic_delegates(monkeypatch) -> None:
    """Positive: a film-topic message passes the gate and returns the core
    builder's block."""

    async def _fake_block(text):
        return "REFERENCIAS\n- chunk"

    monkeypatch.setattr("insult.composition.build_film_references_block", _fake_block)
    out = await default_retrieval_port().film_references_block("qué opinas de la película Stalker")
    assert out == "REFERENCIAS\n- chunk"


async def test_film_block_off_topic_skips_without_embed(monkeypatch) -> None:
    """Resistance: an off-topic message returns None WITHOUT calling the core
    builder (no wasted embed call) — the gate is the port's job now."""
    called = {"n": 0}

    async def _fake_block(text):
        called["n"] += 1
        return "should not happen"

    monkeypatch.setattr("insult.composition.build_film_references_block", _fake_block)
    out = await default_retrieval_port().film_references_block("hoy comí tacos de canasta")
    assert out is None
    assert called["n"] == 0, "off-topic must not trigger corpus retrieval"


async def test_film_block_failure_returns_none(monkeypatch) -> None:
    """Resistance: a corpus-retrieval error never breaks the turn."""

    async def _boom(text):
        raise RuntimeError("pgvector down")

    monkeypatch.setattr("insult.composition.build_film_references_block", _boom)
    out = await default_retrieval_port().film_references_block("el montaje de esa película es brutal")
    assert out is None
