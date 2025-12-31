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

- Node.js 18+
- pnpm
- Rust (for Tauri)
- FI Edge Server running (`python -m fi_edge.server`)
