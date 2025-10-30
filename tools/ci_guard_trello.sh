#!/bin/bash
#
# CI Guard: Trello Artifacts Verification
#
# Validates that Trello card has required artifacts before allowing PR merge
#
# Card: FI-GOV-TOOL-001
# Philosophy: Done is auditable - without artifacts, Done doesn't exist
#
# Usage:
#   TRELLO_CARD=shortLink ./ci_guard_trello.sh
#
# Environment variables required:
#   TRELLO_KEY, TRELLO_TOKEN, TRELLO_CARD (from PR description)
#
# Exit codes:
#   0 - All artifacts verified
#   1 - Missing artifacts or validation failed

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() {
    echo -e "${RED}[GUARD FAIL]${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[GUARD PASS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[GUARD WARN]${NC} $1"
}

info() {
    echo "[GUARD INFO] $1"
}

# Validate environment
if [ -z "$TRELLO_KEY" ] || [ -z "$TRELLO_TOKEN" ]; then
    error "TRELLO_KEY and TRELLO_TOKEN must be set"
fi

if [ -z "$TRELLO_CARD" ]; then
    error "TRELLO_CARD must be set (use shortLink from PR description)"
fi

info "Validating Trello card: $TRELLO_CARD"

# Fetch card data
AUTH="key=$TRELLO_KEY&token=$TRELLO_TOKEN"
CARD_URL="https://api.trello.com/1/cards/$TRELLO_CARD"
CARD_DATA=$(curl -s "$CARD_URL?attachments=true&attachment_fields=url,name&fields=name,desc,labels,idChecklists&$AUTH")

if [ -z "$CARD_DATA" ] || echo "$CARD_DATA" | grep -q "invalid id"; then
    error "Failed to fetch card $TRELLO_CARD (invalid ID or API error)"
fi

CARD_NAME=$(echo "$CARD_DATA" | jq -r '.name // "Unknown"')
info "Card: $CARD_NAME"

# Check for "Artifacts OK" label
HAS_ARTIFACTS_OK=$(echo "$CARD_DATA" | jq -r '.labels[] | select(.name == "Artifacts OK") | .name' | grep -c "Artifacts OK" || true)

if [ "$HAS_ARTIFACTS_OK" -eq 0 ]; then
    warning "Missing 'Artifacts OK' label - checking artifacts manually..."
fi

# Extract description and attachments
DESC=$(echo "$CARD_DATA" | jq -r '.desc // ""')
ATTACHMENTS=$(echo "$CARD_DATA" | jq -r '.attachments[]?.url // ""')
CHECKLIST_IDS=$(echo "$CARD_DATA" | jq -r '.idChecklists[]? // ""')

# Combine text for pattern matching
COMBINED_TEXT="$DESC $ATTACHMENTS"

# Fetch checklist items
CHECKLIST_TEXT=""
for CHECKLIST_ID in $CHECKLIST_IDS; do
    CHECKLIST_DATA=$(curl -s "https://api.trello.com/1/checklists/$CHECKLIST_ID?$AUTH")
    CHECKLIST_NAME=$(echo "$CHECKLIST_DATA" | jq -r '.name // ""')

    if echo "$CHECKLIST_NAME" | grep -qi "artifacts"; then
        info "Found 'Artifacts' checklist"

        # Check if all items are complete
        TOTAL_ITEMS=$(echo "$CHECKLIST_DATA" | jq '.checkItems | length')
        COMPLETE_ITEMS=$(echo "$CHECKLIST_DATA" | jq '[.checkItems[] | select(.state == "complete")] | length')

        info "Checklist items: $COMPLETE_ITEMS/$TOTAL_ITEMS complete"

        if [ "$COMPLETE_ITEMS" -ne "$TOTAL_ITEMS" ]; then
            error "Artifacts checklist incomplete ($COMPLETE_ITEMS/$TOTAL_ITEMS). Cannot merge."
        fi

        # Extract checklist text for pattern matching
        CHECKLIST_TEXT=$(echo "$CHECKLIST_DATA" | jq -r '.checkItems[].name' | tr '\n' ' ')
        COMBINED_TEXT="$COMBINED_TEXT $CHECKLIST_TEXT"
    fi
done

info "Validating artifact patterns..."

# Validation patterns
DEMO_PATTERN='https?://'
COMMIT_PATTERN='[0-9a-f]{7,40}'
TAG_PATTERN='v[0-9]+\.[0-9]+\.[0-9]+'
MANIFEST_PATTERN='manifest\.json'

# Track validation results
MISSING_ARTIFACTS=()

# Check for Demo URL
if ! echo "$COMBINED_TEXT" | grep -Eq "$DEMO_PATTERN"; then
    MISSING_ARTIFACTS+=("Demo URL (http://...)")
fi

# Check for Commit or Tag
if ! echo "$COMBINED_TEXT" | grep -Eq "$COMMIT_PATTERN" && ! echo "$COMBINED_TEXT" | grep -Eq "$TAG_PATTERN"; then
    MISSING_ARTIFACTS+=("Commit SHA or Tag (abc1234 or v1.2.3)")
fi

# Check for Manifest
if ! echo "$COMBINED_TEXT" | grep -Eq "$MANIFEST_PATTERN"; then
    warning "No manifest.json found (optional for some cards)"
fi

# Report results
if [ ${#MISSING_ARTIFACTS[@]} -gt 0 ]; then
    error "Missing required artifacts:\n  - ${MISSING_ARTIFACTS[*]}"
fi

success "All required artifacts verified ✅"
info "  ✓ Demo URL found"
info "  ✓ Commit/Tag found"

# Post success comment to Trello
COMMENT_TEXT="CI Guard: Artifacts verified ✅\n\nValidation passed:\n- Demo URL: present\n- Commit/Tag: present\n- Checklist: complete\n\nMerge approved by governance guard."

curl -s -X POST "https://api.trello.com/1/cards/$TRELLO_CARD/actions/comments?text=$(echo -e "$COMMENT_TEXT" | jq -sRr @uri)&$AUTH" > /dev/null

success "Comment posted to Trello card"

exit 0
