"""Text extraction service for document uploads.

Extracts text content from PDF, DOCX, TXT, and MD files.
Integrates with audit service for error logging.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile, status

from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.api.audit.dependencies import DIAuditService

logger = get_logger(__name__)


class TextExtractor:
    """Extracts text content from uploaded files.

    Supports: TXT, MD, PDF, DOCX

    Single Responsibility: Only handles text extraction logic.
    """

    SUPPORTED_EXTENSIONS = frozenset({"txt", "md", "pdf", "docx"})

    def __init__(self, audit_service: "DIAuditService | None" = None) -> None:
        self.audit_service = audit_service

    def extract(
        self,
        file: UploadFile,
        content: bytes,
        user_id: str | None = None,
        clinic_id: str | None = None,
    ) -> str:
        """Extract text content from uploaded file.

        Args:
            file: Uploaded file metadata
            content: File binary content
            user_id: Optional user ID for audit logging
            clinic_id: Optional clinic ID for audit logging

        Returns:
            Extracted text content

        Raises:
            HTTPException: If text extraction fails
        """
        filename = file.filename or "unknown"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        try:
            if ext in ("txt", "md"):
                return self._extract_plain_text(content)
            elif ext == "pdf":
                return self._extract_pdf(content, filename, user_id, clinic_id)
            elif ext == "docx":
                return self._extract_docx(content, filename, user_id, clinic_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Formato no soportado: .{ext}. "
                    f"Formatos validos: TXT, MD, PDF, DOCX",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("TEXT_EXTRACTION_ERROR", filename=filename, error=str(e))
            self._log_extraction_failure(filename, ext, str(e), user_id, clinic_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar archivo: {str(e)}",
            )

    def _log_extraction_failure(
        self,
        filename: str,
        file_type: str,
        error: str,
        user_id: str | None,
        clinic_id: str | None,
    ) -> None:
        """Log extraction failure to audit service."""
        if self.audit_service and user_id:
            self.audit_service.log_action(
                action="document_extraction_failed",
                user_id=user_id,
                clinic_id=clinic_id,
                resource=filename,
                result="failure",
                details={"file_type": file_type or "unknown", "error": error},
            )

    def _extract_plain_text(self, content: bytes) -> str:
        """Extract text from plain text files."""
        return content.decode("utf-8")

    def _extract_pdf(
        self,
        content: bytes,
        filename: str,
        user_id: str | None,
        clinic_id: str | None,
    ) -> str:
        """Extract text from PDF files."""
        try:
            import PyPDF2
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF processing not available (PyPDF2 not installed)",
            )

        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
            return text.strip()
        except Exception as e:
            logger.error("PDF_EXTRACTION_ERROR", filename=filename, error=str(e))
            self._log_extraction_failure(filename, "pdf", str(e), user_id, clinic_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo extraer texto del PDF: {str(e)}",
            )

    def _extract_docx(
        self,
        content: bytes,
        filename: str,
        user_id: str | None,
        clinic_id: str | None,
    ) -> str:
        """Extract text from DOCX files."""
        try:
            import docx
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="DOCX processing not available (python-docx not installed)",
            )

        try:
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            text = "\n\n".join([para.text for para in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error("DOCX_EXTRACTION_ERROR", filename=filename, error=str(e))
            self._log_extraction_failure(filename, "docx", str(e), user_id, clinic_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo extraer texto del DOCX: {str(e)}",
            )
