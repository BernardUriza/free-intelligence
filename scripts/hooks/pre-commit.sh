#!/bin/bash
# Pre-commit hook: Validate version consistency before commit

echo "🔍 Validating version consistency..."

if ! node scripts/sync-versions.js --check >/dev/null 2>&1; then
  echo ""
  echo "❌ Version mismatch detected!"
  node scripts/sync-versions.js --check
  echo ""
  echo "💡 Fix with: pnpm version:sync"
  exit 1
fi

echo "✅ Version check passed"
exit 0
