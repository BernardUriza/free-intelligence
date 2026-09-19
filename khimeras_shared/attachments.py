"""Discord attachment processing for Claude API multimodal messages.

Classifies attachments by type, downloads content, and converts
to Claude API content blocks (text, image, document).

Each supported type has its own handler. Adding a new type means
adding a handler class and registering it once — no edits to
`process_attachment` or to the classifier.

Image-size handling: phone cameras routinely produce 5-12 MB JPEGs that
exceed Claude's 5 MB per-attachment cap. Rather than reject those, we
attempt compression: resize to max-2048px on the long edge, save as
JPEG at progressively lower quality (85→75→65→55) until the bytes fit.
PNGs with transparency get flattened to white. Non-images and images
that don't shrink below the cap after the lowest quality pass are still
rejected with an in-character error.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

import structlog

log = structlog.get_logger()

MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5MB — Claude API per-attachment cap

# Images travel base64-encoded and the AIRE door rejects >5,000,000 chars (422),
# so the image budget is the RAW size whose base64 fits: 3,750,000 bytes.
MAX_IMAGE_B64_CHARS = 5_000_000
MAX_IMAGE_BYTES = MAX_IMAGE_B64_CHARS * 3 // 4

# Hard upper bound on what we even download. Beyond this, compression won't
# salvage the file (and downloading 50 MB just to fail wastes egress).
HARD_DOWNLOAD_LIMIT = 25 * 1024 * 1024  # 25MB

# Compression target: long-edge pixel dimension after resize. 2048 keeps
# enough fidelity for screenshots / photos without producing files that
# blow past the 5 MB cap on the first pass.
COMPRESS_LONG_EDGE = 2048

# Quality steps we try in order. JPEG q=85 is visually lossless for most
# inputs; we step down only if the previous pass still exceeded the cap.
COMPRESS_QUALITY_STEPS = (85, 75, 65, 55)


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
        ext = _get_extension(filename)
        media_type = self.media_types.get(ext, "image/png")
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(data).decode("ascii"),
            },
        }, None


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
    ``enforce_size_limit=False`` because images larger than 5 MB now go through
    a compression pass before being rejected.
    """
    if enforce_size_limit and size > MAX_ATTACHMENT_SIZE:
        return AttachmentType.UNSUPPORTED, f"Archivo muy pesado ({size / 1024 / 1024:.1f}MB). Maximo 5MB."

    handler = _handler_for(filename, content_type)
    if handler is not None:
        return handler.attachment_type, None

    ext = _get_extension(filename)
    return AttachmentType.UNSUPPORTED, f"No puedo leer archivos .{ext}. Mandame texto, codigo, imagenes o PDFs."


def _compress_image(data: bytes, filename: str) -> tuple[bytes, str] | None:
    """Resize + re-encode an oversize image so it fits under ``MAX_IMAGE_BYTES``.

    Returns ``(compressed_bytes, jpeg_media_type)`` on success, or ``None`` if
    even the lowest-quality JPEG pass still exceeds the cap. The resulting
    bytes are always JPEG — even PNG/WebP inputs — because JPEG gives the
    best size-vs-quality ratio for the photo/screenshot content that triggers
    this path. Transparency is flattened to white.

    GIFs are not compressed (animation would be lost); the caller still gets
    None and reports the size to the user, who can convert manually.
    """
    try:
        from PIL import Image
    except ImportError:
        log.warning("attachment_pillow_missing", hint="pip install Pillow")
        return None

    ext = _get_extension(filename)
    if ext == ".gif":
        # Compressing animations to a single JPEG frame is worse than rejecting.
        return None

    try:
        img = Image.open(io.BytesIO(data))
        img.load()  # fully decode now so we surface format errors here
    except Exception as e:
        log.warning("attachment_compress_decode_failed", filename=filename, error=str(e))
        return None

    # Resize on the long edge if needed
    long_edge = max(img.size)
    if long_edge > COMPRESS_LONG_EDGE:
        scale = COMPRESS_LONG_EDGE / long_edge
        new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Flatten transparency onto white — JPEG has no alpha.
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Try progressively lower JPEG quality until it fits
    for quality in COMPRESS_QUALITY_STEPS:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        compressed = buf.getvalue()
        if len(compressed) <= MAX_IMAGE_BYTES:
            log.info(
                "attachment_compressed",
                filename=filename,
                before=len(data),
                after=len(compressed),
                quality=quality,
                final_dimensions=img.size,
            )
            return compressed, "image/jpeg"

    log.warning(
        "attachment_compress_exhausted",
        filename=filename,
        before=len(data),
        last_quality=COMPRESS_QUALITY_STEPS[-1],
    )
    return None


