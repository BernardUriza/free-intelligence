# RAG Embedding Service - GPU Acceleration

**GPU-accelerated embedding generation for FI Monitor**

## Overview

The RAG Service provides fast embedding generation using `sentence-transformers` with **mandatory GPU acceleration**. It exposes a REST API for FI Cloud to offload embedding generation from CPU-bound backend servers.

**Performance Guarantees:**
- **GPU (CUDA/MPS):** 20-50ms per query ✅
- **CPU:** NOT SUPPORTED (100-300ms - 5-10x slower) ❌

**GPU is mandatory by default.** The service will refuse to start without GPU to prevent silent performance degradation.

---

## Requirements

### Hardware

**Required:**
- **Windows:** NVIDIA GPU with 4GB+ VRAM (GTX 1650 or better)
- **macOS:** Apple Silicon (M1/M2/M3) with macOS 13+ (Ventura or newer)
- **Linux:** NVIDIA GPU with 4GB+ VRAM

**Not supported:**
- Integrated Intel/AMD GPUs
- CPU-only systems (without override)

### Software

**Windows (NVIDIA):**
- GPU drivers: [NVIDIA Driver 535+](https://www.nvidia.com/Download/index.aspx)
- CUDA Toolkit: [CUDA 12.1+](https://developer.nvidia.com/cuda-downloads)
- Python 3.10+

**macOS (Apple Silicon):**
- macOS 13+ (Ventura, Sonoma, or Sequoia)
- Python 3.10+

**Linux (NVIDIA):**
- GPU drivers: `nvidia-driver-535` or newer
- CUDA Toolkit: `nvidia-cuda-toolkit`
- Python 3.10+

---

## Installation

### 1. Verify GPU Availability

**Windows (NVIDIA):**
```powershell
nvidia-smi  # Should show GPU name and VRAM
```

**macOS (Apple Silicon):**
```bash
system_profiler SPDisplaysDataType | grep "Chipset Model"
# Should show "Apple M1" or "Apple M2"
```

**Linux (NVIDIA):**
```bash
nvidia-smi
```

### 2. Install Python Dependencies

```bash
cd apps/fi-monitor/rag_service
pip install -r requirements.txt
```

**Important:** On Windows/Linux with NVIDIA GPU, ensure you install PyTorch with CUDA support:

```bash
# CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Or CUDA 11.8 (older GPUs)
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 3. Verify GPU Detection

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('MPS:', torch.backends.mps.is_available())"
```

**Expected output:**
- **Windows/Linux (NVIDIA):** `CUDA: True`
- **macOS (Apple Silicon):** `MPS: True`
- **CPU-only:** `CUDA: False, MPS: False` ❌

---

## Usage

### Start Service

```bash
cd apps/fi-monitor
export RAG_API_KEY="your-secure-key-here"  # Required for auth
python -m uvicorn rag_service.main:app --host 0.0.0.0 --port 11435
```

**Expected startup logs (GPU system):**
```
[RAG Service] 🚀 GPU detected: NVIDIA GeForce RTX 4060
[RAG Service] 💾 VRAM: 8.00 GB
[RAG Service] Testing GPU memory allocation...
[RAG Service] ✅ GPU memory allocation test passed
[RAG Service] Loading model: sentence-transformers/all-MiniLM-L6-v2
[RAG Service] Device: cuda
[RAG Service] Warming up model...
[RAG Service] ✅ Model ready on cuda
[RAG Service] 💾 GPU Memory: 127MB allocated, 178MB reserved
```

### Health Check

```bash
curl http://localhost:11435/rag/health
```

**Response (GPU system):**
```json
{
  "status": "ok",
  "device": "cuda",
  "gpu_name": "NVIDIA GeForce RTX 4060",
  "gpu_memory_mb": 127.0,
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

### Generate Embeddings

```bash
curl -X POST http://localhost:11435/rag/embed \
  -H "X-API-Key: your-secure-key-here" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["patient presenting with fever and cough"]}'
```

**Response:**
```json
{
  "embeddings": [[0.123, -0.456, ...]],  // 384-dim vector
  "device": "cuda",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "count": 1
}
```

---

## GPU Requirement Enforcement

### Default Behavior (GPU Required)

By default, the service **refuses to start** if no GPU is detected:

```
❌ ERROR: No GPU detected - RAG Service requires GPU acceleration
================================================================================

📋 DIAGNOSIS:
   • CUDA available: No
   • MPS available: No
   • CPU-only mode: Not supported (performance <20ms required)

🔧 SOLUTIONS:

   Windows (NVIDIA):
   1. Install GPU drivers: https://www.nvidia.com/Download/index.aspx
   2. Install CUDA Toolkit 12.1+: https://developer.nvidia.com/cuda-downloads
   3. Verify: nvidia-smi (should show GPU)
   4. Reinstall PyTorch with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121

   macOS (Apple Silicon):
   1. Upgrade to macOS 13+ (Ventura or newer)
   2. Reinstall PyTorch: pip install --upgrade torch
   3. Verify: python -c "import torch; print(torch.backends.mps.is_available())"

   Linux (NVIDIA):
   1. Install GPU drivers: sudo apt install nvidia-driver-535
   2. Install CUDA: sudo apt install nvidia-cuda-toolkit
   3. Verify: nvidia-smi

🔓 OVERRIDE (Dev/Testing ONLY):
   export RAG_REQUIRE_GPU=false  # Allow CPU mode (degraded performance)
================================================================================
```

### Override for Development (CPU Mode)

For **development/testing ONLY**, you can allow CPU mode:

```bash
export RAG_REQUIRE_GPU=false
python -m uvicorn rag_service.main:app --host 0.0.0.0 --port 11435
```

**Warning logs (CPU mode):**
```
[RAG Service] ⚠️ No GPU detected - RAG_REQUIRE_GPU=false override active
[RAG Service] ⚠️ Performance will be degraded (100-300ms vs 20-50ms on GPU)
```

**Use cases for override:**
- Unit testing on CI/CD runners without GPU
- Local development on CPU-only laptop
- Debugging non-GPU-related code

**DO NOT use in production** - performance will be 5-10x slower.

---

## Troubleshooting

### Issue: Service exits with "No GPU detected"

**Cause:** GPU drivers not installed or CUDA/MPS not available

**Fix (Windows NVIDIA):**
1. Install NVIDIA drivers: [Download here](https://www.nvidia.com/Download/index.aspx)
2. Install CUDA 12.1+: [Download here](https://developer.nvidia.com/cuda-downloads)
3. Reinstall PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu121`
4. Verify: `nvidia-smi` should show GPU

**Fix (macOS Apple Silicon):**
1. Upgrade to macOS 13+ (Ventura or newer)
2. Reinstall PyTorch: `pip install --upgrade torch`
3. Verify: `python -c "import torch; print(torch.backends.mps.is_available())"`

**Fix (Linux NVIDIA):**
```bash
sudo apt update
sudo apt install nvidia-driver-535 nvidia-cuda-toolkit
nvidia-smi  # Verify GPU appears
```

---

### Issue: "GPU detected but allocation failed"

**Cause:** GPU driver crashed, VRAM exhausted, or GPU in use

**Fix:**
1. **Restart GPU drivers:**
   - Windows: Restart PC or use `nvidia-smi --gpu-reset`
   - Linux: `sudo systemctl restart nvidia-persistenced`
   - macOS: Restart Mac

2. **Close GPU-intensive apps:**
   - Close games, video editors, 3D software
   - Check GPU usage: `nvidia-smi` (CUDA) or Activity Monitor (MPS)

3. **Free VRAM:**
   ```python
   # In Python console
   import torch
   torch.cuda.empty_cache()  # CUDA only
   ```

---

### Issue: Service starts but Tauri health check fails

**Cause:** Service running on CPU (GPU requirement bypass)

**Fix:**
1. Remove `RAG_REQUIRE_GPU=false` override
2. Restart service with GPU
3. Verify health check returns `"device": "cuda"` or `"mps"`

**Check logs:**
```
[FI Monitor] ❌ RAG Service running on CPU (device: cpu) - rejecting
```

---

### Issue: PyTorch installed but CUDA not available

**Cause:** PyTorch installed without CUDA support (CPU-only build)

**Fix:**
```bash
# Uninstall CPU-only PyTorch
pip uninstall torch

# Reinstall with CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Verify
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
# Should print: CUDA: True
```

---

## Performance Benchmarks

| Hardware | Device | Latency (1 query) | Throughput (batch 32) |
|----------|--------|-------------------|-----------------------|
| NVIDIA RTX 4060 (8GB) | CUDA | 22ms | 450 queries/sec |
| Apple M2 Max | MPS | 28ms | 380 queries/sec |
| Intel Core i9 (32 cores) | CPU | 185ms | 45 queries/sec |

**Conclusion:** GPU is 6-10x faster than high-end CPU.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│ FI Cloud (Azure VM)                              │
│ ┌──────────────────────────────────────────────┐ │
│ │ Backend FastAPI (CPU-bound)                  │ │
│ │ • Receives patient query                     │ │
│ │ • Forwards to RAG Service for embedding      │ │
│ └──────────────┬───────────────────────────────┘ │
│                │ POST /rag/embed                  │
│                ▼                                   │
│ ┌──────────────────────────────────────────────┐ │
│ │ FI Monitor (Local Windows/Mac)                │ │
│ │ ┌────────────────────────────────────────────┤ │
│ │ │ RAG Service (FastAPI + GPU)               │ │
│ │ │ • SentenceTransformer on CUDA/MPS         │ │
│ │ │ • Generates 384-dim embeddings            │ │
│ │ │ • Returns to Backend in 20-50ms           │ │
│ │ └────────────────────────────────────────────┤ │
│ │ ┌────────────────────────────────────────────┤ │
│ │ │ Cloudflare Tunnel                         │ │
│ │ │ • Exposes RAG Service to cloud            │ │
│ │ │ • HTTPS with TLS encryption               │ │
│ │ └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## Security

### API Key Authentication

All requests to `/rag/embed` require `X-API-Key` header:

```bash
curl -X POST http://localhost:11435/rag/embed \
  -H "X-API-Key: your-secure-key-here" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["query"]}'
```

**Configure API key:**
```bash
export RAG_API_KEY="generate-random-256bit-key-here"
```

**Generate secure key:**
```python
import secrets
print(secrets.token_urlsafe(32))  # Generates 256-bit key
```

### TLS/HTTPS

In production, RAG Service is exposed via Cloudflare Tunnel with TLS encryption. Direct access to `localhost:11435` is only for local testing.

---

## API Reference

### POST /rag/embed

Generate embeddings for texts.

**Headers:**
- `X-API-Key: string` (required) - API key for authentication
- `Content-Type: application/json`

**Request Body:**
```json
{
  "texts": ["text1", "text2", "..."]  // 1-100 texts
}
```

**Response (200 OK):**
```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],  // 384-dim vectors
  "device": "cuda",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "count": 2
}
```

**Errors:**
- `401 Unauthorized` - Invalid or missing API key
- `503 Service Unavailable` - Model not loaded yet
- `500 Internal Server Error` - Embedding generation failed

---

### GET /rag/health

Health check with GPU validation.

**Headers:** None (public endpoint)

**Response (200 OK):**
```json
{
  "status": "ok",
  "device": "cuda",
  "gpu_name": "NVIDIA GeForce RTX 4060",
  "gpu_memory_mb": 127.0,
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

**Fields:**
- `device`: `"cuda"` (NVIDIA), `"mps"` (Apple Silicon), or `"cpu"` (override only)
- `gpu_name`: GPU model name (null if CPU)
- `gpu_memory_mb`: Allocated VRAM in MB (CUDA only, MPS returns -1)

---

## Development

### Run Tests

```bash
cd apps/fi-monitor/rag_service
pytest test_gpu_validation.py -v
```

### Manual Testing

1. **GPU Detection Test:**
   ```python
   import torch
   print("CUDA:", torch.cuda.is_available())
   print("MPS:", torch.backends.mps.is_available())
   if torch.cuda.is_available():
       print("GPU:", torch.cuda.get_device_name(0))
   ```

2. **Embedding Performance Test:**
   ```python
   from sentence_transformers import SentenceTransformer
   import time

   model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cuda")
   texts = ["test query"] * 32

   start = time.time()
   embeddings = model.encode(texts)
   elapsed_ms = (time.time() - start) * 1000

   print(f"Latency: {elapsed_ms:.1f}ms for {len(texts)} queries")
   print(f"Per query: {elapsed_ms/len(texts):.1f}ms")
   ```

---

## FAQ

### Q: Can I run this on CPU for testing?

**A:** Yes, set `RAG_REQUIRE_GPU=false` environment variable. Performance will be 5-10x slower (100-300ms vs 20-50ms).

### Q: Does Apple Silicon M1/M2 work?

**A:** Yes, macOS 13+ (Ventura or newer) required. MPS (Metal Performance Shaders) provides GPU acceleration on Apple Silicon.

### Q: What if I have multiple GPUs?

**A:** PyTorch will use GPU 0 by default. To use a different GPU:
```bash
export CUDA_VISIBLE_DEVICES=1  # Use GPU 1
```

### Q: How much VRAM is required?

**A:** ~200-300MB for the model. Minimum 2GB recommended (most GPUs have 4GB+).

### Q: Can I use AMD GPUs?

**A:** Not currently supported. CUDA (NVIDIA) and MPS (Apple Silicon) only.

---

## See Also

- [FI Monitor README](../README.md) - Main FI Monitor documentation
- [Gateway Service](../gateway/README.md) - HTTP router for Ollama + RAG
- [sentence-transformers docs](https://www.sbert.net/) - Model library documentation
- [PyTorch CUDA setup](https://pytorch.org/get-started/locally/) - GPU installation guide
