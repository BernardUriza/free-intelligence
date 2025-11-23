#!/bin/bash
# Free Intelligence - Samba (SMB) Setup for Windows Clients (Hardened)
# SMB3 only, encryption required, no legacy auth
#
# Usage: sudo ./scripts/smb-setup.sh [SMB_USER] [SMB_PASSWORD]
# Example: sudo ./scripts/smb-setup.sh fiuser SecureP@ss123

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[SMB]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check root
[[ $EUID -ne 0 ]] && err "Must run as root (sudo)"

# Configuration
SMB_USER="${1:-fiuser}"
SMB_PASSWORD="${2:-}"
SHARE_PATH="/mnt/fi"
SHARE_NAME="fi"
FI_UID=1000
FI_GID=1000

echo ""
echo "========================================"
echo -e "${CYAN}Free Intelligence - SMB Setup (Hardened)${NC}"
echo "========================================"
echo ""

# Prompt for password if not provided
if [ -z "$SMB_PASSWORD" ]; then
    read -sp "Enter SMB password for $SMB_USER: " SMB_PASSWORD
    echo ""
    [ -z "$SMB_PASSWORD" ] && err "Password cannot be empty"

    # Validate password strength
    if [ ${#SMB_PASSWORD} -lt 12 ]; then
        warn "Password should be at least 12 characters for production"
    fi
fi

# 1. Install Samba
log "Installing Samba packages..."
apt-get update -qq
apt-get install -y samba samba-common-bin
ok "Samba installed"

# 2. Backup original config
if [ -f /etc/samba/smb.conf ] && [ ! -f /etc/samba/smb.conf.bak ]; then
    cp /etc/samba/smb.conf /etc/samba/smb.conf.bak
    ok "Original config backed up"
fi

# 3. Create hardened Samba configuration (SMB3 only)
log "Configuring Samba (SMB3, encryption required)..."
cat > /etc/samba/smb.conf << EOF
# Free Intelligence - Samba Configuration (Hardened)
# Generated: $(date)
# Share: \\\\$(hostname -I | awk '{print $1}')\\$SHARE_NAME

[global]
   workgroup = WORKGROUP
   server string = Free Intelligence NAS
   security = user
   map to guest = never

   # ============================================================
   # SECURITY HARDENING (SMB3 only, no legacy protocols)
   # ============================================================
   # Force SMB3 minimum (Windows 8+, macOS 10.9+)
   server min protocol = SMB3
   client min protocol = SMB3

   # Disable legacy authentication (NTLM, LanMan)
   ntlm auth = no
   lanman auth = no
   raw NTLMv2 auth = no

   # Require encryption for all connections
   smb encrypt = required

   # Disable anonymous/guest access
   restrict anonymous = 2
   guest ok = no

   # Disable unused features
   load printers = no
   printing = bsd
   printcap name = /dev/null
   disable spoolss = yes

   # ============================================================
   # PERFORMANCE
   # ============================================================
   socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
   read raw = yes
   write raw = yes
   max xmit = 65535
   dead time = 15
   getwd cache = yes

   # Async I/O (improves performance on Linux)
   aio read size = 1
   aio write size = 1

   # ============================================================
   # LOGGING
   # ============================================================
   log file = /var/log/samba/log.%m
   max log size = 1000
   logging = file
   log level = 1 auth:3

[$SHARE_NAME]
   comment = Free Intelligence Data
   path = $SHARE_PATH
   browseable = yes
   read only = no
   writable = yes

   # Permissions
   create mask = 0664
   directory mask = 0775
   force create mode = 0664
   force directory mode = 0775

   # Access control (no guests)
   valid users = $SMB_USER
   guest ok = no

   # Force UID/GID to match NFS (consistency)
   force user = fi
   force group = fi

   # VFS objects for audit (optional)
   # vfs objects = full_audit
   # full_audit:prefix = %u|%I|%S
   # full_audit:success = connect disconnect mkdir rmdir open read write rename unlink
   # full_audit:failure = none
   # full_audit:facility = local5
   # full_audit:priority = notice
EOF
ok "Samba configured (SMB3 + encryption required)"

# 4. Create system user if not exists
if ! id "fi" &>/dev/null; then
    log "Creating system user 'fi' (UID $FI_UID)..."
    useradd -M -u $FI_UID -s /usr/sbin/nologin fi
    ok "User 'fi' created"
fi

if ! id "$SMB_USER" &>/dev/null; then
    log "Creating SMB user '$SMB_USER'..."
    useradd -M -s /usr/sbin/nologin "$SMB_USER"
    ok "User '$SMB_USER' created"
fi

# 5. Set Samba password
log "Setting Samba password..."
(echo "$SMB_PASSWORD"; echo "$SMB_PASSWORD") | smbpasswd -a "$SMB_USER" -s
smbpasswd -e "$SMB_USER"
ok "Samba password set"

# 6. Ensure directory permissions
log "Setting directory permissions..."
chown -R $FI_UID:$FI_GID "$SHARE_PATH"
chmod 2775 "$SHARE_PATH"
ok "Permissions set"

# 7. Test configuration
log "Testing Samba configuration..."
testparm -s 2>/dev/null | grep -E "(server min protocol|smb encrypt|ntlm auth)" || true

# 8. Restart Samba
log "Restarting Samba services..."
systemctl enable smbd nmbd
systemctl restart smbd nmbd
ok "Samba services restarted"

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================"
echo -e "${GREEN}SMB Server Ready (Hardened)${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}Security Settings:${NC}"
echo "  - Protocol: SMB3 minimum (no SMB1/SMB2)"
echo "  - Encryption: Required"
echo "  - Legacy auth: Disabled (no NTLM/LanMan)"
echo "  - Guest access: Disabled"
echo ""
echo -e "${CYAN}Connection Info:${NC}"
echo "  Share path:  \\\\$SERVER_IP\\$SHARE_NAME"
echo "  Username:    $SMB_USER"
echo "  Password:    [as configured]"
echo ""
echo -e "${CYAN}Windows Client (Windows 10+):${NC}"
echo "  1. Open File Explorer"
echo "  2. Enter: \\\\$SERVER_IP\\$SHARE_NAME"
echo "  3. Use credentials: $SMB_USER / [password]"
echo ""
echo -e "${CYAN}Map Network Drive (PowerShell):${NC}"
echo "  New-PSDrive -Name Z -PSProvider FileSystem -Root \\\\$SERVER_IP\\$SHARE_NAME -Persist -Credential (Get-Credential)"
echo ""
echo -e "${CYAN}macOS Client (10.9+):${NC}"
echo "  Finder > Go > Connect to Server > smb://$SERVER_IP/$SHARE_NAME"
echo ""
echo -e "${CYAN}Server Status:${NC}"
echo "  systemctl status smbd"
echo "  smbstatus"
echo "  pdbedit -L"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  Windows 7 and older clients will NOT connect (SMB3 required)"
echo "  macOS 10.8 and older clients will NOT connect"
echo "========================================"
