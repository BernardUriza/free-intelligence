# Free Intelligence - Optimized Production Dockerfile
# Target: HPE ProLiant DL320 Gen11 Server
# Architecture: Multi-stage build for minimal image size

# ============================================================================
# Stage 1: Python Base with compiled dependencies
# ============================================================================
FROM python:3.11-slim AS python-base

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    cmake \
    postgresql-client \
    libpq-dev \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app user (non-root)
RUN groupadd -r fiuser && useradd -r -g fiuser fiuser

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# ============================================================================
# Stage 2: Python Dependencies Builder
# ============================================================================
FROM python-base AS python-deps

# Copy only requirements for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user uvicorn[standard] gunicorn

# ============================================================================
# Stage 3: Node.js Builder for Frontend
# ============================================================================
FROM node:20-alpine AS frontend-builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml* turbo.json ./
COPY apps/aurity/package.json apps/aurity/
COPY apps/aurity/next.config.*.js apps/aurity/
COPY apps/aurity/tsconfig.json apps/aurity/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY apps/aurity/ apps/aurity/

# Build frontend (static export)
RUN cd apps/aurity && \
    pnpm build && \
    pnpm next export

# ============================================================================
# Stage 4: Final Production Image
# ============================================================================
FROM python-base AS production

# HPE ProLiant optimization settings
ENV OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4 \
    NUMEXPR_NUM_THREADS=4

# Copy Python dependencies from builder
COPY --from=python-deps --chown=fiuser:fiuser /root/.local /home/fiuser/.local
ENV PATH=/home/fiuser/.local/bin:$PATH

# Copy backend application
COPY --chown=fiuser:fiuser backend/ /app/backend/
COPY --chown=fiuser:fiuser storage/ /app/storage/
COPY --chown=fiuser:fiuser config/ /app/config/

# Copy frontend build
COPY --from=frontend-builder --chown=fiuser:fiuser /app/apps/aurity/out /app/static

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R fiuser:fiuser /app

# Health check script
COPY --chown=fiuser:fiuser docker/healthcheck.sh /app/
RUN chmod +x /app/healthcheck.sh

# Switch to non-root user
USER fiuser

# Expose ports
EXPOSE 7001

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh || exit 1

# Set working directory
WORKDIR /app

# Production entrypoint with Gunicorn
CMD ["gunicorn", "backend.app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--threads", "2", \
     "--bind", "0.0.0.0:7001", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "/app/logs/access.log", \
     "--error-logfile", "/app/logs/error.log", \
     "--log-level", "info"]

# ============================================================================
# Build Commands:
# docker build -f docker/Dockerfile -t free-intelligence:latest .
# docker run -d --name fi-prod \
#   -p 7001:7001 \
#   -v $(pwd)/storage:/app/storage \
#   -v $(pwd)/logs:/app/logs \
#   --memory="4g" \
#   --cpus="2" \
#   free-intelligence:latest
# ============================================================================
