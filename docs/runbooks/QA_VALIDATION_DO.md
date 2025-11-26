# FI Cloud Readiness — Next Steps Runbook (DO + NFSv4 + SMB3)

**Branch:** `claude/evaluate-fi-cloud-readiness-01K784uKFfnsi8FP6okb7ALD`
**Commit:** `6f5711e`
**Status baseline:** Hardening items 1–10 ✅

> Goal: Provision, test, and validate the hardened setup end‑to‑end, then enforce parity between UFW and DigitalOcean Cloud Firewall. Capture evidence for QA and roll back safely if needed.

---

## 0) Prerequisites

- `doctl` authenticated (`doctl auth init`), project + region selected.
- `infra/cloud-init.yaml` updated in this branch.
- SSH key ID available via `doctl compute ssh-key list`.
- Server OS: Ubuntu 22.04 LTS (example), NFSv4 server packages installed.
- Client host with NFSv4 and (optionally) SMB3 tools (`cifs-utils`, `samba-client`).

---

## 1) Provision Droplet with cloud‑init

```bash
# Variables
export DO_REGION="nyc3"
export DROPLET_NAME="fi-hardened-nfs"
export SIZE="s-2vcpu-4gb"
export SSH_KEY_ID="<your-ssh-key-id>"

# Create droplet
doctl compute droplet create "$DROPLET_NAME" \
  --region "$DO_REGION" \
  --image "ubuntu-22-04-x64" \
  --size "$SIZE" \
  --ssh-keys "$SSH_KEY_ID" \
  --user-data-file "infra/cloud-init.yaml" \
  --tag-names "fi,hardening,nfs" \
  --wait

# Get IP
doctl compute droplet list | grep "$DROPLET_NAME"
```

### 1.a Server-side Validation (SSH into droplet)

```bash
# NFSv4 pseudo-root present and bind mounts active
grep -E "^[^#].*/export" /etc/exports
mount | grep "on /export"
showmount -e localhost || true  # may be empty for v4, acceptable

# idmapd domain
grep "^Domain" /etc/idmapd.conf
sudo systemctl restart nfs-idmapd || sudo systemctl restart rpcidmapd

# UFW status
sudo ufw status verbose

# fstrim
systemctl status fstrim.timer
journalctl -u fstrim.timer --since "24 hours ago" --no-pager

# SMB server hardening (if Samba is present)
test -f /etc/samba/smb.conf && grep -E "server min protocol|client min protocol|smb encrypt" /etc/samba/smb.conf || true
```

---

## 2) Client Mount & Throughput Test (NFSv4)

> Use a Linux client. Replace `$SERVER_IP` with droplet IP.

```bash
export SERVER_IP="<droplet-ip>"
sudo mkdir -p /mnt/fi-export

# Temporary test mount
sudo mount -t nfs4 -o nconnect=4,rsize=1048576,wsize=1048576,noatime,hard,timeo=600,retrans=2 \
  ${SERVER_IP}:/ /mnt/fi-export

# Verify ownership mapping (root_squash to anonuid/gid 1000:1000)
id $(id -nu 1000)
ls -la /mnt/fi-export

# Root should NOT be privileged on the export (negative test)
sudo touch /mnt/fi-export/root-should-be-squashed 2>&1 | tee /tmp/nfs_root_squash.out || true

# Throughput test (write + fsync)
dd if=/dev/zero of=/mnt/fi-export/dd_4G.test bs=1M count=4096 oflag=direct status=progress
sync
dd if=/mnt/fi-export/dd_4G.test of=/dev/null bs=1M status=progress

# Cleanup test file
rm -f /mnt/fi-export/dd_4G.test

# If stable, add to fstab for permanence
echo "${SERVER_IP}:/ /mnt/fi-export nfs4 x-systemd.automount,_netdev,nofail,nconnect=4,rsize=1048576,wsize=1048576 0 0" | sudo tee -a /etc/fstab
sudo systemctl daemon-reload
sudo systemctl restart remote-fs.target
```

### Checks

| Check | Expected |
|-------|----------|
| `mount \| grep fi-export` | shows `nfs4` + `nconnect=4` |
| `ls -la` | files owned by UID/GID 1000 (anon mapping) |
| Write throughput | ≥50 MB/s for s-2vcpu-4gb droplet |

---

## 3) DigitalOcean Cloud Firewall (Parity with UFW)

> Create a Cloud Firewall that mirrors allowed services only.

