# Azure OpenAI Shared Resource Configuration

## 🎯 Overview

Free-intelligence (Aurity) shares the **same Azure OpenAI resource** as Portfolio backend for cost optimization and unified management.

**Resource**: `bernarduriza-openai`
**Resource Group**: `rg-vhouse-prod`
**Region**: `eastus`
**Endpoint**: `https://eastus.api.cognitive.microsoft.com/`

---

## 🔑 Shared Credentials (All Projects)

```bash
# Same credentials for Portfolio, VHouse, and Aurity (free-intelligence)
AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_OPENAI_API_KEY=4NwU6IBHTPAsi7dBkPG8akXjb730fglZOq4ks2AQlxJ0mmmX4lyGJQQJ99CAACYeBjFXJ3w3AAABACOG0Jd3
```

---

## 📦 Available Deployments

### 1. GPT-5 mini (Chat/LLM)
```bash
AZURE_OPENAI_GPT_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_GPT_API_VERSION=2024-12-01-preview
```

**Used by:**
- Portfolio backend (AI Catalyst chat)
- Can be used by Aurity for medical consultation chat

### 2. TTS (Text-to-Speech)
```bash
AZURE_OPENAI_TTS_DEPLOYMENT=tts-hd
AZURE_OPENAI_TTS_API_VERSION=2025-03-01-preview
```

**Used by:**
- Aurity (patient communication)

### 3. Whisper (Speech-to-Text)
```bash
AZURE_OPENAI_WHISPER_DEPLOYMENT=whisper
AZURE_OPENAI_WHISPER_API_VERSION=2024-02-01
```

**Used by:**
- Aurity (medical transcription)

---

## 🚀 Configuration for Free-Intelligence (Aurity)

### Azure Container Apps Configuration

Aurity backend runs on Azure Container Apps. Secrets are managed via Azure Key Vault (`aurity-secrets`), accessed through Managed Identity.

```bash
# Secrets are stored in Azure Key Vault, NOT environment variables
# To update a secret:
az keyvault secret set --vault-name aurity-secrets \
  --name "AZURE-OPENAI-API-KEY" \
  --value "<key>"

# Container Apps reads secrets via Managed Identity at startup
# No SSH, no manual .env files needed
```

---

## 🧪 Testing

### Test TTS
```bash
curl -X POST https://app.aurity.io/api/v1/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test of Azure OpenAI TTS",
    "voice": "nova",
    "provider": "azure-openai"
  }'
```

### Test Whisper (STT)
```bash
curl -X POST https://app.aurity.io/api/v1/stt/transcribe \
  -F "audio=@test.wav" \
  -F "provider=azure-whisper"
```

### Test GPT-5 mini (if implemented)
```bash
curl -X POST https://app.aurity.io/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the symptoms of diabetes?",
    "provider": "azure-openai"
  }'
```

---

## 📊 Usage Monitoring

All projects share the same Azure OpenAI quota:

**Azure Portal** → OpenAI Services → `bernarduriza-openai` → Metrics

Monitor:
- **Token Usage**: Track per deployment (GPT-5, TTS, Whisper)
- **Rate Limits**: Shared across all projects
- **Costs**: Single billing for all projects

**Cost Estimate:**
- Portfolio GPT-5: ~$3-5/day
- Aurity TTS: ~$1-2/day
- Aurity Whisper: ~$0.50-1/day
- **Total**: ~$150-250/month

---

## ⚠️ Important Notes

1. **Shared Rate Limits**: All projects share quota. High usage in one affects others.
2. **Security**: API key is in environment variables only, never committed to git
3. **Alternative Providers**: Aurity also supports Deepgram (STT) and Ollama (LLM) as fallbacks
4. **Region**: East US chosen for best availability across GPT-5 mini + TTS + Whisper

---

## 🔗 Code Integration

### Python (Aurity)

Already integrated! Code in:
- `backend/src/fi_tts/services/tts_azure_openai.py`
- `backend/providers/stt.py` (Whisper)
- `backend/providers/llm.py` (GPT-5 provider)

Variables are read from `.env` automatically via `python-dotenv`.

### Java/Spring (Portfolio)

Already integrated! Code in:
- `src/main/java/com/portfolio/config/AzureOpenAIConfigValidator.java`
- See `AZURE-OPENAI-SETUP.md` in portfolio-spring repo

---

## 📝 Related Documentation

- **Portfolio Setup**: `/Users/bernardurizaorozco/Documents/portfolio-spring/AZURE-OPENAI-SETUP.md`
- **VHouse Setup**: `/tmp/AURITY-VHOUSE-AZURE-OPENAI-SETUP.md`
- **Azure Portal**: https://portal.azure.com → OpenAI Services → bernarduriza-openai

---

**Last Updated**: 2026-01-26
**Maintained By**: Bernard Uriza
