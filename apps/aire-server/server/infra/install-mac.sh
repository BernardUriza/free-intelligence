#!/usr/bin/env bash
# The Mac box (backlog #52): AIRE as a launchd agent on Bernard's Mac — the one
# body allowed to spawn Codex on the ChatGPT plan. Idempotent; re-running IS the
# deploy (no CI reaches this box). Everything lives under ~/.aire; the memory
# does not: it is the owner's Postgres, the same one the droplet writes.
set -euo pipefail

AIRE_HOME="$HOME/.aire"
SRC="$AIRE_HOME/src"
VENV="$AIRE_HOME/venv"
ENV_FILE="$AIRE_HOME/env"
CODEX="$AIRE_HOME/codex/node_modules/.bin/codex"
LABEL="com.bernarduriza.aire"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
REPO="${AIRE_REPO:-https://github.com/BernardUriza/free-intelligence.git}"
REF="${AIRE_REF:-main}"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3.13}"
PORT="${AIRE_PORT:-8088}"
SECRETS="$HOME/.secrets"

checkout() {
  echo "    [mac] source checkout at $SRC (sparse: the server only)…"
  if [[ ! -d "$SRC/.git" ]]; then
    git clone -q --filter=blob:none --sparse "$REPO" "$SRC"
    git -C "$SRC" sparse-checkout set apps/aire-server/server
  fi
  git -C "$SRC" fetch -q origin "$REF"
  git -C "$SRC" reset -q --hard FETCH_HEAD
  echo "    [mac] at $(git -C "$SRC" rev-parse --short HEAD) ($REF)"
}

venv() {
  echo "    [mac] python venv + deps…"
  [[ -d "$VENV" ]] || "$PYTHON" -m venv "$VENV"
  PIP_USER=0 "$VENV/bin/pip" install -q --no-input -r "$SRC/apps/aire-server/server/requirements.txt"
}

codex_agent() {
  echo "    [mac] the Codex agent (AIRE's only user of the ChatGPT plan)…"
  if [[ ! -x "$CODEX" ]]; then
    mkdir -p "$AIRE_HOME/codex"
    npm install -q --prefix "$AIRE_HOME/codex" @openai/codex
  fi
  echo "    [mac] $("$CODEX" --version)"
  if [[ ! -f "$HOME/.codex/auth.json" ]]; then
    echo "ERROR: Codex is not signed in. Run: $CODEX login  (ChatGPT, Bernard's plan)" >&2
    exit 1
  fi
}

secret_line() {  # <file> <KEY=> <human-name>
  local f="$SECRETS/$1"
  if [[ ! -f "$f" ]]; then echo "ERROR: $f missing — $3 cannot be configured." >&2; exit 1; fi
  grep "^$2" "$f" | head -1
}

optional_line() {  # <file> <KEY=> — a missing file leaves that rotor slot empty (#31, #53)
  local f="$SECRETS/$1"
  [[ -f "$f" ]] && grep "^$2" "$f" | head -1 || true
}

compose_env() {
  echo "    [mac] composing $ENV_FILE from ~/.secrets/…"
  mkdir -p "$AIRE_HOME/workspaces" "$AIRE_HOME/log"
  {
    echo "AIRE_WORKSPACES=$AIRE_HOME/workspaces"
    echo "AIRE_PORT=$PORT"
    echo "AIRE_ISOLATE_CONFIG=1"
    echo "AIRE_CODEX_COMMAND=$CODEX"
    # The rotor's codex chain (#53): the plan seat `codex login` left here, then a metered key behind it.
    echo "CODEX_HOME=$HOME/.codex"
    optional_line aire-codex-api-key-fallback.txt "CODEX_API_KEY_FALLBACK="
    secret_line aire-postgres.txt  "AIRE_DATABASE_URL=" "the database (pen, store, mirror)"
    secret_line aire-llm-token.txt "AIRE_AUTH_TOKEN="   "the engine's LLM door"
  } > "$ENV_FILE.tmp"
  chmod 600 "$ENV_FILE.tmp"
  mv "$ENV_FILE.tmp" "$ENV_FILE"
}

install_agent() {
  echo "    [mac] launchd agent ${LABEL}…"
  mkdir -p "$HOME/Library/LaunchAgents"
  sed "s|__HOME__|$HOME|g" "$SRC/apps/aire-server/server/deploy/mac/$LABEL.plist" > "$PLIST"
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  wait_unloaded
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
}

wait_unloaded() {
  # bootout returns before launchd drops the job; a bootstrap in that window
  # fails with "5: Input/output error" (reproduced 2026-10-26, exit 5).
  local i
  for i in $(seq 1 20); do
    launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || return 0
    sleep 0.5
  done
  echo "ERROR: $LABEL still loaded after bootout" >&2
  exit 1
}

verify() {
  echo "    [mac] verifying real state…"
  local i body
  for i in $(seq 1 30); do
    body="$(curl -s -m 2 "http://127.0.0.1:$PORT/health" || true)"
    [[ "$body" == *'"status":"ok"'* ]] && break
    sleep 1
  done
  if [[ "$body" != *'"status":"ok"'* ]]; then
    echo "$LABEL is NOT serving on :$PORT"; tail -20 "$AIRE_HOME/log/aire.err.log" || true
    exit 1
  fi
  echo "    [mac] /health $body"
  launchctl print "gui/$(id -u)/$LABEL" | grep -E "state =|pid =" | sed 's/^/    [mac] /'
}

checkout
venv
codex_agent
compose_env
install_agent
verify
echo "    [mac] done — the door is http://127.0.0.1:$PORT, Bearer from ~/.secrets/aire-llm-token.txt"
