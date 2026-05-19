"""Tests for `fi_core.memory.types`.

Pure dataclass behavior — construction, immutability, FactSource enum
round-trip, ConsolidationReport rollup counts.
"""

from __future__ import annotations

import pytest

from fi_core.memory import (
    ConsolidationOp,
    Fact,
    FactSource,
)
from fi_core.memory.types import ConsolidationReport


class TestFact:
    def test_minimum_construction(self):
        f = Fact(fact="lives in Madrid", principal_id="u1")
        assert f.fact == "lives in Madrid"
        assert f.principal_id == "u1"
        assert f.category == "general"
        assert f.source == FactSource.AUTO
        assert f.id is None
        assert f.deleted_at is None

    def test_frozen_immutability(self):
        f = Fact(fact="x", principal_id="u1")
        with pytest.raises((AttributeError, TypeError)):
            f.fact = "y"  # type: ignore[misc]

    def test_full_construction(self):
        f = Fact(
            id=42,
            fact="works at Anthropic",
            principal_id="u1",
            category="employment",
            source=FactSource.MANUAL,
            updated_at=1234567890.5,
            deleted_at=None,
        )
        assert f.id == 42
        assert f.source == FactSource.MANUAL


class TestFactSource:
    def test_three_tiers(self):
        assert FactSource.AUTO.value == "auto"
        assert FactSource.MANUAL.value == "manual"
        assert FactSource.AGENT.value == "agent"

    def test_roundtrip_from_string(self):
        for tier in ("auto", "manual", "agent"):
            assert FactSource(tier).value == tier


class TestConsolidationOp:
    def test_noop_construction(self):
        op = ConsolidationOp(
            op="NOOP",
            fact_id_before=1,
            fact_id_after=1,
            fact_text_before="x",
            fact_text_after="x",
            reason="kept",
            run_ts=1000.0,
        )
        assert op.op == "NOOP"
        assert op.fact_id_before == op.fact_id_after

    def test_delete_has_no_after(self):
        op = ConsolidationOp(
            op="DELETE",
            fact_id_before=2,
            fact_id_after=None,
            fact_text_before="stale",
            fact_text_after=None,
            reason="superseded",
            run_ts=1000.0,
        )
        assert op.fact_id_after is None


class TestConsolidationReport:
    def test_counts_by_op_with_mixed(self):
        report = ConsolidationReport(
            principal_id="u1",
            facts_in=5,
            facts_out=3,
            ops=[
                ConsolidationOp(op="NOOP", fact_id_before=1),
                ConsolidationOp(op="DELETE", fact_id_before=2),
                ConsolidationOp(op="DELETE", fact_id_before=3),
                ConsolidationOp(op="UPDATE", fact_id_before=4),
                ConsolidationOp(op="UPDATE", fact_id_before=5),
            ],
        )
        counts = report.counts_by_op()
        assert counts == {"NOOP": 1, "DELETE": 2, "UPDATE": 2, "ADD": 0}

    def test_empty_report_has_zero_counts(self):
        report = ConsolidationReport(principal_id="u1", facts_in=0, facts_out=0)
        counts = report.counts_by_op()
        assert all(c == 0 for c in counts.values())
        assert set(counts.keys()) == {"NOOP", "DELETE", "UPDATE", "ADD"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
