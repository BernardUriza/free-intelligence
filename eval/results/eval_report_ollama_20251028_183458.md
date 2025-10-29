# Free Intelligence - Evaluation Report

**Generated**: 2025-10-28 18:34:58
**Provider**: ollama
**Model**: qwen2.5:7b-instruct-q4_0
**Pass Threshold**: 70.0
**Total Cases**: 55

## 📊 Summary

- **Pass Rate**: 30/55 (54.5%)
- **Mean Score**: 57.6
- **Median Score**: 80.2

## ⏱️  Latency

- **p50**: 24470ms
- **p95**: 193749ms
- **p99**: 303814ms
- **Mean**: 44106ms
- **Min**: 8307ms
- **Max**: 315022ms

## 📂 Results by Category

### GREEN (30 cases)
- Pass Rate: 19/30 (63.3%)
- Mean Score: 70.7

### YELLOW (10 cases)
- Pass Rate: 5/10 (50.0%)
- Mean Score: 43.7

### EDGE (15 cases)
- Pass Rate: 6/15 (40.0%)
- Mean Score: 40.6

## ❌ Failures

25 cases failed:

- **Case 6** (green/easy): score=0.0
  - Error: BLOCKER: Widow-maker detected (aortic_dissection) but urgency=LOW
- **Case 11** (green/easy): score=66.8
- **Case 12** (green/easy): score=66.5
- **Case 14** (green/easy): score=0.0
  - Error: BLOCKER: Widow-maker detected (pulmonary_embolism) but urgency=MODERATE
- **Case 15** (green/easy): score=64.5
- **Case 18** (green/easy): score=60.5
- **Case 21** (green/easy): score=44.9
- **Case 23** (green/easy): score=0.0
  - Error: BLOCKER: Widow-maker detected (aortic_dissection) but urgency=LOW
- **Case 27** (green/easy): score=66.9
- **Case 28** (green/easy): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 29** (green/easy): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 32** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 33** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 35** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 36** (yellow/medium): score=0.0
  - Error: BLOCKER: Widow-maker detected (stroke) but urgency=HIGH
- **Case 39** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 42** (edge/hard): score=53.8
- **Case 44** (edge/hard): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 46** (edge/hard): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 47** (edge/hard): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 49** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → MODERATE is unsafe downgrade
- **Case 50** (edge/hard): score=48.8
- **Case 51** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 53** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 54** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → MODERATE is unsafe downgrade

## 💰 Cost

- **Total Cost**: $0.000000
- **Total Tokens**: 23,956