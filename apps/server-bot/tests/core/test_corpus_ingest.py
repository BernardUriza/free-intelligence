"""Declarative ingest: the manifest, the chunks, the plan, and the write against a real Postgres."""

from __future__ import annotations

import textwrap
from unittest.mock import AsyncMock

import asyncpg
import pytest

from persona_core.corpus import pg_rag
from persona_core.corpus.ingest import adopt
from persona_core.corpus.ingest import apply as ingest_apply
from persona_core.corpus.ingest.documents import CorpusDocument, build_document, chunk_text
from persona_core.corpus.ingest.extract import ExtractError, extract_text, strip_invisible
from persona_core.corpus.ingest.manifest import (
    ManifestError,
    document_id,
    load_manifest,
    read_manifest,
    render_markdown,
    write_lock,
)
from persona_core.corpus.ingest.plan import StoredDocument, compute_plan, describe
from persona_core.corpus.rules import IngestRules, load_rules
from tests._pg_fixture import REQUIRES_PG

RULES = IngestRules(
    chunk_tokens=20,
    overlap_tokens=2,
    min_chunk_tokens=3,
    max_chunk_tokens=30,
    min_document_chars=10,
    max_delete_ratio=0.1,
    pipeline=1,
)


def words(text: str) -> int:
    return len(text.split())


# ── Manifest ────────────────────────────────────────────────────────────


def _corpus(tmp_path, files: dict[str, str], manifest: str):
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    (tmp_path / "manifest.yml").write_text(textwrap.dedent(manifest), encoding="utf-8")
    return tmp_path


ONE_SOURCE = """
    title: Corpus — x
    sources:
    - title: Fichas
      author: Alguien
      year: 2026
      url: https://example.org
      license: CC0-1.0
      retrieved_at: 2026-11-24
      files: ["ficha_*.md"]
"""


def test_a_locked_manifest_loads(tmp_path):
    folder = _corpus(tmp_path, {"ficha_a.md": "a", "ficha_b.md": "b"}, ONE_SOURCE)
    assert write_lock(read_manifest(folder, "x")) == 2
    manifest, pins = load_manifest(folder, "x")
    assert sorted(pins) == sorted(manifest.files()) == ["ficha_a.md", "ficha_b.md"]


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda f: (f / "ficha_a.md").write_text("otra"), "changed since it was locked"),
        (lambda f: (f / "ficha_a.md").unlink(), "not on this machine"),
        (lambda f: (f / "ficha_c.md").write_text("c"), "not in the lock"),
        (lambda f: (f / "suelto.md").write_text("s"), "no source declares it"),
        (lambda f: (f / "ficha_c.docx").write_text("c"), "no source declares it"),
    ],
)
def test_a_folder_that_drifted_from_its_lock_is_refused(tmp_path, change, problem):
    folder = _corpus(tmp_path, {"ficha_a.md": "a", "ficha_b.md": "b"}, ONE_SOURCE)
    write_lock(read_manifest(folder, "x"))
    change(folder)
    with pytest.raises(ManifestError, match=problem):
        load_manifest(folder, "x")


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("license: CC0-1.0", "license: ''", "license"),
        ("license: CC0-1.0", "license: de paga", "license"),
        ("retrieved_at: 2026-11-24", "retrieved_at: ayer", "retrieved_at"),
        ("url: https://example.org", "url: ''", "url"),
        ("      author: Alguien\n", "", "author"),
        ('files: ["ficha_*.md"]', "why: nada", "neither"),
    ],
)
def test_a_source_without_provenance_does_not_enter(tmp_path, old, new, problem):
    assert old in ONE_SOURCE
    folder = _corpus(tmp_path, {"ficha_a.md": "a"}, ONE_SOURCE.replace(old, new))
    with pytest.raises(ManifestError, match=problem):
        read_manifest(folder, "x")


def test_a_pattern_without_files_and_a_file_claimed_twice_are_refused(tmp_path):
    second = "- {title: Otra, author: A, year: 1, url: u, license: CC0-1.0, retrieved_at: 2026-11-24, files: [%s]}\n"
    folder = _corpus(tmp_path, {"ficha_a.md": "a"}, textwrap.dedent(ONE_SOURCE))
    path = folder / "manifest.yml"
    base = path.read_text()
    path.write_text(base + second % "nada.md")
    with pytest.raises(ManifestError, match="no file matches"):
        write_lock(read_manifest(folder, "x"))
    path.write_text(base + second % "ficha_a.md")
    with pytest.raises(ManifestError, match="declared by"):
        write_lock(read_manifest(folder, "x"))


