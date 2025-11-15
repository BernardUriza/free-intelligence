# Azure OpenAI API - Curl Reference Guide

## Configuration

```bash
# Set environment variables
export AZURE_ENDPOINT="https://csp-eastus2-uat-aoai1.openai.azure.com/"
export AZURE_API_KEY="2a48df168ba44526a8f3cf71ae280d3f"
export AZURE_API_VERSION="2024-02-15-preview"

# Available Deployments
# - gpt-4o (chat_completion, inference ✅)
# - gpt-4 (chat_completion, inference ✅)
# - whisper-001 (transcription) ❌ Not deployed
```

## 1. Chat Completions (gpt-4o)

### Basic Request
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_API_KEY" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }' \
  "${AZURE_ENDPOINT}openai/deployments/gpt-4o/chat/completions?api-version=${AZURE_API_VERSION}"
```

### Response Example
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking. How can I assist you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "completion_tokens": 22,
    "prompt_tokens": 12,
    "total_tokens": 34
  }
}
```

## 2. Medical Consultation (System Prompt)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_API_KEY" \
  -d '{
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful medical assistant specialized in telemedicine. Provide accurate, concise clinical guidance. Always recommend professional consultation for serious symptoms."
      },
      {
        "role": "user",
        "content": "What are the main symptoms of influenza?"
      }
    ],
    "temperature": 0.5,
    "max_tokens": 500
  }' \
  "${AZURE_ENDPOINT}openai/deployments/gpt-4o/chat/completions?api-version=${AZURE_API_VERSION}"
```

## 3. Streaming Responses

```bash
# Note: Returns server-sent events (SSE)
curl -X POST \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_API_KEY" \
  -d '{
    "messages": [{"role": "user", "content": "List 3 cold symptoms"}],
    "stream": true,
    "max_tokens": 200
  }' \
  "${AZURE_ENDPOINT}openai/deployments/gpt-4o/chat/completions?api-version=${AZURE_API_VERSION}"

# Output format (SSE):
# data: {"choices":[{"delta":{"content":"Hello"}}]}
# data: {"choices":[{"delta":{"content":" world"}}]}
# data: [DONE]
```

## 4. Multi-Turn Conversation

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_API_KEY" \
  -d '{
    "messages": [
      {"role": "user", "content": "I have a fever of 38.5°C"},
      {"role": "assistant", "content": "A fever of 38.5°C is considered moderate. Common causes include viral infections. Do you have other symptoms?"},
      {"role": "user", "content": "Yes, also a sore throat"}
    ],
    "temperature": 0.7,
    "max_tokens": 300
  }' \
  "${AZURE_ENDPOINT}openai/deployments/gpt-4o/chat/completions?api-version=${AZURE_API_VERSION}"
```

## 5. Structured Output (JSON Mode)

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "api-key: $AZURE_API_KEY" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Extract patient vitals from: Temperature 37.5°C, Heart rate 80 bpm, BP 120/80. Return as JSON."
      }
    ],
    "temperature": 0,
    "max_tokens": 200
  }' \
  "${AZURE_ENDPOINT}openai/deployments/gpt-4o/chat/completions?api-version=${AZURE_API_VERSION}"
```

## 6. Using Python (for Backend Integration)

```python
import aiohttp
import json

async def query_azure_openai(messages, model="gpt-4o"):
    """Query Azure OpenAI with async/await support"""

    url = f"{AZURE_ENDPOINT}openai/deployments/{model}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_API_KEY
    }

    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{url}?api-version={AZURE_API_VERSION}",
            headers=headers,
            json=payload
        ) as resp:
            return await resp.json()

# Usage
messages = [
    {"role": "system", "content": "You are a medical assistant."},
    {"role": "user", "content": "What causes headaches?"}
]

response = await query_azure_openai(messages)
print(response["choices"][0]["message"]["content"])
```

## 7. Error Handling

```bash
# Common errors and solutions:

# 1. DeploymentNotFound - Model not deployed in region
# Response:
{
  "error": {
    "code": "DeploymentNotFound",
    "message": "The API deployment for this resource does not exist."
  }
}
# Solution: Use available deployments (gpt-4o, gpt-4)

# 2. InvalidRequestError - Malformed JSON
# Solution: Validate JSON with: curl ... | jq '.'

# 3. AuthenticationError - Wrong API key
# Response:
{
  "error": {
    "code": "Unauthorized",
    "message": "Invalid credentials"
  }
}
# Solution: Check AZURE_API_KEY export
```

## 8. Performance Tips

| Parameter | Use Case | Value |
|-----------|----------|-------|
| `temperature` | Deterministic (clinical) | 0 |
| `temperature` | Balanced (conversations) | 0.5-0.7 |
| `temperature` | Creative | 0.9-1.0 |
| `max_tokens` | Short responses | 100-200 |
| `max_tokens` | Clinical notes | 500-1000 |
| `stream` | Real-time UI feedback | `true` |
| `stream` | Batch processing | `false` |

## 9. Testing Script

```bash
#!/bin/bash
# Save as: test_azure_openai.sh

AZURE_ENDPOINT="https://csp-eastus2-uat-aoai1.openai.azure.com/"
API_KEY="2a48df168ba44526a8f3cf71ae280d3f"
API_VERSION="2024-02-15-preview"

test_chat() {
  echo "Testing GPT-4o..."
  RESPONSE=$(curl -s --max-time 10 -X POST \
    -H "Content-Type: application/json" \
    -H "api-key: $API_KEY" \
    -d '{"messages":[{"role":"user","content":"Say hello"}],"max_tokens":50}' \
    "${AZURE_ENDPOINT}openai/deployments/gpt-4o/chat/completions?api-version=${API_VERSION}")

  echo "$RESPONSE" | jq '.choices[0].message.content'
}

test_chat
```

## 10. Integration Checklist

- [ ] Store API key in `.env` (never in code)
- [ ] Add `aiohttp` to `requirements.txt` for Python
- [ ] Create async wrapper in `backend/services/azure_openai_client.py`
- [ ] Replace Ollama in `llm_client.py`
- [ ] Test with medical consultation prompts
- [ ] Add logging/tracing for API calls
- [ ] Implement rate limiting (if needed)
- [ ] Add fallback to local Ollama (optional)

## Available Models (as of 2025-11-15)

✅ **Ready to use:**
- `gpt-4o` - Latest GPT-4 optimized
- `gpt-4` - GPT-4 base

❌ **Not deployed:**
- `whisper-001` (use Deepgram instead)
- `gpt-35-turbo-*` variants
- `gpt-4-turbo-*` variants

---

**Last tested:** 2025-11-15
**Endpoint:** `csp-eastus2-uat-aoai1.openai.azure.com`
**Region:** East US 2 (UAT)
