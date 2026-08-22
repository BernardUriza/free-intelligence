"""`quota()` is the DENOMINATOR that `stats()` is a numerator of.

A consumer rendering "N% of capacity used" needs both halves. Before this it had
only usage, and the only way to the ceilings was reaching into `_rag` — a private
attribute whose shape is fi-core's business.

The case that matters is the unset one: `None` means UNLIMITED, and it must
arrive as `None` so the consumer can say "no cap" instead of dividing by an
invented ceiling.
"""

from __future__ import annotations

import pytest

from fi_runner.rag_store import RagStoreClient


@pytest.fixture(autouse=True)
def hdf5_store(monkeypatch, tmp_path):
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "quota.h5"))


def test_no_quota_configured_reports_none_not_zero() -> None:
    assert RagStoreClient().quota() == {"max_docs": None, "max_bytes": None}, (
        "zero would read as a full corpus; None is the honest 'unbounded'"
    )


def test_configured_quotas_are_reported(monkeypatch) -> None:
    monkeypatch.setenv("FI_RAG_MAX_DOCS", "50")
    monkeypatch.setenv("FI_RAG_MAX_BYTES", "1048576")

    assert RagStoreClient().quota() == {"max_docs": 50, "max_bytes": 1048576}


@pytest.mark.asyncio
async def test_usage_and_ceiling_are_the_two_halves_of_the_meter(monkeypatch) -> None:
    monkeypatch.setenv("FI_RAG_MAX_BYTES", "1048576")
    client = RagStoreClient()
    await client.ingest("corpus-1", "doc.md", "Lamina diez pesos. " * 60, min_chunk_size=20)

    used = (await client.stats("corpus-1"))["bytes"]
    cap = client.quota()["max_bytes"]

    assert 0 < used < cap, "both halves have to be real numbers for a meter to mean anything"
