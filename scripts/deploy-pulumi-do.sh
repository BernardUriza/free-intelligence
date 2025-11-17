#!/bin/bash
#
# 🎯 Pulumi + DigitalOcean = CDK para todos!
# Deploy with code, not YAML!
#

set -e

echo "╔════════════════════════════════════════════╗"
echo "║     Pulumi + DO - Infrastructure as Code    ║"
echo "║         (Like CDK but BETTER!)              ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check Pulumi
if ! command -v pulumi &> /dev/null; then
    echo "📦 Installing Pulumi..."
    brew install pulumi
fi

echo -e "${GREEN}✓${NC} Pulumi version: $(pulumi version)"

# Get DO token
if [ -z "$DIGITALOCEAN_TOKEN" ]; then
    echo ""
    echo "🔑 You need a DigitalOcean API token"
    echo "   Get it from: https://cloud.digitalocean.com/account/api/tokens"
    echo ""
    read -sp "Enter your DO token: " DO_TOKEN
    echo ""
else
    DO_TOKEN=$DIGITALOCEAN_TOKEN
fi

# Navigate to Pulumi directory
cd pulumi-do/

# Setup Python environment
echo ""
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt

# Initialize Pulumi stack
echo ""
echo "📚 Initializing Pulumi stack..."
if [ ! -f "Pulumi.dev.yaml" ]; then
    pulumi stack init dev
fi

# Set configuration
echo ""
echo "⚙️  Configuring stack..."
pulumi config set digitalocean:token $DO_TOKEN --secret
pulumi config set region nyc3
pulumi config set environment dev

# Ask deployment type
echo ""
echo "🚀 Choose deployment type:"
echo "   1) App Platform (Serverless, $5-10/month) - RECOMMENDED"
echo "   2) Droplet (VPS, $6/month)"
read -p "Select [1-2]: " DEPLOY_TYPE

if [ "$DEPLOY_TYPE" = "2" ]; then
    pulumi config set use_droplet true
else
    pulumi config set use_droplet false
fi

# Preview changes
echo ""
echo "👀 Preview of resources to create:"
pulumi preview

# Deploy
echo ""
read -p "🚀 Ready to deploy? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔨 Deploying infrastructure..."
    pulumi up -y

    # Show outputs
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║         ✅ DEPLOYMENT SUCCESSFUL!          ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""

    APP_URL=$(pulumi stack output app_url 2>/dev/null || echo "N/A")
    DROPLET_IP=$(pulumi stack output droplet_ip 2>/dev/null || echo "N/A")
    BUCKET=$(pulumi stack output spaces_bucket 2>/dev/null || echo "N/A")

    if [ "$APP_URL" != "N/A" ]; then
        echo -e "🌐 App URL: ${GREEN}$APP_URL${NC}"
    fi

    if [ "$DROPLET_IP" != "N/A" ]; then
        echo -e "🖥️  Droplet IP: ${GREEN}$DROPLET_IP${NC}"
        echo -e "   SSH: ${YELLOW}ssh root@$DROPLET_IP${NC}"
    fi

    echo -e "📦 Spaces Bucket: ${GREEN}$BUCKET${NC}"
    echo ""
    echo "📊 Management commands:"
    echo "   View stack:     pulumi stack"
    echo "   See outputs:    pulumi stack output"
    echo "   View logs:      pulumi logs"
    echo "   Destroy:        pulumi destroy"
    echo ""
    echo -e "${BLUE}💡 Tip: Pulumi saves state locally by default.${NC}"
    echo -e "${BLUE}   For teams, use: pulumi login${NC}"
else
    echo "Deployment cancelled"
fi

# Deactivate venv
deactivate 2>/dev/null || true
