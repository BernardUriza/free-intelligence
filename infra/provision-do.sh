#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AIRE — reproducible provisioning of the daemon droplet on DigitalOcean.
#
# The EC-GPS model: "the primordial skeleton of the daemon". An Ubuntu 24.04
# droplet, running as root, that keeps AIRE's listener up 24/7.
#
# Pivot away from Azure: the whole B-series was blocked at subscription level,
# so AIRE is born on DO — cheaper and more natural for a daemon-in-a-box.
#
# Run this ONCE from your machine (doctl already authenticated via `doctl auth
# init`). After that, the CI/CD (.github/workflows/deploy.yml) deploys on every
# push. See infra/README.md.
#
# Idempotent: reuses the SSH key and the droplet if they already exist.
# ============================================================================

# ---- Variables -------------------------------------------------------------
NAME="aire-droplet"
REGION="${REGION:-nyc3}"
SIZE="${SIZE:-s-1vcpu-512mb-10gb}"     # cheapest (~$4/mo); fallback s-1vcpu-1gb (~$6/mo)
IMAGE="ubuntu-24-04-x64"
SSH_KEY="$HOME/.ssh/aire_vm"           # key pair dedicated to this droplet
# The repo is PRIVATE — the droplet clones over SSH with the read-only deploy
# key, installed below at /root/.ssh/github_deploy from ~/.secrets/.
DEPLOY_KEY="$HOME/.secrets/aire-github-deploy-key.txt"
PEN_SECRET="$HOME/.secrets/aire-postgres.txt"
VERB_TOKEN_FILE="$HOME/.secrets/aire-verb-token.txt"
LLM_TOKEN_FILE="$HOME/.secrets/aire-llm-token.txt"
OAUTH_FILE="$HOME/.secrets/og118-claude-oauth.txt"
WHITELIST_FILE="$HOME/.secrets/aire-whitelist.txt"
REPO_URL="git@github.com:BernardUriza/aire-server.git"
REMOTE_DIR="/opt/aire"

echo "==> AIRE provision (DigitalOcean)"
echo "    NAME=$NAME  REGION=$REGION  SIZE=$SIZE  IMAGE=$IMAGE"

# ---- 0. Sanity: doctl authenticated ----------------------------------------
echo "==> [0/6] Checking doctl auth…"
doctl account get --format Email --no-header >/dev/null

# ---- 1. ed25519 SSH key pair (only if it doesn't exist) --------------------
echo "==> [1/6] SSH key ($SSH_KEY)…"
if [[ -f "$SSH_KEY" ]]; then
  echo "    already exists — reusing (not regenerating)."
else
  mkdir -p "$(dirname "$SSH_KEY")"
  ssh-keygen -t ed25519 -f "$SSH_KEY" -N '' -C "aire-vm"
  echo "    generated."
fi

# ---- 2. Public key in DO (import if missing, or reuse its fingerprint) -----
echo "==> [2/6] Public key in DigitalOcean…"
FINGERPRINT="$(doctl compute ssh-key list --format Name,FingerPrint --no-header \
  | awk '$1 == "aire-vm" { print $2; exit }')"

if [[ -z "$FINGERPRINT" ]]; then
  echo "    'aire-vm' not in DO — importing…"
  FINGERPRINT="$(doctl compute ssh-key import aire-vm \
    --public-key-file "${SSH_KEY}.pub" \
    --format FingerPrint --no-header)"
  echo "    imported. fingerprint=$FINGERPRINT"
else
  echo "    'aire-vm' already in DO — reusing. fingerprint=$FINGERPRINT"
fi

if [[ -z "$FINGERPRINT" ]]; then
  echo "ERROR: could not obtain the SSH key fingerprint." >&2
  exit 1
fi

# ---- 3. Droplet (idempotent: if it already exists, it is not recreated) ----
echo "==> [3/6] Droplet '$NAME'…"
if doctl compute droplet get "$NAME" --format ID --no-header >/dev/null 2>&1; then
  echo "    already exists — reusing (not recreating)."
