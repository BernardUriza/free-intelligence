"""Tests for khimeras_shared.attachments — file classification and processing."""

import io
from unittest.mock import AsyncMock

from khimeras_shared.attachments import (
    MAX_ATTACHMENT_SIZE,
    AttachmentType,
    classify_attachment,
    process_attachment,
    process_attachments,
)

# --- Classification ---


class TestClassifyAttachment:
    def test_png_image(self):
        att_type, error = classify_attachment("screenshot.png", "image/png", 1000)
        assert att_type == AttachmentType.IMAGE
        assert error is None

    def test_jpg_image(self):
        att_type, _ = classify_attachment("photo.jpg", "image/jpeg", 1000)
        assert att_type == AttachmentType.IMAGE

    def test_webp_image(self):
        att_type, _ = classify_attachment("sticker.webp", "image/webp", 1000)
        assert att_type == AttachmentType.IMAGE

    def test_python_file(self):
        att_type, _ = classify_attachment("main.py", "text/plain", 500)
        assert att_type == AttachmentType.TEXT

    def test_javascript_file(self):
        att_type, _ = classify_attachment("app.js", "application/javascript", 500)
        assert att_type == AttachmentType.TEXT

    def test_json_file(self):
        att_type, _ = classify_attachment("config.json", "application/json", 500)
        assert att_type == AttachmentType.TEXT

    def test_txt_file(self):
        att_type, _ = classify_attachment("notes.txt", "text/plain", 500)
        assert att_type == AttachmentType.TEXT

    def test_csv_file(self):
        att_type, _ = classify_attachment("data.csv", "text/csv", 500)
        assert att_type == AttachmentType.TEXT

    def test_pdf_file(self):
        att_type, _ = classify_attachment("document.pdf", "application/pdf", 1000)
        assert att_type == AttachmentType.PDF

    def test_unsupported_mp3(self):
        att_type, error = classify_attachment("song.mp3", "audio/mpeg", 1000)
        assert att_type == AttachmentType.UNSUPPORTED
        assert error is not None

    def test_unsupported_zip(self):
        att_type, error = classify_attachment("archive.zip", "application/zip", 1000)
        assert att_type == AttachmentType.UNSUPPORTED
        assert error is not None

    def test_too_large(self):
        att_type, error = classify_attachment("big.png", "image/png", MAX_ATTACHMENT_SIZE + 1)
        assert att_type == AttachmentType.UNSUPPORTED
        assert "5MB" in error

    def test_exactly_at_limit(self):
        att_type, error = classify_attachment("ok.png", "image/png", MAX_ATTACHMENT_SIZE)
        assert att_type == AttachmentType.IMAGE
        assert error is None

    def test_text_content_type_fallback(self):
        """Files with text/ content type should be treated as text even with unknown extension."""
        att_type, _ = classify_attachment("data.unknown", "text/plain", 500)
        assert att_type == AttachmentType.TEXT

    def test_no_extension(self):
        att_type, _error = classify_attachment("Makefile", None, 500)
        assert att_type == AttachmentType.UNSUPPORTED


# --- Processing ---


def _mock_attachment(filename: str, content_type: str, size: int, data: bytes):
    att = AsyncMock()
    att.filename = filename
    att.content_type = content_type
    att.size = size
    att.read = AsyncMock(return_value=data)
    return att


class TestProcessAttachment:
    async def test_process_image(self):
        att = _mock_attachment("test.png", "image/png", 100, b"\x89PNG fake image data")
        result = await process_attachment(att)
        assert result.attachment_type == AttachmentType.IMAGE
        assert result.content_block is not None
        assert result.content_block["type"] == "image"
        assert result.content_block["source"]["media_type"] == "image/png"
        assert result.error is None

    async def test_process_text(self):
        """v3.9.59 fix: text files emit a `document` block (not `text`)
        so they don't get concatenated into the agent runner's user_text
        (which had an 8000-char cap; Bernard 21KB paste hit 422)."""
        att = _mock_attachment("hello.py", "text/plain", 20, b"print('hello')")
        result = await process_attachment(att)
        assert result.attachment_type == AttachmentType.TEXT
        assert result.content_block is not None
        assert result.content_block["type"] == "document"
        assert result.content_block["source"]["type"] == "text"
        assert result.content_block["source"]["media_type"] == "text/plain"
        assert result.content_block["source"]["data"] == "print('hello')"
        assert result.content_block["title"] == "hello.py"

    async def test_process_pdf(self):
        att = _mock_attachment("doc.pdf", "application/pdf", 100, b"%PDF-1.4 fake")
        result = await process_attachment(att)
        assert result.attachment_type == AttachmentType.PDF
        assert result.content_block is not None
        assert result.content_block["type"] == "document"
        assert result.content_block["source"]["media_type"] == "application/pdf"

    async def test_process_unsupported(self):
        att = _mock_attachment("song.mp3", "audio/mpeg", 100, b"fake audio")
        result = await process_attachment(att)
        assert result.content_block is None
        assert result.error is not None

    async def test_process_too_large_text(self):
        # Non-images over 5 MB still hard-reject (no compression path).
        att = _mock_attachment("huge.txt", "text/plain", MAX_ATTACHMENT_SIZE + 1, b"")
        result = await process_attachment(att)
        assert result.content_block is None
        assert "5MB" in (result.error or "")

    async def test_process_download_failure(self):
        att = _mock_attachment("fail.png", "image/png", 100, b"")
        att.read = AsyncMock(side_effect=Exception("Network error"))
        result = await process_attachment(att)
        assert result.content_block is None
        assert result.error is not None

    async def test_text_latin1_fallback(self):
        att = _mock_attachment("legacy.txt", "text/plain", 10, "café".encode("latin-1"))
        result = await process_attachment(att)
        assert result.content_block is not None
        assert result.content_block["type"] == "document"
        # The decoded text now lives in source.data (v3.9.59).
        assert "café" in result.content_block["source"]["data"]


