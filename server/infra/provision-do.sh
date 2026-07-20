#!/usr/bin/env bash
set -euo pipefail

# AIRE — reproducible provisioning of the daemon droplet on DigitalOcean.
# The EC-GPS model: "the primordial skeleton of the daemon" — Ubuntu 24.04,
# root, keeps AIRE's listener up 24/7. Born on DO (Azure's whole B-series was
# blocked at subscription level). Run ONCE from your machine (doctl already
# authenticated); after that the CI/CD deploys on every push. Idempotent:
# reuses the SSH key and the droplet if they already exist. See infra/README.md.
# The steps live in infra/lib/*.sh (thirty-line law); the on-droplet half is
# infra/remote-bootstrap.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="aire-droplet"
REGION="${REGION:-nyc3}"
SIZE="${SIZE:-s-1vcpu-512mb-10gb}"     # cheapest (~$4/mo); fallback s-1vcpu-1gb (~$6/mo)
IMAGE="ubuntu-24-04-x64"
SSH_KEY="$HOME/.ssh/aire_vm"           # key pair dedicated to this droplet
DEPLOY_KEY="$HOME/.secrets/aire-github-deploy-key.txt"   # read-only, private repo
PEN_SECRET="$HOME/.secrets/aire-postgres.txt"
VERB_TOKEN_FILE="$HOME/.secrets/aire-verb-token.txt"
LLM_TOKEN_FILE="$HOME/.secrets/aire-llm-token.txt"
OAUTH_FILE="$HOME/.secrets/aire-claude-oauth.txt"
WHITELIST_FILE="$HOME/.secrets/aire-whitelist.txt"
REPO_URL="git@github.com:BernardUriza/aire-server.git"
REMOTE_DIR="/opt/aire"
PG_SERVER="development-pg-n66dz"          # the pen's Azure Postgres
PG_RG="insult-rg"

source "$SCRIPT_DIR/lib/keys.sh"
source "$SCRIPT_DIR/lib/droplet.sh"
source "$SCRIPT_DIR/lib/secrets.sh"
source "$SCRIPT_DIR/lib/pgfirewall.sh"

echo "==> AIRE provision (DigitalOcean)"
echo "    NAME=$NAME  REGION=$REGION  SIZE=$SIZE  IMAGE=$IMAGE"
echo "==> [0/6] Checking doctl auth…"
doctl account get --format Email --no-header >/dev/null

ensure_ssh_key
ensure_do_fingerprint
ensure_droplet
capture_ip
ensure_pg_firewall

echo "==> [5/6] Remote bootstrap on $IP (clone repo, install units, start daemon)…"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"
for i in $(seq 1 10); do  # a freshly created droplet takes a moment to accept ssh
  if $SSH "root@${IP}" true 2>/dev/null; then break; fi
  echo "    waiting for sshd… ($i/10)"; sleep 6
done

install_deploy_key
compose_env
$SSH "root@${IP}" REPO_URL="$REPO_URL" REMOTE_DIR="$REMOTE_DIR" 'bash -s' \
  < "$SCRIPT_DIR/remote-bootstrap.sh"
echo "    bootstrap OK — services reported 'active'."

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