else
  echo "    creating (--wait: blocks until ready)…"
  doctl compute droplet create "$NAME" \
    --region "$REGION" \
    --size "$SIZE" \
    --image "$IMAGE" \
    --ssh-keys "$FINGERPRINT" \
    --wait \
    --format ID,Name,Region,Status --no-header
  echo "    created."
fi

# ---- 4. Public IP -----------------------------------------------------------
echo "==> [4/6] Capturing public IP…"
IP="$(doctl compute droplet get "$NAME" --format PublicIPv4 --no-header)"
if [[ -z "$IP" ]]; then
  echo "ERROR: could not obtain the droplet's public IP." >&2
  exit 1
fi
echo "    IP=$IP"

# ---- 5. Remote bootstrap over SSH -------------------------------------------
echo "==> [5/6] Remote bootstrap on $IP (clone repo, install units, start daemon)…"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"

# Wait for sshd to accept (a freshly created droplet can take a few seconds).
for i in $(seq 1 10); do
  if $SSH "root@${IP}" true 2>/dev/null; then break; fi
  echo "    waiting for sshd… ($i/10)"; sleep 6
done

echo "    [local] installing the GitHub deploy key (private repo)…"
if [[ ! -f "$DEPLOY_KEY" ]]; then
  echo "ERROR: $DEPLOY_KEY missing — the private repo cannot be cloned without it." >&2
  exit 1
fi
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$DEPLOY_KEY" "root@${IP}:/root/.ssh/github_deploy"
$SSH "root@${IP}" 'chmod 600 /root/.ssh/github_deploy
grep -q "^Host github.com$" /root/.ssh/config 2>/dev/null || printf "Host github.com\n  IdentityFile /root/.ssh/github_deploy\n  StrictHostKeyChecking accept-new\n" >> /root/.ssh/config'

# Compose /etc/aire/env from ALL operational secrets so a re-provision (the kill
# test) resurrects the FULL droplet, not a half-configured one. Every knob set
# out-of-band this session lives in a ~/.secrets/ file and is restored here:
# the pen DSN, the verb token, the engine's Bearer + OAuth + budget, and the
# whitelist enforcement flag. A missing file degrades that one feature, loudly.
echo "    [local] composing /etc/aire/env from ~/.secrets/…"
ENV_CONTENT=""
append_secret() {  # <file> <KEY=> <human-name>
  if [[ -f "$1" ]]; then
    local line; line="$(grep "^$2" "$1" | head -1)"
    [[ -n "$line" ]] && ENV_CONTENT+="$line"$'\n'
  else
    echo "    [local] no $1 — $3 disabled."
  fi
}
append_secret "$PEN_SECRET"        "AIRE_DATABASE_URL=" "the pen (Postgres mirror)"
append_secret "$PEN_SECRET"        "AIRE_DSN="          "the engine store"  # if the file also carries AIRE_DSN
# The engine reads AIRE_DSN; it is the same Postgres as the pen. Derive it from
# the pen DSN when the file does not carry an explicit AIRE_DSN line.
if [[ -f "$PEN_SECRET" ]] && ! grep -q '^AIRE_DSN=' "$PEN_SECRET"; then
  ENV_CONTENT+="AIRE_DSN=$(grep '^AIRE_DATABASE_URL=' "$PEN_SECRET" | cut -d= -f2-)"$'\n'
