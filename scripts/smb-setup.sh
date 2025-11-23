#!/bin/bash
# Free Intelligence - Samba (SMB) Setup for Windows Clients
# Optional: Use if Windows clients need access to /mnt/fi
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

echo ""
echo "========================================"
echo -e "${CYAN}Free Intelligence - SMB Setup${NC}"
echo "========================================"
echo ""

# Prompt for password if not provided
if [ -z "$SMB_PASSWORD" ]; then
    read -sp "Enter SMB password for $SMB_USER: " SMB_PASSWORD
    echo ""
    [ -z "$SMB_PASSWORD" ] && err "Password cannot be empty"
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

# 3. Create Samba configuration
log "Configuring Samba..."
cat > /etc/samba/smb.conf << EOF
# Free Intelligence - Samba Configuration
# Generated: $(date)
# Share: \\\\$(hostname -I | awk '{print $1}')\\$SHARE_NAME

[global]
   workgroup = WORKGROUP
   server string = Free Intelligence NAS
   security = user
   map to guest = never

   # Performance tuning
   socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
   read raw = yes
   write raw = yes
   max xmit = 65535
   dead time = 15
   getwd cache = yes

   # Security
   client min protocol = SMB2
   server min protocol = SMB2
   smb encrypt = desired

   # Logging
   log file = /var/log/samba/log.%m
   max log size = 1000
   logging = file

[$SHARE_NAME]
   comment = Free Intelligence Data
   path = $SHARE_PATH
   browseable = yes
   read only = no
   writable = yes
   create mask = 0664
   directory mask = 0775
   valid users = $SMB_USER
   force user = fi
   force group = fi
EOF
ok "Samba configured"

# 4. Create system user if not exists
if ! id "$SMB_USER" &>/dev/null; then
    log "Creating system user $SMB_USER..."
    useradd -M -s /usr/sbin/nologin "$SMB_USER"
    ok "User created"
fi

# 5. Set Samba password
log "Setting Samba password..."
(echo "$SMB_PASSWORD"; echo "$SMB_PASSWORD") | smbpasswd -a "$SMB_USER" -s
smbpasswd -e "$SMB_USER"
ok "Samba password set"

# 6. Ensure directory permissions
log "Setting directory permissions..."
chown -R 1000:1000 "$SHARE_PATH"
chmod 2775 "$SHARE_PATH"
ok "Permissions set"

# 7. Restart Samba
log "Restarting Samba services..."
systemctl enable smbd nmbd
systemctl restart smbd nmbd
ok "Samba services restarted"

# 8. Test configuration
log "Testing Samba configuration..."
testparm -s 2>/dev/null | head -20

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================"
echo -e "${GREEN}SMB Server Ready${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}Connection Info:${NC}"
echo "  Share path:  \\\\$SERVER_IP\\$SHARE_NAME"
echo "  Username:    $SMB_USER"
echo "  Password:    [as configured]"
echo ""
echo -e "${CYAN}Windows Client:${NC}"
echo "  1. Open File Explorer"
echo "  2. Enter: \\\\$SERVER_IP\\$SHARE_NAME"
echo "  3. Use credentials: $SMB_USER / [password]"
echo ""
echo -e "${CYAN}Map Network Drive (cmd):${NC}"
echo "  net use Z: \\\\$SERVER_IP\\$SHARE_NAME /user:$SMB_USER /persistent:yes"
echo ""
echo -e "${CYAN}Linux Client (optional):${NC}"
echo "  sudo mount -t cifs //$SERVER_IP/$SHARE_NAME /mnt/fi -o user=$SMB_USER,password=XXX"
echo ""
echo -e "${CYAN}Server Status:${NC}"
echo "  systemctl status smbd"
echo "  smbstatus"
echo "  pdbedit -L"
echo "========================================"
