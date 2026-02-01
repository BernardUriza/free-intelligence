#!/bin/bash
# Verification script for RAG Testing Tool setup

echo "=========================================="
echo "RAG Testing Tool - Setup Verification"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check files exist
echo "1. Checking files..."

files=(
    "test_rag_ui.py"
    "requirements-dev.txt"
    "README-testing.md"
    "test_data/sample_medical_note.txt"
    "test_data/convert_to_pdf.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✅${NC} $file"
    else
        echo -e "   ${RED}❌${NC} $file (MISSING)"
    fi
done

echo ""

# Check Python syntax
echo "2. Checking Python syntax..."
if python3.14 -m py_compile test_rag_ui.py 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} test_rag_ui.py compiles"
else
    echo -e "   ${RED}❌${NC} test_rag_ui.py has syntax errors"
fi

if python3.14 -m py_compile test_data/convert_to_pdf.py 2>/dev/null; then
    echo -e "   ${GREEN}✅${NC} convert_to_pdf.py compiles"
else
    echo -e "   ${RED}❌${NC} convert_to_pdf.py has syntax errors"
fi

echo ""

# Check dependencies installable
echo "3. Checking dependencies..."
echo -e "   ${YELLOW}ℹ${NC}  To install: pip install -r requirements-dev.txt"
echo ""

# Check sample text file content
echo "4. Checking sample medical note..."
if grep -q "NOTA MÉDICA" test_data/sample_medical_note.txt; then
    echo -e "   ${GREEN}✅${NC} Sample medical note has content"
else
    echo -e "   ${RED}❌${NC} Sample medical note appears empty"
fi

echo ""

# Check environment variables
echo "5. Checking environment variables..."
RAG_SERVICE_URL=${RAG_SERVICE_URL:-"http://localhost:11435"}
RAG_API_KEY=${RAG_API_KEY:-"test-api-key-12345"}

echo "   RAG_SERVICE_URL: $RAG_SERVICE_URL"
echo "   RAG_API_KEY: ${RAG_API_KEY:0:10}..."

echo ""

# Final summary
echo "=========================================="
echo "Setup Verification Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements-dev.txt"
echo "2. (Optional) Create PDF: cd test_data && python convert_to_pdf.py"
echo "3. Start RAG Service: cd rag_service && python -m uvicorn main:app --port 11435"
echo "4. Launch UI: python test_rag_ui.py"
echo "5. Open browser: http://localhost:7860"
echo ""
