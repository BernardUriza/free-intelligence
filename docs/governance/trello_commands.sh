#!/bin/bash
#
# Trello Governance - Useful Shell Commands
#
# Card: FI-GOV-TOOL-001
# Usage: Source this file or copy-paste commands as needed
#
# Setup:
#   export TRELLO_KEY="your_api_key"
#   export TRELLO_TOKEN="your_token"
#   export TRELLO_BOARD_ID="68fbfeeb7f8614df2eb61e42"  # Free Intelligence board

# ============================================================================
# AUTHENTICATION
# ============================================================================

# Base auth string (reusable)
AUTH="key=$TRELLO_KEY&token=$TRELLO_TOKEN"

# Test authentication
test_auth() {
    curl -s "https://api.trello.com/1/members/me?$AUTH" | jq -r '.username'
}

# ============================================================================
# CARD INSPECTION
# ============================================================================

# Get card details (use shortLink)
get_card() {
    local CARD="$1"
    curl -s "https://api.trello.com/1/cards/$CARD?attachments=true&attachment_fields=url,name&fields=name,desc,labels,idChecklists&$AUTH" | jq .
}

# Get card with checklists expanded
get_card_full() {
    local CARD="$1"
    curl -s "https://api.trello.com/1/cards/$CARD?checklists=all&fields=name,desc,labels&$AUTH" | jq .
}

# Check if card has "Artifacts OK" label
check_artifacts_ok() {
    local CARD="$1"
    HAS_LABEL=$(curl -s "https://api.trello.com/1/cards/$CARD?fields=labels&$AUTH" | \
        jq -r '.labels[] | select(.name == "Artifacts OK") | .name' | grep -c "Artifacts OK" || true)

    if [ "$HAS_LABEL" -eq 1 ]; then
        echo "✅ Card has 'Artifacts OK' label"
        return 0
    else
        echo "❌ Card missing 'Artifacts OK' label"
        return 1
    fi
}

# ============================================================================
# LABEL MANAGEMENT
# ============================================================================

# Add "Artifacts OK" label (green)
add_artifacts_ok_label() {
    local CARD="$1"
    curl -s -X POST "https://api.trello.com/1/cards/$CARD/labels?color=green&name=Artifacts%20OK&$AUTH" > /dev/null
    echo "✅ Added 'Artifacts OK' label to card $CARD"
}

# Remove "Guard: Missing artifacts" label (red)
remove_guard_label() {
    local CARD="$1"
    LABEL_ID=$(curl -s "https://api.trello.com/1/cards/$CARD?fields=labels&$AUTH" | \
        jq -r '.labels[] | select(.name == "Guard: Missing artifacts") | .id')

    if [ -n "$LABEL_ID" ]; then
        curl -s -X DELETE "https://api.trello.com/1/cards/$CARD/idLabels/$LABEL_ID?$AUTH" > /dev/null
        echo "✅ Removed 'Guard: Missing artifacts' label"
    else
        echo "ℹ️  No guard label found"
    fi
}

# ============================================================================
# CHECKLIST OPERATIONS
# ============================================================================

# Get checklist completion status
check_checklist_complete() {
    local CARD="$1"
    local CHECKLIST_NAME="${2:-Artifacts}"

    CHECKLIST_DATA=$(curl -s "https://api.trello.com/1/cards/$CARD/checklists?$AUTH" | \
        jq --arg name "$CHECKLIST_NAME" '.[] | select(.name == $name)')

    if [ -z "$CHECKLIST_DATA" ]; then
        echo "❌ Checklist '$CHECKLIST_NAME' not found"
        return 1
    fi

    TOTAL=$(echo "$CHECKLIST_DATA" | jq '.checkItems | length')
    COMPLETE=$(echo "$CHECKLIST_DATA" | jq '[.checkItems[] | select(.state == "complete")] | length')

    echo "Checklist '$CHECKLIST_NAME': $COMPLETE/$TOTAL items complete"

    if [ "$COMPLETE" -eq "$TOTAL" ]; then
        echo "✅ Checklist is complete"
        return 0
    else
        echo "❌ Checklist incomplete"
        return 1
    fi
}

# ============================================================================
# ARTIFACT VALIDATION
# ============================================================================

# Validate artifacts (patterns) in card description + attachments
validate_artifacts() {
    local CARD="$1"

    CARD_DATA=$(curl -s "https://api.trello.com/1/cards/$CARD?attachments=true&attachment_fields=url&fields=desc&$AUTH")
    DESC=$(echo "$CARD_DATA" | jq -r '.desc // ""')
    ATTACHMENTS=$(echo "$CARD_DATA" | jq -r '.attachments[]?.url // ""')
    COMBINED="$DESC $ATTACHMENTS"

    echo "Validating artifacts for card: $CARD"
    echo ""

    # Demo URL
    if echo "$COMBINED" | grep -Eq 'https?://'; then
        echo "✅ Demo URL found"
    else
        echo "❌ Missing Demo URL"
    fi

    # Commit/Tag
    if echo "$COMBINED" | grep -Eq '[0-9a-f]{7,40}|v[0-9]+\.[0-9]+\.[0-9]+'; then
        echo "✅ Commit/Tag found"
    else
        echo "❌ Missing Commit/Tag"
    fi

    # Manifest (optional)
    if echo "$COMBINED" | grep -Eq 'manifest\.json'; then
        echo "✅ Manifest found (optional)"
    else
        echo "ℹ️  No manifest.json (optional)"
    fi
}

# ============================================================================
# BULK OPERATIONS
# ============================================================================

# Get all cards in "Done" list without "Artifacts OK" label
find_done_without_artifacts() {
    local LIST_ID="${1:-68fc0116622f29eecd78b7d4}"  # Default: Done list

    echo "Finding cards in Done without 'Artifacts OK' label..."
    echo ""

    curl -s "https://api.trello.com/1/lists/$LIST_ID/cards?fields=name,labels,shortLink&$AUTH" | \
        jq -r '.[] | select([.labels[].name] | index("Artifacts OK") | not) | "\(.shortLink) - \(.name)"'
}

# Audit all cards in Done list
audit_done_list() {
    local LIST_ID="${1:-68fc0116622f29eecd78b7d4}"

    CARDS=$(curl -s "https://api.trello.com/1/lists/$LIST_ID/cards?fields=shortLink,name&$AUTH" | jq -r '.[] | .shortLink')

    for CARD in $CARDS; do
        echo "=============================================="
        echo "Card: $CARD"
        echo "=============================================="
        check_artifacts_ok "$CARD" || true
        check_checklist_complete "$CARD" || true
        validate_artifacts "$CARD"
        echo ""
    done
}

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

: '
# Example 1: Check single card
get_card abc123XY

# Example 2: Validate artifacts
validate_artifacts abc123XY

# Example 3: Manually add "Artifacts OK" label
add_artifacts_ok_label abc123XY

# Example 4: Audit all Done cards
audit_done_list

# Example 5: Find cards missing artifacts
find_done_without_artifacts
'
