# Evaluation Framework - Free Intelligence

**Card**: FI-OBS-RES-001
**Axioma**: Gnóstico/Alquimista = Tester OG
**Owner**: ML/Observability Team
**Version**: 1.0.0
**Date**: 2025-10-29

---

## Overview

Free Intelligence evaluation framework implements Axiom 4: **"Quien busca verdad primero falsifica hipótesis"**.

This golden set contains **50 prompts** across 10 categories, designed to evaluate:
1. **Adecuación** (appropriateness): Does response match prompt intent?
2. **Factualidad** (factuality): Are claims accurate per docs?
3. **p95 Latency**: Response time under realistic load
4. **Cost**: Token usage per prompt category

---

## Golden Set Structure

### Categories (10)

| Category | Count | Difficulty | Focus |
|----------|-------|------------|-------|
| **technical_query** | 5 | easy-medium | Core concepts explanation |
| **workflow** | 5 | easy-medium | API usage patterns |
| **architecture** | 5 | medium-hard | System design principles |
| **philosophy** | 5 | hard | Hermetic axioms mapping |
| **troubleshooting** | 5 | easy-hard | Error diagnosis |
| **best_practices** | 5 | easy-hard | Recommended patterns |
| **security** | 5 | medium-hard | Privacy & compliance |
| **performance** | 5 | easy-hard | SLO targets & optimization |
| **integration** | 5 | medium-hard | External system interaction |
| **edge_cases** | 5 | medium-hard | Failure scenarios |

---

## Metrics

### 1. Adecuación (Appropriateness)

**Definition**: Does the response address the prompt intent?

**Scoring** (1-5):
- **5**: Perfect match, complete answer
- **4**: Good match, minor gaps
- **3**: Partial match, missing key info
- **2**: Tangential, mostly off-topic
- **1**: Completely wrong topic

**Evaluation Method**:
- Manual review by domain expert
- Check for presence of `expected_keywords` (CSV column)
- Validate structure (e.g., list for "What APIs", explanation for "How does X work")

**Example**:
```
Prompt: "What is the difference between a session and an interaction?"
Expected Keywords: session, interaction, uuid, timestamp

Response Analysis:
✅ Mentions session (container concept)
✅ Mentions interaction (individual item)
✅ Explains UUIDs for identification
✅ Notes timestamps for ordering

Score: 5/5 (Perfect)
```

---

### 2. Factualidad (Factuality)

**Definition**: Are claims accurate per official documentation?

**Sources of Truth**:
- `docs/PHILOSOPHY_CORPUS.md` (axioms)
- `docs/PHI_MAPPING.md` (philosophy → practice)
- `docs/policies/ERROR_BUDGETS.md` (SLO targets)
- `backend/*.py` (API implementation)
- `config/config.yml` (configuration)

**Scoring** (1-5):
- **5**: All claims verifiable, 100% accurate
- **4**: 1 minor inaccuracy (e.g., off-by-one)
- **3**: 2-3 factual errors
- **2**: Multiple errors, core concept wrong
- **1**: Hallucination, no basis in docs

**Verification Protocol**:
1. Extract all factual claims from response
2. Cross-reference each claim with source docs
3. Mark as ✅ (verified), ⚠️ (unverifiable), or ❌ (false)
4. Calculate accuracy percentage

**Example**:
```
Prompt: "What is the target p95 latency for Timeline API?"
Response: "The target p95 latency for Timeline API is <100ms (99th percentile)."

Fact-Check:
✅ p95 target <100ms (ERROR_BUDGETS.md line 24)
❌ "99th percentile" → Should be "95th percentile" (confusing p95 with p99)

Score: 4/5 (Minor inaccuracy)
```

---

### 3. p95 Latency

**Definition**: Time from prompt submission to full response completion (95th percentile).

**Target**: <2 seconds (Ingestion API SLO)

**Measurement**:
1. Send each prompt 20 times
2. Record latency for each run
3. Calculate p95 (95th percentile)
4. Compare against SLO

