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

# Copy the runner's real import graph (post-castigo 2026-07-14 — `personas/`
# no existe; el engine conductual vive en khimeras_shared.behavior):
#   - shared/* for chunking, logging setup, and the persona registry/DNA
#   - khimeras_shared/* for runner.agent_client, prompts loader,
#     memory/vectors/style/corpus, memory_consolidation, deep_memory,
#     html_artifacts, and behavior/ (presets+flows+vulnerability engine that
#     persona_runner.{model_routing,router_runtime} import)
#   - persona_runner/* — the shared runner service (FastAPI + workspace_renderer)
#   - demux_ai/* — routing seeds (host_llm, summon) reachable by lazy imports
COPY shared/ shared/
COPY khimeras_shared/ khimeras_shared/
COPY persona_runner/ persona_runner/
COPY demux_ai/ demux_ai/

# All persona DNA (insult.md, vultur.md, etc.) → /app/personas/ to match the
# runner's PERSONAS_DIR default. A turn's persona_id selects <id>.md from here;
# PERSONA_PATH defaults to insult.md in this same dir (dedup 2026-07-16 — the
# root persona.md verbatim copy is DELETED, shared/personas/insult.md is the
# single source of truth). Renderer NEVER overwrites these.
COPY shared/personas/ /app/personas/

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

# See ../../Dockerfile: ConsoleRenderer's ANSI escapes break every KQL field predicate.
ENV LOG_FORMAT=json

EXPOSE 8080
CMD ["/entrypoint.sh"]
