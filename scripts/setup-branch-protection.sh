#!/bin/bash
# Setup branch protection for main after GitHub Pro upgrade
# Run this script after upgrading to GitHub Pro

set -e

REPO="BernardUriza/free-intelligence"
BRANCH="main"

echo "🔒 Setting up branch protection for $REPO ($BRANCH)..."

gh api repos/$REPO/branches/$BRANCH/protection \
  -X PUT \
  --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["PR Gate Status"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

echo ""
echo "✅ Branch protection configured!"
echo ""
echo "Rules applied:"
echo "  - PR Gate Status must pass before merge"
echo "  - Force pushes blocked"
echo "  - Branch deletion blocked"
echo ""
echo "To require PR reviews, add this later:"
echo '  "required_pull_request_reviews": {"required_approving_review_count": 1}'
