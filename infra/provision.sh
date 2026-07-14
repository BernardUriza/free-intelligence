#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AIRE — reproducible provisioning of the daemon VM on Azure.
#
# LEGACY / historical reference: Azure was discarded (the whole B-series was
# blocked at subscription level). The canonical script is provision-do.sh
# (DigitalOcean). See infra/README.md.
#
# Brings up ONE Ubuntu 24.04 LTS VM in an ISOLATED resource group (aire-rg)
# that runs AIRE's listener 24/7, reachable over SSH, with a greppable logfile.
#
# Run this ONCE from your machine (az already logged in). After that, the CI/CD
# (.github/workflows/deploy.yml) deploys on every push. See infra/README.md.
#
# NEVER touches any other resource group. Everything lives in $RG.
# ============================================================================

# ---- Variables -------------------------------------------------------------
RG="aire-rg"                      # NEW, isolated RG — no other RG is ever touched
LOCATION="${LOCATION:-eastus2}"   # override: LOCATION=<region> bash provision.sh
VM="aire-vm"
SIZE="${SIZE:-Standard_B1s}"      # cheapest burstable (~$0.0104/h Linux); override: SIZE=<sku>
ADMIN="azureuser"
IMAGE="Ubuntu2404"                # official alias → Canonical:ubuntu-24_04-lts:server:latest
PORT=9099                         # AIRE's listener
SSH_KEY="$HOME/.ssh/aire_vm"      # key pair dedicated to this VM
REPO_URL="https://github.com/BernardUriza/aire-server"
REMOTE_DIR="/opt/aire"

echo "==> AIRE provision"
echo "    RG=$RG  LOCATION=$LOCATION  VM=$VM  SIZE=$SIZE  IMAGE=$IMAGE  PORT=$PORT"
echo "    Everything is created in '$RG'. No other resource group is touched."

# ---- 0. Sanity: az logged in -------------------------------------------------
echo "==> [0/7] Checking az login…"
az account show --query "{name:name, id:id}" -o tsv >/dev/null

# ---- 1. ed25519 SSH key pair (only if it doesn't exist) ----------------------
echo "==> [1/7] SSH key ($SSH_KEY)…"
if [[ -f "$SSH_KEY" ]]; then
  echo "    already exists — reusing (not regenerating)."
else
  mkdir -p "$(dirname "$SSH_KEY")"
  ssh-keygen -t ed25519 -f "$SSH_KEY" -N '' -C "aire-vm"
  echo "    generated."
fi

# ---- 2. Isolated resource group ----------------------------------------------
echo "==> [2/7] Resource group '$RG'…"
if [[ "$(az group exists -n "$RG")" == "true" ]]; then
  echo "    already exists — reusing."
else
  az group create -n "$RG" -l "$LOCATION" -o none
  echo "    created in $LOCATION."
fi

# ---- 3. VM (idempotent: if it already exists, it is not recreated) -----------
echo "==> [3/7] VM '$VM'…"
if az vm show -g "$RG" -n "$VM" -o none 2>/dev/null; then
  echo "    already exists — reusing (not recreating)."
else
  az vm create \
    --resource-group "$RG" \
    --name "$VM" \
    --image "$IMAGE" \
    --size "$SIZE" \
    --admin-username "$ADMIN" \
    --ssh-key-values "${SSH_KEY}.pub" \
    --public-ip-sku Standard \
    --nic-delete-option Delete \
    --os-disk-delete-option Delete \
    --output none
  echo "    created."
fi

# ---- 4. Open ports on the NSG (distinct priorities) --------------------------
echo "==> [4/7] Opening ports on the NSG (22, $PORT)…"
az vm open-port -g "$RG" -n "$VM" --port 22    --priority 1001 -o none
az vm open-port -g "$RG" -n "$VM" --port "$PORT" --priority 1002 -o none
echo "    22 (SSH) and $PORT (listener) open."

# ---- 5. Public IP -------------------------------------------------------------
echo "==> [5/7] Capturing public IP…"
IP="$(az vm show -d -g "$RG" -n "$VM" --query publicIps -o tsv)"
if [[ -z "$IP" ]]; then
  echo "ERROR: could not obtain the VM's public IP." >&2
  exit 1
fi
echo "    IP=$IP"

# ---- 6. Remote bootstrap over SSH ---------------------------------------------
echo "==> [6/7] Remote bootstrap on $IP (clone repo, install units, start daemon)…"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"

# Wait for sshd to accept (a freshly created VM can take a few seconds).
for i in $(seq 1 10); do
  if $SSH "${ADMIN}@${IP}" true 2>/dev/null; then break; fi
  echo "    waiting for sshd… ($i/10)"; sleep 6
done

$SSH "${ADMIN}@${IP}" REPO_URL="$REPO_URL" REMOTE_DIR="$REMOTE_DIR" ADMIN="$ADMIN" 'bash -s' <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "    [remote] base packages (git, python3)…"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 >/dev/null

echo "    [remote] repo at $REMOTE_DIR…"
if [[ -d "$REMOTE_DIR/.git" ]]; then
  # already cloned and owned by $ADMIN → git as the user itself (no sudo,
  # avoids git's "dubious ownership" when running as root on someone else's dir).
  git -C "$REMOTE_DIR" fetch --all --quiet
  git -C "$REMOTE_DIR" reset --hard origin/main
else
  # first clone: /opt belongs to root → sudo to create, then hand over to $ADMIN.
  sudo git clone "$REPO_URL" "$REMOTE_DIR"
  sudo chown -R "$ADMIN" "$REMOTE_DIR"
fi

echo "    [remote] systemd units…"
sudo cp "$REMOTE_DIR/deploy/aire-listener.service" "$REMOTE_DIR/deploy/aire-device.service" /etc/systemd/system/

echo "    [remote] NOPASSWD sudoers entry for the CI restart…"
echo "$ADMIN ALL=(root) NOPASSWD: /usr/bin/systemctl restart aire-listener aire-device" \
  | sudo tee /etc/sudoers.d/aire-deploy >/dev/null
sudo chmod 440 /etc/sudoers.d/aire-deploy

echo "    [remote] daemon-reload + enable --now…"
sudo systemctl daemon-reload
sudo systemctl enable --now aire-listener aire-device

echo "    [remote] verifying real state…"
sleep 3
# is-active with multiple units exits 0 if AT LEAST ONE is active — check each
# unit on its own so a dead one actually fails the bootstrap.
for u in aire-listener aire-device; do
  if ! systemctl --quiet is-active "$u"; then
    echo "$u is NOT active"
    systemctl status "$u" --no-pager || true
    exit 1
  fi
  echo "$u active"
done
REMOTE

echo "    bootstrap OK — services reported 'active'."

# ---- 7. Final output -----------------------------------------------------------
echo ""
echo "============================================================"
echo "  AIRE VM READY"
echo "============================================================"
echo "  Public IP : $IP"
echo "  SSH       : ssh -i $SSH_KEY ${ADMIN}@${IP}"
echo "  Log       : ssh -i $SSH_KEY ${ADMIN}@${IP} 'tail -f $REMOTE_DIR/aire.log'"
echo ""
echo "  Set the GitHub secrets so the CI/CD deploys on every push:"
echo "    gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b \"$IP\""
echo "    cat $SSH_KEY | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server"
echo "============================================================"
