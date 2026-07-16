"""Ingest a persona's corpus sources into deep_memory_chunks as a SHARED corpus.

Generalization of the (deleted) `scripts/ingest_film_corpus.py`: instead of a
hardcoded film-book list under one namespace, this ingests EVERY source file
found under `data/corpus/<persona_id>/` into the namespace declared by that
persona's registry entry (`Persona.corpus_namespace`). The corpus is retrieved
on ANY user's turn when the topic matches, via `deep_memory.query_corpus`.

Pipeline per source (verbatim from the original film script):
  .pdf → pypdf text extraction (page by page); .txt / .md → direct UTF-8 read
  → fi_core.rag PARAGRAPH_AWARE chunking (same chunker as AURITY / deep_memory)
  → Azure OpenAI ada-002 embeddings
  → INSERT into deep_memory_chunks with source_type="manual".
Idempotent via the schema's unique index on (user_id, source_ref, md5(chunk_text)).

Source files: everything in `data/corpus/<persona_id>/` except MANIFEST.md and
hidden files. Each gets source_ref "<persona_id>:<slug>" where slug is the
filename stem lowercased with spaces/underscores → hyphens.

CLI:
    conda activate discord-bot
    python scripts/ingest_corpus.py --persona <persona_id> --dry-run  # extract + chunk only
    python scripts/ingest_corpus.py --persona <persona_id>            # real ingest

Env required (same as the original film script):
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
    python scripts/ingest_corpus.py --persona <persona_id>
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

_CORPUS_ROOT = _REPO_ROOT / "data" / "corpus"
_TEXT_SUFFIXES = {".txt", ".md"}
_SUPPORTED_SUFFIXES = {".pdf", *_TEXT_SUFFIXES}


def slugify_stem(filename: str) -> str:
    """Filename → source_ref slug: stem, lowercased, spaces/underscores → hyphens."""
    stem = Path(filename).stem
    return stem.lower().replace(" ", "-").replace("_", "-")


def discover_sources(persona_id: str) -> list[tuple[str, Path]]:
    """All ingestable files under data/corpus/<persona_id>/ as (source_ref, path).

    Skips MANIFEST.md, hidden files, and unsupported extensions (warned).
    """
    src_dir = _CORPUS_ROOT / persona_id
    sources: list[tuple[str, Path]] = []
    for path in sorted(src_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.name == "MANIFEST.md":
            continue
        if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            print(f"  WARN: skipping unsupported file type: {path.name}")
            continue
        sources.append((f"{persona_id}:{slugify_stem(path.name)}", path))
    return sources


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


def extract_source_text(path: Path) -> str:
    """Dispatch extraction by suffix: pypdf for .pdf, direct UTF-8 for .txt/.md."""
    if path.suffix.lower() == ".pdf":
        return extract_pdf_text(path)
    return path.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    p.add_argument(
        "--persona",
        required=True,
        help="persona_id from shared.personas.registry whose corpus to ingest.",
    )
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
    from khimeras_shared.deep_memory import embed_text

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
            print(
                f"    pg connect retry {attempt + 1}/{_PG_CONNECT_ATTEMPTS}: {type(e).__name__}",
                flush=True,
            )
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
        rows = [
            (namespace, "manual", source_ref, c, v)
            for c, v in zip(slice_, vecs, strict=False)
            if v is not None
        ]
        got = await _insert_batch(pg_url, rows) if rows else 0
        inserted += got
        failed = len(slice_) - len(rows)
        print(
            f"    {min(start + batch, len(pending))}/{len(pending)} embedded "
            f"(+{got} inserted{f', {failed} embed-failed' if failed else ''})",
            flush=True,
        )
    return inserted


def _resolve_namespace(persona_id: str, *, dry_run: bool) -> str | None:
    """Resolve the corpus namespace from the persona registry.

    `Persona.corpus_namespace` is a NEW registry field being added in parallel;
    until it lands, getattr keeps this script importable and a dry-run usable
    (chunking needs no namespace). A real run without it is a hard fatal.
    """
    from shared.personas.registry import get_persona

    persona = get_persona(persona_id)
    if persona is None:
        print(f"FATAL: persona '{persona_id}' is not in shared.personas.registry", file=sys.stderr)
        raise SystemExit(2)
    namespace = getattr(persona, "corpus_namespace", None)
    if namespace is None:
        msg = (
            f"persona '{persona_id}' has no corpus_namespace in the registry "
            "(field not set or not yet added to shared.personas.registry.Persona)"
        )
        if dry_run:
            print(f"  WARN: {msg} — dry-run continues; a real ingest would abort here.")
            return None
        print(f"FATAL: {msg}", file=sys.stderr)
        raise SystemExit(2)
    return namespace


async def main() -> int:
    args = parse_args()

    pg_url = os.environ.get("POSTGRES_URL")
    if not args.dry_run and not pg_url:
        print("FATAL: POSTGRES_URL not set", file=sys.stderr)
        return 2
    if not args.dry_run and (not os.environ.get("AZURE_OPENAI_ENDPOINT") or not os.environ.get("AZURE_OPENAI_KEY")):
        print("FATAL: AZURE_OPENAI_ENDPOINT / KEY not set", file=sys.stderr)
        return 2

    namespace = _resolve_namespace(args.persona, dry_run=args.dry_run)

    src_dir = _CORPUS_ROOT / args.persona
    if not src_dir.is_dir():
        print(f"FATAL: no sources dir for persona '{args.persona}' — expected {src_dir}", file=sys.stderr)
        return 2

    sources = discover_sources(args.persona)
    if not sources:
        print(f"FATAL: no ingestable sources (.pdf/.txt/.md) under {src_dir}", file=sys.stderr)
        return 2

    print(f"persona={args.persona} namespace={namespace or '<unset>'} sources={len(sources)}")

    # Extract + chunk every source first (cheap, local, no network).
    from khimeras_shared.deep_memory import chunk_text_for_embedding

    prepared: list[tuple[str, list[str]]] = []
    for source_ref, path in sources:
        print(f"\n=== {source_ref} ({path.name}) ===")
        doc = extract_source_text(path)
        print(f"  extracted {len(doc):,} chars (~{len(doc.split()):,} words)")
        if not doc.strip():
            print("  no extractable text, skipping")
            continue
        chunks = chunk_text_for_embedding(doc, chunk_size=args.chunk_size, overlap=args.overlap)
        print(f"  produced {len(chunks)} chunks via fi_core.rag")
        prepared.append((source_ref, chunks))

    if args.dry_run:
        total = sum(len(chunks) for _, chunks in prepared)
        print(f"\n[DRY RUN] skipping embed + insert ({total} chunks across {len(prepared)} sources)")
        return 0

    total_inserted = 0
    started = time.monotonic()

    for source_ref, chunks in prepared:
        print(f"\n--- embedding {source_ref} ---")
        total_inserted += await _ingest_source(pg_url, namespace=namespace, source_ref=source_ref, chunks=chunks)

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
            namespace,
        )
        print(f"\n=== corpus '{namespace}' in deep_memory_chunks ===")
        for r in rows:
            print(f"  {r['source_ref']}: {r['n']} chunks")
    finally:
        await conn.close()

    elapsed = time.monotonic() - started
    print(f"\nDone in {elapsed:.1f}s. Inserted {total_inserted} new chunks total.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
