#!/bin/bash
# Quick deploy script for OG metadata testing
# Card: FI-UI-DESIGN-003

set -e

echo "🚀 Quick Deploy - OG Metadata Test"
echo "=================================="
echo ""

# Step 1: Verify banner exists
if [ ! -f "public/og-banner.png" ]; then
    echo "❌ Banner not found! Generating..."
    python3.14 scripts/generate_og_banner.py
else
    echo "✅ Banner found: public/og-banner.png"
fi

# Step 2: Build
echo ""
echo "📦 Building frontend..."
pnpm build

if [ $? -eq 0 ]; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi

# Step 3: Deploy
echo ""
echo "🚢 Deploying to production..."
python3 scripts/deploy-scp.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deploy complete!"
    echo ""
    echo "📊 Test your OG metadata:"
    echo "  1. WhatsApp: Send this link to yourself"
    echo "     https://app.aurity.io/chat"
    echo ""
    echo "  2. Facebook Debugger (refresh cache):"
    echo "     https://developers.facebook.com/tools/debug/"
    echo ""
    echo "  3. OpenGraph Validator:"
    echo "     https://www.opengraph.xyz/?url=https://app.aurity.io/chat"
    echo ""
else
    echo "❌ Deploy failed"
    exit 1
fi
