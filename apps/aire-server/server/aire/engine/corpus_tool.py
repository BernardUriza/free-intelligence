"""The `rag_store` in-process MCP server — the consumer's documents, searchable.

The registry's fourth tenant (backlog #46). A consumer uploads files into a
corpus; the agent searches it mid-turn instead of guessing. The storage and the
retrieval are `aire/corpus.py` — Postgres full-text search over the owner's own
database, for the reason documented there.

The tool NAMES are fi-core's, exactly. A consumer's prompt binding tells the model
to "call search_documents IMMEDIATELY", so a rename here would leave the model
reaching for a tool that does not answer — which is the failure this whole item
exists to end, reintroduced from the other side.

SCOPE: the `owner` is derived from the casita's `@base` (#36) — every chat of one
consumer shares one shelf, and a casita of a different consumer cannot name it,
because the owner never crosses the wire. Within that shelf `corpus_id` is the
consumer's, exactly as its local store had it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ..agent_sdk import mcp_server as create_sdk_mcp_server
from ..agent_sdk import tool

from .. import corpus

SERVER_NAME = "rag_store"
_CORPUS = {"corpus_id": str}


def owner_of(cwd: str) -> str:
    """The shelf this casita writes to: the base it inherits from, or itself.

    Read off disk, never off the wire. A chat casita is born with `@base og118`
    (#36), so every chat of that consumer resolves to the same shelf; a casita
    with no base — a canary, a probe — owns only its own."""
    name = Path(cwd).name
    try:
        head = (Path(cwd) / "CLAUDE.md").read_text(encoding="utf-8").lstrip().split("\n", 1)[0]
    except OSError:
        return name
    if not head.startswith("@base "):
        return name
    from ..names import InvalidName, clean
    try:
        return clean("project", head[6:].strip())
    except InvalidName:
        return name


def _reply(payload: Any, failed: bool = False) -> dict[str, Any]:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    out: dict[str, Any] = {"content": [{"type": "text", "text": body}]}
    if failed:
        out["is_error"] = True
    return out


def _text(args: dict[str, Any], key: str) -> str:
    return str(args.get(key) or "").strip()


async def _ingest(owner: str, a: dict[str, Any]) -> Any:
    body = str(a.get("text") or "")
    if not body.strip():
        raise ValueError("text is required — an empty document indexes nothing")
    n = await corpus.ingest(owner, _text(a, "corpus_id"), _text(a, "doc_id"), body)
    return {"doc_id": _text(a, "doc_id"), "chunks": n, "replaced": True}


async def _search(owner: str, a: dict[str, Any]) -> Any:
    try:
        top_k = int(a.get("top_k") or 5)
    except (TypeError, ValueError):
        top_k = 5
    hits = await corpus.search(owner, _text(a, "corpus_id"), _text(a, "query"), top_k)
    return hits if hits else "No document in this corpus matches that query."


async def _drop_doc(owner: str, a: dict[str, Any]) -> Any:
    removed = await corpus.drop(owner, _text(a, "corpus_id"), _text(a, "doc_id"))
    return {"doc_id": _text(a, "doc_id"), "chunks_removed": removed}


async def _drop_corpus(owner: str, a: dict[str, Any]) -> Any:
    return {"corpus_id": _text(a, "corpus_id"),
            "chunks_removed": await corpus.drop(owner, _text(a, "corpus_id"))}


# (name, description, schema, op) — `op` takes the resolved owner and the raw args.
TOOLS: tuple[tuple[str, str, dict, Callable], ...] = (
    ("search_documents",
     "Search the active project's uploaded documents and get the passages that "
     "match, best first. Matches on WORDS, so query with the terms the document "
     "would use. Pass the active `corpus_id`.",
     {**_CORPUS, "query": str, "top_k": int}, _search),
    ("ingest_document",
     "Store a document in a corpus under `doc_id`, chunked and indexed. Ingesting "
     "the same `doc_id` again REPLACES it, so a corrected file leaves no stale "
     "sentences behind.",
     {**_CORPUS, "doc_id": str, "text": str}, _ingest),
    ("list_documents", "List what a corpus holds: each `doc_id`, its chunk count and when it landed.",
     _CORPUS, lambda o, a: corpus.documents(o, _text(a, "corpus_id"))),
    ("delete_document", "Remove one document from a corpus.",
     {**_CORPUS, "doc_id": str}, _drop_doc),
    ("delete_corpus", "Remove every document in a corpus. This cannot be undone.",
     _CORPUS, _drop_corpus),
)


def _bind(owner: str, spec: tuple) -> Any:
    """One table row into one SDK tool, with a failure handed BACK TO THE MODEL as
    text. A dead database mid-turn must cost the retrieval, never the answer the
    caller is already paying for — the same law the mirror and the ledger run
    under, applied where the model can still say what it could not find."""
    name, description, schema, op = spec

    async def run(args: dict[str, Any]) -> dict[str, Any]:
        if not _text(args, "corpus_id"):
            return _reply("corpus_id is required — name the active project's corpus", True)
        try:
            return _reply(await op(owner, args))
        except ValueError as exc:
            return _reply(str(exc), True)
        except Exception as exc:  # noqa: BLE001 — a tool reports its failure as text
            return _reply(f"the corpus is unreachable right now ({type(exc).__name__})", True)

    run.__name__ = name
    return tool(name, description, schema)(run)


def build_tools(owner: str) -> list[Any]:
    """Every row of the table bound to one shelf. Named so the server and its
    tests reach the tools the same way — a test that rebuilt them itself could
    pass while the server shipped a different set."""
    return [_bind(owner, spec) for spec in TOOLS]


def build_corpus_server(_project_key: str, cwd: str = "") -> Any:
    """The `rag_store` server for whichever consumer owns this casita."""
    return create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0",
                                 tools=build_tools(owner_of(cwd)))
