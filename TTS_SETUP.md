# TTS Multi-Provider Setup Guide

Sistema de Text-to-Speech híbrido con OpenAI TTS y Azure Speech Services.

## 🎯 ¿Por qué dos providers?

### OpenAI TTS (Recomendado por defecto)
✅ **Ventajas:**
- Voces **extremadamente naturales** y expresivas
- Suenan como humanos reales, no robots
- Perfecto para demos, chat de voz, asistentes conversacionales
- 11 voces disponibles (2025)
- Modelo `tts-1-hd` con alta calidad

❌ **Desventajas:**
- Solo inglés nativo (puede hablar español pero con acento)
- Requiere API key de OpenAI (pagado)

### Azure Speech Services
✅ **Ventajas:**
- 17 voces en **español de México** (es-MX)
- Pronunciación perfecta de términos médicos en español
- Voces multilingües disponibles
- Gratis con Azure subscription

❌ **Desventajas:**
- Suenan más robotizadas comparado con OpenAI
- Menos expresivas y naturales

---

## 🔧 Configuración

### 1. Obtener API Key de OpenAI

1. Ve a https://platform.openai.com/api-keys
2. Inicia sesión o crea una cuenta
3. Haz clic en "Create new secret key"
4. Copia la key (empieza con `sk-proj-...`)

**Costo:** ~$0.015 USD por 1,000 caracteres (modelo `tts-1-hd`)

### 2. Configurar .env

Abre `/Users/bernardurizaorozco/Documents/free-intelligence/.env` y reemplaza:

```bash
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY_HERE>
```

Por tu API key real:

```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
```

### 3. Reiniciar Backend

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
make dev-all  # O el comando que uses para iniciar el backend
```

---

## 🎙️ Voces Disponibles

### OpenAI TTS (11 voces)

**Femeninas:**
- `nova` ⭐ - Cálida, natural (default, recomendada)
- `shimmer` - Clara, profesional
- `ballad` - Nueva 2025
- `coral` - Nueva 2025

**Masculinas:**
- `alloy` - Neutral, versátil
- `echo` - Masculina estándar
- `fable` - Acento británico
- `onyx` - Profunda, autoritaria

**Nuevas 2025:**
- `ash`, `sage`, `verse`

### Azure Speech Services (17 voces es-MX)

**Femeninas (9):**
- `es-MX-DaliaNeural` - Default para contexto médico
- `es-MX-RenataNeural`, `es-MX-MarinaNeural`
- `es-MX-CarlotaNeural`, `es-MX-LarissaNeural`
- `es-MX-DaliaMultilingualNeural` (es/en)
- Y más...

**Masculinas (8):**
- `es-MX-JorgeNeural`
- `es-MX-GerardoNeural`
- `es-MX-JorgeMultilingualNeural` (es/en)
- Y más...

---

## 🧪 Prueba de Comparación

Ejecuta el script de prueba para comparar ambas voces:

```bash
python3 /tmp/test_tts_comparison.py
```

Esto generará archivos MP3 en `/tmp/` para que los compares:
- `/tmp/openai_nova.mp3` (OpenAI - natural)
- `/tmp/azure_Dalia.mp3` (Azure - más robótica)

**Reproducir audio:**
```bash
# macOS
open /tmp/openai_nova.mp3

# Linux
mpg123 /tmp/openai_nova.mp3
```

---

## 📡 Uso de la API

### Auto-detección de Provider

El sistema detecta automáticamente el provider basándose en el nombre de la voz:

```bash
# OpenAI (automático si la voz no empieza con "es-MX-")
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a natural sounding voice",
    "voice": "nova"
  }'

# Azure (automático si la voz empieza con "es-MX-")
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hola, esta es una voz en español de México",
    "voice": "es-MX-DaliaNeural"
  }'
```

### Selección Manual de Provider

```bash
# Forzar OpenAI
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Using OpenAI explicitly",
    "voice": "nova",
    "provider": "openai"
  }'

# Forzar Azure
curl -X POST http://localhost:7001/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Usando Azure explícitamente",
    "voice": "es-MX-DaliaNeural",
    "provider": "azure"
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
✅ **Usar OpenAI TTS**
- Voz: `nova` (femenina) o `alloy` (neutral)
- Provider: `openai`
- Razón: Suena mucho más natural y humana

### Para Contenido Médico en Español
✅ **Usar Azure Speech Services**
- Voz: `es-MX-DaliaNeural` (femenina) o `es-MX-JorgeNeural` (masculina)
- Provider: `azure`
- Razón: Pronunciación perfecta de términos médicos en español

### Para Contenido Bilingüe (es/en)
✅ **Usar Azure Multilingüe**
- Voz: `es-MX-DaliaMultilingualNeural`
- Provider: `azure`
- Razón: Puede hablar español e inglés correctamente

---

## 🔍 Verificación

### Check 1: API Keys configuradas

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
grep "OPENAI_API_KEY" .env
grep "AZURE_SPEECH_KEY" .env
```

Deberías ver ambas keys configuradas (no `<YOUR_..._HERE>`).

### Check 2: Backend funcionando

```bash
curl http://localhost:7001/health
# Respuesta esperada: {"status":"ok"}
```

### Check 3: Documentación de API

Abre http://localhost:7001/docs y busca el endpoint `POST /api/tts/synthesize`.
Deberías ver la documentación con todas las voces listadas.

---

## 📚 Referencias

- [OpenAI TTS API Reference](https://platform.openai.com/docs/api-reference/audio/createSpeech)
- [OpenAI TTS Guide](https://www.videosdk.live/developer-hub/ai/openai-text-to-speech)
- [Azure Speech Services](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/text-to-speech-quickstart)

---

## 💰 Costos Estimados

### OpenAI TTS
- **Modelo HD:** $0.015 / 1,000 caracteres (~$15 por 1 millón de caracteres)
- **Modelo Standard:** $0.015 / 1,000 caracteres

**Ejemplo:** 1,000 mensajes de 100 caracteres = $1.50 USD

### Azure Speech Services
- **Neural Voices:** Incluido en Azure subscription
- **Free tier:** 5M caracteres gratis/mes

**Recomendación:** Empieza con Azure (gratis), cambia a OpenAI para mejor calidad.

---

**Created:** 2025-12-08
**Status:** ✅ Production Ready