fi
append_secret "$VERB_TOKEN_FILE"   "AIRE_VERB_TOKEN="   "the verbs (MKDIR/ALLOW/REVOKE)"
append_secret "$LLM_TOKEN_FILE"    "AIRE_AUTH_TOKEN="   "the engine's LLM door"
append_secret "$OAUTH_FILE"        "CLAUDE_CODE_OAUTH_TOKEN=" "the engine's Anthropic auth"
append_secret "$WHITELIST_FILE"    "AIRE_WHITELIST_ENFORCE=" "the whitelist gate"
ENV_CONTENT+="AIRE_MAX_BUDGET_USD=${AIRE_MAX_BUDGET_USD:-1.0}"$'\n'
if [[ -n "$ENV_CONTENT" ]]; then
  printf '%s' "$ENV_CONTENT" | $SSH "root@${IP}" "install -d -m 700 /etc/aire; umask 077; cat > /etc/aire/env"
fi

$SSH "root@${IP}" REPO_URL="$REPO_URL" REMOTE_DIR="$REMOTE_DIR" 'bash -s' <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "    [remote] base packages (git, python3, venv, asyncpg)…"
# A fresh droplet's cloud-init holds the dpkg lock for a while — wait, don't race.
APT="apt-get -o DPkg::Lock::Timeout=300"
$APT update -qq
$APT install -y -qq git python3 python3-venv python3-asyncpg tmux >/dev/null

echo "    [remote] swap (the Claude CLI is memory-hungry on a 512MB box)…"
if [[ ! -f /swapfile ]]; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile -q \
    && swapon /swapfile && echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "    [remote] /etc/aire (out-of-band secrets)…"
install -d -m 700 /etc/aire

echo "    [remote] repo at $REMOTE_DIR…"
if [[ -d "$REMOTE_DIR/.git" ]]; then
  git -C "$REMOTE_DIR" fetch --all --quiet
  git -C "$REMOTE_DIR" reset --hard origin/main
else
  git clone "$REPO_URL" "$REMOTE_DIR"
fi

echo "    [remote] python venv + deps (the engine)…"
[[ -d "$REMOTE_DIR/.venv" ]] || python3 -m venv "$REMOTE_DIR/.venv"
"$REMOTE_DIR/.venv/bin/pip" install -q --no-input -r "$REMOTE_DIR/requirements.txt"

echo "    [remote] Claude CLI (the engine's subprocess AND the SSH door)…"
command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash >/dev/null 2>&1

echo "    [remote] systemd units (listener + engine + broom; device installed, not enabled)…"
cp "$REMOTE_DIR/deploy/aire-listener.service" "$REMOTE_DIR/deploy/aire-device.service" \
   "$REMOTE_DIR/deploy/aire-server.service" \
   "$REMOTE_DIR/deploy/aire-sweep.service" "$REMOTE_DIR/deploy/aire-sweep.timer" /etc/systemd/system/
cp "$REMOTE_DIR/deploy/logrotate-aire" /etc/logrotate.d/aire

echo "    [remote] daemon-reload + enable --now (device stays disabled — it's retired)…"
systemctl daemon-reload
systemctl enable --now aire-listener aire-server aire-sweep.timer

echo "    [remote] verifying real state…"
sleep 3
# is-active with multiple units exits 0 if AT LEAST ONE is active — check each
# unit on its own so a dead one actually fails the bootstrap.
for u in aire-listener aire-server aire-sweep.timer; do
  if ! systemctl --quiet is-active "$u"; then
    echo "$u is NOT active"
    systemctl status "$u" --no-pager || true
    exit 1
  fi
  echo "$u active"
done
REMOTE

echo "    bootstrap OK — services reported 'active'."

# ---- 6. Final output ---------------------------------------------------------
echo ""
echo "============================================================"
echo "  AIRE DROPLET READY"
echo "============================================================"
echo "  Public IP : $IP"
echo "  SSH       : ssh -i ~/.ssh/aire_vm root@$IP"
echo "  Log       : ssh -i ~/.ssh/aire_vm root@$IP 'tail -f $REMOTE_DIR/aire.log'"
echo ""
echo "  Set the GitHub secrets so the CI/CD deploys on every push:"
echo "    gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b \"$IP\""
echo "    cat ~/.ssh/aire_vm | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server"
echo "============================================================"
