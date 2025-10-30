# Policy Enforcement Integration Guide

**Card:** FI-POLICY-STR-001
**Date:** 2025-10-30
**Status:** Complete

## Overview

PolicyEnforcer has been integrated into the LLM middleware and provider adapters to enforce sovereignty, privacy, and cost policies at runtime.

## Integration Points

### 1. LLM Middleware (`backend/llm_middleware.py`)

**Location:** Lines 38, 45, 367-391, 415

**Integration:**
```python
from backend.policy_enforcer import get_policy_enforcer, PolicyViolation, redact

# Initialize enforcer
policy = get_policy_enforcer()

# After LLM generation:
# 1. Check cost budget
total_tokens = response_data["usage"]["in"] + response_data["usage"]["out"]
estimated_cost_cents = total_tokens * 0.0001
policy.check_cost(int(estimated_cost_cents), run_id=prompt_hash[:16])

# 2. Redact PII/PHI from response
original_text = llm_response.content
redacted_text = redact(original_text)

# 3. Return redacted text
return GenerateResponse(..., text=redacted_text)
```

**Enforcement:**
- Cost checking (post-generation, logs violations but doesn't block response)
- PII/PHI redaction (email, phone, SSN, CURP, RFC, MRN, etc.)
- Logs violations for audit trail

---

### 2. Claude Adapter (`backend/providers/claude.py`)

**Location:** Lines 18-22, 124-132, 238-246

**Integration:**
```python
from backend.policy_enforcer import PolicyViolation, get_policy_enforcer

# Initialize enforcer
policy = get_policy_enforcer()

# Before API call (generate method):
try:
    policy.check_egress(
        "https://api.anthropic.com",
        run_id=request.metadata.get("interaction_id") if request.metadata else None,
    )
except PolicyViolation as e:
    logger.error("EGRESS_BLOCKED", provider="claude", url="api.anthropic.com", error=str(e))
    raise LLMProviderError(f"External API call blocked by policy: {e}")

# Before streaming API call (stream method):
policy.check_egress("https://api.anthropic.com", run_id=...)
```

**Enforcement:**
- Egress blocking for external API calls
- Raises `LLMProviderError` if `sovereignty.egress.default=deny`
- Blocks BEFORE making HTTP request (hard stop)

---

### 3. Ollama Adapter (`backend/providers/ollama.py`)

**Location:** Lines 29-33, 177-185

**Integration:**
```python
from backend.policy_enforcer import PolicyViolation, get_policy_enforcer

# Initialize enforcer
policy = get_policy_enforcer()

# Before API call (inside retry loop):
try:
    policy.check_egress(
        f"{self.base_url}/api/generate",
        run_id=request.metadata.get("interaction_id") if request.metadata else None,
    )
except PolicyViolation as e:
    logger.error("EGRESS_BLOCKED", provider="ollama", url=self.base_url, error=str(e))
    raise LLMProviderError(f"API call blocked by policy: {e}")
```

**Enforcement:**
- Egress checking (for consistency, though Ollama is local-only)
- Local URLs (127.0.0.1) should pass unless policy explicitly denies

---

## Policy Configuration

**File:** `config/fi.policy.yaml`

### Sovereignty Policy
```yaml
sovereignty:
  egress:
    default: deny  # Blocks all external API calls
```

### Privacy Policy
```yaml
privacy:
  phi:
    enabled: false  # PHI detection disabled
  redaction:
    spoilers: true  # Redact sensitive data
    style_file: "config/redaction_style.yaml"
```

### Cost Policy
```yaml
llm:
  budgets:
    monthly_usd: 200  # 20,000 cents/month limit
```

---

## Test Coverage

### Policy Enforcement Tests
**File:** `tests/test_policy_enforcement.py`
- 30 tests covering sovereignty, privacy, cost, feature flags, utilities

### Redaction Tests
**File:** `tests/test_redaction.py`
- 10 tests covering email, phone, SSN, credit card, MRN, patient names, CURP, RFC

### Decision Rules Tests
**File:** `tests/test_decision_rules.py`
- 10 tests covering triage, PII quarantine, latency SLO, auto-archive

### Integration Tests
**File:** `tests/test_policy_integration.py`
- 15 tests covering:
  - PolicyEnforcer singleton and methods
  - Redaction functionality (email, phone, multiple patterns, preservation)
  - Egress policy checks (external/local URLs)
  - Cost budget enforcement
  - Provider imports (Claude, Ollama, middleware)

**Total:** 65 tests passing

---

## Runtime Behavior

### Egress Blocking (sovereignty.egress.default=deny)
1. Claude adapter: Blocks `https://api.anthropic.com` → raises `LLMProviderError`
2. Ollama adapter: Checks `http://127.0.0.1:11434/api/generate` (usually passes unless policy denies all)
3. Logged: `EGRESS_BLOCKED` with provider, URL, error

### Cost Checking
1. Triggered: After LLM generation in middleware
2. Calculation: `total_tokens * 0.0001` (placeholder estimation)
3. If exceeds budget: Logs `LLM_COST_VIOLATION` (doesn't block response, post-generation check)

### PII/PHI Redaction
1. Patterns applied: Email, phone, SSN, credit card, CURP, RFC, MRN, patient names, stop terms
2. Format: `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, etc.
3. Logged: `LLM_RESPONSE_REDACTED` with provider, prompt hash, redaction count

---

## Verification

### Quick Test
```bash
# Run all policy tests
python3 -m pytest tests/test_policy_enforcement.py tests/test_redaction.py tests/test_decision_rules.py tests/test_policy_integration.py -v

# Should output: 65 passed
```

### Policy Workflow
```bash
# Full verification
make policy-all

# Outputs:
# - Tests: 65/65 passing
# - Manifest: eval/results/policy_manifest.json
# - Digest: SHA256 hash of fi.policy.yaml
```

---

## Troubleshooting

### Issue: External API calls still working despite egress=deny
**Check:**
1. Verify `config/fi.policy.yaml` has `sovereignty.egress.default: deny`
2. Check PolicyEnforcer initialization in logs: `PolicyEnforcer loaded: 1.0`
3. Verify provider imports: `from backend.policy_enforcer import get_policy_enforcer`

### Issue: Cost violations not logged
**Check:**
1. Cost must exceed budget to trigger violation
2. Budget configured in cents: `monthly_usd: 200` = 20,000 cents
3. Estimation is post-generation (doesn't block response)

### Issue: PII not redacted
**Check:**
1. Verify pattern matches: Phone must be `+1-XXX-XXX-XXXX` format
2. Check redaction_style.yaml patterns are enabled
3. Verify `redact()` function is called: Check logs for `LLM_RESPONSE_REDACTED`

---

## Future Enhancements

1. **Router Integration:** Add policy checks to other API routers (sessions, exports, KPIs)
2. **Async Support:** Add policy enforcement to async/streaming endpoints
3. **Policy Drift Detection:** Monitor SHA256 digest changes in fi.policy.yaml
4. **Cost Tracking:** Replace estimation with actual provider token counts
5. **Whitelist/Blacklist:** Support egress allow-list for specific domains

---

## Related Documentation

- **Policy-as-Code:** `config/fi.policy.yaml`
- **Redaction Patterns:** `config/redaction_style.yaml`
- **QA Report:** `docs/qa/FI-POLICY-STR-001_QA.md`
- **Test Suite:** `tests/test_policy_*.py`

---

**Last Updated:** 2025-10-30
**Integration Status:** ✅ Complete (65/65 tests passing)
