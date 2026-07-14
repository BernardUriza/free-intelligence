# Deploy — AIRE en una VM de Azure (Ubuntu 24.04 LTS)

CI/CD por GitHub Actions. **Nunca se despliega a mano.** Cada `push` a `main` que
toca el código corre `.github/workflows/deploy.yml`, que entra por SSH a la VM,
hace `git reset --hard origin/main`, reinicia los servicios systemd y **verifica
que quedaron `active`** (si no, el CI falla — sin fake-green).

## El flujo, en dos fases

### 1. Provisión — UNA sola vez, por VM

Se corre una vez en una VM Ubuntu 24.04 recién creada (usuario `azureuser`):

```bash
sudo bash infra/provision.sh
```

Lo que la provisión deja listo (contrato que este deploy asume):

- Python 3.12 del sistema en `/usr/bin/python3` (viene con Ubuntu 24.04).
- El repo clonado en `/opt/aire`, propiedad de `azureuser`, con `origin` →
  `git@github.com:BernardUriza/aire-server.git`.
- Las units copiadas a `/etc/systemd/system/` y habilitadas:
  ```bash
  sudo cp deploy/aire-listener.service deploy/aire-device.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now aire-listener aire-device
  ```
- El puerto **9099/tcp** abierto en el NSG de Azure (para devices externos) — o
  cerrado y solo `127.0.0.1` si únicamente corre el device demo local.
- `azureuser` con `sudo` NOPASSWD para `systemctl restart aire-listener aire-device`
  (el workflow hace `sudo systemctl restart` sin TTY).

> `infra/provision.sh` es el script idempotente de esta fase. Si aún no existe,
> los pasos de arriba son su contenido mínimo.

### 2. Deploy continuo — en cada push

`.github/workflows/deploy.yml` se dispara con:

- `push` a `main` en las rutas `aire/**`, `demo_device.py`, `deploy/**`,
  `.github/workflows/deploy.yml`.
- `workflow_dispatch` (botón manual en la pestaña Actions).

Y ejecuta, dentro de la VM:

```bash
cd /opt/aire && git fetch --all && git reset --hard origin/main \
  && sudo systemctl restart aire-listener aire-device \
  && sleep 1 && systemctl is-active aire-listener aire-device
```

`systemctl is-active` sale con código ≠ 0 si algún servicio no está `active`, y
eso **rompe el job**: el CI confirma el deploy contra el estado real, no contra
"el push salió".

## Secrets de GitHub (repo → Settings → Secrets and variables → Actions)

| Secret | Qué es |
|---|---|
| `AIRE_VM_HOST` | IP pública o DNS de la VM (ej. `20.51.x.x` o `aire.eastus.cloudapp.azure.com`). |
| `AIRE_VM_SSH_KEY` | Llave **privada** SSH (PEM completo) cuya pública está en `~azureuser/.ssh/authorized_keys` de la VM. |

La llave se carga con `webfactory/ssh-agent@v0.9.0`; el host se acepta con
`StrictHostKeyChecking=accept-new` (TOFU en el primer contacto).

## Verlo funcionar

```bash
ssh azureuser@<IP>
tail -f /opt/aire/aire.log | grep KEEPALIVE     # los latidos del device, en vivo
```

Otros comandos útiles en la VM:

```bash
systemctl status aire-listener aire-device       # estado de los servicios
journalctl -u aire-listener -f                    # stdout del listener
grep MESSAGE /opt/aire/aire.log                   # los eventos GPS random
```
