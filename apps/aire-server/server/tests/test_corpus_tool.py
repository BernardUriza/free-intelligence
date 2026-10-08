"""The door's half of `rag_store` (backlog #46): what the model may ask, what it
gets, and — the one that matters — which shelf it lands on.

The scope is derived from DISK, never from the wire. These pin that: a chat casita
resolves to the base it inherits, so every chat of one consumer shares a shelf, and
nothing the model can say moves it to another's.
"""

import json
from pathlib import Path

import pytest
import pytest_asyncio

from aire import corpus, db
from aire.engine.corpus_tool import (SERVER_NAME, TOOLS, build_corpus_server,
                                     build_tools, owner_of)
from aire.engine.tools import REGISTRY, clean_tools, resolve

FI_CORE_NAMES = {"search_documents", "ingest_document", "list_documents",
                 "delete_document", "delete_corpus"}


def _casita(tmp_path: Path, name: str, claude_md: str | None = None) -> str:
    home = tmp_path / name
    home.mkdir()
    if claude_md is not None:
        (home / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    return str(home)


def test_the_tool_names_are_fi_cores_exactly():
    """A consumer's prompt binding orders the model to call `search_documents`.
    Renaming one here leaves it reaching for a tool that does not answer."""
    assert {name for name, _, _, _ in TOOLS} == FI_CORE_NAMES


def test_the_registry_ships_it_and_the_wire_can_name_it():
    assert clean_tools(["rag_store"]) == ["rag_store"]
    servers, allowed = resolve(["rag_store"], "pk", "/tmp")
    assert servers["rag_store"]["name"] == SERVER_NAME and allowed == ["mcp__rag_store"]
    assert "rag_store" in REGISTRY


def test_a_chat_casita_lands_on_the_base_it_inherits(tmp_path):
    """#36 births a chat thin with `@base og118`, so every chat of that consumer
    writes to one shelf — which is what makes a project's documents visible from
    more than the chat that uploaded them."""
    assert owner_of(_casita(tmp_path, "og118-chat-a", "@base og118\n\nsoul")) == "og118"
    assert owner_of(_casita(tmp_path, "og118-chat-b", "@base og118\n")) == "og118"


def test_a_casita_with_no_base_owns_only_itself(tmp_path):
    assert owner_of(_casita(tmp_path, "canary", "persona sin base")) == "canary"
    assert owner_of(_casita(tmp_path, "sin-md")) == "sin-md"


def test_a_hostile_base_cannot_name_another_shelf(tmp_path):
    """The base is a name, and it goes through the same allowlist a project does:
    a traversal in a CLAUDE.md must not reach out of the workspaces root."""
    assert owner_of(_casita(tmp_path, "malo", "@base ../../etc\n")) == "malo"


def _handlers(cwd: str) -> dict:
    """One casita's tools, reached exactly as the server reaches them."""
    return {t.name: t.handler for t in build_tools(owner_of(cwd))}


def _body(result) -> str:
    return result["content"][0]["text"]


@pytest_asyncio.fixture()
async def shelves(tmp_path):
    await corpus.ensure()
    a = _handlers(_casita(tmp_path, "og118-chat-a", "@base og118-test\n"))
    b = _handlers(_casita(tmp_path, "og118-chat-b", "@base og118-test\n"))
    other = _handlers(_casita(tmp_path, "otro-test", "persona propia"))
    yield a, b, other
    await corpus.drop("og118-test", "proj-1")
    await corpus.drop("otro-test", "proj-1")
    await db.close()


@pytest.mark.asyncio
async def test_a_second_chat_of_the_same_consumer_reads_what_the_first_uploaded(shelves):
    a, b, _ = shelves
    await a["ingest_document"]({"corpus_id": "proj-1", "doc_id": "notas.md",
                                "text": "El presupuesto aprobado fue de 45 mil pesos."})
    hits = json.loads(_body(await b["search_documents"]({"corpus_id": "proj-1",
                                                         "query": "presupuesto aprobado"})))
    assert hits and "45 mil" in hits[0]["text"]


@pytest.mark.asyncio
async def test_another_consumer_reads_nothing_even_naming_the_same_corpus(shelves):
    a, _, other = shelves
    await a["ingest_document"]({"corpus_id": "proj-1", "doc_id": "privado.md",
                                "text": "El presupuesto aprobado fue de 45 mil pesos."})
    out = await other["search_documents"]({"corpus_id": "proj-1", "query": "presupuesto"})
    assert "No document" in _body(out)


@pytest.mark.asyncio
async def test_a_miss_says_so_instead_of_returning_an_empty_list(shelves):
    """The model reads this text. `[]` invites it to say nothing was found without
    knowing whether it searched at all."""
    a, _, _ = shelves
    out = await a["search_documents"]({"corpus_id": "proj-1", "query": "criptomonedas"})
    assert "No document" in _body(out) and out.get("is_error") is None


@pytest.mark.asyncio
async def test_a_call_with_no_corpus_id_is_refused_before_it_touches_the_database(shelves):
    a, _, _ = shelves
    out = await a["search_documents"]({"query": "lo que sea"})
    assert out["is_error"] is True and "corpus_id" in _body(out)


@pytest.mark.asyncio
async def test_an_empty_document_is_refused(shelves):
    a, _, _ = shelves
    out = await a["ingest_document"]({"corpus_id": "proj-1", "doc_id": "vacio.md", "text": "   "})
    assert out["is_error"] is True


@pytest.mark.asyncio
async def test_listing_and_deleting_report_real_counts(shelves):
    a, _, _ = shelves
    await a["ingest_document"]({"corpus_id": "proj-1", "doc_id": "uno.md", "text": "hola mundo"})
    docs = json.loads(_body(await a["list_documents"]({"corpus_id": "proj-1"})))
    assert [d["doc_id"] for d in docs] == ["uno.md"]
    gone = json.loads(_body(await a["delete_document"]({"corpus_id": "proj-1", "doc_id": "uno.md"})))
    assert gone["chunks_removed"] == 1
