"""Behavior engine seams — the failures that only happen when components interact.

1. Cross-persona guidance isolation (cruel-critic 2026-07-14, GRAVE #1): the
   prompt cache used to be keyed by NAME only, and container images give every
   file the SAME mtime (az acr build tars a fresh checkout) — so two personas
   with the same-named guidance file could be served each other's voice. The
   resistance test forces equal mtimes and demands each persona its own prose.

2. Fact-shape contract (IMPORTANTE #3): the engine reads ``fact["fact"]`` from
   the dicts ``khimeras_shared.memory`` emits. That contract was convention-only;
   if the memory layer renames the key, Alex's vulnerability guardian silently
   scores 0. This test welds the two layers together.
"""

from __future__ import annotations

import os

from khimeras_shared.behavior import content
from khimeras_shared.behavior.content import clear_guidance_cache, load_guidance
from khimeras_shared.behavior.vulnerability import (
    VULNERABLE_THRESHOLD,
    compute_vulnerability_score,
)
from khimeras_shared.memory.repositories.facts import _fact_to_dict


def test_same_named_guidance_with_equal_mtimes_stays_per_persona(tmp_path, monkeypatch):
    for persona, prose in (("insult", "filo y navaja"), ("vultur", "carroña y cine")):
        d = tmp_path / persona / "presets"
        d.mkdir(parents=True)
        (d / "preset_guidance_default_abrasive.md").write_text(prose, encoding="utf-8")
    stamp = 1_700_000_000
    for persona in ("insult", "vultur"):
        os.utime(
            tmp_path / persona / "presets" / "preset_guidance_default_abrasive.md",
            ns=(stamp, stamp),
        )
    monkeypatch.setattr(content, "_GUIDANCE_ROOT", tmp_path)
    clear_guidance_cache()

    assert load_guidance("insult", "presets", "preset_guidance_default_abrasive") == "filo y navaja"
    assert load_guidance("vultur", "presets", "preset_guidance_default_abrasive") == "carroña y cine"
    # And again from cache — still isolated.
    assert load_guidance("insult", "presets", "preset_guidance_default_abrasive") == "filo y navaja"


def test_persona_without_content_gets_empty_string_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(content, "_GUIDANCE_ROOT", tmp_path)
    clear_guidance_cache()
    assert load_guidance("frugivoro", "presets", "preset_guidance_default_abrasive") == ""


class _Fact:
    def __init__(self, fact_id: int, fact: str):
        self.id = fact_id
        self.fact = fact
        self.category = "salud"
        self.updated_at = "2026-07-14"


def test_memory_fact_dict_shape_feeds_the_vulnerability_guardian():
    """The EXACT dicts the memory layer emits must cross the threshold when
    they carry a clinical cluster — welding the implicit contract."""
    rows = [
        _fact_to_dict(_Fact(fact_id=1, fact="diagnosticada con CPTSD por su psiquiatra")),
        _fact_to_dict(_Fact(fact_id=2, fact="toma quetiapina cada noche")),
    ]
    assert set(rows[0]) == {"id", "fact", "category", "updated_at"}
    assert compute_vulnerability_score(rows) >= VULNERABLE_THRESHOLD
