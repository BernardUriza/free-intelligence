#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Event Name Validator

Validates event names against the naming convention:
FORMAT: [AREA_]ENTITY_ACTION_PAST_PARTICIPLE

Examples:
  - CORPUS_INITIALIZED
  - INTERACTION_APPENDED
  - CORPUS_IDENTITY_ADDED

FI-API-FEAT-001
"""

import re
from typing import Any, Optional

# Canonical list of approved events (from docs/events.md + docs/honest-uncertainty.md)
CANONICAL_EVENTS = {
    # Corpus events (updated for honest uncertainty)
    "CORPUS_INITIALIZED",
    "CORPUS_INIT_FAILED",
    "CORPUS_SCHEMA_CHECKS_COMPLETED",  # Was: CORPUS_VALIDATION_PASSED
    "CORPUS_STATS_FAILED",
    "STATS_SNAPSHOT_COMPUTED",  # Was: CORPUS_STATS_RETRIEVED
    # Identity events (updated for honest uncertainty)
    "CORPUS_IDENTITY_ADDED",
    "CORPUS_IDENTITY_ADD_FAILED",
    "IDENTITY_METADATA_READ",  # Was: CORPUS_IDENTITY_RETRIEVED
    "CORPUS_IDENTITY_RETRIEVAL_FAILED",
    "CORPUS_IDENTITY_NOT_SET",
    "OWNERSHIP_HASH_MATCHED",  # Was: CORPUS_OWNERSHIP_VERIFIED
    "OWNERSHIP_HASH_MISMATCH",  # Was: CORPUS_OWNERSHIP_MISMATCH
    "CORPUS_VERIFICATION_ERROR",
    # Interaction events
    "INTERACTION_APPENDED",
    "INTERACTION_APPEND_FAILED",
    "INTERACTIONS_READ",
    "INTERACTIONS_READ_FAILED",
    # Embedding events
    "EMBEDDING_APPENDED",
    "EMBEDDING_APPEND_FAILED",
    # Config events
    "CONFIG_LOADED",
    "CONFIG_LOAD_FAILED",
    "CONFIG_VALIDATION_FAILED",
    # Logger events
    "LOGGER_INITIALIZED",
    "LOGGER_INIT_FAILED",
    # Policy/Validation events (honest uncertainty)
    "LLM_AUDIT_SCAN_COMPLETED",  # Was: LLM_AUDIT_VALIDATION_PASSED
    "LLM_AUDIT_VIOLATIONS_DETECTED",
    "MUTATION_SCAN_COMPLETED",  # Was: MUTATION_VALIDATION_PASSED
    "MUTATION_VIOLATIONS_DETECTED",
    "ROUTER_POLICY_SCAN_COMPLETED",  # Was: ROUTER_POLICY_VALIDATION_PASSED
    "ROUTER_POLICY_VIOLATIONS_DETECTED",
    "APPEND_ONLY_CHECKS_COMPLETED",  # Was: APPEND_ONLY_VERIFIED
    "APPEND_ONLY_VIOLATION_DETECTED",
    # Export events (honest uncertainty)
    "EXPORT_MANIFEST_CREATED",
    "MANIFEST_HASH_COMPARED",  # Was: EXPORT_MANIFEST_VALIDATED
    "EXPORT_HASH_MATCHED",  # Was: EXPORT_VALIDATED
    "EXPORT_HASH_MISMATCH",
    # Audit log events
    "AUDIT_LOGS_GROUP_INITIALIZED",
    "AUDIT_LOGS_GROUP_EXISTS",
    "AUDIT_LOG_APPENDED",
    "AUDIT_LOGS_READ_FAILED",
    "AUDIT_STATS_FAILED",
    # Retention policy events (FI-DATA-FEAT-007)
    "RETENTION_DRY_RUN",
    "RETENTION_CLEANUP_COMPLETED",
    "RETENTION_CLEANUP_NOTHING_TO_DELETE",
    "RETENTION_CLEANUP_FAILED",
    "RETENTION_CHECK_FAILED",
    "RETENTION_STATS_FAILED",
}

# Common past participles for validation (updated for honest uncertainty)
COMMON_PAST_PARTICIPLES = {
    "INITIALIZED",
    "CREATED",
    "ADDED",
    "UPDATED",
    "DELETED",
    "LOADED",
    "SAVED",
    "APPENDED",
    "STARTED",
    "STOPPED",
    "COMPLETED",
    "FAILED",
    "MISMATCH",
    "REJECTED",
    "BLOCKED",
    "NOT_FOUND",
    "NOT_SET",
    "READ",
    # Honest uncertainty terms (preferred)
    "MATCHED",
    "COMPUTED",
    "SCANNED",
    "DETECTED",
    "COMPARED",
    "RECORDED",
    "ATTEMPTED",
    "CHECKED",
    "SNAPSHOT",
    "OBSERVED",
    # Legacy terms (avoid in new code, kept for backwards compatibility)
    "RETRIEVED",
    "VERIFIED",
    "VALIDATED",
    "PASSED",
}


def validate_event_name(event_name: str, strict: bool = False) -> dict[str, Any]:
    """
    Validate event name against naming convention.

    Args:
        event_name: Event name to validate
        strict: If True, only allows canonical events

    Returns:
        Dictionary with validation results:
        - valid: bool
        - errors: List[str]
        - warnings: List[str]
        - event_name: str

    Examples:
        >>> result = validate_event_name("CORPUS_INITIALIZED")
        >>> result["valid"]
        True

        >>> result = validate_event_name("corpus_init")
        >>> result["valid"]
        False
        >>> "uppercase" in result["errors"][0].lower()
        True
    """
    errors = []
    warnings = []

    # Rule 1: Strict mode - must be in canonical list
    if strict and event_name not in CANONICAL_EVENTS:
        errors.append(
            f"Event '{event_name}' not in canonical list. " +
            "See docs/events.md for approved events."
        )

    # Rule 2: Must be all uppercase
    if not event_name.isupper():
        errors.append("Event name must be UPPER_SNAKE_CASE")

    # Rule 3: Only alphanumeric + underscores
    if not re.match(r"^[A-Z0-9_]+$", event_name):
        errors.append("Event name must contain only uppercase letters, numbers, and underscores")

    # Rule 4: No consecutive underscores
    if "__" in event_name:
        errors.append("Event name cannot have consecutive underscores")

    # Rule 5: No leading/trailing underscores
    if event_name.startswith("_") or event_name.endswith("_"):
        errors.append("Event name cannot start or end with underscore")

    # Rule 6: Maximum 50 characters
    if len(event_name) > 50:
        errors.append(f"Event name too long ({len(event_name)} chars). Maximum: 50")

    # Rule 7: Minimum 2 components (ENTITY_ACTION or AREA_ENTITY_ACTION)
    parts = event_name.split("_")
    if len(parts) < 2:
        errors.append("Event name must have at least 2 components: ENTITY_ACTION")

    # Rule 8: Should end with common past participle (warning only)
    if parts and not strict:
        last_part = parts[-1]
        # Check if last part is a known past participle
        if last_part not in COMMON_PAST_PARTICIPLES:
            # Also check for common compound endings
            is_past_tense = any(
                [
                    last_part.endswith("ED"),
                    last_part.endswith("SET"),
                    last_part.endswith("FOUND"),
                    last_part == "FAILED",
                    last_part == "PASSED",
                ]
            )
            if not is_past_tense:
                warnings.append(
                    f"Event may not end with past participle. " +
                    f"Got: '{last_part}'. Common endings: INITIALIZED, FAILED, ADDED, etc."
                )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "event_name": event_name,
    }


def validate_events_in_code(file_path: str) -> list[dict]:
    """
    Extract and validate all event names from a Python file.

    Args:
        file_path: Path to Python file to scan

    Returns:
        List of validation results for each event found

    Examples:
        >>> results = validate_events_in_code("backend/corpus_schema.py")
        >>> all(r["valid"] for r in results)
        True
    """
    import re
    from pathlib import Path

    if not Path(file_path).exists():
        return []

    content = Path(file_path).read_text()

    # Pattern to match logger calls: logger.info("EVENT_NAME", ...)
    pattern = r'logger\.(info|warning|error|debug|critical)\s*\(\s*["\']([A-Z_a-z0-9]+)["\']'
    matches = re.findall(pattern, content)

    results = []
    seen_events = set()

    for level, event_name in matches:
        if event_name not in seen_events:
            seen_events.add(event_name)
            result = validate_event_name(event_name, strict=False)
            result["level"] = level
            result["file"] = str(file_path)
            results.append(result)

    return results


def get_canonical_events() -> list[str]:
    """
    Get list of all canonical (approved) event names.

    Returns:
        Sorted list of canonical event names

    Examples:
        >>> events = get_canonical_events()
        >>> "CORPUS_INITIALIZED" in events
        True
    """
    return sorted(CANONICAL_EVENTS)


def suggest_event_name(description: str) -> Optional[str]:
    """
    Suggest a properly formatted event name from a description.

    Args:
        description: Human-readable description

    Returns:
        Suggested event name or None

    Examples:
        >>> suggest_event_name("corpus was initialized")
        'CORPUS_INITIALIZED'

        >>> suggest_event_name("failed to load config")
        'CONFIG_LOAD_FAILED'
    """
    # Simple heuristic-based suggestion
    description = description.upper()

    # Remove common words
    stop_words = ["THE", "A", "AN", "WAS", "IS", "TO", "FROM"]
    words = [w for w in description.split() if w not in stop_words]

    if not words:
        return None

    # Convert to past participle if needed
    past_participle_map = {
        "INITIALIZE": "INITIALIZED",
        "LOAD": "LOADED",
        "SAVE": "SAVED",
        "CREATE": "CREATED",
        "ADD": "ADDED",
        "FAIL": "FAILED",
        "VERIFY": "VERIFIED",
        "RETRIEVE": "RETRIEVED",
        "APPEND": "APPENDED",
    }

    # Replace with past participles
    converted_words = []
    for word in words:
        if word in past_participle_map:
            converted_words.append(past_participle_map[word])
        else:
            converted_words.append(word)

    suggested = "_".join(converted_words)

    # Validate suggestion
    result = validate_event_name(suggested)
    if result["valid"]:
        return suggested

    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        # Validate a single event name
        if len(sys.argv) < 3:
            print("Usage: python3 event_validator.py validate <event_name>")
            sys.exit(1)

        event_name = sys.argv[2]
        result = validate_event_name(event_name, strict=False)

        print(f"Event: {event_name}")
        print(f"Valid: {result['valid']}")

        if result["errors"]:
            print("\nErrors:")
            for error in result["errors"]:
                print(f"  ❌ {error}")

        if result["warnings"]:
            print("\nWarnings:")
            for warning in result["warnings"]:
                print(f"  ⚠️  {warning}")

        if result["valid"] and not result["warnings"]:
            print("✅ Event name is valid!")

        sys.exit(0 if result["valid"] else 1)

    elif len(sys.argv) > 1 and sys.argv[1] == "scan":
        # Scan a file for events
        if len(sys.argv) < 3:
            print("Usage: python3 event_validator.py scan <file_path>")
            sys.exit(1)

        file_path = sys.argv[2]
        results = validate_events_in_code(file_path)

        print(f"📄 Scanning: {file_path}")
        print(f"Found {len(results)} unique events\n")

        invalid_count = 0
        for result in results:
            status = "✅" if result["valid"] else "❌"
            print(f"{status} {result['event_name']} ({result['level']})")

            if result["errors"]:
                for error in result["errors"]:
                    print(f"     ❌ {error}")
                invalid_count += 1

            if result["warnings"]:
                for warning in result["warnings"]:
                    print(f"     ⚠️  {warning}")

        print(f"\nSummary: {len(results) - invalid_count}/{len(results)} valid")
        sys.exit(0 if invalid_count == 0 else 1)

    elif len(sys.argv) > 1 and sys.argv[1] == "list":
        # List canonical events
        print("📋 Canonical Events:")
        for event in get_canonical_events():
            print(f"  • {event}")

    else:
        print("Usage:")
        print("  python3 event_validator.py validate <event_name>")
        print("  python3 event_validator.py scan <file_path>")
        print("  python3 event_validator.py list")
