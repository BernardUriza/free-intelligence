#!/bin/bash
# Setup systemd service for Aurity Backend
# Run this script ON the production server (104.131.175.65)

set -e

echo "🔧 Setting up Aurity Backend systemd service..."

# Create systemd service file
cat > /etc/systemd/system/aurity-backend.service << 'EOF'
[Unit]
Description=Aurity Backend FastAPI Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/free-intelligence
Environment="PYTHONPATH=/opt/free-intelligence"
ExecStart=/usr/bin/python3.14 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=aurity-backend

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"

# Reload systemd
systemctl daemon-reload
echo "✅ systemd reloaded"

# Enable service (start on boot)
systemctl enable aurity-backend
echo "✅ Service enabled"

# Kill any existing uvicorn process
pkill -f "uvicorn backend.app.main" || true
sleep 2

# Start service
systemctl start aurity-backend
echo "✅ Service started"

# Check status
systemctl status aurity-backend --no-pager

echo ""
echo "🎉 Backend service setup complete!"
echo ""
echo "Useful commands:"
echo "  systemctl status aurity-backend   # Check status"
echo "  systemctl restart aurity-backend  # Restart"
echo "  journalctl -u aurity-backend -f   # View logs"
