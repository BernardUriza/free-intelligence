#!/bin/bash
#
# 🌊 DigitalOcean Deployment Script
# Simple, fast, and works with PayPal!
#

set -e

echo "╔════════════════════════════════════════════╗"
echo "║    DigitalOcean Deployment - Free Intel    ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 not found${NC}"
        echo "   Install: $2"
        exit 1
    else
        echo -e "${GREEN}✓${NC} $1 found"
    fi
}

echo "📋 Checking prerequisites..."
check_command "doctl" "brew install doctl"
check_command "terraform" "brew install terraform"
check_command "docker" "Download from docker.com"

# Check for DO token
if [ -z "$DIGITALOCEAN_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  DIGITALOCEAN_TOKEN not set${NC}"
    echo ""
    echo "Get your token from:"
    echo "https://cloud.digitalocean.com/account/api/tokens"
    echo ""
    read -p "Enter your DigitalOcean API token: " DO_TOKEN
    export DIGITALOCEAN_TOKEN=$DO_TOKEN
fi

# Authenticate doctl
echo ""
echo "🔐 Authenticating with DigitalOcean..."
doctl auth init -t $DIGITALOCEAN_TOKEN

# Verify authentication
if doctl account get &> /dev/null; then
    EMAIL=$(doctl account get --format Email --no-header)
    echo -e "${GREEN}✓${NC} Authenticated as: $EMAIL"
else
    echo -e "${RED}❌ Authentication failed${NC}"
    exit 1
fi

# Choose deployment method
echo ""
echo "🚀 Choose deployment method:"
echo "   1) App Platform (Serverless, $5/month)"
echo "   2) Droplet (Traditional VPS, $6/month)"
echo "   3) Kubernetes (Advanced, $12/month)"
read -p "Select [1-3]: " DEPLOY_METHOD

case $DEPLOY_METHOD in
    1)
        echo ""
        echo "📦 Deploying to App Platform..."

        # Create app spec
        cat > app.yaml << 'EOF'
name: free-intelligence
region: nyc
services:
- name: backend
  github:
    repo: yourusername/free-intelligence
    branch: main
    deploy_on_push: true
  dockerfile_path: Dockerfile.do
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 7001
  health_check:
    http_path: /api/health
  envs:
  - key: NODE_ENV
    value: production
  - key: PORT
    value: "7001"
EOF

        # Deploy
        doctl apps create --spec app.yaml

        # Get app ID
        APP_ID=$(doctl apps list --format ID --no-header | head -1)

        echo -e "${GREEN}✅ App deployed!${NC}"
        echo "URL: $(doctl apps get $APP_ID --format LiveURL --no-header)"
        ;;

    2)
        echo ""
        echo "🖥️  Creating Droplet..."

        # Create droplet
        doctl compute droplet create fi-backend \
            --region nyc3 \
            --size s-1vcpu-1gb \
            --image docker-20-04 \
            --ssh-keys $(doctl compute ssh-key list --format ID --no-header) \
            --user-data-file cloud-init.yaml \
            --wait

        # Get IP
        IP=$(doctl compute droplet get fi-backend --format PublicIPv4 --no-header)

        echo -e "${GREEN}✅ Droplet created!${NC}"
        echo "IP: $IP"
        echo "SSH: ssh root@$IP"

        # Wait for Docker to be ready
        echo "⏳ Waiting for Docker setup (60s)..."
        sleep 60

        # Deploy container
        ssh root@$IP << 'ENDSSH'
            docker run -d \
                --name fi-backend \
                --restart unless-stopped \
                -p 7001:7001 \
                -e PORT=7001 \
                ghcr.io/yourusername/free-intelligence:latest
ENDSSH

        echo "Backend URL: http://$IP:7001"
        ;;

    3)
        echo ""
        echo "☸️  Creating Kubernetes cluster..."

        doctl kubernetes cluster create fi-cluster \
            --region nyc3 \
            --size s-1vcpu-2gb \
            --count 2 \
            --wait

        echo -e "${GREEN}✅ Kubernetes cluster created!${NC}"
        echo "Configure kubectl: doctl kubernetes cluster kubeconfig save fi-cluster"
        ;;

    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║         ✅ DEPLOYMENT SUCCESSFUL!          ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "📊 Next steps:"
echo "   1. View apps:     doctl apps list"
echo "   2. View logs:     doctl apps logs $APP_ID"
echo "   3. View metrics:  doctl apps metrics get $APP_ID"
echo "   4. Destroy:       doctl apps delete $APP_ID"
echo ""
echo "💰 Costs:"
echo "   App Platform:  $5/month"
echo "   Database:      $15/month"
echo "   Spaces:        $5/month"
echo "   Total:         ~$25/month"
echo ""
echo "📚 Docs: https://docs.digitalocean.com"
