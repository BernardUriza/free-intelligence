"""Ingest the film-theory PDFs into deep_memory_chunks as a SHARED corpus.

Unlike `backfill_deep_memory.py` (which keys chunks by a real user_id so the
bot recalls a person's own history), this script ingests TOPIC knowledge under
the synthetic namespace `deep_memory.FILM_CORPUS_NAMESPACE` ("__corpus_film__").
That corpus is retrieved on ANY user's turn when the topic is film, via
`deep_memory.query_corpus` / `build_film_references_block`, and injected under
the Vultur (film-criticism) frame from `shared/corpus/film_criticism.md`.

Pipeline per PDF: pypdf text extraction (page by page) → fi_core.rag
PARAGRAPH_AWARE chunking (same chunker as AURITY / deep_memory) → Azure OpenAI
ada-002 embeddings → INSERT into deep_memory_chunks with source_type="manual".
Idempotent via the schema's unique index on (user_id, source_ref, md5(chunk_text)).

The two source books (place under data/film_corpus_sources/, gitignored):
  - "Leo Braudy, Marshall Cohen-Film Theory and Criticism-Oxford University
     Press, USA (2009).pdf"   → source_ref "film:braudy-cohen-2009"
  - "The-Language-and-Style-of-Film-Criticism-.pdf"
     → source_ref "film:language-style-criticism"

CLI:
    conda activate discord-bot
    python scripts/ingest_film_corpus.py --dry-run     # extract + chunk, no embed/insert
    python scripts/ingest_film_corpus.py               # real ingest

Env required (same as backfill_deep_memory.py):
    POSTGRES_URL                       — PG connection string
    AZURE_OPENAI_ENDPOINT              — Azure cognitive endpoint
    AZURE_OPENAI_KEY                   — key for the account
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT  — defaults to text-embedding-ada-002

Run helper from this Mac (env injected from Azure secrets):
    POSTGRES_URL=$(az containerapp secret show -n discord-bot -g insult-rg \\
        --secret-name postgres-url --query value -o tsv) \\
    AZURE_OPENAI_ENDPOINT=https://northcentralus.api.cognitive.microsoft.com/ \\
    AZURE_OPENAI_KEY=$(az cognitiveservices account keys list \\
        -n insult-openai -g insult-rg --query key1 -o tsv) \\
    python scripts/ingest_film_corpus.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

import asyncpg

# Run from the repo root regardless of where the script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

# (source_ref, filename) — filenames live under data/film_corpus_sources/.
_SOURCES: list[tuple[str, str]] = [
    (
        "film:braudy-cohen-2009",
        "Leo Braudy, Marshall Cohen-Film Theory and Criticism-Oxford University Press, USA (2009).pdf",
    ),
    (
        "film:language-style-criticism",
        "The-Language-and-Style-of-Film-Criticism-.pdf",
    ),
]
_CORPUS_DIR = _REPO_ROOT / "data" / "film_corpus_sources"


def extract_pdf_text(path: Path) -> str:
    """Extract all text from a PDF, page by page, joined with blank lines.

    Uses pypdf (already in the env; fitz/pdfplumber are not). Pages that fail
    to extract are skipped with a warning rather than aborting the whole book —
    a few unreadable pages in a 400-page volume shouldn't lose the other 396.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    failed = 0
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            failed += 1
            continue
        txt = txt.strip()
        if txt:
            parts.append(txt)
    if failed:
        print(f"  WARN: {failed} page(s) failed to extract in {path.name}")
    return "\n\n".join(parts)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract + chunk and print stats without embedding / inserting.",
    )
    p.add_argument(
        "--chunk-size",
        type=int,
        default=400,
        help="fi_core chunk size in tokens (default 400, same as deep_memory).",
    )
    p.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="fi_core chunk overlap in tokens (default 50).",
    )
    return p.parse_args()


_EMBED_CONCURRENCY = 6  # Azure embeddings quota is 10/350 — 6 in flight is safe
_EMBED_RETRIES = 3  # per-chunk retries on transient APIConnectionError blips


async def _embed_with_retry(chunk: str, sem: asyncio.Semaphore) -> list[float] | None:
    """Embed one chunk under a concurrency gate, retrying transient failures.

    Uses deep_memory.embed_text (which already swallows + logs and returns None
    on failure). A single network blip in a ~2400-chunk run must NOT kill the
    job, so we retry a few times with a short backoff before giving up on this
    chunk. Returns the vector or None (the chunk is then skipped, not fatal)."""
    from personas.insult.core.deep_memory import embed_text

    async with sem:
        for attempt in range(_EMBED_RETRIES):
            vec = await embed_text(chunk)
            if vec is not None:
                return vec
            await asyncio.sleep(1.5 * (attempt + 1))
    return None


_PG_CONNECT_ATTEMPTS = 6  # residential→Azure Postgres SSL is flaky; reconnect hard


