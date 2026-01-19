# Test script para verificar instalación de Python post-Aurity install
$ErrorActionPreference = "Stop"

Write-Host "=== Testing Python 3.14 Installation ===" -ForegroundColor Cyan

# Test 1: Python executable exists
Write-Host "`n[1/5] Checking python.exe in PATH..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.14") {
        Write-Host "✅ PASS: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ FAIL: Expected 3.14, got $pythonVersion" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ FAIL: python.exe not found in PATH" -ForegroundColor Red
    exit 1
}

# Test 2: Pip available
Write-Host "`n[2/5] Checking pip availability..." -ForegroundColor Yellow
try {
    $pipVersion = python -m pip --version 2>&1
    Write-Host "✅ PASS: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ FAIL: pip not available" -ForegroundColor Red
    exit 1
}

# Test 3: FastAPI installed
Write-Host "`n[3/5] Checking fastapi..." -ForegroundColor Yellow
python -c "import fastapi; print(f'fastapi {fastapi.__version__}')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PASS" -ForegroundColor Green
} else {
    Write-Host "❌ FAIL: fastapi not installed" -ForegroundColor Red
    exit 1
}

# Test 4: Uvicorn installed
Write-Host "`n[4/5] Checking uvicorn..." -ForegroundColor Yellow
python -c "import uvicorn; print(f'uvicorn {uvicorn.__version__}')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PASS" -ForegroundColor Green
} else {
    Write-Host "❌ FAIL: uvicorn not installed" -ForegroundColor Red
    exit 1
}

# Test 5: Sentence-transformers installed
Write-Host "`n[5/5] Checking sentence-transformers..." -ForegroundColor Yellow
python -c "import sentence_transformers; print(f'sentence-transformers {sentence_transformers.__version__}')"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PASS" -ForegroundColor Green
} else {
    Write-Host "❌ FAIL: sentence-transformers not installed" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== All Tests Passed ===" -ForegroundColor Green
