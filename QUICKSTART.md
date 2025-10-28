# Free Intelligence - Quick Start Guide

**Version**: 0.3.0
**Last Updated**: 2025-10-28
**Time to Deploy**: ~5 minutes

---

## 🎯 What is Free Intelligence?

Free Intelligence (FI) is a **local-first**, **event-sourced** AI consultation system designed for medical settings. It combines:

- **Event Sourcing**: All state changes captured as immutable events
- **SOAP Notes**: NOM-004-SSA3-2012 compliant medical documentation
- **Local LLMs**: Ollama integration for offline operation
- **Audit Trail**: SHA256 hashing for compliance and non-repudiation

**Key Feature**: Your data never leaves your infrastructure. Everything runs on your hardware.

---

## 🚀 Quick Start (3 steps)

### Prerequisites

- Python 3.11+ (3.9+ works but 3.11+ recommended)
- Docker (optional, for containerized deployment)
- 8GB RAM minimum
- macOS, Linux, or Windows (WSL2)

### Step 1: Clone & Install

\`\`\`bash
# Clone repository
git clone https://github.com/BernardUriza/free-intelligence.git
cd free-intelligence

# Install dependencies + initialize corpus
make init

# Verify installation
make info
\`\`\`

### Step 2: Run Services

\`\`\`bash
# Start FI Consult Service (port 7001)
make run
\`\`\`

### Step 3: Test

\`\`\`bash
# Health check
curl http://localhost:7001/health

# Run test scenario
make test-scenario-1
\`\`\`

---

## 🐳 Docker Deployment

\`\`\`bash
# Build & run
make docker-build
make docker-run

# Check health
make health-check
\`\`\`

---

## 🛠️ Common Commands

\`\`\`bash
make help          # Show all commands
make run           # Start FI Consult Service
make run-gateway   # Start AURITY Gateway
make test          # Run tests
make clean         # Clean generated files
\`\`\`

---

See full documentation in \`docs/\` directory.
