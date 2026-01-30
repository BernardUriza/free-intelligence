#!/bin/bash
# Integration test for RAG Quality Metrics
# Tests annotation generation and evaluation endpoints

set -e

echo "=== RAG Quality Metrics Integration Test ==="
echo ""

API_KEY="change-me-in-production"
BASE_URL="http://localhost:11435"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Prerequisites:${NC}"
echo "  1. Ollama running: ollama serve"
echo "  2. RAG service running: python main.py"
echo "  3. Sample PDF uploaded (use TestSuiteLibrary UI)"
echo ""

# Check if RAG service is running
if ! curl -s "$BASE_URL/rag/health" > /dev/null; then
    echo -e "${RED}❌ RAG service not running on port 11435${NC}"
    echo "Start it with: python main.py"
    exit 1
fi

echo -e "${GREEN}✅ RAG service is running${NC}"
echo ""

# Test filename (adjust based on what you uploaded)
FILENAME="diabetes.pdf"

echo -e "${BLUE}Test 1: Generate Annotations${NC}"
echo "Generating 2 questions per chunk using Ollama llama3.1:8b..."

RESPONSE=$(curl -s -X POST "$BASE_URL/rag/generate_annotations" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"$FILENAME\",\"questions_per_chunk\":2}")

if echo "$RESPONSE" | jq -e '.status == "success"' > /dev/null 2>&1; then
    ANNOTATIONS_COUNT=$(echo "$RESPONSE" | jq -r '.annotations_count')
    CHUNKS_PROCESSED=$(echo "$RESPONSE" | jq -r '.chunks_processed')
    TIME_MS=$(echo "$RESPONSE" | jq -r '.estimated_time_ms')

    echo -e "${GREEN}✅ Annotations generated${NC}"
    echo "  • Annotations: $ANNOTATIONS_COUNT"
    echo "  • Chunks processed: $CHUNKS_PROCESSED"
    echo "  • Time: ${TIME_MS}ms"
else
    echo -e "${RED}❌ Annotation generation failed${NC}"
    echo "$RESPONSE" | jq .
    exit 1
fi
echo ""

echo -e "${BLUE}Test 2: Get Annotations${NC}"

RESPONSE=$(curl -s -X GET "$BASE_URL/rag/annotations/$FILENAME" \
  -H "X-API-Key: $API_KEY")

if echo "$RESPONSE" | jq -e '.count > 0' > /dev/null 2>&1; then
    COUNT=$(echo "$RESPONSE" | jq -r '.count')
    FIRST_QUERY=$(echo "$RESPONSE" | jq -r '.annotations[0].query')

    echo -e "${GREEN}✅ Annotations retrieved${NC}"
    echo "  • Total: $COUNT"
    echo "  • First query: \"$FIRST_QUERY\""
else
    echo -e "${RED}❌ Failed to retrieve annotations${NC}"
    echo "$RESPONSE" | jq .
    exit 1
fi
echo ""

echo -e "${BLUE}Test 3: Evaluate Single Query${NC}"

RESPONSE=$(curl -s -X POST "$BASE_URL/rag/evaluate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"$FIRST_QUERY\",\"filename\":\"$FILENAME\",\"top_k\":3}")

if echo "$RESPONSE" | jq -e '.metrics' > /dev/null 2>&1; then
    RECALL=$(echo "$RESPONSE" | jq -r '.metrics["recall@3"]')
    PRECISION=$(echo "$RESPONSE" | jq -r '.metrics["precision@3"]')
    MRR=$(echo "$RESPONSE" | jq -r '.metrics.mrr')
    NDCG=$(echo "$RESPONSE" | jq -r '.metrics["ndcg@3"]')

    echo -e "${GREEN}✅ Query evaluated${NC}"
    echo "  • Recall@3:    $(printf "%.1f%%" $(echo "$RECALL * 100" | bc))"
    echo "  • Precision@3: $(printf "%.1f%%" $(echo "$PRECISION * 100" | bc))"
    echo "  • MRR:         $(printf "%.1f%%" $(echo "$MRR * 100" | bc))"
    echo "  • NDCG@3:      $(printf "%.1f%%" $(echo "$NDCG * 100" | bc))"
else
    echo -e "${RED}❌ Evaluation failed${NC}"
    echo "$RESPONSE" | jq .
    exit 1
fi
echo ""

echo -e "${BLUE}Test 4: Batch Evaluate All Queries${NC}"

RESPONSE=$(curl -s -X POST "$BASE_URL/rag/batch_evaluate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"$FILENAME\",\"top_k\":3}")

if echo "$RESPONSE" | jq -e '.avg_metrics' > /dev/null 2>&1; then
    TOTAL_QUERIES=$(echo "$RESPONSE" | jq -r '.total_queries')
    AVG_RECALL=$(echo "$RESPONSE" | jq -r '.avg_metrics["recall@3"]')
    AVG_PRECISION=$(echo "$RESPONSE" | jq -r '.avg_metrics["precision@3"]')
    AVG_MRR=$(echo "$RESPONSE" | jq -r '.avg_metrics.mrr')
    AVG_NDCG=$(echo "$RESPONSE" | jq -r '.avg_metrics["ndcg@3"]')

    echo -e "${GREEN}✅ Batch evaluation complete${NC}"
    echo "  • Total queries: $TOTAL_QUERIES"
    echo "  • Avg Recall@3:    $(printf "%.1f%%" $(echo "$AVG_RECALL * 100" | bc))"
    echo "  • Avg Precision@3: $(printf "%.1f%%" $(echo "$AVG_PRECISION * 100" | bc))"
    echo "  • Avg MRR:         $(printf "%.1f%%" $(echo "$AVG_MRR * 100" | bc))"
    echo "  • Avg NDCG@3:      $(printf "%.1f%%" $(echo "$AVG_NDCG * 100" | bc))"

    # Quality gates
    echo ""
    echo -e "${BLUE}Quality Gates:${NC}"

    if (( $(echo "$AVG_RECALL >= 0.75" | bc -l) )); then
        echo -e "  ${GREEN}✅ Recall@3 ≥ 75% (PASS)${NC}"
    else
        echo -e "  ${RED}❌ Recall@3 < 75% (FAIL - improve chunking)${NC}"
    fi

    if (( $(echo "$AVG_PRECISION >= 0.70" | bc -l) )); then
        echo -e "  ${GREEN}✅ Precision@3 ≥ 70% (PASS)${NC}"
    else
        echo -e "  ${RED}❌ Precision@3 < 70% (FAIL - too much noise)${NC}"
    fi

    if (( $(echo "$AVG_MRR >= 0.70" | bc -l) )); then
        echo -e "  ${GREEN}✅ MRR ≥ 70% (PASS)${NC}"
    else
        echo -e "  ${RED}❌ MRR < 70% (FAIL - first result not relevant)${NC}"
    fi

    if (( $(echo "$AVG_NDCG >= 0.80" | bc -l) )); then
        echo -e "  ${GREEN}✅ NDCG@3 ≥ 80% (PASS)${NC}"
    else
        echo -e "  ${RED}❌ NDCG@3 < 80% (FAIL - poor ranking)${NC}"
    fi
else
    echo -e "${RED}❌ Batch evaluation failed${NC}"
    echo "$RESPONSE" | jq .
    exit 1
fi

echo ""
echo -e "${GREEN}=== All tests passed! ===${NC}"
