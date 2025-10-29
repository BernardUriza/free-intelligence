"""
Tests for fi_diag module

Card: FI-CORE-FEAT-005
"""

import json
from pathlib import Path

import pytest

from fi_diag.run import DiagnosticRunner


def test_diagnostic_runner_init():
    """Test DiagnosticRunner initialization"""
    runner = DiagnosticRunner(dry_run=True)
    assert runner.dry_run is True
    assert runner.results == []


def test_run_all_checks():
    """Test running all diagnostic checks"""
    runner = DiagnosticRunner(dry_run=True)
    results = runner.run_all_checks()

    # Should have 4 checks
    assert len(results) == 4

    # Check names
    check_names = [r.check_name for r in results]
    assert "corpus_integrity" in check_names
    assert "api_latency" in check_names
    assert "disk_space" in check_names
    assert "docker_health" in check_names


def test_check_corpus_integrity():
    """Test corpus integrity check"""
    runner = DiagnosticRunner(dry_run=True)
    result = runner.check_corpus_integrity()

    assert result.check_name == "corpus_integrity"
    assert result.status in ["OK", "WARNING", "CRITICAL"]
    assert result.message is not None
    assert result.duration_ms >= 0


def test_check_api_latency():
    """Test API latency check"""
    runner = DiagnosticRunner(dry_run=True)
    result = runner.check_api_latency()

    assert result.check_name == "api_latency"
    assert result.status in ["OK", "WARNING", "CRITICAL"]
    assert result.duration_ms >= 0


def test_check_disk_space():
    """Test disk space check"""
    runner = DiagnosticRunner(dry_run=True)
    result = runner.check_disk_space()

    assert result.check_name == "disk_space"
    assert result.status in ["OK", "WARNING", "CRITICAL"]
    assert result.duration_ms >= 0

    # Should have disk usage details
    if result.details:
        assert "used_pct" in result.details
        assert 0 <= result.details["used_pct"] <= 100


def test_check_docker_health():
    """Test Docker health check"""
    runner = DiagnosticRunner(dry_run=True)
    result = runner.check_docker_health()

    assert result.check_name == "docker_health"
    assert result.status in ["OK", "WARNING", "CRITICAL"]
    assert result.duration_ms >= 0


def test_generate_report():
    """Test report generation"""
    runner = DiagnosticRunner(dry_run=True)
    runner.run_all_checks()

    report = runner.generate_report()

    assert "timestamp" in report
    assert "overall_status" in report
    assert "summary" in report
    assert "checks" in report

    # Summary should have counts
    assert "total_checks" in report["summary"]
    assert "critical" in report["summary"]
    assert "warning" in report["summary"]
    assert "ok" in report["summary"]

    # Overall status should be determined correctly
    assert report["overall_status"] in ["OK", "WARNING", "CRITICAL"]


def test_report_json_serialization(tmp_path):
    """Test that report can be serialized to JSON"""
    runner = DiagnosticRunner(dry_run=True)
    runner.run_all_checks()

    report = runner.generate_report()

    # Write to temp file
    output_file = tmp_path / "test_report.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    # Read back and validate
    with open(output_file) as f:
        loaded_report = json.load(f)

    assert loaded_report["overall_status"] == report["overall_status"]
    assert len(loaded_report["checks"]) == len(report["checks"])


@pytest.mark.skipif(not Path("storage/corpus.h5").exists(), reason="Corpus file not found")
def test_corpus_integrity_with_real_corpus():
    """Test corpus integrity with actual corpus.h5 file"""
    runner = DiagnosticRunner(dry_run=True)
    result = runner.check_corpus_integrity()

    # Should succeed if corpus exists
    assert result.status in ["OK", "WARNING"]

    # Should have session count in details
    if result.details:
        assert "sessions" in result.details
        assert isinstance(result.details["sessions"], int)