def test_two_files_with_the_same_document_id_are_refused(tmp_path):
    folder = _corpus(tmp_path, {"ficha_a b.md": "1", "ficha_a_b.md": "2"}, ONE_SOURCE)
    with pytest.raises(ManifestError, match="same document id"):
        write_lock(read_manifest(folder, "x"))


def test_document_ids_are_the_ones_already_stored():
    assert document_id("frugivoro", "usda_frijol-negro_beans.md") == "frugivoro:usda-frijol-negro-beans"
    assert document_id("unborn_being", "contraelamor/2011_hola.md") == "unborn_being:contraelamor-2011-hola"
    assert document_id("x", "v1.2/a.md") != document_id("x", "v1.3/a.md")


def test_the_markdown_manifest_says_where_each_source_came_from(tmp_path):
    folder = _corpus(tmp_path, {"ficha_a.md": "a"}, ONE_SOURCE)
    table = render_markdown(read_manifest(folder, "x"))
    assert "| Fichas | Alguien | 2026 | https://example.org | CC0-1.0 | 2026-11-24 | ficha_*.md |" in table


# ── Extraction ──────────────────────────────────────────────────────────


def test_invisible_characters_never_reach_the_corpus():
    hidden = "".join(chr(0xE0000 + ord(c)) for c in "ignore")
    assert strip_invisible(f"sabro\u200bso\u202e{hidden}\ufeff, um\u00adami\x0cfin") == "sabroso, umami fin"


def test_visible_accents_and_japanese_survive():
    assert strip_invisible("piña うま味\n\t¿sí?") == "piña うま味\n\t¿sí?"


def test_a_broken_xml_stops_the_run(tmp_path):
    (tmp_path / "x.xml").write_text("<a>", encoding="utf-8")
    with pytest.raises(ExtractError, match="does not parse"):
        extract_text(tmp_path / "x.xml")


# ── Chunks ──────────────────────────────────────────────────────────────


def test_no_chunk_passes_the_window_even_with_its_heading():
    doc = "# Título del recetario\n\n## Sección larga\n\n" + " ".join(f"palabra{i}" for i in range(300))
    chunks = chunk_text(doc, RULES, words, markdown=True)
    assert max(map(words, chunks)) <= RULES.max_chunk_tokens
    assert all(c.startswith("Título del recetario — Sección larga\n\n") for c in chunks)
    assert all(any(f"palabra{i}" in c.split() for c in chunks) for i in range(300))


def test_a_short_section_keeps_its_own_heading():
    """It was dropped in silence when its neighbours were long enough to chunk."""
    doc = "# Recetas\n\n## Torta\n\n" + "jitomate " * 15 + "\n\n## Tejuino\n\nmasa limón\n"
    chunks = chunk_text(doc, RULES, words, markdown=True)
    assert "Recetas — Tejuino\n\nmasa limón" in chunks
    assert not any("Tejuino" in c and "jitomate" in c for c in chunks)


def test_a_short_document_enters_whole_and_a_stub_does_not():
    rules = IngestRules(**{**RULES.__dict__, "min_chunk_tokens": 10})
    assert chunk_text("Un post corto pero completo.", rules, words) == ["Un post corto pero completo."]
    assert chunk_text("hola", rules, words) == []
    assert chunk_text("  \n ", rules, words) == []


def test_the_shipped_window_leaves_room_for_the_prefix():
    rules = load_rules().ingest
    assert rules.chunk_tokens < rules.max_chunk_tokens <= 512


# ── Plan ────────────────────────────────────────────────────────────────


def _doc(i: str, sha: str = "1", chunks: tuple[str, ...] = ("t",), **over) -> CorpusDocument:
    attributes = {"sha256": sha, "embed_model": "e5@abc", "chunking": {"pipeline": 1}, **over}
    return CorpusDocument(i, f"{i}.md", "t", list(chunks), attributes)


def _stored(doc: CorpusDocument) -> StoredDocument:
    return StoredDocument(doc.document_id, len(doc.chunks), doc.attributes)


