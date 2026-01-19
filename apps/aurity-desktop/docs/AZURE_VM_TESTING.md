# Azure VM de Windows para Testing de Aurity Desktop

## Resumen Ejecutivo

VM de Windows 11 en Azure para testing del installer de Aurity Desktop cada 3 meses.

**Gestión de costos:**
- VM deallocated (apagada) = $0/mes compute + ~$9/mes disco
- VM running solo durante testing (~1-2 días cada 3 meses) = ~$4-10 adicionales
- **Costo trimestral estimado**: ~$31
- **Costo anual estimado**: ~$124

**Especificaciones:**
- **Size**: Standard_B2s (2 vCPUs, 4GB RAM) - $30/mes running, $0 deallocated
- **OS**: Windows 11 Pro (versión más reciente)
- **Disco**: 127GB SSD estándar
- **Región**: East US (más cercana y económica desde México)

## Quick Start

```bash
# 1. Verificar estado actual
./apps/aurity-desktop/scripts/azure-vm-status.sh

# 2. Encender/Apagar (toggle)
./apps/aurity-desktop/scripts/azure-vm-toggle.sh

# 3. Obtener IP para RDP
az vm show \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester \
  --show-details \
  --query publicIps \
  --output tsv
```

## Setup Inicial (Una sola vez)

### 1. Configurar variables

```bash
# Configuración (personalizar si es necesario)
RESOURCE_GROUP="aurity-testing-vms"
VM_NAME="aurity-win11-tester"
LOCATION="eastus"
VM_SIZE="Standard_B2s"
IMAGE="MicrosoftWindowsDesktop:windows-11:win11-23h2-pro:latest"
ADMIN_USER="auritytest"
ADMIN_PASS="AurityTest2025!"  # Cambiar por algo más seguro
```

### 2. Crear resource group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

**Output esperado:**
```json
{
  "id": "/subscriptions/.../resourceGroups/aurity-testing-vms",
  "location": "eastus",
  "name": "aurity-testing-vms",
  "properties": {
    "provisioningState": "Succeeded"
  }
}
```

### 3. Crear VM de Windows 11

```bash
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image $IMAGE \
  --size $VM_SIZE \
  --admin-username $ADMIN_USER \
  --admin-password "$ADMIN_PASS" \
  --public-ip-sku Standard \
  --nsg-rule RDP \
  --os-disk-size-gb 127 \
  --storage-sku Standard_LRS
```

**Tiempo estimado**: ~3-5 minutos

**Output importante**: Anota el `publicIpAddress` del JSON de salida.

### 4. Configurar RDP desde Mac

```bash
# Instalar Microsoft Remote Desktop (si no lo tienes)
brew install --cask microsoft-remote-desktop
```

**Conectar:**
1. Abrir Microsoft Remote Desktop
2. Click en "+" → "Add PC"
3. PC name: `<publicIpAddress>` (del paso 3)
4. User account: `auritytest` / `AurityTest2025!`
5. Click "Add" → doble click para conectar

## Comandos de Gestión Diaria

### Encender VM (antes de testing)

```bash
# Usando script
./apps/aurity-desktop/scripts/azure-vm-toggle.sh

# O manualmente
az vm start \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester

# Obtener IP pública
az vm show \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester \
  --show-details \
  --query publicIps \
  --output tsv
```

**Tiempo**: ~1-2 minutos
**Costo**: Empieza a cobrar por minuto (~$0.04/hora)

### Apagar VM (después de testing)

```bash
# Usando script
./apps/aurity-desktop/scripts/azure-vm-toggle.sh

# O manualmente
az vm deallocate \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester
```

**Tiempo**: ~30-60 segundos
**Costo**: Deja de cobrar compute, solo cobra disco (~$9/mes)

### Verificar estado actual

```bash
# Usando script
./apps/aurity-desktop/scripts/azure-vm-status.sh

# O manualmente
az vm get-instance-view \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester \
  --query instanceView.statuses[1].displayStatus \
  --output tsv
```

**Posibles estados:**
- `VM running` → cobrando compute + disco
- `VM deallocated` → solo cobrando disco

