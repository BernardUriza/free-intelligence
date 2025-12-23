TTS (Multi-Provider) - Quick Setup

This project supports OpenAI TTS voices via multiple providers:
- **Azure OpenAI TTS** - OpenAI models deployed on your Azure infrastructure
- **OpenAI TTS** - Standard OpenAI API (api.openai.com)
- **OpenAI Steerable TTS** - With accent control for Spanish

All providers support the same 3 voices: `alloy`, `nova` (default), `shimmer`

---

## OpenAI Standard TTS

For general use with standard OpenAI API:

Local development (bash/zsh):

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
# Start backend (example):
PYTHONPATH=backend/src uvicorn backend.app.main:app --reload --port 7001
```

Quick curl test (after starting backend):

```bash
curl -X POST 'http://localhost:7001/api/tts/synthesize' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "text": "Hello world",
    "voice": "nova",
    "provider": "openai",
    "response_format": "mp3"
  }' --output test-openai.mp3
```

Available voices: `alloy` (neutral), `nova` (female, warm - default), `shimmer` (female, clear)

CI / Production:
- Add `OPENAI_API_KEY` to your deployment secrets (DigitalOcean, Docker Swarm, Kubernetes, or CI env).
- The application will return HTTP 400 if key is missing during a TTS request.

---

## Azure OpenAI TTS

For OpenAI models deployed on your Azure infrastructure:

Local development:

```bash
export AZURE_OPENAI_TTS_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_TTS_API_KEY="your-api-key-here"
export AZURE_OPENAI_TTS_API_VERSION="2025-03-01-preview"
export AZURE_OPENAI_TTS_DEPLOYMENT="tts-hd"  # Your deployment name

# Start backend
PYTHONPATH=backend/src uvicorn backend.app.main:app --reload --port 7001
```

Quick curl test:

```bash
curl -X POST 'http://localhost:7001/api/tts/synthesize' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "text": "Hola, esto es una prueba de Azure OpenAI TTS",
    "voice": "nova",
    "provider": "azure-openai",
    "response_format": "mp3"
  }' --output test-azure-openai.mp3
```

Available voices (aligned with Aurity): `alloy`, `nova` (default), `shimmer`

Backward compatibility: If you use old variable names (`AZURE_TTS_ENDPOINT`, `AZURE_TTS_API_KEY`), they will work automatically as fallback.

CI / Production:
- Add `AZURE_OPENAI_TTS_ENDPOINT`, `AZURE_OPENAI_TTS_API_KEY`, `AZURE_OPENAI_TTS_API_VERSION`, and `AZURE_OPENAI_TTS_DEPLOYMENT` to your deployment secrets.
- The system will auto-detect and use Azure OpenAI TTS when configured.

---

## OpenAI Steerable TTS (Accent Control)

For Spanish content with automatic Mexican Spanish accent detection:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
PYTHONPATH=backend/src uvicorn backend.app.main:app --reload --port 7001
```

Quick curl test:

```bash
curl -X POST 'http://localhost:7001/api/tts/synthesize' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "text": "Hola, este es un mensaje con acento mexicano",
    "voice": "nova",
    "provider": "openai-steerable",
    "accent": "Mexican Spanish",
    "response_format": "mp3"
  }' --output test-steerable.mp3
```

Available voices: `alloy`, `echo`, `shimmer` (steerable-enabled voices)

Accent examples: `"Mexican Spanish"`, `"neutral Spanish"`, or auto-detect based on text language

---

## Provider Detection

The `/api/tts/providers` endpoint returns which providers are configured:

```bash
curl http://localhost:7001/api/tts/providers | jq
```

Response:
```json
{
  "providers": {
    "azure-openai": true,
    "openai": true,
    "openai_steerable": true
  }
}
```

---

## Auto-Detection Strategy

The system automatically selects the best provider based on:
1. **Spanish text + steerable voice (alloy/echo/shimmer)** → Use `openai-steerable` with Mexican accent
2. **Explicit provider specified** → Use requested provider
3. **Default** → Use `openai` (standard OpenAI API)

---

## Troubleshooting

**"At least one TTS provider must be configured"**
- Set one of: `OPENAI_API_KEY` or `AZURE_OPENAI_TTS_*` variables
- For Azure: need both endpoint and API key

**"OpenAI API error 401"**
- Verify `OPENAI_API_KEY` is correct
- Check API key permissions at https://platform.openai.com/api-keys

**"Azure OpenAI endpoint not configured"**
- Ensure both `AZURE_OPENAI_TTS_ENDPOINT` and `AZURE_OPENAI_TTS_API_KEY` are set
- Endpoint should include the full URL (e.g., `https://resource.openai.azure.com`)

**HTTP 500 errors during synthesis**
- Check logs: `tail -f /tmp/backend.log` (or your log location)
- Verify API credentials are correct
- Test endpoint directly with `curl`

**Rate limiting (429 responses)**
- Implement retry logic in your client
- Check API provider rate limits and quotas

---

## Voice Examples

**nova** (Default, recommended for medical context)
- Warm, expressive female voice
- Good for accessible/friendly tone
- Recommended as default voice

**alloy**
- Neutral, versatile voice
- Good for professional contexts
- Supports Mexican Spanish accent with steerable TTS

**shimmer**
- Clear, bright female voice
- Good for clear pronunciation
- Supports Mexican Spanish accent with steerable TTS

---

Updated: 2025-12-23 (Removed Azure Speech Services, simplified to OpenAI-only)
