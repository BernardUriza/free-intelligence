#!/bin/bash
# Toggle Aurity testing VM (start if stopped, stop if running)
# Usage: ./azure-vm-toggle.sh

RESOURCE_GROUP="aurity-testing-vms"
VM_NAME="aurity-win11-tester"

STATUS=$(az vm get-instance-view -g $RESOURCE_GROUP -n $VM_NAME --query instanceView.statuses[1].displayStatus -o tsv)

if [ "$STATUS" = "VM running" ]; then
    echo "🛑 Apagando VM..."
    az vm deallocate -g $RESOURCE_GROUP -n $VM_NAME
    echo "✅ VM deallocated (costo reducido a disco: ~\$9/mes)"
elif [ "$STATUS" = "VM deallocated" ]; then
    echo "▶️  Encendiendo VM..."
    az vm start -g $RESOURCE_GROUP -n $VM_NAME
    IP=$(az vm show -g $RESOURCE_GROUP -n $VM_NAME --show-details --query publicIps -o tsv)
    echo "✅ VM running"
    echo "IP: $IP"
    echo "Conectar con Microsoft Remote Desktop"
else
    echo "⚠️  Estado desconocido: $STATUS"
fi
