# Free Intelligence - DigitalOcean NAS Deployment Runbook

Deploy FI as a simulated NAS on DigitalOcean using Droplet + Block Storage + NFSv4 (hardened).

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| DO Account | With billing enabled |
| doctl CLI | `brew install doctl` + `doctl auth init` |
| SSH Key | Uploaded to DO (Settings > Security) |
| VPC | Created in target region (e.g., nyc3) |

---

## 1. Provision VPC (One-time)

```bash
# Create VPC in NYC3 region
doctl vpcs create \
  --name fi-vpc \
  --region nyc3 \
  --ip-range 10.116.0.0/20 \
  --description "Free Intelligence private network"

# Get VPC UUID for next steps
VPC_UUID=$(doctl vpcs list --format ID,Name --no-header | grep fi-vpc | awk '{print $1}')
echo "VPC UUID: $VPC_UUID"
```

---

## 2. Create Block Storage Volume

```bash
# Create 100GB SSD volume
doctl compute volume create fi-data \
  --region nyc3 \
  --size 100GiB \
  --fs-type ext4 \
  --desc "Free Intelligence data volume"

# Get Volume ID
VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep fi-data | awk '{print $1}')
echo "Volume ID: $VOLUME_ID"
```

---

## 3. Create NAS Droplet with cloud-init

```bash
# Create Droplet with cloud-init (hardened config)
doctl compute droplet create fi-nas \
  --region nyc3 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --vpc-uuid $VPC_UUID \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1) \
  --user-data-file infra/cloud-init.yaml \
  --volumes $VOLUME_ID \
  --wait

# Get private IP
NAS_IP=$(doctl compute droplet get fi-nas --format PrivateIPv4 --no-header)
echo "NAS Private IP: $NAS_IP"
```

---

## 4. Create DO Cloud Firewall (Defense-in-Depth)

**IMPORTANT**: UFW runs on the Droplet, but a DO Cloud Firewall provides protection even if UFW is disabled.

```bash
# Get Droplet ID
DROPLET_ID=$(doctl compute droplet get fi-nas --format ID --no-header)

# Create Cloud Firewall matching UFW rules
doctl compute firewall create \
  --name fi-nas-fw \
  --droplet-ids $DROPLET_ID \
  --inbound-rules "protocol:tcp,ports:22,address:10.116.0.0/20" \
  --inbound-rules "protocol:tcp,ports:2049,address:10.116.0.0/20" \
  --inbound-rules "protocol:tcp,ports:111,address:10.116.0.0/20" \
  --inbound-rules "protocol:udp,ports:111,address:10.116.0.0/20" \
  --outbound-rules "protocol:tcp,ports:all,address:0.0.0.0/0" \
  --outbound-rules "protocol:udp,ports:all,address:0.0.0.0/0" \
  --outbound-rules "protocol:icmp,address:0.0.0.0/0"

# Verify
doctl compute firewall list
```

---

## 5. Verify NAS Setup

```bash
# SSH into NAS (via public IP initially, or bastion)
ssh root@$(doctl compute droplet get fi-nas --format PublicIPv4 --no-header)

# Inside NAS - verify mount
df -h /mnt/fi
# Expected: /dev/disk/by-id/scsi-0DO_Volume_fi-data mounted at /mnt/fi

# Verify bind mount for NFS pseudo-root
mount | grep /export/fi
# Expected: /mnt/fi on /export/fi type none (rw,bind)

# Verify NFS exports (pseudo-root structure)
exportfs -v
# Expected:
# /export         10.116.0.0/20(ro,fsid=0,crossmnt,...)
# /export/fi      10.116.0.0/20(rw,sync,root_squash,anonuid=1000,anongid=1000,...)

# Verify UFW
ufw status verbose
# Expected: 22, 2049, 111 allowed from VPC CIDR only

# Check TRIM timer
systemctl status fstrim.timer
# Expected: active (enabled)

# Check directory structure
tree -L 2 /mnt/fi
# Expected: data/, backups/, logs/, config/
```

---

## 6. Mount NFS from Client VM (Optimized)

On another Droplet in the same VPC:

```bash
# Install NFS client
apt-get update && apt-get install -y nfs-common

# Configure idmapd domain (MUST match server)
cat > /etc/idmapd.conf << 'EOF'
[General]
Verbosity = 0
Domain = vpc.local

[Mapping]
Nobody-User = nobody
Nobody-Group = nogroup
EOF
systemctl restart nfs-idmapd

# Create mount point
mkdir -p /mnt/fi

# Mount with optimized options (nconnect=4 for modern kernels)
mount -t nfs4 -o rsize=1048576,wsize=1048576,hard,noatime,nconnect=4 $NAS_IP:/fi /mnt/fi

# Verify
df -h /mnt/fi
touch /mnt/fi/test-write && rm /mnt/fi/test-write
echo "NFS mount successful!"

# Add to fstab for persistence (optimized options)
echo "$NAS_IP:/fi /mnt/fi nfs4 rsize=1048576,wsize=1048576,hard,noatime,nconnect=4,_netdev 0 0" >> /etc/fstab
```

