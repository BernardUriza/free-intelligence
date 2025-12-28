# Azure OpenAI Unified Resource Deployment Guide

**Status:** ✅ Deployed
**Date:** 2025-12-24
**Resource:** `aurity-openai-whisper` (North Central US)
**Approach:** Option 1 - Single unified resource with TTS + Whisper deployments

---

## 📋 What Was Deployed

### Azure Resource
- **Name:** `aurity-openai-whisper`
- **Region:** North Central US
- **Endpoint:** `https://northcentralus.api.cognitive.microsoft.com/`
- **Kind:** OpenAI

### Deployments

#### 1. Text-to-Speech (TTS)
- **Deployment Name:** `tts-hd`
- **Model:** `tts-hd` (OpenAI TTS with HD quality)
- **Version:** `001`
- **Voices:** nova (default), alloy, shimmer
- **API Version:** `2025-03-01-preview`
- **Capabilities:** `audioSpeech`

#### 2. Speech-to-Text (Whisper)
- **Deployment Name:** `whisper`
- **Model:** `whisper` (Azure OpenAI Whisper)
- **Version:** `001`
- **Languages:** All supported languages + translation to English
- **API Version:** `2024-02-01`
- **Capabilities:** `audioTranscriptions`, `audioTranslations`

---

## 🚀 Deployment Steps Completed

```bash
# 1. Create resource in North Central US
az cognitiveservices account create \
  --resource-group aurity-prod \
  --name aurity-openai-whisper \
  --kind OpenAI \
  --location northcentralus \
  --sku s0 \
  --custom-domain aurity-openai-whisper

# 2. Deploy TTS model
az cognitiveservices account deployment create \
  --resource-group aurity-prod \
  --name aurity-openai-whisper \
  --deployment-name tts-hd \
  --model-name tts-hd \
  --model-version "001" \
  --model-format OpenAI \
  --sku-capacity 1 \
  --sku-name Standard

# 3. Deploy Whisper model
az cognitiveservices account deployment create \
  --resource-group aurity-prod \
  --name aurity-openai-whisper \
  --deployment-name whisper \
  --model-name whisper \
  --model-version "001" \
  --model-format OpenAI \
  --sku-capacity 1 \
  --sku-name Standard
```

---

## 🔑 Configuration

### Environment Variables Required

```bash
# Core Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://northcentralus.api.cognitive.microsoft.com/
AZURE_OPENAI_API_KEY=<YOUR_API_KEY>

# TTS Configuration
AZURE_OPENAI_TTS_DEPLOYMENT=tts-hd
AZURE_OPENAI_TTS_API_VERSION=2025-03-01-preview

# Whisper STT Configuration
AZURE_OPENAI_WHISPER_DEPLOYMENT=whisper
AZURE_OPENAI_WHISPER_API_VERSION=2024-02-01
```

### How to Get the API Key

```bash
az cognitiveservices account keys list \
  --resource-group aurity-prod \
  --name aurity-openai-whisper \
  --query "key1" \
  -o tsv
```

---

## 🧪 Testing the Deployment

### Test TTS (Text-to-Speech)

```bash
curl -X POST \
  'https://northcentralus.api.cognitive.microsoft.com/openai/deployments/tts-hd/audio/speech?api-version=2025-03-01-preview' \
  -H 'api-key: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "input": "Hello, this is a test of the text-to-speech system",
    "voice": "nova",
    "response_format": "mp3"
  }' \
  --output test-audio.mp3

file test-audio.mp3  # Should show: Audio file with ID3 version
```

### Test Whisper (Speech-to-Text)

```bash
# Create a small test audio file (or use existing)
curl -X POST \
  'https://northcentralus.api.cognitive.microsoft.com/openai/deployments/whisper/audio/transcriptions?api-version=2024-02-01' \
  -H 'api-key: YOUR_API_KEY' \
  -F "file=@test-audio.mp3" \
  -F "model=whisper-1" \
  -F "language=en"
```

---

## ✅ Verification Checklist

