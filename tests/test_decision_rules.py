"""
Tests for decision_rules.yaml policy engine
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def decision_rules():
    """Load decision rules config."""
    config_path = Path(__file__).parent.parent / "config" / "decision_rules.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def evaluate_condition(condition: dict, context: dict) -> bool:
    """Evaluate a rule condition against context."""
    field = condition["field"]
    operator = condition["operator"]
    value = condition["value"]

    # Get actual value from context (nested field access)
    actual = context
    for key in field.split("."):
        actual = actual.get(key)
        if actual is None:
            return False

    # Evaluate operator
    if operator == "greater_than":
        return actual > value
    elif operator == "less_than":
        return actual < value
    elif operator == "equals":
        return actual == value
    elif operator == "older_than":
        # Parse value like "180d"
        days = int(value.rstrip("d"))
        threshold = datetime.now() - timedelta(days=days)
        return datetime.fromisoformat(actual) < threshold
    else:
        raise ValueError(f"Unknown operator: {operator}")


class TestDecisionRules:
    """Test decision rule evaluation."""

    def test_triage_red_creates_decision_applied_event(self, decision_rules):
        """Test triage=red creates DECISION_APPLIED event with high risk."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "triage_red_high_risk")

        # Context: triage is red
        context = {"output": {"triage": "red"}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "emit_event"
        assert rule["action"]["event"] == "DECISION_APPLIED"
        assert rule["action"]["metadata"]["risk"] == "high"

    def test_pii_detected_quarantine_and_redact(self, decision_rules):
        """Test contains_pii=true triggers quarantine + redact."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "pii_quarantine")

        # Context: PII detected
        context = {"output": {"contains_pii": True}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "quarantine"
        assert rule["action"]["redact"] is True
        assert rule["action"]["metadata"]["reason"] == "pii_detected"

    def test_latency_breach_creates_slo_breach_event(self, decision_rules):
        """Test latency_ms > 2000 creates SLO_BREACH event with warn severity."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "latency_slo_breach")

        # Context: latency exceeds threshold
        context = {"latency_ms": 2500}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "emit_event"
        assert rule["action"]["event"] == "SLO_BREACH"
        assert rule["action"]["severity"] == "warn"
        assert rule["action"]["metadata"]["threshold_ms"] == 2000

    def test_auto_archive_rule(self, decision_rules):
        """Test auto-archive rule for old sessions."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "auto_archive_old_sessions")

        # Context: old session (>180 days)
        old_date = (datetime.now() - timedelta(days=200)).isoformat()
        context = {"session": {"created_at": old_date}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "archive"

    def test_reject_large_export(self, decision_rules):
        """Test reject rule for large exports."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "reject_large_export")

        # Context: large export
        context = {"export": {"size_mb": 600}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "reject"

    def test_fallback_llm_on_latency(self, decision_rules):
        """Test LLM fallback rule on high latency."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "fallback_llm_on_latency")

        # Context: high latency
        context = {"llm": {"p95_latency_ms": 6000}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "route"
        assert rule["action"]["model"] == "ollama/llama3:8b"

    def test_error_budget_alert(self, decision_rules):
        """Test error budget alert rule."""
        rule = next(r for r in decision_rules["rules"] if r["name"] == "alert_error_budget_low")

        # Context: low error budget
        context = {"error_budget": {"remaining": 0.05}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "alert"
        assert rule["action"]["severity"] == "critical"

    def test_block_mutation_without_event(self, decision_rules):
        """Test mutation blocking rule."""
        rule = next(
            r for r in decision_rules["rules"] if r["name"] == "block_mutation_without_event"
        )

        # Context: mutation without event
        context = {"mutation": {"has_event": False}}

        should_trigger = evaluate_condition(rule["condition"], context)
        assert should_trigger is True
        assert rule["action"]["type"] == "reject"

    def test_rule_disabled_check(self, decision_rules):
        """Test that disabled rules are not evaluated."""
        chaos_rule = next(r for r in decision_rules["rules"] if r["name"] == "trigger_chaos_drill")

        # Rule should be disabled by default
        assert chaos_rule["enabled"] is False

    def test_all_rules_have_required_fields(self, decision_rules):
        """Test that all rules have required fields."""
        required_fields = ["name", "enabled", "condition", "action"]

        for rule in decision_rules["rules"]:
            for field in required_fields:
                assert field in rule, f"Rule {rule.get('name', 'UNKNOWN')} missing field: {field}"

            # Condition must have field, operator, value
            assert "field" in rule["condition"]
            assert "operator" in rule["condition"]
            assert "value" in rule["condition"]

            # Action must have type
            assert "type" in rule["action"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
