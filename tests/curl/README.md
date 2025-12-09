# AURITY - Suite de Pruebas cURL 🧪

Suite completa de pruebas para el sistema AURITY usando cURL. Prueba todos los endpoints de producción sin necesidad de frontend.

## 📁 Estructura

```
tests/curl/
├── README.md                      ← Este archivo
├── CURL_TESTS.md                  ← Documentación completa de todos los endpoints
├── setup.sh                       ← Configuración inicial (ejecutar primero)
├── test_medical_session.sh        ← Test E2E de sesión médica completa
├── test_checkin.sh                ← Test de check-in receptionist
├── test_chat_mode.sh              ← Test de modo chat (transcripción síncrona)
├── .env.curl                      ← Configuración (generado por setup.sh)
└── temp/                          ← Archivos temporales (audio, QR codes)
```

## 🚀 Quick Start

### 1. Configuración Inicial

```bash
cd tests/curl

# Ejecutar setup (solo una vez)
./setup.sh

# Seleccionar ambiente:
#   1 = Local (http://localhost:7001)
#   2 = Producción (https://app.aurity.io)

# Ingresar token de Auth0 (desde consola del navegador)
```

El script `setup.sh` te guiará paso a paso:
- ✅ Verificará conectividad con el backend
- ✅ Validará tu token de Auth0
- ✅ Creará archivo `.env.curl` con configuración
- ✅ Generará audio de prueba con ffmpeg
- ✅ Creará directorio `temp/` para archivos

### 2. Cargar Configuración

```bash
# Cargar variables de entorno
source .env.curl

# Verificar configuración
echo "Backend: $BACKEND_URL"
echo "Token: ${AUTH_TOKEN:0:20}..."
```

### 3. Ejecutar Tests

#### Test Completo de Sesión Médica (E2E)

```bash
./test_medical_session.sh
```

**Qué hace:**
1. ✅ Crea sesión médica con metadata de paciente
2. ✅ Sube 4 chunks de audio (0-8 segundos)
3. ✅ Hace polling hasta transcripción completa
4. ✅ Finaliza sesión con audio completo + WebSpeech
5. ✅ Ejecuta diarización (identificar speakers)
6. ✅ Genera nota SOAP con LLM
7. ✅ Muestra timeline y audit log

**Duración:** ~60-90 segundos

**Output esperado:**
```
🏥 AURITY - Test de Sesión Médica
==================================

📋 Session ID: a1b2c3d4-e5f6-...

1️⃣  Subiendo chunk 0 (iniciando sesión)...
✅ Chunk 0 subido

2️⃣  Subiendo chunks adicionales...
   ✅ Chunk 1 subido
   ✅ Chunk 2 subido
   ✅ Chunk 3 subido

3️⃣  Esperando transcripción...
   Intento 5/30: completed (4/4 chunks, 100%)
✅ Transcripción completa

...

✅ Test completado exitosamente
```

#### Test de Check-in Receptionist

```bash
./test_checkin.sh
```

**Qué hace:**
1. ✅ Genera QR code para tablet en clínica
2. ✅ Inicia sesión de check-in
3. ✅ Identifica paciente por nombre + fecha nacimiento
4. ✅ Muestra acciones pendientes (formularios)
5. ✅ Completa check-in
6. ✅ Muestra estado de sala de espera

**Duración:** ~10-15 segundos

#### Test de Modo Chat

```bash
./test_chat_mode.sh
```

**Qué hace:**
1. ✅ Envía 3 mensajes en modo chat (transcripción síncrona)
2. ✅ Obtiene transcripts inmediatamente (sin polling)
3. ✅ Compara con modo medical (async con polling)
4. ✅ Muestra diferencias de performance

**Duración:** ~5-10 segundos

## 📖 Documentación Completa

Ver `CURL_TESTS.md` para:
- 📋 Todos los endpoints disponibles
- 🔐 Configuración de Auth0
- 🎤 Transcripción de audio
- 👥 Diarización
- 📋 Generación SOAP
- 🏨 Check-in receptionist
- 📊 Monitoreo y auditoría
- 🛠️ Troubleshooting

## 🔧 Troubleshooting

### Error: "401 Unauthorized"

**Causa:** Token de Auth0 expirado (duran 24 horas)

**Solución:**
```bash
# 1. Obtener nuevo token desde navegador
# 2. Editar .env.curl
nano .env.curl

# 3. Actualizar AUTH_TOKEN
export AUTH_TOKEN="eyJ..."

# 4. Recargar
source .env.curl
```

### Error: "Backend no disponible"

**Causa:** Backend local no está corriendo

**Solución:**
```bash
# Iniciar backend
cd ../../
make dev-backend

# En otra terminal, ejecutar test
cd tests/curl
./test_medical_session.sh
```

### Error: "ffmpeg: command not found"

**Causa:** ffmpeg no instalado

**Solución:**
```bash
# macOS
brew install ffmpeg

# Regenerar audio de prueba
./setup.sh
```

### Error: "Session not found"

**Causa:** Sesión expiró o ID incorrecto

**Solución:**
```bash
# Generar nuevo session ID
export SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
echo "New session: $SESSION_ID"
```

