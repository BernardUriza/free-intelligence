#!/bin/bash
# Free Intelligence - NFS Server Setup for DigitalOcean (Hardened)
# Configures NFSv4 with pseudo-root, root_squash, and proper UID/GID mapping
#
# Usage: sudo ./scripts/nfs-setup.sh [VPC_CIDR]
# Example: sudo ./scripts/nfs-setup.sh 10.116.0.0/20

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[NFS]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check root
[[ $EUID -ne 0 ]] && err "Must run as root (sudo)"

# VPC CIDR (default: DigitalOcean NYC3 VPC range)
VPC_CIDR="${1:-10.116.0.0/20}"
DATA_PATH="/mnt/fi"
EXPORT_ROOT="/export"
EXPORT_PATH="/export/fi"
FI_UID=1000
FI_GID=1000

echo ""
echo "========================================"
echo -e "${CYAN}Free Intelligence - NFS Setup (Hardened)${NC}"
echo "========================================"
echo ""
log "VPC CIDR: $VPC_CIDR"
log "Data path: $DATA_PATH"
log "Export path: $EXPORT_PATH (pseudo-root: $EXPORT_ROOT)"
log "UID/GID: $FI_UID/$FI_GID"
echo ""

# 1. Install NFS packages
log "Installing NFS server packages..."
apt-get update -qq
apt-get install -y nfs-kernel-server nfs-common
ok "NFS packages installed"

# 2. Create data directory if not exists
if [ ! -d "$DATA_PATH" ]; then
    log "Creating data directory..."
    mkdir -p "$DATA_PATH"/{data,backups,logs,config}
    chown -R $FI_UID:$FI_GID "$DATA_PATH"
    chmod 755 "$DATA_PATH"
    ok "Data directory created"
else
    ok "Data directory exists"
fi

# 3. Create NFS pseudo-root with bind mount
log "Creating NFS pseudo-root structure..."
mkdir -p "$EXPORT_ROOT"
mkdir -p "$EXPORT_PATH"

# Create systemd mount unit for bind mount
cat > /etc/systemd/system/export-fi.mount << EOF
[Unit]
Description=Bind mount $DATA_PATH to $EXPORT_PATH for NFS
After=local-fs.target
Requires=local-fs.target

[Mount]
What=$DATA_PATH
Where=$EXPORT_PATH
Type=none
Options=bind

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now export-fi.mount
ok "Pseudo-root bind mount configured"

# 4. Configure /etc/exports with root_squash
log "Configuring NFS exports (with root_squash)..."
cat > /etc/exports << EOF
# Free Intelligence NFS Exports (NFSv4 pseudo-root)
# Generated: $(date)
# VPC CIDR: $VPC_CIDR
#
# Security: root_squash maps client root to anonuid/anongid
# This prevents client root from having full access

# Pseudo-root (read-only, required for NFSv4 proper operation)
$EXPORT_ROOT           $VPC_CIDR(ro,fsid=0,crossmnt,no_subtree_check)

# FI data share (root_squash enforced)
$EXPORT_PATH        $VPC_CIDR(rw,sync,no_subtree_check,root_squash,anonuid=$FI_UID,anongid=$FI_GID)
EOF
ok "Exports configured with root_squash"

# 5. Configure idmapd for NFSv4 (domain must match clients)
log "Configuring NFSv4 ID mapping..."
cat > /etc/idmapd.conf << 'EOF'
[General]
Verbosity = 0
Domain = vpc.local

[Mapping]
Nobody-User = nobody
Nobody-Group = nogroup

[Translation]
Method = nsswitch
EOF
ok "idmapd configured (Domain: vpc.local)"

# 6. Tune NFS server
log "Applying NFS performance tuning..."
cat > /etc/default/nfs-kernel-server << 'EOF'
# NFS server configuration (tuned for HDF5 workloads)
RPCNFSDCOUNT=8
RPCNFSDPRIORITY=0
RPCMOUNTDOPTS="--manage-gids"
NEED_SVCGSSD=""
RPCSVCGSSDOPTS=""
EOF

cat > /etc/sysctl.d/99-nfs-tuning.conf << 'EOF'
# NFS performance tuning
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 30000
EOF
sysctl --system > /dev/null 2>&1
ok "Performance tuning applied"

# 7. Restart NFS services
log "Restarting NFS services..."
systemctl enable nfs-kernel-server
systemctl restart nfs-idmapd
systemctl restart nfs-kernel-server
exportfs -ra
ok "NFS services restarted"

# 8. Enable TRIM for SSD (if applicable)
log "Enabling SSD TRIM timer..."
systemctl enable --now fstrim.timer 2>/dev/null || warn "fstrim.timer not available"

# 9. Verify exports
echo ""
log "Verifying NFS exports..."
exportfs -v

# 10. Show connection info
PRIVATE_IP=$(ip -4 addr show eth1 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
[ -z "$PRIVATE_IP" ] && PRIVATE_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================"
echo -e "${GREEN}NFS Server Ready (Hardened)${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}Server Info:${NC}"
echo "  Pseudo-root: $EXPORT_ROOT"
echo "  Export path: $EXPORT_PATH"
echo "  Private IP:  $PRIVATE_IP"
echo "  VPC CIDR:    $VPC_CIDR"
echo "  UID/GID:     $FI_UID/$FI_GID (root_squash enabled)"
echo ""
echo -e "${CYAN}Client Mount Command (optimized):${NC}"
echo "  # On Linux client (in VPC):"
echo "  sudo mkdir -p /mnt/fi"
echo "  sudo mount -t nfs4 -o rsize=1048576,wsize=1048576,hard,noatime,nconnect=4 $PRIVATE_IP:/fi /mnt/fi"
echo ""
echo "  # Add to /etc/fstab for persistent mount:"
echo "  $PRIVATE_IP:/fi /mnt/fi nfs4 rsize=1048576,wsize=1048576,hard,noatime,nconnect=4,_netdev 0 0"
echo ""
echo -e "${CYAN}Verify Mount:${NC}"
echo "  df -h /mnt/fi"
echo "  touch /mnt/fi/test && rm /mnt/fi/test"
echo ""
echo -e "${CYAN}Server Status:${NC}"
echo "  systemctl status nfs-kernel-server"
echo "  exportfs -v"
echo "  cat /proc/fs/nfsd/versions"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  1. Set Domain=vpc.local in /etc/idmapd.conf on ALL clients"
echo "  2. Create matching DO Cloud Firewall for defense-in-depth"
echo "  3. Run services as UID $FI_UID to match anonuid"
echo "========================================"