### Mount Options Explained

| Option | Purpose |
|--------|---------|
| `rsize=1048576,wsize=1048576` | 1MB read/write buffers (max throughput) |
| `hard` | Retry indefinitely on NFS errors (data safety) |
| `noatime` | Don't update access times (reduces I/O) |
| `nconnect=4` | 4 parallel TCP connections (kernel 5.3+) |
| `_netdev` | Wait for network before mounting |

---

## 7. Configure Snapshots (Automated)

### Manual Snapshot

```bash
# Create snapshot of volume
VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep fi-data | awk '{print $1}')
doctl compute volume-action snapshot $VOLUME_ID \
  --snapshot-name "fi-data-$(date +%Y%m%d-%H%M)"

# List snapshots
doctl compute snapshot list --resource volume
```

### Automated Nightly Snapshots

Create a cron job on your **control plane** (not the NAS):

```bash
# Create snapshot script
cat > /usr/local/bin/fi-snapshot.sh << 'EOF'
#!/bin/bash
# FI Volume Nightly Snapshot
VOLUME_ID=$(doctl compute volume list --format ID,Name --no-header | grep fi-data | awk '{print $1}')
SNAPSHOT_NAME="fi-nightly-$(date +%Y%m%d)"

# Create snapshot
doctl compute volume-action snapshot $VOLUME_ID --snapshot-name "$SNAPSHOT_NAME"

# Delete snapshots older than 7 days
doctl compute snapshot list --resource volume --format ID,Name,Created --no-header | \
  grep fi-nightly | \
  while read id name created; do
    age_days=$(( ($(date +%s) - $(date -d "$created" +%s)) / 86400 ))
    if [ $age_days -gt 7 ]; then
      echo "Deleting old snapshot: $name ($age_days days old)"
      doctl compute snapshot delete $id --force
    fi
  done

echo "$(date): Snapshot $SNAPSHOT_NAME created" >> /var/log/fi-snapshots.log
EOF
chmod +x /usr/local/bin/fi-snapshot.sh

# Add to crontab (runs at 2 AM UTC daily)
echo "0 2 * * * /usr/local/bin/fi-snapshot.sh" | crontab -
```

---

## 8. Resize Volume (When Needed)

```bash
# Check current usage
ssh root@$NAS_IP "df -h /mnt/fi"

# Resize volume (online, no downtime)
doctl compute volume-action resize $VOLUME_ID --size 200 --region nyc3

# Extend filesystem on NAS
ssh root@$NAS_IP << 'EOF'
  # Find device
  DEVICE=$(mount | grep /mnt/fi | awk '{print $1}')
  # Resize filesystem
  resize2fs $DEVICE
  # Verify new size
  df -h /mnt/fi
EOF
```

---

## 9. Failover / Recovery

### Scenario: NAS Droplet Failure

```bash
# 1. Create new Droplet from cloud-init
doctl compute droplet create fi-nas-recovery \
  --region nyc3 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --vpc-uuid $VPC_UUID \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1) \
  --user-data-file infra/cloud-init.yaml \
  --wait

# 2. Detach volume from failed Droplet
OLD_DROPLET_ID=$(doctl compute droplet list --format ID,Name --no-header | grep fi-nas | head -1 | awk '{print $1}')
doctl compute volume-action detach $VOLUME_ID --droplet-id $OLD_DROPLET_ID --wait

# 3. Attach to new Droplet
NEW_DROPLET_ID=$(doctl compute droplet get fi-nas-recovery --format ID --no-header)
doctl compute volume-action attach $VOLUME_ID --droplet-id $NEW_DROPLET_ID --wait

# 4. SSH and configure
NEW_IP=$(doctl compute droplet get fi-nas-recovery --format PrivateIPv4 --no-header)
ssh root@$NEW_IP << 'EOF'
  mount -a
  systemctl restart export-fi.mount
  systemctl restart nfs-kernel-server
  exportfs -ra
  exportfs -v
EOF

# 5. Update DO Cloud Firewall with new Droplet
doctl compute firewall update fi-nas-fw --droplet-ids $NEW_DROPLET_ID

# 6. Update client fstab with new IP
echo "Update clients: sed -i 's/OLD_IP/$NEW_IP/g' /etc/fstab && mount -a"
```

### Scenario: Restore from Snapshot