## 🎯 Ejemplos de Uso Avanzado

### Probar con Audio Real

```bash
# Usar tu propio archivo de audio
curl -X POST "$BACKEND_URL/api/transcription/stream" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -F "session_id=$(uuidgen | tr '[:upper:]' '[:lower:]')" \
  -F "chunk_number=0" \
  -F "mode=medical" \
  -F "patient_name=Juan Pérez" \
  -F "patient_age=45" \
  -F "audio=@/path/to/my/audio.wav" | jq
```

### Filtrar Sesiones por Fecha

```bash
source .env.curl

# Sesiones de hoy
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions?start_date=$(date +%Y-%m-%d)" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq

# Sesiones de diciembre 2025
curl -X GET "$BACKEND_URL/api/workflows/aurity/sessions?start_date=2025-12-01&end_date=2025-12-31" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq
```

### Exportar Transcripción

```bash
SESSION_ID="a1b2c3d4-..."

# Como JSON
curl -X GET "$BACKEND_URL/api/export/transcript/$SESSION_ID?format=json" \
  -H "Authorization: Bearer $AUTH_TOKEN" | jq > transcript.json

# Como TXT
curl -X GET "$BACKEND_URL/api/export/transcript/$SESSION_ID?format=txt" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -o transcript.txt

# Como DOCX
curl -X GET "$BACKEND_URL/api/export/transcript/$SESSION_ID?format=docx" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -o transcript.docx
```

### Monitoreo en Tiempo Real

```bash
SESSION_ID="a1b2c3d4-..."

# Poll cada segundo
watch -n 1 "curl -s -X GET '$BACKEND_URL/api/workflows/aurity/sessions/$SESSION_ID/monitor' \
  -H 'Authorization: Bearer $AUTH_TOKEN' | jq"
```

## 📊 Métricas de Performance

**Tiempos esperados** (backend en localhost):

| Operación | Tiempo Promedio | Max Aceptable |
|-----------|----------------|---------------|
| Upload chunk (2s audio) | 300-500ms | 1s |
| Transcripción Deepgram | 200-400ms | 2s |
| Diarización (5 min audio) | 8-12s | 20s |
| Generación SOAP | 15-25s | 40s |
| Check-in completo | 30-45s | 60s |

**Tiempos en producción** (latencia de red incluida):

| Operación | Tiempo Promedio | Max Aceptable |
|-----------|----------------|---------------|
| Upload chunk | 500-800ms | 2s |
| Polling cycle | 100-200ms | 500ms |
| Diarización | 10-15s | 30s |
| Generación SOAP | 20-35s | 60s |

## 🔐 Seguridad

### ⚠️ NUNCA:

- ❌ Hacer commit de `.env.curl` (contiene tokens)
- ❌ Compartir tokens en Slack/email
- ❌ Usar tokens de producción en localhost
- ❌ Hardcodear tokens en scripts

### ✅ SIEMPRE:

- ✅ Agregar `.env.curl` a `.gitignore`
- ✅ Renovar tokens cada 24h
- ✅ Usar HTTPS en producción
- ✅ Validar responses con `jq`

## 📝 Convenciones

### Nombres de Session ID

```bash
# Medical sessions (UUID v4)
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
# Ejemplo: a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Chat sessions (user-scoped)
CHAT_SESSION_ID="chat_${USER_ID}"
# Ejemplo: chat_user_auth0|123456

# Check-in sessions (UUID v4)
CHECKIN_SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
```

### Formatos de Audio

```bash
# ✅ Recomendado
WAV: 16kHz, mono, 16-bit PCM
WebM: Opus codec, 16kHz

# ✅ Soportado
MP3: CBR 128kbps+
FLAC: lossless
OGG: Vorbis codec

# ❌ No soportado
AAC-LC
WMA
Real Audio
```

## 🎓 Recursos Adicionales

- **Documentación completa:** `CURL_TESTS.md`
- **Arquitectura del sistema:** `../../docs/STORAGE_ARCHITECTURE.md`
- **API Backend:** `../../backend/docs/API_ARCHITECTURE.md`
- **Frontend:** `../../apps/aurity/docs/NAVIGATION.md`
- **Contexto completo:** `../../claude.md`

## 🤝 Contribuir

Para agregar nuevos tests:

1. Seguir convenciones de nombres: `test_<feature>.sh`
2. Usar `set -e` para fail-fast
3. Incluir mensajes descriptivos con emojis
4. Validar responses con `jq`
5. Limpiar archivos temporales
6. Documentar en `CURL_TESTS.md`

Ejemplo:
```bash
#!/bin/bash
# test_new_feature.sh

set -e
source .env.curl

echo "🎯 Test de Nueva Feature"
echo "========================"
echo ""

# Test logic...

echo "✅ Test completado"
```

## 📞 Soporte

**Problemas comunes:** Ver sección Troubleshooting arriba

**Bugs en tests:** Abrir issue en GitHub

**Preguntas:** Slack #aurity-dev

---

**Autor:** Bernard Uriza Orozco
**Proyecto:** AURITY v0.3.0
**Última actualización:** 2025-12-08
