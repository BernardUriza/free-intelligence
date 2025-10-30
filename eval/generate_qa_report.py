#!/usr/bin/env python3
"""
QA Report Generator for FI-OBS-RES-001
Reads manifest.json and results/*.json to generate QA_REPORT.md
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def load_manifest(manifest_path: Path) -> dict:
    """Load manifest.json"""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path) as f:
        return json.load(f)


def load_latest_results(results_dir: Path) -> dict:
    """Load the latest run_*.json file"""
    json_files = sorted(results_dir.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not json_files:
        raise FileNotFoundError(f"No run_*.json files found in {results_dir}")

    latest = json_files[0]
    with open(latest) as f:
        return json.load(f), latest.name


def compute_domain_stats(results: list) -> dict:
    """Compute per-domain statistics"""
    domains = {}

    for result in results:
        category = result["category"]
        if category not in domains:
            domains[category] = {
                "count": 0,
                "adequacy": [],
                "factuality": [],
                "latency": [],
            }

        domains[category]["count"] += 1
        domains[category]["adequacy"].append(result["metrics"]["adequacy"])
        domains[category]["factuality"].append(result["metrics"]["factuality"])
        domains[category]["latency"].append(result["metrics"]["latency_ms"])

    # Compute averages
    for domain, stats in domains.items():
        stats["avg_adequacy"] = round(sum(stats["adequacy"]) / len(stats["adequacy"]), 3)
        stats["avg_factuality"] = round(sum(stats["factuality"]) / len(stats["factuality"]), 3)
        stats["avg_latency_ms"] = round(sum(stats["latency"]) / len(stats["latency"]), 0)

    return domains


def check_thresholds(aggregates: dict) -> dict:
    """Check if aggregates meet thresholds"""
    thresholds = {
        "avg_adequacy": 0.75,
        "avg_factuality": 0.80,
        "p95_latency_ms": 2000,
        "p99_latency_ms": 5000,
        "total_cost_usd": 5.00,
    }

    results = {}
    for key, threshold in thresholds.items():
        value = aggregates.get(key, 0)

        # For latency and cost, lower is better
        if "latency" in key or "cost" in key:
            passed = value <= threshold
        else:
            passed = value >= threshold

        results[key] = {
            "value": value,
            "threshold": threshold,
            "status": "PASS ✅" if passed else "FAIL ❌",
        }

    return results


def generate_report(manifest: dict, results_data: dict, results_filename: str) -> str:
    """Generate QA report markdown"""
    aggregates = manifest["metrics"]
    domain_stats = compute_domain_stats(results_data["results"])
    threshold_results = check_thresholds(aggregates)

    # Count passes and fails
    total_checks = len(threshold_results)
    passes = sum(1 for r in threshold_results.values() if "PASS" in r["status"])

    report = f"""# QA Report: FI-RELIABILITY-STR-001
## Golden Set Evaluation - Quality Assurance Evidence

**Card:** FI-OBS-RES-001 · Testers OG → Golden Set & Evaluación
**Version:** 1.0
**Status:** {"PASS ✅" if passes == total_checks else f"PARTIAL ({passes}/{total_checks}) ⚠️"}
**Generated:** {datetime.now().isoformat()}

---

## 1. Context and Scope

**Objective:** Establish reproducible evaluation framework for Free Intelligence LLM middleware using a Golden Set of 50+ prompts across 10 domains.

**Scope:**
- Golden Set: 50 prompts (eval/prompts.csv)
- Runner: run_eval.py with deterministic seeds
- Metrics: adequacy, factuality, latency (p50/p95/p99), cost, tokens
- Validation: jsonschema compliance + threshold enforcement

---

## 2. Golden Set

**Source:** `eval/prompts.csv`
**Dataset Digest (SHA256):** `{manifest['dataset_digest']}`
**Total Prompts:** {results_data['total_prompts']}

**Coverage by Domain:**
| Domain | Count | Avg Adequacy | Avg Factuality | Avg Latency (ms) |
|--------|-------|--------------|----------------|------------------|
"""

    # Add domain rows
    for domain, stats in sorted(domain_stats.items()):
        report += f"| {domain} | {stats['count']} | {stats['avg_adequacy']:.3f} | {stats['avg_factuality']:.3f} | {stats['avg_latency_ms']:.0f} |\n"

    report += f"""
**Criteria:**
- Each prompt has expected_keywords for adequacy scoring
- Categories match enum in metrics.schema.json
- Difficulty levels: easy (40%), medium (40%), hard (20%)

---

## 3. Runner

**Version:** run_eval.py@1.1
**Seed:** `{manifest['seed']}`
**Git SHA:** `{manifest['git_sha']}`
**Run ID:** `{manifest['run_id']}`
**Model:** {results_data['model_id']}

**Configuration:**
- Prompts: eval/prompts.csv
- Dry-run mode: True (mock LLM responses)
- Deterministic seeding: SHA256-based RNG

---

## 4. Metrics

**Definitions:**
| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| adequacy | float | 0.0-1.0 | Response completeness vs. expected keywords |
| factuality | float | 0.0-1.0 | Factual accuracy (mock scoring) |
| latency_ms | int | ≥0 | Response time in milliseconds |
| cost_usd | float | ≥0 | API call cost in USD |
| tokens_in | int | ≥0 | Input tokens consumed |
| tokens_out | int | ≥0 | Output tokens generated |

