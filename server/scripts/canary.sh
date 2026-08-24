#!/usr/bin/env bash
# One REAL turn per NOTCH through the public door — the only checks here that
# cannot go green while the engine is dead.
#
# `systemctl is-active` and `/health` both answered ok for a daemon whose every
# agent turn died with ProcessError (CLAUDE.md: the root/bypassPermissions
# refusal), and would answer ok today if the credential rotor ran dry, if the
# `claude` binary vanished from the image, or if Caddy relayed to nothing. They
# measure that something responded, never that it responded correctly
# ([[verify-before-assuming]] Rule 22). This measures the contract instead:
# DNS → TLS → Caddy → the door's Bearer → the SDK → Anthropic → an SSE `result`
# carrying text and a cost, from OUTSIDE the droplet.
#
# BOTH notches, because the founding defect killed exactly the one a
# `mode=complete` probe cannot see: `bypassPermissions` is refused when the
# process runs as root, so every agent turn died while complete stayed green.
# The agent probe forces a TOOL — a turn that answers without ever entering the
# tool loop proves the notch dispatched, not that it works — and the tool is
# read-only on purpose: `Write` hits the SDK's read-before-write guard the
# second day and turns the canary non-deterministic, and a file per run is a
# canary that grows the disk it watches.
#
# Env: AIRE_PULSE_TOKEN (its own consumer slot, revocable alone), AIRE_GATE_URL,
#      AIRE_CANARY_MAX_USD / AIRE_CANARY_AGENT_MAX_USD (a turn that costs more
#      than this is also a failure — a canary is how you find out the cheap path
#      stopped being cheap). Measured 2026-08-24: complete $0.002 warm / $0.028
#      cold, agent $0.0099 in 15s.
set -euo pipefail

GATE="${AIRE_GATE_URL:-https://gate.bernarduriza.com}"
MODEL="${AIRE_CANARY_MODEL:-claude-haiku-4-5-20251001}"
SESSION="pulse-$(date -u +%Y%m%d)"
COMPLETE_ASK="Reply with exactly: PONG"
AGENT_ASK="Use the Glob tool once with the pattern * to list your working directory, then reply with exactly: PONG"

if [[ -z "${AIRE_PULSE_TOKEN:-}" ]]; then
  echo "::error::AIRE_PULSE_TOKEN is missing — the canary is blind, and a blind canary reports green"
  exit 1
fi

one_turn() {  # <mode> <ask> → the raw SSE stream on stdout
  curl -sS -N -m 240 -X POST "${GATE}/projects/canary/sessions/${SESSION}-$1/messages" \
    -H "Authorization: Bearer ${AIRE_PULSE_TOKEN}" \
    -H 'content-type: application/json' \
    -d "$(jq -nc --arg m "$2" --arg mode "$1" --arg model "$MODEL" \
            '{message:$m, mode:$mode, model:$model}')"
}

verdict() {  # <stream-file> <mode> <max-usd> → 0 if the turn really completed
  local raw="$1" mode="$2" max="$3" result text cost
  result="$(grep '^data: ' "$raw" | sed 's/^data: //' | jq -c 'select(.type=="result")' | head -1)"
  if [[ -z "$result" ]]; then
    echo "no result event — the ${mode} turn never completed"
    grep '^data: ' "$raw" | tail -3
    return 1
  fi
  text="$(jq -r '.result.text // ""' <<<"$result")"
  # `.result.usage.total_cost_usd`, not `.result.total_cost_usd`: the dollars
  # ride INSIDE usage (drain.py puts them there). Reading the shallow path
  # returned null → 0 on the canary's first flight, and the "$0 with text" guard
  # below caught the canary's own bug before it could ever excuse the daemon's.
  cost="$(jq -r '.result.usage.total_cost_usd // 0' <<<"$result")"
  echo "[${mode}] text: ${text:0:40} | cost: \$${cost} | $(jq -c '.result.usage | {cache_creation_input_tokens, cache_read_input_tokens, output_tokens}' <<<"$result")"
  [[ "$text" == *PONG* ]] || { echo "the result carried no PONG — an empty turn is the budget lie (#23)"; return 1; }
  awk -v c="$cost" 'BEGIN{exit !(c+0 > 0)}' \
    || { echo "cost \$0 with text — the usage report is lying"; jq -c '.result.usage' <<<"$result"; return 1; }
  awk -v c="$cost" -v m="$max" 'BEGIN{exit !(c+0 <= m+0)}' \
    || { echo "::error::the ${mode} canary cost \$${cost} > \$${max} ceiling"; return 1; }
  [[ "$mode" == "agent" ]] && ! tools_ran "$result" && return 1
  return 0
}

tools_ran() {  # <result-json> → 0 if the turn really entered the tool loop
  local calls errs
  calls="$(jq '.result.tool_calls | length' <<<"$1")"
  errs="$(jq '[.result.tool_calls[] | select(.is_error == true)] | length' <<<"$1")"
  echo "[agent] tool calls: ${calls} ($(jq -c '[.result.tool_calls[].name]' <<<"$1")), errors: ${errs}"
  if [[ "$calls" == 0 ]]; then
    echo "::error::the agent turn answered without ever calling a tool — the notch dispatched, the tool loop did not"
    return 1
  fi
  if [[ "$errs" != 0 ]]; then
    echo "::error::a tool call came back is_error — the cage (#24) or the tool loop is refusing work the canary is allowed to do"
    return 1
  fi
  return 0
}

probe() {  # <mode> <ask> <max-usd>
  local raw start
  for attempt in 1 2; do
    raw="$(mktemp)"
    start=$(date +%s)
    if one_turn "$1" "$2" > "$raw" 2>/dev/null && verdict "$raw" "$1" "$3"; then
      echo "[$1] OK on attempt ${attempt} in $(( $(date +%s) - start ))s"
      return 0
    fi
    echo "[$1] attempt ${attempt} failed"
    if [[ "$attempt" == 1 ]]; then sleep 20; fi
  done
  echo "::error::the door did NOT complete a real $1 turn — units and /health prove nothing about this"
  return 1
}

probe complete "$COMPLETE_ASK" "${AIRE_CANARY_MAX_USD:-0.15}"
probe agent    "$AGENT_ASK"    "${AIRE_CANARY_AGENT_MAX_USD:-0.25}"
echo "canary OK — ${GATE} completes a real turn in BOTH notches"
