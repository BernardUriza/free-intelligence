"""Discord attachment processing for Claude API multimodal messages.

Classifies attachments by type, downloads content, and converts
to Claude API content blocks (text, image, document).

Each supported type has its own handler. Adding a new type means
adding a handler class and registering it once — no edits to
`process_attachment` or to the classifier.

Images travel BY REFERENCE (aire-server #50): the block carries the signed
Discord CDN URL, never the bytes. AIRE fetches it (SSRF-pinned), shrinks it
to <= 2000 px and detects its type, so this module no longer downloads,
compresses or base64s a single image — the cap on image bytes has ONE owner,
AIRE. Only text files and PDFs are still downloaded here.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

import structlog

log = structlog.get_logger()

MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5MB — Claude API per-attachment cap

# What AIRE's image fetch accepts (aire-server engine/fetch.py MAX_FETCH_BYTES,
# Discord's free upload cap); refused here in character instead of as a 422.
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# AIRE's door takes at most 4 images per turn (engine/vision.py MAX_IMAGES);
# beyond that the extras are named in character instead of killing the turn.
MAX_IMAGES_PER_MESSAGE = 4

# Hard upper bound on what we even download (text/PDF only).
HARD_DOWNLOAD_LIMIT = 25 * 1024 * 1024  # 25MB


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

    Subclasses declare which extensions they own and how to turn raw bytes
    into a Claude API content block. Handlers don't deal with download
    failures, size limits, or logging — those live in `process_attachment`
    so each handler stays a pure transform.
    """

    attachment_type: ClassVar[AttachmentType]
    extensions: ClassVar[set[str]]

    def build_block(self, data: bytes, filename: str) -> tuple[dict | None, str | None]:
        """Convert downloaded bytes to a content block.

        Returns ``(block, error)``. ``block`` is None when ``data`` can't be
        rendered (e.g. text that's neither UTF-8 nor latin-1).
        """
        raise NotImplementedError


class ImageHandler(_Handler):
    attachment_type: ClassVar[AttachmentType] = AttachmentType.IMAGE
    extensions: ClassVar[set[str]] = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    # Claude API supported image media types
    media_types: ClassVar[dict[str, str]] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    def build_block(self, data: bytes, filename: str) -> tuple[dict | None, str | None]:
        raise TypeError("images travel by reference; use ImageHandler.reference_block")

    @staticmethod
    def reference_block(url: str) -> dict:
        """The Anthropic URL-source image block; AIRE fetches and types it."""
        return {"type": "image", "source": {"type": "url", "url": url}}


class TextHandler(_Handler):
    attachment_type: ClassVar[AttachmentType] = AttachmentType.TEXT
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

    def build_block(self, data: bytes, filename: str) -> tuple[dict | None, str | None]:
        """Return an Anthropic ``document`` block — NOT a text block.

        Pre-v3.9.59 this returned ``{type: "text", text: "[Archivo: ...]\\n..."}``
        which got concatenated into the agent runner's ``user_text`` field and
        blew its 8000-char cap with even modest attachments (Bernard 21KB
        message.txt incident, 2026-05-19 07:06 → 422 → ALICE failover with no
        attachment context).

        Returning a proper document block routes the file through the same
        dedicated ``attachments`` channel that images use (REWRITE-B1,
        v3.9.43). The agent sees a real document the LLM can choose to
        process. The Anthropic API supports text-source documents natively
        (matching the PDFHandler shape below, just with `type: "text"`
        instead of base64).
        """
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
            except Exception:
                return None, "No pude leer el archivo. Parece que no es texto."
        return {
            "type": "document",
            "source": {
                "type": "text",
                "media_type": "text/plain",
                "data": text,
            },
            "title": filename,
            "context": f"File the user attached in chat: {filename}",
        }, None


class PDFHandler(_Handler):
    attachment_type: ClassVar[AttachmentType] = AttachmentType.PDF
    extensions: ClassVar[set[str]] = {".pdf"}

    def build_block(self, data: bytes, filename: str) -> tuple[dict | None, str | None]:
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(data).decode("ascii"),
            },
        }, None