**Tooling**:
```bash
# Using curl + time
for i in {1..20}; do
  curl -X POST http://localhost:9001/api/ingest/interaction \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test_session", "content": "PROMPT_TEXT"}' \
    -w "%{time_total}\n" \
    -o /dev/null -s
done | sort -n | tail -1
```

**Pass Criteria**: p95 <2s for 90% of prompts

---

### 4. Cost (Token Usage)

**Definition**: Total tokens (input + output) per prompt category.

**Tracking**:
- Input tokens: prompt length
- Output tokens: response length
- Cost per token: model-dependent (e.g., Claude 3.5 Sonnet: $3/MTok input, $15/MTok output)

**Calculation**:
```python
def calculate_cost(prompt_tokens, completion_tokens, model="claude-3-5-sonnet"):
    rates = {
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},  # per 1K tokens
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    }

    input_cost = (prompt_tokens / 1000) * rates[model]["input"]
    output_cost = (completion_tokens / 1000) * rates[model]["output"]

    return input_cost + output_cost
```

**Budget**: $5 per full eval run (50 prompts × $0.10 avg)

---

## Evaluation Protocol

### Step 1: Prepare Environment

```bash
# Navigate to project root
cd ~/Documents/free-intelligence

# Start APIs
uvicorn backend.timeline_api:app --port 9002 &
uvicorn backend.verify_api:app --port 9003 &

# Ensure corpus.h5 exists
ls -lh storage/corpus.h5
```

---

### Step 2: Run Golden Set

**Manual Run** (for first iteration):
1. Open `eval/prompts.csv`
2. Send each prompt to LLM (via Claude Code or API)
3. Record response in `eval/results/run_001.jsonl`

**Format**:
```jsonl
{"prompt_id": "P001", "prompt": "...", "response": "...", "latency_ms": 1234, "input_tokens": 50, "output_tokens": 150, "timestamp": "2025-10-29T16:30:00Z"}
{"prompt_id": "P002", "prompt": "...", "response": "...", "latency_ms": 987, "input_tokens": 45, "output_tokens": 200, "timestamp": "2025-10-29T16:30:05Z"}
...
```

---

### Step 3: Score Responses

**Scoring Script** (Python):
```python
import csv
import json
from pathlib import Path

def score_response(prompt_id, response, expected_keywords):
    """
    Score adecuación (1-5) based on keyword presence.

    For factuality, manual review required (compare with docs).
    """
    keywords = [kw.strip() for kw in expected_keywords.split(',')]
    matches = sum(1 for kw in keywords if kw.lower() in response.lower())

    # Simple heuristic: keyword coverage → score
    if matches == len(keywords):
        return 5
    elif matches >= len(keywords) * 0.75:
        return 4
    elif matches >= len(keywords) * 0.5:
        return 3
    elif matches >= len(keywords) * 0.25:
        return 2
    else:
        return 1

# Load prompts
prompts = {}
with open('eval/prompts.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        prompts[row['prompt_id']] = row

# Load results
results = []
with open('eval/results/run_001.jsonl') as f:
    for line in f:
        results.append(json.loads(line))

# Score each result
scores = []
for result in results:
    prompt_id = result['prompt_id']
    prompt = prompts[prompt_id]

    adecuacion = score_response(
        prompt_id,
        result['response'],
        prompt['expected_keywords']
    )

    scores.append({
        'prompt_id': prompt_id,
        'category': prompt['category'],
        'adecuacion': adecuacion,
        'latency_ms': result['latency_ms'],
        'input_tokens': result['input_tokens'],
        'output_tokens': result['output_tokens'],
    })

# Aggregate by category
import pandas as pd
df = pd.DataFrame(scores)

print("=== Adecuación por Categoría ===")
print(df.groupby('category')['adecuacion'].mean())

print("\n=== p95 Latency por Categoría ===")
print(df.groupby('category')['latency_ms'].quantile(0.95))

print("\n=== Costo Estimado (Claude 3.5 Sonnet) ===")
df['cost'] = (df['input_tokens'] / 1000) * 0.003 + (df['output_tokens'] / 1000) * 0.015
print(f"Total: ${df['cost'].sum():.2f}")
```

