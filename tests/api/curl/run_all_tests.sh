#!/bin/bash

# run_all_tests.sh - Suite completa de tests API
# Ejecuta todos los tests en orden y reporta resultados

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
PASSED=0
FAILED=0
TOTAL=0

# Función para ejecutar test
run_test() {
  local test_name="$1"
  local test_script="$2"
  local test_args="${3:-}"

  TOTAL=$((TOTAL + 1))

  echo -e "${YELLOW}[$TOTAL] Ejecutando: $test_name${NC}"

  if [ -n "$test_args" ]; then
    if ./$test_script $test_args > /tmp/test_output.log 2>&1; then
      PASSED=$((PASSED + 1))
      echo -e "${GREEN}    ✓ Pasó${NC}"
    else
      FAILED=$((FAILED + 1))
      echo -e "${RED}    ✗ Falló${NC}"
      echo "    Ver detalles: /tmp/test_output.log"
    fi
  else
    if ./$test_script > /tmp/test_output.log 2>&1; then
      PASSED=$((PASSED + 1))
      echo -e "${GREEN}    ✓ Pasó${NC}"
    else
      FAILED=$((FAILED + 1))
      echo -e "${RED}    ✗ Falló${NC}"
      echo "    Ver detalles: /tmp/test_output.log"
    fi
  fi

  sleep 1
}

# Header
echo "========================================"
echo "  AURITY API Test Suite"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# Cargar variables de entorno
if [ -f .env.test ]; then
  echo "📝 Cargando configuración (.env.test)..."
  source .env.test
  echo ""
else
  echo "⚠️  Advertencia: .env.test no encontrado"
  echo "   Usando valores por defecto"
  echo ""
fi

# Verificar que AUTH_TOKEN existe
if [ -z "$AUTH_TOKEN" ]; then
  echo -e "${RED}❌ Error: AUTH_TOKEN no configurado${NC}"
  echo "   Exporta tu token: export AUTH_TOKEN='eyJhbGci...'"
  exit 1
fi

START_TIME=$(date +%s)

# ===================================
# TESTS DE SESIONES
# ===================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 GESTIÓN DE SESIONES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

run_test "Crear sesión" "01_create_session.sh"

# Obtener session_id creado
if [ -f .last_session_id ]; then
  SESSION_ID=$(cat .last_session_id)
  echo "   Session ID: $SESSION_ID"
else
  echo -e "${RED}   ✗ No se pudo obtener session_id${NC}"
  exit 1
fi

run_test "Listar sesiones" "02_list_sessions.sh"
run_test "Obtener sesión" "03_get_session.sh" "$SESSION_ID"

echo ""

# ===================================
# TESTS DE AUDIO
# ===================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎤 AUDIO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Nota: Estos tests requieren archivos de audio reales
# Se pueden omitir si no existen los fixtures

if [ -f "./fixtures/audio/sample.wav" ]; then
  run_test "Upload audio completo" "04_upload_audio.sh" "$SESSION_ID ./fixtures/audio/sample.wav"
else
  echo -e "${YELLOW}[SKIP] Upload audio (fixture no encontrado)${NC}"
fi

if [ -f "./fixtures/audio/chunk_001.wav" ]; then
  run_test "Stream audio chunk" "05_stream_audio_chunk.sh" "$SESSION_ID ./fixtures/audio/chunk_001.wav 0"
else
  echo -e "${YELLOW}[SKIP] Stream chunk (fixture no encontrado)${NC}"
fi

echo ""

# ===================================
# TESTS DE PROCESAMIENTO
# ===================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  PROCESAMIENTO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

run_test "Iniciar transcripción" "06_start_transcription.sh" "$SESSION_ID"

# Esperar un poco para que procese
echo "   ⏳ Esperando procesamiento (5s)..."
sleep 5

echo ""

# ===================================
# TESTS DE MONITOREO
# ===================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 MONITOREO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

run_test "Estado de sesión" "13_session_status.sh" "$SESSION_ID"
run_test "Health check" "14_health_check.sh"

echo ""

# ===================================
# RESULTADOS FINALES
# ===================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "========================================"
echo "  RESULTADOS"
echo "========================================"
echo ""
echo -e "Total:    $TOTAL tests"
echo -e "${GREEN}Pasados:  $PASSED${NC}"

if [ $FAILED -gt 0 ]; then
  echo -e "${RED}Fallados: $FAILED${NC}"
else
  echo -e "Fallados: $FAILED"
fi

echo ""
echo "Duración: ${DURATION}s"
echo ""

# Calcular porcentaje
if [ $TOTAL -gt 0 ]; then
  PERCENTAGE=$((PASSED * 100 / TOTAL))
  echo "Tasa de éxito: $PERCENTAGE%"
fi

echo "========================================"

# Exit code basado en resultados
if [ $FAILED -gt 0 ]; then
  exit 1
else
  exit 0
fi
