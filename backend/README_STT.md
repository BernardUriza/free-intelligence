STT (Speech-to-Text) - Azure OpenAI Whisper

This project uses **Azure OpenAI Whisper** for speech-to-text transcription.

---

## 🚀 Setup

### Prerequisites

**Azure OpenAI Whisper Deployment:**
- Azure subscription with Azure OpenAI resource
- Whisper model deployed in a [supported region](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models?tabs=standard-audio#standard-deployment-regional-models-by-endpoint)
  - **Supported regions:** North Central US, West Europe
- Deployment name: `whisper` (default, configurable)

### Environment Variables

```bash
# Shared Azure OpenAI credentials (same as TTS)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>

# Whisper STT configuration
AZURE_OPENAI_WHISPER_DEPLOYMENT=whisper        # Deployment name (default)
AZURE_OPENAI_WHISPER_API_VERSION=2024-02-01    # API version (official)
```

### Local Development

```bash
# 1. Set environment variables
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_WHISPER_DEPLOYMENT="whisper"

# 2. Start backend
PYTHONPATH=backend/src uvicorn backend.app.main:app --reload --port 7001
```

### Production

Add to your deployment secrets:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_WHISPER_DEPLOYMENT` (optional)
- `AZURE_OPENAI_WHISPER_API_VERSION` (optional)

---

## 📝 API Usage

### Using Aurity STT Workflow (Recommended)

```bash
curl -X POST 'http://localhost:7001/api/workflows/aurity/stream' \
  -H 'Authorization: Bearer <your_jwt_token>' \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @audio.wav
```

The workflow automatically uses Azure Whisper to transcribe audio.

### Direct Azure Whisper API

```bash
curl -X POST \
  "https://your-resource.openai.azure.com/openai/deployments/whisper/audio/transcriptions?api-version=2024-02-01" \
  -H "api-key: $AZURE_OPENAI_API_KEY" \
  -F "file=@audio.wav" \
  -F "language=es"
```

---

## 🗣️ Supported Languages

Whisper supports **all languages** for transcription:

| Language | Code | Example |
|----------|------|---------|
| Spanish | es | "Hola, buenos días" |
| English | en | "Hello, good morning" |
| French | fr | "Bonjour, comment allez-vous?" |
| German | de | "Guten Morgen" |
| Portuguese | pt | "Olá, bom dia" |
| ... | ... | [Full list](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=speech-to-text#spoken-languages) |

### Translation to English

Whisper can also **translate any language to English**:

```python
# Python example
transcription = client.audio.transcriptions.create(
    file=open("spanish_audio.wav", "rb"),
    model="whisper",
    language="es",
    # This would translate to English (if translation feature is enabled)
)
```

---

## ⚙️ Configuration

### Deployment Name

By default uses `whisper`, but you can customize:

```bash
export AZURE_OPENAI_WHISPER_DEPLOYMENT="my-whisper-deployment"
```

### API Version

Default: `2024-02-01` (current official release)

```bash
export AZURE_OPENAI_WHISPER_API_VERSION="2024-08-01-preview"  # Preview version
```

---

## 📊 Limitations & Considerations

| Aspect | Details |
|--------|---------|
| **File size limit** | 25 MB |
| **Supported formats** | WAV, WebM, MP3, MP4, MPEG, FLAC, OGG, Opus, AAC |
| **Request timeout** | 30 seconds (configurable) |
| **Rate limit** | 3 requests per minute (built-in backoff) |
| **Larger files** | Use [Batch Transcription API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-transcription-create?view=foundry-classic) |

---

## 🔍 Troubleshooting

**"AZURE_OPENAI_ENDPOINT environment variable not set"**
- Ensure you set `AZURE_OPENAI_ENDPOINT` in `.env`
- Format: `https://your-resource.openai.azure.com/`

**"Azure Whisper endpoint has been removed by Microsoft"**
- Old Azure Speech Services endpoint deprecated
- Use Azure OpenAI Whisper instead (this provider)
- Verify deployment name is `whisper`

**"Timeout waiting for response"**
- Default timeout: 30 seconds
- Large files (>10 MB) may timeout
- Use batch transcription for large files

**"Invalid API key or endpoint"**
- Verify credentials in Azure Portal
- Check region supports Whisper (North Central US, West Europe)
- Ensure deployment exists with name `whisper`

**"413 Payload Too Large"**
- File exceeds 25 MB limit
- Split into smaller files or use batch API

---

## 🔗 Azure OpenAI Architecture

Your unified stack:

```
🎙️ Audio
   ↓
[Azure OpenAI Whisper] ← STT (this file)
   ↓
📝 Transcribed Text
   ↓
[LLM: Qwen3/Claude/Azure OpenAI]
   ↓
💬 Response Text
   ↓
[Azure OpenAI TTS] ← (see README_TTS.md)
   ↓
🔊 Audio Response
```

All components use the same Azure OpenAI resource (`AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY`).

---

## 📚 References

- [Azure OpenAI Whisper Documentation](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/whisper-overview)
- [Quickstart Guide](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whisper-quickstart)
- [Batch Transcription API](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/batch-transcription-create)
- [Language Support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=speech-to-text#spoken-languages)

---

Updated: 2025-12-24 (Azure OpenAI Whisper STT - unified with TTS)
