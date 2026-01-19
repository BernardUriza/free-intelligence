#!/bin/bash
#
# cleanup-azure-blob.sh
# Delete old release artifacts from Azure Blob Storage
#
# This script is OPTIONAL - only run if you want to fully migrate to GitHub Releases.
# Azure Blob URLs in apps/aurity/app/downloads/page.tsx will be replaced with GitHub API.
#
# Prerequisites:
#   - Azure CLI installed: brew install azure-cli
#   - Logged in: az login
#   - Storage account: aurityreleases
#   - Container: releases
#
# Usage:
#   ./scripts/cleanup-azure-blob.sh            # Dry-run (list files)
#   ./scripts/cleanup-azure-blob.sh --delete   # Actually delete
#

set -e

ACCOUNT_NAME="aurityreleases"
CONTAINER_NAME="releases"
DELETE=false

if [[ "$1" == "--delete" ]]; then
  DELETE=true
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Azure Blob Storage Cleanup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Account: $ACCOUNT_NAME"
echo "Container: $CONTAINER_NAME"
echo "Mode: $([ "$DELETE" = true ] && echo "DELETE" || echo "DRY-RUN")"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Azure CLI
if ! command -v az &> /dev/null; then
  echo "❌ Azure CLI not found. Install with: brew install azure-cli"
  exit 1
fi

# Check login status
if ! az account show &> /dev/null; then
  echo "❌ Not logged into Azure. Run: az login"
  exit 1
fi

echo "📦 Listing blobs in $CONTAINER_NAME..."
echo ""

# List all blobs
BLOBS=$(az storage blob list \
  --account-name "$ACCOUNT_NAME" \
  --container-name "$CONTAINER_NAME" \
  --auth-mode login \
  --output json)

if [ -z "$BLOBS" ] || [ "$BLOBS" = "[]" ]; then
  echo "✅ No blobs found in container"
  exit 0
fi

# Display blobs
echo "$BLOBS" | jq -r '.[] | "\(.name) - \((.properties.contentLength / 1024 / 1024) | floor)MB - \(.properties.lastModified)"'

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

BLOB_COUNT=$(echo "$BLOBS" | jq 'length')
echo "Total blobs: $BLOB_COUNT"

if [ "$DELETE" = false ]; then
  echo ""
  echo "⚠️  This is a DRY-RUN. No files will be deleted."
  echo ""
  echo "To actually delete these files, run:"
  echo "  ./scripts/cleanup-azure-blob.sh --delete"
  exit 0
fi

echo ""
read -p "❌ Are you sure you want to DELETE all $BLOB_COUNT blobs? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "❌ Cancelled"
  exit 0
fi

echo ""
echo "🗑️  Deleting blobs..."

echo "$BLOBS" | jq -r '.[].name' | while read -r BLOB_NAME; do
  echo "  - Deleting: $BLOB_NAME"
  az storage blob delete \
    --account-name "$ACCOUNT_NAME" \
    --container-name "$CONTAINER_NAME" \
    --name "$BLOB_NAME" \
    --auth-mode login \
    --output none
done

echo ""
echo "✅ All blobs deleted successfully"
echo ""
echo "🔄 Next steps:"
echo "  1. Replace apps/aurity/app/downloads/page.tsx with page-dynamic.tsx"
echo "  2. Test /downloads page with: pnpm dev"
echo "  3. Commit changes"