# Registry — extension lookup walks this in order. New types: append a
# handler instance here and that's it.
_HANDLERS: list[_Handler] = [ImageHandler(), TextHandler(), PDFHandler()]
_TEXT_HANDLER: TextHandler = next(h for h in _HANDLERS if isinstance(h, TextHandler))

# Backwards-compatible exports — older callers and tests import these
# constants directly. Keep them in sync with the handler registry.
IMAGE_EXTENSIONS = ImageHandler.extensions
TEXT_EXTENSIONS = TextHandler.extensions
PDF_EXTENSIONS = PDFHandler.extensions
IMAGE_MEDIA_TYPES = ImageHandler.media_types


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


def _image_reference(attachment, att_type: AttachmentType) -> ProcessedAttachment:
    """An image never downloads here: its signed URL rides to AIRE (#50)."""
    filename = attachment.filename
    if attachment.size > MAX_IMAGE_SIZE:
        return _rejected(
            att_type,
            filename,
            f"Imagen muy pesada ({attachment.size / 1024 / 1024:.1f}MB). Maximo 10MB.",
            size=attachment.size,
        )
    url = getattr(attachment, "url", None)
    if not url:
        return _rejected(att_type, filename, "No pude leer la imagen. Intentale de nuevo.")
    log.info("attachment_processed", filename=filename, type=att_type.value, size=attachment.size, by="reference")
    return ProcessedAttachment(
        attachment_type=att_type, filename=filename, content_block=ImageHandler.reference_block(url)
    )


async def process_attachment(attachment) -> ProcessedAttachment:
    """Process a single discord.Attachment into a Claude API content block.

    Images become URL references (no download); text and PDFs are downloaded
    and inlined, capped at ``MAX_ATTACHMENT_SIZE``. Every refusal carries an
    in-character error for the channel.
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
    if isinstance(handler, ImageHandler):
        return _image_reference(attachment, att_type)
    if attachment.size > MAX_ATTACHMENT_SIZE:
        return _rejected(att_type, filename, f"Archivo muy pesado ({attachment.size / 1024 / 1024:.1f}MB). Maximo 5MB.")
    try:
        data = await attachment.read()
    except Exception as e:
        log.error("attachment_download_failed", filename=filename, error=str(e))
        return ProcessedAttachment(
            attachment_type=att_type,
            filename=filename,
            content_block=None,
            error="No pude descargar el archivo. Intentale de nuevo.",
        )
    block, build_error = handler.build_block(data, filename)
    if build_error or block is None:
        return ProcessedAttachment(attachment_type=att_type, filename=filename, content_block=None, error=build_error)
    log.info("attachment_processed", filename=filename, type=att_type.value, size=len(data))
    return ProcessedAttachment(attachment_type=att_type, filename=filename, content_block=block)


async def process_attachments(attachments: list) -> tuple[list[dict], list[str]]:
    """Process multiple Discord attachments.

    Returns:
        (content_blocks, errors) — content blocks for Claude API and in-character error messages.
        Images past ``MAX_IMAGES_PER_MESSAGE`` are skipped and named, never sent: AIRE
        refuses the whole turn over its cap.
    """
    blocks: list[dict] = []
    errors: list[str] = []
    skipped: list[str] = []
    images = 0
    for att in attachments:
        result = await process_attachment(att)
        block = result.content_block
        if block and block.get("type") == "image":
            images += 1
            if images > MAX_IMAGES_PER_MESSAGE:
                skipped.append(result.filename)
                continue
        if block:
            blocks.append(block)
        if result.error:
            errors.append(f"**{result.filename}**: {result.error}")
    if skipped:
        errors.append(
            f"Solo veo {MAX_IMAGES_PER_MESSAGE} imagenes por mensaje; no vi: {', '.join(skipped)}. "
            "Mandalas en otro mensaje."
        )
    return blocks, errors


def _get_extension(filename: str) -> str:
    """Get lowercase file extension including the dot."""
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        return ""
    return filename[dot_idx:].lower()
