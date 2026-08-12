# Step 5a: the GitHub deploy key + /etc/aire/env composed from ~/.secrets/ so a
# re-provision (the kill test) resurrects the FULL droplet, not a half-configured
# one. Every out-of-band knob lives in a ~/.secrets/ file and is restored here;
# a missing file degrades that one feature, loudly.
# Sourced by provision-do.sh; expects SSH/IP and the secret-file variables.

install_deploy_key() {
  echo "    [local] installing the GitHub deploy key (private repo)…"
  if [[ ! -f "$DEPLOY_KEY" ]]; then
    echo "ERROR: $DEPLOY_KEY missing — the private repo cannot be cloned without it." >&2
    exit 1
  fi
  scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$DEPLOY_KEY" "root@${IP}:/root/.ssh/github_deploy"
  $SSH "root@${IP}" 'chmod 600 /root/.ssh/github_deploy
grep -q "^Host github.com$" /root/.ssh/config 2>/dev/null || printf "Host github.com\n  IdentityFile /root/.ssh/github_deploy\n  StrictHostKeyChecking accept-new\n" >> /root/.ssh/config'
}

append_secret() {  # <file> <KEY=> <human-name>
  if [[ -f "$1" ]]; then
    # `|| true`: a file without this key is normal (grep exits 1, and under
    # `set -euo pipefail` that would kill the whole provision — it did, 2026-07-20).
    local line; line="$(grep "^$2" "$1" | head -1 || true)"
    [[ -n "$line" ]] && ENV_CONTENT+="$line"$'\n' || true
  else
    echo "    [local] no $1 — $3 disabled."
  fi
}

compose_env() {
  echo "    [local] composing /etc/aire/env from ~/.secrets/…"
  ENV_CONTENT=""
  append_secret "$PEN_SECRET"      "AIRE_DATABASE_URL=" "the pen (Postgres mirror)"
  append_secret "$PEN_SECRET"      "AIRE_DSN="          "the engine store"
  # The engine reads AIRE_DSN (same Postgres as the pen) — derive it when the
  # file does not carry an explicit AIRE_DSN line.
  if [[ -f "$PEN_SECRET" ]] && ! grep -q '^AIRE_DSN=' "$PEN_SECRET"; then
    ENV_CONTENT+="AIRE_DSN=$(grep '^AIRE_DATABASE_URL=' "$PEN_SECRET" | cut -d= -f2-)"$'\n'
  fi
  append_secret "$VERB_TOKEN_FILE" "AIRE_VERB_TOKEN="   "the verbs (MKDIR/ALLOW/REVOKE)"
  append_secret "$LLM_TOKEN_FILE"  "AIRE_AUTH_TOKEN="   "the engine's LLM door"
  append_secret "$CANARY_TOKEN_FILE" "AIRE_CANARY_TOKEN=" "the revocable Azure-front door"
  append_secret "$OAUTH_FILE"      "CLAUDE_CODE_OAUTH_TOKEN=" "the engine's Anthropic auth"
  # The failover chain (#31): both slots are OPTIONAL — a missing file only
  # leaves that slot empty and the rotor skips it. The backup OAuth must come
  # from a DIFFERENT seat/account, or it shares the primary's weekly pool.
  append_secret "$OAUTH_BACKUP_FILE"     "CLAUDE_CODE_OAUTH_TOKEN_BACKUP=" "the failover backup OAuth (#31)"
  append_secret "$API_KEY_FALLBACK_FILE" "ANTHROPIC_API_KEY_FALLBACK="     "the failover metered API key (#31)"
  append_secret "$WHITELIST_FILE"  "AIRE_WHITELIST_ENFORCE=" "the whitelist gate"
  # The invitation flow (#32). Without these the request-access button answers
  # 503 and says so — it never silently posts a stranger into a void.
  append_secret "$ACCESS_FILE" "AIRE_ACCESS_SECRET="    "the approve link's signature (#32)"
  append_secret "$ACCESS_FILE" "AIRE_OWNER_EMAIL="      "who the doorman mails (#32)"
  append_secret "$ACCESS_FILE" "AIRE_GATE_PUBLIC_URL="  "the approve link's own host (#32)"
  append_secret "$ACCESS_FILE" "AIRE_FRONT_URL="        "where the approval receipt renders (#32)"
  append_secret "$RESEND_FILE" "RESEND_API_KEY="        "the mail transport (#32)"
  # What ONE invited stranger may spend before their key answers 402 (#32d/#28).
  # Absent, tokens.py falls back to $1.00 — this is the knob that decides how much
  # a leaked invitation can cost, so it belongs in provisioning, not in a shell.
  append_secret "$ACCESS_FILE" "AIRE_INVITE_BUDGET_USD=" "the per-invite ceiling (#32d/#28)"
  ENV_CONTENT+="AIRE_MAX_BUDGET_USD=${AIRE_MAX_BUDGET_USD:-1.0}"$'\n'
  if [[ -n "$ENV_CONTENT" ]]; then
    printf '%s' "$ENV_CONTENT" | $SSH "root@${IP}" "install -d -m 700 /etc/aire; umask 077; cat > /etc/aire/env"
  fi
}