```bash
export FW_NAME="fi-hardened-nfs-fw"
export DROPLET_ID=$(doctl compute droplet list --no-header --format ID,Name | awk '/fi-hardened-nfs/{print $1}')

# Example: allow SSH from trusted CIDRs, allow NFSv4 (2049/tcp) from selected subnets/VPC only
doctl compute firewall create \
  --name "$FW_NAME" \
  --inbound-rules "protocol:tcp,ports:22,address:203.0.113.0/24" \
  --inbound-rules "protocol:tcp,ports:2049,tag:fi" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0" \
  --outbound-rules "protocol:udp,ports:all,address:0.0.0.0/0" \
  --droplet-ids "$DROPLET_ID"

# Attach additional constraints as needed (VPC, private ranges).
doctl compute firewall list
doctl compute firewall get "$FW_NAME"
```

### Parity Checklist

- [ ] UFW and DO FW both allow **only**: SSH (trusted sources), NFSv4 `tcp/2049` (expected sources), and necessary egress.
- [ ] Confirm inbound default-deny on UFW and DO FW.

---

## 4) SMB3 Encryption Validation (if using Samba)

> Only SMB3 with `smb encrypt = required` should be negotiated.

```bash
# Client-side test (Linux)
sudo mkdir -p /mnt/fi-smb
sudo mount -t cifs //${SERVER_IP}/<share> /mnt/fi-smb -o username=<user>,vers=3.1.1,seal

# Verify negotiated dialect
dmesg | tail -n 50 | grep -i cifs || true
```

On the server:

```bash
sudo test -x /usr/bin/smbstatus && smbstatus -b || true
grep -E "smb encrypt\s*=\s*required" /etc/samba/smb.conf
```

---

## 5) Snapshots Nightly — Verification

```bash
# If snapshots are filesystem-level (e.g., btrfs)
sudo systemctl status snapshots.timer || true
sudo ls -1 /.snapshots | tail -n 10 || true

# If DigitalOcean snapshots
doctl compute droplet-action snapshot "$DROPLET_ID" --snapshot-name "nightly-$(date +%F)"
doctl compute snapshot list --resource droplet | head
```

Ensure **retention of 7 days** via your timer/cron or housekeeping job.

---

## 6) Evidence Collection (for QA)

```bash
# NFS config & state
uname -a > evidence.txt
date -Is >> evidence.txt
echo -e "\n## exports\n" >> evidence.txt
grep -E "^[^#]" /etc/exports >> evidence.txt || true
echo -e "\n## mounts\n" >> evidence.txt
mount | grep -E "nfs4|cifs" >> evidence.txt || true
echo -e "\n## ufw\n" >> evidence.txt
sudo ufw status verbose >> evidence.txt || true
echo -e "\n## doctl firewall\n" >> evidence.txt
doctl compute firewall list >> evidence.txt || true

# Throughput results
echo -e "\n## dd results\n" >> evidence.txt
grep -E "copied,.*s,.*MB/s" /var/log/syslog >> evidence.txt || true
```

Upload `evidence.txt` to your repo or artifact store for traceability.

---

## 7) Rollback Plan

| Scenario | Action |
|----------|--------|
| Locked out of SSH | Detach DO Cloud Firewall or widen CIDRs in DO Console |
| NFS mount broken | Comment out entry in `/etc/fstab`, then `systemctl daemon-reload && systemctl restart remote-fs.target` |
| Exports misconfigured | Revert `/etc/exports` and reload: `sudo exportfs -ra` |
| Full rollback | Destroy droplet: `doctl compute droplet delete "$DROPLET_ID"` (confirm) |

---

## 8) Acceptance Criteria

| # | Criterion | Pass? |
|---|-----------|-------|
| 1 | NFSv4 mount succeeds with `nconnect=4`, `rsize=wsize=1M` | ☐ |
| 2 | Root is squashed to UID/GID 1000 (cannot create files as root) | ☐ |
| 3 | `fstrim.timer` active and executed within last 24h | ☐ |
| 4 | DO Cloud Firewall restricts inbound to SSH (trusted) + `tcp/2049` only | ☐ |
| 5 | UFW parity maintained (same rules as DO FW) | ☐ |
| 6 | SMB mounts negotiate 3.1.1 with encryption (if applicable) | ☐ |
| 7 | Nightly snapshots present with rolling 7‑day retention | ☐ |
| 8 | Throughput ≥50 MB/s on benchmark | ☐ |

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `doctl compute droplet list` | List droplets |
| `doctl compute firewall list` | List firewalls |
| `exportfs -v` | Show NFS exports |
| `mount \| grep nfs4` | Show NFS mounts |
| `nfsstat -s` | NFS server stats |
| `ufw status verbose` | UFW rules |
| `systemctl status fstrim.timer` | TRIM status |

---

**Last Updated**: 2025-11-23
**Version**: 1.0.0
**Related**: `docs/runbooks/NAS_DEPLOYMENT_DO.md`
