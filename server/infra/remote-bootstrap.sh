#!/usr/bin/env bash
# Step 5b — runs ON the droplet (piped via `ssh bash -s`): packages, swap, repo,
# venv, Claude CLI, systemd units, and the real-state verification.
# Expects REPO_URL and REMOTE_DIR in the environment (passed by provision-do.sh).
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

install_packages() {
  echo "    [remote] base packages (git, python3, venv, asyncpg)…"
  # A fresh droplet's cloud-init holds the dpkg lock for a while — wait, don't race.
  local APT="apt-get -o DPkg::Lock::Timeout=300"
  $APT update -qq
  $APT install -y -qq git python3 python3-venv python3-asyncpg tmux >/dev/null
}

ensure_swap() {
  echo "    [remote] swap (the Claude CLI is memory-hungry on a 512MB box)…"
  if [[ ! -f /swapfile ]]; then
    fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile -q \
      && swapon /swapfile && echo "/swapfile none swap sw 0 0" >> /etc/fstab
  fi
}

sync_repo() {
  echo "    [remote] repo at $REMOTE_DIR…"
  if [[ -d "$REMOTE_DIR/.git" ]]; then
    git -C "$REMOTE_DIR" fetch --all --quiet
    git -C "$REMOTE_DIR" reset --hard origin/main
  else
    git clone "$REPO_URL" "$REMOTE_DIR"
  fi
}

install_runtime() {
  echo "    [remote] python venv + deps (the engine)…"
  [[ -d "$REMOTE_DIR/.venv" ]] || python3 -m venv "$REMOTE_DIR/.venv"
  "$REMOTE_DIR/.venv/bin/pip" install -q --no-input -r "$REMOTE_DIR/server/requirements.txt"
  echo "    [remote] Claude CLI (the engine's subprocess AND the SSH door)…"
  command -v claude >/dev/null 2>&1 || curl -fsSL https://claude.ai/install.sh | bash >/dev/null 2>&1
}

install_units() {
  echo "    [remote] systemd units (listener + engine + broom; device installed, not enabled)…"
  cp "$REMOTE_DIR/server/deploy/aire-listener.service" "$REMOTE_DIR/server/deploy/aire-device.service" \
     "$REMOTE_DIR/server/deploy/aire-server.service" \
     "$REMOTE_DIR/server/deploy/aire-sweep.service" "$REMOTE_DIR/server/deploy/aire-sweep.timer" \
     "$REMOTE_DIR/server/deploy/aire-tick.service" "$REMOTE_DIR/server/deploy/aire-tick.timer" /etc/systemd/system/
  cp "$REMOTE_DIR/server/deploy/logrotate-aire" /etc/logrotate.d/aire
  systemctl daemon-reload
  systemctl enable --now aire-listener aire-server aire-sweep.timer aire-tick.timer
}

verify_units() {
  echo "    [remote] verifying real state…"
  sleep 3
  # is-active with multiple units exits 0 if AT LEAST ONE is active — check each
  # unit on its own so a dead one actually fails the bootstrap.
  local u
  for u in aire-listener aire-server aire-sweep.timer; do
    if ! systemctl --quiet is-active "$u"; then
      echo "$u is NOT active"
      systemctl status "$u" --no-pager || true
      exit 1
    fi
    echo "$u active"
  done
}

install_packages
ensure_swap
echo "    [remote] /etc/aire (out-of-band secrets)…"
install -d -m 700 /etc/aire
sync_repo
install_runtime
install_units
verify_units
