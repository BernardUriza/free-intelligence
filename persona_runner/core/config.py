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
DEFAULT_MODEL = os.environ.get("AGENT_RUNNER_MODEL", "claude-sonnet-4-6")
TURN_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_TIMEOUT_S", "90"))

# Close a per-channel ClaudeSDKClient after this many seconds of no turn
# activity. Default 15 min — comfortably past the 5-min cache TTL so the
# next turn after this re-opens with a fresh cache window anyway.
SESSION_IDLE_TIMEOUT_S = float(os.environ.get("AGENT_RUNNER_SESSION_IDLE_TIMEOUT_S", "900"))

# Hard ceiling on concurrent pool slots. Each slot is a live Node subprocess,
# and og118 keys slots by client-minted conversation UUIDs (OG118-CONTINUITY),
# so without a cap an authed caller can grow the pool without bound — the
# 2026-05-22 judge pile-up OOM'd this exact 1-CPU/2Gi runner. At the cap the
# least-recently-used slot is closed before a new one opens: Discord channels
# keep durable context in the workspace and og118 reseeds from replayed
# history, so an eviction costs one cold start, never permanent context loss.
MAX_POOL_SESSIONS = int(os.environ.get("AGENT_RUNNER_MAX_POOL_SESSIONS", "8"))

# Max concurrent /v1/judge SDK calls. Default 1 — the judge spawns a FRESH
# Node subprocess per call (no session pool) and generates thousands of tokens
# (the SDK has no max_tokens cap). On 2026-05-22 a consolidator backlog fired
# ~25 judges at once on a 1-CPU/2Gi runner: the subprocess pile-up OOM-killed
# the chat turns' SDK and starved their CPU (p50 turn latency 27-53s). Judges
# are background utility work (consolidator, fact-extraction, summaries) — the
# user is NOT waiting on them — so serializing them protects the interactive
# turns. Override via env for a bigger runner.
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
