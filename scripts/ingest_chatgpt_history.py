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


def _conv_date(conv: dict) -> str:
    """`YYYY-MM-DD` of the conversation's create_time, or 'fecha-desconocida'.

    The temporal axis is the whole point of ingesting the bodies: it lets the
    bot situate a memory in Bernard's timeline ("en 2024 batallabas con X, para
    2026 ya lo das por sentado") — his ChatGPT history spans 2024-03 → 2026-05.
    The date rides BOTH the chunk header (so the embedding is era-aware) and the
    source_ref (so chunks can be ordered / cited by date)."""
    ct = conv.get("create_time")
    if isinstance(ct, int | float) and ct > 0:
        return time.strftime("%Y-%m-%d", time.gmtime(ct))
    return "fecha-desconocida"


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
    date = _conv_date(conv)
    header = f"[Conversación del {date}: {title}]\n\n" if title else f"[Conversación del {date}]\n\n"
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

_EMBED_BATCH = 16  # chunks per Azure request — ~16x400tok ~= 6.4K, safely < ada-002's 8191/req
_REQUEST_CONCURRENCY = 8  # parallel requests (250K TPM headroom; 8x6.4K ~= 51K in flight)
_EMBED_RETRIES = 4
_MAX_CHARS_PER_CHUNK = 8000  # ~2K tokens — hard cap so a pathological chunk can't 400 the batch
_PG_CONNECT_ATTEMPTS = 6


async def _embed_request(texts: list[str], sem: asyncio.Semaphore) -> list[list[float] | None]:
    """One raw Azure embeddings request under the concurrency gate.

    Returns vectors aligned by `resp.data[i].index`; None only on dim mismatch.
    Raises the SDK error (RateLimitError / BadRequestError / …) so the caller
    can branch."""
    from insult.core.deep_memory import EMBEDDING_DIM, _get_default_embedder

    emb = _get_default_embedder()
    client = emb._get_client()
    async with sem:
        resp = await client.embeddings.create(model=emb.deployment, input=texts)
    out: list[list[float] | None] = [None] * len(texts)
    for item in resp.data:
        v = item.embedding
        out[item.index] = v if len(v) == EMBEDDING_DIM else None
    return out


async def _embed_batch_azure(texts: list[str], sem: asyncio.Semaphore) -> list[list[float] | None]:
    """Embed a batch, tolerant of rate limits (retry) and oversize requests
    (recursive split). Batching ONE request over ~16 chunks is what makes the
    bumped 250K-TPM headroom usable (the single-text path topped out at ~48/min).

    - RateLimitError / transient → retry with backoff.
    - BadRequestError on a multi-item batch → split in half and recurse (isolates
      whichever chunk blew the per-request token cap; the previous 96-wide batch
      tripped this every time).
    - BadRequestError on a single item → give up on that one (None), never fatal.
    Chunks are hard-truncated to `_MAX_CHARS_PER_CHUNK` up front as a guard."""
    safe = [t[:_MAX_CHARS_PER_CHUNK] for t in texts]
    for attempt in range(_EMBED_RETRIES):
        try:
            return await _embed_request(safe, sem)
        except Exception as e:
            name = type(e).__name__
            if "RateLimit" in name or "Timeout" in name or "Connection" in name:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            if "BadRequest" in name and len(safe) > 1:
                mid = len(safe) // 2
                left = await _embed_batch_azure(texts[:mid], sem)
                right = await _embed_batch_azure(texts[mid:], sem)
                return left + right
            print(f"    embed skip ({name}) on {len(safe)} chunk(s)", flush=True)
            return [None] * len(texts)
    print(f"    embed gave up after {_EMBED_RETRIES} retries on {len(safe)} chunk(s)", flush=True)
    return [None] * len(texts)


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

    Resumable: pre-loads what's already stored and skips it. Embeds in batched
    Azure requests (~96 chunks each) run a few in parallel, then flushes a DB
    insert per wave. Reconnect-tolerant throughout."""
    existing = await _load_existing_namespace(pg_url, namespace)
    pending = [(sr, ct) for (sr, ct) in items if (sr, ct) not in existing]
    print(f"  namespace {namespace}: {len(existing)} stored, {len(pending)} new to embed", flush=True)
    if not pending:
        return 0

    sem = asyncio.Semaphore(_REQUEST_CONCURRENCY)
    groups = [pending[i : i + _EMBED_BATCH] for i in range(0, len(pending), _EMBED_BATCH)]
    wave = _REQUEST_CONCURRENCY * 3  # embed groups per DB insert flush
    inserted = 0
    done = 0

    async def _do_group(group: list[tuple[str, str]]) -> list[tuple]:
        vecs = await _embed_batch_azure([ct for (_sr, ct) in group], sem)
        return [(namespace, "manual", sr, ct, v) for (sr, ct), v in zip(group, vecs, strict=False) if v is not None]

    for w in range(0, len(groups), wave):
        batch_groups = groups[w : w + wave]
        results = await asyncio.gather(*(_do_group(g) for g in batch_groups))
        rows = [r for grp in results for r in grp]
        if rows:
            inserted += await _insert_batch(pg_url, rows)
        done += sum(len(g) for g in batch_groups)
        print(f"    {done}/{len(pending)} embedded (+{inserted} inserted total)", flush=True)
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
        # Date in the source_ref so chunks can be ordered/cited by when they
        # happened — the temporal axis that lets the bot read Bernard's arc.
        source_ref = f"chatgpt:{_conv_date(conv)}:{cid}"
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
