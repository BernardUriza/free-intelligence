# Free Intelligence - Dockerfile
# Multi-stage build for production deployment

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libhdf5-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

LABEL maintainer="Bernard Uriza <bernard.uriza@example.com>"
LABEL description="Free Intelligence - Local-first AI consultation system"
LABEL version="0.3.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libhdf5-103 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY backend/ ./backend/
COPY config/ ./config/
COPY prompts/ ./prompts/
COPY schemas/ ./schemas/
COPY docs/ ./docs/

# Create necessary directories
RUN mkdir -p storage logs backups exports eval/results

# Initialize corpus if it doesn't exist
RUN python3 -c "from backend.corpus_schema import init_corpus; import os; \
    corpus_path = 'storage/corpus.h5'; \
    os.makedirs('storage', exist_ok=True); \
    init_corpus(corpus_path, owner_identifier='docker@fi', force=False) if not os.path.exists(corpus_path) else None"

# Expose ports
# 7001: FI Consult Service
# 7002: AURITY Gateway
EXPOSE 7001 7002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7001/health || exit 1

# Default command: Start FI Consult Service
CMD ["python3", "-m", "uvicorn", "backend.fi_consult_service:app", "--host", "0.0.0.0", "--port", "7001"]

# Alternative commands (use via docker run):
# - AURITY Gateway: CMD ["python3", "-m", "uvicorn", "backend.aurity_gateway:app", "--host", "0.0.0.0", "--port", "7002"]
# - Both services: Use docker-compose.yml
