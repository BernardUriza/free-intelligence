#!/usr/bin/env bash
# Local dev launcher. Sources the gitignored .env.local and picks ONE auth mode
# deterministically — never prints the secret values:
#   - ANTHROPIC_API_KEY present  -> API-billing mode (cloud parity). OAuth token
#     is unset so the Claude CLI can't silently prefer the subscription.
#   - else CLAUDE_CODE_OAUTH_TOKEN present -> OAuth Max subscription (local/dev).
# To force OAuth locally while the API key sits in .env.local, comment the
# ANTHROPIC_API_KEY line there.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source .venv/bin/activate
set -a; [ -f .env.local ] && source .env.local; set +a

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  unset CLAUDE_CODE_OAUTH_TOKEN || true
  echo "auth mode: ANTHROPIC_API_KEY (API billing)"
elif [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  unset ANTHROPIC_API_KEY || true
  echo "auth mode: CLAUDE_CODE_OAUTH_TOKEN (OAuth Max subscription)"
else
  echo "ERROR: set ANTHROPIC_API_KEY (API mode) or CLAUDE_CODE_OAUTH_TOKEN (OAuth) in .env.local" >&2
  exit 1
fi

exec uvicorn app:app --port 8118 --log-level info
