# infra — provisión del droplet daemon de AIRE en DigitalOcean

Runbook de la **fase de provisión**: levantar UNA vez el droplet Ubuntu 24.04 que
corre el listener de AIRE 24/7. Después, el CI/CD (`.github/workflows/deploy.yml`)
despliega en cada push. El detalle del deploy continuo vive en
[`../deploy/README.md`](../deploy/README.md); esto es sólo cómo nace el droplet.

## Pivote: Azure → DigitalOcean

AIRE nació apuntando a Azure (una VM B1s). **Azure quedó descartado:** toda la
B-series estaba bloqueada a nivel suscripción (no se podía crear una sola VM
burstable). DigitalOcean es el modelo de EC-GPS — *"el esqueleto primigenio del
daemon"* — más barato y más natural para un daemon-en-caja: un droplet, root, un
`systemd` unit, y ya. El script viejo `provision.sh` (Azure) queda como
referencia histórica; el canónico ahora es `provision-do.sh`.

## Parámetros (fijados arriba de `provision-do.sh`)

| Variable | Valor | Nota |
|---|---|---|
| `NAME` | `aire-droplet` | |
| `REGION` | `nyc3` | común/estándar; override: `REGION=<slug> bash provision-do.sh` |
| `SIZE` | `s-1vcpu-512mb-10gb` | el más barato, ~$4/mo; fallback `s-1vcpu-1gb` ~$6/mo |
| `IMAGE` | `ubuntu-24-04-x64` | slug oficial de DO |
| llave SSH | `~/.ssh/aire_vm` | ed25519, dedicada; se genera si no existe |

El droplet corre como **root** por default (así es DO), así que las units
`deploy/*.service` usan `User=root` y el CI reinicia sin `sudo`.

## Fase 1 — Provisión (UNA sola vez)

Requisitos: `doctl` autenticado (`doctl auth init`), `gh` logueado (para los secrets).

```bash
cd ~/Documents/aire-server
bash infra/provision-do.sh
```

El script es **idempotente** donde tiene sentido: reutiliza la llave, la llave
pública en DO y el droplet si ya existen; sólo (re)aplica el bootstrap. Hace, en
orden:

1. Genera `~/.ssh/aire_vm` (ed25519, sin passphrase) si no existe.
2. Importa la llave pública a DO como `aire-vm` (o reutiliza su fingerprint si ya
   está); captura el fingerprint.
3. `doctl compute droplet create --wait` — Ubuntu 24.04, el size más barato, con
   la llave embebida en root (si no existe ya).
4. Captura la IP pública (`doctl compute droplet get ... --format PublicIPv4`) y
   la imprime.
5. Bootstrap por SSH como `root@<IP>`: instala `git`/`python3`, clona el repo en
   `/opt/aire` (o `git reset --hard origin/main` si ya existe), copia las units
   `deploy/aire-listener.service` y `deploy/aire-device.service` a
   `/etc/systemd/system/`, `daemon-reload`, `enable --now`, y **verifica con
   `systemctl is-active`** (si un servicio no queda `active`, el script falla —
   sin fake-green).
6. Imprime IP, comando SSH y los dos comandos de secrets de abajo.

Al terminar verás algo así:

```
  IP pública : 143.198.x.x
  SSH        : ssh -i ~/.ssh/aire_vm root@143.198.x.x
  Log        : ssh -i ~/.ssh/aire_vm root@143.198.x.x 'tail -f /opt/aire/aire.log'
```

## Fase 2 — Setear los secrets de GitHub (para el CI/CD)

El workflow `deploy.yml` entra por SSH y reinicia los servicios en cada push.
Necesita dos secrets. Corre esto **con la IP que imprimió `provision-do.sh`**:

```bash
# Host: la IP pública del droplet
gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b "<IP>"

# Llave PRIVADA SSH (su pública ya quedó en authorized_keys del droplet)
cat ~/.ssh/aire_vm | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server
```

Mientras `AIRE_VM_HOST` no exista, el workflow **no falla**: imprime
`no host secret yet — skipping deploy` y termina el job en verde. En cuanto lo
setees, cada `push` a `main` que toque el código redepliega solo.
**Nunca se despliega a mano.**

## Verlo funcionar

```bash
ssh -i ~/.ssh/aire_vm root@<IP>
systemctl is-active aire-listener aire-device   # ambos → active
tail -f /opt/aire/aire.log | grep KEEPALIVE     # los latidos del device, en vivo
grep MESSAGE /opt/aire/aire.log                 # los eventos del device
```

## Notas / riesgos

- **Origin por HTTPS, no SSH.** El clon usa `https://github.com/BernardUriza/aire-server`
  (repo público) → el `git fetch`/`reset --hard` del CI no necesita deploy key en
  el droplet. Si el repo se hace privado, cambia el origin a SSH y añade una deploy key.
- **Fallback de size.** Si `s-1vcpu-512mb-10gb` no está disponible en la región,
  exporta `SIZE=s-1vcpu-1gb` (~$6/mo) antes de correr el script.
- **Las units `deploy/*.service` las escribe otro agente.** El bootstrap las
  referencia desde `/opt/aire/deploy/` tras el clon; deben existir en `main` al
  correr el script.
- **Costo.** `s-1vcpu-512mb-10gb` ~$4/mo (incluye disco de 10 GB y la IP pública).
  Sin cargos separados por disco/IP como en Azure.
- **Borrar todo:** `doctl compute droplet delete aire-droplet` elimina SÓLO este
  droplet.
```
