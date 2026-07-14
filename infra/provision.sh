#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AIRE — provisión reproducible de la VM daemon en Azure.
#
# Levanta UNA VM Ubuntu 24.04 LTS en un resource group AISLADO (aire-rg) que
# corre el listener de AIRE 24/7, accesible por SSH, con logfile greppable.
#
# Corre esto UNA vez desde tu máquina (az ya logueado). Después el CI/CD
# (.github/workflows/deploy.yml) despliega en cada push. Ver infra/README.md.
#
# NUNCA toca ningún otro resource group. Todo vive en $RG.
# ============================================================================

# ---- Variables -------------------------------------------------------------
RG="aire-rg"                      # RG NUEVO y aislado — jamás se toca otro
LOCATION="eastus2"                # barata/estándar, B1s disponible (verificado)
VM="aire-vm"
SIZE="Standard_B1s"               # burstable más barata (~$0.0104/h Linux)
ADMIN="azureuser"
IMAGE="Ubuntu2404"                # alias oficial → Canonical:ubuntu-24_04-lts:server:latest
PORT=9099                         # el listener de AIRE
SSH_KEY="$HOME/.ssh/aire_vm"      # par de llaves dedicado a esta VM
REPO_URL="https://github.com/BernardUriza/aire-server"
REMOTE_DIR="/opt/aire"

echo "==> AIRE provision"
echo "    RG=$RG  LOCATION=$LOCATION  VM=$VM  SIZE=$SIZE  IMAGE=$IMAGE  PORT=$PORT"
echo "    Todo se crea en '$RG'. Ningún otro resource group se toca."

# ---- 0. Sanity: az logueado ------------------------------------------------
echo "==> [0/7] Verificando login de az…"
az account show --query "{name:name, id:id}" -o tsv >/dev/null

# ---- 1. Par de llaves SSH ed25519 (solo si no existe) ----------------------
echo "==> [1/7] Llave SSH ($SSH_KEY)…"
if [[ -f "$SSH_KEY" ]]; then
  echo "    ya existe — se reutiliza (no se regenera)."
else
  mkdir -p "$(dirname "$SSH_KEY")"
  ssh-keygen -t ed25519 -f "$SSH_KEY" -N '' -C "aire-vm"
  echo "    generada."
fi

# ---- 2. Resource group aislado ---------------------------------------------
echo "==> [2/7] Resource group '$RG'…"
if [[ "$(az group exists -n "$RG")" == "true" ]]; then
  echo "    ya existe — se reutiliza."
else
  az group create -n "$RG" -l "$LOCATION" -o none
  echo "    creado en $LOCATION."
fi

# ---- 3. VM (idempotente: si ya existe, no se recrea) -----------------------
echo "==> [3/7] VM '$VM'…"
if az vm show -g "$RG" -n "$VM" -o none 2>/dev/null; then
  echo "    ya existe — se reutiliza (no se recrea)."
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
  echo "    creada."
fi

# ---- 4. Abrir puertos en el NSG (prioridades distintas) --------------------
echo "==> [4/7] Abriendo puertos en el NSG (22, $PORT)…"
az vm open-port -g "$RG" -n "$VM" --port 22    --priority 1001 -o none
az vm open-port -g "$RG" -n "$VM" --port "$PORT" --priority 1002 -o none
echo "    22 (SSH) y $PORT (listener) abiertos."

# ---- 5. IP pública ---------------------------------------------------------
echo "==> [5/7] Capturando IP pública…"
IP="$(az vm show -d -g "$RG" -n "$VM" --query publicIps -o tsv)"
if [[ -z "$IP" ]]; then
  echo "ERROR: no se obtuvo IP pública de la VM." >&2
  exit 1
fi
echo "    IP=$IP"

# ---- 6. Bootstrap remoto vía SSH -------------------------------------------
echo "==> [6/7] Bootstrap remoto en $IP (clona repo, instala units, arranca daemon)…"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=30"

# Espera a que sshd acepte (la VM recién creada puede tardar unos segundos).
for i in $(seq 1 10); do
  if $SSH "${ADMIN}@${IP}" true 2>/dev/null; then break; fi
  echo "    esperando sshd… ($i/10)"; sleep 6
done

$SSH "${ADMIN}@${IP}" REPO_URL="$REPO_URL" REMOTE_DIR="$REMOTE_DIR" ADMIN="$ADMIN" 'bash -s' <<'REMOTE'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "    [remote] paquetes base (git, python3)…"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 >/dev/null

echo "    [remote] repo en $REMOTE_DIR…"
if [[ -d "$REMOTE_DIR/.git" ]]; then
  # ya clonado y propiedad de $ADMIN → git como el propio usuario (sin sudo,
  # evita el "dubious ownership" de git al correr como root sobre dir ajeno).
  git -C "$REMOTE_DIR" fetch --all --quiet
  git -C "$REMOTE_DIR" reset --hard origin/main
else
  # primer clon: /opt es de root → sudo para crear, luego se cede a $ADMIN.
  sudo git clone "$REPO_URL" "$REMOTE_DIR"
  sudo chown -R "$ADMIN" "$REMOTE_DIR"
fi

echo "    [remote] units systemd…"
sudo cp "$REMOTE_DIR/deploy/aire-listener.service" "$REMOTE_DIR/deploy/aire-device.service" /etc/systemd/system/

echo "    [remote] sudoers NOPASSWD para el restart del CI…"
echo "$ADMIN ALL=(root) NOPASSWD: /usr/bin/systemctl restart aire-listener aire-device" \
  | sudo tee /etc/sudoers.d/aire-deploy >/dev/null
sudo chmod 440 /etc/sudoers.d/aire-deploy

echo "    [remote] daemon-reload + enable --now…"
sudo systemctl daemon-reload
sudo systemctl enable --now aire-listener aire-device

echo "    [remote] verificando estado real…"
sleep 1
systemctl is-active aire-listener aire-device
REMOTE

echo "    bootstrap OK — servicios reportados 'active'."

# ---- 7. Salida final -------------------------------------------------------
echo ""
echo "============================================================"
echo "  AIRE VM LISTA"
echo "============================================================"
echo "  IP pública : $IP"
echo "  SSH        : ssh -i $SSH_KEY ${ADMIN}@${IP}"
echo "  Log        : ssh -i $SSH_KEY ${ADMIN}@${IP} 'tail -f $REMOTE_DIR/aire.log'"
echo ""
echo "  Setea los GitHub secrets para que el CI/CD despliegue en cada push:"
echo "    gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b \"$IP\""
echo "    cat $SSH_KEY | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server"
echo "============================================================"
