#!/bin/bash
# Free Intelligence - NFS Server Setup for DigitalOcean
# Run on existing Droplet to configure NFS exports
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
EXPORT_PATH="/mnt/fi"

echo ""
echo "========================================"
echo -e "${CYAN}Free Intelligence - NFS Setup${NC}"
echo "========================================"
echo ""
log "VPC CIDR: $VPC_CIDR"
log "Export path: $EXPORT_PATH"
echo ""

# 1. Install NFS packages
log "Installing NFS server packages..."
apt-get update -qq
apt-get install -y nfs-kernel-server nfs-common
ok "NFS packages installed"

# 2. Create export directory if not exists
if [ ! -d "$EXPORT_PATH" ]; then
    log "Creating export directory..."
    mkdir -p "$EXPORT_PATH"/{data,backups,logs,config}
    chown -R 1000:1000 "$EXPORT_PATH"
    chmod 755 "$EXPORT_PATH"
    ok "Directory structure created"
else
    ok "Export directory exists"
fi

# 3. Configure /etc/exports
log "Configuring NFS exports..."
cat > /etc/exports << EOF
# Free Intelligence NFS Exports
# Generated: $(date)
# VPC CIDR: $VPC_CIDR

# Main FI data export (VPC-only, NFSv4)
$EXPORT_PATH $VPC_CIDR(rw,sync,no_subtree_check,no_root_squash,crossmnt)
EOF
ok "Exports configured"

# 4. Configure idmapd for NFSv4
log "Configuring NFSv4 ID mapping..."
cat > /etc/idmapd.conf << 'EOF'
[General]
Verbosity = 0
Domain = fi.local

[Mapping]
Nobody-User = nobody
Nobody-Group = nogroup

[Translation]
Method = nsswitch
EOF
ok "idmapd configured"

# 5. Tune NFS server
log "Applying NFS performance tuning..."
cat > /etc/default/nfs-kernel-server << 'EOF'
# NFS server configuration
RPCNFSDCOUNT=8
RPCNFSDPRIORITY=0
RPCMOUNTDOPTS="--manage-gids"
NEED_SVCGSSD=""
RPCSVCGSSDOPTS=""
EOF

cat > /etc/sysctl.d/99-nfs-tuning.conf << 'EOF'
# NFS performance tuning for HDF5 workloads
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 30000
EOF
sysctl --system > /dev/null 2>&1
ok "Performance tuning applied"

# 6. Restart NFS services
log "Restarting NFS services..."
systemctl enable nfs-kernel-server
systemctl restart nfs-idmapd
systemctl restart nfs-kernel-server
exportfs -ra
ok "NFS services restarted"

# 7. Verify exports
echo ""
log "Verifying NFS exports..."
exportfs -v

# 8. Show connection info
PRIVATE_IP=$(ip -4 addr show eth1 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
[ -z "$PRIVATE_IP" ] && PRIVATE_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================"
echo -e "${GREEN}NFS Server Ready${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}Server Info:${NC}"
echo "  Export path: $EXPORT_PATH"
echo "  Private IP:  $PRIVATE_IP"
echo "  VPC CIDR:    $VPC_CIDR"
echo ""
echo -e "${CYAN}Client Mount Command:${NC}"
echo "  # On Linux client (in VPC):"
echo "  sudo mkdir -p /mnt/fi"
echo "  sudo mount -t nfs4 -o rw,sync,hard,intr $PRIVATE_IP:$EXPORT_PATH /mnt/fi"
echo ""
echo "  # Add to /etc/fstab for persistent mount:"
echo "  $PRIVATE_IP:$EXPORT_PATH /mnt/fi nfs4 rw,sync,hard,intr,_netdev 0 0"
echo ""
echo -e "${CYAN}Verify Mount:${NC}"
echo "  df -h /mnt/fi"
echo "  touch /mnt/fi/test && rm /mnt/fi/test"
echo ""
echo -e "${CYAN}Server Status:${NC}"
echo "  systemctl status nfs-kernel-server"
echo "  exportfs -v"
echo "  cat /proc/fs/nfsd/versions"
echo "========================================"
