"""Ingest Bernard's ChatGPT conversation history into deep_memory_chunks.

Step 3 of the ChatGPT → own-BDD sovereignty migration (steps 1+2 = filter +
facts, already done). This ingests the CONVERSATION BODIES of the 965 `keep=True`
conversations from `data/chatgpt_export/` as retrievable RAG chunks, with a
HYBRID privacy routing decided by Bernard (2026-06-03):

  - "live" categories  → user_id=<BERNARD_DISCORD_ID>   (auto-recalled by
    `deep_memory.query_user_memory` when Bernard talks; the bot may surface
    them in a shared channel, so ONLY non-intimate topics go here).
  - "intimate" categories → user_id="__chatgpt_archive__" (a synthetic
    namespace `query_user_memory` never touches — stored in the BDD for
    sovereignty / on-demand recall, but NEVER auto-injected into a public
    turn). Same shape as FILM_CORPUS_NAMESPACE: present but not auto-served.

Routing (category from data/chatgpt_export/classification.json `cat`):
  LIVE    = trabajo, intereses, creatividad, valores, comida, viajes,
            opiniones, espiritual, historia, finanzas, tecnico, personalidad, otro
  ARCHIVE = emocional, salud, relaciones, sexualidad, sensible

Pipeline per conversation: walk the ChatGPT `mapping` tree → user/assistant
text in chronological order → `[title]\nBernard: …\nChatGPT: …` document →
fi_core.rag PARAGRAPH_AWARE chunking → Azure OpenAI ada-002 embeddings → INSERT
into deep_memory_chunks. source_ref = "chatgpt:<conversation_id>" so the agent
can cite a specific past conversation. Idempotent + resumable via the schema's
unique index on (user_id, source_ref, md5(chunk_text)) — re-running never
re-embeds what's already stored.

CLI:
    conda activate discord-bot
    python scripts/ingest_chatgpt_history.py --dry-run     # parse + chunk, no embed/insert
    python scripts/ingest_chatgpt_history.py               # real ingest
    python scripts/ingest_chatgpt_history.py --only-live   # skip the archive namespace
    python scripts/ingest_chatgpt_history.py --only-archive

Env required (same as ingest_film_corpus.py):
    POSTGRES_URL, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY,
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT (defaults to text-embedding-ada-002)

Run helper from this Mac (env injected from Azure secrets):
    POSTGRES_URL=$(az containerapp secret show -n discord-bot -g insult-rg \\
        --secret-name postgres-url --query value -o tsv) \\
    AZURE_OPENAI_ENDPOINT=https://northcentralus.api.cognitive.microsoft.com/ \\
    AZURE_OPENAI_KEY=$(az cognitiveservices account keys list \\
        -n insult-openai -g insult-rg --query key1 -o tsv) \\
    python scripts/ingest_chatgpt_history.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import asyncpg

# Run from the repo root regardless of where the script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

BERNARD_DISCORD_ID = "907264175246569543"
ARCHIVE_NAMESPACE = "__chatgpt_archive__"

LIVE_CATS = frozenset(
    {
        "trabajo",
        "intereses",
        "creatividad",
        "valores",
        "comida",
        "viajes",
        "opiniones",
        "espiritual",
        "historia",
        "finanzas",
        "tecnico",
        "personalidad",
        "otro",
    }
)
ARCHIVE_CATS = frozenset({"emocional", "salud", "relaciones", "sexualidad", "sensible"})

_EXPORT_DIR = _REPO_ROOT / "data" / "chatgpt_export"
_EXTRACTED = _EXPORT_DIR / "extracted"
_CLASSIFICATION = _EXPORT_DIR / "classification.json"


# ---------------------------------------------------------------------------
# Parsing the ChatGPT export
# ---------------------------------------------------------------------------


def load_classification() -> dict[str, str]:
    """Return {conversation_id: category} for the keep=True conversations only."""
    items = json.loads(_CLASSIFICATION.read_text())
    out: dict[str, str] = {}
    for it in items:
        if it.get("keep"):
            cid = it.get("id") or it.get("conversation_id")
            if cid:
                out[cid] = (it.get("cat") or "otro").strip().lower()
    return out


def _namespace_for(cat: str) -> str | None:
    if cat in LIVE_CATS:
        return BERNARD_DISCORD_ID
    if cat in ARCHIVE_CATS:
        return ARCHIVE_NAMESPACE
    return None  # unknown category → skip (don't guess where intimate data goes)


def extract_conv_text(conv: dict) -> str:
    """Flatten a ChatGPT conversation's `mapping` tree into a readable transcript.

    Collects user + assistant text messages, orders them chronologically by
    create_time (nodes with null time keep their tree order via a stable sort),
    and formats as `Bernard: …` / `ChatGPT: …`. Non-text parts (images, tool
    calls, system/tool roles) are skipped. The title is prepended so the first
    chunk carries topic context.
    """
    mapping = conv.get("mapping") or {}
    rows: list[tuple[float, int, str]] = []
    for order, (_node_id, node) in enumerate(mapping.items()):
        msg = (node or {}).get("message")
        if not msg:
            continue
        role = ((msg.get("author") or {}).get("role")) or ""
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content") or {}
        if content.get("content_type") != "text":
            continue
        parts = content.get("parts") or []
        text = "\n".join(p for p in parts if isinstance(p, str) and p.strip()).strip()
        if not text:
            continue
        ts = msg.get("create_time")
        ts = float(ts) if isinstance(ts, int | float) else 0.0
        speaker = "Bernard" if role == "user" else "ChatGPT"
        rows.append((ts, order, f"{speaker}: {text}"))

    rows.sort(key=lambda r: (r[0], r[1]))
    if not rows:
        return ""

    title = (conv.get("title") or "").strip()
    header = f"[Conversación: {title}]\n\n" if title else ""
    return header + "\n\n".join(r[2] for r in rows)


def iter_conversations():
    """Yield every conversation dict across the conversations-*.json shards."""
    for shard in sorted(_EXTRACTED.glob("conversations-*.json")):
        data = json.loads(shard.read_text())
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            yield data


# ---------------------------------------------------------------------------
# DB + embedding plumbing (mirrors ingest_film_corpus.py — same robustness)
# ---------------------------------------------------------------------------

_EMBED_CONCURRENCY = 6  # Azure embeddings quota is 10/350 — 6 in flight is safe
_EMBED_RETRIES = 3
_PG_CONNECT_ATTEMPTS = 6


async def _embed_with_retry(chunk: str, sem: asyncio.Semaphore) -> list[float] | None:
    from insult.core.deep_memory import embed_text

    async with sem:
        for attempt in range(_EMBED_RETRIES):
            vec = await embed_text(chunk)
            if vec is not None:
                return vec
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


async def _connect_retry(pg_url: str) -> asyncpg.Connection:
    from pgvector.asyncpg import register_vector

    last: Exception | None = None
    for attempt in range(_PG_CONNECT_ATTEMPTS):
        try:
            conn = await asyncpg.connect(pg_url, timeout=20)
            await register_vector(conn)
            return conn
        except Exception as e:
            last = e
            print(f"    pg connect retry {attempt + 1}/{_PG_CONNECT_ATTEMPTS}: {type(e).__name__}", flush=True)
            await asyncio.sleep(3 * (attempt + 1))
    raise RuntimeError(f"could not connect to Postgres after {_PG_CONNECT_ATTEMPTS} attempts: {last}")


async def _load_existing_namespace(pg_url: str, namespace: str) -> set[tuple[str, str]]:
    """Pre-load (source_ref, chunk_text) already stored for a namespace so a
    resumed run skips them. One query for the whole namespace beats 600 per-conv
    round-trips over the flaky residential link."""
    conn = await _connect_retry(pg_url)
    try:
        rows = await conn.fetch(
            "SELECT source_ref, chunk_text FROM deep_memory_chunks WHERE user_id = $1",
            namespace,
        )
        return {(r["source_ref"], r["chunk_text"]) for r in rows}
    finally:
        await conn.close()


async def _insert_batch(pg_url: str, rows: list[tuple]) -> int:
    for attempt in range(_PG_CONNECT_ATTEMPTS):
        conn = await _connect_retry(pg_url)
        try:
            await conn.executemany(
                """
                INSERT INTO deep_memory_chunks
                  (user_id, source_type, source_ref, chunk_text, embedding)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, source_ref, md5(chunk_text)) DO NOTHING
                """,
                rows,
            )
            return len(rows)
        except Exception as e:
            print(f"    batch insert retry {attempt + 1}: {type(e).__name__}", flush=True)
            await asyncio.sleep(3 * (attempt + 1))
        finally:
            await conn.close()
    print("    WARN: batch failed after retries, leaving for next resume", flush=True)
    return 0


async def _ingest_namespace(pg_url: str, namespace: str, items: list[tuple[str, str]]) -> int:
    """Embed + insert all (source_ref, chunk_text) pairs for one namespace.

    Resumable: pre-loads what's already stored and skips it. Parallel embed
    under a concurrency gate; batched, reconnect-tolerant inserts."""
    existing = await _load_existing_namespace(pg_url, namespace)
    pending = [(sr, ct) for (sr, ct) in items if (sr, ct) not in existing]
    print(f"  namespace {namespace}: {len(existing)} stored, {len(pending)} new to embed")
    if not pending:
        return 0

    sem = asyncio.Semaphore(_EMBED_CONCURRENCY)
    inserted = 0
    batch = 120
    for start in range(0, len(pending), batch):
        slice_ = pending[start : start + batch]
        vecs = await asyncio.gather(*(_embed_with_retry(ct, sem) for (_sr, ct) in slice_))
        rows = [(namespace, "manual", sr, ct, v) for (sr, ct), v in zip(slice_, vecs, strict=False) if v is not None]
        got = await _insert_batch(pg_url, rows) if rows else 0
        inserted += got
        failed = len(slice_) - len(rows)
        print(
            f"    {min(start + batch, len(pending))}/{len(pending)} embedded "
            f"(+{got} inserted{f', {failed} embed-failed' if failed else ''})",
            flush=True,
        )
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    p.add_argument("--dry-run", action="store_true", help="Parse + chunk and print stats; no embed/insert.")
    p.add_argument("--only-live", action="store_true", help="Ingest only the live (user_id) namespace.")
    p.add_argument("--only-archive", action="store_true", help="Ingest only the __chatgpt_archive__ namespace.")
    p.add_argument("--chunk-size", type=int, default=400)
    p.add_argument("--overlap", type=int, default=50)
    return p.parse_args()


async def main() -> int:
    args = parse_args()

    pg_url = os.environ.get("POSTGRES_URL")
    if not args.dry_run and not pg_url:
        print("FATAL: POSTGRES_URL not set", file=sys.stderr)
        return 2
    if not args.dry_run and (not os.environ.get("AZURE_OPENAI_ENDPOINT") or not os.environ.get("AZURE_OPENAI_KEY")):
        print("FATAL: AZURE_OPENAI_ENDPOINT / KEY not set", file=sys.stderr)
        return 2

    from insult.core.deep_memory import chunk_text_for_embedding

    classification = load_classification()
    print(f"classification: {len(classification)} keep=True conversations")

    # namespace → list[(source_ref, chunk_text)]
    buckets: dict[str, list[tuple[str, str]]] = {BERNARD_DISCORD_ID: [], ARCHIVE_NAMESPACE: []}
    stats = {"convs_live": 0, "convs_archive": 0, "convs_empty": 0, "convs_unknown_cat": 0, "convs_not_kept": 0}

    for conv in iter_conversations():
        cid = conv.get("conversation_id") or conv.get("id")
        cat = classification.get(cid)
        if cat is None:
            stats["convs_not_kept"] += 1
            continue
        namespace = _namespace_for(cat)
        if namespace is None:
            stats["convs_unknown_cat"] += 1
            continue
        text = extract_conv_text(conv)
        if not text.strip():
            stats["convs_empty"] += 1
            continue
        chunks = chunk_text_for_embedding(text, chunk_size=args.chunk_size, overlap=args.overlap)
        source_ref = f"chatgpt:{cid}"
        for ch in chunks:
            ch = ch.strip()
            if ch:
                buckets[namespace].append((source_ref, ch))
        stats["convs_live" if namespace == BERNARD_DISCORD_ID else "convs_archive"] += 1

    print(
        f"\nrouting: {stats['convs_live']} live convs → {len(buckets[BERNARD_DISCORD_ID])} chunks | "
        f"{stats['convs_archive']} archive convs → {len(buckets[ARCHIVE_NAMESPACE])} chunks"
    )
    print(
        f"skipped: {stats['convs_empty']} empty, {stats['convs_unknown_cat']} unknown-cat, "
        f"{stats['convs_not_kept']} not-kept"
    )

    if args.dry_run:
        print("\n[DRY RUN] skipping embed + insert")
        return 0

    targets = [BERNARD_DISCORD_ID, ARCHIVE_NAMESPACE]
    if args.only_live:
        targets = [BERNARD_DISCORD_ID]
    elif args.only_archive:
        targets = [ARCHIVE_NAMESPACE]

    total = 0
    started = time.monotonic()
    for namespace in targets:
        items = buckets[namespace]
        if not items:
            continue
        print(f"\n--- embedding namespace {namespace} ({len(items)} chunks) ---")
        total += await _ingest_namespace(pg_url, namespace, items)

    # Final tally per namespace.
    conn = await _connect_retry(pg_url)
    try:
        for namespace in (BERNARD_DISCORD_ID, ARCHIVE_NAMESPACE):
            n = await conn.fetchval(
                "SELECT COUNT(*) FROM deep_memory_chunks WHERE user_id = $1",
                namespace,
            )
            print(f"  {namespace}: {n} chunks total in deep_memory_chunks")
    finally:
        await conn.close()

    print(f"\nDone in {time.monotonic() - started:.1f}s. Inserted {total} new chunks.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