async def _connect_retry(pg_url: str) -> asyncpg.Connection:
    """Open a pgvector-enabled Postgres connection, retrying flaky timeouts.

    The residential link to Azure Postgres drops connections mid-run, so every
    DB touch goes through a fresh/retried connection rather than one long-lived
    handle. Raises after _PG_CONNECT_ATTEMPTS exhausted."""
    from pgvector.asyncpg import register_vector

    last: Exception | None = None
    for attempt in range(_PG_CONNECT_ATTEMPTS):
        try:
            conn = await asyncpg.connect(pg_url, timeout=20)
            await register_vector(conn)
            return conn
        except Exception as e:  # TimeoutError, ConnectionError, SSL — all transient here
            last = e
            print(f"    pg connect retry {attempt + 1}/{_PG_CONNECT_ATTEMPTS}: {type(e).__name__}", flush=True)
            await asyncio.sleep(3 * (attempt + 1))
    raise RuntimeError(f"could not connect to Postgres after {_PG_CONNECT_ATTEMPTS} attempts: {last}")


async def _load_existing(pg_url: str, namespace: str, source_ref: str) -> set[str]:
    conn = await _connect_retry(pg_url)
    try:
        rows = await conn.fetch(
            "SELECT chunk_text FROM deep_memory_chunks WHERE user_id = $1 AND source_ref = $2",
            namespace,
            source_ref,
        )
        return {r["chunk_text"] for r in rows}
    finally:
        await conn.close()


async def _insert_batch(pg_url: str, rows: list[tuple]) -> int:
    """Insert one batch, reconnecting+retrying if the link drops mid-write."""
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


async def _ingest_source(pg_url: str, *, namespace: str, source_ref: str, chunks: list[str]) -> int:
    """Resumable, parallel, reconnect-tolerant embed+insert for one source.

    Resumability: pre-loads the chunk_text already stored for (namespace,
    source_ref) and skips them — re-running after a crash does NOT re-embed
    what's already in. Each DB touch uses its own retried connection so a
    flaky residential link can't kill the whole run. Returns newly inserted.
    """
    existing = await _load_existing(pg_url, namespace, source_ref)
    pending = [c.strip() for c in chunks if c and c.strip() and c.strip() not in existing]
    print(f"  {len(existing)} already stored, {len(pending)} new to embed")
    if not pending:
        return 0

    sem = asyncio.Semaphore(_EMBED_CONCURRENCY)
    inserted = 0
    batch = 120
    for start in range(0, len(pending), batch):
        slice_ = pending[start : start + batch]
        vecs = await asyncio.gather(*(_embed_with_retry(c, sem) for c in slice_))
        rows = [(namespace, "manual", source_ref, c, v) for c, v in zip(slice_, vecs, strict=False) if v is not None]
        got = await _insert_batch(pg_url, rows) if rows else 0
        inserted += got
        failed = len(slice_) - len(rows)
        print(
            f"    {min(start + batch, len(pending))}/{len(pending)} embedded "
            f"(+{got} inserted{f', {failed} embed-failed' if failed else ''})",
            flush=True,
        )
    return inserted


async def main() -> int:
    args = parse_args()

    pg_url = os.environ.get("POSTGRES_URL")
    if not args.dry_run and not pg_url:
        print("FATAL: POSTGRES_URL not set", file=sys.stderr)
        return 2
    if not args.dry_run and (not os.environ.get("AZURE_OPENAI_ENDPOINT") or not os.environ.get("AZURE_OPENAI_KEY")):
        print("FATAL: AZURE_OPENAI_ENDPOINT / KEY not set", file=sys.stderr)
        return 2

    # Import here so module-load errors surface as fatals with a clear stack.
    from personas.insult.core.deep_memory import FILM_CORPUS_NAMESPACE, chunk_text_for_embedding

    missing = [fn for _, fn in _SOURCES if not (_CORPUS_DIR / fn).exists()]
    if missing:
        print(f"FATAL: missing source PDF(s) under {_CORPUS_DIR}:", file=sys.stderr)
        for fn in missing:
            print(f"  - {fn}", file=sys.stderr)
        return 2

    # Extract + chunk every source first (cheap, local, no network).
    prepared: list[tuple[str, list[str]]] = []
    for source_ref, filename in _SOURCES:
        path = _CORPUS_DIR / filename
        print(f"\n=== {source_ref} ({filename}) ===")
        doc = extract_pdf_text(path)
        print(f"  extracted {len(doc):,} chars (~{len(doc.split()):,} words)")
        if not doc.strip():
            print("  no extractable text, skipping")
            continue
        chunks = chunk_text_for_embedding(doc, chunk_size=args.chunk_size, overlap=args.overlap)
        print(f"  produced {len(chunks)} chunks via fi_core.rag")
        prepared.append((source_ref, chunks))

    if args.dry_run:
        print("\n[DRY RUN] skipping embed + insert")
        return 0

    total_inserted = 0
    started = time.monotonic()

    for source_ref, chunks in prepared:
        print(f"\n--- embedding {source_ref} ---")
        total_inserted += await _ingest_source(
            pg_url, namespace=FILM_CORPUS_NAMESPACE, source_ref=source_ref, chunks=chunks
        )

    conn = await _connect_retry(pg_url)
    try:
        rows = await conn.fetch(
            """
            SELECT source_ref, COUNT(*) AS n
            FROM deep_memory_chunks
            WHERE user_id = $1
            GROUP BY source_ref
            ORDER BY source_ref
            """,
            FILM_CORPUS_NAMESPACE,
        )
        print("\n=== film corpus in deep_memory_chunks ===")
        for r in rows:
            print(f"  {r['source_ref']}: {r['n']} chunks")
    finally:
        await conn.close()

    elapsed = time.monotonic() - started
    print(f"\nDone in {elapsed:.1f}s. Inserted {total_inserted} new chunks total.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
