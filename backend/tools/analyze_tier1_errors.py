#!/usr/bin/env python3
"""Analyze and extract Tier 1 critical type errors."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def analyze_tier1_errors():
    """Extract reportUndefinedVariable and reportArgumentType errors."""
    results_path = Path(
        "/Users/bernardurizaorozco/Documents/free-intelligence/ops/type_check_results/results.json"
    )

    if not results_path.exists():
        print(f"❌ Results file not found: {results_path}")
        return

    with open(results_path) as f:
        data = json.load(f)

    # Filter Tier 1 errors
    tier1_rules = {"reportUndefinedVariable", "reportArgumentType"}
    tier1_errors = [
        error
        for error in data["details"]
        if error.get("rule") in tier1_rules and error.get("severity") == "error"
    ]

    # Group by rule and file
    by_rule = defaultdict(list)
    by_file = defaultdict(list)

    for error in tier1_errors:
        rule = error.get("rule", "unknown")
        file_path = error.get("file", "unknown")
        by_rule[rule].append(error)
        by_file[file_path].append(error)

    # Print summary
    print(f"\n{'='*60}")
    print(f"🔍 Tier 1 Critical Errors Analysis")
    print(f"{'='*60}")
    print(f"Total Tier 1 Errors: {len(tier1_errors)}")
    print(f"\nBy Rule:")
    for rule, errors in sorted(by_rule.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  - {rule}: {len(errors)}")

    print(f"\nTop Files with Tier 1 Errors:")
    for file_path, errors in sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        short_path = file_path.replace(
            "/Users/bernardurizaorozco/Documents/free-intelligence/backend/", ""
        )
        print(f"  - {short_path}: {len(errors)}")

    # Export detailed list
    output = {
        "total": len(tier1_errors),
        "by_rule": {rule: len(errors) for rule, errors in by_rule.items()},
        "errors": tier1_errors,
    }

    output_path = Path(
        "/Users/bernardurizaorozco/Documents/free-intelligence/ops/type_check_results/tier1_errors.json"
    )
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Exported to: {output_path}")

    # Show first 5 errors of each type
    print(f"\n{'='*60}")
    print("📋 Sample Errors (first 5 of each type):")
    print(f"{'='*60}")

    for rule in tier1_rules:
        errors = by_rule.get(rule, [])
        if errors:
            print(f"\n{rule} ({len(errors)} total):")
            for error in errors[:5]:
                file_path = error.get("file", "").replace(
                    "/Users/bernardurizaorozco/Documents/free-intelligence/backend/", ""
                )
                line = error.get("line", "?")
                message = error.get("message", "").split("\n")[0]  # First line only
                print(f"  {file_path}:{line} - {message}")


if __name__ == "__main__":
    analyze_tier1_errors()
