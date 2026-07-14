#!/usr/bin/env bash
# Corre DENTRO de la VM (como root). Idempotente: se puede volver a correr.
# Clona el repo público, crea el usuario de servicio, instala los systemd units
# y arranca el daemon + el device. Todo stdlib — no hay pip, no hay venv.
set -euo pipefail

REPO="https://github.com/BernardUriza/aire-server.git"
DIR=/opt/aire

# usuario de servicio (sin login)
id aire &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin aire

# código
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch --all && git -C "$DIR" reset --hard origin/main
else
  git clone "$REPO" "$DIR"
fi
chown -R aire:aire "$DIR"

# servicios
cp "$DIR/deploy/aire-listener.service"    /etc/systemd/system/
cp "$DIR/deploy/aire-demo-device.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now aire-listener aire-demo-device

sleep 3
echo "==== estado ===="
systemctl is-active aire-listener aire-demo-device
echo "==== primeras líneas del log ===="
tail -n 6 "$DIR/aire.log" 2>/dev/null || echo "(aún sin log)"
