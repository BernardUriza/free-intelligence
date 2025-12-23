# TTS Multi-Provider Setup Guide

Sistema de Text-to-Speech con OpenAI TTS y Azure OpenAI TTS.

## 🎯 Providers Disponibles

### OpenAI TTS (Recomendado por defecto)
✅ **Ventajas:**
- Voces **extremadamente naturales** y expresivas
- Suenan como humanos reales, no robots
- Perfecto para demos, chat de voz, asistentes conversacionales
- 11 voces disponibles (2025)
- Modelo `tts-1-hd` con alta calidad

❌ **Desventajas:**
- Requiere API key de OpenAI (pagado)
- ~$0.015 USD por 1,000 caracteres

### Azure OpenAI TTS
✅ **Ventajas:**
- Modelos OpenAI desplegados en tu infraestructura Azure
- Mismas voces naturales que OpenAI standard
- Integración con Azure subscription
- Mismo soporte de acento control con steerable TTS

❌ **Desventajas:**
- Requiere Azure subscription y deployment
- Requiere configuración de endpoint y API key

### OpenAI Steerable TTS (Accent Control)
✅ **Ventajas:**
- Control de acento mexicano automático para español
- Usa steerable voices (alloy, echo, shimmer)
- Auto-detección de idioma español

Perfecta para contenido en español con acento mexicano natural.

---

## 🔧 Configuración

### 1. Obtener API Key de OpenAI (para OpenAI TTS)

1. Ve a https://platform.openai.com/api-keys
2. Inicia sesión o crea una cuenta
3. Haz clic en "Create new secret key"
4. Copia la key (empieza con `sk-proj-...`)

### 2. Configurar .env

Abre `/Users/bernardurizaorozco/Documents/free-intelligence/.env` y agrega:

```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

### 3. (Opcional) Configurar Azure OpenAI TTS

Si tienes modelos OpenAI desplegados en Azure:

```bash
AZURE_OPENAI_TTS_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_TTS_API_KEY=your-api-key-here
AZURE_OPENAI_TTS_API_VERSION=2025-03-01-preview
AZURE_OPENAI_TTS_DEPLOYMENT=tts-hd
```

### 4. Reiniciar Backend

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
make dev-all  # O el comando que uses para iniciar el backend
```

---

## 🎙️ Voces Disponibles (3 voces)

Todos los providers soportan las mismas 3 voces alineadas con Aurity:

### nova ⭐ (Default, Recomendada)
- **Género:** Femenina
- **Características:** Cálida, natural, expresiva
- **Casos de uso:** Demo mode, asistentes conversacionales, contexto médico
- **Accento:** Neutra (estándar OpenAI)
- **Acento Mexicano:** Sí (con OpenAI Steerable)

### alloy
- **Género:** Neutral/Versátil
- **Características:** Neutral, profesional
- **Casos de uso:** Contextos profesionales, narración
- **Acento:** Neutro
- **Acento Mexicano:** Sí (con OpenAI Steerable)

### shimmer
- **Género:** Femenina
- **Características:** Clara, brillante
- **Casos de uso:** Pronunciación clara, instrucciones
- **Acento:** Neutro
- **Acento Mexicano:** Sí (con OpenAI Steerable)

---

## 📡 Uso de la API

### Auto-detección de Provider

El sistema detecta automáticamente el provider:

```bash
# Spanish text + steerable voice = OpenAI Steerable con acento mexicano
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hola, esto es una prueba de acento mexicano",
    "voice": "nova"
  }'
```

### Selección Manual de Provider

```bash
# Forzar OpenAI Standard
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Using OpenAI explicitly",
    "voice": "nova",
    "provider": "openai"
  }'

# Forzar Azure OpenAI TTS
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Using Azure OpenAI explicitly",
    "voice": "nova",
    "provider": "azure-openai"
  }'

# Forzar OpenAI Steerable (con acento mexicano)
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hola, con acento mexicano garantizado",
    "voice": "nova",
    "provider": "openai-steerable",
    "accent": "Mexican Spanish"
  }'
```

### Opciones Avanzadas

```bash
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Custom speed and format",
    "voice": "nova",
    "speed": 1.2,
    "response_format": "opus"
  }' \
  --output test.opus
```

**Formatos soportados:**
- `mp3` (recomendado para web)
- `opus` (alta compresión)
- `aac` (Apple devices)
- `flac` (sin pérdida)
- `wav`, `pcm` (sin comprimir)

**Velocidad:**
- `0.25` - 4× más lento
- `1.0` - Normal (default)
- `2.0` - 2× más rápido
- `4.0` - 4× más rápido

---

## 🎯 Recomendaciones de Uso

### Para Demo Mode (Voz Conversacional)
✅ **Usar OpenAI TTS o Azure OpenAI TTS**
- Voz: `nova` (femenina) o `alloy` (neutral)
- Provider: `openai` o `azure-openai`
- Razón: Suena natural y humana, perfecto para conversación

### Para Contenido Médico en Español
✅ **Usar OpenAI Steerable TTS con acento mexicano**
- Voz: `nova` (femenina) o `alloy` (neutral)
- Provider: `openai-steerable`
- Accent: `"Mexican Spanish"`
- Razón: Acento mexicano natural + voz clara para contexto médico

### Para Contenido Profesional
✅ **Usar OpenAI TTS**
- Voz: `alloy` (neutral) o `shimmer` (clara)
- Provider: `openai`
- Razón: Profesional y claro

---

## 🔍 Verificación

### Check 1: API Keys configuradas

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
grep "OPENAI_API_KEY" .env
```

Deberías ver la key configurada (no `<YOUR_OPENAI_API_KEY_HERE>`).

### Check 2: Backend funcionando

```bash
curl http://localhost:7001/health
# Respuesta esperada: {"status":"ok"}
```

### Check 3: Providers disponibles

```bash
curl http://localhost:7001/api/tts/providers | jq
```

Respuesta esperada:
```json
{
  "providers": {
    "azure-openai": true,    # Si está configurado
    "openai": true,          # Si está configurado
    "openai_steerable": true # Si está configurado
  }
}
```

### Check 4: Prueba de síntesis

```bash
curl -X POST 'http://localhost:7001/api/tts/synthesize' \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Hola mundo",
    "voice": "nova",
    "response_format": "mp3"
  }' --output test.mp3

file test.mp3  # Debe decir "Audio file with ID3"
```

---

## 📚 Referencias

- [OpenAI TTS API Reference](https://platform.openai.com/docs/api-reference/audio/createSpeech)
- [Azure OpenAI TTS](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#audio)

---

## 💰 Costos Estimados

### OpenAI TTS
- **Precio:** $0.015 / 1,000 caracteres
- **Ejemplo:** 1,000 mensajes de 100 caracteres = $1.50 USD/mes

### Azure OpenAI TTS
- **Precio:** Basado en Azure subscription
- **Incluye:** Actualizaciones y soporte de Azure

---

**Updated:** 2025-12-23
**Status:** ✅ Production Ready
**Changes:** Removed Azure Speech Services, simplified to OpenAI-only
