"""Tests for the SerenityOps snapshot prompt block.

`_format_serenityops_block` and the `compose_extra_layers` wiring around
it. Pure rendering — no DB, no LLM. Covers:

- Block is omitted entirely when snapshot is None.
- Block renders with realistic curriculum.yaml shape (full Alex sample).
- Stale snapshots flag their age so Insult knows to ask for a re-sync.
- Pipeline rows with `outcome != None` are filtered out (closed apps).
- Empty/missing sections don't blow up the renderer.
"""

from __future__ import annotations

import time

from insult.core.character.prompts import (
    _format_serenityops_block,
    compose_extra_layers,
)


def _alex_curriculum() -> dict:
    """A trimmed but realistic curriculum.yaml shape, mirroring the
    Alex fixture from /tmp/serenityops-lite-build/curriculum/curriculum.yaml."""
    return {
        "personal": {
            "full_name": "Alex Nava",
            "title": "Psicóloga · Coordinadora de procesos",
            "tagline": "15+ años coordinando procesos entre instituciones, familias e infancias neurodivergentes.",
            "location": "Ciudad de México",
            "work_modality_required": "remote",
        },
        "summary": (
            "Profesional con más de 15 años coordinando procesos entre múltiples actores: "
            "instituciones educativas, familias, infancias neurodivergentes. Formación en psicología (ITESO)."
        ),
        "experience": [
            {"company": "Freelance", "role": "Pet Sitter", "start_date": "2015-01", "end_date": None, "current": True},
            {"company": "Local 1", "role": "Gerente y meserx", "start_date": "2021-01", "end_date": "2023-12"},
            {"company": "V Ramen", "role": "Meserx", "start_date": "2024-03", "end_date": "2024-08"},
            {"company": "ASF Guadalajara", "role": "Shadow Teacher", "start_date": "2015-08", "end_date": "2017-09"},
            {"company": "Täleny", "role": "Shadow Teacher", "start_date": "2017-11", "end_date": "2018-06"},
            {"company": "ICF", "role": "Shadow Teacher", "start_date": "2012-08", "end_date": "2014-01"},
        ],
        "skills": {
            "coordinacion_y_procesos": ["..."],
            "psicologia_y_acompanamiento": ["..."],
            "investigacion_cualitativa": ["..."],
        },
        "targets": {
            "desired_roles": [
                "Coordinación de casos en OSCs de discapacidad",
                "Acompañamiento a familias con hijes neurodivergentes",
                "Investigación cualitativa freelance",
            ],
        },
    }


def _live_pipeline() -> dict:
    return {
        "pipeline": [
            {
                "id": "osc-001",
                "company": "Fundación Ejemplo",
                "role": "Coordinadora de Casos",
                "stage": "applied",
                "outcome": None,
            },
            {
                "id": "osc-002",
                "company": "UNICEF MX",
                "role": "Consultora",
                "stage": "screen",
                "outcome": None,
            },
            {
                "id": "osc-003",
                "company": "Empresa Cerrada SA",
                "role": "X",
                "stage": "rejected",
                "outcome": "rejected",
            },
        ],
    }


def _fresh_snapshot() -> dict:
    return {
        "id": 1,
        "snapshot_at": time.time(),
        "curriculum": _alex_curriculum(),
        "opportunities": _live_pipeline(),
        "client_version": "lite-1.0.0",
        "source": "serenityops-lite",
    }


class TestFormatBlock:
    def test_renders_user_name_in_header(self):
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        assert "Professional Data — Alex" in block

    def test_includes_role_headline(self):
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        assert "Psicóloga · Coordinadora de procesos" in block

    def test_includes_modality(self):
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        assert "Modalidad: remote" in block

    def test_includes_top_experiences_capped_at_5(self):
        """Six experiences in the fixture, only the first five render."""
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        # First 5 by fixture order.
        assert "Freelance" in block
        assert "Local 1" in block
        assert "V Ramen" in block
        assert "ASF Guadalajara" in block
        assert "Täleny" in block
        # 6th must NOT appear.
        assert "ICF" not in block

    def test_current_flag_becomes_actual(self):
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        # Freelance has current=True, no end_date → "actual"
        assert "Freelance" in block
        assert "actual" in block

    def test_pipeline_filters_closed_outcomes(self):
        """Only outcome=None rows render; rejected/ghosted/hired are dropped
        because they don't help Insult know what's in flight."""
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        assert "Fundación Ejemplo" in block
        assert "UNICEF MX" in block
        assert "Empresa Cerrada" not in block

    def test_pipeline_count_reflects_only_live(self):
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        assert "Pipeline activo (2 vacante(s))" in block

    def test_stale_snapshot_flags_age(self):
        """A 45-day-old snapshot should warn Insult to ask for a re-sync."""
        snap = _fresh_snapshot()
        snap["snapshot_at"] = time.time() - 45 * 86400
        block = _format_serenityops_block(snap, "Alex")
        assert "pídeles re-sync" in block

    def test_fresh_snapshot_does_not_flag_age(self):
        block = _format_serenityops_block(_fresh_snapshot(), "Alex")
        assert "pídeles re-sync" not in block

    def test_handles_empty_curriculum(self):
        """No payload data → block still renders header but no sections crash."""
        snap = {"snapshot_at": time.time(), "curriculum": None, "opportunities": None}
        block = _format_serenityops_block(snap, "Alex")
        assert "Professional Data — Alex" in block

    def test_falls_back_when_user_name_is_empty(self):
        snap = _fresh_snapshot()
        # compose_extra_layers passes "" when user_name unavailable.
        block = _format_serenityops_block(snap, "")
        # The header still renders with whatever the caller gave.
        assert "Professional Data" in block


class TestComposeExtraLayersWiring:
    def test_omits_block_when_snapshot_none(self):
        out = compose_extra_layers("BASE", serenityops_snapshot=None)
        assert "Professional Data" not in out
        assert out == "BASE"

    def test_appends_block_when_snapshot_present(self):
        out = compose_extra_layers(
            "BASE",
            serenityops_snapshot=_fresh_snapshot(),
            serenityops_user_name="Alex",
        )
        assert "BASE" in out
        assert "Professional Data — Alex" in out

    def test_block_placed_after_facts_prompt(self):
        """Order matters for the cache boundary: facts block comes first
        (user-specific facts), then the SerenityOps block (also user-specific
        but heavier and more recent). Tests pin the order so a refactor
        doesn't accidentally swap them."""
        out = compose_extra_layers(
            "BASE",
            facts_prompt="## Facts about user\n- foo",
            serenityops_snapshot=_fresh_snapshot(),
            serenityops_user_name="Alex",
        )
        facts_idx = out.index("Facts about user")
        sync_idx = out.index("Professional Data")
        assert facts_idx < sync_idx