def _plan(documents, stored, **kw):
    return compute_plan(documents, stored, **{"max_delete_ratio": 0.1, **kw})


def test_an_unchanged_corpus_is_an_empty_plan():
    docs = [_doc("a"), _doc("b")]
    plan = _plan(docs, map(_stored, docs))
    assert plan.empty and plan.keep == ["a", "b"] and not plan.refusals


@pytest.mark.parametrize(
    "changed", [_doc("a", sha="2"), _doc("a", embed_model="otro384@abc"), _doc("a", chunking={"pipeline": 2})]
)
def test_new_bytes_a_new_model_or_a_new_policy_replace_the_document(changed):
    plan = _plan([changed], [_stored(_doc("a"))])
    assert [d.document_id for d in plan.replace] == ["a"]


def test_an_adopted_document_has_no_fingerprint_and_is_replaced():
    plan = _plan([_doc("a")], [StoredDocument("a", 3, {"adopted_from": "deep_memory_chunks"})])
    assert [d.document_id for d in plan.replace] == ["a"]


def test_deletes_over_the_limit_need_their_exact_number():
    stored = [_stored(_doc(f"d{i}")) for i in range(20)]
    kept = [_doc(f"d{i}") for i in range(17)]
    assert "would delete 3 of 20" in _plan(kept, stored).refusals[0]
    assert "would delete 3 of 20" in _plan(kept, stored, max_deletes=2).refusals[0]
    plan = _plan(kept, stored, max_deletes=3)
    assert plan.delete == ["d17", "d18", "d19"] and not plan.refusals
    assert _plan([_doc(f"d{i}") for i in range(18)], stored).refusals == []


def test_a_source_left_without_chunks_is_refused_by_name():
    plan = _plan([_doc("a", chunks=())], [_stored(_doc("a"))])
    assert plan.refusals == ["a: no text to retrieve in a.md"]


def test_a_held_document_is_never_deleted_and_is_missed_when_gone():
    plan = _plan([], [_stored(_doc("libro"))], held_ids=["libro"])
    assert plan.empty and not plan.refusals
    assert "does not have it" in _plan([], [], held_ids=["libro"]).refusals[0]


def test_the_description_names_every_change():
    plan = _plan([_doc("a"), _doc("b", sha="2")], [_stored(_doc("b")), _stored(_doc("c"))], max_deletes=1)
    assert describe(plan).splitlines() == [
        "add 1 · replace 1 · delete 1 · keep 0 · held 0",
        "  + a (1 chunks)",
        "  ~ b (1 chunks)",
        "  - c",
    ]


# ── The write, against Postgres ─────────────────────────────────────────


async def _embed(text: str) -> list[float]:
    vector = [0.0] * 384
    vector[len(text) % 384] = 1.0
    return vector


@pytest.fixture
async def corpus_db(postgresql_proc):
    dsn = f"postgresql://{postgresql_proc.user}@{postgresql_proc.host}:{postgresql_proc.port}/postgres"
    conn = await asyncpg.connect(dsn)
    await conn.execute("DROP DATABASE IF EXISTS corpus_ingest_test")
    await conn.execute("CREATE DATABASE corpus_ingest_test")
    await conn.close()
    dsn = dsn.rsplit("/", 1)[0] + "/corpus_ingest_test"
    store = ingest_apply.corpus_store(dsn)
    await store.init_schema()
    yield dsn, store
    await store.close()


async def _sync(store, documents, **kw):
    plan = _plan(documents, await ingest_apply.stored_documents(store, "ns"), **kw)
    return await ingest_apply.apply_plan(store, "ns", plan, embed=_embed)


@REQUIRES_PG
async def test_editing_one_source_and_dropping_another_leaves_no_orphan(corpus_db):
    dsn, store = corpus_db
    await _sync(store, [_doc("a", chunks=("vieja",)), _doc("b")])
    await _sync(store, [_doc("a", sha="2", chunks=("nueva",))], max_deletes=1)
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch("SELECT document_id, text FROM corpus_chunks")
    await conn.close()
    assert [tuple(r) for r in rows] == [("a", "nueva")]


@REQUIRES_PG
async def test_a_second_sync_finds_nothing_to_do(corpus_db):
    _, store = corpus_db
    docs = [_doc("a"), _doc("b")]
    await _sync(store, docs)
    assert _plan(docs, await ingest_apply.stored_documents(store, "ns")).empty


