#!/bin/bash
# Free Intelligence - UFW Firewall Setup for DigitalOcean NAS
# Configures deny-all + allow SSH + NFS from VPC only
#
# IMPORTANT: Also create a matching DO Cloud Firewall for defense-in-depth
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

# 6. Allow SMB if requested (SMB3 only - port 445)
if [ "$ENABLE_SMB" = true ]; then
    log "Allowing SMB from VPC (port 445 only for SMB3)..."
    ufw allow from "$VPC_CIDR" to any port 445 proto tcp comment 'SMB3 from VPC'
    # Note: ports 137-139 are for legacy NetBIOS, not needed for SMB3
    ok "SMB3 allowed"
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

# 10. Generate DO Cloud Firewall equivalent
echo ""
echo "========================================"
echo -e "${GREEN}Firewall Configured${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}UFW Rules Applied:${NC}"
echo "  - SSH (22/tcp)     from $VPC_CIDR"
echo "  - NFSv4 (2049/tcp) from $VPC_CIDR"
echo "  - RPC (111)        from $VPC_CIDR"
if [ "$ENABLE_SMB" = true ]; then
echo "  - SMB3 (445/tcp)   from $VPC_CIDR"
fi
echo ""
echo -e "${CYAN}Default Policy:${NC}"
echo "  - Incoming: DENY (all other traffic blocked)"
echo "  - Outgoing: ALLOW"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}IMPORTANT: Create DO Cloud Firewall Too!${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Defense-in-depth: If someone disables UFW, the Cloud Firewall"
echo "still protects the Droplet. Create via DO Console or CLI:"
echo ""
echo -e "${CYAN}doctl compute firewall create \\${NC}"
echo "  --name fi-nas-fw \\"
echo "  --droplet-ids \$(doctl compute droplet get fi-nas --format ID --no-header) \\"
echo "  --inbound-rules \"protocol:tcp,ports:22,address:$VPC_CIDR\" \\"
echo "  --inbound-rules \"protocol:tcp,ports:2049,address:$VPC_CIDR\" \\"
echo "  --inbound-rules \"protocol:tcp,ports:111,address:$VPC_CIDR\" \\"
echo "  --inbound-rules \"protocol:udp,ports:111,address:$VPC_CIDR\" \\"
if [ "$ENABLE_SMB" = true ]; then
echo "  --inbound-rules \"protocol:tcp,ports:445,address:$VPC_CIDR\" \\"
fi
echo "  --outbound-rules \"protocol:tcp,ports:all,address:0.0.0.0/0\" \\"
echo "  --outbound-rules \"protocol:udp,ports:all,address:0.0.0.0/0\""
echo ""
echo -e "${CYAN}Verify Firewall:${NC}"
echo "  doctl compute firewall list"
echo ""
echo -e "${CYAN}UFW Commands:${NC}"
echo "  ufw status numbered   # Show rules with numbers"
echo "  ufw delete [N]        # Delete rule by number"
echo "  ufw reload            # Reload rules"
echo "  ufw disable           # Disable firewall (NOT recommended)"
echo "========================================"
