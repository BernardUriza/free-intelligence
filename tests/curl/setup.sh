#!/bin/bash
# setup.sh - Configuración inicial para pruebas con cURL
# Autor: Bernard Uriza Orozco
# Proyecto: AURITY v0.3.0

set -e

echo "🔧 AURITY - Configuración de Pruebas cURL"
echo "=========================================="
echo ""

# Detectar ambiente
read -p "¿Ambiente? (1=Local, 2=Producción): " ENV_CHOICE

if [ "$ENV_CHOICE" = "1" ]; then
  BACKEND_URL="http://localhost:7001"
  echo "✅ Ambiente: LOCAL (http://localhost:7001)"
elif [ "$ENV_CHOICE" = "2" ]; then
  BACKEND_URL="https://app.aurity.io"
  echo "✅ Ambiente: PRODUCCIÓN (https://app.aurity.io)"
else
  echo "❌ Opción inválida"
  exit 1
fi

# Verificar conectividad
echo ""
echo "🔍 Verificando conectividad..."
if curl -s -f "$BACKEND_URL/health" > /dev/null; then
  echo "✅ Backend disponible"
else
  echo "❌ Backend no disponible en $BACKEND_URL"
  exit 1
fi

# Obtener token
echo ""
echo "🔑 Configurando autenticación..."
echo ""
echo "Por favor, obtén tu token de Auth0:"
echo "1. Abre la consola del navegador en $BACKEND_URL"
echo "2. Ejecuta: await auth0.getAccessTokenSilently()"
echo "3. Copia el token"
echo ""
read -p "Pega tu token aquí: " AUTH_TOKEN

if [ -z "$AUTH_TOKEN" ]; then
  echo "❌ Token vacío"
  exit 1
fi

# Validar token
echo ""
echo "🔍 Validando token..."
if curl -s -f -H "Authorization: Bearer $AUTH_TOKEN" "$BACKEND_URL/api/workflows/aurity/sessions" > /dev/null; then
  echo "✅ Token válido"
else
  echo "❌ Token inválido o expirado"
  exit 1
fi

# Crear archivo .env
echo ""
echo "📝 Creando archivo .env.curl..."

cat > .env.curl << EOF
# AURITY cURL Test Configuration
# Generado: $(date)

# Backend URL
export BACKEND_URL="$BACKEND_URL"

# Auth0 Token (renovar cada 24h)
export AUTH_TOKEN="$AUTH_TOKEN"

# IDs de prueba (generar nuevos con: uuidgen | tr '[:upper:]' '[:lower:]')
export SESSION_ID="\$(uuidgen | tr '[:upper:]' '[:lower:]')"
export CLINIC_ID="clinic_001"
export PATIENT_ID="patient_test_001"

# Funciones helper
function new_session_id() {
  uuidgen | tr '[:upper:]' '[:lower:]'
}

function api_get() {
  curl -s -X GET "\$BACKEND_URL\$1" \\
    -H "Authorization: Bearer \$AUTH_TOKEN" \\
    -H "Accept: application/json"
}

function api_post() {
  local endpoint="\$1"
  local data="\$2"
  curl -s -X POST "\$BACKEND_URL\$endpoint" \\
    -H "Authorization: Bearer \$AUTH_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d "\$data"
}
EOF

echo "✅ Archivo .env.curl creado"

# Crear directorio para archivos temporales
mkdir -p temp
echo "✅ Directorio temp/ creado"

# Crear audio de prueba
echo ""
echo "🎵 Generando audio de prueba..."

if command -v ffmpeg &> /dev/null; then
  ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" \
    -ar 16000 -ac 1 -f wav temp/test_audio.wav -y -loglevel quiet
  echo "✅ Audio de prueba creado: temp/test_audio.wav"
else
  echo "⚠️  ffmpeg no instalado - omitiendo generación de audio"
  echo "   Instalar con: brew install ffmpeg"
fi

# Resumen
echo ""
echo "=========================================="
echo "✅ Configuración completa"
echo ""
echo "Para usar:"
echo "  source .env.curl"
echo "  ./test_medical_session.sh"
echo ""
echo "Archivos creados:"
echo "  - .env.curl (configuración)"
echo "  - temp/test_audio.wav (audio de prueba)"
echo ""
echo "Scripts disponibles:"
echo "  - test_medical_session.sh (sesión médica completa)"
echo "  - test_checkin.sh (check-in receptionist)"
echo "  - test_chat_mode.sh (modo chat)"
echo ""
