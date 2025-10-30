# QA Report: FI-RELIABILITY-STR-001
## Golden Set Evaluation - Quality Assurance Evidence

**Card:** FI-OBS-RES-001 · Testers OG → Golden Set & Evaluación
**Version:** 1.0
**Status:** TEMPLATE
**Created:** 2025-10-30

---

## 1. Context and Scope

**Objective:** Establish reproducible evaluation framework for Free Intelligence LLM middleware using a Golden Set of 50+ prompts across 10 domains.

**Scope:**
- Golden Set: 50 prompts (eval/prompts.csv)
- Runner: run_eval.py with deterministic seeds
- Metrics: adequacy, factuality, latency (p50/p95/p99), cost, tokens
- Validation: jsonschema compliance + threshold enforcement

**Out of Scope:**
- Production LLM API integration (dry-run mode only)
- Real-time monitoring (separate observability stack)

---

## 2. Golden Set

**Source:** `eval/prompts.csv`
**Dataset Digest (SHA256):** `<to_be_computed>`
**Total Prompts:** 50

**Coverage by Domain:**
| Domain | Count | Examples |
|--------|-------|----------|
| technical_query | 8 | P001, P002, P003 |
| workflow | 6 | P011, P012 |
| architecture | 7 | P021, P022 |
| philosophy | 5 | P031, P032 |
| troubleshooting | 6 | P041, P042 |
| best_practices | 5 | P051, P052 |
| security | 4 | P061, P062 |
| performance | 4 | P071, P072 |
| integration | 3 | P081, P082 |
| edge_cases | 2 | P091, P092 |

**Criteria:**
- Each prompt has expected_keywords for adequacy scoring
- Categories match enum in metrics.schema.json
- Difficulty levels: easy (40%), medium (40%), hard (20%)

---

## 3. Runner

**Version:** run_eval.py v1.1 (commit: `<git_sha>`)
**Seed:** `fi-obs-001` (deterministic mode)
**Flags:**
- `--prompts eval/prompts.csv`
- `--dry-run` (mock LLM responses)
- `--output results/RUN_<timestamp>.json`
- `--report results/manifest.json`

**Limits:**
- Timeout: 30s per prompt
- Max retries: 3
- Rate limit: 10 req/s (n/a for dry-run)

---

## 4. Metrics

**Definitions:**
| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| adequacy | float | 0.0-1.0 | Response completeness vs. expected keywords |
| factuality | float | 0.0-1.0 | Factual accuracy (manual or LLM-as-judge) |
| latency_ms | int | ≥0 | Response time in milliseconds |
| cost_usd | float | ≥0 | API call cost in USD |
| tokens_in | int | ≥0 | Input tokens consumed |
| tokens_out | int | ≥0 | Output tokens generated |

**Aggregates:**
- avg_adequacy, avg_factuality
- p50_latency_ms, p95_latency_ms, p99_latency_ms
- total_cost_usd
- total_tokens (tokens_in + tokens_out)

---

## 5. Thresholds and Acceptance Criteria

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| avg_adequacy | ≥ 0.75 | 75% keyword coverage acceptable |
| avg_factuality | ≥ 0.80 | High accuracy required for clinical domain |
| p95_latency_ms | ≤ 2000 | Interactive UX requirement (2s SLO) |
| p99_latency_ms | ≤ 5000 | Worst-case acceptable (5s SLO) |
| total_cost_usd | ≤ 5.00 | Budget constraint for 50 prompts |

**Pass Criteria:**
- All thresholds met
- Schema validation passes (jsonschema)
- Reproducibility verified (same seed → same hashes)

---

## 6. Reproducible Procedure

**Prerequisites:**
- Python 3.11+
- Dependencies: `pip install jsonschema numpy`
- Git repo: free-intelligence (commit: `<git_sha>`)

**Commands:**
```bash
# 1. Clean previous runs
cd /Users/bernardurizaorozco/Documents/free-intelligence
make -C eval clean

# 2. Run evaluation with fixed seed
make -C eval run-eval SEED=fi-obs-001

# 3. Validate against schema
make -C eval validate

# 4. Generate QA report
make -C eval report

# 5. Verify reproducibility
sha256sum eval/prompts.csv eval/results/manifest.json
```

**Expected Output:**
- `eval/results/RUN_<timestamp>.json` (detailed results)
- `eval/results/manifest.json` (metadata + aggregates)
- `eval/report/QA_REPORT.md` (this file, populated)

---

## 7. Results and Deviations

**Run ID:** `<to_be_populated>`
**Timestamp:** `<iso8601>`
**Git SHA:** `<short_sha>`

**Aggregate Metrics:**
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| avg_adequacy | `<value>` | ≥ 0.75 | `<PASS/FAIL>` |
| avg_factuality | `<value>` | ≥ 0.80 | `<PASS/FAIL>` |
| p95_latency_ms | `<value>` | ≤ 2000 | `<PASS/FAIL>` |
| p99_latency_ms | `<value>` | ≤ 5000 | `<PASS/FAIL>` |
| total_cost_usd | `<value>` | ≤ 5.00 | `<PASS/FAIL>` |

**Deviations:**
- None (or list specific deviations from expected behavior)

**Artifacts:**
- Results JSON: `eval/results/RUN_<timestamp>.json`
- Manifest: `eval/results/manifest.json`
- Dataset digest: `<sha256>`

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
**Date:** `<iso8601>`
**Git Commit:** `<short_sha>`
**Git Tag:** `<v0.x.x>` (if applicable)

**Conformity Statement:**
This evaluation complies with FI-RELIABILITY-STR-001 requirements. All artifacts are reproducible, schema-validated, and meet acceptance criteria.

**Attestation:**
```
sha256(<manifest.json>) = <hash>
sha256(<prompts.csv>) = 1baf683674b07ad42829bf174b04fd7aaa5e68abad9ea3be766e79cc8695a36a
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

**End of QA Report Template**
