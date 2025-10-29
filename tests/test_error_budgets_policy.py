"""
Tests for error_budgets.yml policy

Card: FI-RELIABILITY-STR-001
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def policy():
    """Load error budgets policy"""
    policy_path = Path("policies/error_budgets.yml")
    assert policy_path.exists(), "Policy file not found"

    with open(policy_path) as f:
        return yaml.safe_load(f)


def test_policy_structure(policy):
    """Test policy has required sections"""
    required_sections = [
        "slos",
        "budget_thresholds",
        "degradation",
        "chaos_drills",
        "monitoring",
        "review",
    ]

    for section in required_sections:
        assert section in policy, f"Missing section: {section}"


def test_slos_defined(policy):
    """Test all SLOs are properly defined"""
    slos = policy["slos"]

    required_services = [
        "ingestion_api",
        "timeline_api",
        "verify_api",
        "corpus_writes",
        "llm_routing",
    ]

    for service in required_services:
        assert service in slos, f"Missing SLO for {service}"

        slo = slos[service]
        assert "metric" in slo
        assert "window_days" in slo
        assert "error_budget_pct" in slo
        assert "description" in slo


def test_slo_targets(policy):
    """Test SLO targets match expected values"""
    slos = policy["slos"]

    # Timeline API: p99 <100ms
    assert slos["timeline_api"]["metric"] == "p99_latency"
    assert slos["timeline_api"]["target_ms"] == 100

    # Ingestion API: p95 <2s
    assert slos["ingestion_api"]["metric"] == "p95_latency"
    assert slos["ingestion_api"]["target_ms"] == 2000

    # Corpus writes: 99.9% success rate
    assert slos["corpus_writes"]["metric"] == "success_rate"
    assert slos["corpus_writes"]["target_pct"] == 99.9


def test_budget_thresholds(policy):
    """Test budget threshold actions"""
    thresholds = policy["budget_thresholds"]

    # Check threshold ordering
    assert thresholds["healthy"]["min_pct"] == 75
    assert thresholds["warning"]["min_pct"] == 50
    assert thresholds["critical"]["min_pct"] == 25
    assert thresholds["emergency"]["max_pct"] == 25

    # Check actions
    assert thresholds["healthy"]["action"] == "normal_operations"
    assert thresholds["warning"]["action"] == "monitor_closely"
    assert thresholds["critical"]["action"] == "freeze_risky_deployments"
    assert thresholds["emergency"]["action"] == "emergency_mode"


def test_degradation_policies(policy):
    """Test degradation policies are defined"""
    degradation = policy["degradation"]

    required_policies = ["backpressure", "circuit_breaker", "queue_shedding"]

    for pol in required_policies:
        assert pol in degradation
        assert "trigger" in degradation[pol]
        assert "action" in degradation[pol]
        assert "log_event" in degradation[pol]


def test_chaos_drills_scheduled(policy):
    """Test chaos drills are scheduled"""
    drills = policy["chaos_drills"]

    required_drills = [
        "network_partition",
        "corpus_file_lock",
        "llm_timeout_storm",
        "disk_full",
    ]

    for drill in required_drills:
        assert drill in drills
        assert "date" in drills[drill]
        assert "objective" in drills[drill]
        assert "success_criteria" in drills[drill]


def test_network_partition_drill(policy):
    """Test network partition drill config"""
    drill = policy["chaos_drills"]["network_partition"]

    assert drill["date"] == "2025-11-15"
    assert drill["duration_min"] == 90
    assert len(drill["success_criteria"]) == 3

    # Check success criteria
    criteria = drill["success_criteria"]
    assert any("Queue depth" in c for c in criteria)
    assert any("Recovery time" in c for c in criteria)
    assert any("Data integrity" in c for c in criteria)


def test_monitoring_config(policy):
    """Test monitoring dashboards and alerts"""
    monitoring = policy["monitoring"]

    assert "dashboards" in monitoring
    assert "alerts" in monitoring

    # Check dashboards exist
    assert len(monitoring["dashboards"]) >= 3

    # Check alert conditions
    alerts = monitoring["alerts"]
    severities = [a["severity"] for a in alerts]

    assert "WARNING" in severities
    assert "CRITICAL" in severities
    assert "INCIDENT" in severities


def test_review_process(policy):
    """Test review process is defined"""
    review = policy["review"]

    assert review["frequency"] == "quarterly"
    assert "next_review" in review
    assert "questions" in review
    assert len(review["questions"]) >= 4
