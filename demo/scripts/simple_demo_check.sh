#!/bin/bash
# Simple Demo Check - Validar que sistema funciona para demo
# No carga datos, solo verifica que servicios corren

set -e

echo "==============================================="
echo "FI-Entry Demo - System Check"
echo "==============================================="
echo ""

# Check 1: Backend running
echo "✓ Checking backend (port 7001)..."
if lsof -ti:7001 > /dev/null 2>&1; then
    echo "  ✅ Backend is running"

    # Test health endpoint
    HEALTH=$(curl -s http://localhost:7001/health 2>&1 || echo "error")
    if echo "$HEALTH" | grep -q "ok"; then
        echo "  ✅ Health endpoint OK"
    else
        echo "  ⚠️  Health endpoint not responding"
    fi
else
    echo "  ❌ Backend NOT running"
    echo "     Run: pnpm backend:dev"
    exit 1
fi

echo ""

# Check 2: Frontend running
echo "✓ Checking frontend (port 9000)..."
if lsof -ti:9000 > /dev/null 2>&1; then
    echo "  ✅ Frontend is running"
else
    echo "  ❌ Frontend NOT running"
    echo "     Run: pnpm frontend:dev"
    exit 1
fi

echo ""

# Check 3: Sessions API
echo "✓ Checking Sessions API..."
SESSIONS=$(curl -s "http://localhost:7001/api/sessions?limit=5" 2>&1 || echo "error")
if echo "$SESSIONS" | grep -q "\["; then
    COUNT=$(echo "$SESSIONS" | grep -o '"id"' | wc -l | tr -d ' ')
    echo "  ✅ Sessions API OK ($COUNT sessions found)"

    if [ "$COUNT" -eq 0 ]; then
        echo "  ⚠️  No sessions in database (demo will be empty)"
        echo "     Workaround: Show YAML files directly"
    fi
else
    echo "  ⚠️  Sessions API error"
fi

echo ""

# Check 4: Demo files
echo "✓ Checking demo files..."
if [ -f "demo/consultas/consulta_001.yaml" ]; then
    echo "  ✅ Consulta 001 (Hipertensión) found"
else
    echo "  ❌ Consulta 001 not found"
fi

if [ -f "demo/consultas/consulta_002.yaml" ]; then
    echo "  ✅ Consulta 002 (Diabetes) found"
else
    echo "  ❌ Consulta 002 not found"
fi

if [ -f "demo/consultas/consulta_003.yaml" ]; then
    echo "  ✅ Consulta 003 (Infección) found"
else
    echo "  ❌ Consulta 003 not found"
fi

echo ""

# Check 5: Sales materials
echo "✓ Checking sales materials..."
if [ -f "sales/entry/loi_template.yaml" ]; then
    echo "  ✅ LOI template found"
else
    echo "  ❌ LOI template not found"
fi

if [ -f "sales/entry/pricing.yaml" ]; then
    echo "  ✅ Pricing found"
else
    echo "  ❌ Pricing not found"
fi

echo ""
echo "==============================================="
echo "Demo Readiness Check"
echo "==============================================="

# Summary
if lsof -ti:7001 > /dev/null 2>&1 && lsof -ti:9000 > /dev/null 2>&1; then
    echo "✅ READY FOR DEMO"
    echo ""
    echo "Next steps:"
    echo "  1. Open browser: http://localhost:9000/dashboard"
    echo "  2. Open sessions: http://localhost:9000/sessions"
    echo "  3. Follow demo script: demo/DEMO_SCRIPT.md"
    echo ""
    echo "Backup plan (if no data in sessions):"
    echo "  - Show demo/consultas/*.yaml files directly"
    echo "  - Explain: 'This is how data looks when transcribed'"
else
    echo "❌ NOT READY"
    echo ""
    echo "Fix:"
    echo "  pnpm dev  # Start all services"
fi

echo ""
