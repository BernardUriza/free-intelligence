#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

HOST="${HOST:?Set HOST to the VM public IP or DNS name}"
ADMIN_USER="${ADMIN_USER:-azureuser}"
REMOTE_DIR="${REMOTE_DIR:-/opt/arbor-tts}"

rsync -az --delete \
  --exclude node_modules \
  --exclude auth \
  --exclude output \
  --exclude .env \
  "$REPO_ROOT/arbor-tts/" "$ADMIN_USER@$HOST:/tmp/arbor-tts/"

ssh "$ADMIN_USER@$HOST" "sudo rsync -a --delete /tmp/arbor-tts/ '$REMOTE_DIR/' && sudo chown -R arbor:arbor '$REMOTE_DIR'"

scp "$SCRIPT_DIR/arbor-tts.service" "$ADMIN_USER@$HOST:/tmp/arbor-tts.service"
scp "$SCRIPT_DIR/nginx-arbor-tts.conf" "$ADMIN_USER@$HOST:/tmp/nginx-arbor-tts.conf"

ssh "$ADMIN_USER@$HOST" "\
  sudo mv /tmp/arbor-tts.service /etc/systemd/system/arbor-tts.service && \
  sudo mv /tmp/nginx-arbor-tts.conf /etc/nginx/sites-available/arbor-tts && \
  sudo ln -sf /etc/nginx/sites-available/arbor-tts /etc/nginx/sites-enabled/default && \
  cd '$REMOTE_DIR' && sudo -u arbor npm ci && \
  sudo env PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright npx playwright install --with-deps chromium && \
  sudo chmod -R a+rX /opt/ms-playwright && \
  sudo systemctl daemon-reload && sudo systemctl enable arbor-tts && \
  sudo nginx -t && sudo systemctl restart nginx && sudo systemctl restart arbor-tts && \
  sudo systemctl --no-pager --full status arbor-tts | sed -n '1,20p'"

echo
echo "Deployed. Check:"
echo "curl -s http://$HOST/health"
