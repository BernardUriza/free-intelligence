# Deploy — AIRE on the daemon box (Ubuntu 24.04 LTS)

CI/CD via GitHub Actions. **Never deploy by hand.** Every `push` to `main` that
touches the code runs `.github/workflows/deploy-server.yml`, which SSHes into the box,
resets to `origin/main`, reinstalls the units, restarts them and **verifies each
one individually came back `active`** (otherwise the CI fails — no fake-green).

The box is born once via [`../infra/`](../infra/README.md) (DigitalOcean droplet,
runs as **root**, so the workflow connects as `root@` without `sudo`). This file
is only the deploy contract.

## What the workflow does on every push

Gated by a `test` job — the thirty-line law plus the full pytest suite against
a real Postgres; red there and the droplet never sees the push.

Triggers: `push` to `main` on `server/**`, the
workflow file itself — plus `workflow_dispatch`. Inside the box:

```bash
cd /opt/aire && git fetch --all && git reset --hard origin/main \
  && install -m 644 deploy/*.service /etc/systemd/system/ && systemctl daemon-reload \
  && systemctl restart aire-listener \
  && sleep 3 && for u in aire-listener; do systemctl --quiet is-active "$u" || exit 1; done
```

The units are reinstalled on every deploy so `/etc/systemd/system` never drifts
from `deploy/`. Each unit is checked **individually** (`systemctl is-active`
with multiple units exits 0 if *at least one* is active — a fake-green), and a
dead unit **breaks the job**.

## The pen — Postgres credentials, out-of-band

The listener mirrors every log line to an append-only `aire_log` table in Azure
Postgres (`development-pg-n66dz`, database `aire`) when `AIRE_DATABASE_URL` is
set. The DSN is a **secret and never enters the repo** (see the playbook's
secrets-management rule): it lives on the box at `/etc/aire/env` (`chmod 600`),
loaded by the unit via `EnvironmentFile=-/etc/aire/env`. The `-` makes it
optional — without the file the listener runs in file-only mode.

Set it once per box (the DSN is kept in `~/.secrets/aire-postgres.txt` on
Bernard's machine; the provision script installs it automatically):

```bash
ssh root@<droplet> 'umask 077; printf "AIRE_DATABASE_URL=%s\n" "<dsn>" > /etc/aire/env'
```

The Azure PG firewall must allow the droplet's IP (rule `aire-droplet-do`).

## GitHub secrets (repo → Settings → Secrets and variables → Actions)

| Secret | What it is |
|---|---|
| `AIRE_VM_HOST` | Public IP or DNS of the box. |
| `AIRE_VM_SSH_KEY` | **Private** SSH key (full PEM) whose public half is in the box's `authorized_keys`. |
| `DO_API_TOKEN` | Read by `costwatch.yml` (the $20/mo budget watchdog), not by the deploy. |

The key is loaded with `webfactory/ssh-agent@v0.9.0`; the host is accepted with
`StrictHostKeyChecking=accept-new` (TOFU on first contact).

## Watch it work

```bash
ssh -i ~/.ssh/aire_vm root@<IP>
tail -f /opt/aire/aire.log | grep KEEPALIVE      # the device's heartbeats, live
journalctl -u aire-listener -f                    # the listener's stdout
systemctl status aire-listener                   # service state
```
