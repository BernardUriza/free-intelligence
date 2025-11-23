# Free Intelligence - DigitalOcean NAS Deployment Runbook

Deploy FI as a simulated NAS on DigitalOcean using Droplet + Block Storage + NFSv4.

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
# Create Droplet with cloud-init
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

## 4. Verify NAS Setup

```bash
# SSH into NAS (via public IP initially, or bastion)
ssh root@$(doctl compute droplet get fi-nas --format PublicIPv4 --no-header)

# Inside NAS - verify mount
df -h /mnt/fi
# Expected: /dev/sda mounted at /mnt/fi

# Verify NFS exports
exportfs -v
# Expected: /mnt/fi 10.116.0.0/20(rw,sync,...)

# Verify UFW
ufw status
# Expected: 22, 2049, 111 allowed from VPC CIDR

# Check directory structure
tree -L 2 /mnt/fi
# Expected: data/, backups/, logs/, config/
```

---

## 5. Mount NFS from Client VM

On another Droplet in the same VPC:

```bash
# Install NFS client
apt-get update && apt-get install -y nfs-common

# Create mount point
mkdir -p /mnt/fi

# Test mount
mount -t nfs4 -o rw,sync,hard,intr 10.116.0.2:/mnt/fi /mnt/fi

# Verify
df -h /mnt/fi
touch /mnt/fi/test-write && rm /mnt/fi/test-write
echo "NFS mount successful!"

# Add to fstab for persistence
echo "10.116.0.2:/mnt/fi /mnt/fi nfs4 rw,sync,hard,intr,_netdev 0 0" >> /etc/fstab
```

---

## 6. Configure Snapshots (Backup)

### Manual Snapshot

```bash
# Create snapshot of volume
doctl compute volume-action snapshot $VOLUME_ID \
  --snapshot-name "fi-data-$(date +%Y%m%d-%H%M)"

# List snapshots
doctl compute snapshot list --resource volume
```

### Automated Snapshots (Weekly)

```bash
# Create DO cron job or use external scheduler
# Example: every Sunday at 2 AM UTC
# 0 2 * * 0 doctl compute volume-action snapshot $VOLUME_ID --snapshot-name "fi-weekly-$(date +%Y%m%d)"
```

---

## 7. Resize Volume (When Needed)

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

## 8. Failover / Recovery

### Scenario: NAS Droplet Failure

```bash
# 1. Create new Droplet from snapshot or cloud-init
doctl compute droplet create fi-nas-recovery \
  --region nyc3 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --vpc-uuid $VPC_UUID \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header | head -1) \
  --user-data-file infra/cloud-init.yaml \
  --wait

# 2. Detach volume from failed Droplet
doctl compute volume-action detach $VOLUME_ID --droplet-id OLD_DROPLET_ID

# 3. Attach to new Droplet
NEW_DROPLET_ID=$(doctl compute droplet get fi-nas-recovery --format ID --no-header)
doctl compute volume-action attach $VOLUME_ID --droplet-id $NEW_DROPLET_ID

# 4. SSH and remount
ssh root@NEW_IP << 'EOF'
  mount -a
  systemctl restart nfs-kernel-server
  exportfs -ra
EOF

# 5. Update DNS or client fstab with new IP
```

### Scenario: Restore from Snapshot

```bash
# 1. List available snapshots
doctl compute snapshot list --resource volume

# 2. Create new volume from snapshot
doctl compute volume create fi-data-restored \
  --region nyc3 \
  --snapshot-id SNAPSHOT_ID

# 3. Attach to NAS and mount as needed
```

---

## 9. Monitoring

### Droplet Metrics

```bash
# CPU, RAM, Disk via doctl
doctl monitoring droplet bandwidth $DROPLET_ID --start $(date -d '1 hour ago' +%s) --end $(date +%s)

# Or use DO Monitoring in console
# https://cloud.digitalocean.com/droplets/fi-nas/graphs
```

### NFS Performance

```bash
# On NAS server
nfsstat -s          # Server stats
cat /proc/net/rpc/nfsd  # Detailed stats

# On client
nfsstat -c          # Client stats
nfsiostat 1 5       # I/O stats every 1s, 5 times
```

### Alerts (DO Console)

1. Go to Monitoring > Create Alert
2. Set alerts for:
   - CPU > 80% for 5 min
   - Disk > 85% used
   - Droplet down

---

## 10. Cost Breakdown

| Resource | Spec | Monthly Cost |
|----------|------|--------------|
| Droplet | s-2vcpu-4gb | $24 |
| Block Storage | 100GB SSD | $10 |
| Snapshots | ~10GB retained | $0.05/GB = ~$0.50 |
| Egress (VPC) | Internal | $0 |
| **Total** | | **~$35/month** |

For smaller workloads:
- s-1vcpu-2gb Droplet: $12/month
- 50GB Volume: $5/month
- **Budget Total: ~$17/month**

---

## 11. Troubleshooting

### NFS Mount Fails

```bash
# Check exports on server
ssh root@NAS_IP "exportfs -v"

# Check firewall
ssh root@NAS_IP "ufw status"

# Check client can reach server
nc -zv NAS_IP 2049

# Check NFS versions
ssh root@NAS_IP "cat /proc/fs/nfsd/versions"
# Should show: +4.2 +4.1

# Force NFSv4
mount -t nfs4 -o vers=4.1 NAS_IP:/mnt/fi /mnt/fi
```

### HDF5 Locking Issues

If corpus.h5 shows `ESTALE` or locking errors:

```bash
# 1. Use NFSv4.1+ (already configured)
# 2. Enable SWMR in HDF5 code (backend change required)
# 3. Alternative: Use SQLite instead of HDF5 for new features
```

### Slow Performance

```bash
# Benchmark
dd if=/dev/zero of=/mnt/fi/test bs=1M count=1024 oflag=direct
# Expected: >50MB/s on SSD Block Storage

# Check network MTU
ip link show eth1

# Enable jumbo frames (if VPC supports)
ip link set eth1 mtu 9000
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

---

**Last Updated**: 2025-11-23
**Author**: Claude Code (Cloud Architect)
**Version**: 1.0.0
