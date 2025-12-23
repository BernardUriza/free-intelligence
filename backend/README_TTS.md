TTS (Text-to-Speech) - Azure OpenAI

This project uses **Azure OpenAI TTS** for speech synthesis.

Supported voices: `alloy`, `nova` (default), `shimmer`

---

## Setup

### Local Development

Environment variables:

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

### Production

Add these to your deployment secrets (DigitalOcean, Docker Swarm, Kubernetes, or CI env):
- `AZURE_OPENAI_TTS_ENDPOINT`
- `AZURE_OPENAI_TTS_API_KEY`
- `AZURE_OPENAI_TTS_API_VERSION`
- `AZURE_OPENAI_TTS_DEPLOYMENT`

The system will auto-detect and use Azure OpenAI TTS when configured.

---

## Provider Status

Check if TTS is configured with:

```bash
curl http://localhost:7001/api/tts/providers | jq
```

Response:
```json
{
  "providers": {
    "azure-openai": true
  }
}
```

---

## Troubleshooting

**"TTS provider must be configured in production"**
- Set `AZURE_OPENAI_TTS_ENDPOINT` and `AZURE_OPENAI_TTS_API_KEY`
- Both endpoint and API key are required

**"Azure OpenAI endpoint not configured"**
- Ensure `AZURE_OPENAI_TTS_ENDPOINT` and `AZURE_OPENAI_TTS_API_KEY` are set
- Endpoint format: `https://your-resource.openai.azure.com`
- Verify credentials in Azure Portal

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

Updated: 2025-12-24 (Azure OpenAI TTS only - removed OpenAI direct and OpenAI Steerable)