```bash
# 1. List available snapshots
doctl compute snapshot list --resource volume

# 2. Create new volume from snapshot
doctl compute volume create fi-data-restored \
  --region nyc3 \
  --snapshot-id SNAPSHOT_ID

# 3. Attach to NAS and mount
```

---

## 10. Monitoring

### Droplet Metrics

```bash
# Via doctl
doctl monitoring droplet bandwidth $DROPLET_ID --start $(date -d '1 hour ago' +%s) --end $(date +%s)

# DO Console: https://cloud.digitalocean.com/droplets/fi-nas/graphs
```

### NFS Performance

```bash
# On NAS server
nfsstat -s              # Server stats
cat /proc/net/rpc/nfsd  # Detailed stats
nfsdcltrack list        # Active clients

# On client
nfsstat -c              # Client stats
nfsiostat 1 5           # I/O stats every 1s, 5 times

# Benchmark throughput
dd if=/dev/zero of=/mnt/fi/bench bs=1M count=1024 oflag=direct
# Expected: >100MB/s with nconnect=4
```

### Alerts (DO Console)

1. Go to Monitoring > Create Alert
2. Set alerts for:
   - CPU > 80% for 5 min
   - Disk > 85% used
   - Droplet down

---

## 11. Cost Breakdown

| Resource | Spec | Monthly Cost |
|----------|------|--------------|
| Droplet | s-2vcpu-4gb | $24 |
| Block Storage | 100GB SSD | $10 |
| Snapshots | ~10GB retained (7 days) | ~$0.50 |
| Egress (VPC) | Internal | $0 |
| **Total** | | **~$35/month** |

For smaller workloads:
- s-1vcpu-2gb Droplet: $12/month
- 50GB Volume: $5/month
- **Budget Total: ~$17/month**

---

## 12. Troubleshooting

### NFS Mount Fails

```bash
# Check exports on server (should show pseudo-root)
ssh root@$NAS_IP "exportfs -v"

# Check firewall (both UFW and DO Cloud Firewall)
ssh root@$NAS_IP "ufw status"
doctl compute firewall list

# Check client can reach server
nc -zv $NAS_IP 2049

# Check NFS versions
ssh root@$NAS_IP "cat /proc/fs/nfsd/versions"
# Should show: +4.2 +4.1

# Mount with pseudo-root path (note: /fi not /mnt/fi)
mount -t nfs4 -o vers=4.1 $NAS_IP:/fi /mnt/fi
```

### UID/GID Mismatch (files show "nobody")

```bash
# Verify idmapd domain matches on both server and client
cat /etc/idmapd.conf | grep Domain
# Both should show: Domain = vpc.local

# Restart idmapd
systemctl restart nfs-idmapd
```

### HDF5 Locking Issues

If corpus.h5 shows `ESTALE` or locking errors:

```bash
# 1. Verify NFSv4.1+ is in use
mount | grep nfs4

# 2. Check for stale locks
lslocks | grep corpus.h5

# 3. Options if locking still fails:
#    a) Enable SWMR in HDF5 code (backend change)
#    b) Stage writes locally, flush periodically
#    c) Migrate to SQLite/Parquet for concurrent access
```

### Slow Performance

```bash
# Benchmark (expect >100MB/s with nconnect=4)
dd if=/dev/zero of=/mnt/fi/test bs=1M count=1024 oflag=direct
rm /mnt/fi/test

# Verify nconnect is active
cat /proc/mounts | grep /mnt/fi
# Should show: nconnect=4

# Check if nconnect is supported (kernel 5.3+)
uname -r

# Monitor network
iftop -i eth1
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| SSH to NAS | `ssh root@$(doctl compute droplet get fi-nas --format PublicIPv4 --no-header)` |
| Check exports | `exportfs -v` |
| Restart NFS | `systemctl restart nfs-kernel-server` |
| Create snapshot | `doctl compute volume-action snapshot $VOLUME_ID --snapshot-name "backup-$(date +%Y%m%d)"` |
| Resize volume | `doctl compute volume-action resize $VOLUME_ID --size 200 --region nyc3` |
| Check disk | `df -h /mnt/fi` |
| NFS stats | `nfsstat -s` |
| List firewalls | `doctl compute firewall list` |
| TRIM status | `systemctl status fstrim.timer` |

---

## Security Checklist

- [ ] UFW enabled with VPC-only rules
- [ ] DO Cloud Firewall matching UFW rules
- [ ] root_squash enabled (no client root access)
- [ ] idmapd Domain matches on all nodes
- [ ] SMB3 with encryption (if SMB enabled)
- [ ] No public IP on NAS (VPC-only access)
- [ ] Weekly snapshots automated
- [ ] TRIM timer enabled

---

**Last Updated**: 2025-11-23
**Author**: Claude Code (Cloud Architect)
**Version**: 1.1.0 (Hardened)
