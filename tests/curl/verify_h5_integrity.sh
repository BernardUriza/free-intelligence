#!/bin/bash
# verify_h5_integrity.sh - Verificar integridad de archivos HDF5
# Autor: Bernard Uriza Orozco

set -e

# Cargar configuración
if [ ! -f .env.curl ]; then
  echo "❌ Archivo .env.curl no encontrado"
  echo "Ejecuta primero: ./setup.sh"
  exit 1
fi

source .env.curl

echo "🔍 AURITY - Verificación de Integridad HDF5"
echo "==========================================="
echo ""

# Obtener lista de sesiones
echo "1️⃣  Obteniendo lista de sesiones..."

SESSIONS=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions" \
  -H "Authorization: Bearer $AUTH_TOKEN")

SESSION_COUNT=$(echo "$SESSIONS" | jq '. | length')

if [ "$SESSION_COUNT" -eq 0 ]; then
  echo "⚠️  No hay sesiones disponibles"
  echo "   Ejecuta primero: ./test_medical_session.sh"
  exit 0
fi

echo "📋 Sesiones encontradas: $SESSION_COUNT"
echo ""

# Seleccionar sesión más reciente
LATEST_SESSION=$(echo "$SESSIONS" | jq -r '.[0].session_id')
echo "🎯 Verificando sesión más reciente: $LATEST_SESSION"
echo ""

# 2. Verificar estructura HDF5
echo "2️⃣  Verificando estructura de archivo HDF5..."

SESSION_DETAILS=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$LATEST_SESSION" \
  -H "Authorization: Bearer $AUTH_TOKEN")

echo "$SESSION_DETAILS" | jq '{
  session_id,
  created_at,
  tasks: .tasks | keys,
  chunks_count: .metadata.chunks_count,
  audio_duration: .metadata.audio_duration_seconds
}'

echo ""

# 3. Verificar checksums
echo "3️⃣  Verificando integridad con checksums..."

# Nota: Este endpoint es interno, requiere permisos especiales
INTEGRITY_RESPONSE=$(curl -s -X GET "$BACKEND_URL/api/internal/sessions/$LATEST_SESSION/integrity" \
  -H "Authorization: Bearer $AUTH_TOKEN")

if echo "$INTEGRITY_RESPONSE" | jq -e '.is_valid' > /dev/null 2>&1; then
  IS_VALID=$(echo "$INTEGRITY_RESPONSE" | jq -r '.is_valid')

  if [ "$IS_VALID" = "true" ]; then
    echo "✅ Checksum válido - Archivo íntegro"
    echo "$INTEGRITY_RESPONSE" | jq '{
      file_path,
      checksum_expected: (.checksum_expected[:16] + "..."),
      checksum_actual: (.checksum_actual[:16] + "..."),
      is_valid
    }'
  else
    echo "❌ Checksum inválido - Posible corrupción"
    echo "$INTEGRITY_RESPONSE" | jq
  fi
else
  echo "⚠️  Endpoint de integridad no disponible"
  echo "   (Requiere permisos de admin o endpoint no implementado)"
fi

echo ""

# 4. Verificar tareas completadas
echo "4️⃣  Verificando tareas completadas..."

TASKS=$(echo "$SESSION_DETAILS" | jq -r '.tasks | to_entries[] | "\(.key): \(.value.status)"')

echo "$TASKS"
echo ""

# 5. Verificar versiones (event sourcing)
echo "5️⃣  Verificando versioning (event sourcing)..."

# Contar versiones de cada tarea
TRANSCRIPTION_VERSIONS=$(echo "$SESSION_DETAILS" | jq -r '.tasks.TRANSCRIPTION.versions | length // 0')
DIARIZATION_VERSIONS=$(echo "$SESSION_DETAILS" | jq -r '.tasks.DIARIZATION.versions | length // 0')
SOAP_VERSIONS=$(echo "$SESSION_DETAILS" | jq -r '.tasks.SOAP_GENERATION.versions | length // 0')

echo "TRANSCRIPTION: $TRANSCRIPTION_VERSIONS versiones"
echo "DIARIZATION: $DIARIZATION_VERSIONS versiones"
echo "SOAP_GENERATION: $SOAP_VERSIONS versiones"

if [ "$TRANSCRIPTION_VERSIONS" -gt 0 ]; then
  echo "✅ Event sourcing activo (append-only pattern)"
else
  echo "⚠️  Sin versiones registradas"
fi

echo ""

# 6. Verificar chunks de audio
echo "6️⃣  Verificando chunks de audio..."

CHUNKS=$(curl -s -X GET "$BACKEND_URL/api/transcription/sessions/$LATEST_SESSION/chunks" \
  -H "Authorization: Bearer $AUTH_TOKEN")

CHUNKS_COUNT=$(echo "$CHUNKS" | jq '.chunks | length')
echo "📦 Chunks guardados: $CHUNKS_COUNT"

if [ "$CHUNKS_COUNT" -gt 0 ]; then
  echo ""
  echo "Detalles de chunks:"
  echo "$CHUNKS" | jq '.chunks[] | {
    chunk_number,
    duration: .metadata.duration,
    timestamp_start: .metadata.timestamp_start,
    timestamp_end: .metadata.timestamp_end,
    has_audio: (.audio_bytes > 0),
    has_transcript: (.transcript != "")
  }'
fi

echo ""

# 7. Verificar inmutabilidad (no hay deletes)
echo "7️⃣  Verificando inmutabilidad (append-only)..."

AUDIT_LOG=$(curl -s -X GET "$BACKEND_URL/api/workflows/aurity/sessions/$LATEST_SESSION/audit" \
  -H "Authorization: Bearer $AUTH_TOKEN")

DELETE_EVENTS=$(echo "$AUDIT_LOG" | jq '[.events[] | select(.event_type | contains("DELETE"))] | length')

if [ "$DELETE_EVENTS" -eq 0 ]; then
  echo "✅ Sin eventos de DELETE (append-only respetado)"
else
  echo "⚠️  Se encontraron $DELETE_EVENTS eventos DELETE (posible violación)"
fi

# Verificar eventos de MODIFY/UPDATE
MODIFY_EVENTS=$(echo "$AUDIT_LOG" | jq '[.events[] | select(.event_type | contains("MODIFY") or contains("UPDATE"))] | length')

if [ "$MODIFY_EVENTS" -eq 0 ]; then
  echo "✅ Sin eventos de MODIFY/UPDATE (inmutabilidad respetada)"
else
  echo "⚠️  Se encontraron $MODIFY_EVENTS eventos MODIFY/UPDATE"
fi

echo ""

# 8. Resumen de integridad
echo "8️⃣  Resumen de Integridad"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Calcular score
SCORE=0
MAX_SCORE=5

# Check 1: Checksum válido
if [ "$IS_VALID" = "true" ]; then
  echo "✅ Checksum SHA256 válido"
  SCORE=$((SCORE + 1))
else
  echo "❌ Checksum inválido"
fi

# Check 2: Versioning activo
if [ "$TRANSCRIPTION_VERSIONS" -gt 0 ]; then
  echo "✅ Event sourcing activo (versioning)"
  SCORE=$((SCORE + 1))
else
  echo "⚠️  Sin versiones (esperado si sesión nueva)"
fi

# Check 3: Chunks guardados
if [ "$CHUNKS_COUNT" -gt 0 ]; then
  echo "✅ Chunks de audio guardados ($CHUNKS_COUNT)"
  SCORE=$((SCORE + 1))
else
  echo "❌ Sin chunks de audio"
fi

# Check 4: No deletes
if [ "$DELETE_EVENTS" -eq 0 ]; then
  echo "✅ Append-only respetado (sin DELETEs)"
  SCORE=$((SCORE + 1))
else
  echo "❌ Eventos DELETE detectados"
fi

# Check 5: No modifies (inmutabilidad)
if [ "$MODIFY_EVENTS" -eq 0 ]; then
  echo "✅ Inmutabilidad respetada (sin MODIFYs)"
  SCORE=$((SCORE + 1))
else
  echo "⚠️  Eventos MODIFY detectados"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Score de Integridad: $SCORE/$MAX_SCORE"

if [ "$SCORE" -eq "$MAX_SCORE" ]; then
  echo "🎉 PERFECTO - Integridad total garantizada"
elif [ "$SCORE" -ge 3 ]; then
  echo "✅ BUENO - Integridad aceptable"
else
  echo "⚠️  ATENCIÓN - Posibles problemas de integridad"
fi

echo ""
echo "==========================================="
echo "✅ Verificación completada"
echo ""
echo "📋 Session ID verificado: $LATEST_SESSION"
echo ""
echo "Más detalles:"
echo "  curl -X GET '$BACKEND_URL/api/workflows/aurity/sessions/$LATEST_SESSION' \\"
echo "    -H 'Authorization: Bearer \$AUTH_TOKEN' | jq"
echo ""
