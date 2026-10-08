"""`search_facts_semantic` enforces its limit on EVERY path.

2026-07-23: a voice note whose embedding failed came back from the store's own
unranked fallback with ALL 4115 of Bernard's facts. The relevant-facts block
inflated the runner payload to 376,300 chars and the turn died on a 422
(`user_text` > 256000) — the bot went mute and the failure was visible only in
the logs.

Mutator rule: positive (a store that ignores `limit` is capped here) +
resistance (a normally-ranked result under the limit passes through untouched,
and the exception path is capped too).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from persona_core.memory.repositories.facts import FactsRepository


def _fact(text: str):
    return MagicMock(fact=text, category="general", source="auto", id=1)


def _repo(store) -> FactsRepository:
    repo = FactsRepository.__new__(FactsRepository)
    repo._get_store = lambda: store
    return repo


async def test_store_ignoring_limit_is_capped():
    store = MagicMock()
    store.semantic_search = AsyncMock(return_value=[_fact(f"dato {i}") for i in range(4115)])
    out = await _repo(store).search_facts_semantic("907", "prueba de audio", limit=8)
    assert len(out) == 8


async def test_ranked_result_under_the_limit_passes_through():
    store = MagicMock()
    store.semantic_search = AsyncMock(return_value=[_fact("dato a"), _fact("dato b")])
    out = await _repo(store).search_facts_semantic("907", "prueba", limit=8)
    assert [o["fact"] for o in out] == ["dato a", "dato b"]


async def test_exception_fallback_is_capped_too():
    store = MagicMock()
    store.semantic_search = AsyncMock(side_effect=RuntimeError("pgvector down"))
    repo = _repo(store)
    with patch.object(
        FactsRepository,
        "get_facts",
        new=AsyncMock(return_value=[{"fact": f"dato {i}"} for i in range(4115)]),
    ):
        out = await repo.search_facts_semantic("907", "prueba", limit=8)
    assert len(out) == 8