def _build_real_jpeg(width: int, height: int) -> bytes:
    """Build a real JPEG of the given dimensions for compression tests."""
    from PIL import Image

    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    # Add some entropy so quality steps actually change the size
    pixels = img.load()
    for y in range(0, height, 7):
        for x in range(0, width, 11):
            pixels[x, y] = ((x * 7) % 255, (y * 11) % 255, (x + y) % 255)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=100)
    return buf.getvalue()


class TestImageCompression:
    """Phase 2026-04-26: oversize images are compressed before reject."""

    async def test_oversize_image_compressed_to_under_cap(self):
        # 4000x3000 high-quality JPEG — typically ~5-7 MB raw
        data = _build_real_jpeg(4000, 3000)
        # Real Discord attachment object reports raw size; we mock it
        att = _mock_attachment("photo.jpg", "image/jpeg", len(data), data)
        result = await process_attachment(att)
        assert result.attachment_type == AttachmentType.IMAGE
        assert result.content_block is not None
        assert result.error is None
        # Decode the base64 — must fit under the 5 MB cap after compression
        import base64

        compressed_bytes = base64.standard_b64decode(result.content_block["source"]["data"])
        assert len(compressed_bytes) <= MAX_ATTACHMENT_SIZE
        # Compressed images are always returned as JPEG regardless of input
        assert result.content_block["source"]["media_type"] == "image/jpeg"

    async def test_image_under_cap_passes_through_uncompressed(self):
        # Small image — must NOT be re-encoded (no quality loss for users
        # sending normal-sized screenshots/uploads)
        small = _build_real_jpeg(100, 100)
        assert len(small) < MAX_ATTACHMENT_SIZE
        att = _mock_attachment("small.jpg", "image/jpeg", len(small), small)
        result = await process_attachment(att)
        assert result.content_block is not None
        assert result.error is None
        # Bytes match the original — no re-encoding when under the cap
        import base64

        passthrough = base64.standard_b64decode(result.content_block["source"]["data"])
        assert passthrough == small

    async def test_oversize_non_image_still_rejected(self):
        # Text files don't get a compression path
        big_text = b"x" * (MAX_ATTACHMENT_SIZE + 100)
        att = _mock_attachment("big.py", "text/plain", len(big_text), big_text)
        result = await process_attachment(att)
        assert result.content_block is None
        assert "Maximo 5MB" in (result.error or "")

    async def test_huge_image_above_hard_limit_rejected_without_download(self):
        # Beyond 25 MB we don't even try to download
        att = _mock_attachment("huge.jpg", "image/jpeg", 30 * 1024 * 1024, b"")
        result = await process_attachment(att)
        assert result.content_block is None
        assert "25MB" in (result.error or "")
        # Confirm we never downloaded it
        att.read.assert_not_awaited()

    async def test_gif_oversize_rejected_no_compression(self):
        # GIFs aren't compressed (animation would be lost). Use raw bytes >5MB
        # — the .gif extension makes _compress_image bail before decoding.
        data = b"GIF89a" + b"\x00" * (MAX_ATTACHMENT_SIZE + 100)
        att = _mock_attachment("animation.gif", "image/gif", len(data), data)
        result = await process_attachment(att)
        assert result.content_block is None
        assert "no se comprime" in (result.error or "").lower() or "maximo" in (result.error or "").lower()

    async def test_png_with_alpha_compressed_flattens_to_jpeg(self):
        from PIL import Image

        # Create a real oversize PNG with transparency
        img = Image.new("RGBA", (3000, 3000), color=(100, 200, 50, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()
        if len(data) <= MAX_ATTACHMENT_SIZE:
            # Pad with random data isn't an option; build a noisier image
            pixels = img.load()
            for y in range(img.size[1]):
                for x in range(img.size[0]):
                    pixels[x, y] = ((x * 13) % 255, (y * 17) % 255, (x + y) % 255, 128)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            data = buf.getvalue()

        if len(data) > MAX_ATTACHMENT_SIZE:
            att = _mock_attachment("transparent.png", "image/png", len(data), data)
            result = await process_attachment(att)
            assert result.content_block is not None
            # PNG with alpha compressed to JPEG — media_type must reflect that
            assert result.content_block["source"]["media_type"] == "image/jpeg"


class TestProcessAttachments:
    async def test_multiple_attachments(self):
        atts = [
            _mock_attachment("code.py", "text/plain", 20, b"x = 1"),
            _mock_attachment("screenshot.png", "image/png", 100, b"\x89PNG data"),
        ]
        blocks, errors = await process_attachments(atts)
        assert len(blocks) == 2
        assert len(errors) == 0

    async def test_mixed_valid_and_invalid(self):
        atts = [
            _mock_attachment("code.py", "text/plain", 20, b"x = 1"),
            _mock_attachment("song.mp3", "audio/mpeg", 100, b"audio"),
        ]
        blocks, errors = await process_attachments(atts)
        assert len(blocks) == 1  # only code.py
        assert len(errors) == 1  # mp3 rejected

    async def test_empty_list(self):
        blocks, errors = await process_attachments([])
        assert blocks == []
        assert errors == []
