"""File validation service for document uploads.

Validates file size, format, and magic bytes.
Integrates with audit service for security logging.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile, status

from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.api.audit.dependencies import DIAuditService

logger = get_logger(__name__)


@dataclass(frozen=True)
class FileValidationConfig:
    """Configuration for file validation."""

    min_size_bytes: int = 10
    max_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_extensions: frozenset[str] = frozenset({"txt", "md", "pdf", "docx"})


# Magic bytes for file type validation
MAGIC_BYTES: dict[str, tuple[bytes, str]] = {
    "pdf": (b"%PDF", "PDF debe comenzar con %PDF"),
    "png": (b"\x89PNG", "PNG debe tener header valido"),
    "jpg": (b"\xff\xd8\xff", "JPEG debe tener header valido"),
    "jpeg": (b"\xff\xd8\xff", "JPEG debe tener header valido"),
    "docx": (b"PK\x03\x04", "DOCX debe ser un archivo ZIP valido"),
}


class FileValidator:
    """Validates uploaded files for security and format compliance.

    Single Responsibility: Only handles file validation logic.
    """

    def __init__(
        self,
        config: FileValidationConfig | None = None,
        audit_service: "DIAuditService | None" = None,
    ) -> None:
        self.config = config or FileValidationConfig()
        self.audit_service = audit_service

    def validate(
        self,
        file: UploadFile,
        content: bytes,
        user_id: str | None = None,
        clinic_id: str | None = None,
    ) -> None:
        """Validate uploaded file.

        Args:
            file: Uploaded file metadata
            content: File binary content
            user_id: Optional user ID for audit logging
            clinic_id: Optional clinic ID for audit logging

        Raises:
            HTTPException: If validation fails
        """
        filename = file.filename or "unknown"

        self._validate_not_empty(filename, content, user_id, clinic_id)
        self._validate_min_size(filename, content, user_id, clinic_id)
        self._validate_max_size(filename, content, user_id, clinic_id)
        self._validate_not_html_masquerade(filename, content, user_id, clinic_id)
        self._validate_magic_bytes(filename, content, user_id, clinic_id)

    def _log_rejection(
        self,
        reason: str,
        filename: str,
        user_id: str | None,
        clinic_id: str | None,
        details: dict,
    ) -> None:
        """Log rejection to audit service if available."""
        if self.audit_service and user_id:
            self.audit_service.log_action(
                action="document_upload_rejected",
                user_id=user_id,
                clinic_id=clinic_id,
                resource=filename,
                result="failure",
                details={"reason": reason, **details},
            )

    def _validate_not_empty(
        self,
        filename: str,
        content: bytes,
        user_id: str | None,
        clinic_id: str | None,
    ) -> None:
        """Reject empty files."""
        if len(content) == 0:
            logger.error("UPLOAD_REJECTED_EMPTY_FILE", filename=filename)
            self._log_rejection("empty_file", filename, user_id, clinic_id, {})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo esta vacio. Por favor selecciona un archivo valido.",
            )

    def _validate_min_size(
        self,
        filename: str,
        content: bytes,
        user_id: str | None,
        clinic_id: str | None,
    ) -> None:
        """Reject suspiciously small files."""
        if len(content) < self.config.min_size_bytes:
            logger.error(
                "UPLOAD_REJECTED_TOO_SMALL",
                filename=filename,
                size_bytes=len(content),
            )
            self._log_rejection(
                "file_too_small",
                filename,
                user_id,
                clinic_id,
                {
                    "size_bytes": len(content),
                    "min_size_bytes": self.config.min_size_bytes,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo es demasiado pequeno ({len(content)} bytes). "
                f"Minimo {self.config.min_size_bytes} bytes.",
            )

    def _validate_max_size(
        self,
        filename: str,
        content: bytes,
        user_id: str | None,
        clinic_id: str | None,
    ) -> None:
        """Reject files that are too large."""
        if len(content) > self.config.max_size_bytes:
            logger.error(
                "UPLOAD_REJECTED_TOO_LARGE",
                filename=filename,
                size_bytes=len(content),
            )
            self._log_rejection(
                "file_too_large",
                filename,
                user_id,
                clinic_id,
                {
                    "size_bytes": len(content),
                    "max_size_bytes": self.config.max_size_bytes,
                },
            )
            max_mb = self.config.max_size_bytes / 1024 / 1024
            actual_mb = len(content) / 1024 / 1024
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Archivo demasiado grande. Maximo {max_mb:.0f} MB, "
                f"recibido {actual_mb:.1f} MB",
            )

    def _validate_not_html_masquerade(
        self,
        filename: str,
        content: bytes,
        user_id: str | None,
        clinic_id: str | None,
    ) -> None:
        """Detect HTML content masquerading as other file types."""
        content_start = content[:100].lower()
        is_html = (
            content_start.startswith(b"<!doctype html")
            or content_start.startswith(b"<html")
            or (content_start.startswith(b"<?xml") and b"<html" in content_start)
        )

        if is_html and not filename.lower().endswith((".html", ".htm")):
            logger.error(
                "UPLOAD_REJECTED_HTML_MASQUERADE",
                filename=filename,
                actual_content_start=content[:50].decode("utf-8", errors="replace"),
            )
            self._log_rejection(
                "html_masquerade",
                filename,
                user_id,
                clinic_id,
                {"content_start": content[:50].decode("utf-8", errors="replace")},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error de navegador: Se recibio HTML en lugar del archivo. "
                "Intenta recargar la pagina y subir el archivo nuevamente.",
            )

    def _validate_magic_bytes(
        self,
        filename: str,
        content: bytes,
        user_id: str | None,
        clinic_id: str | None,
    ) -> None:
        """Validate magic bytes for known file types."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext in MAGIC_BYTES:
            expected_magic, error_msg = MAGIC_BYTES[ext]
            if not content.startswith(expected_magic):
                logger.error(
                    "UPLOAD_REJECTED_INVALID_MAGIC_BYTES",
                    filename=filename,
                    ext=ext,
                    expected=expected_magic.hex(),
                    actual=content[:10].hex(),
                )
                self._log_rejection(
                    "invalid_magic_bytes",
                    filename,
                    user_id,
                    clinic_id,
                    {
                        "extension": ext,
                        "expected_magic": expected_magic.hex(),
                        "actual_magic": content[:10].hex(),
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Archivo corrupto: {error_msg}",
                )
