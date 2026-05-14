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

# Copy shared/ and insult/ — runner needs:
#   - shared/* for chunking, retry, logging setup
#   - insult/agent/* for workspace_renderer + (Fase 2b) FastAPI runner
#   - insult/core/memory/* for asyncpg repos that the renderer queries
# alice/ is NOT copied — runner is bot-agnostic; only the workspace
# matters at agent-loop time.
COPY shared/ shared/
COPY insult/ insult/

# Bootstrap script + supervisord-style entrypoint. Two long-running
# processes share the container:
#   - workspace_renderer (Postgres -> markdown, every 60s)
#   - Fase 2b: FastAPI runner on :8080
# Until Fase 2b lands, only the renderer runs. The smoke versions print
# happens once at boot so logs confirm the toolchain is wired.
CMD ["sh", "-c", "node --version && python3 --version && claude --version && echo 'runner up' && exec python3 -m insult.agent.workspace_renderer"]
