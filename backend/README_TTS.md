TTS (Multi-Provider) - Quick Setup

This project supports multiple TTS providers:
- **Azure OpenAI TTS** - OpenAI models deployed on your Azure infrastructure
- **Azure Speech Services** - Native Spanish (Mexico) neural voices
- **OpenAI TTS** - Standard OpenAI models (api.openai.com)

If you get an error like:

{"detail":"TTS_INVALID_REQUEST","message":"Azure Speech Services API key not configured"}

it means the backend is not configured with the required environment variables for any TTS provider.

Local development (bash/zsh):

```bash
export AZURE_SPEECH_KEY="<YOUR_AZURE_TTS_KEY_HERE>"
export AZURE_SPEECH_REGION="westus"
# Start backend (example):
PYTHONPATH=backend/src uvicorn backend.app.main:app --reload --port 7001
```

CI / Production:

- Add `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` to your deployment secrets (DigitalOcean, Docker Swarm, Kubernetes, or CI env).
- The application will now return HTTP 400 with a helpful message when the key is missing during a TTS request.

Quick curl test (after starting backend):

```bash
curl -v -X POST 'http://localhost:7001/api/tts/synthesize' \
  -H 'Content-Type: application/json' \
  --data-raw '{"text":"Hola mundo","voice":"es-MX-DaliaNeural","provider":"azure","response_format":"mp3"}'
```

Expected success: binary audio streamed back with `Content-Type: audio/mpeg`.
Expected failure (no key): HTTP 400 and message explaining how to set `AZURE_SPEECH_KEY`.

---

## Azure OpenAI TTS

If you have OpenAI models deployed on your Azure infrastructure:

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

Available voices (aligned with Aurity): alloy, nova (default), shimmer

Backward compatibility: If you use old variable names (`AZURE_TTS_ENDPOINT`, `AZURE_TTS_API_KEY`), they will work automatically as fallback.

CI / Production:

- Add `AZURE_OPENAI_TTS_ENDPOINT`, `AZURE_OPENAI_TTS_API_KEY`, `AZURE_OPENAI_TTS_API_VERSION`, and `AZURE_OPENAI_TTS_DEPLOYMENT` to your deployment secrets.
- The system will auto-detect and use Azure OpenAI TTS when configured.

---

## Provider Detection

The `/api/tts/providers` endpoint returns which providers are available:

```bash
curl http://localhost:7001/api/tts/providers | jq
```

Response:
```json
{
  "providers": {
    "azure-openai": true,
    "azure": false,
    "openai": true,
    "openai_steerable": true
  }
}
```

---

## Troubleshooting

**"Azure Speech Services API key not configured"**
- Set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` for Azure Speech Services
- OR set `AZURE_OPENAI_TTS_*` variables for Azure OpenAI TTS
- OR set `OPENAI_API_KEY` for standard OpenAI TTS

**"Azure OpenAI endpoint not configured"**
- Ensure both `AZURE_OPENAI_TTS_ENDPOINT` and `AZURE_OPENAI_TTS_API_KEY` are set
- Endpoint should include the full URL (e.g., `https://resource.openai.azure.com`)

**HTTP 500 errors during synthesis**
- Check logs: `tail -f /tmp/backend.log` (or your log location)
- Verify API credentials are correct
- Test endpoint directly: `curl -H "api-key: $AZURE_OPENAI_TTS_API_KEY" $AZURE_OPENAI_TTS_ENDPOINT`

**Rate limiting**
- Azure imposes rate limits. Check Azure docs for your tier.
- Implement retry logic in your client for 429 responses.
