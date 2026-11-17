"""A corpus document's versions (#55): the exact text back, the history kept, a
delete appended rather than erased — against the real Postgres, like the corpus.

The write end is the product's own (`corpus.put`, the same call the door and the
tool make); nothing is inserted into the versions table by hand."""

import uuid

import pytest
import pytest_asyncio

from aire import corpus, corpus_versions, db

pytestmark = pytest.mark.asyncio

EXPEDIENTE = "# Sources — niebla\n\n## Verified\n\n- **El 90 %** del bosque.\n\n\n## Inserts\n\n| # | Quién |\n|---|---|\n"


@pytest_asyncio.fixture()
async def shelf():
    owner = f"test-versions-{uuid.uuid4().hex[:8]}"
    yield owner
    await corpus.drop(owner, "exp")
    await db.close()


async def test_the_exact_text_comes_back_blank_lines_and_all(shelf):
    """The chunk table drops the blank lines it splits on; a hook that parses
    tables out of the file needs the bytes it stored, not a reassembly."""
    landed = await corpus.put(shelf, "exp", "casos/niebla/sources-niebla.md", EXPEDIENTE)
    assert landed["changed"] and landed["chunks"] >= 1
    found = await corpus_versions.read(shelf, "exp", "casos/niebla/sources-niebla.md")
    assert found["text"] == EXPEDIENTE and found["version"] == landed["version"]
    assert found["sha256"] == corpus_versions.digest(EXPEDIENTE)


async def test_an_unchanged_push_appends_nothing_and_keeps_the_index(shelf):
    first = await corpus.put(shelf, "exp", "backlog.md", EXPEDIENTE)
    again = await corpus.put(shelf, "exp", "backlog.md", EXPEDIENTE)
    assert again == {**first, "changed": False}
    assert len(await corpus_versions.history(shelf, "exp", "backlog.md")) == 1
    assert await corpus.search(shelf, "exp", "bosque", 3), "the index survived the no-op push"


async def test_an_edit_is_a_new_version_and_the_old_one_stays_readable(shelf):
    old = await corpus.put(shelf, "exp", "lore.md", "La reunión es el lunes.")
    new = await corpus.put(shelf, "exp", "lore.md", "La reunión es el martes.")
    versions = await corpus_versions.history(shelf, "exp", "lore.md")
    assert [v["version"] for v in versions] == [new["version"], old["version"]]
    assert (await corpus_versions.read(shelf, "exp", "lore.md"))["text"].endswith("martes.")
    assert (await corpus_versions.read(shelf, "exp", "lore.md", old["version"]))["text"].endswith("lunes.")
    hits = await corpus.search(shelf, "exp", "lunes", 5)
    assert hits == [], "the index holds only the newest version"


async def test_a_delete_is_a_tombstone_not_an_erasure(shelf):
    kept = await corpus.put(shelf, "exp", "fichas/x.md", "Desde 1998 construye en Zapopan.")
    assert await corpus.drop(shelf, "exp", "fichas/x.md") == 1
    assert await corpus_versions.read(shelf, "exp", "fichas/x.md") is None
    versions = await corpus_versions.history(shelf, "exp", "fichas/x.md")
    assert [v["deleted"] for v in versions] == [True, False]
    assert (await corpus_versions.read(shelf, "exp", "fichas/x.md", kept["version"]))["text"].startswith("Desde")


async def test_dropping_twice_appends_one_tombstone(shelf):
    await corpus.put(shelf, "exp", "a.md", "uno")
    await corpus.put(shelf, "exp", "b.md", "dos")
    await corpus.drop(shelf, "exp")
    await corpus.drop(shelf, "exp")
    for doc in ("a.md", "b.md"):
        assert [v["deleted"] for v in await corpus_versions.history(shelf, "exp", doc)] == [True, False]


async def test_a_document_written_back_after_a_delete_lives_again(shelf):
    await corpus.put(shelf, "exp", "a.md", "uno")
    await corpus.drop(shelf, "exp", "a.md")
    back = await corpus.put(shelf, "exp", "a.md", "uno")
    assert back["changed"] and (await corpus_versions.read(shelf, "exp", "a.md"))["text"] == "uno"


async def test_a_reindex_that_fails_takes_its_version_with_it(shelf, monkeypatch):
    """Review of #55: the version once committed before its reindex, so a failed
    reindex left the index on the old text and the retry — same sha, chunks
    present — reported success while search answered the old sentences forever."""
    from aire import corpus_write

    await corpus.put(shelf, "exp", "d.md", "texto viejo sobre zapotillo")

    async def timeout(*_args):
        raise TimeoutError("statement timeout mid-reindex")

    monkeypatch.setattr(corpus_write, "_reindex", timeout)
    with pytest.raises(TimeoutError):
        await corpus.put(shelf, "exp", "d.md", "texto nuevo sobre niebla")
    monkeypatch.undo()
    assert (await corpus_versions.read(shelf, "exp", "d.md"))["text"].endswith("zapotillo")
    retry = await corpus.put(shelf, "exp", "d.md", "texto nuevo sobre niebla")
    assert retry["changed"]
    assert await corpus.search(shelf, "exp", "niebla", 5)
    assert await corpus.search(shelf, "exp", "zapotillo", 5) == []


async def test_an_index_cut_from_another_text_is_rebuilt_even_when_the_version_is_unchanged(shelf):
    """The index is current only when its chunks carry the newest version's sha:
    an index left on other text (a pre-#55 row reads '') heals on the next push."""
    await corpus.put(shelf, "exp", "d.md", "el agua de la presa")
    async with db.acquire() as conn:
        await conn.execute("UPDATE aire_corpus_chunk SET body='otra cosa', norm='otra cosa', sha256=''"
                           " WHERE owner=$1 AND corpus_id='exp' AND doc_id='d.md'", shelf)
    again = await corpus.put(shelf, "exp", "d.md", "el agua de la presa")
    assert not again["changed"] and again["chunks"] >= 1
    assert await corpus.search(shelf, "exp", "presa", 5)
    assert await corpus.search(shelf, "exp", "cosa", 5) == []


async def test_concurrent_puts_leave_the_index_on_the_newest_version(shelf):
    """Puts racing on one document serialize on its lock: whichever lands last is
    both the newest version and the indexed text, and identical racers append once."""
    import asyncio

    texts = [f"versión {word} del expediente" for word in ("alfa", "beta", "gamma", "delta")] * 3
    await asyncio.gather(*(corpus.put(shelf, "exp", "race.md", t) for t in texts))
    newest = await corpus_versions.read(shelf, "exp", "race.md")
    async with db.acquire() as conn:
        shas = {r["sha256"] for r in await conn.fetch(
            "SELECT sha256 FROM aire_corpus_chunk WHERE owner=$1 AND corpus_id='exp' AND doc_id='race.md'",
            shelf)}
    assert shas == {newest["sha256"]}
    word = newest["text"].split()[1]
    assert [h["doc_id"] for h in await corpus.search(shelf, "exp", word, 5)] == ["race.md"]
    for other in {"alfa", "beta", "gamma", "delta"} - {word}:
        assert await corpus.search(shelf, "exp", other, 5) == [], f"{other} is not the newest text"
    await asyncio.gather(*(corpus.put(shelf, "exp", "same.md", "igual") for _ in range(6)))
    assert len(await corpus_versions.history(shelf, "exp", "same.md")) == 1
