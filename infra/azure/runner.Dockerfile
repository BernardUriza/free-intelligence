# Insult Agent SDK Runner — Container Apps image.
#
# Built on `khimeras-runner-base` (infra/azure/runner-base.Dockerfile), which
# owns the whole toolchain — the conda env from environment.yml, Node 22, the
# Claude Code CLI and Playwright's Chromium. This image is COPY layers only, so
# a code commit no longer reinstalls ~260s of dependencies nor re-pushes a
# multi-GB Chromium.
#
# Workspace state is NOT in the image. It comes from an Azure Files mount at
# /data/insult-workspace populated by the workspace_renderer (Postgres -> markdown).
#
# This image is intentionally fat (Node + Python + Claude Code) because the runner
# is a single co-located process. Splitting Node and Python would mean inter-container
# IPC which is overkill at this scale.

ARG BASE_IMAGE=serverbotacr.azurecr.io/khimeras-runner-base:latest
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-l", "-c"]
WORKDIR /app

# Copy the runner's real import graph (post-castigo 2026-07-14 — `personas/`
# no existe; el engine conductual vive en khimeras_shared.behavior):
#   - shared/* for chunking, logging setup, and the persona registry/DNA
#   - khimeras_shared/* for runner.agent_client, prompts loader,
#     memory/vectors/style/corpus, consolidation/, deep_memory,
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
