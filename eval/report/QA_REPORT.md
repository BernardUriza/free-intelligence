# QA Report: FI-RELIABILITY-STR-001
## Golden Set Evaluation - Quality Assurance Evidence

**Card:** FI-OBS-RES-001 · Testers OG → Golden Set & Evaluación
**Version:** 1.0
**Status:** PARTIAL (3/5) ⚠️
**Generated:** 2025-10-29T21:15:25.777174

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
**Dataset Digest (SHA256):** `1baf683674b07ad42829bf174b04fd7aaa5e68abad9ea3be766e79cc8695a36a`
**Total Prompts:** 50

**Coverage by Domain:**
| Domain | Count | Avg Adequacy | Avg Factuality | Avg Latency (ms) |
|--------|-------|--------------|----------------|------------------|
| architecture | 5 | 0.600 | 0.832 | 2016 |
| best_practices | 5 | 0.750 | 0.826 | 1154 |
| edge_cases | 5 | 0.700 | 0.883 | 1990 |
| integration | 5 | 0.500 | 0.866 | 1729 |
| performance | 5 | 0.550 | 0.863 | 1165 |
| philosophy | 5 | 0.750 | 0.857 | 2507 |
| security | 5 | 0.800 | 0.840 | 1479 |
| technical_query | 5 | 0.650 | 0.769 | 1031 |
| troubleshooting | 5 | 0.650 | 0.894 | 1599 |
| workflow | 5 | 0.733 | 0.925 | 824 |

**Criteria:**
- Each prompt has expected_keywords for adequacy scoring
- Categories match enum in metrics.schema.json
- Difficulty levels: easy (40%), medium (40%), hard (20%)

---

## 3. Runner

**Version:** run_eval.py@1.1
**Seed:** `fi-obs-001`
**Git SHA:** `4f8d158`
**Run ID:** `RUN_20251030_031445`
**Model:** mock-llm

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
- avg_adequacy: 0.668
- avg_factuality: 0.855
- p50_latency_ms: 1239
- p95_latency_ms: 2574
- p99_latency_ms: 2628
- total_cost_usd: $0.133836
- total_tokens: 9,508

---

## 5. Thresholds and Acceptance Criteria

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| avg_adequacy | 0.668 | ≥ 0.75 | FAIL ❌ |
| avg_factuality | 0.855 | ≥ 0.80 | PASS ✅ |
| p95_latency_ms | 2574 | ≤ 2000 | FAIL ❌ |
| p99_latency_ms | 2628 | ≤ 5000 | PASS ✅ |
| total_cost_usd | 0.134 | ≤ 5.00 | PASS ✅ |

**Overall Status:** 3/5 checks passed

---

## 6. Reproducible Procedure

**Prerequisites:**
- Python 3.11+
- Dependencies: `pip install jsonschema numpy`
- Git repo: free-intelligence (commit: 4f8d158)

**Commands:**
```bash
# 1. Clean previous runs
cd /Users/bernardurizaorozco/Documents/free-intelligence
make -C eval clean

# 2. Run evaluation with fixed seed
make -C eval all SEED=fi-obs-001

# 3. Verify reproducibility
sha256sum eval/prompts.csv eval/results/manifest.json
```

**Expected Output:**
- `eval/results/run_20251030_031445.json` (detailed results)
- `eval/results/manifest.json` (metadata + aggregates)
- `eval/report/QA_REPORT.md` (this file)

---

## 7. Results and Deviations

**Run ID:** `RUN_20251030_031445`
**Timestamp:** `2025-10-30T03:14:45.788112+00:00`
**Git SHA:** `4f8d158`

**Deviations:**
- **avg_adequacy**: 0.668 (expected 0.75)
- **p95_latency_ms**: 2574 (expected 2000)

**Artifacts:**
- Results JSON: `eval/results/run_20251030_031445.json`
- Manifest: `eval/results/manifest.json`
- Dataset digest: `1baf683674b07ad4...`

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
**Date:** 2025-10-29T21:15:25.777213
**Git Commit:** 4f8d158
**Run ID:** RUN_20251030_031445

**Conformity Statement:**
This evaluation complies with FI-RELIABILITY-STR-001 requirements. All artifacts are reproducible, schema-validated, and partially meet acceptance criteria.

**Attestation:**
```
sha256(prompts.csv) = 1baf683674b07ad42829bf174b04fd7aaa5e68abad9ea3be766e79cc8695a36a
run_id = RUN_20251030_031445
git_sha = 4f8d158
```

---

## Appendix: Commands Reference

```bash
# Full evaluation workflow
make -C eval all SEED=fi-obs-001

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
**Status:** ⚠️ 2 CHECK(S) FAILED
