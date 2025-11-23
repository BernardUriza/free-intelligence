#!/bin/bash
# Free Intelligence - UFW Firewall Setup for DigitalOcean NAS
# Configures deny-all + allow SSH + NFS from VPC only
#
# Usage: sudo ./scripts/ufw-setup.sh [VPC_CIDR] [--with-smb]
# Example: sudo ./scripts/ufw-setup.sh 10.116.0.0/20 --with-smb

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[UFW]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check root
[[ $EUID -ne 0 ]] && err "Must run as root (sudo)"

# Parse arguments
VPC_CIDR="${1:-10.116.0.0/20}"
ENABLE_SMB=false
[[ "$*" == *"--with-smb"* ]] && ENABLE_SMB=true

echo ""
echo "========================================"
echo -e "${CYAN}Free Intelligence - UFW Setup${NC}"
echo "========================================"
echo ""
log "VPC CIDR: $VPC_CIDR"
log "SMB enabled: $ENABLE_SMB"
echo ""

# 1. Install UFW if needed
if ! command -v ufw &> /dev/null; then
    log "Installing UFW..."
    apt-get update -qq
    apt-get install -y ufw
    ok "UFW installed"
fi

# 2. Reset UFW to default (clean slate)
log "Resetting UFW to defaults..."
ufw --force reset > /dev/null 2>&1
ok "UFW reset"

# 3. Set default policies
log "Setting default policies (deny incoming, allow outgoing)..."
ufw default deny incoming
ufw default allow outgoing
ok "Defaults set"

# 4. Allow SSH from VPC only
log "Allowing SSH from VPC..."
ufw allow from "$VPC_CIDR" to any port 22 proto tcp comment 'SSH from VPC'
ok "SSH allowed"

# 5. Allow NFS (NFSv4 uses port 2049 only)
log "Allowing NFSv4 from VPC..."
ufw allow from "$VPC_CIDR" to any port 2049 proto tcp comment 'NFSv4 from VPC'
ufw allow from "$VPC_CIDR" to any port 111 proto tcp comment 'RPC portmapper'
ufw allow from "$VPC_CIDR" to any port 111 proto udp comment 'RPC portmapper UDP'
ok "NFS allowed"

# 6. Allow SMB if requested
if [ "$ENABLE_SMB" = true ]; then
    log "Allowing SMB from VPC..."
    ufw allow from "$VPC_CIDR" to any port 445 proto tcp comment 'SMB from VPC'
    ufw allow from "$VPC_CIDR" to any port 139 proto tcp comment 'NetBIOS from VPC'
    ufw allow from "$VPC_CIDR" to any port 137 proto udp comment 'NetBIOS NS'
    ufw allow from "$VPC_CIDR" to any port 138 proto udp comment 'NetBIOS DGM'
    ok "SMB allowed"
fi

# 7. Allow loopback
log "Allowing loopback interface..."
ufw allow in on lo
ok "Loopback allowed"

# 8. Enable UFW
log "Enabling UFW..."
ufw --force enable
ok "UFW enabled"

# 9. Show status
echo ""
log "Current UFW rules:"
ufw status verbose

# 10. Show summary
echo ""
echo "========================================"
echo -e "${GREEN}Firewall Configured${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}Allowed Services:${NC}"
echo "  - SSH (22/tcp)     from $VPC_CIDR"
echo "  - NFSv4 (2049/tcp) from $VPC_CIDR"
echo "  - RPC (111)        from $VPC_CIDR"
if [ "$ENABLE_SMB" = true ]; then
echo "  - SMB (445/tcp)    from $VPC_CIDR"
echo "  - NetBIOS (139)    from $VPC_CIDR"
fi
echo ""
echo -e "${CYAN}Default Policy:${NC}"
echo "  - Incoming: DENY (all other traffic blocked)"
echo "  - Outgoing: ALLOW"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "  ufw status numbered   # Show rules with numbers"
echo "  ufw delete [N]        # Delete rule by number"
echo "  ufw reload            # Reload rules"
echo "  ufw disable           # Disable firewall"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  Also configure DigitalOcean Cloud Firewall in the console"
echo "  for defense-in-depth (restrict to VPC CIDR only)."
echo "========================================"
