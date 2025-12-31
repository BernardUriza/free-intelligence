"""PHI Redaction - Detect and redact Protected Health Information.

HIPAA defines 18 identifiers as PHI:
1. Names
2. Geographic data (smaller than state)
3. Dates (except year) related to individual
4. Phone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers
13. Device identifiers
14. URLs
15. IP addresses
16. Biometric identifiers
17. Full-face photos
18. Any unique identifying number

This module provides patterns to detect and redact common PHI types.

Usage:
    from backend.src.fi_events.security.phi_redaction import redact_phi, detect_phi

    # Redact PHI from a dict
    safe_data = redact_phi({"patient_name": "John Doe", "count": 5})
    # Result: {"patient_name": "[REDACTED:NAME]", "count": 5}

    # Detect PHI in text
    findings = detect_phi("Call me at 555-123-4567")
    # Result: [{"type": "PHONE", "value": "555-123-4567", "start": 11}]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)

# Redaction placeholder format
REDACTED_FORMAT = "[REDACTED:{type}]"


@dataclass
class PHIPattern:
    """A pattern for detecting PHI."""

    name: str
    pattern: re.Pattern
    description: str


# PHI detection patterns
PHI_PATTERNS: list[PHIPattern] = [
    PHIPattern(
        name="SSN",
        pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        description="Social Security Number",
    ),
    PHIPattern(
        name="PHONE",
        pattern=re.compile(r"\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        description="Phone number",
    ),
    PHIPattern(
        name="EMAIL",
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        description="Email address",
    ),
    PHIPattern(
        name="IP",
        pattern=re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        description="IP address",
    ),
    PHIPattern(
        name="MRN",
        pattern=re.compile(r"\b(?:MRN|mrn|Medical Record)[:\s#]*[A-Z0-9]{6,12}\b", re.IGNORECASE),
        description="Medical Record Number",
    ),
    PHIPattern(
        name="DOB",
        pattern=re.compile(r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"),
        description="Date of Birth (MM/DD/YYYY or MM-DD-YYYY)",
    ),
    PHIPattern(
        name="CREDIT_CARD",
        pattern=re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        description="Credit card number",
    ),
    PHIPattern(
        name="ZIP",
        pattern=re.compile(r"\b\d{5}(?:-\d{4})?\b"),
        description="ZIP code",
    ),
]

# Field names that likely contain PHI
PHI_FIELD_NAMES = {
    # Names
    "name",
    "patient_name",
    "first_name",
    "last_name",
    "full_name",
    "physician_name",
    "doctor_name",
    "provider_name",
    # Contact
    "phone",
    "telephone",
    "fax",
    "email",
    "address",
    "street",
    "city",
    "state",
    "zip",
    "zipcode",
    "postal_code",
    # Medical
    "ssn",
    "social_security",
    "mrn",
    "medical_record",
    "health_plan_id",
    "insurance_id",
    "policy_number",
    "dob",
    "date_of_birth",
    "birthdate",
    # Content
    "transcript",
    "transcription",
    "text",
    "content",
    "message",
    "notes",
    "soap_note",
    "chief_complaint",
    "diagnosis",
}


@dataclass
class PHIFinding:
    """A detected PHI finding."""

    type: str
    value: str
    start: int
    end: int


def detect_phi(text: str) -> list[PHIFinding]:
    """Detect PHI in text.

    Args:
        text: Text to scan for PHI

    Returns:
        List of PHI findings
    """
    findings = []

    for pattern in PHI_PATTERNS:
        for match in pattern.pattern.finditer(text):
            findings.append(
                PHIFinding(
                    type=pattern.name,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                )
            )

    # Sort by position
    findings.sort(key=lambda f: f.start)

    return findings


def redact_text(text: str) -> str:
    """Redact PHI from text.

    Args:
        text: Text to redact

    Returns:
        Redacted text
    """
    result = text
    offset = 0

    findings = detect_phi(text)

    for finding in findings:
        replacement = REDACTED_FORMAT.format(type=finding.type)
        start = finding.start + offset
        end = finding.end + offset
        result = result[:start] + replacement + result[end:]
        offset += len(replacement) - (finding.end - finding.start)

    return result


def is_phi_field(field_name: str) -> bool:
    """Check if a field name likely contains PHI.

    Args:
        field_name: Field name to check

    Returns:
        True if likely PHI field
    """
    normalized = field_name.lower().replace("-", "_")
    return normalized in PHI_FIELD_NAMES


def redact_phi(
    data: dict[str, Any],
    deep: bool = True,
    redact_text_values: bool = True,
) -> dict[str, Any]:
    """Redact PHI from a dictionary.

    Args:
        data: Dictionary to redact
        deep: Whether to recursively redact nested dicts
        redact_text_values: Whether to scan text values for patterns

    Returns:
        Redacted dictionary (new copy)
    """
    result = {}

    for key, value in data.items():
        # Check if field name is PHI
        if is_phi_field(key):
            result[key] = REDACTED_FORMAT.format(type="FIELD")
            logger.debug("PHI_FIELD_REDACTED", field=key)

        # Recursively handle nested dicts
        elif isinstance(value, dict) and deep:
            result[key] = redact_phi(value, deep=True, redact_text_values=redact_text_values)

        # Recursively handle lists
        elif isinstance(value, list) and deep:
            result[key] = [
                redact_phi(item, deep=True, redact_text_values=redact_text_values)
                if isinstance(item, dict)
                else (
                    redact_text(str(item)) if isinstance(item, str) and redact_text_values else item
                )
                for item in value
            ]

        # Scan text values for PHI patterns
        elif isinstance(value, str) and redact_text_values:
            redacted = redact_text(value)
            if redacted != value:
                logger.debug("PHI_TEXT_REDACTED", field=key)
            result[key] = redacted

        # Pass through other values
        else:
            result[key] = value

    return result


def sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize data for safe logging (quick redaction).

    Only redacts known PHI field names, doesn't scan text.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary
    """
    return redact_phi(data, deep=True, redact_text_values=False)
