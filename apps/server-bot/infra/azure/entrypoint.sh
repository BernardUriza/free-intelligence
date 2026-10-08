#!/bin/bash
# Entrypoint for persona-runner Container App.
#
# Two processes share the container:
#   - workspace_renderer (Python, background) — mirrors Postgres -> markdown
#   - FastAPI Agent SDK runner (uvicorn, foreground) — exposes POST /v1/turn
#
# The renderer's logs go to /var/log/insult-renderer.log so `az containerapp logs`
# only shows the FastAPI side by default. tail the file via exec if you need
# the renderer activity. (TODO Fase 4: ship renderer logs to stdout too via
# a tee or a sidecar process — for now this keeps the main log stream clean.)
#
# No Anthropic credential lives here: since v4.35.0 every turn rides AIRE's
# engine door (AIRE_AUTH_TOKEN, a door bearer — not the fleet OAuth). The
# credentials.json materialization died with the local SDK host
# (backlog runner-base-node-cli-muertos.md).

set -euo pipefail

echo "[entrypoint] persona-runner booting"
echo "[entrypoint] python $(python3 --version)"

# --- Workspace renderer (DISABLED in F4 phase 3, v3.9.56) -------------------
#
# The renderer projected Postgres -> markdown every 60 s so the agent's
# Read/Grep/Glob tools could see PG state. F4 replaced that with
# in-process MCP tools (`mcp__insult_db__*`) that query PG directly,
# making the projection redundant. Read/Grep/Glob were also removed from
# allowed_tools in runner.py so the markdown files are no longer consulted.
#
# The Azure Files mount at /data/insult-workspace is still mounted —
# the agent reads CLAUDE.md from there via setting_sources=["project"].
# The facts/messages/disclosure_log.md files in that mount are now
# FROZEN at whatever the last render left behind. Fase 4 will unmount
# the share entirely once CLAUDE.md is moved into the container image.
#
# To re-enable for debugging only: uncomment the python3 line below.
# python3 -m persona_runner.workspace_renderer > /tmp/insult-logs/renderer.log 2>&1 &
mkdir -p /tmp/insult-logs
echo "[entrypoint] workspace_renderer DISABLED (F4 phase 3) — MCP tools query PG directly"

# --- FastAPI Agent SDK runner (foreground) ----------------------------------

# uvicorn binds 0.0.0.0:8080 because Container Apps internal ingress targets
# 8080 by default; we'll enable ingress with target-port 8080 separately.
# --workers 1 keeps it single-process: the agent loop is async and CPU-light,
# more workers just multiply OAuth quota burn.
echo "[entrypoint] starting FastAPI runner on :8080"
exec uvicorn persona_runner.runner:app \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 1 \
  --log-level info \
  --access-log
