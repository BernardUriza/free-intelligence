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