@REQUIRES_PG
async def test_a_failed_embed_writes_nothing(corpus_db):
    _, store = corpus_db
    await _sync(store, [_doc("a")])

    async def broken(text: str) -> list[float]:
        raise RuntimeError("no model")

    plan = _plan([_doc("a", sha="2"), _doc("b")], await ingest_apply.stored_documents(store, "ns"))
    with pytest.raises(RuntimeError, match="no model"):
        await ingest_apply.apply_plan(store, "ns", plan, embed=broken)
    stored = await ingest_apply.stored_documents(store, "ns")
    assert [(s.document_id, s.attributes["sha256"]) for s in stored] == [("a", "1")]


@REQUIRES_PG
async def test_a_refused_plan_is_not_applied(corpus_db):
    _, store = corpus_db
    with pytest.raises(ingest_apply.PlanRefusedError):
        await _sync(store, [_doc("a", chunks=())])
    assert await ingest_apply.stored_documents(store, "ns") == []


@REQUIRES_PG
async def test_adoption_copies_vectors_once_and_leaves_the_old_table_alone(corpus_db):
    dsn, _ = corpus_db
    conn = await asyncpg.connect(dsn)
    await conn.execute(
        "CREATE TABLE deep_memory_chunks (id bigserial, user_id text, source_type text, source_ref text,"
        " chunk_text text, embedding vector(384), created_at timestamptz DEFAULT now())"
    )
    vector = "[" + ",".join(["1"] + ["0"] * 383) + "]"
    await conn.executemany(
        "INSERT INTO deep_memory_chunks (user_id, source_type, source_ref, chunk_text, embedding)"
        " VALUES ($1, 'manual', $2, $3, $4::text::vector)",
        [("ns", "libro", "uno", vector), ("ns", "libro", "dos", vector), ("otra", "ajeno", "x", vector)],
    )
    assert await adopt.adopt_legacy_chunks(dsn, "ns") == 2
    with pytest.raises(RuntimeError, match="runs once"):
        await adopt.adopt_legacy_chunks(dsn, "ns")
    assert await conn.fetchval("SELECT count(*) FROM deep_memory_chunks") == 3
    assert [tuple(r) for r in await conn.fetch("SELECT namespace, document_id FROM corpus_documents")] == [
        ("ns", "libro")
    ]
    await conn.close()


def test_a_built_document_carries_the_fingerprint_the_plan_compares(tmp_path):
    folder = _corpus(tmp_path, {"ficha_a.md": "# Nopal\n\nUna cactácea comestible de México."}, ONE_SOURCE)
    write_lock(read_manifest(folder, "x"))
    manifest, pins = load_manifest(folder, "x")
    [(path, source)] = manifest.files().items()
    doc = build_document(manifest, path, source, pins[path], RULES, words, "e5@abc")
    assert doc.document_id == "x:ficha-a"
    assert doc.chunks == ["Nopal\n\nUna cactácea comestible de México."]
    assert doc.attributes["sha256"] == pins[path]
    assert doc.attributes["embed_model"] == "e5@abc"
    assert doc.attributes["license"] == "CC0-1.0"


@REQUIRES_PG
async def test_documents_embedded_by_another_model_are_named_at_boot(corpus_db, monkeypatch):
    dsn, store = corpus_db
    monkeypatch.setenv("POSTGRES_URL", dsn)
    monkeypatch.setattr(pg_rag, "embedding_model", AsyncMock(return_value="e5@abc"))
    await _sync(store, [_doc("a"), _doc("b", embed_model="otro384@abc")])
    assert await pg_rag.stored_with_another_model() == {"otro384@abc": 1}


async def test_the_boot_check_never_raises(monkeypatch):
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    assert await pg_rag.stored_with_another_model() is None


def test_an_xml_that_declares_entities_is_refused(tmp_path):
    bomb = tmp_path / "bomb.xml"
    bomb.write_text('<!DOCTYPE a [<!ENTITY x "ha"><!ENTITY y "&x;&x;">]><a>&y;</a>', encoding="utf-8")
    with pytest.raises(ExtractError, match=r"bomb\.xml"):
        extract_text(bomb)