- [x] Resource created in North Central US region
- [x] TTS deployment (`tts-hd`) created and working
- [x] Whisper deployment (`whisper`) created and working
- [x] Both deployments use same endpoint and API key
- [x] Documentation updated (README_STT.md, README_TTS.md)
- [x] .env.example updated with unified configuration
- [x] Backend code verified to work with unified resource
- [ ] Update production deployment secrets
- [ ] Test full STT → LLM → TTS pipeline
- [ ] Decommission old aurity-openai-prod resource (optional)

---

## 📊 Architecture Diagram

```
                    North Central US
                  aurity-openai-whisper
                          |
            ______________+______________
           /                              \
           |                              |
      [whisper]                      [tts-hd]
    Deployment                       Deployment
         |                               |
         |                               |
      Speech-to-Text               Text-to-Speech
    (Whisper Model)              (OpenAI TTS-HD)
         |                               |
    Transcription               Voice Synthesis
   (All Languages)           (nova/alloy/shimmer)

  Shared Credentials:
  - Endpoint: https://northcentralus.api.cognitive.microsoft.com/
  - API Key: Single key for both services
```

---

## 🔄 Migration Steps (Next)

### For Development
1. Update `.env` with API key from unified resource
2. Set `ENVIRONMENT=development`
3. Start backend with: `PYTHONPATH=backend/src uvicorn backend.app.main:app --reload --port 7001`
4. Test STT endpoint: `/api/workflows/aurity/stream` (audio upload)
5. Test TTS endpoint: `/api/tts/synthesize` (text → speech)

### For Production
1. Store API key in deployment secrets (DigitalOcean App Platform, K8s, etc.)
2. Set environment variables on all production workers
3. Restart backend services
4. Verify with production health check: `curl https://app.aurity.io/api/health`

---

## ⚠️ Important Notes

### Region-Specific Constraints
- ✅ North Central US: Supports both TTS and Whisper ✓
- ✅ West Europe: Supports both TTS and Whisper ✓
- ⚠️ Other regions may support only one or the other

### Cost Optimization
- Both TTS and Whisper share the same resource
- Single API Key to manage
- Consolidated billing under one resource
- Simpler monitoring and troubleshooting

### Decommissioning Old Resource (Optional)
If the old `aurity-openai-prod` resource (West US) was used for TTS only:

```bash
# List old resource
az cognitiveservices account show \
  --resource-group aurity-prod \
  --name aurity-openai-prod

# Delete when ready
az cognitiveservices account delete \
  --resource-group aurity-prod \
  --name aurity-openai-prod \
  --yes
```

---

## 🔗 References

- [Azure OpenAI Models](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models)
- [Whisper Deployment Guide](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/whisper-quickstart)
- [TTS Setup Guide](../backend/README_TTS.md)
- [STT Setup Guide](../backend/README_STT.md)

---

## 📝 Deployment Commit

**Commit Hash:** `170f648`
**Message:** `feat(azure): deploy unified Azure OpenAI resource with TTS + Whisper STT`
**Date:** 2025-12-24

```bash
git log --oneline | head -1
# 170f648 feat(azure): deploy unified Azure OpenAI resource with TTS + Whisper STT
```

---

## 🆘 Troubleshooting

### Issue: "Invalid API key or endpoint"
- Verify API key matches resource `aurity-openai-whisper`
- Check endpoint region: `northcentralus.api.cognitive.microsoft.com`
- Ensure environment variables are correctly set

### Issue: "Deployment not found"
- Verify deployment names: `tts-hd` (for TTS), `whisper` (for STT)
- List deployments: `az cognitiveservices account deployment list -g aurity-prod -n aurity-openai-whisper`

### Issue: "Model not available in region"
- This was the reason for choosing North Central US
- Both TTS and Whisper are available there
- Other regions might not support both models

### Issue: Rate Limiting (429)
- Azure Whisper allows 3 requests per minute by default
- Implement exponential backoff retry logic
- Check deployment capacity settings if high volume needed

---

**Status: READY FOR PRODUCTION DEPLOYMENT** ✅
