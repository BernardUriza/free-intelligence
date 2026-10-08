#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RG="${RG:-insult-rg}"
LOCATION="${LOCATION:-$(az group show -g "$RG" --query location -o tsv)}"
VM_NAME="${VM_NAME:-arbor-tts-vm}"
ADMIN_USER="${ADMIN_USER:-azureuser}"
VM_SIZE="${VM_SIZE:-Standard_B2s}"
IMAGE="${IMAGE:-Ubuntu2404}"
VNET="${VNET:-arbor-tts-vnet}"
SUBNET="${SUBNET:-default}"
NSG="${NSG:-arbor-tts-nsg}"
PIP="${PIP:-arbor-tts-pip}"
NIC="${NIC:-arbor-tts-nic}"
SSH_SOURCE_CIDR="${SSH_SOURCE_CIDR:?Set SSH_SOURCE_CIDR, for example 203.0.113.10/32}"
HTTPS_SOURCE_CIDR="${HTTPS_SOURCE_CIDR:-*}"

az network nsg create -g "$RG" -n "$NSG" -l "$LOCATION" >/dev/null

az network nsg rule create \
  -g "$RG" \
  --nsg-name "$NSG" \
  -n AllowSshFromOperator \
  --priority 100 \
  --access Allow \
  --direction Inbound \
  --protocol Tcp \
  --source-address-prefixes "$SSH_SOURCE_CIDR" \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 22 \
  >/dev/null

az network nsg rule create \
  -g "$RG" \
  --nsg-name "$NSG" \
  -n AllowHttpForNginx \
  --priority 110 \
  --access Allow \
  --direction Inbound \
  --protocol Tcp \
  --source-address-prefixes "$HTTPS_SOURCE_CIDR" \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 80 \
  >/dev/null

az network nsg rule create \
  -g "$RG" \
  --nsg-name "$NSG" \
  -n AllowHttpsForNginx \
  --priority 120 \
  --access Allow \
  --direction Inbound \
  --protocol Tcp \
  --source-address-prefixes "$HTTPS_SOURCE_CIDR" \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 443 \
  >/dev/null

az vm create \
  -g "$RG" \
  -n "$VM_NAME" \
  --location "$LOCATION" \
  --image "$IMAGE" \
  --size "$VM_SIZE" \
  --admin-username "$ADMIN_USER" \
  --authentication-type ssh \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --public-ip-address "$PIP" \
  --vnet-name "$VNET" \
  --subnet "$SUBNET" \
  --nsg "$NSG" \
  --nsg-rule NONE \
  --assign-identity \
  --custom-data "$SCRIPT_DIR/cloud-init.sh" \
  -o table

echo
echo "VM ready. Public IP:"
az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv
