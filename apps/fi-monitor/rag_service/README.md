# RAG Embedding Service - GPU Accelerator

Fast embedding generation using sentence-transformers with GPU support for FI Monitor.

## Features

- **GPU Acceleration**: CUDA (NVIDIA) or MPS (Apple Silicon) support
- **CPU Fallback**: Works without GPU (slower)
- **Batch Processing**: Efficient batch embedding generation
- **API Key Auth**: Secure with X-API-Key header

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start Service

```bash
# Set API key (required)
export RAG_API_KEY="your-secure-key"

# Run service
python main.py
```

Service runs on `http://0.0.0.0:11435`

### Test Locally

```bash
# Health check (no auth)
curl http://localhost:11435/rag/health

# Generate embeddings (requires API key)
curl -X POST http://localhost:11435/rag/embed \
  -H "X-API-Key: your-secure-key" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["hello world", "machine learning"]}'
```

## API Endpoints

### POST /rag/embed

Generate embeddings for texts.

**Headers:**
- `X-API-Key`: API key (required)

**Request:**
```json
{
  "texts": ["text 1", "text 2", ...]
}
```

**Response:**
```json
{
  "embeddings": [[0.123, 0.456, ...], [...]],
  "device": "cuda",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "count": 2
}
```

### GET /rag/health

Health check (no auth required).

**Response:**
```json
{
  "status": "ok",
  "device": "cuda",
  "gpu_name": "NVIDIA GeForce RTX 4060",
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

## GPU Detection

- **CUDA** (NVIDIA): Automatically detected via PyTorch
- **MPS** (Apple Silicon): M1/M2/M3 Macs
- **CPU**: Fallback if no GPU

## Performance

### Expected Latency (Single Query):
- **GPU (CUDA/MPS)**: 20-50ms
- **CPU (M1)**: 100-150ms
- **CPU (i5)**: 200-300ms

### Batch Performance:
- 10 queries: ~5-10x faster than sequential CPU
- 100 queries: ~10-20x faster

## Integration with FI Monitor

FI Monitor (Tauri app) manages this service:
- Auto-start on app launch
- Auto-stop on app exit
- Exposes via Cloudflare Tunnel

## Integration with FI Cloud

FI Cloud backend calls this service via tunnel:
1. Try GPU endpoint (fast)
2. Fallback to local CPU if unavailable
3. Circuit breaker prevents cascading failures

## Security

- API key required for /rag/embed
- Health check is public (no sensitive data)
- Only listens on localhost (tunnel provides external access)
