# infra — provisioning AIRE's daemon droplet on DigitalOcean

Runbook for the **provisioning phase**: bring up, ONCE, the Ubuntu 24.04 droplet
that runs AIRE's listener 24/7. Everything after birth is the CI/CD's job —
see [`../deploy/README.md`](../deploy/README.md).

> Azure was the first target and is dead (burstable B-series blocked at
> subscription level — kill-list in [`CLAUDE.md`](../CLAUDE.md)). The Azure
> script lived at `infra/provision.sh` until it was removed; git history has it.

## Parameters (set at the top of `provision-do.sh`)

| Variable | Value | Note |
|---|---|---|
| `NAME` | `aire-droplet` | |
| `REGION` | `nyc3` | override: `REGION=<slug> bash provision-do.sh` |
| `SIZE` | `s-1vcpu-512mb-10gb` | ~$4/mo; fallback `SIZE=s-1vcpu-1gb` ~$6/mo if unavailable |
| `IMAGE` | `ubuntu-24-04-x64` | official DO slug |
| SSH key | `~/.ssh/aire_vm` | ed25519, dedicated; generated if absent |
| Deploy key | `~/.secrets/aire-github-deploy-key.txt` | read-only GitHub key — the repo is PRIVATE, the droplet clones over SSH |
| Pen secret | `~/.secrets/aire-postgres.txt` | optional `AIRE_DATABASE_URL`; without it the listener runs file-only |
| Backup OAuth (#31) | `~/.secrets/aire-claude-oauth-backup.txt` | optional `CLAUDE_CODE_OAUTH_TOKEN_BACKUP=` — a DIFFERENT seat/account (same account = same weekly pool); missing file skips the slot |
| Fallback API key (#31) | `~/.secrets/aire-api-key-fallback.txt` | optional `ANTHROPIC_API_KEY_FALLBACK=` — metered last resort, never resets, budget-capped; missing file skips the slot |
| Invitations (#32) | `~/.secrets/aire-access.txt` | `AIRE_ACCESS_SECRET=` (signs the approve link), `AIRE_OWNER_EMAIL=`, `AIRE_GATE_PUBLIC_URL=`, `AIRE_FRONT_URL=` |
| Mail transport (#32) | `~/.secrets/resend-aire.txt` | `RESEND_API_KEY=` — Resend, whose free tier mails the account's own address with no verified domain. Missing → the request-access button answers 503 and says so |

The droplet runs as **root** (that's how DO works), so the `deploy/*.service`
units use `User=root` and the CI restarts without `sudo`.

## Phase 1 — Provision (ONCE)

Requirements: `doctl` authenticated, `gh` logged in, the two secret files above.

```bash
bash infra/provision-do.sh
```

Idempotent: reuses the SSH key, the key in DO and the droplet if they exist. In
order: key pair → key into DO → `droplet create --wait` → capture IP → install
the GitHub deploy key and the pen secret (`/etc/aire/env`, `chmod 600`) → clone
`git@github.com:BernardUriza/aire-server.git` into `/opt/aire` → install the
systemd units → `enable --now` → **verify each unit individually with
`systemctl is-active`** (the multi-unit form exits 0 if *at least one* is
active — that's why the check is per-unit; a dead unit fails the script).

## Phase 2 — GitHub secrets (for the CI/CD)

Run with the IP the script printed:

```bash
gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b "<IP>"
cat ~/.ssh/aire_vm | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server
```

While `AIRE_VM_HOST` is missing the deploy workflow skips green; once set, every
push to `main` that touches the code redeploys on its own. **Never deploy by hand.**

## Watch it work

```bash
ssh -i ~/.ssh/aire_vm root@<IP>
systemctl is-active aire-listener              # → active
tail -f /opt/aire/aire.log | grep KEEPALIVE     # the heartbeats, live
```

## Budget — $20/month HARD

The whole DO budget is **$20 USD/month**; the budgeted inventory is exactly one
`s-1vcpu-512mb-10gb` droplet (~$4/mo, backups off) and nothing else. Enforced by
`.github/workflows/costwatch.yml` (daily cron; fails red → GitHub email if
month-to-date usage crosses $10/$20, if the inventory drifts, or if backups get
enabled) plus a $10 billing alert in the DO panel. Full law:
[`.claude/rules/do-budget.md`](../.claude/rules/do-budget.md). No paid resource
gets created without Bernard's explicit go.
`doctl compute droplet delete aire-droplet` removes ONLY this droplet.
