"""Export Policy - Free Intelligence.

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
        "format": "Union[markdown, json, hdf5] | csv",
        "purpose": "Union[personal_review, backup, migration] | analysis",
        "retention_days": int (opcional),
        "includes_pii": bool,
        "metadata": dict (opcional)
    }

Attributes:
    Author: Bernard Uriza Orozco
    Fecha: 2025-10-25
    Sprint: SPR-2025W44 (Sprint 2)
    Task: FI-SEC-FEAT-004

"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import sys
from pathlib import Path

# Import logger with fallback
try:
    from logger import get_logger

    logger = get_logger(__name__)
except ImportError:

    class SimpleLogger:
        """Simple fallback logger implementation."""

        def info(self, event: str, **kwargs: dict[str, Any]) -> None:
            """Log an info level message."""
            sys.stdout.write(f"INFO: {event} - {kwargs}\n")

        def warning(self, event: str, **kwargs: dict[str, Any]) -> None:
            """Log a warning level message."""
            sys.stderr.write(f"WARNING: {event} - {kwargs}\n")

        def error(self, event: str, **kwargs: dict[str, Any]) -> None:
            """Log an error level message."""
            sys.stderr.write(f"ERROR: {event} - {kwargs}\n")

    logger = SimpleLogger()

# ============================================================================
# EXCEPTIONS
# ============================================================================


class ExportPolicyError(Exception):
    """Raised when export policy is violated."""


class InvalidManifestError(Exception):
    """Raised when manifest schema is invalid."""


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

# Constants
SHA256_LENGTH = 64
MIN_ARGV_LENGTH = 2
CREATE_ARGV_LENGTH = 7
VALIDATE_ARGV_LENGTH = 4
LOAD_ARGV_LENGTH = 3


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class ExportManifest:
    """Manifest de exportación con metadata completa.

    Fields:
        export_id: UUID v4 único para export
        timestamp: ISO 8601 con timezone
        exported_by: owner_hash prefix o user_id
        data_source: HDF5 group exportado (e.g., /interactions/)
        data_hash: SHA256 de datos exportados
        format_: Formato de export (markdown, json, etc.)
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
    format_: str
    purpose: str
    retention_days: int | None = None
    includes_pii: bool = True
    metadata: dict[str, Any] | None = None

    def __init__(
        self,
        *,
        export_id: str,
        timestamp: str,
        exported_by: str,
        data_source: str,
        data_hash: str,
        format_: str,
        purpose: str,
        retention_days: int | None = None,
        includes_pii: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ExportManifest instance."""
        # Core required fields
        self.export_id = export_id
        self.timestamp = timestamp
        self.exported_by = exported_by
        self.data_source = data_source
        self.data_hash = data_hash
        self.format_ = format_
        self.purpose = purpose

        # Optional fields
        self.retention_days = retention_days
        self.includes_pii = includes_pii
        self.metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """Convierte a dict (para JSON serialization)."""
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self, indent: int = 2) -> str:
        """Serializa a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: Path) -> None:
        """Guarda manifest a archivo JSON."""
        filepath.write_text(self.to_json(), encoding="utf-8")
        logger.info("EXPORT_MANIFEST_SAVED", export_id=self.export_id, filepath=str(filepath))


# ============================================================================
# VALIDATORS
# ============================================================================


def validate_manifest_schema(manifest: ExportManifest) -> bool:
    """Valida que el manifest cumpla con el schema.

    Raises:
        InvalidManifest: Si hay campos faltantes o inválidos

    """
    # Check required fields
    manifest_dict = manifest.to_dict()
    missing_fields = REQUIRED_FIELDS - set(manifest_dict.keys())

    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        raise InvalidManifestError(error_msg)

    # Validate export_id is UUID
    try:
        uuid.UUID(manifest.export_id)
    except ValueError as err:
        error_msg = f"export_id must be valid UUID v4: {manifest.export_id}"
        raise InvalidManifestError(error_msg) from err

    # Validate timestamp is ISO 8601
    try:
        datetime.fromisoformat(manifest.timestamp)
    except ValueError as err:
        error_msg = f"timestamp must be ISO 8601: {manifest.timestamp}"
        raise InvalidManifestError(error_msg) from err

    # Validate format
    if manifest.format_ not in ALLOWED_FORMATS:
        error_msg = f"format must be one of {ALLOWED_FORMATS}, got: {manifest.format_}"
        raise InvalidManifestError(error_msg)

    # Validate purpose
    if manifest.purpose not in ALLOWED_PURPOSES:
        error_msg = f"purpose must be one of {ALLOWED_PURPOSES}, got: {manifest.purpose}"
        raise InvalidManifestError(error_msg)

    # Validate data_hash is SHA256 (64 hex chars)
    if len(manifest.data_hash) != SHA256_LENGTH or not all(
        c in "0123456789abcdef" for c in manifest.data_hash
    ):
        error_msg = f"data_hash must be SHA256 ({SHA256_LENGTH} hex chars): {manifest.data_hash}"
        raise InvalidManifestError(error_msg)

    logger.info(
        "MANIFEST_HASH_COMPARED",
        export_id=manifest.export_id,
        format=manifest.format_,
        purpose=manifest.purpose,
    )

    return True


