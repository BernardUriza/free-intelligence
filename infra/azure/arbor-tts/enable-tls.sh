#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:?Set HOST to the VM public IP or DNS name}"
DOMAIN="${DOMAIN:?Set DOMAIN to the DNS name pointing at this VM}"
EMAIL="${EMAIL:?Set EMAIL for Lets Encrypt notices}"
ADMIN_USER="${ADMIN_USER:-azureuser}"

printf -v EMAIL_Q "%q" "$EMAIL"
printf -v DOMAIN_Q "%q" "$DOMAIN"
REMOTE_CMD="sudo certbot --nginx --non-interactive --agree-tos --redirect --email $EMAIL_Q -d $DOMAIN_Q && sudo systemctl reload nginx"
ssh "$ADMIN_USER@$HOST" "$REMOTE_CMD"

echo "TLS enabled: https://$DOMAIN/health"
