from __future__ import annotations

"""
Export Policy - Free Intelligence

Policy: TODA exportación de datos debe tener manifest con metadata completa.

Propósito:
- Trazabilidad de exports (quién, cuándo, qué, para qué)
- Validación de schema de manifest
- Audit trail de salida de datos
- Non-repudiation (SHA256 de exported data)

Uso:
    from export_policy import ExportManifest, validate_export

    # Crear manifest
    manifest = ExportManifest(
        export_id="uuid",
        timestamp="ISO8601",
        exported_by="user_hash",
        data_source="/interactions/",
        data_hash="sha256",
        format="markdown",
        purpose="personal_review",
        retention_days=30
    )

    # Validar export
    is_valid = validate_export(manifest, export_filepath)

Manifest Schema:
    {
        "export_id": "UUID v4",
        "timestamp": "ISO 8601 con timezone",
        "exported_by": "owner_hash prefix o user_id",
        "data_source": "HDF5 group exportado (/interactions/)",
        "data_hash": "SHA256 de datos exportados",
        "format": "markdown | json | hdf5 | csv",
        "purpose": "personal_review | backup | migration | analysis",
        "retention_days": int (opcional),
        "includes_pii": bool,
        "metadata": dict (opcional)
    }

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Sprint: SPR-2025W44 (Sprint 2)
Task: FI-SEC-FEAT-004
"""

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Optional logger import
try:
    from logger import get_logger

    logger = get_logger(__name__)
except ImportError:

    class SimpleLogger:
        def info(self, event, **kwargs):
            print(f"INFO: {event} - {kwargs}")

        def warning(self, event, **kwargs):
            print(f"WARNING: {event} - {kwargs}")

        def error(self, event, **kwargs):
            print(f"ERROR: {event} - {kwargs}")

    logger = SimpleLogger()


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ExportPolicyViolation(Exception):
    """Raised when export policy is violated."""

    pass


class InvalidManifest(Exception):
    """Raised when manifest schema is invalid."""

    pass


# ============================================================================
# CONFIGURATION
# ============================================================================

# Allowed export formats
ALLOWED_FORMATS = {"markdown", "json", "hdf5", "csv", "txt"}

# Allowed export purposes
ALLOWED_PURPOSES = {
    "personal_review",  # User reviewing own data
    "backup",  # Backup to external storage
    "migration",  # Moving to different system
    "analysis",  # Data analysis
    "compliance",  # Legal/compliance requirement
    "research",  # Research purposes
}

