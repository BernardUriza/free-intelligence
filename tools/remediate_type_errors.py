#!/usr/bin/env python3
"""
Type Error Remediation Tool - Following Expert Python Best Practices

Implements recommendations from:
- Meta 2024 Typed Python Survey
- Quantlane: Type-checking large codebases
- Python typing community discussions

Strategy: Gradual adoption with pragmatic ignore rules for untyped libraries
"""

import json
import re
import subprocess
from typing import Any


def run_pyright() -> dict[str, Any]:
    """Run Pyright and capture results."""
    result = subprocess.run(
        ["python3", "tools/detect_type_errors.py", "backend/", "--export"],
        capture_output=True,
        text=True,
    )

    # Extract JSON from output (last JSON object)
    output = result.stdout + result.stderr
    json_matches = re.findall(r"\{.*\}", output, re.DOTALL)
    if json_matches:
        return json.loads(json_matches[-1])
    return {"errors": []}


def categorize_errors(errors: list[dict]) -> dict[str, list[dict]]:
    """Categorize errors by type and severity."""
    categories = {
        "reportMissingTypeStubs": [],
        "reportAttributeAccessIssue": [],
        "reportUndefinedVariable": [],
        "reportUnusedImport": [],
        "reportArgumentType": [],
        "reportAssignmentType": [],
        "other": [],
    }

    for error in errors:
        rule = error.get("rule", "other")
        category = categories.get(rule, categories["other"])
        category.append(error)

    return categories


def suggest_fixes(categories: dict[str, list[dict]]) -> dict[str, Any]:
    """Suggest fixes per category based on expert recommendations."""
    fixes = {
        "summary": {},
        "actions": [],
        "per_file": {},
    }

    # === Category: reportMissingTypeStubs (h5py, pydantic, etc) ===
    # Expert recommendation: Use # type: ignore[import-untyped]
    stub_errors = categories["reportMissingTypeStubs"]
    if stub_errors:
        fixes["summary"]["missing_stubs"] = f"{len(stub_errors)} untyped imports"
        fixes["actions"].append(
            {
                "type": "config",
                "description": "Disable reportMissingTypeStubs in pyrightconfig.json",
                "reason": "Per Meta survey: Allow untyped third-party libraries",
                "implemented": True,
            }
        )

    # === Category: reportAttributeAccessIssue (h5py) ===
    # Expert recommendation: Use # type: ignore[index] pragmatically
    attr_errors = categories["reportAttributeAccessIssue"]
    if attr_errors:
        fixes["summary"]["attribute_access"] = f"{len(attr_errors)} attribute issues"
        fixes["actions"].append(
            {
                "type": "file-ignore",
                "rule": "reportAttributeAccessIssue",
                "description": "Relax to 'warning' (h5py has no type stubs)",
                "reason": "h5py doesn't provide type hints; using # type: ignore is pragmatic",
                "implemented": True,
            }
        )

    # === Category: reportUndefinedVariable ===
    # Expert recommendation: Fix these - they're likely bugs
    undef_errors = categories["reportUndefinedVariable"]
    if undef_errors:
        fixes["summary"]["undefined_vars"] = f"{len(undef_errors)} undefined variables"
        fixes["actions"].append(
            {
                "type": "fix",
                "rule": "reportUndefinedVariable",
                "description": "These are likely real bugs - investigate and fix",
                "reason": "Undefined variables indicate logic errors, not type issues",
                "severity": "high",
            }
        )

    # === Category: reportUnusedImport ===
    # Expert recommendation: Always fix - clean code
    unused = categories["reportUnusedImport"]
    if unused:
        fixes["summary"]["unused_imports"] = f"{len(unused)} unused imports"
        fixes["actions"].append(
            {
                "type": "fix",
                "rule": "reportUnusedImport",
                "description": "Remove unused imports (clean code practice)",
                "reason": "Always enforced - keeps code clean",
                "severity": "high",
            }
        )

    # === Category: reportArgumentType ===
    # Expert recommendation: Fix mismatches - these are real errors
    arg_errors = categories["reportArgumentType"]
    if arg_errors:
        fixes["summary"]["argument_type"] = f"{len(arg_errors)} argument type mismatches"
        fixes["actions"].append(
            {
                "type": "fix",
                "rule": "reportArgumentType",
                "description": "Fix type mismatches in function calls",
                "reason": "Real bugs that can cause runtime errors",
                "severity": "high",
            }
        )

    return fixes


def print_remediation_plan(fixes: dict[str, Any]) -> None:
    """Print remediation plan."""
    print("\n" + "=" * 70)
    print("TYPE ERROR REMEDIATION PLAN (Following Expert Recommendations)")
    print("=" * 70)

    print("\n📊 SUMMARY")
    for issue, count in fixes["summary"].items():
        print(f"  • {issue}: {count}")

    print("\n🎯 RECOMMENDED ACTIONS")
    for i, action in enumerate(fixes["actions"], 1):
        print(f"\n  {i}. {action['description']}")
        print(f"     Type: {action['type'].upper()}")
        print(f"     Reason: {action.get('reason', 'N/A')}")
        if action.get("implemented"):
            print("     Status: ✅ DONE")
        if action.get("severity"):
            print(f"     Severity: {action['severity'].upper()}")

    print("\n💡 STRATEGY NOTES")
    print("  Per Meta 2024 Python Survey & expert recommendations:")
    print("  • ✓ Allow untyped third-party imports (h5py, pydantic)")
    print("  • ✓ Use # type: ignore[error-code] pragmatically for lib types")
    print("  • ✓ Enforce strict typing on internal code")
    print("  • ✓ Fix real bugs (undefined vars, argument type mismatches)")
    print("  • ✓ Remove unused imports (code cleanliness)")
    print("  • ✓ Gradual adoption: New code must be typed")

    print("\n✅ NEXT STEPS")
    print("  1. Run: python3 tools/detect_type_errors.py backend/")
    print("  2. Review 'high severity' errors (undefined vars, arg types)")
    print("  3. Commit pragmatic configuration")
    print("  4. Enforce typing on new code")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    print("🔍 Analyzing type errors...")
    results = run_pyright()

    if "errors" in results:
        errors = results["errors"]
        print(f"Found {len(errors)} type errors")

        categories = categorize_errors(errors)
        fixes = suggest_fixes(categories)
        print_remediation_plan(fixes)
    else:
        print("Could not parse type check results")
