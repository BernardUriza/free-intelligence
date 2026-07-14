# infra — provisioning AIRE's daemon droplet on DigitalOcean

Runbook for the **provisioning phase**: bring up, ONCE, the Ubuntu 24.04 droplet
that runs AIRE's listener 24/7. After that, the CI/CD
(`.github/workflows/deploy.yml`) deploys on every push. The continuous-deploy
detail lives in [`../deploy/README.md`](../deploy/README.md); this is only how
the droplet is born.

## Pivot: Azure → DigitalOcean

AIRE started out aimed at Azure (a B1s VM). **Azure was discarded:** the entire
B-series was blocked at subscription level (not a single burstable VM could be
created). DigitalOcean is the EC-GPS model — *"the primordial skeleton of the
daemon"* — cheaper and more natural for a daemon-in-a-box: a droplet, root, a
`systemd` unit, done. The old `provision.sh` script (Azure) remains as
historical reference; the canonical one is now `provision-do.sh`.

## Parameters (set at the top of `provision-do.sh`)

| Variable | Value | Note |
|---|---|---|
| `NAME` | `aire-droplet` | |
| `REGION` | `nyc3` | common/standard; override: `REGION=<slug> bash provision-do.sh` |
| `SIZE` | `s-1vcpu-512mb-10gb` | the cheapest, ~$4/mo; fallback `s-1vcpu-1gb` ~$6/mo |
| `IMAGE` | `ubuntu-24-04-x64` | official DO slug |
| SSH key | `~/.ssh/aire_vm` | ed25519, dedicated; generated if it doesn't exist |

The droplet runs as **root** by default (that's how DO works), so the
`deploy/*.service` units use `User=root` and the CI restarts without `sudo`.

## Phase 1 — Provisioning (ONCE)

Requirements: `doctl` authenticated (`doctl auth init`), `gh` logged in (for the
secrets).

```bash
cd ~/Documents/aire-server
bash infra/provision-do.sh
```

The script is **idempotent** where it makes sense: it reuses the key, the public
key in DO and the droplet if they already exist; it only (re)applies the
bootstrap. It does, in order:

1. Generates `~/.ssh/aire_vm` (ed25519, no passphrase) if it doesn't exist.
2. Imports the public key into DO as `aire-vm` (or reuses its fingerprint if
   it's already there); captures the fingerprint.
3. `doctl compute droplet create --wait` — Ubuntu 24.04, the cheapest size, with
   the key embedded for root (unless the droplet already exists).
4. Captures the public IP (`doctl compute droplet get ... --format PublicIPv4`)
   and prints it.
5. Bootstraps over SSH as `root@<IP>`: installs `git`/`python3`, clones the repo
   into `/opt/aire` (or `git reset --hard origin/main` if it already exists),
   copies the `deploy/aire-listener.service` and `deploy/aire-device.service`
   units to `/etc/systemd/system/`, `daemon-reload`, `enable --now`, and
   **verifies with `systemctl is-active`** (if a service doesn't come back
   `active`, the script fails — no fake-green).
6. Prints the IP, the SSH command and the two secrets commands below.

When it finishes you'll see something like:

```
  Public IP : 143.198.x.x
  SSH       : ssh -i ~/.ssh/aire_vm root@143.198.x.x
  Log       : ssh -i ~/.ssh/aire_vm root@143.198.x.x 'tail -f /opt/aire/aire.log'
```

## Phase 2 — Set the GitHub secrets (for the CI/CD)

The `deploy.yml` workflow SSHes in and restarts the services on every push. It
needs two secrets. Run this **with the IP that `provision-do.sh` printed**:

```bash
# Host: the droplet's public IP
gh secret set AIRE_VM_HOST -R BernardUriza/aire-server -b "<IP>"

# PRIVATE SSH key (its public half already landed in the droplet's authorized_keys)
cat ~/.ssh/aire_vm | gh secret set AIRE_VM_SSH_KEY -R BernardUriza/aire-server
```

As long as `AIRE_VM_HOST` doesn't exist, the workflow **does not fail**: it
prints `no host secret yet — skipping deploy` and the job ends green. As soon as
you set it, every `push` to `main` that touches the code redeploys on its own.
**Never deploy by hand.**

## Watch it work

```bash
ssh -i ~/.ssh/aire_vm root@<IP>
systemctl is-active aire-listener aire-device   # both → active
tail -f /opt/aire/aire.log | grep KEEPALIVE     # the device's heartbeats, live
grep MESSAGE /opt/aire/aire.log                 # the device's events
```

## Notes / risks

- **Origin over HTTPS, not SSH.** The clone uses
  `https://github.com/BernardUriza/aire-server` (public repo) → the CI's
  `git fetch`/`reset --hard` needs no deploy key on the droplet. If the repo
  goes private, switch the origin to SSH and add a deploy key.
- **Size fallback.** If `s-1vcpu-512mb-10gb` isn't available in the region,
  export `SIZE=s-1vcpu-1gb` (~$6/mo) before running the script.
- **The `deploy/*.service` units are written by another agent.** The bootstrap
  references them from `/opt/aire/deploy/` after the clone; they must exist on
  `main` when the script runs.
- **Cost.** `s-1vcpu-512mb-10gb` ~$4/mo (includes the 10 GB disk and the public
  IP). No separate disk/IP charges like on Azure.
- **Delete everything:** `doctl compute droplet delete aire-droplet` removes
  ONLY this droplet.
