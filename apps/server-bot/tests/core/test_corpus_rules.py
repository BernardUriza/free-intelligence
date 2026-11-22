"""rules.yml is the corpus policy the runtime actually reads, not decoration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import yaml

from persona_core.corpus import references, rules


def _write(tmp_path, mutate=None):
    raw = yaml.safe_load(rules.RULES_PATH.read_text(encoding="utf-8"))
    if mutate:
        mutate(raw)
    path = tmp_path / "rules.yml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def test_shipped_rules_load():
    loaded = rules.load_rules()
    assert loaded.references.top_k > 0
    assert loaded.voice.top_k > 0


def test_missing_key_fails_instead_of_defaulting(tmp_path):
    path = _write(tmp_path, lambda raw: raw["references"].pop("min_relevance"))
    with pytest.raises(TypeError):
        rules.load_rules(path)


async def test_editing_the_floor_changes_what_reaches_the_turn(tmp_path, monkeypatch):
    """Mutation receipt: the same passage is dropped, then kept, by a YAML edit alone."""
    hit = {"source_type": "manual", "source_ref": "x:y", "chunk_text": "máxima", "similarity": 0.8}

    async def _block():
        with (
            patch.object(references, "query_corpus", new=AsyncMock(return_value=[hit])),
            patch.object(references, "score_relevance", new=AsyncMock(return_value=[-3.0])),
        ):
            return await references.build_references_block("pregunta bastante larga", namespace="n", header="H")

    assert await _block() is None
    lowered = _write(tmp_path, lambda raw: raw["references"].update(min_relevance=-4.0))
    monkeypatch.setattr(rules, "RULES_PATH", lowered)
    monkeypatch.setattr(references, "load_rules", lambda: rules.load_rules(lowered))
    assert await _block() == "H\n- [y] máxima"
