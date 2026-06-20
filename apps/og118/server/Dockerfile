# og118 server — FastAPI + fi-runner (ClaudeCodeBackend).
#
# NOTE: build context MUST be the repo root (the server pip-installs fi-core +
# fi-runner from ../../packages). Build with:
#   docker build -f apps/og118/server/Dockerfile -t og118-server:staging .
#
# Why Node + the Claude CLI live in this image: fi-runner's ClaudeCodeBackend is
# claude-agent-sdk, which drives the `claude` CLI (a Node binary) as a
# subprocess — there is no pure-Python Anthropic backend in fi-runner. The
# ANTHROPIC_API_KEY (injected at runtime, never baked) only switches the CLI's
# auth from OAuth to API billing; it does not remove the CLI.
#
# Secrets (ANTHROPIC_API_KEY, OG118_ACCESS_TOKEN) and config (OG118_ALLOWED_ORIGINS)
# are injected at RUN time via -e / --env-file. Nothing secret is copied in.

FROM python:3.12-slim-bookworm

# Node 20 + the Claude Code CLI pinned to the version claude-agent-sdk expects.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @anthropic-ai/claude-code@2.1.162 \
 && apt-get purge -y curl gnupg && apt-get autoremove -y \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Substrate packages from the monorepo (context = repo root). Installed before
# the server so this layer caches across server-only edits.
COPY apps/packages/fi-core   /opt/fi/packages/fi-core
COPY apps/packages/fi-runner /opt/fi/packages/fi-runner
# stores-hdf5 (h5py+numpy) is REQUIRED by the rag_store capability's default
# HDF5 backend — without it the MCP 500s at the first ingest/search (the
# lazily-imported-dep deploy trap). pgvector is the persistent prod alternative
# (FI_RAG_BACKEND=pgvector) and needs its own extra + a DB.
RUN pip install --no-cache-dir \
      "/opt/fi/packages/fi-core[mcp,stores-hdf5]" \
      "/opt/fi/packages/fi-runner[claude]"

# The FastAPI app itself.
COPY apps/og118/server /opt/fi/server
RUN pip install --no-cache-dir -r /opt/fi/server/requirements.txt

# Run unprivileged; the Claude CLI needs a writable HOME for its config dir.
RUN useradd --create-home --uid 10001 og118
USER og118
ENV HOME=/home/og118

WORKDIR /opt/fi/server
EXPOSE 8118

# Bind 0.0.0.0 (container), not run.sh (which is the local .venv launcher).
# Auth mode is decided by the injected env: ANTHROPIC_API_KEY present → API mode.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8118", "--log-level", "info"]
