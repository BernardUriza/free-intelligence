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
REPO_URL="https://github.com/BernardUriza/aire-server"
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

$SSH "root@${IP}" REPO_URL="$REPO_URL" REMOTE_DIR="$REMOTE_DIR" 'bash -s' <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "    [remote] base packages (git, python3)…"
apt-get update -qq
apt-get install -y -qq git python3 >/dev/null

echo "    [remote] repo at $REMOTE_DIR…"
if [[ -d "$REMOTE_DIR/.git" ]]; then
  git -C "$REMOTE_DIR" fetch --all --quiet
  git -C "$REMOTE_DIR" reset --hard origin/main
else
  git clone "$REPO_URL" "$REMOTE_DIR"
fi

echo "    [remote] systemd units…"
cp "$REMOTE_DIR/deploy/aire-listener.service" "$REMOTE_DIR/deploy/aire-device.service" /etc/systemd/system/

echo "    [remote] daemon-reload + enable --now…"
systemctl daemon-reload
systemctl enable --now aire-listener aire-device

echo "    [remote] verifying real state…"
sleep 1
systemctl is-active aire-listener aire-device
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
