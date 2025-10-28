# Ollama Setup Guide - Free Intelligence Offline-First

**Last Updated**: 2025-10-28
**Status**: Production-Ready ✅
**Roadmap**: Sprint 3 - Offline CPU

---

## 🎯 Overview

Free Intelligence now supports **100% offline operation** using Ollama for local LLM inference. This eliminates:
- ❌ Cloud API costs ($0/month vs $10+/month)
- ❌ API rate limits
- ❌ Data privacy concerns (no external calls)
- ❌ Internet dependency

**One-switch rollback**: Change `primary_provider` in `fi.policy.yaml` from `claude` to `ollama`.

---

## 📋 Prerequisites

### 1. Install Ollama

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Or download**: https://ollama.com/download

**Verify installation:**
```bash
ollama --version
# Should show: ollama version 0.x.x
```

---

## 🚀 Quick Start (5 minutes)

### Step 1: Pull Recommended Models

```bash
# Text generation model (Qwen 2.5 7B - best for Chinese + code)
ollama pull qwen2.5:7b-instruct-q4_0

# Embedding model (768 dimensions - compatible with corpus)
ollama pull nomic-embed-text
```

**Model sizes:**
- `qwen2.5:7b-instruct-q4_0`: ~4.3 GB (Q4 quantization)
- `nomic-embed-text`: ~274 MB

**Download time**: 5-15 minutes (depending on internet speed)

---

### Step 2: Verify Ollama is Running

```bash
# Start Ollama server (if not auto-started)
ollama serve

# Test in another terminal
ollama list
# Should show: qwen2.5:7b-instruct-q4_0 and nomic-embed-text
```

---

### Step 3: Switch Free Intelligence to Ollama

Edit `config/fi.policy.yaml`:

```yaml
llm:
  primary_provider: "ollama"     # Change from "claude"
  fallback_provider: "claude"    # Keep Claude as backup
  enable_offline: true           # Enable offline mode
```

**That's it!** Free Intelligence will now use Ollama by default.

---

## 🧪 Test Ollama Integration

```bash
# Interactive chat with Ollama
python3 cli/fi.py chat

# Search using Ollama embeddings
python3 cli/fi.py search "your query"

# View configuration
python3 cli/fi.py config
```

**Expected output:**
```
📋 Provider:  ollama
🤖 Model:     qwen2.5:7b-instruct-q4_0
💰 Cost:      $0.000000 (FREE!)
```

---

## 🔧 Advanced Configuration

### Recommended Models by Use Case

**1. Chinese + Code (Best All-Around):**
```yaml
model: "qwen2.5:7b-instruct-q4_0"
embed_model: "nomic-embed-text"
```

**2. Reasoning-Focused:**
```yaml
model: "deepseek-r1:7b"           # DeepSeek R1 Distill 7B
embed_model: "nomic-embed-text"
```

**3. Speed-Optimized (Low RAM):**
```yaml
model: "llama3.2:3b"              # Llama 3.2 3B (very fast)
embed_model: "nomic-embed-text"
```

**4. Larger Context (if you have RAM):**
```yaml
model: "qwen2.5:14b"              # 14B model, better quality
embed_model: "mxbai-embed-large"  # 1024-dim embeddings
```

---

### Pull Alternative Models

```bash
# DeepSeek R1 (reasoning)
ollama pull deepseek-r1:7b

# Llama 3.2 (fast)
ollama pull llama3.2:3b

# Alternative embedding model
ollama pull mxbai-embed-large
```

---

### Running Ollama on NAS (Network Mode)

If running Ollama on a NAS server:

**1. On NAS, expose Ollama:**
```bash
# Set OLLAMA_HOST environment variable
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

**2. Update `fi.policy.yaml`:**
```yaml
ollama:
  base_url: "http://192.168.1.100:11434"  # Your NAS IP
```

**3. Test connection:**
```bash
curl http://192.168.1.100:11434/api/tags
```

---

## 📊 Performance Comparison

| Metric | Claude API | Ollama (Local) |
|--------|------------|----------------|
| **Cost** | $3-15 per 1M tokens | **$0** (free) |
| **Latency** | 800-1500ms | 2000-5000ms (CPU) / 500-1500ms (GPU) |
| **Privacy** | External API | **100% local** |
| **Offline** | ❌ Requires internet | ✅ **Fully offline** |
| **Rate Limits** | Yes (60 req/min) | **None** |
| **Context Window** | 200K tokens | 8-32K tokens (model-dependent) |

---

## 🔍 Troubleshooting

### "Connection refused" error

**Problem**: Ollama server not running

**Solution**:
```bash
# Start Ollama manually
ollama serve

# Or check if running
ps aux | grep ollama
```

---

### "Model not found" error

**Problem**: Model not pulled

**Solution**:
```bash
# List available models
ollama list

# Pull missing model
ollama pull qwen2.5:7b-instruct-q4_0
```

---

### Slow inference (>10s per response)

**Problem**: Running on CPU without optimization

**Solutions**:
1. **Use smaller model**:
   ```bash
   ollama pull llama3.2:3b
   ```

2. **Enable GPU acceleration** (if available):
   ```bash
   # Ollama auto-detects CUDA/Metal
   # Check logs for "GPU detected"
   ```

3. **Reduce max_tokens** in `fi.policy.yaml`:
   ```yaml
   max_tokens: 512  # Faster inference
   ```

---

### Embeddings dimension mismatch

**Problem**: Different embed model dimensions

**Solution**: Free Intelligence expects 768-dim embeddings (or will pad).

**Recommended embedding models (768-dim)**:
- `nomic-embed-text` (768-dim) ✅
- `all-minilm` (384-dim, auto-padded) ✅

**If using 1024-dim model**, update corpus schema in future (breaking change).

---

## 🎨 Best Practices

### 1. Keep Models Updated

```bash
# Update all models
ollama list | tail -n +2 | awk '{print $1}' | xargs -I {} ollama pull {}
```

### 2. Monitor Resource Usage

```bash
# Check Ollama memory usage
ps aux | grep ollama

# macOS: Activity Monitor
# Linux: htop or top
```

### 3. Hybrid Mode (Best of Both Worlds)

Keep both providers configured:

```yaml
llm:
  primary_provider: "ollama"     # Use Ollama by default (free, private)
  fallback_provider: "claude"    # Fall back to Claude if Ollama fails
```

**Automatic fallback** when:
- Ollama server is down
- Model not found
- Timeout exceeded

---

## 📚 Additional Resources

- **Ollama Documentation**: https://ollama.com/docs
- **Qwen Models**: https://ollama.com/library/qwen2.5
- **DeepSeek Models**: https://ollama.com/library/deepseek-r1
- **Embedding Models**: https://ollama.com/blog/embedding-models

---

## 🚀 Next Steps

1. ✅ Install Ollama
2. ✅ Pull models (`qwen2.5:7b-instruct-q4_0`, `nomic-embed-text`)
3. ✅ Update `fi.policy.yaml` to use Ollama
4. ✅ Test with `python3 cli/fi.py chat`
5. 🎯 **Enjoy 100% offline, $0-cost AI memory!**

---

**Need help?** Check `ROADMAP_OFFLINE_FIRST.md` for the complete offline-first strategy.
