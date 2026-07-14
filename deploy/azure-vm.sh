#!/usr/bin/env bash
# Crea la VM de AIRE en Azure y arranca el daemon + el device dentro de ella.
# Infra-as-code (live-infra-changes-as-code): esto ES el deploy, no un click.
# Solo expone SSH (22); el daemon escucha en 127.0.0.1 y el device le pega local.
#
# Correr:  bash deploy/azure-vm.sh
# Matar todo:  az group delete -n aire-rg --yes --no-wait
set -euo pipefail

RG=${RG:-aire-rg}
LOC=${LOC:-eastus}
VM=${VM:-aire-listener}
SIZE=${SIZE:-Standard_B1s}
IMAGE=${IMAGE:-Ubuntu2204}
ADMIN=${ADMIN:-azureuser}

az account show -o none  # falla temprano y claro si no hay login

az group create -n "$RG" -l "$LOC" -o none

az vm create \
  -g "$RG" -n "$VM" \
  --image "$IMAGE" --size "$SIZE" \
  --admin-username "$ADMIN" \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --nsg-rule SSH \
  -o none

IP=$(az vm show -g "$RG" -n "$VM" -d --query publicIps -o tsv)
echo "VM lista → IP: $IP"

# setup DENTRO de la VM: instala git+python3, bootstrappea desde el repo público
az vm run-command invoke \
  -g "$RG" -n "$VM" \
  --command-id RunShellScript \
  --scripts "export DEBIAN_FRONTEND=noninteractive; apt-get update -y && apt-get install -y git python3 && curl -fsSL https://raw.githubusercontent.com/BernardUriza/aire-server/main/deploy/setup.sh | bash" \
  --query 'value[0].message' -o tsv

echo
echo "==== LISTO ===="
echo "SSH:   ssh $ADMIN@$IP"
echo "Logs:  ssh $ADMIN@$IP 'tail -f /opt/aire/aire.log | grep KEEPALIVE'"
echo "Matar: az group delete -n $RG --yes --no-wait"