async def process_attachment(attachment) -> ProcessedAttachment:
    """Process a single discord.Attachment into a Claude API content block.

    Images exceeding ``MAX_ATTACHMENT_SIZE`` are compressed before being
    rejected — see ``_compress_image``. Non-images and images that don't
    fit even at the lowest JPEG quality fall through to the size-rejection
    branch with an in-character error.
    """
    filename = attachment.filename

    # Classify WITHOUT the size cap first — we need to know if it's an image
    # to decide whether to attempt compression.
    att_type, type_error = classify_attachment(
        filename, attachment.content_type, attachment.size, enforce_size_limit=False
    )

    if type_error:
        # Unsupported file type — never compressible regardless of size.
        log.warning("attachment_rejected", filename=filename, reason=type_error)
        return ProcessedAttachment(
            attachment_type=att_type,
            filename=filename,
            content_block=None,
            error=type_error,
        )

    handler = _handler_for(filename, attachment.content_type)
    if handler is None:
        return ProcessedAttachment(
            attachment_type=att_type,
            filename=filename,
            content_block=None,
            error="Tipo de archivo no soportado.",
        )

    is_image = isinstance(handler, ImageHandler)

    # Hard upper bound on what we even download.
    if attachment.size > HARD_DOWNLOAD_LIMIT:
        msg = f"Archivo muy pesado ({attachment.size / 1024 / 1024:.1f}MB). Maximo 25MB."
        log.warning("attachment_rejected", filename=filename, reason=msg, size=attachment.size)
        return ProcessedAttachment(
            attachment_type=att_type,
            filename=filename,
            content_block=None,
            error=msg,
        )

    # Non-images over the cap: no compression path, reject immediately.
    if not is_image and attachment.size > MAX_ATTACHMENT_SIZE:
        msg = f"Archivo muy pesado ({attachment.size / 1024 / 1024:.1f}MB). Maximo 5MB."
        log.warning("attachment_rejected", filename=filename, reason=msg)
        return ProcessedAttachment(
            attachment_type=att_type,
            filename=filename,
            content_block=None,
            error=msg,
        )

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

    # Image compression path — only fires when the downloaded bytes exceed
    # the cap. Images already under 5 MB skip this entirely (no quality loss).
    forced_media_type: str | None = None
    if is_image and len(data) > MAX_IMAGE_BYTES:
        result = _compress_image(data, filename)
        if result is None:
            msg = f"Imagen no se comprime lo suficiente ({len(data) / 1024 / 1024:.1f}MB). Mandala mas chica."
            log.warning("attachment_compress_failed", filename=filename, original_size=len(data))
            return ProcessedAttachment(
                attachment_type=att_type,
                filename=filename,
                content_block=None,
                error=msg,
            )
        data, forced_media_type = result

    block, build_error = handler.build_block(data, filename)
    if build_error or block is None:
        return ProcessedAttachment(
            attachment_type=att_type,
            filename=filename,
            content_block=None,
            error=build_error,
        )

    # Override media_type when compression converted the format (PNG → JPEG).
    if forced_media_type and isinstance(block.get("source"), dict):
        block["source"]["media_type"] = forced_media_type

    log.info("attachment_processed", filename=filename, type=att_type.value, size=len(data))
    return ProcessedAttachment(attachment_type=att_type, filename=filename, content_block=block)


async def process_attachments(attachments: list) -> tuple[list[dict], list[str]]:
    """Process multiple Discord attachments.

    Returns:
        (content_blocks, errors) — content blocks for Claude API and in-character error messages
    """
    blocks = []
    errors = []

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
