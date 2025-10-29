#!/usr/bin/env python3
"""
Free Intelligence - Trello Workflow Validator (Python)

Validación de workflow Kanban para prevenir violaciones de reglas.

Usage:
    python3 scripts/trello_workflow.py validate <card_id> <target_list>
    python3 scripts/trello_workflow.py move <card_id> <target_list>
    python3 scripts/trello_workflow.py status

Exit codes:
    0 - Validation passed / Move successful
    1 - Validation failed / Move failed
"""

import sys
import subprocess
from pathlib import Path
from typing import Tuple, List


# Trello List IDs (Free Intelligence board)
LISTS = {
    "to_prioritize": "68fc0114043ad4a639ec8fce",
    "sprint": "68fc011510584fb24b9ef5a6",
    "in_progress": "68fc0116e8a27f8caaec894d",
    "testing": "68fc0116783741e5e925a633",
    "done": "68fc0116622f29eecd78b7d4"
}

TRELLO_CLI = str(Path.home() / "Documents/trello-cli-python/trello")


def run_trello_command(args: List[str]) -> Tuple[int, str]:
    """Run trello CLI command."""
    cmd = [TRELLO_CLI] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout


def count_cards(list_id: str) -> int:
    """Count cards in a list."""
    returncode, output = run_trello_command(["cards", list_id])
    if returncode != 0:
        return 0

    # Count lines that start with 24-char hex (card IDs)
    count = sum(1 for line in output.split('\n') if len(line) >= 24 and all(c in '0123456789abcdef' for c in line[:24]))
    return count


def validate_workflow(card_id: str, target_list: str) -> Tuple[bool, str]:
    """
    Validate workflow before moving card.

    Returns:
        (is_valid, message)
    """
    # Only validate moves to Testing or Done
    if target_list not in [LISTS["testing"], LISTS["done"]]:
        return True, "✅ Not moving to Testing/Done - validation skipped"

    print("🔍 VALIDATING WORKFLOW...")
    print()

    # Count cards in In Progress
    in_progress_count = count_cards(LISTS["in_progress"])
    print(f"📊 In Progress: {in_progress_count} card(s)")

    # After move, In Progress will have in_progress_count-1 cards
    remaining_in_progress = in_progress_count - 1
    print(f"   After move: {remaining_in_progress} card(s)")
    print()

    # If In Progress will be empty, check Sprint
    if remaining_in_progress <= 0:
        print("⚠️  WARNING: In Progress will become empty!")
        print()

        # Check Sprint
        sprint_count = count_cards(LISTS["sprint"])
        print(f"📊 To Do (Sprint): {sprint_count} card(s)")
        print()

        if sprint_count == 0:
            # Check To Prioritize as fallback
            to_prioritize_count = count_cards(LISTS["to_prioritize"])
            print(f"📊 To Prioritize: {to_prioritize_count} card(s)")
            print()

            if to_prioritize_count == 0:
                return False, "❌ VIOLATION: No cards available to move to In Progress!"

            return False, "⚠️  WARNING: Sprint empty but To Prioritize has cards. Move manually first!"

        return False, f"⚠️  REMINDER: Move next card from Sprint to In Progress first! ({sprint_count} available)"

    return True, "✅ Workflow validation passed"


def move_card_safe(card_id: str, target_list: str) -> Tuple[bool, str]:
    """
    Move card with workflow validation.

    Returns:
        (success, message)
    """
    # Validate first
    is_valid, message = validate_workflow(card_id, target_list)
    print(message)
    print()

    if not is_valid:
        return False, "Move cancelled due to workflow violation"

    # If moving to Testing/Done and Sprint has cards, prompt to move one first
    if target_list in [LISTS["testing"], LISTS["done"]]:
        in_progress_count = count_cards(LISTS["in_progress"])
        if in_progress_count <= 1:  # Only current card
            sprint_count = count_cards(LISTS["sprint"])
            if sprint_count > 0:
                print("📋 Suggested workflow:")
                print("   1. Run: python3 scripts/trello_workflow.py move-next-to-progress")
                print("   2. Then retry this move")
                print()
                return False, "Move cancelled - move next card to In Progress first"

    # Perform move
    print(f"🔄 Moving card {card_id[:8]}... to list {target_list[:8]}...")
    returncode, output = run_trello_command(["move-card", card_id, target_list])

    if returncode == 0:
        return True, f"✅ Card moved successfully\n{output}"
    else:
        return False, f"❌ Move failed:\n{output}"


def move_next_to_progress() -> Tuple[bool, str]:
    """Move next card from Sprint to In Progress."""
    # Get first card from Sprint
    returncode, output = run_trello_command(["cards", LISTS["sprint"]])

    if returncode != 0:
        return False, "❌ Failed to get Sprint cards"

    # Find first card ID
    for line in output.split('\n'):
        if len(line) >= 24 and all(c in '0123456789abcdef' for c in line[:24]):
            card_id = line[:24]
            card_name = line[26:].strip()

            print(f"📋 Moving card to In Progress:")
            print(f"   {card_name}")
            print()

            # Move to In Progress
            returncode, move_output = run_trello_command(["move-card", card_id, LISTS["in_progress"]])

            if returncode == 0:
                # Add start comment
                run_trello_command([
                    "add-comment",
                    card_id,
                    f"🚀 Started {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"
                ])
                return True, f"✅ Moved to In Progress:\n{move_output}"
            else:
                return False, f"❌ Move failed:\n{move_output}"

    return False, "❌ No cards found in Sprint"


def show_status():
    """Show current workflow status."""
    print("📊 TRELLO WORKFLOW STATUS")
    print("=" * 60)
    print()

    for name, list_id in LISTS.items():
        count = count_cards(list_id)
        status = "✅" if count > 0 or name not in ["in_progress"] else "⚠️"
        if name == "in_progress" and count == 0:
            status = "❌"

        print(f"{status} {name.replace('_', ' ').title()}: {count} card(s)")

    print()

    # Check for violations
    in_progress_count = count_cards(LISTS["in_progress"])
    if in_progress_count == 0:
        print("❌ VIOLATION: In Progress is empty!")
        sprint_count = count_cards(LISTS["sprint"])
        if sprint_count > 0:
            print(f"   → Run: python3 scripts/trello_workflow.py move-next-to-progress")
        else:
            print(f"   → Add cards to Sprint first")
    else:
        print("✅ Workflow is healthy")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/trello_workflow.py status")
        print("  python3 scripts/trello_workflow.py validate <card_id> <target_list>")
        print("  python3 scripts/trello_workflow.py move <card_id> <target_list>")
        print("  python3 scripts/trello_workflow.py move-next-to-progress")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        show_status()

    elif command == "validate":
        if len(sys.argv) < 4:
            print("Usage: python3 scripts/trello_workflow.py validate <card_id> <target_list>")
            sys.exit(1)

        card_id = sys.argv[2]
        target_list = sys.argv[3]

        is_valid, message = validate_workflow(card_id, target_list)
        print(message)
        sys.exit(0 if is_valid else 1)

    elif command == "move":
        if len(sys.argv) < 4:
            print("Usage: python3 scripts/trello_workflow.py move <card_id> <target_list>")
            sys.exit(1)

        card_id = sys.argv[2]
        target_list = sys.argv[3]

        success, message = move_card_safe(card_id, target_list)
        print(message)
        sys.exit(0 if success else 1)

    elif command == "move-next-to-progress":
        success, message = move_next_to_progress()
        print(message)
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
