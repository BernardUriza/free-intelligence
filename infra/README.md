# infra — provisión de la VM daemon de AIRE en Azure

Runbook de la **fase de provisión**: levantar UNA vez la VM Ubuntu 24.04 que
corre el listener de AIRE 24/7. Después, el CI/CD (`.github/workflows/deploy.yml`)
despliega en cada push. El detalle del deploy continuo vive en
[`../deploy/README.md`](../deploy/README.md); esto es sólo cómo nace la VM.

## Aislamiento (regla dura)

Todo se crea en un resource group **nuevo y aislado: `aire-rg`**. El script
**jamás** toca, referencia ni modifica los otros RGs de la cuenta
(`insult-rg`, `activist-os-rg`, `tianguis-cmn-rg`, etc.). Un solo `az group`,
un solo blast radius.

## Parámetros (fijados arriba de `provision.sh`)

| Variable | Valor | Nota |
|---|---|---|
| `RG` | `aire-rg` | RG aislado, se crea si no existe |
| `LOCATION` | `eastus2` | barata/estándar, B1s disponible (verificado) |
| `VM` | `aire-vm` | |
| `SIZE` | `Standard_B1s` | burstable más barata, ~$0.0104/h Linux (~$7.6/mes) |
| `ADMIN` | `azureuser` | |
| `IMAGE` | `Ubuntu2404` | alias oficial → `Canonical:ubuntu-24_04-lts:server:latest` |
| `PORT` | `9099` | el listener; se abre en el NSG junto con 22 (SSH) |
| llave SSH | `~/.ssh/aire_vm` | ed25519, dedicada; se genera si no existe |

## Fase 1 — Provisión (UNA sola vez)

Requisitos: `az` logueado (`az account show`), `gh` logueado (para los secrets).

```bash
cd ~/Documents/aire-server
bash infra/provision.sh
```

El script es **idempotente** donde tiene sentido: reutiliza la llave, el RG y la
VM si ya existen; sólo (re)aplica reglas de puerto y el bootstrap. Hace, en orden:

1. Genera `~/.ssh/aire_vm` (ed25519, sin passphrase) si no existe.
2. `az group create aire-rg` (si no existe).
3. `az vm create` — Ubuntu 24.04, B1s, IP pública Standard, tu llave pública.
4. Abre **22** (prioridad 1001) y **9099** (prioridad 1002) en el NSG.
5. Captura la IP pública y la imprime.
6. Bootstrap por SSH dentro de la VM: instala `git`/`python3`, clona el repo en
   `/opt/aire` (o `git reset --hard origin/main` si ya existe), copia las units
   `deploy/aire-listener.service` y `deploy/aire-device.service` a
   `/etc/systemd/system/`, escribe el sudoers NOPASSWD para el restart del CI,
   `daemon-reload`, `enable --now`, y **verifica con `systemctl is-active`**
   (si un servicio no queda `active`, el script falla — sin fake-green).
7. Imprime IP, comando SSH y los dos comandos de secrets de abajo.

Al terminar verás algo así:

```
  IP pública : 20.51.x.x
  SSH        : ssh -i ~/.ssh/aire_vm azureuser@20.51.x.x
  Log        : ssh -i ~/.ssh/aire_vm azureuser@20.51.x.x 'tail -f /opt/aire/aire.log'
```

## Fase 2 — Setear los secrets de GitHub (para el CI/CD)

El workflow `deploy.yml` entra por SSH y reinicia los servicios en cada push.
Necesita dos secrets. Corre esto **con la IP que imprimió `provision.sh`**:

```bash
# Host: la IP pública de la VM
gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b "<IP>"

# Llave PRIVADA SSH (su pública ya quedó en authorized_keys de la VM)
cat ~/.ssh/aire_vm | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server
```

A partir de aquí, cada `push` a `main` que toque el código redepliega solo.
**Nunca se despliega a mano.**

## Verlo funcionar

```bash
ssh -i ~/.ssh/aire_vm azureuser@<IP>
systemctl is-active aire-listener aire-device   # ambos → active
tail -f /opt/aire/aire.log | grep KEEPALIVE     # los latidos del device, en vivo
grep MESSAGE /opt/aire/aire.log                 # los eventos del device
```

## Notas / riesgos

- **Origin por HTTPS, no SSH.** El clon usa `https://github.com/BernardUriza/aire-server`
  (repo público) → el `git fetch`/`reset --hard` del CI no necesita deploy key en
  la VM. Si el repo se hace privado, cambia el origin a SSH y añade una deploy key.
- **La imagen `Ubuntu2404` es gen2.** B1s soporta gen2 — verificado disponible en
  eastus2. Si algún día cambias a un tamaño gen1-only, usa un URN gen1 explícito.
- **Las units `deploy/*.service` las escribe otro agente.** El bootstrap las
  referencia desde `/opt/aire/deploy/` tras el clon; deben existir en `main` al
  correr el script.
- **Costo.** B1s Linux ~$0.0104/h (~$7.6/mes) + disco managed + IP Standard
  (~$3.6/mes). Apágala con `az vm deallocate -g aire-rg -n aire-vm` para dejar de
  pagar cómputo (el disco y la IP siguen cobrando poco).
- **Borrar todo:** `az group delete -n aire-rg --yes` elimina SÓLO este RG.
```
