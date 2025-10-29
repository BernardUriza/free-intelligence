# Free Intelligence - Evaluation Report

**Generated**: 2025-10-28 13:36:59
**Provider**: ollama
**Model**: qwen2.5:7b-instruct-q4_0
**Pass Threshold**: 70.0
**Total Cases**: 55

## 📊 Summary

- **Pass Rate**: 33/55 (60.0%)
- **Mean Score**: 61.6
- **Median Score**: 82.8

## ⏱️  Latency

- **p50**: 13018ms
- **p95**: 26382ms
- **p99**: 42903ms
- **Mean**: 15896ms
- **Min**: 9185ms
- **Max**: 43902ms

## 📂 Results by Category

### GREEN (30 cases)
- Pass Rate: 21/30 (70.0%)
- Mean Score: 77.1

### YELLOW (10 cases)
- Pass Rate: 5/10 (50.0%)
- Mean Score: 44.2

### EDGE (15 cases)
- Pass Rate: 7/15 (46.7%)
- Mean Score: 42.4

## ❌ Failures

22 cases failed:

- **Case 7** (green/easy): score=0.0
  - Error: SCHEMA_VALIDATION_FAILED: None is not of type 'array'
- **Case 11** (green/easy): score=66.8
- **Case 12** (green/easy): score=66.5
- **Case 15** (green/easy): score=64.5
- **Case 21** (green/easy): score=44.9
- **Case 23** (green/easy): score=56.2
- **Case 27** (green/easy): score=66.9
- **Case 28** (green/easy): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 29** (green/easy): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 31** (yellow/medium): score=0.0
  - Error: 'NoneType' object has no attribute 'lower'
- **Case 32** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 33** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → MODERATE is unsafe downgrade
- **Case 35** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 39** (yellow/medium): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 44** (edge/hard): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 45** (edge/hard): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 46** (edge/hard): score=0.0
  - Error: BLOCKER: HIGH → MODERATE is unsafe downgrade
- **Case 49** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → MODERATE is unsafe downgrade
- **Case 50** (edge/hard): score=48.8
- **Case 51** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 53** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade
- **Case 54** (edge/hard): score=0.0
  - Error: BLOCKER: CRITICAL → HIGH is unsafe downgrade

## 💰 Cost

- **Total Cost**: $0.000000
- **Total Tokens**: 23,506