def compute_file_hash(filepath: Path) -> str:
    """Computa SHA256 hash de archivo.

    Returns:
        SHA256 hash en hex (64 chars)

    """
    sha256 = hashlib.sha256()

    with filepath.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def validate_export(manifest: ExportManifest, export_filepath: Path) -> bool:
    """Valida export completo: manifest schema + data hash match.

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
        error_msg = f"Export file does not exist: {export_filepath}"
        raise ExportPolicyError(error_msg)

    # 3. Compute actual file hash
    actual_hash = compute_file_hash(export_filepath)

    # 4. Verify hash matches manifest
    if actual_hash != manifest.data_hash:
        error_msg = f"Data hash mismatch! Manifest: {manifest.data_hash}, Actual: {actual_hash}"
        raise ExportPolicyError(error_msg)

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
    format_: str,
    purpose: str,
    *,
    retention_days: int | None = None,
    includes_pii: bool = True,
    metadata: dict[str, Any] | None = None,
) -> ExportManifest:
    """Crea manifest de export con metadata completa.

    Args:
        exported_by: owner_hash prefix o user_id
        data_source: HDF5 group exportado (e.g., /interactions/)
        export_filepath: Path al archivo exportado
        format_: Formato de export
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
        format_=format_,
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
        format=format_,
        purpose=purpose,
    )

    return manifest


def load_manifest(filepath: Path) -> ExportManifest:
    """Carga manifest desde archivo JSON.

    Args:
        filepath: Path al manifest JSON

    Returns:
        ExportManifest validado

    """
    if not filepath.exists():
        error_msg = f"Manifest not found: {filepath}"
        raise FileNotFoundError(error_msg)

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

    if len(sys.argv) < MIN_ARGV_LENGTH:
        sys.stdout.write("Usage:\n")
        sys.stdout.write(
            "  python3 backend/export_policy.py create "
            "<export_file> <data_source> <format> <purpose> <user_id>\n",
        )
        sys.stdout.write(
            "  python3 backend/export_policy.py validate <manifest.json> <export_file>\n",
        )
        sys.stdout.write("  python3 backend/export_policy.py load <manifest.json>\n")
        sys.stdout.write("\nExamples:\n")
        sys.stdout.write(
            "  python3 backend/export_policy.py create "
            "exports/data.md /interactions/ markdown personal_review user123\n",
        )
        sys.stdout.write(
            "  python3 backend/export_policy.py validate "
            "exports/data.manifest.json exports/data.md\n",
        )
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < CREATE_ARGV_LENGTH:
            sys.stdout.write(
                "Error: create requires: <export_file> <data_source> "
                "<format> <purpose> <user_id>\n",
            )
            sys.exit(1)

        export_file = Path(sys.argv[2])
        data_source = sys.argv[3]
        format_type = sys.argv[4]
        purpose = sys.argv[5]
        user_id = sys.argv[6]

        if not export_file.exists():
            sys.stdout.write(f"Error: Export file not found: {export_file}\n")
            sys.exit(1)

        sys.stdout.write(f"📦 Creating export manifest for {export_file}...\n")

        manifest = create_export_manifest(
            exported_by=user_id,
            data_source=data_source,
            export_filepath=export_file,
            format_=format_type,
            purpose=purpose,
        )

        # Save manifest
        manifest_file = export_file.with_suffix(".manifest.json")
        manifest.save(manifest_file)

        sys.stdout.write(f"\n✅ Manifest created: {manifest_file}\n")
        sys.stdout.write(f"   Export ID: {manifest.export_id}\n")
        sys.stdout.write(f"   Data hash: {manifest.data_hash[:16]}...\n")
        sys.stdout.write(f"   Format: {manifest.format_}\n")
        sys.stdout.write(f"   Purpose: {manifest.purpose}\n")

    elif command == "validate":
        if len(sys.argv) < VALIDATE_ARGV_LENGTH:
            sys.stdout.write("Error: validate requires: <manifest.json> <export_file>\n")
            sys.exit(1)

        manifest_file = Path(sys.argv[2])
        export_file = Path(sys.argv[3])

        sys.stdout.write("🔍 Validating export...\n")

        try:
            manifest = load_manifest(manifest_file)
            validate_export(manifest, export_file)

            sys.stdout.write("\n✅ EXPORT VALIDATION PASSED\n")
            sys.stdout.write(f"   Export ID: {manifest.export_id}\n")
            sys.stdout.write(f"   Data hash: {manifest.data_hash[:16]}... ✓\n")
            sys.stdout.write("   Schema: Valid ✓\n")

        except (InvalidManifestError, ExportPolicyError) as e:
            sys.stderr.write("\n❌ EXPORT VALIDATION FAILED\n")
            sys.stderr.write(f"   Error: {e!s}\n")
            sys.exit(1)

    elif command == "load":
        if len(sys.argv) < LOAD_ARGV_LENGTH:
            sys.stdout.write("Error: load requires: <manifest.json>\n")
            sys.exit(1)

        manifest_file = Path(sys.argv[2])

        sys.stdout.write(f"📖 Loading manifest {manifest_file}...\n")

        try:
            manifest = load_manifest(manifest_file)

            sys.stdout.write("\n✅ Manifest loaded:\n")
            sys.stdout.write(json.dumps(manifest.to_dict(), indent=2) + "\n")

        except (FileNotFoundError, InvalidManifestError) as e:
            sys.stderr.write("\n❌ Failed to load manifest\n")
            sys.stderr.write(f"   Error: {e!s}\n")
            sys.exit(1)

    else:
        sys.stderr.write(f"Error: Unknown command '{command}'\n")
        sys.stderr.write("Available commands: create, validate, load\n")
        sys.exit(1)
