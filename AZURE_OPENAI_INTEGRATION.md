# Azure OpenAI Provider Integration Guide

**Last Updated:** 2025-11-15
**Status:** ✅ Fully Integrated & Tested
**Authors:** Bernard Uriza Orozco

## Overview

Azure OpenAI (GPT-4, GPT-4o) has been integrated into Free Intelligence as an LLM provider alongside Claude and Ollama. This guide covers setup, usage, and configuration.

## Provider Architecture

Free Intelligence uses a **provider-agnostic** abstraction layer (`backend/providers/llm.py`) that supports multiple LLM providers:

```
┌─────────────────────────────────────┐
│    llm_generate() - Public API      │
│  (provider-agnostic entry point)    │
└────────────────┬────────────────────┘
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
  ClaudeProvider │    AzureOpenAIProvider
                 ▼
             OllamaProvider
```

### Supported Providers

| Provider | Type | Status | Use Case |
|----------|------|--------|----------|
| **Claude** | Cloud | ✅ Production | Primary LLM (best quality) |
| **Azure OpenAI** | Cloud | ✅ Production | Cost-effective alternative (GPT-4o) |
| **Ollama** | Local | ✅ Production | Offline-first, privacy-focused |

## Setup Instructions

### 1. Configure Environment Variables

Add to `.env.local` or export in your shell:

```bash
# Azure OpenAI Credentials (from demo account)
export AZURE_OPENAI_ENDPOINT="https://csp-eastus2-uat-aoai1.openai.azure.com/"
export AZURE_OPENAI_KEY="2a48df168ba44526a8f3cf71ae280d3f"
```

**Security Note:** Store API keys in environment variables, **never** in code or version control.

### 2. Install Dependencies

Azure OpenAI requires `aiohttp` for async HTTP requests:

```bash
# Already in requirements.txt, but ensure installed:
pip install aiohttp>=3.9.0
```

### 3. Policy Configuration

Azure is already configured in `/backend/config/fi.policy.yaml`:

```yaml
llm:
  providers:
    azure:
      model: gpt-4o                    # Model name
      deployment: gpt-4o               # Azure deployment name
      api_version: "2024-02-15-preview"  # API version
      timeout_seconds: 30              # Request timeout
      max_tokens: 1024                 # Max output tokens
      temperature: 0.7                 # Sampling temperature
```

## Usage

### Using the Public API

```python
from backend.providers.llm import llm_generate

# Option 1: Use policy defaults (recommended)
response = llm_generate(
    "What are the symptoms of influenza?",
    provider="azure"
)
print(f"Response: {response.content}")
print(f"Model: {response.model}")
print(f"Cost: ${response.cost_usd:.6f}")
print(f"Latency: {response.latency_ms:.2f}ms")

# Option 2: Override parameters
response = llm_generate(
    "List 3 causes of fever",
    provider="azure",
    model="gpt-4o",
    deployment="gpt-4o",
    temperature=0.5,  # More deterministic
    max_tokens=500    # Longer response
)
```

### Direct Provider Usage

```python
from backend.providers.llm import get_provider

# Get Azure provider instance
azure = get_provider("azure")

# Generate text
response = azure.generate(
    "Explain COVID-19 symptoms",
    temperature=0.3,  # Clinical accuracy
    max_tokens=200
)

print(f"Content: {response.content}")
print(f"Tokens: {response.tokens_used}")
print(f"Cost: ${response.cost_usd:.6f}")
```

## Response Format

All providers return a unified `LLMResponse` object:

```python
@dataclass
class LLMResponse:
    content: str              # Generated text
    model: str               # Model name (gpt-4o)
    provider: str            # Provider name (azure)
    tokens_used: int         # Total tokens
    cost_usd: Optional[float] # Cost in USD ($0.000752)
    latency_ms: Optional[float] # Latency in milliseconds
    metadata: Optional[dict] # Provider-specific metadata
```

### Example Response

```python
LLMResponse(
    content="Influenza commonly presents with high fever, severe cough...",
    model="gpt-4o",
    provider="azure",
    tokens_used=91,
    cost_usd=0.000752,
    latency_ms=1501.71,
    metadata={
        "input_tokens": 12,
        "output_tokens": 79,
        "deployment": "gpt-4o",
        "finish_reason": "stop"
    }
)
```

## Available Models

The demo Azure subscription has these models available:

### Active Deployments
- **gpt-4o** - GPT-4 Optimized (recommended) - $2.50/$10 per 1M tokens
- **gpt-4** - GPT-4 base - $30/$60 per 1M tokens

### Not Deployed (use Deepgram instead)
- whisper-001 (STT not available)

## Pricing

### Cost Calculation

Azure OpenAI pricing is per 1 million tokens:

| Model | Input | Output | Notes |
|-------|-------|--------|-------|
| **gpt-4o** | $2.50 | $10.00 | Recommended (fastest, cheapest) |
| **gpt-4** | $30.00 | $60.00 | Higher quality, expensive |

### Example Costs

- Clinical consultation (500 tokens): ~$0.01
- Full session analysis (5000 tokens): ~$0.05-$0.10
- Monthly (100,000 tokens): ~$1.00

