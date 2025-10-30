#!/usr/bin/env python3
"""
Generate Policy Manifest
Card: FI-POLICY-STR-001

Creates manifest.json with policy digest and test results
"""

import json
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    # Compute policy digest
    policy_path = Path("config/fi.policy.yaml")
    if not policy_path.exists():
        print("❌ Policy file not found: config/fi.policy.yaml")
        sys.exit(1)

    with open(policy_path, 'rb') as f:
        policy_digest = hashlib.sha256(f.read()).hexdigest()

    # Get git SHA
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        git_sha = "unknown"

    # Run tests and capture result
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_policy_enforcement.py", "-q"],
        capture_output=True,
        text=True
    )
    tests_passed = result.returncode == 0
    test_output = result.stdout

    # Count tests
    test_count = test_output.count("passed")

    # Create manifest
    manifest = {
        "id": f"POLICY_RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "git_sha": git_sha,
        "policy_digest": policy_digest,
        "policy_version": "1.0",
        "results": {
            "tests_passed": tests_passed,
            "count": test_count,
            "test_output": test_output.strip()
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policies": {
            "sovereignty.egress.default": "deny",
            "privacy.phi.enabled": False,
            "llm.budgets.monthly_usd": 200,
            "timeline.auto.enabled": False,
            "agents.enabled": False
        }
    }

    # Ensure output directory exists
    output_dir = Path("eval/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest_path = output_dir / "policy_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"✅ Manifest created: {manifest_path}")
    print(f"   Git SHA: {git_sha}")
    print(f"   Policy digest: {policy_digest[:16]}...")
    print(f"   Tests: {test_count} passed ({tests_passed and '✅' or '❌'})")

    sys.exit(0 if tests_passed else 1)


if __name__ == "__main__":
    main()
