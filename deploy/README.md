# Deploy — AIRE on the daemon box (Ubuntu 24.04 LTS)

CI/CD via GitHub Actions. **Never deploy by hand.** Every `push` to `main` that
touches the code runs `.github/workflows/deploy.yml`, which SSHes into the box,
does `git reset --hard origin/main`, restarts the systemd units and **verifies
they came back `active`** (otherwise the CI fails — no fake-green).

> The box is a DigitalOcean droplet (the original Azure path was discarded — see
> [`../infra/README.md`](../infra/README.md)). The droplet runs as **root**, so
> the workflow connects as `root@` and restarts without `sudo`.

## The flow, in two phases

### 1. Provisioning — ONCE per box

Run once from your machine against DigitalOcean:

```bash
bash infra/provision-do.sh
```

What provisioning leaves ready (the contract this deploy assumes):

- System Python 3.12 at `/usr/bin/python3` (ships with Ubuntu 24.04).
- The repo cloned at `/opt/aire`, with `origin` →
  `https://github.com/BernardUriza/aire-server`.
- The units copied to `/etc/systemd/system/` and enabled:
  ```bash
  cp deploy/aire-listener.service deploy/aire-device.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now aire-listener aire-device
  ```
- Port **9099/tcp** reachable (for external devices) — or closed and
  `127.0.0.1`-only if only the local demo device runs.
- `python3-asyncpg` installed and `/etc/aire/` created (`chmod 700`) — for the pen.

### 1.5 The pen — Postgres credentials, out-of-band

The listener mirrors every log line to an append-only `aire_log` table in Azure
Postgres (`development-pg-n66dz`, database `aire`) when `AIRE_DATABASE_URL` is
set. The DSN is a **secret and never enters the repo** (see the playbook's
secrets-management rule): it lives on the box at `/etc/aire/env` (`chmod 600`),
loaded by the unit via `EnvironmentFile=-/etc/aire/env`. The `-` makes it
optional — without the file the listener runs in file-only mode.

Set it once per box (the DSN is kept in `~/.secrets/aire-postgres.txt` on
Bernard's machine):

```bash
ssh root@<droplet> 'umask 077; printf "AIRE_DATABASE_URL=%s\n" "<dsn>" > /etc/aire/env'
```

The Azure PG firewall must allow the droplet's IP (rule `aire-droplet-do`).

### 2. Continuous deploy — on every push

`.github/workflows/deploy.yml` triggers on:

- `push` to `main` touching the paths `aire/**`, `demo_device.py`, `deploy/**`,
  `.github/workflows/deploy.yml`.
- `workflow_dispatch` (manual button in the Actions tab).

And runs, inside the box:

```bash
cd /opt/aire && git fetch --all && git reset --hard origin/main \
  && systemctl restart aire-listener aire-device \
  && sleep 3 && for u in aire-listener aire-device; do systemctl --quiet is-active "$u" || exit 1; done
```

Each unit is checked **individually** (`systemctl is-active` with multiple
units exits 0 if *at least one* is active — a fake-green), and a dead unit
**breaks the job**: the CI confirms the deploy against the real state, not
against "the push went out".

## GitHub secrets (repo → Settings → Secrets and variables → Actions)

| Secret | What it is |
|---|---|
| `AIRE_VM_HOST` | Public IP or DNS of the box (e.g. `143.198.x.x`). |
| `AIRE_VM_SSH_KEY` | **Private** SSH key (full PEM) whose public half is in the box's `authorized_keys`. |

The key is loaded with `webfactory/ssh-agent@v0.9.0`; the host is accepted with
`StrictHostKeyChecking=accept-new` (TOFU on first contact).

## Watch it work

```bash
ssh -i ~/.ssh/aire_vm root@<IP>
tail -f /opt/aire/aire.log | grep KEEPALIVE     # the device's heartbeats, live
```

Other useful commands on the box:

```bash
systemctl status aire-listener aire-device       # service state
journalctl -u aire-listener -f                    # the listener's stdout
grep MESSAGE /opt/aire/aire.log                   # the random GPS events
```
