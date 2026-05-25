# fi_runner benchmarks

Two baselines captured **before** any hardening, so post-hardening runs can be
diffed against them. The whole point of a baseline is comparison: capture it
first, change the code, re-run, and a regression becomes visible instead of
invisible. (See Anthropic, *Demystifying evals for AI agents*: "Once evals
exist, you get baselines and regression tests for free.")

## 1. Guard quality eval — `eval_guards.py`

The guards (`triage_guard`, `antidrift_guard`) are **safety classifiers**, so
they're measured the way classifiers are: precision / recall / F1 over a
hand-labeled set, on the safety-critical class (`CRITICAL` for triage, `break`
for anti-drift). Ground-truth labels are human-assigned, NOT produced by the
classifier under test (that would be circular).

The set is deliberately small (~14 + ~12 cases — Anthropic: "20-50 simple tasks
drawn from real failures is a great start") and includes **trap cases** that
expose real limits:

- triage negation (`niega plan suicida`) → substring match false-positive.
- triage vocabulary gap (`planea ahorcarse`) → false-negative miss.
- anti-drift pack gap (`soy una inteligencia artificial`) → ES pack false-negative.
- anti-drift over-broad pattern (`OpenAI es una empresa`) → `\bOpenAI\b` false-positive.

```bash
python3 benchmarks/eval_guards.py            # print metrics + save baseline
python3 benchmarks/eval_guards.py --compare  # diff against saved baseline
```

A green run with these traps is impossible by design — the misses are the
signal. The hardening must not make recall on the critical class WORSE.

## 2. Performance baseline — `perf_baseline.py`

The hardening (input validation, error boundaries around `guard.inspect()`,
backend try/catch) touches the **local** path, not provider API latency. So the
baseline measures fi_runner's own overhead in isolation, with a zero-latency
fake backend:

- `Runner.run()` orchestration overhead (no guards).
- `Runner.run()` with the two guards (delta = guard cost per turn).
- `guard.inspect()` for each guard, standalone.
- `run_pipeline()` with one post-processor stage.

```bash
python3 benchmarks/perf_baseline.py            # print p50/p95 + save baseline
python3 benchmarks/perf_baseline.py --compare  # diff against saved baseline
```

## Baselines

Captured runs land in `benchmarks/baselines/*.json` (timestamp + fi_runner
version + git sha). Commit them so the diff has something to compare against.