## Workflow de Testing (cada 3 meses)

### Día 1: Setup

```bash
# 1. Encender VM
./apps/aurity-desktop/scripts/azure-vm-toggle.sh

# 2. Obtener IP
IP=$(az vm show \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester \
  --show-details \
  --query publicIps -o tsv)
echo "Conectar a RDP: $IP"

# 3. Conectar con Microsoft Remote Desktop
# Usuario: auritytest / AurityTest2025!
```

### Día 2-3: Testing

En la VM Windows:
1. Descargar installer de GitHub Releases
2. Ejecutar `Aurity_1.0.0_x64-setup.exe`
3. Verificar instalación de Python 3.14
4. Verificar FI Monitor
5. Ejecutar `test-python-install.ps1` (del repo)
6. Documentar resultados en GitHub Issue

### Día 3: Cleanup

```bash
# Apagar VM (deja de cobrar compute)
./apps/aurity-desktop/scripts/azure-vm-toggle.sh

# Confirmar estado
./apps/aurity-desktop/scripts/azure-vm-status.sh
# Debe decir: "VM deallocated"
```

## Costos Estimados (East US, Standard_B2s)

| Componente | Running | Deallocated |
|------------|---------|-------------|
| Compute (2 vCPU, 4GB RAM) | $30.37/mes | $0.00 |
| OS Disk (127GB SSD) | $6.40/mes | $6.40/mes |
| Public IP | $3.00/mes | $3.00/mes |
| **Total por mes** | **$39.77** | **$9.40** |

**Uso real (3 días cada 3 meses):**
- 3 días running: ~$4.00
- 87 días deallocated: $27.00
- **Costo trimestral**: ~$31.00
- **Costo anual**: ~$124.00

## Optimizaciones de Costo

### Opción 1: Deallocate IP cuando no uses (ahorra $3/mes)

```bash
# Antes de deallocate VM
az network public-ip delete \
  --resource-group aurity-testing-vms \
  --name "aurity-win11-testerPublicIP"

# Cuando enciendas VM, se crea nueva IP automáticamente
```

**Ahorro**: $3/mes → $108/año
**Costo anual**: $16 (solo storage durante deallocate)

### Opción 2: Snapshot + Delete (costo mínimo)

```bash
# Crear snapshot del disco (antes de borrar VM)
az snapshot create \
  --resource-group aurity-testing-vms \
  --name "aurity-win11-tester-snapshot" \
  --source $(az vm show \
    -g aurity-testing-vms \
    -n aurity-win11-tester \
    --query "storageProfile.osDisk.managedDisk.id" -o tsv)

# Borrar VM completa
az vm delete -g aurity-testing-vms -n aurity-win11-tester --yes

# Cuando necesites la VM, recrear desde snapshot
az disk create \
  --resource-group aurity-testing-vms \
  --name "aurity-win11-tester-os-disk" \
  --source "aurity-win11-tester-snapshot"

az vm create \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester \
  --attach-os-disk "aurity-win11-tester-os-disk" \
  --os-type Windows
```

**Costo snapshot**: $2/mes (vs $9.40/mes VM deallocated)
**Ahorro**: $7.40/mes → $266/año
**Trade-off**: Tardas ~5 min en recrear VM desde snapshot vs 1 min en start

## Troubleshooting

### Error: "No subscription found"

```bash
az login
az account list --output table
az account set --subscription "d61ba6bc-eda9-4327-a264-5cfddef30bc8"
```

### Error: RDP no conecta

```bash
# Verificar NSG (Network Security Group) tiene regla RDP
az network nsg rule list \
  --resource-group aurity-testing-vms \
  --nsg-name "aurity-win11-testerNSG" \
  --query "[?destinationPortRange=='3389'].{Name:name,Access:access,Priority:priority}" \
  --output table

# Si no existe, crear regla
az network nsg rule create \
  --resource-group aurity-testing-vms \
  --nsg-name "aurity-win11-testerNSG" \
  --name AllowRDP \
  --priority 300 \
  --source-address-prefixes '*' \
  --destination-port-ranges 3389 \
  --access Allow \
  --protocol Tcp
```

