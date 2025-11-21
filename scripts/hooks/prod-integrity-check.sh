#!/bin/bash
# =============================================================================
# AURITY Production Integrity Monitor
# =============================================================================
# Runs via cron every 5 minutes on production server.
# Detects unauthorized file modifications and alerts.
#
# Install: crontab -e
# */5 * * * * /opt/free-intelligence/scripts/hooks/prod-integrity-check.sh
# =============================================================================

set -euo pipefail

PROD_DIR="/opt/free-intelligence"
LOG_FILE="/var/log/aurity-integrity.log"
ALERT_FILE="/tmp/aurity-dirty-prod-alert"
SLACK_WEBHOOK="${AURITY_SLACK_WEBHOOK:-}"

log() {
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") $1" >> "$LOG_FILE"
}

alert() {
    local message="$1"
    log "ALERT: $message"

    # Create alert file for other processes to detect
    echo "$message" > "$ALERT_FILE"

    # Send Slack alert if webhook configured
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\":\"🚨 AURITY PROD INTEGRITY ALERT\\n$message\"}" \
            > /dev/null 2>&1 || true
    fi

    # Also send to stderr for cron email
    echo "🚨 AURITY INTEGRITY ALERT: $message" >&2
}

# Check 1: Git status (uncommitted changes)
check_git_status() {
    cd "$PROD_DIR"

    if ! git diff --quiet 2>/dev/null; then
        local changed_files=$(git diff --name-only 2>/dev/null | head -10)
        alert "DIRTY_GIT: Modified files detected on production!\n$changed_files"
        return 1
    fi

    if ! git diff --cached --quiet 2>/dev/null; then
        alert "DIRTY_GIT: Staged changes detected on production!"
        return 1
    fi

    # Check for untracked files in critical directories
    local untracked=$(git ls-files --others --exclude-standard backend/ apps/ 2>/dev/null | head -10)
    if [[ -n "$untracked" ]]; then
        alert "UNTRACKED_FILES: New files in production!\n$untracked"
        return 1
    fi

    return 0
}

# Check 2: Critical files haven't been modified since last deploy
check_file_checksums() {
    local checksum_file="$PROD_DIR/.deploy-checksums"

    if [[ ! -f "$checksum_file" ]]; then
        log "INFO: No checksum file found, skipping checksum validation"
        return 0
    fi

    while IFS=' ' read -r expected_hash filepath; do
        if [[ -f "$PROD_DIR/$filepath" ]]; then
            local actual_hash=$(sha256sum "$PROD_DIR/$filepath" 2>/dev/null | cut -d' ' -f1)
            if [[ "$actual_hash" != "$expected_hash" ]]; then
                alert "CHECKSUM_MISMATCH: $filepath has been modified!"
                return 1
            fi
        fi
    done < "$checksum_file"

    return 0
}

# Check 3: No debug prints in Python files
check_debug_statements() {
    cd "$PROD_DIR"

    # Look for obvious debug statements
    local debug_found=$(grep -rn "print(.*debug\|print(.*DEBUG\|breakpoint()\|pdb.set_trace()\|import pdb" \
        backend/*.py backend/**/*.py 2>/dev/null | head -5 || true)

    if [[ -n "$debug_found" ]]; then
        alert "DEBUG_CODE: Debug statements found in production!\n$debug_found"
        return 1
    fi

    return 0
}

# Check 4: Backend process is running expected version
check_backend_version() {
    local expected_commit_file="$PROD_DIR/.deployed-commit"

    if [[ -f "$expected_commit_file" ]]; then
        local expected_commit=$(cat "$expected_commit_file")
        local actual_commit=$(cd "$PROD_DIR" && git rev-parse HEAD 2>/dev/null)

        if [[ "$expected_commit" != "$actual_commit" ]]; then
            alert "VERSION_MISMATCH: Deployed commit ($expected_commit) != current HEAD ($actual_commit)"
            return 1
        fi
    fi

    return 0
}

# Main execution
main() {
    local exit_code=0

    log "INFO: Starting integrity check"

    check_git_status || exit_code=1
    check_file_checksums || exit_code=1
    check_debug_statements || exit_code=1
    check_backend_version || exit_code=1

    if [[ $exit_code -eq 0 ]]; then
        log "INFO: Integrity check passed"
        rm -f "$ALERT_FILE" 2>/dev/null || true
    else
        log "ERROR: Integrity check FAILED"
    fi

    return $exit_code
}

main "$@"
