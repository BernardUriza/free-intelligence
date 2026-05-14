# Insult Agent SDK Runner — Container Apps image.
#
# Runs:
#   - Node 22 + @anthropic-ai/claude-code CLI (for the Agent SDK loop)
#   - Python 3.14 + uv (for the FastAPI service that Insult Container App calls)
#
# Workspace state is NOT in the image. It comes from an Azure Files mount at
# /data/insult-workspace populated by the workspace_renderer (Postgres -> markdown).
#
# This image is intentionally fat (Node + Python + Claude Code) because the runner
# is a single co-located process. Splitting Node and Python would mean inter-container
# IPC which is overkill at this scale.

FROM mcr.microsoft.com/devcontainers/python:3.14-bookworm

WORKDIR /app

# Install Node 22 (NodeSource repo, Bookworm has 18 by default)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally. OAuth Max credentials get mounted at runtime
# via /home/runner/.claude/.credentials.json (NOT baked into the image).
RUN npm install -g --silent @anthropic-ai/claude-code

# Install Python deps. requirements.txt is the same one Insult uses; the runner
# pulls in asyncpg/structlog/fastapi/uvicorn from there.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared/ (text chunking, retry, structlog setup) — runner reuses these.
# Insult/ and alice/ are NOT copied: the runner is intentionally agnostic of
# either bot's persona logic. Persona lives in the workspace mount.
COPY shared/ shared/

# Placeholder entrypoint until Fase 2 lands the real FastAPI app:
#   - keeps the container alive so `az containerapp exec` works
#   - smoke-tests Node + Python + claude-code at every boot
# Fase 2 swaps to `python -m insult.agent.runner` or similar.
CMD ["sh", "-c", "node --version && python3 --version && claude --version && echo 'runner placeholder up' && sleep infinity"]
