"""Discord attachment processing for Claude API multimodal messages.

Classifies attachments by type and turns each into a content block that
carries a REFERENCE — the signed Discord CDN URL — never the bytes
(aire-server #50, the Claim Check). AIRE fetches it (SSRF-pinned), shrinks an
image to <= 2000 px, and detects a document's type (PDF by its magic bytes,
anything else must be text), so this module downloads nothing, base64s
nothing and compresses nothing. Every cap it keeps is the one AIRE enforces,
refused here in character instead of as a 422 that kills the turn.

Each supported type has its own handler. Adding a new type means
adding a handler class and registering it once — no edits to
`process_attachment` or to the classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

import structlog

log = structlog.get_logger()

MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5MB — the legacy classify_attachment contract

# What AIRE's fetch accepts (aire-server engine/fetch.py MAX_FETCH_BYTES,
# Discord's free upload cap) — images and PDFs alike.
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_PDF_SIZE = MAX_IMAGE_SIZE

# AIRE refuses a text document over 200k chars (engine/documents.py); a byte
# never decodes to more than one char, so 200 KB is a cap that can't overshoot.
MAX_TEXT_SIZE = 200_000

# AIRE's door takes at most 4 images and 4 documents per turn (engine/vision.py,
# engine/documents.py); beyond that the extras are cut here, never sent.
MAX_IMAGES_PER_MESSAGE = 4
MAX_DOCUMENTS_PER_MESSAGE = 4


class AttachmentType(Enum):
    IMAGE = "image"
    TEXT = "text"
    PDF = "pdf"
    UNSUPPORTED = "unsupported"


@dataclass
class ProcessedAttachment:
    """A Discord attachment processed and ready for Claude API."""

    attachment_type: AttachmentType
    filename: str
    content_block: dict | None  # Claude API content block, None if unsupported
    error: str | None = None  # Error message if processing failed


# ---------------------------------------------------------------------------
# Type handlers
# ---------------------------------------------------------------------------


class _Handler:
    """Base for type-specific handlers.

    Subclasses declare which extensions they own, the largest file AIRE will
    take for them, and the reference block they ride as. Handlers don't deal
    with refusals or logging — those live in `process_attachment`.
    """

    attachment_type: ClassVar[AttachmentType]
    extensions: ClassVar[set[str]]
    max_size: ClassVar[int]

    def reference_block(self, url: str, filename: str) -> dict:
        """The content block that carries this file's signed URL."""
        raise NotImplementedError


class _DocumentHandler(_Handler):
    def reference_block(self, url: str, filename: str) -> dict:
        """A URL-source document block; AIRE decides whether it is a PDF or text."""
        return {"type": "document", "source": {"type": "url", "url": url}, "title": filename}


class ImageHandler(_Handler):
    attachment_type: ClassVar[AttachmentType] = AttachmentType.IMAGE
    extensions: ClassVar[set[str]] = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    max_size: ClassVar[int] = MAX_IMAGE_SIZE

    def reference_block(self, url: str, filename: str) -> dict:
        """The Anthropic URL-source image block; AIRE fetches and types it."""
        return {"type": "image", "source": {"type": "url", "url": url}}


class TextHandler(_DocumentHandler):
    attachment_type: ClassVar[AttachmentType] = AttachmentType.TEXT
    max_size: ClassVar[int] = MAX_TEXT_SIZE
    extensions: ClassVar[set[str]] = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".html",
        ".css",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".md",
        ".txt",
        ".csv",
        ".log",
        ".sh",
        ".bash",
        ".zsh",
        ".sql",
        ".xml",
        ".ini",
        ".cfg",
        ".env",
        ".rs",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".r",
        ".lua",
        ".dockerfile",
    }


class PDFHandler(_DocumentHandler):
    attachment_type: ClassVar[AttachmentType] = AttachmentType.PDF
    extensions: ClassVar[set[str]] = {".pdf"}
    max_size: ClassVar[int] = MAX_PDF_SIZE


# Registry — extension lookup walks this in order. New types: append a
# handler instance here and that's it.
_HANDLERS: list[_Handler] = [ImageHandler(), TextHandler(), PDFHandler()]
_TEXT_HANDLER: TextHandler = next(h for h in _HANDLERS if isinstance(h, TextHandler))

# Backwards-compatible exports — older callers and tests import these
# constants directly. Keep them in sync with the handler registry.
IMAGE_EXTENSIONS = ImageHandler.extensions
TEXT_EXTENSIONS = TextHandler.extensions
PDF_EXTENSIONS = PDFHandler.extensions


