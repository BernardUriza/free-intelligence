#!/bin/bash
#
# 🎨 Frontend Deploy to DigitalOcean - Ultra Simple!
# Deploys Aurity frontend to Spaces + CDN
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║   🎨 Aurity Frontend → DigitalOcean 🌊    ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 not found${NC}"
        echo "   Install: $2"
        exit 1
    fi
}

echo "📋 Checking prerequisites..."
check_command "doctl" "brew install doctl"
check_command "pnpm" "npm install -g pnpm"

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

# Authenticate
echo ""
echo "🔐 Authenticating..."
doctl auth init -t $DIGITALOCEAN_TOKEN

# Configuration
SPACE_NAME="fi-aurity-frontend"
REGION="nyc3"
PROJECT_DIR="apps/aurity"
BUILD_DIR="$PROJECT_DIR/out"

# Step 1: Build frontend
echo ""
echo -e "${BLUE}📦 Step 1: Building frontend...${NC}"
cd $PROJECT_DIR

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    pnpm install
fi

# Build
echo "   Building production bundle..."
pnpm build

# Export static files
echo "   Exporting static files..."
pnpm export || {
    echo -e "${YELLOW}   ℹ️  Static export not configured, using .next/static${NC}"
    # If export fails, we'll use the .next directory
    BUILD_DIR=".next"
}

cd ../..

# Step 2: Create or update Space
echo ""
echo -e "${BLUE}📤 Step 2: Creating/Updating Space...${NC}"

# Check if space exists
if doctl spaces list | grep -q "$SPACE_NAME"; then
    echo "   ✓ Space '$SPACE_NAME' exists"
else
    echo "   Creating Space '$SPACE_NAME'..."
    doctl spaces create $SPACE_NAME --region $REGION
    sleep 5  # Wait for space to be ready
fi

# Step 3: Upload files
echo ""
echo -e "${BLUE}🚀 Step 3: Uploading files to Space...${NC}"

# Upload files with public-read ACL
echo "   Uploading static files..."
doctl spaces upload $SPACE_NAME \
    $BUILD_DIR/* \
    --region $REGION \
    --recursive \
    --acl public-read

# Step 4: Enable CDN
echo ""
echo -e "${BLUE}⚡ Step 4: Enabling CDN...${NC}"

# Check if CDN is already enabled
CDN_STATUS=$(doctl spaces cdn list $SPACE_NAME --region $REGION 2>&1 || echo "not_enabled")

if echo "$CDN_STATUS" | grep -q "not_enabled\|No CDN"; then
    echo "   Enabling CDN..."
    doctl spaces cdn enable $SPACE_NAME --region $REGION
    echo "   ✓ CDN enabled! (May take 5-10 minutes to propagate)"
else
    echo "   ✓ CDN already enabled"
fi

# Get URLs
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║         ✅ DEPLOYMENT SUCCESSFUL!          ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}🌐 Your frontend is live!${NC}"
echo ""
echo "URLs:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}📦 Direct URL (no CDN):${NC}"
echo "   https://$SPACE_NAME.$REGION.digitaloceanspaces.com"
echo ""
echo -e "${GREEN}⚡ CDN URL (RECOMMENDED - faster):${NC}"
echo "   https://$SPACE_NAME.$REGION.cdn.digitaloceanspaces.com"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Next Steps:"
echo "   1. Test your app: open https://$SPACE_NAME.$REGION.cdn.digitaloceanspaces.com"
echo "   2. Update backend CORS: Add CDN URL to ALLOWED_ORIGINS"
echo "   3. Configure custom domain (optional):"
echo "      CNAME: app.yourdomain.com → $SPACE_NAME.$REGION.cdn.digitaloceanspaces.com"
echo ""
echo "💡 To redeploy: Just run this script again!"
echo ""
echo "💰 Cost: \$5/month (250GB storage + CDN)"
echo ""

# Save deployment info
cat > deployment-info.txt << EOF
Deployment Date: $(date)
Space Name: $SPACE_NAME
Region: $REGION
Direct URL: https://$SPACE_NAME.$REGION.digitaloceanspaces.com
CDN URL: https://$SPACE_NAME.$REGION.cdn.digitaloceanspaces.com

Next Deploy:
./scripts/deploy-frontend-do.sh
EOF

echo "📄 Deployment info saved to: deployment-info.txt"
echo ""
