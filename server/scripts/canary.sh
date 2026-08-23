#!/usr/bin/env bash
# One REAL turn through the public door — the only check here that cannot go
# green while the engine is dead.
#
# `systemctl is-active` and `/health` both answered ok for a daemon whose every
# agent turn died with ProcessError (CLAUDE.md: the root/bypassPermissions
# refusal), and would answer ok today if the credential rotor ran dry, if the
# `claude` binary vanished from the image, or if Caddy relayed to nothing. They
# measure that something responded, never that it responded correctly
# ([[verify-before-assuming]] Rule 22). This spends $0.028 to measure the
# contract instead: DNS → TLS → Caddy → the door's Bearer → the SDK → Anthropic
# → an SSE `result` carrying text and a cost, from OUTSIDE the droplet.
#
# Env: AIRE_PULSE_TOKEN (its own consumer slot, revocable alone), AIRE_GATE_URL,
#      AIRE_CANARY_MAX_USD (a turn that costs more than this is also a failure —
#      a canary is how you find out the cheap path stopped being cheap).
set -euo pipefail

GATE="${AIRE_GATE_URL:-https://gate.bernarduriza.com}"
MODEL="${AIRE_CANARY_MODEL:-claude-haiku-4-5-20251001}"
MAX_USD="${AIRE_CANARY_MAX_USD:-0.15}"
SESSION="pulse-$(date -u +%Y%m%d)"

if [[ -z "${AIRE_PULSE_TOKEN:-}" ]]; then
  echo "::error::AIRE_PULSE_TOKEN is missing — the canary is blind, and a blind canary reports green"
  exit 1
fi

one_turn() {  # → the raw SSE stream on stdout
  curl -sS -N -m 180 -X POST "${GATE}/projects/canary/sessions/${SESSION}/messages" \
    -H "Authorization: Bearer ${AIRE_PULSE_TOKEN}" \
    -H 'content-type: application/json' \
    -d "{\"message\":\"Reply with exactly: PONG\",\"mode\":\"complete\",\"model\":\"${MODEL}\"}"
}

verdict() {  # <stream-file> → 0 if the turn really completed
  local raw="$1" result text cost
  result="$(grep '^data: ' "$raw" | sed 's/^data: //' | jq -c 'select(.type=="result")' | head -1)"
  if [[ -z "$result" ]]; then
    echo "no result event — the turn never completed"
    grep '^data: ' "$raw" | tail -3
    return 1
  fi
  text="$(jq -r '.result.text // ""' <<<"$result")"
  cost="$(jq -r '.result.total_cost_usd // 0' <<<"$result")"
  echo "text: ${text:0:40} | cost: \$${cost}"
  [[ -n "$text" ]] || { echo "the result carried NO text — an empty turn is the budget lie (#23)"; return 1; }
  awk -v c="$cost" 'BEGIN{exit !(c+0 > 0)}' || { echo "cost \$0 with text — the usage report is lying"; return 1; }
  awk -v c="$cost" -v m="$MAX_USD" 'BEGIN{exit !(c+0 <= m+0)}' \
    || { echo "::error::the canary cost \$${cost} > \$${MAX_USD} ceiling"; return 1; }
}

for attempt in 1 2; do
  RAW="$(mktemp)"
  START=$(date +%s)
  if one_turn > "$RAW" 2>/dev/null && verdict "$RAW"; then
    echo "canary OK on attempt ${attempt} in $(( $(date +%s) - START ))s — ${GATE} completes a real turn"
    exit 0
  fi
  echo "attempt ${attempt} failed"
  [[ $attempt == 1 ]] && sleep 20
done
echo "::error::the door did NOT complete a real turn — units and /health prove nothing about this"
exit 1
