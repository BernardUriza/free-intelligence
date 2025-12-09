#!/bin/bash
# run_all_tests.sh - Ejecutar todos los tests en secuencia
# Autor: Bernard Uriza Orozco

set -e

# Cargar configuración
if [ ! -f .env.curl ]; then
  echo "❌ Archivo .env.curl no encontrado"
  echo ""
  echo "Ejecuta primero la configuración:"
  echo "  ./setup.sh"
  echo ""
  exit 1
fi

source .env.curl

echo "🧪 AURITY - Suite Completa de Tests"
echo "===================================="
echo ""
echo "Backend: $BACKEND_URL"
echo "Token: ${AUTH_TOKEN:0:20}..."
echo ""

# Verificar conectividad
echo "🔍 Verificando conectividad..."
if curl -s -f "$BACKEND_URL/health" > /dev/null; then
  echo "✅ Backend disponible"
else
  echo "❌ Backend no disponible en $BACKEND_URL"
  exit 1
fi

echo ""
echo "===================================="
echo ""

# Menu de tests
echo "Selecciona tests a ejecutar:"
echo ""
echo "  1) Test Sesión Médica (E2E)"
echo "  2) Test Check-in Receptionist"
echo "  3) Test Modo Chat"
echo "  4) Verificar Integridad HDF5"
echo "  5) Todos los tests (1-4)"
echo "  6) Test Médico + Verificación (1+4)"
echo ""
read -p "Opción (1-6): " TEST_CHOICE

echo ""
echo "===================================="
echo ""

run_test() {
  local test_name="$1"
  local test_script="$2"

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🚀 Ejecutando: $test_name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  if [ -f "$test_script" ]; then
    bash "$test_script"
  else
    echo "❌ Script no encontrado: $test_script"
    return 1
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "✅ Completado: $test_name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Pausa entre tests
  if [ "$TEST_CHOICE" = "5" ] || [ "$TEST_CHOICE" = "6" ]; then
    echo "⏳ Esperando 3 segundos antes del siguiente test..."
    sleep 3
  fi
}

case $TEST_CHOICE in
  1)
    run_test "Sesión Médica E2E" "./test_medical_session.sh"
    ;;

  2)
    run_test "Check-in Receptionist" "./test_checkin.sh"
    ;;

  3)
    run_test "Modo Chat" "./test_chat_mode.sh"
    ;;

  4)
    run_test "Verificación Integridad HDF5" "./verify_h5_integrity.sh"
    ;;

  5)
    # Todos los tests
    run_test "Sesión Médica E2E" "./test_medical_session.sh"
    run_test "Check-in Receptionist" "./test_checkin.sh"
    run_test "Modo Chat" "./test_chat_mode.sh"
    run_test "Verificación Integridad HDF5" "./verify_h5_integrity.sh"
    ;;

  6)
    # Médico + Verificación
    run_test "Sesión Médica E2E" "./test_medical_session.sh"
    run_test "Verificación Integridad HDF5" "./verify_h5_integrity.sh"
    ;;

  *)
    echo "❌ Opción inválida: $TEST_CHOICE"
    exit 1
    ;;
esac

echo ""
echo "===================================="
echo "🎉 Suite de tests completada"
echo "===================================="
echo ""

# Mostrar resumen
echo "📊 Resumen de Ejecución"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

case $TEST_CHOICE in
  1)
    echo "✅ Test Sesión Médica - Completado"
    echo ""
    echo "Qué se probó:"
    echo "  • Upload de chunks de audio"
    echo "  • Transcripción con Deepgram"
    echo "  • Diarización (identificación de speakers)"
    echo "  • Generación de nota SOAP"
    echo "  • Timeline y audit log"
    ;;

  2)
    echo "✅ Test Check-in - Completado"
    echo ""
    echo "Qué se probó:"
    echo "  • Generación de QR codes"
    echo "  • Identificación de pacientes"
    echo "  • Acciones pendientes (formularios)"
    echo "  • Sala de espera en tiempo real"
    ;;

  3)
    echo "✅ Test Modo Chat - Completado"
    echo ""
    echo "Qué se probó:"
    echo "  • Transcripción síncrona (sin polling)"
    echo "  • Comparación chat vs medical mode"
    echo "  • Performance de ambos modos"
    ;;

  4)
    echo "✅ Verificación Integridad - Completada"
    echo ""
    echo "Qué se probó:"
    echo "  • Checksums SHA256"
    echo "  • Event sourcing (versioning)"
    echo "  • Append-only pattern"
    echo "  • Inmutabilidad de datos"
    ;;

  5)
    echo "✅ Todos los tests - Completados"
    echo ""
    echo "Coverage completo:"
    echo "  • Sesiones médicas E2E"
    echo "  • Check-in receptionist"
    echo "  • Modo chat"
    echo "  • Integridad de datos"
    ;;

  6)
    echo "✅ Tests Médicos + Verificación - Completados"
    echo ""
    echo "Coverage:"
    echo "  • Sesión médica completa"
    echo "  • Verificación de integridad post-test"
    ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Sugerencias
echo "💡 Próximos pasos:"
echo ""

if [ "$TEST_CHOICE" = "1" ] || [ "$TEST_CHOICE" = "5" ] || [ "$TEST_CHOICE" = "6" ]; then
  echo "Ver sesiones creadas:"
  echo "  curl -X GET '$BACKEND_URL/api/workflows/aurity/sessions' \\"
  echo "    -H 'Authorization: Bearer \$AUTH_TOKEN' | jq"
  echo ""
fi

echo "Ver documentación completa:"
echo "  cat README.md"
echo "  cat CURL_TESTS.md"
echo ""

echo "Ejecutar test individual:"
echo "  ./test_medical_session.sh"
echo "  ./test_checkin.sh"
echo "  ./test_chat_mode.sh"
echo "  ./verify_h5_integrity.sh"
echo ""

# Limpiar archivos temporales
if [ -d temp ]; then
  TEMP_FILES=$(ls -1 temp 2>/dev/null | wc -l)
  if [ "$TEMP_FILES" -gt 0 ]; then
    echo "🧹 Archivos temporales en temp/: $TEMP_FILES"
    echo "   Limpiar con: rm -rf temp/*"
    echo ""
  fi
fi

echo "===================================="
echo ""
