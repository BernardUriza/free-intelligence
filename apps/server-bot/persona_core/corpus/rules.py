"""Loader for `rules.yml`, the corpus policy. A missing key fails at load, never defaults."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# Wire cap of a turn's references block; `max_block_chars` plus a header sits well under it.
MAX_REFERENCES_CHARS = 8000

RULES_PATH = Path(__file__).with_name("rules.yml")


@dataclass(frozen=True)
class ReferenceRules:
    candidates: int
    fusion_pool: int
    top_k: int
    min_relevance: float
    min_query_chars: int
    max_block_chars: int
    truncate_backoff_chars: int


@dataclass(frozen=True)
class IngestRules:
    chunk_tokens: int
    overlap_tokens: int
    min_chunk_tokens: int
    max_chunk_tokens: int
    min_document_chars: int
    max_delete_ratio: float
    pipeline: int


@dataclass(frozen=True)
class VoiceRules:
    draw: int
    drop_most_similar: int
    top_k: int
    min_query_chars: int


@dataclass(frozen=True)
class CorpusRules:
    references: ReferenceRules
    ingest: IngestRules
    voice: VoiceRules


_cache: dict[Path, tuple[float, CorpusRules]] = {}


def load_rules(path: Path = RULES_PATH) -> CorpusRules:
    """The rules as the file says them now; reread only when its mtime changes."""
    mtime = path.stat().st_mtime
    cached = _cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = CorpusRules(
        references=ReferenceRules(**raw["references"]),
        ingest=IngestRules(**raw["ingest"]),
        voice=VoiceRules(**raw["voice"]),
    )
    _cache[path] = (mtime, rules)
    return rules
