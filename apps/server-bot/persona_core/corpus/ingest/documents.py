"""A declared file to the document the store must hold: text, chunks and fingerprint."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from fi_core.rag import ChunkConfig, chunk_document

from persona_core.corpus.ingest.extract import extract_text
from persona_core.corpus.ingest.manifest import Manifest, Source, document_id
from persona_core.corpus.rules import IngestRules

TokenCounter = Callable[[str], int]


@dataclass(frozen=True)
class CorpusDocument:
    """`chunks` is empty for a source with nothing to retrieve; the plan refuses it by name."""

    document_id: str
    path: str
    content: str
    chunks: list[str]
    attributes: dict[str, Any] = field(default_factory=dict)


def _pieces(text: str, rules: IngestRules, count_tokens: TokenCounter, context: str = "") -> list[str]:
    """Chunks of `text`, each opened by `context`, none over the window with it included."""
    spent = count_tokens(f"{context}\n\n") if context else 0
    room = max(rules.max_chunk_tokens - spent, 2 * rules.overlap_tokens + 2)
    target = min(rules.chunk_tokens, room)
    config = ChunkConfig(
        chunk_size=target,
        overlap=min(rules.overlap_tokens, target - 1),
        min_chunk_size=rules.min_chunk_tokens,
        max_chunk_size=room,
        count_tokens=count_tokens,
    )
    pieces = chunk_document(text, config=config)
    return [f"{context}\n\n{p}" for p in pieces] if context else pieces


def _sections(doc: str) -> tuple[str, list[tuple[str, str]]]:
    title = next((ln[2:].strip() for ln in doc.splitlines() if ln.startswith("# ")), "")
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in doc.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif not line.startswith("# "):
            sections[-1][1].append(line)
    return title, [(heading, "\n".join(lines).strip()) for heading, lines in sections]


def chunk_text(text: str, rules: IngestRules, count_tokens: TokenCounter, *, markdown: bool = False) -> list[str]:
    """The chunks of one document; none is lost for being short.

    A markdown chunk opens with `<# title> — <## heading>`: the torta ahogada
    recipe body carried no "torta ahogada", and the reranker put another recipe
    first (2026-11-20).
    """
    chunks: list[str] = []
    if markdown:
        title, sections = _sections(text)
        for heading, body in sections:
            context = " — ".join(x for x in (title, heading) if x)
            if body:
                chunks += _pieces(body, rules, count_tokens, context) or _whole(f"{context}\n\n{body}", rules)
    chunks = chunks or _pieces(text, rules, count_tokens)
    return chunks or _whole(text, rules)


def _whole(text: str, rules: IngestRules) -> list[str]:
    stripped = text.strip()
    return [stripped] if len(stripped) >= rules.min_document_chars else []


def build_document(
    manifest: Manifest,
    path: str,
    source: Source,
    sha256: str,
    rules: IngestRules,
    count_tokens: TokenCounter,
    model: str,
) -> CorpusDocument:
    """The document declared by `path`, fingerprinted by everything its vectors depend on."""
    text = extract_text(manifest.folder / path)
    return CorpusDocument(
        document_id=document_id(manifest.persona_id, path),
        path=path,
        content=text,
        chunks=chunk_text(text, rules, count_tokens, markdown=path.lower().endswith(".md")),
        attributes={
            **fingerprint(sha256, rules, model),
            "title": source.title,
            "url": source.url,
            "license": source.license,
        },
    )


def fingerprint(sha256: str, rules: IngestRules, model: str) -> dict[str, Any]:
    """What decides whether a stored document is current: its bytes, the chunking policy and the model."""
    policy = {k: v for k, v in asdict(rules).items() if k != "max_delete_ratio"}
    return {"sha256": sha256, "embed_model": model, "chunking": policy}
