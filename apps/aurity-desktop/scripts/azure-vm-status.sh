#!/bin/bash
# Check status of Aurity testing VM
# Usage: ./azure-vm-status.sh

RESOURCE_GROUP="aurity-testing-vms"
VM_NAME="aurity-win11-tester"

echo "=== Aurity Testing VM Status ==="
STATUS=$(az vm get-instance-view -g $RESOURCE_GROUP -n $VM_NAME --query instanceView.statuses[1].displayStatus -o tsv 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "❌ VM no encontrada o Azure CLI no autenticado"
    echo "   Ejecutar: az login"
    exit 1
fi

echo "Estado: $STATUS"

if [ "$STATUS" = "VM running" ]; then
    IP=$(az vm show -g $RESOURCE_GROUP -n $VM_NAME --show-details --query publicIps -o tsv)
    echo "IP pública: $IP"
    echo "Conectar con: Microsoft Remote Desktop → $IP"
    echo "Usuario: auritytest"
    echo ""
    echo "⚠️  VM COBRANDO: \$1.01/hora (~\$30/mes)"
    echo "   Apagar con: az vm deallocate -g $RESOURCE_GROUP -n $VM_NAME"
elif [ "$STATUS" = "VM deallocated" ]; then
    echo "✅ VM APAGADA (solo cobrando disco: ~\$9/mes)"
    echo "   Encender con: az vm start -g $RESOURCE_GROUP -n $VM_NAME"
fi
