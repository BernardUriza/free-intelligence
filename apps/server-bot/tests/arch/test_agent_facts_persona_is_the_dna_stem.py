"""The persona the server binds is the key existing self-facts were written under.

Until 2026-09-26 each persona passed its own `agent_id` to the agent_facts tools, as
written in its DNA ("keyed by `agent_id='vultur'`"). Now the server binds
`base_persona_id(...)`, the DNA file's stem. If a stem and the key a DNA declares
ever diverge, that persona's accumulated self-knowledge silently disappears. This
pins them together.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from persona_runner.core import config
from persona_runner.engine.persona_files import resolve_persona_path

ROOT = Path(__file__).resolve().parents[2]
PERSONAS = ROOT / "shared" / "personas"
KEY = re.compile(r"keyed (?:por|by) `agent_id='([^']+)'`")
DNA_WITH_SELF_FACTS = sorted(p for p in PERSONAS.glob("*.md") if KEY.search(p.read_text(encoding="utf-8")))


def test_every_persona_with_self_facts_is_covered():
    assert len(DNA_WITH_SELF_FACTS) >= 6


def test_the_runner_image_serves_these_dna_files():
    """The stem only resolves because the runner image copies this directory to the
    PERSONAS_DIR default; if that COPY moves, every non-default persona binds the
    default persona's key."""
    dockerfile = (ROOT / "infra" / "azure" / "runner.Dockerfile").read_text(encoding="utf-8")
    assert "COPY shared/personas/ /app/personas/" in dockerfile


@pytest.mark.parametrize("dna", DNA_WITH_SELF_FACTS, ids=lambda p: p.stem)
def test_the_declared_key_is_the_stem_the_server_binds(dna, monkeypatch):
    monkeypatch.setattr(config, "PERSONAS_DIR", PERSONAS)  # what the runner image does
    declared = KEY.search(dna.read_text(encoding="utf-8")).group(1)
    assert declared == dna.stem
    assert resolve_persona_path(dna.stem).stem == dna.stem
