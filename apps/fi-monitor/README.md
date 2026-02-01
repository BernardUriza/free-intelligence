# FI Monitor

Real-time LLM observability dashboard for FI Edge.

## Development

```bash
# Install dependencies
pnpm install

# Start development server (web only)
pnpm dev

# Start Tauri development (desktop app)
pnpm tauri dev
```

## Build

```bash
# Build for production
pnpm tauri build
```

## Configuration

Edit `.env` to point to your FI Edge Server:
```
VITE_API_URL=http://localhost:9200
```

## Requirements

### Development
- Node.js 18+
- pnpm
- Rust (for Tauri)

### Runtime Services
- **Ollama** (LLM inference)
- **Python 3.10+** (for RAG Service + Gateway)
- **GPU (MANDATORY for RAG Service)**:
  - **Windows/Linux:** NVIDIA GPU with 4GB+ VRAM + CUDA 12.1+
  - **macOS:** Apple Silicon (M1/M2/M3) + macOS 13+
  - **Not supported:** CPU-only systems (performance degradation 5-10x)

**Note:** GPU is mandatory by default for RAG Service. See [RAG Service README](rag_service/README.md) for troubleshooting.
