# Insult Agent SDK Runner — Container Apps image.
#
# Conda-native base (memory: feedback_no_pypi_only_conda). Uses Quay.io
# to dodge the Docker Hub anonymous-pull rate limit (same reason MCR
# replaced python:3.14-slim originally — see reference_dockerfile_base_mcr).
#
# Runs:
#   - Node 22 + @anthropic-ai/claude-code CLI (for the Agent SDK loop) —
#     Node installed via conda-forge, not apt, so the whole stack is
#     conda-managed.
#   - Python 3.14 + the env from environment.yml (FastAPI runner +
#     workspace_renderer + asyncpg + the shared deps).
#
# Workspace state is NOT in the image. It comes from an Azure Files mount at
# /data/insult-workspace populated by the workspace_renderer (Postgres -> markdown).
#
# This image is intentionally fat (Node + Python + Claude Code) because the runner
# is a single co-located process. Splitting Node and Python would mean inter-container
# IPC which is overkill at this scale.

FROM quay.io/condaforge/miniforge3:26.1.1-3

SHELL ["/bin/bash", "-l", "-c"]
WORKDIR /app

# Install the conda env into `base`, then add Node 22 from conda-forge.
# Node-from-conda avoids the NodeSource apt repo + the OS-version-specific
# Bookworm-has-18 dance — everything stays inside one package manager.
COPY environment.yml .
RUN mamba env update -n base -f environment.yml \
 && mamba install -n base -c conda-forge -y 'nodejs>=22,<23' \
 && mamba clean --all --yes \
 && find /opt/conda/ -follow -type f -name '*.a' -delete \
 && find /opt/conda/ -follow -type f -name '*.pyc' -delete

# Install Claude Code CLI globally via npm (npm comes from the conda
# nodejs package). OAuth Max credentials get mounted at runtime via
# /home/runner/.claude/.credentials.json (NOT baked into the image).
RUN npm install -g --silent @anthropic-ai/claude-code

# Playwright MCP server + headless Chromium for scraping JS-heavy / social-media
# sites (IG/FB/TikTok/X) that web_search cannot reach. Chromium lives at
# PLAYWRIGHT_BROWSERS_PATH so the non-root runner user can read it. apt deps
# (libnss3, libgbm, libxcomposite, libxdamage, libasound, etc.) are pulled in
# by `--with-deps`, which needs root — done here before the USER switch below.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN npm install -g --silent @playwright/mcp \
 && npx -y playwright install --with-deps chromium \
 && chmod -R a+rX /opt/playwright-browsers

# Copy shared/ and insult/ — runner needs:
#   - shared/* for chunking, retry, logging setup
#   - insult/agent/* for workspace_renderer + (Fase 2b) FastAPI runner
#   - insult/core/memory/* for asyncpg repos that the renderer queries
# alice/ is NOT copied — runner is bot-agnostic; only the workspace
# matters at agent-loop time.
COPY shared/ shared/
COPY insult/ insult/

# Persona file lives in the repo (not in workspace mount) so it ships
# with the image. Renderer NEVER overwrites it.
COPY persona.md /app/persona.md

# Entrypoint script orchestrates two processes: renderer (background) +
# FastAPI runner (foreground). See infra/azure/entrypoint.sh for details
# on OAuth credential materialization and process lifecycle.
COPY infra/azure/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Non-root user is MANDATORY for Claude Code: it refuses to run with
# `--dangerously-skip-permissions` (which our `bypassPermissions` mode
# uses under the hood) when the process is root. Discovered the hard
# way in v3.9.22 prod test: agent loop exits with
# "--dangerously-skip-permissions cannot be used with root/sudo
# privileges for security reasons". HOME is set so the SDK writes
# `~/.claude/.credentials.json` to the right place.
RUN useradd --create-home --shell /bin/bash --uid 10001 runner \
 && chown -R runner:runner /app /home/runner
USER runner
ENV HOME=/home/runner

EXPOSE 8080
CMD ["/entrypoint.sh"]
