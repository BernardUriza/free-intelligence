"""Ingest a persona's corpus sources into deep_memory_chunks as a SHARED corpus.

Generalization of the (deleted) `scripts/ingest_film_corpus.py`: instead of a
hardcoded film-book list under one namespace, this ingests EVERY source file
found under `data/corpus/<persona_id>/` into the namespace declared by that
persona's registry entry (`Persona.corpus_namespace`). The corpus is retrieved
on ANY user's turn when the topic matches, via `deep_memory.query_corpus`.

Pipeline per source (verbatim from the original film script):
  .pdf → pypdf; .xml → JATS/PMC flatten (ElementTree); .txt/.md → direct UTF-8
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
    POSTGRES_URL=$(az containerapp secret show -n persona-gateway -g insult-rg \\
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
from collections.abc import Callable
from pathlib import Path

import asyncpg

# Run from the repo root regardless of where the script is invoked from.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

_CORPUS_ROOT = _REPO_ROOT / "data" / "corpus"
_TEXT_SUFFIXES = {".txt", ".md"}
# .xml = JATS full-text from PMC / Europe PMC (open-access articles). Tags are
# stripped to plain text via the stdlib ElementTree — no extra dependency.
_SUPPORTED_SUFFIXES = {".pdf", ".xml", *_TEXT_SUFFIXES}
# Floor for salvaging a whole document the chunker rejected for being under its
# 50-token min_chunk_size. Above this it is a real (if short) source worth one
# chunk; below it there is nothing to retrieve — a stub, a caption, a title.
_MIN_SALVAGE_CHARS = 120


def slugify_stem(filename: str) -> str:
    """Filename → source_ref slug: stem, lowercased, spaces/underscores → hyphens."""
    stem = Path(filename).stem
    return _slug(stem)


def slugify_dirname(dirname: str) -> str:
    """Directory name → slug, keeping everything AFTER a dot.

    A directory is not a file: `Path("v1.2").stem` is "v1", so sibling folders
    `v1.2/` and `v1.3/` both collapsed to "v1" and their source_refs collided —
    the dedupe index `(user_id, source_ref, md5(chunk_text))` would then treat
    two different corpora as one and every citation would point at the wrong
    folder. Directories keep their full name.
    """
    return _slug(dirname)


def _slug(text: str) -> str:
    return text.lower().replace(" ", "-").replace("_", "-").replace(".", "-")


def discover_sources(persona_id: str) -> list[tuple[str, Path]]:
    """All ingestable files under data/corpus/<persona_id>/ as (source_ref, path).

    RECURSIVE: a corpus of hundreds of small files (a scraped blog, a paper set)
    belongs in its own subfolder, not dumped flat next to the books. A file in
    `contraelamor/` gets source_ref `<persona_id>:contraelamor-<slug>`, so the
    subfolder both namespaces the slug against collisions and stays visible in
    the citation the RAG surfaces.

    Skips MANIFEST.md, hidden files/dirs, and unsupported extensions (warned).
    """
    src_dir = _CORPUS_ROOT / persona_id
    sources: list[tuple[str, Path]] = []
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src_dir)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if path.name == "MANIFEST.md":
            continue
        if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
            print(f"  WARN: skipping unsupported file type: {rel}")
            continue
        prefix = "-".join(slugify_dirname(part) for part in rel.parts[:-1])
        slug = slugify_stem(path.name)
        ref = f"{prefix}-{slug}" if prefix else slug
        sources.append((f"{persona_id}:{ref}", path))
    return sources


def prepare_chunks(
    doc: str,
    *,
    chunker: Callable[..., list[str]],
    chunk_size: int,
    overlap: int,
) -> tuple[list[str], str]:
    """Document text → (chunks, status) with NO silent losses.

    status ∈ {"chunked", "salvaged", "dropped", "no_text"}.

    A whole document shorter than the chunker's `min_chunk_size` (50 tokens)
    comes back as ZERO chunks. That used to vanish without a word — the source
    counted as "processed", nothing was inserted, no warning fired — which
    silently dropped the 14 shortest posts of the contraelamor corpus
    (2026-07-27, found only by diffing Postgres against the files on disk).

    The floor exists to reject a FRAGMENT of a large document, not to discard a
    short document WHOLE, so a short-but-real source is salvaged as one chunk.
    Below `_MIN_SALVAGE_CHARS` there is genuinely nothing to retrieve (a stub, a
    caption) and it is dropped — but reported as dropped, never swallowed.
    """
    if not doc or not doc.strip():
        return [], "no_text"
    chunks = chunker(doc, chunk_size=chunk_size, overlap=overlap)
    if chunks:
        return chunks, "chunked"
    stripped = doc.strip()
    if len(stripped) >= _MIN_SALVAGE_CHARS:
        return [stripped], "salvaged"
    return [], "dropped"


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


def extract_xml_text(path: Path) -> str:
    """Flatten a JATS/PMC XML article to plain text.

    Walks the tree, concatenating every element's text/tail with whitespace, so
    the prose survives while the markup is dropped. Stdlib ElementTree only — no
    lxml dependency. A parse failure returns "" (the source is skipped upstream,
    never aborting the whole persona's ingest).
    """
    import re
    import xml.etree.ElementTree as ET

    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError as e:
        print(f"  WARN: XML parse failed for {path.name}: {e}")
        return ""
    text = " ".join(t.strip() for t in root.itertext() if t and t.strip())
    return re.sub(r"\s+\n", "\n", re.sub(r"[ \t]{2,}", " ", text)).strip()


def extract_source_text(path: Path) -> str:
    """Dispatch extraction by suffix: pypdf for .pdf, ElementTree for .xml,
    direct UTF-8 for .txt/.md."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".xml":
        return extract_xml_text(path)
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
    from persona_core.deep_memory import embed_text

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
        print(f"FATAL: no ingestable sources (.pdf/.xml/.txt/.md) under {src_dir}", file=sys.stderr)
        return 2

    print(f"persona={args.persona} namespace={namespace or '<unset>'} sources={len(sources)}")

    # Extract + chunk every source first (cheap, local, no network).
    from persona_core.deep_memory import chunk_text_for_embedding

    prepared: list[tuple[str, list[str]]] = []
    empty: list[str] = []
    salvaged: list[str] = []
    for source_ref, path in sources:
        print(f"\n=== {source_ref} ({path.name}) ===")
        doc = extract_source_text(path)
        print(f"  extracted {len(doc):,} chars (~{len(doc.split()):,} words)")
        chunks, status = prepare_chunks(doc, chunker=chunk_text_for_embedding, chunk_size=args.chunk_size, overlap=args.overlap)
        if status == "no_text":
            print("  no extractable text, skipping")
            empty.append(source_ref)
            continue
        if status == "dropped":
            empty.append(source_ref)
            print(f"  produced 0 chunks and is under {_MIN_SALVAGE_CHARS} chars — DROPPED")
            continue
        if status == "salvaged":
            salvaged.append(source_ref)
            print("  chunker returned 0 (doc under its 50-token floor) → salvaged as 1 whole-document chunk")
        else:
            print(f"  produced {len(chunks)} chunks via fi_core.rag")
        prepared.append((source_ref, chunks))

    # Never let a silent cap read as full coverage.
    if salvaged:
        print(f"\nSALVAGED as whole-document chunks ({len(salvaged)}): {', '.join(salvaged)}")
    if empty:
        print(f"\nDROPPED, nothing ingested ({len(empty)}): {', '.join(empty)}")

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