### IP cambia después de deallocate

Esto es normal con IP dinámica. Soluciones:

**Opción A**: Usar IP estática ($3/mes extra)
```bash
az network public-ip update \
  --resource-group aurity-testing-vms \
  --name "aurity-win11-testerPublicIP" \
  --allocation-method Static
```

**Opción B**: Obtener IP cada vez que enciendes
```bash
az vm start -g aurity-testing-vms -n aurity-win11-tester && \
az vm show -g aurity-testing-vms -n aurity-win11-tester --show-details --query publicIps -o tsv
```

### Error: "VM already exists"

```bash
# Ver VMs existentes
az vm list -g aurity-testing-vms --output table

# Borrar VM existente
az vm delete -g aurity-testing-vms -n aurity-win11-tester --yes

# Recrear con comandos de Setup
```

## Comandos de Limpieza (si ya no necesitas la VM)

### Borrar solo la VM (mantiene resource group)

```bash
az vm delete \
  --resource-group aurity-testing-vms \
  --name aurity-win11-tester \
  --yes
```

### Borrar todo (VM + disco + network + resource group)

```bash
az group delete \
  --name aurity-testing-vms \
  --yes \
  --no-wait
```

## Checklist de Setup (Primera Vez)

- [ ] Ejecutar `az login` y verificar subscription activa
- [ ] Crear resource group con `az group create`
- [ ] Crear VM con `az vm create` (~5 minutos)
- [ ] Anotar `publicIpAddress` del output
- [ ] Instalar Microsoft Remote Desktop en Mac
- [ ] Conectar a RDP con IP + credenciales (auritytest/AurityTest2025!)
- [ ] Verificar Windows 11 funciona correctamente
- [ ] Apagar VM con `az vm deallocate`
- [ ] Verificar estado con script (debe decir "deallocated")
- [ ] Documentar credenciales en 1Password o similar

## Checklist de Testing (Cada 3 Meses)

- [ ] Encender VM con `./azure-vm-status.sh` o script toggle
- [ ] Obtener IP con script o `az vm show`
- [ ] Conectar RDP desde Microsoft Remote Desktop
- [ ] Descargar installer de GitHub Releases
- [ ] Ejecutar installer `Aurity_1.0.0_x64-setup.exe`
- [ ] Verificar Python 3.14 con `python --version`
- [ ] Verificar FI Monitor gateway (puerto 11400)
- [ ] Ejecutar `test-python-install.ps1` del repo
- [ ] Documentar resultados en GitHub Issue
- [ ] Apagar VM con script toggle
- [ ] Verificar estado "deallocated" para evitar cobros

## Ventajas de este Approach

✅ **Costo optimizado**: $31/trimestre vs $160/mes de VM siempre encendida
✅ **Windows nativo**: Testing real del installer (no Wine/CrossOver)
✅ **Reproducible**: Scripts documentados, fácil recrear
✅ **Low maintenance**: No necesitas mantener hardware Windows en casa
✅ **Escalable**: Puedes crear múltiples VMs para diferentes versiones de Windows
✅ **Azure credits**: Si tienes Visual Studio subscription, puedes usar créditos gratis ($50-150/mes)

## Scripts Disponibles

| Script | Ubicación | Propósito |
|--------|-----------|-----------|
| `azure-vm-status.sh` | `apps/aurity-desktop/scripts/` | Verificar estado de VM e IP |
| `azure-vm-toggle.sh` | `apps/aurity-desktop/scripts/` | Encender/Apagar VM (toggle) |
| `test-python-install.ps1` | `apps/aurity-desktop/scripts/` | Verificar instalación de Python en Windows |

## Referencias

- **Azure CLI Docs**: https://learn.microsoft.com/en-us/cli/azure/vm
- **Azure VM Pricing**: https://azure.microsoft.com/en-us/pricing/details/virtual-machines/windows/
- **Microsoft Remote Desktop**: https://apps.apple.com/app/microsoft-remote-desktop/id1295203466
