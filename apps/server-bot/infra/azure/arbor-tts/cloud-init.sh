#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates certbot curl git nginx python3-certbot-nginx rsync

curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

useradd --system --create-home --shell /bin/bash arbor || true
mkdir -p /opt/arbor-tts /var/log/arbor-tts
chown -R arbor:arbor /opt/arbor-tts /var/log/arbor-tts

systemctl enable nginx
systemctl restart nginx
