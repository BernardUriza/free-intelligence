#!/bin/bash
# Quick Test - Free Intelligence
# Ejecuta los tests más importantes en un solo comando

set -e  # Exit on error

echo "🚀 FREE INTELLIGENCE - QUICK TEST"
echo "=================================="
echo ""

# Test 1: Unit Tests
echo "📝 Test 1/6: Running unit tests..."
python3 -m unittest discover tests/ -v 2>&1 | tail -5
echo ""

# Test 2: Generate Test Data
echo "📝 Test 2/6: Generating test data..."
python3 scripts/generate_test_data.py 2>&1 | grep -E "(Interactions added|Embeddings added|completed)"
echo ""

# Test 3: Mutation Validator
echo "📝 Test 3/6: Validating no-mutation policy..."
python3 backend/mutation_validator.py 2>&1 | grep -E "(PASSED|FAILED)"
echo ""

# Test 4: LLM Audit Policy
echo "📝 Test 4/6: Validating LLM audit policy..."
python3 backend/llm_audit_policy.py validate backend/ 2>&1 | grep -E "(PASSED|FAILED)"
echo ""

# Test 5: LLM Router Policy
echo "📝 Test 5/6: Validating LLM router policy..."
python3 backend/llm_router_policy.py validate backend/ 2>&1 | grep -E "(PASSED|FAILED)"
echo ""

# Test 6: Corpus Stats
echo "📝 Test 6/6: Checking corpus stats..."
python3 -c "
from backend.corpus_ops import get_corpus_stats
stats = get_corpus_stats('storage/corpus.h5')
print(f'   Interactions: {stats[\"interactions_count\"]}')
print(f'   Embeddings: {stats[\"embeddings_count\"]}')
print(f'   File size: {stats[\"file_size_mb\"]:.2f} MB')
"
echo ""

echo "=================================="
echo "✅ All quick tests completed!"
echo ""
echo "Full test suite: python3 -m unittest discover tests/"
echo "Manual testing: See MANUAL_TESTING_GUIDE.md"