# Required manifest fields
REQUIRED_FIELDS = {
    "export_id",
    "timestamp",
    "exported_by",
    "data_source",
    "data_hash",
    "format",
    "purpose",
}


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class ExportManifest:
    """
    Manifest de exportación con metadata completa.

    Fields:
        export_id: UUID v4 único para export
        timestamp: ISO 8601 con timezone
        exported_by: owner_hash prefix o user_id
        data_source: HDF5 group exportado (e.g., /interactions/)
        data_hash: SHA256 de datos exportados
        format: Formato de export (markdown, json, etc.)
        purpose: Propósito del export
        retention_days: Días de retención (opcional)
        includes_pii: Si incluye datos personales
        metadata: Metadata adicional (opcional)
    """

    export_id: str
    timestamp: str
    exported_by: str
    data_source: str
    data_hash: str
    format: str
    purpose: str
    retention_days: Optional[int] = None
    includes_pii: bool = True
    metadata: dict[str, Optional[Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convierte a dict (para JSON serialization)."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self, indent: int = 2) -> str:
        """Serializa a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: Path):
        """Guarda manifest a archivo JSON."""
        filepath.write_text(self.to_json(), encoding="utf-8")
        logger.info("EXPORT_MANIFEST_SAVED", export_id=self.export_id, filepath=str(filepath))


# ============================================================================
# VALIDATORS
# ============================================================================


def validate_manifest_schema(manifest: ExportManifest) -> bool:
    """
    Valida que el manifest cumpla con el schema.

    Raises:
        InvalidManifest: Si hay campos faltantes o inválidos
    """
    # Check required fields
    manifest_dict = manifest.to_dict()
    missing_fields = REQUIRED_FIELDS - set(manifest_dict.keys())

    if missing_fields:
        raise InvalidManifest(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate export_id is UUID
    try:
        uuid.UUID(manifest.export_id)
    except ValueError:
        raise InvalidManifest(f"export_id must be valid UUID v4: {manifest.export_id}")

    # Validate timestamp is ISO 8601
    try:
        datetime.fromisoformat(manifest.timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise InvalidManifest(f"timestamp must be ISO 8601: {manifest.timestamp}")

    # Validate format
    if manifest.format not in ALLOWED_FORMATS:
        raise InvalidManifest(f"format must be one of {ALLOWED_FORMATS}, got: {manifest.format}")

    # Validate purpose
    if manifest.purpose not in ALLOWED_PURPOSES:
        raise InvalidManifest(f"purpose must be one of {ALLOWED_PURPOSES}, got: {manifest.purpose}")

    # Validate data_hash is SHA256 (64 hex chars)
    if len(manifest.data_hash) != 64 or not all(
        c in "0123456789abcdef" for c in manifest.data_hash
    ):
        raise InvalidManifest(f"data_hash must be SHA256 (64 hex chars): {manifest.data_hash}")

    logger.info(
        "MANIFEST_HASH_COMPARED",
        export_id=manifest.export_id,
        format=manifest.format,
        purpose=manifest.purpose,
    )

    return True


def compute_file_hash(filepath: Path) -> str:
    """
    Computa SHA256 hash de archivo.

    Returns:
        SHA256 hash en hex (64 chars)
    """
    sha256 = hashlib.sha256()

    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def validate_export(manifest: ExportManifest, export_filepath: Path) -> bool:
    """
    Valida export completo: manifest schema + data hash match.

    Args:
        manifest: ExportManifest con metadata
        export_filepath: Path al archivo exportado

    Returns:
        True si validación pasa

    Raises:
        InvalidManifest: Si manifest es inválido
        ExportPolicyViolation: Si data hash no match
    """
    # 1. Validate manifest schema
    validate_manifest_schema(manifest)

    # 2. Validate export file exists
    if not export_filepath.exists():
        raise ExportPolicyViolation(f"Export file does not exist: {export_filepath}")

    # 3. Compute actual file hash
    actual_hash = compute_file_hash(export_filepath)

    # 4. Verify hash matches manifest
    if actual_hash != manifest.data_hash:
        raise ExportPolicyViolation(
            "Data hash mismatch! " + f"Manifest: {manifest.data_hash}, " + f"Actual: {actual_hash}"
        )

    logger.info(
        "EXPORT_HASH_MATCHED",
        export_id=manifest.export_id,
        filepath=str(export_filepath),
        data_hash=actual_hash[:16] + "...",
    )

    return True


# ============================================================================
# MANIFEST CREATION
# ============================================================================


def create_export_manifest(
    exported_by: str,
    data_source: str,
    export_filepath: Path,
    format: str,
    purpose: str,
    retention_days: Optional[int] = None,
    includes_pii: bool = True,
    metadata: dict[str, Optional[Any]] = None,
) -> ExportManifest:
    """
    Crea manifest de export con metadata completa.

    Args:
        exported_by: owner_hash prefix o user_id
        data_source: HDF5 group exportado (e.g., /interactions/)
        export_filepath: Path al archivo exportado
        format: Formato de export
        purpose: Propósito del export
        retention_days: Días de retención (opcional)
        includes_pii: Si incluye PII
        metadata: Metadata adicional

    Returns:
        ExportManifest validado
    """
    # Generate export_id
    export_id = str(uuid.uuid4())

    # Generate timestamp
    timestamp = datetime.now(timezone.utc).isoformat()

    # Compute data hash
    data_hash = compute_file_hash(export_filepath)

    # Create manifest
    manifest = ExportManifest(
        export_id=export_id,
        timestamp=timestamp,
        exported_by=exported_by,
        data_source=data_source,
        data_hash=data_hash,
        format=format,
        purpose=purpose,
        retention_days=retention_days,
        includes_pii=includes_pii,
        metadata=metadata,
    )

    # Validate schema
    validate_manifest_schema(manifest)

    logger.info(
        "EXPORT_MANIFEST_CREATED",
        export_id=export_id,
        data_source=data_source,
        format=format,
        purpose=purpose,
    )

    return manifest


def load_manifest(filepath: Path) -> ExportManifest:
    """
    Carga manifest desde archivo JSON.

    Args:
        filepath: Path al manifest JSON

    Returns:
        ExportManifest validado
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Manifest not found: {filepath}")

    data = json.loads(filepath.read_text(encoding="utf-8"))

    manifest = ExportManifest(**data)

    # Validate schema
    validate_manifest_schema(manifest)

    logger.info("EXPORT_MANIFEST_LOADED", export_id=manifest.export_id, filepath=str(filepath))

    return manifest


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python3 backend/export_policy.py create <export_file> <data_source> <format> <purpose> <user_id>"
        )
        print("  python3 backend/export_policy.py validate <manifest.json> <export_file>")
        print("  python3 backend/export_policy.py load <manifest.json>")
        print("\nExamples:")
        print(
            "  python3 backend/export_policy.py create exports/data.md /interactions/ markdown personal_review user123"
        )
        print(
            "  python3 backend/export_policy.py validate exports/data.manifest.json exports/data.md"
        )
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 7:
            print(
                "Error: create requires: <export_file> <data_source> <format> <purpose> <user_id>"
            )
            sys.exit(1)

        export_file = Path(sys.argv[2])
        data_source = sys.argv[3]
        format_type = sys.argv[4]
        purpose = sys.argv[5]
        user_id = sys.argv[6]

        if not export_file.exists():
            print(f"Error: Export file not found: {export_file}")
            sys.exit(1)

        print(f"📦 Creating export manifest for {export_file}...")

        manifest = create_export_manifest(
            exported_by=user_id,
            data_source=data_source,
            export_filepath=export_file,
            format=format_type,
            purpose=purpose,
        )

        # Save manifest
        manifest_file = export_file.with_suffix(".manifest.json")
        manifest.save(manifest_file)

        print(f"\n✅ Manifest created: {manifest_file}")
        print(f"   Export ID: {manifest.export_id}")
        print(f"   Data hash: {manifest.data_hash[:16]}...")
        print(f"   Format: {manifest.format}")
        print(f"   Purpose: {manifest.purpose}")

    elif command == "validate":
        if len(sys.argv) < 4:
            print("Error: validate requires: <manifest.json> <export_file>")
            sys.exit(1)

        manifest_file = Path(sys.argv[2])
        export_file = Path(sys.argv[3])

        print("🔍 Validating export...")

        try:
            manifest = load_manifest(manifest_file)
            validate_export(manifest, export_file)

            print("\n✅ EXPORT VALIDATION PASSED")
            print(f"   Export ID: {manifest.export_id}")
            print(f"   Data hash: {manifest.data_hash[:16]}... ✓")
            print("   Schema: Valid ✓")

        except (InvalidManifest, ExportPolicyViolation) as e:
            print("\n❌ EXPORT VALIDATION FAILED")
            print(f"   Error: {str(e)}")
            sys.exit(1)

    elif command == "load":
        if len(sys.argv) < 3:
            print("Error: load requires: <manifest.json>")
            sys.exit(1)

        manifest_file = Path(sys.argv[2])

        print(f"📖 Loading manifest {manifest_file}...")

        try:
            manifest = load_manifest(manifest_file)

            print("\n✅ Manifest loaded:")
            print(json.dumps(manifest.to_dict(), indent=2))

        except (FileNotFoundError, InvalidManifest) as e:
            print("\n❌ Failed to load manifest")
            print(f"   Error: {str(e)}")
            sys.exit(1)

    else:
        print(f"Error: Unknown command '{command}'")
        print("Available commands: create, validate, load")
        sys.exit(1)
