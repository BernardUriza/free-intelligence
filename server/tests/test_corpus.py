"""The corpus: what it stores, what it finds, and who cannot reach it (backlog #46).

Against the REAL Postgres, not a fake, because everything load-bearing here is the
database's: the generated `tsvector`, `websearch_to_tsquery` tolerating a model's
prose, and the `owner` scope that keeps one consumer's shelf out of another's
reach. A fake would pass while any of the three was wrong.
"""

import pytest
import pytest_asyncio

from aire import corpus, db

pytestmark = pytest.mark.asyncio

DOC = ("El semáforo regula el tráfico con luces de colores.\n\n"
       "La luz roja significa alto total para los vehículos.\n\n"
       "La luz verde autoriza el paso.")


@pytest_asyncio.fixture()
async def shelf():
    """A throwaway owner per test, cleaned up after — the table is shared and a
    leftover row would make the next run's ranking depend on the last one's."""
    await corpus.ensure()
    owner = "test-owner-corpus"
    yield owner
    await corpus.drop(owner, "c1")
    await corpus.drop(owner, "c2")
    await corpus.drop("otro-consumer", "c1")
    await db.close()


async def test_a_document_is_stored_in_chunks_and_found_by_its_words(shelf):
    assert await corpus.ingest(shelf, "c1", "semaforos.md", DOC) == 1
    hits = await corpus.search(shelf, "c1", "qué significa la luz roja", 5)
    assert hits and "roja" in hits[0]["text"]
    assert hits[0]["doc_id"] == "semaforos.md" and hits[0]["score"] > 0


async def test_a_query_that_matches_nothing_returns_nothing_not_everything(shelf):
    await corpus.ingest(shelf, "c1", "semaforos.md", DOC)
    assert await corpus.search(shelf, "c1", "criptomonedas", 5) == []


async def test_a_models_prose_query_does_not_blow_up_the_parser(shelf):
    """`to_tsquery` raises on a bare sentence; `websearch_to_tsquery` is why a
    retrieval cannot become an error in the middle of a paid turn."""
    await corpus.ingest(shelf, "c1", "semaforos.md", DOC)
    for query in ('¿de qué color es el "alto"?', "luz roja or verde", "a & b | !c"):
        await corpus.search(shelf, "c1", query, 5)


async def test_reingesting_replaces_and_leaves_no_stale_sentences(shelf):
    await corpus.ingest(shelf, "c1", "doc.md", "La reunión es el lunes.")
    await corpus.ingest(shelf, "c1", "doc.md", "La reunión es el martes.")
    hits = await corpus.search(shelf, "c1", "reunión", 5)
    assert len(hits) == 1 and "martes" in hits[0]["text"]
    assert "lunes" not in hits[0]["text"], "the corrected file must not leave the old one searchable"


async def test_a_corpus_cannot_see_a_sibling_corpus(shelf):
    await corpus.ingest(shelf, "c1", "uno.md", "El semáforo regula el tráfico.")
    await corpus.ingest(shelf, "c2", "dos.md", "El semáforo regula el tráfico.")
    hits = await corpus.search(shelf, "c1", "semáforo", 5)
    assert [h["doc_id"] for h in hits] == ["uno.md"]


async def test_another_owner_cannot_read_this_shelf(shelf):
    """The scope that matters: `owner` never crosses the wire, so a casita of a
    different consumer cannot name this one even knowing the corpus_id."""
    await corpus.ingest(shelf, "c1", "privado.md", "El semáforo regula el tráfico.")
    assert await corpus.search("otro-consumer", "c1", "semáforo", 5) == []


async def test_listing_says_what_is_there(shelf):
    await corpus.ingest(shelf, "c1", "uno.md", DOC)
    docs = await corpus.documents(shelf, "c1")
    assert [d["doc_id"] for d in docs] == ["uno.md"] and docs[0]["chunks"] == 1


async def test_deleting_reports_what_it_removed(shelf):
    await corpus.ingest(shelf, "c1", "uno.md", DOC)
    await corpus.ingest(shelf, "c1", "dos.md", DOC)
    assert await corpus.drop(shelf, "c1", "uno.md") == 1
    assert await corpus.drop(shelf, "c1", "no-existe.md") == 0, \
        "a delete that matched nothing must be distinguishable from one that worked"
    assert await corpus.drop(shelf, "c1") == 1, "the rest of the corpus"
    assert await corpus.documents(shelf, "c1") == []


async def test_top_k_is_bounded(shelf):
    await corpus.ingest(shelf, "c1", "uno.md", DOC)
    assert len(await corpus.search(shelf, "c1", "semáforo", 10_000)) <= corpus.MAX_TOP_K
