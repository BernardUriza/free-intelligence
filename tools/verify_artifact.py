#!/usr/bin/env python3
"""
Free Intelligence — Artifact Verifier
Verifies that cards have corresponding executable artifacts (not MDs)
"""

import json
import sys
from pathlib import Path

# Artifact registry: card_id -> expected artifact path
ARTIFACT_REGISTRY = {
    # Evaluation
    "FI-EVAL-001": "eval/prompts.csv",
    "FI-EVAL-002": "eval/metrics.schema.json",
    "FI-EVAL-003": "eval/run_eval.py",
    "FI-EVAL-004": "eval/Makefile",
    # Observability
    "FI-OBS-RES-001": "observability/error_budgets.yaml",
    "FI-OBS-002": "observability/alerts.prom",
    # Policies
    "FI-POLICY-001": "config/fi.policy.yaml",
    "FI-POLICY-002": "config/redaction_style.yaml",
    "FI-POLICY-003": "config/decision_rules.yaml",
    "FI-POLICY-004": "tests/test_redaction.py",
    "FI-POLICY-005": "tests/test_decision_rules.py",
    # Governance
    "FI-GOV-TOOL-001": "tools/verify_artifact.py",
}


def verify_artifact(card_id: str, artifact_path: str, base_path: Path) -> dict:
    """
    Verify artifact exists and is valid.

    Returns:
        dict with status, message, metadata
    """
    full_path = base_path / artifact_path

    if not full_path.exists():
        return {
            "status": "MISSING",
            "card_id": card_id,
            "artifact": artifact_path,
            "message": f"Artifact not found: {artifact_path}",
        }

    # Check it's not a large MD (>150 lines)
    if full_path.suffix == ".md":
        lines = sum(1 for _ in open(full_path))
        if lines > 150:
            return {
                "status": "INVALID",
                "card_id": card_id,
                "artifact": artifact_path,
                "message": f"Artifact is large MD ({lines} lines). Must be executable.",
            }
        # Small MDs (≤150 lines) are allowed per NO_MD policy
    else:
        # Check for executable types (non-MD files)
        valid_extensions = {".py", ".yaml", ".yml", ".json", ".prom", ".csv", ".sh"}
        if full_path.suffix not in valid_extensions and full_path.name != "Makefile":
            return {
                "status": "INVALID",
                "card_id": card_id,
                "artifact": artifact_path,
                "message": f"Artifact type not executable: {full_path.suffix}",
            }

    # File size check
    size_kb = full_path.stat().st_size / 1024

    return {
        "status": "VALID",
        "card_id": card_id,
        "artifact": artifact_path,
        "size_kb": round(size_kb, 2),
        "message": "✅ Artifact valid and executable",
    }


def verify_all(base_path: Path | None = None) -> list[dict]:
    """Verify all registered artifacts."""
    if base_path is None:
        base_path = Path(__file__).parent.parent

    results = []
    for card_id, artifact_path in ARTIFACT_REGISTRY.items():
        result = verify_artifact(card_id, artifact_path, base_path)
        results.append(result)

    return results


def print_report(results: list[dict]):
    """Print verification report."""
    print("=" * 60)
    print("Free Intelligence — Artifact Verification Report")
    print("=" * 60)
    print()

    valid = [r for r in results if r["status"] == "VALID"]
    missing = [r for r in results if r["status"] == "MISSING"]
    invalid = [r for r in results if r["status"] == "INVALID"]

    print("📊 Summary:")
    print(f"  ✅ Valid:   {len(valid)}/{len(results)}")
    print(f"  ❌ Missing: {len(missing)}/{len(results)}")
    print(f"  ⚠️  Invalid: {len(invalid)}/{len(results)}")
    print()

    if missing:
        print("❌ Missing Artifacts:")
        for r in missing:
            print(f"  • {r['card_id']}: {r['artifact']}")
        print()

    if invalid:
        print("⚠️  Invalid Artifacts:")
        for r in invalid:
            print(f"  • {r['card_id']}: {r['message']}")
        print()

    if valid:
        print("✅ Valid Artifacts:")
        for r in valid:
            print(f"  • {r['card_id']}: {r['artifact']} ({r['size_kb']}KB)")

    print()
    print("=" * 60)

    return len(missing) + len(invalid) == 0


def main():
    """Main entry point."""
    results = verify_all()
    all_valid = print_report(results)

    # Save results to JSON
    output_path = Path(__file__).parent.parent / "tools" / "artifact_verification.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "timestamp": "2025-10-29T00:00:00Z",
                "total": len(results),
                "valid": len([r for r in results if r["status"] == "VALID"]),
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"💾 Results saved: {output_path}")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
