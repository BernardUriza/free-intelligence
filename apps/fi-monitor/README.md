# FI Monitor

[![Version](https://img.shields.io/badge/version-1.0.1-blue)](https://github.com/BernardUriza/free-intelligence/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://tauri.app)
[![License](https://img.shields.io/badge/license-Proprietary-red)](https://app.aurity.io)

Real-time LLM observability dashboard and Ollama tunnel manager for Aurity.

## Features

- 🌐 **Cloudflare Tunnel Management** - Automatically expose local Ollama to cloud
- 🔄 **Auto-Update** - Seamless updates via GitHub Releases
- 📊 **System Tray Integration** - Runs quietly in the background
- 🚀 **Cross-Platform** - Windows, macOS, and Linux support
- 🔒 **Secure** - Ed25519 signed updates, no external dependencies

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