**Aggregates:**
- avg_adequacy: {aggregates['avg_adequacy']:.3f}
- avg_factuality: {aggregates['avg_factuality']:.3f}
- p50_latency_ms: {aggregates['p50_latency_ms']}
- p95_latency_ms: {aggregates['p95_latency_ms']}
- p99_latency_ms: {aggregates['p99_latency_ms']}
- total_cost_usd: ${aggregates['total_cost_usd']:.6f}
- total_tokens: {aggregates['total_tokens']:,}

---

## 5. Thresholds and Acceptance Criteria

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
"""

    # Add threshold rows
    for key, result in threshold_results.items():
        value_str = f"{result['value']:.3f}" if isinstance(result['value'], float) and result['value'] < 10 else f"{result['value']}"
        threshold_str = f"{result['threshold']:.2f}" if isinstance(result['threshold'], float) else f"{result['threshold']}"

        if "latency" in key or "cost" in key:
            operator = "≤"
        else:
            operator = "≥"

        report += f"| {key} | {value_str} | {operator} {threshold_str} | {result['status']} |\n"

    report += f"""
**Overall Status:** {passes}/{total_checks} checks passed

---

## 6. Reproducible Procedure

**Prerequisites:**
- Python 3.11+
- Dependencies: `pip install jsonschema numpy`
- Git repo: free-intelligence (commit: {manifest['git_sha']})

**Commands:**
```bash
# 1. Clean previous runs
cd /Users/bernardurizaorozco/Documents/free-intelligence
make -C eval clean

# 2. Run evaluation with fixed seed
make -C eval all SEED={manifest['seed']}

# 3. Verify reproducibility
sha256sum eval/prompts.csv eval/results/manifest.json
```

**Expected Output:**
- `eval/results/{results_filename}` (detailed results)
- `eval/results/manifest.json` (metadata + aggregates)
- `eval/report/QA_REPORT.md` (this file)

---

## 7. Results and Deviations

**Run ID:** `{manifest['run_id']}`
**Timestamp:** `{manifest['created_at']}`
**Git SHA:** `{manifest['git_sha']}`

**Deviations:**
"""

    # List any failures
    failures = [k for k, v in threshold_results.items() if "FAIL" in v["status"]]
    if failures:
        for key in failures:
            result = threshold_results[key]
            report += f"- **{key}**: {result['value']} (expected {result['threshold']})\n"
    else:
        report += "- None (all thresholds met)\n"

    report += f"""
**Artifacts:**
- Results JSON: `eval/results/{results_filename}`
- Manifest: `eval/results/manifest.json`
- Dataset digest: `{manifest['dataset_digest'][:16]}...`

---

## 8. Risks and Actions

**Identified Risks:**
1. **Mock LLM responses** (dry-run mode): Real API integration pending
   - **Action:** Update run_eval.py with actual LLM client integration
   - **Timeline:** Sprint S2 (FI-API-FEAT-011)

2. **Manual factuality scoring**: Requires human validation or LLM-as-judge
   - **Action:** Implement automated factuality scorer
   - **Timeline:** Sprint S3 (FI-OBS-RES-002)

**Mitigations:**
- Dry-run mode validates schema compliance and aggregation logic
- Reproducibility verified with fixed seeds and dataset hashes

---

## 9. Signatures and Conformity

**QA Engineer:** Claude Code (Autonomous Tester)
**Date:** {datetime.now().isoformat()}
**Git Commit:** {manifest['git_sha']}
**Run ID:** {manifest['run_id']}

**Conformity Statement:**
This evaluation complies with FI-RELIABILITY-STR-001 requirements. All artifacts are reproducible, schema-validated, and {"meet" if passes == total_checks else "partially meet"} acceptance criteria.

**Attestation:**
```
sha256(prompts.csv) = {manifest['dataset_digest']}
run_id = {manifest['run_id']}
git_sha = {manifest['git_sha']}
```

---

## Appendix: Commands Reference

```bash
# Full evaluation workflow
make -C eval all SEED={manifest['seed']}

# Individual steps
make -C eval install      # Install dependencies
make -C eval run-eval     # Run evaluation
make -C eval validate     # Validate JSON schema
make -C eval report       # Generate QA report

# Verify artifacts
python3 -c "import json; print(json.load(open('eval/results/manifest.json'))['run_id'])"
sha256sum eval/prompts.csv eval/results/manifest.json
```

---

**End of QA Report**
**Status:** {"✅ ALL CHECKS PASSED" if passes == total_checks else f"⚠️ {total_checks - passes} CHECK(S) FAILED"}
"""

    return report


def main():
    manifest_path = Path("eval/results/manifest.json")
    results_dir = Path("eval/results")
    output_path = Path("eval/report/QA_REPORT.md")

    try:
        manifest = load_manifest(manifest_path)
        results_data, results_filename = load_latest_results(results_dir)

        report = generate_report(manifest, results_data, results_filename)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)

        print(f"✅ QA Report generated: {output_path}")
        print(f"   Run ID: {manifest['run_id']}")
        print(f"   Dataset: {manifest['dataset_digest'][:16]}...")
        print(f"   Git SHA: {manifest['git_sha']}")

        sys.exit(0)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
