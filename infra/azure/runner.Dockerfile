# persona-runner — Container Apps image.
#
# Built straight on `khimeras-base` (the shared conda env): since v4.35.x the
# runner fronts AIRE's engine door over httpx — no Node, no Claude CLI, no
# Chromium. The intermediate `khimeras-runner-base` that carried that toolchain
# was deleted when its last consumer (the local SDK host) died. This image is
# COPY layers only.
#
# Workspace state is NOT in the image. It comes from an Azure Files mount at
# /data/insult-workspace populated by the workspace_renderer (Postgres -> markdown).
#
ARG BASE_IMAGE=serverbotacr.azurecr.io/khimeras-base:latest
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

# Entrypoint: boot log + uvicorn foreground. See infra/azure/entrypoint.sh.
COPY infra/azure/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Non-root stays (least privilege for a container fronting Discord input),
# even though the Claude-CLI root refusal that originally forced it is gone.
RUN useradd --create-home --shell /bin/bash --uid 10001 runner \
 && chown -R runner:runner /app /home/runner
USER runner
ENV HOME=/home/runner

# See ../../Dockerfile: ConsoleRenderer's ANSI escapes break every KQL field predicate.
ENV LOG_FORMAT=json

EXPOSE 8080
CMD ["/entrypoint.sh"]