def _handler_for(filename: str, content_type: str | None) -> _Handler | None:
    """Pick the handler that owns this file, or None if unsupported.

    Extension match wins; the ``text/*`` content-type fallback rescues
    text files with unknown extensions (e.g. ``data.unknown`` served
    with ``Content-Type: text/plain``) — see test_text_content_type_fallback.
    """
    ext = _get_extension(filename)
    for h in _HANDLERS:
        if ext in h.extensions:
            return h
    if content_type and content_type.startswith("text/"):
        return _TEXT_HANDLER
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_attachment(
    filename: str,
    content_type: str | None,
    size: int,
    *,
    enforce_size_limit: bool = True,
) -> tuple[AttachmentType, str | None]:
    """Classify a Discord attachment by type. Returns (type, error_or_none).

    ``enforce_size_limit=True`` (default) keeps the legacy contract: anything
    over 5 MB is UNSUPPORTED. ``process_attachment`` calls with
    ``enforce_size_limit=False`` because images have their own cap
    (``MAX_IMAGE_SIZE``) and ride by reference to AIRE, which shrinks them.
    """
    if enforce_size_limit and size > MAX_ATTACHMENT_SIZE:
        return AttachmentType.UNSUPPORTED, f"Archivo muy pesado ({size / 1024 / 1024:.1f}MB). Maximo 5MB."

    handler = _handler_for(filename, content_type)
    if handler is not None:
        return handler.attachment_type, None

    ext = _get_extension(filename)
    return AttachmentType.UNSUPPORTED, f"No puedo leer archivos .{ext}. Mandame texto, codigo, imagenes o PDFs."


def _rejected(att_type: AttachmentType, filename: str, error: str, **fields) -> ProcessedAttachment:
    log.warning("attachment_rejected", filename=filename, reason=error, **fields)
    return ProcessedAttachment(attachment_type=att_type, filename=filename, content_block=None, error=error)


def _mb(size: int) -> str:
    return f"{size / 1024 / 1024:.1f}MB" if size >= 1024 * 1024 else f"{size // 1024}KB"


def _reference(attachment, handler: _Handler, att_type: AttachmentType) -> ProcessedAttachment:
    """No attachment downloads here: its signed URL rides to AIRE (#50)."""
    filename = attachment.filename
    if attachment.size > handler.max_size:
        return _rejected(
            att_type,
            filename,
            f"Archivo muy pesado ({_mb(attachment.size)}). Maximo {_mb(handler.max_size)}.",
            size=attachment.size,
        )
    url = getattr(attachment, "url", None)
    if not url:
        return _rejected(att_type, filename, "No pude leer el archivo. Intentale de nuevo.")
    log.info("attachment_processed", filename=filename, type=att_type.value, size=attachment.size, by="reference")
    return ProcessedAttachment(
        attachment_type=att_type, filename=filename, content_block=handler.reference_block(url, filename)
    )


async def process_attachment(attachment) -> ProcessedAttachment:
    """Process a single discord.Attachment into a reference content block.

    Every supported type rides as its signed URL (images and documents alike);
    every refusal carries an in-character error for the channel.
    """
    filename = attachment.filename
    att_type, type_error = classify_attachment(
        filename, attachment.content_type, attachment.size, enforce_size_limit=False
    )
    if type_error:
        return _rejected(att_type, filename, type_error)
    handler = _handler_for(filename, attachment.content_type)
    if handler is None:
        return _rejected(att_type, filename, "Tipo de archivo no soportado.")
    return _reference(attachment, handler, att_type)


def cap_documents(attachments: list, max_documents: int = MAX_DOCUMENTS_PER_MESSAGE) -> tuple[list, list[str]]:
    """Keep the first ``max_documents`` text/PDF attachments (and everything
    else), in order. Returns ``(kept, dropped_filenames)``: AIRE refuses the
    whole turn over its cap, so the extras are cut and named, never sent."""
    kept: list = []
    dropped: list[str] = []
    docs = 0
    for att in attachments:
        if isinstance(_handler_for(att.filename, att.content_type), _DocumentHandler):
            if docs >= max_documents:
                dropped.append(att.filename)
                continue
            docs += 1
        kept.append(att)
    return kept, dropped


def cap_images(attachments: list, max_images: int = MAX_IMAGES_PER_MESSAGE) -> tuple[list, int]:
    """Keep the first ``max_images`` image attachments (and every non-image), in order.

    Returns ``(kept, dropped)``. AIRE refuses the whole turn over its image cap,
    so the extras are cut here and the persona says so in its own voice
    (``prompts_md/images_over_cap_note.md``). Rescued from PR #97."""
    kept: list = []
    images = dropped = 0
    for att in attachments:
        if isinstance(_handler_for(att.filename, att.content_type), ImageHandler):
            if images >= max_images:
                dropped += 1
                continue
            images += 1
        kept.append(att)
    return kept, dropped


async def process_attachments(attachments: list) -> tuple[list[dict], list[str]]:
    """Process multiple Discord attachments.

    Returns:
        (content_blocks, errors) — content blocks for Claude API and in-character error messages.
    """
    blocks: list[dict] = []
    errors: list[str] = []
    for att in attachments:
        result = await process_attachment(att)
        if result.content_block:
            blocks.append(result.content_block)
        if result.error:
            errors.append(f"**{result.filename}**: {result.error}")
    return blocks, errors


def _get_extension(filename: str) -> str:
    """Get lowercase file extension including the dot."""
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        return ""
    return filename[dot_idx:].lower()
