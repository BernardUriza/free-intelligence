#!/bin/bash
# Free Intelligence - Setup SSL for app.aurity.io
# Author: Bernard Uriza Orozco
# Created: 2025-11-20

set -e

DOMAIN="app.aurity.io"
DROPLET_IP="104.131.175.65"

echo "🔐 Setting up SSL certificate for $DOMAIN"
echo ""

# Check DNS first
echo "🔍 Verifying DNS resolution..."
RESOLVED_IP=$(dig +short $DOMAIN | tail -1)
if [ "$RESOLVED_IP" != "$DROPLET_IP" ]; then
    echo "⚠️  WARNING: DNS not pointing to droplet!"
    echo "   Expected: $DROPLET_IP"
    echo "   Got:      $RESOLVED_IP"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ DNS correctly points to $DROPLET_IP"
fi

echo ""
echo "📝 This script will:"
echo "   1. Install certbot if needed"
echo "   2. Stop nginx temporarily"
echo "   3. Obtain SSL certificate for $DOMAIN"
echo "   4. Configure nginx to use new certificate"
echo "   5. Setup auto-renewal"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo ""
echo "🚀 Connecting to droplet..."

ssh root@$DROPLET_IP << 'ENDSSH'
set -e

DOMAIN="app.aurity.io"
EMAIL="bernarduriza@gmail.com"

echo ""
echo "📦 Installing certbot..."
apt-get update
apt-get install -y certbot python3-certbot-nginx

echo ""
echo "🛑 Stopping nginx temporarily..."
systemctl stop nginx

echo ""
echo "🎫 Obtaining SSL certificate..."
certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    -d $DOMAIN

echo ""
echo "📝 Creating nginx config for $DOMAIN..."
cat > /etc/nginx/sites-available/aurity << 'EOF'
# HTTP (redirect to HTTPS)
server {
    listen 80;
    server_name app.aurity.io;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name app.aurity.io;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/app.aurity.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.aurity.io/privkey.pem;

    # SSL Security (HIPAA compliant)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Frontend (Next.js static export)
    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    # API Backend (FastAPI)
    location /api/ {
        proxy_pass http://localhost:7001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts for long-running requests (audio upload)
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Frontend routing (SPA fallback)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

echo ""
echo "🔗 Enabling site..."
ln -sf /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/aurity

# Remove old DuckDNS config if exists
if [ -f /etc/nginx/sites-enabled/aurity-duckdns ]; then
    echo "🗑️  Removing old DuckDNS config..."
    rm /etc/nginx/sites-enabled/aurity-duckdns
fi

echo ""
echo "✅ Testing nginx config..."
nginx -t

echo ""
echo "🚀 Starting nginx..."
systemctl start nginx
systemctl enable nginx

echo ""
echo "🔄 Setting up auto-renewal..."
certbot renew --dry-run

echo ""
echo "✅ SSL setup complete!"
echo ""
echo "📋 Certificate details:"
certbot certificates

echo ""
echo "🧪 Test your site:"
echo "   curl -I https://$DOMAIN"
echo "   curl https://$DOMAIN/api/health"
ENDSSH

echo ""
echo "✅ Done! Your site is now available at https://$DOMAIN"
echo ""
echo "📝 Next steps:"
echo "   1. Test frontend: https://app.aurity.io"
echo "   2. Test backend:  https://app.aurity.io/api/health"
echo "   3. Push changes to trigger GitHub Actions deployment"
echo ""
