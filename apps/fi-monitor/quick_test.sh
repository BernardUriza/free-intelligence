#!/bin/bash
# Quick verification script for RAG Testing Tool setup

set -e

echo "🔍 RAG Testing Tool - Quick Verification"
echo "========================================"
echo ""

# Check Python version
echo "1. Checking Python version..."
python3.14 --version || { echo "❌ Python 3.14 not found"; exit 1; }
echo "✅ Python 3.14 installed"
echo ""

# Check files exist
echo "2. Checking required files..."
files=(
    "test_rag_ui.py"
    "requirements-dev.txt"
    "README-testing.md"
    "test_data/sample_medical_note.txt"
    "test_data/convert_to_pdf.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file MISSING"
        exit 1
    fi
done
echo ""

# Check syntax
echo "3. Validating Python syntax..."
python3.14 -m py_compile test_rag_ui.py && echo "  ✅ test_rag_ui.py"
python3.14 -m py_compile test_data/convert_to_pdf.py && echo "  ✅ convert_to_pdf.py"
echo ""

# Check dependencies
echo "4. Checking dependencies (will fail if not installed)..."
if python3.14 -c "import gradio" 2>/dev/null; then
    echo "  ✅ gradio installed"
else
    echo "  ⚠️  gradio NOT installed (run: pip install -r requirements-dev.txt)"
fi

if python3.14 -c "import PyPDF2" 2>/dev/null; then
    echo "  ✅ PyPDF2 installed"
else
    echo "  ⚠️  PyPDF2 NOT installed (run: pip install -r requirements-dev.txt)"
fi
echo ""

# Check RAG Service
echo "5. Checking RAG Service availability..."
if curl -s http://localhost:11435/rag/health > /dev/null 2>&1; then
    echo "  ✅ RAG Service running on port 11435"
else
    echo "  ⚠️  RAG Service NOT running (start with: python -m rag_service.main)"
fi
echo ""

# Summary
echo "========================================"
echo "✅ Setup verification complete!"
echo ""
echo "Next steps:"
echo "  1. Install dependencies: pip install -r requirements-dev.txt"
echo "  2. Start RAG Service: python -m rag_service.main"
echo "  3. Launch UI: python test_rag_ui.py"
echo "  4. Open browser: http://localhost:7860"
echo ""
