from __future__ import annotations

"""
Free Intelligence - Schema Normalizer

Normalizes LLM outputs to conform to JSON schemas by:
- Converting null → [] for array fields with type "array"
- Converting null → {} for object fields with type "object"
- Ensuring required fields exist with correct types

This prevents schema validation failures from incomplete/truncated LLM responses.

Philosophy: Be lenient with LLM output, strict with validation.

File: backend/schema_normalizer.py
Created: 2025-10-28
"""

from typing import Any, Dict

from backend.logger import get_logger

logger = get_logger(__name__)


def normalize_output(output: Dict[str, Any], schema: Dict[str, Any]) -> dict[str, Any]:
    """
    Normalize LLM output to match schema requirements.

    Fixes common issues:
    - null → [] for array fields
    - null → {} for object fields
    - Missing required fields filled with defaults

    Args:
        output: Raw LLM output (possibly incomplete/malformed)
        schema: JSON Schema definition

    Returns:
        Normalized output conforming to schema

    Examples:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "items": {"type": "array"},
        ...         "count": {"type": "integer"}
        ...     },
        ...     "required": ["items", "count"]
        ... }
        >>> output = {"items": None, "count": 5}
        >>> normalized = normalize_output(output, schema)
        >>> assert normalized == {"items": [], "count": 5}
    """
    if not isinstance(output, dict) or not isinstance(schema, dict):
        logger.warning(
            "NORMALIZE_SKIP_INVALID_TYPES",
            output_type=type(output).__name__,
            schema_type=type(schema).__name__,
        )
        return output

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    normalized = output.copy()

    # Normalize properties
    for field_name, field_schema in properties.items():
        field_type = field_schema.get("type")

        # Handle list/tuple type specs (e.g., ["string", "null"])
        if isinstance(field_type, list):
            # Extract non-null type (e.g., "array" from ["array", "null"])
            field_type = next((t for t in field_type if t != "null"), None)

        current_value = normalized.get(field_name)

        # Fix 1: null → [] for array fields
        if field_type == "array" and current_value is None:
            normalized[field_name] = []
            logger.info("NORMALIZE_NULL_TO_ARRAY", field=field_name, before="null", after="[]")

        # Fix 2: null → {} for object fields
        elif field_type == "object" and current_value is None:
            normalized[field_name] = {}
            logger.info("NORMALIZE_NULL_TO_OBJECT", field=field_name, before="null", after="{}")

        # Fix 3: Recursively normalize nested objects
        elif field_type == "object" and isinstance(current_value, dict):
            normalized[field_name] = normalize_output(current_value, field_schema)

    # Fix 4: Add missing required fields with defaults
    for field_name in required:
        if field_name not in normalized or normalized[field_name] is None:
            field_schema = properties.get(field_name, {})
            field_type = field_schema.get("type")

            # Handle list type specs
            if isinstance(field_type, list):
                field_type = next((t for t in field_type if t != "null"), None)

            # Add default value based on type
            if field_type == "array":
                default_value = []
            elif field_type == "object":
                default_value = {}
            elif field_type == "string":
                default_value = ""
            elif field_type == "integer":
                default_value = 0
            elif field_type == "number":
                default_value = 0.0
            elif field_type == "boolean":
                default_value = False
            else:
                default_value = None

            if default_value is not None:
                normalized[field_name] = default_value
                logger.warning(
                    "NORMALIZE_MISSING_REQUIRED_FIELD",
                    field=field_name,
                    type=field_type,
                    default=default_value,
                )

    return normalized


