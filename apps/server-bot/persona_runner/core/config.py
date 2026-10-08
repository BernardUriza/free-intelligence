"""Runner configuration — every env knob in ONE place.

Extracted from the 1076-line runner.py monolith (2026-07-14). Before this, the
config was interleaved with the pool, the schemas and the endpoints, so a knob's
blast radius was invisible: `MAX_POOL_SESSIONS` sat 400 lines from the pool it
caps. Anything reading env for the runner reads it HERE.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/data/insult-workspace"))
PERSONA_PATH = Path(os.environ.get("PERSONA_PATH", "/app/personas/insult.md"))

# Multi-persona (Khimeras): a turn may carry a `persona_id` to load a sibling
# persona (e.g. "vultur") from PERSONAS_DIR/<id>.md instead of the default
# PERSONA_PATH. The id is allowlisted to a tight charset so it can never escape
# the directory (path traversal) — anything else falls back to the default.
PERSONAS_DIR = Path(os.environ.get("PERSONAS_DIR", "/app/personas"))
PERSONA_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")

RUNNER_AUTH_TOKEN = os.environ.get("PERSONA_RUNNER_TOKEN") or os.environ.get("INSULT_AGENT_RUNNER_TOKEN", "")

# FastAPI publishes /docs, /redoc and /openapi.json with no auth by default, and
# this runner is the one app in the environment with EXTERNAL ingress — it has to
# be, because a human opens `/a/{id}` artifacts in a browser and AIRE calls
# `/mcp/{casita}` from the droplet. Verified 2026-09-09: both /docs and
# /openapi.json answered 200 from the open internet, handing anyone who finds the
# FQDN the full map of the turn, judge, workspace and MCP endpoints with their
# schemas. Every endpoint does authenticate (core/auth.py is fail-closed and
# timing-safe), so this is reconnaissance, not a breach — and reconnaissance the
# service gains nothing by giving away. Off by default, opt-in for local work.
DOCS_ENABLED = os.environ.get("RUNNER_DOCS_ENABLED", "").strip().lower() in ("1", "true", "yes")
DEFAULT_MODEL = os.environ.get("AGENT_RUNNER_MODEL", "claude-sonnet-4-6")
TURN_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_TIMEOUT_S", "90"))

# Boletos durables (engine/turn_jobs, 2026-09-23). `deadline` es el presupuesto
# del turno del gateway (first_turn_timeout_s = 600): pasado eso nadie está
# escuchando y una reanudación sólo quemaría tokens. `drain` es la espera de
# shutdown por los jobs abiertos: grace de ACA (600) menos 30 s para cerrar
# clientes y pool; al vencer, las filas se sueltan para la réplica sucesora.
RUNNER_JOB_DEADLINE_S = float(os.environ.get("RUNNER_JOB_DEADLINE_S", "600"))
RUNNER_SHUTDOWN_DRAIN_S = float(os.environ.get("RUNNER_SHUTDOWN_DRAIN_S", "570"))

# The AIRE door mode persona turns ride. Only "agent" carries WebSearch/WebFetch
# (server-side dial); verify_aire_route crashes the boot on anything else.
AIRE_TURN_MODE = os.environ.get("AIRE_TURN_MODE", "agent").strip().lower()
# Cap on the in-band <user_memory> facts block the AIRE route composes per turn.
AIRE_FACTS_MAX_CHARS = int(os.environ.get("AIRE_FACTS_MAX_CHARS", "6000"))

# The THIRD axis of the AIRE mapping (Bernard, 2026-08-22): the casita is the
# channel's SOUL and lives forever; the SESSION inside it is a TOPIC that rolls
# over after this many seconds of channel silence.
#
# WHAT A ROLLOVER COSTS: the next turn is a COLD AIRE session, so the persona
# system prompt (~14k tokens of DNA alone) is cache-CREATED again — a
# single-sentence cold turn measured $0.107 against the live gate (stage-2
# backlog). Too short a window is a money leak paid once per silence; too long
# defeats the axis, because the transcript AIRE resumes keeps growing and last
# month's conversation rides into today's answer.
#
# WHY 3600 s: it makes the rollover nearly FREE instead of merely tolerable.
# AIRE evicts an idle pooled client after AIRE_POOL_IDLE_S (3300 s ≈ 55 min), so
# a channel silent for an hour has ALREADY lost its warm client — that turn
# re-pays the system prompt whether or not the topic rolls. Rolling just past
# that boundary buys a fresh transcript at the price of a cold start that was
# already going to be charged. Shortening this below ~55 min is where real money
# starts being spent, and that — not tidiness — is the trade to weigh.
AIRE_TOPIC_IDLE_TIMEOUT_S = float(os.environ.get("AIRE_TOPIC_IDLE_TIMEOUT_S", "3600"))

# Max concurrent /v1/judge calls. Default 1. Born on 2026-05-22, when a
# consolidator backlog fired ~25 judges at once and the local SDK's subprocess
# pile-up OOM-killed the chat turns (p50 turn latency 27-53s). The pile-up only
# MOVED with the AIRE migration — to the droplet's 2 RAM slots — so the gate
# still protects the interactive turns from consolidator bursts. Judges are
# background utility work (consolidator, fact-extraction, summaries); the user
# is NOT waiting on them. Override via env for a bigger AIRE pool.
JUDGE_MAX_CONCURRENCY = int(os.environ.get("AGENT_RUNNER_JUDGE_MAX_CONCURRENCY", "1"))
JUDGE_DEFAULT_MODEL = os.environ.get("AGENT_RUNNER_JUDGE_MODEL", "claude-haiku-4-5-20251001")

# OG118-CONTINUITY caps for replayed history — mirror fi_runner's client-history
# defaults (20 msgs / 16k chars) so both sides of the contract bound the same.
HISTORY_MAX_MESSAGES = int(os.environ.get("AGENT_RUNNER_HISTORY_MAX_MESSAGES", "20"))
HISTORY_MAX_CHARS = int(os.environ.get("AGENT_RUNNER_HISTORY_MAX_CHARS", "16000"))

# Read-only workspace window (the "log in and see what the agents built" surface).
WORKSPACE_MAX_ENTRIES = 500
WORKSPACE_MAX_FILE_BYTES = 256 * 1024
WORKSPACE_SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", ".venv"})
