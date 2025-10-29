#!/bin/bash
# Validate Trello Kanban Workflow
# Prevents moving cards to Testing when In Progress would become empty
#
# Usage:
#   ./scripts/validate_trello_workflow.sh <card_id> <target_list>
#
# Exit codes:
#   0 - Validation passed
#   1 - Validation failed (workflow violation)

set -e

CARD_ID="$1"
TARGET_LIST="$2"

# Trello List IDs (Free Intelligence board)
SPRINT_LIST="68fc011510584fb24b9ef5a6"      # To Do (Sprint)
IN_PROGRESS_LIST="68fc0116e8a27f8caaec894d" # In Progress
TESTING_LIST="68fc0116783741e5e925a633"     # Testing
DONE_LIST="68fc0116622f29eecd78b7d4"        # Done

# Trello CLI path
TRELLO_CLI="$HOME/Documents/trello-cli-python/trello"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 VALIDATING TRELLO WORKFLOW..."
echo ""

# Check if moving to Testing or Done
if [ "$TARGET_LIST" != "$TESTING_LIST" ] && [ "$TARGET_LIST" != "$DONE_LIST" ]; then
    echo "${GREEN}✅ Not moving to Testing/Done - validation skipped${NC}"
    exit 0
fi

echo "⚠️  Detected move to Testing/Done - validating workflow..."
echo ""

# Count cards in In Progress (excluding current card)
echo "📊 Checking In Progress list..."
IN_PROGRESS_COUNT=$($TRELLO_CLI cards "$IN_PROGRESS_LIST" 2>/dev/null | grep -c "^[a-f0-9]\{24\}" || echo "0")
echo "   Current count: $IN_PROGRESS_COUNT card(s)"

# If moving current card out, In Progress will have IN_PROGRESS_COUNT-1 cards
REMAINING_IN_PROGRESS=$((IN_PROGRESS_COUNT - 1))
echo "   After move: $REMAINING_IN_PROGRESS card(s)"
echo ""

# If In Progress will be empty, check Sprint
if [ "$REMAINING_IN_PROGRESS" -eq 0 ]; then
    echo "${YELLOW}⚠️  WARNING: In Progress will become empty!${NC}"
    echo "📊 Checking To Do (Sprint) list..."

    SPRINT_COUNT=$($TRELLO_CLI cards "$SPRINT_LIST" 2>/dev/null | grep -c "^[a-f0-9]\{24\}" || echo "0")
    echo "   Available cards in Sprint: $SPRINT_COUNT"
    echo ""

    if [ "$SPRINT_COUNT" -eq 0 ]; then
        echo "${RED}❌ WORKFLOW VIOLATION DETECTED!${NC}"
        echo ""
        echo "Cannot move card to Testing/Done:"
        echo "  • In Progress will become empty (0 cards)"
        echo "  • To Do (Sprint) has no cards to move (0 cards)"
        echo ""
        echo "Required action:"
        echo "  1. Add cards to 'To Do (Sprint)' first, OR"
        echo "  2. Ask user which card to work on next"
        echo ""
        exit 1
    else
        echo "${YELLOW}⚠️  REMINDER: Move next card from Sprint to In Progress!${NC}"
        echo ""
        echo "Available cards in Sprint:"
        $TRELLO_CLI cards "$SPRINT_LIST" 2>/dev/null | grep "^[a-f0-9]\{24\}" | head -3
        echo ""
        echo "Suggested workflow:"
        echo "  1. Move one of the above cards to In Progress"
        echo "  2. THEN move current card to Testing/Done"
        echo ""
    fi
fi

echo "${GREEN}✅ Workflow validation passed${NC}"
exit 0