def normalize_intake_output(output: Dict[str, Any]) -> dict[str, Any]:
    """
    Normalize IntakeCoach output specifically.

    Handles common issues with intake.schema.json:
    - medical_history.allergies null → []
    - medical_history.medications null → []
    - medical_history.conditions null → []
    - symptoms null → []

    Args:
        output: Raw IntakeCoach output

    Returns:
        Normalized output

    Examples:
        >>> output = {
        ...     "demographics": {"age": 28},
        ...     "chief_complaint": null,
        ...     "symptoms": [],
        ...     "medical_history": {
        ...         "allergies": ["penicillin"],
        ...         "medications": null,  # TRUNCATED!
        ...         "conditions": null    # TRUNCATED!
        ...     },
        ...     "urgency": null
        ... }
        >>> normalized = normalize_intake_output(output)
        >>> assert normalized["medical_history"]["medications"] == []
        >>> assert normalized["medical_history"]["conditions"] == []
    """
    normalized = output.copy()

    # Fix 1: symptoms null → []
    if "symptoms" in normalized and normalized["symptoms"] is None:
        normalized["symptoms"] = []
        logger.info("NORMALIZE_INTAKE_SYMPTOMS", before="null", after="[]")

    # Fix 2: medical_history fields
    if "medical_history" in normalized and isinstance(normalized["medical_history"], dict):
        med_hist = normalized["medical_history"]

        # allergies null → []
        if "allergies" in med_hist and med_hist["allergies"] is None:
            med_hist["allergies"] = []
            logger.info("NORMALIZE_INTAKE_ALLERGIES", before="null", after="[]")

        # medications null → []
        if "medications" in med_hist and med_hist["medications"] is None:
            med_hist["medications"] = []
            logger.info("NORMALIZE_INTAKE_MEDICATIONS", before="null", after="[]")

        # conditions null → []
        if "conditions" in med_hist and med_hist["conditions"] is None:
            med_hist["conditions"] = []
            logger.info("NORMALIZE_INTAKE_CONDITIONS", before="null", after="[]")

        # Add missing required fields
        if "allergies" not in med_hist:
            med_hist["allergies"] = []
            logger.warning("NORMALIZE_INTAKE_MISSING_ALLERGIES", added="[]")

        if "medications" not in med_hist:
            med_hist["medications"] = []
            logger.warning("NORMALIZE_INTAKE_MISSING_MEDICATIONS", added="[]")

        if "conditions" not in med_hist:
            med_hist["conditions"] = []
            logger.warning("NORMALIZE_INTAKE_MISSING_CONDITIONS", added="[]")

    # Fix 3: Add missing medical_history object
    elif "medical_history" not in normalized or normalized["medical_history"] is None:
        normalized["medical_history"] = {"allergies": [], "medications": [], "conditions": []}
        logger.warning("NORMALIZE_INTAKE_MISSING_MEDICAL_HISTORY", added="{...}")

    return normalized


if __name__ == "__main__":
    """Demo script"""
    print("🔧 Schema Normalizer Demo")
    print("=" * 60)

    # Test Case 1: Generic normalization
    print("\n1️⃣  Test: Generic schema normalization (null → [])")

    schema = {
        "type": "object",
        "properties": {
            "items": {"type": "array"},
            "tags": {"type": "array"},
            "metadata": {"type": "object"},
            "count": {"type": "integer"},
        },
        "required": ["items", "count"],
    }

    output = {
        "items": None,  # Should become []
        "tags": None,  # Should become []
        "metadata": None,  # Should become {}
        "count": 5,
    }

    normalized = normalize_output(output, schema)

    print(
        f"   Before: items={output['items']}, tags={output['tags']}, metadata={output['metadata']}"
    )
    print(
        f"   After:  items={normalized['items']}, tags={normalized['tags']}, metadata={normalized['metadata']}"
    )
    assert normalized["items"] == []
    assert normalized["tags"] == []
    assert normalized["metadata"] == {}
    assert normalized["count"] == 5
    print("   ✅ PASSED")

    # Test Case 2: IntakeCoach specific (Case 7 scenario)
    print("\n2️⃣  Test: IntakeCoach normalization (Case 7 scenario)")

    output = {
        "demographics": {"name": None, "age": 28, "gender": None, "contact": None},
        "chief_complaint": None,
        "symptoms": [],
        "medical_history": {
            "allergies": ["penicillin"],
            "medications": None,  # TRUNCATED - should become []
            "conditions": None,  # TRUNCATED - should become []
        },
        "urgency": None,
        "notes": None,
    }

    normalized = normalize_intake_output(output)

    print(f"   Before: medications={output['medical_history']['medications']}")
    print(f"   After:  medications={normalized['medical_history']['medications']}")
    print(f"   Before: conditions={output['medical_history']['conditions']}")
    print(f"   After:  conditions={normalized['medical_history']['conditions']}")

    assert normalized["medical_history"]["medications"] == []
    assert normalized["medical_history"]["conditions"] == []
    assert normalized["medical_history"]["allergies"] == ["penicillin"]
    print("   ✅ PASSED")

    # Test Case 3: Missing required field
    print("\n3️⃣  Test: Add missing required fields")

    output = {
        "demographics": {"age": 30},
        # missing: chief_complaint, symptoms, medical_history, urgency
    }

    schema = {
        "type": "object",
        "properties": {
            "demographics": {"type": "object"},
            "chief_complaint": {"type": "string"},
            "symptoms": {"type": "array"},
            "medical_history": {"type": "object"},
            "urgency": {"type": "string"},
        },
        "required": ["demographics", "chief_complaint", "symptoms", "medical_history", "urgency"],
    }

    normalized = normalize_output(output, schema)

    print(f"   Fields added: {set(normalized.keys()) - set(output.keys())}")
    assert "symptoms" in normalized
    assert normalized["symptoms"] == []
    assert "medical_history" in normalized
    assert normalized["medical_history"] == {}
    print("   ✅ PASSED")

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