---

### Step 4: Generate Report

**Report Template** (`eval/results/run_001_report.md`):
```markdown
# Evaluation Report - Run 001

**Date**: 2025-10-29
**Model**: claude-3-5-sonnet-20241022
**Prompts**: 50 (10 categories)
**Runner**: Manual via Claude Code

---

## Summary Metrics

| Metric | Value | Target | Pass? |
|--------|-------|--------|-------|
| Avg Adecuación | 4.2/5 | ≥4.0 | ✅ |
| Avg Factualidad | 4.5/5 | ≥4.0 | ✅ |
| p95 Latency | 1.8s | <2s | ✅ |
| Total Cost | $4.20 | <$5 | ✅ |

---

## By Category

| Category | Adecuación | Factualidad | p95 Latency | Cost |
|----------|-----------|------------|------------|------|
| technical_query | 4.4/5 | 4.8/5 | 1.2s | $0.60 |
| workflow | 4.6/5 | 4.6/5 | 1.5s | $0.75 |
| architecture | 4.0/5 | 4.2/5 | 2.1s | $1.10 |
| philosophy | 3.8/5 | 4.0/5 | 2.5s | $1.20 |
| troubleshooting | 4.2/5 | 4.4/5 | 1.8s | $0.55 |

---

## Failed Prompts (Score <3)

### P019: "What does 'Gnóstico/Alquimista = Tester OG' mean?"
**Adecuación**: 2/5
**Issue**: Response focused on historical alchemy, missed connection to testing/falsification.
**Action**: Update prompt to emphasize "testing" context.

### P048: "How does Free Intelligence handle very large sessions (1000+ interactions)?"
**Adecuación**: 2/5
**Issue**: No mention of pagination, chunking, or HDF5 optimization.
**Action**: Add scalability docs to architecture section.

---

## Recommendations

1. **Improve Philosophy Prompts**: Avg score 3.8/5. Consider adding examples to prompts.
2. **Optimize Hard Prompts**: p95 latency for hard prompts >2s. Use caching for repeated concepts.
3. **Document Scalability**: P048 revealed gap in large-session handling docs.
4. **Cost Optimization**: Philosophy prompts cost 2× avg. Consider Haiku for non-critical queries.

---

## Next Run

**Target**: 2025-11-05 (1 week)
**Changes**:
- Update P019, P048 prompts
- Add scalability docs
- Re-run with Claude 3 Haiku for cost comparison
```

---

## Automation (Future Sprint)

**Goal**: Automate evaluation runs for CI/CD

**Tools**:
- **LangSmith**: LLM evaluation platform
- **LangChain**: Prompt chaining + evaluation
- **pytest**: Test runner integration

**Example Test**:
```python
import pytest
from langchain.evaluation import load_evaluator

@pytest.mark.parametrize("prompt_id", [f"P{i:03d}" for i in range(1, 51)])
def test_golden_set(prompt_id, golden_set):
    prompt = golden_set[prompt_id]

    # Send to LLM
    response = llm_client.send(prompt['prompt'])

    # Evaluate adecuación
    evaluator = load_evaluator("qa", llm=claude)
    result = evaluator.evaluate_strings(
        prediction=response,
        input=prompt['prompt'],
        reference=prompt['expected_keywords']
    )

    assert result['score'] >= 3, f"Low adecuación for {prompt_id}"
```

---

## References

- **Axioma**: `docs/PHILOSOPHY_CORPUS.md` (Gnóstico = Tester OG)
- **Mapping**: `docs/PHI_MAPPING.md` (Axiom 4 → Golden Sets)
- **SLO Targets**: `docs/policies/ERROR_BUDGETS.md`
- **LangSmith Docs**: https://docs.smith.langchain.com/evaluation

---

_"Sin golden set, no hay gnosis. Sin falsificación, no hay verdad."_