## Configuration Files

### 1. Backend Provider Class
**File:** `backend/providers/llm.py`

New class `AzureOpenAIProvider` implements:
- `__init__()` - Initialize with Azure credentials
- `generate()` - Synchronous text generation (uses asyncio internally)
- `_generate_async()` - Async Azure OpenAI API call
- `embed()` - Fallback to sentence-transformers (Azure doesn't support embeddings)
- `get_provider_name()` - Return "azure"

### 2. LLM Configuration
**File:** `config/llm.yaml`

Defines default parameters:
```yaml
azure:
  model: "gpt-4o"
  deployment: "gpt-4o"
  api_version: "2024-02-15-preview"
  timeout_seconds: 30
  max_tokens: 1024
  temperature: 0.7
```

### 3. Policy Configuration
**File:** `backend/config/fi.policy.yaml`

Policy controls routing and fallback:
```yaml
llm:
  primary_provider: claude    # Default provider
  fallback_provider: ollama   # If primary fails
  providers:
    azure:                    # Azure config (loaded here too)
      model: gpt-4o
      deployment: gpt-4o
      # ... etc
```

## Testing

### Quick Test

```bash
cd /Users/bernardurizaorozco/Documents/free-intelligence
python3 -c "
from backend.providers.llm import llm_generate
response = llm_generate('Say hello in one word', provider='azure', max_tokens=10)
print(f'✅ Response: {response.content}')
print(f'💰 Cost: \${response.cost_usd:.6f}')
"
```

### Full Test Suite

```bash
python3 /tmp/test_azure_provider.py
# Output: 3/3 tests passed ✅
```

## Error Handling

### Common Issues

#### 1. ImportError: aiohttp not installed
```
Error: aiohttp library not installed. Install with: pip install aiohttp
```
**Solution:** Install aiohttp
```bash
pip install aiohttp>=3.9.0
```

#### 2. ValueError: AZURE_OPENAI_ENDPOINT not set
```
Error: AZURE_OPENAI_ENDPOINT environment variable not set
```
**Solution:** Export credentials
```bash
export AZURE_OPENAI_ENDPOINT="https://csp-eastus2-uat-aoai1.openai.azure.com/"
export AZURE_OPENAI_KEY="your-key-here"
```

#### 3. DeploymentNotFound Error
```json
{
  "error": {
    "code": "DeploymentNotFound",
    "message": "The API deployment for this resource does not exist."
  }
}
```
**Solution:** Use available deployments (gpt-4o, gpt-4)

## Comparing Providers

### Performance & Cost Comparison

| Metric | Claude | Azure (GPT-4o) | Ollama |
|--------|--------|---|--------|
| **Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Speed** | 1-3s | 1-2s | 5-30s |
| **Cost (per 1M tokens)** | $3-15 | $2.50-10 | $0 (local) |
| **Offline** | ❌ | ❌ | ✅ |
| **Privacy** | External API | External API | Local only |
| **API Latency** | ~500ms avg | ~1500ms avg | N/A |

### When to Use

- **Claude:** Best quality, primary choice for medical consultation
- **Azure (GPT-4o):** Cost-effective alternative, good balance
- **Ollama:** Privacy-critical, offline operation, resource-constrained

## Architecture Notes

### Provider Pattern

The provider abstraction follows these design principles:

1. **Single Responsibility:** Each provider handles one LLM service
2. **Consistent Interface:** All providers implement `LLMProvider` ABC
3. **Independent Config:** Providers load config from policy/env
4. **Error Isolation:** Provider errors don't cascade
5. **Async-Safe:** Sync API with internal async support (AzureOpenAIProvider)

### Request Flow

```
User Code
    ↓
llm_generate() [public API]
    ↓
get_policy_loader() → Load fi.policy.yaml
    ↓
get_provider("azure") → Create AzureOpenAIProvider
    ↓
provider.generate(prompt, **kwargs)
    ↓
asyncio.run(_generate_async()) → HTTP request to Azure
    ↓
Parse response → LLMResponse
    ↓
Return to user
```

## Future Enhancements

- [ ] Streaming responses (SSE)
- [ ] Token count estimation
- [ ] Retry logic with exponential backoff
- [ ] Rate limiting per provider
- [ ] Cost tracking & budgeting
- [ ] Provider health checks
- [ ] Metrics collection (latency, errors, costs)

## See Also

- **LLM Provider Reference:** `AZURE_OPENAI_CURL_REFERENCE.md`
- **Curl Examples:** Test endpoints manually
- **Code:** `backend/providers/llm.py` - Main implementation
- **Config:** `backend/config/fi.policy.yaml` - Policy configuration

## Support

For issues or questions about Azure OpenAI integration:

1. Check error logs: `logs/backend.log`
2. Review curl reference: `AZURE_OPENAI_CURL_REFERENCE.md`
3. Inspect policy: `backend/config/fi.policy.yaml`
4. Test directly: `python3 /tmp/test_azure_provider.py`

---

**Integration Date:** 2025-11-15
**Python Compatibility:** 3.9+
**Status:** Production Ready ✅
