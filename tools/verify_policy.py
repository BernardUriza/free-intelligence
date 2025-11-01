#!/usr/bin/env python3
"""
Verify Policy Artifacts
Card: FI-POLICY-STR-001

Verifies policy files, digest, and test results
"""

import hashlib
import json
import sys
from pathlib import Path


def main():
    # Check required files
    required_files = [
        "config/fi.policy.yaml",
        "config/redaction_style.yaml",
        "config/decision_rules.yaml",
        "backend/policy_enforcer.py",
        "tests/test_policy_enforcement.py",
    ]

    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)

    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        sys.exit(1)

    print("✅ All required policy files present")

    # Verify manifest
    manifest_path = Path("eval/results/policy_manifest.json")
    if not manifest_path.exists():
        print("❌ Manifest not found. Run 'make policy-report' first")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"✅ Manifest found: {manifest['id']}")

    # Verify policy digest matches
    policy_path = Path("config/fi.policy.yaml")
    with open(policy_path, "rb") as f:
        current_digest = hashlib.sha256(f.read()).hexdigest()

    if current_digest != manifest["policy_digest"]:
        print("⚠️  Policy file changed since manifest")
        print(f"   Manifest: {manifest['policy_digest'][:16]}...")
        print(f"   Current:  {current_digest[:16]}...")
        print("   Run 'make policy-report' to regenerate manifest")
    else:
        print(f"✅ Policy digest verified: {current_digest[:16]}...")

    # Verify tests passed
    if not manifest["results"]["tests_passed"]:
        print("❌ Tests failed in manifest")
        sys.exit(1)

    print(f"✅ All {manifest['results']['count']} tests passed")
    print("✅ Artifacts verified")

    # Display policy summary
    print("\n📋 Policy Summary:")
    for key, value in manifest.get("policies", {}).items():
        print(f"   {key}: {value}")

    sys.exit(0)


if __name__ == "__main__":
    main()
