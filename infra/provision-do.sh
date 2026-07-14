#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AIRE — provisión reproducible del droplet daemon en DigitalOcean.
#
# El modelo de EC-GPS: "el esqueleto primigenio del daemon". Un droplet Ubuntu
# 24.04, corriendo como root, que levanta el listener de AIRE 24/7.
#
# Pivote desde Azure: toda la B-series quedó bloqueada a nivel suscripción, así
# que AIRE nace en DO — más barato y natural para un daemon-en-caja.
#
# Corre esto UNA vez desde tu máquina (doctl ya autenticado con `doctl auth
# init`). Después el CI/CD (.github/workflows/deploy.yml) despliega en cada push.
# Ver infra/README.md.
#
# Idempotente: reutiliza la llave SSH y el droplet si ya existen.
# ============================================================================

# ---- Variables -------------------------------------------------------------
NAME="aire-droplet"
REGION="${REGION:-nyc3}"
SIZE="${SIZE:-s-1vcpu-512mb-10gb}"     # el más barato (~$4/mo); fallback s-1vcpu-1gb (~$6/mo)
IMAGE="ubuntu-24-04-x64"
SSH_KEY="$HOME/.ssh/aire_vm"           # par de llaves dedicado a este droplet
REPO_URL="https://github.com/BernardUriza/aire-server"
REMOTE_DIR="/opt/aire"

echo "==> AIRE provision (DigitalOcean)"
echo "    NAME=$NAME  REGION=$REGION  SIZE=$SIZE  IMAGE=$IMAGE"

# ---- 0. Sanity: doctl autenticado ------------------------------------------
echo "==> [0/6] Verificando auth de doctl…"
doctl account get --format Email --no-header >/dev/null

# ---- 1. Par de llaves SSH ed25519 (solo si no existe) ----------------------
echo "==> [1/6] Llave SSH ($SSH_KEY)…"
if [[ -f "$SSH_KEY" ]]; then
  echo "    ya existe — se reutiliza (no se regenera)."
else
  mkdir -p "$(dirname "$SSH_KEY")"
  ssh-keygen -t ed25519 -f "$SSH_KEY" -N '' -C "aire-vm"
  echo "    generada."
fi

# ---- 2. Llave pública en DO (importa si no está, o reutiliza su fingerprint)-
echo "==> [2/6] Llave pública en DigitalOcean…"
FINGERPRINT="$(doctl compute ssh-key list --format Name,FingerPrint --no-header \
  | awk '$1 == "aire-vm" { print $2; exit }')"

if [[ -z "$FINGERPRINT" ]]; then
  echo "    no existe 'aire-vm' en DO — importando…"
  FINGERPRINT="$(doctl compute ssh-key import aire-vm \
    --public-key-file "${SSH_KEY}.pub" \
    --format FingerPrint --no-header)"
  echo "    importada. fingerprint=$FINGERPRINT"
else
  echo "    ya existe 'aire-vm' en DO — se reutiliza. fingerprint=$FINGERPRINT"
fi

if [[ -z "$FINGERPRINT" ]]; then
  echo "ERROR: no se obtuvo el fingerprint de la llave SSH." >&2
  exit 1
fi

# ---- 3. Droplet (idempotente: si ya existe, no se recrea) ------------------
echo "==> [3/6] Droplet '$NAME'…"
if doctl compute droplet get "$NAME" --format ID --no-header >/dev/null 2>&1; then
  echo "    ya existe — se reutiliza (no se recrea)."
else
  echo "    creando (--wait: espera a que esté listo)…"
  doctl compute droplet create "$NAME" \
    --region "$REGION" \
    --size "$SIZE" \
    --image "$IMAGE" \
    --ssh-keys "$FINGERPRINT" \
    --wait \
    --format ID,Name,Region,Status --no-header
  echo "    creado."
fi

# ---- 4. IP pública ---------------------------------------------------------
echo "==> [4/6] Capturando IP pública…"
IP="$(doctl compute droplet get "$NAME" --format PublicIPv4 --no-header)"
if [[ -z "$IP" ]]; then
  echo "ERROR: no se obtuvo IP pública del droplet." >&2
  exit 1
fi
echo "    IP=$IP"

# ---- 5. Bootstrap remoto vía SSH -------------------------------------------
echo "==> [5/6] Bootstrap remoto en $IP (clona repo, instala units, arranca daemon)…"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"

# Espera a que sshd acepte (el droplet recién creado puede tardar unos segundos).
for i in $(seq 1 10); do
  if $SSH "root@${IP}" true 2>/dev/null; then break; fi
  echo "    esperando sshd… ($i/10)"; sleep 6
done

$SSH "root@${IP}" REPO_URL="$REPO_URL" REMOTE_DIR="$REMOTE_DIR" 'bash -s' <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "    [remote] paquetes base (git, python3)…"
apt-get update -qq
apt-get install -y -qq git python3 >/dev/null

echo "    [remote] repo en $REMOTE_DIR…"
if [[ -d "$REMOTE_DIR/.git" ]]; then
  git -C "$REMOTE_DIR" fetch --all --quiet
  git -C "$REMOTE_DIR" reset --hard origin/main
else
  git clone "$REPO_URL" "$REMOTE_DIR"
fi

echo "    [remote] units systemd…"
cp "$REMOTE_DIR/deploy/aire-listener.service" "$REMOTE_DIR/deploy/aire-device.service" /etc/systemd/system/

echo "    [remote] daemon-reload + enable --now…"
systemctl daemon-reload
systemctl enable --now aire-listener aire-device

echo "    [remote] verificando estado real…"
sleep 1
systemctl is-active aire-listener aire-device
REMOTE

echo "    bootstrap OK — servicios reportados 'active'."

# ---- 6. Salida final -------------------------------------------------------
echo ""
echo "============================================================"
echo "  AIRE DROPLET LISTO"
echo "============================================================"
echo "  IP pública : $IP"
echo "  SSH        : ssh -i ~/.ssh/aire_vm root@$IP"
echo "  Log        : ssh -i ~/.ssh/aire_vm root@$IP 'tail -f $REMOTE_DIR/aire.log'"
echo ""
echo "  Setea los GitHub secrets para que el CI/CD despliegue en cada push:"
echo "    gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b \"$IP\""
echo "    cat ~/.ssh/aire_vm | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server"
echo "============================================================"
