"""The turn's document attachments (#50 item 6) — PDFs and text files by
reference, the same Claim Check the images use.

A caller sends `documents: [{url, title?}]`; AIRE fetches each through the
SSRF-pinned `fetch.py` and builds the Anthropic `document` block itself. The
type is DETECTED, never taken from the caller: bytes that open with `%PDF-`
become a base64 PDF block; anything else must decode as text (UTF-8, latin-1 as
a fallback) or it is refused. Verified before this was built (2026-09-25): the
bundled CLI accepts both block shapes through streaming input and the model
read the PDF's text and the text file's content back verbatim.

One at a time, like the images: a 10 MiB PDF is the whole budget of this box's
spare RAM several times over once it is base64'd."""

import base64
from typing import Any

from .fetch import FetchRefused, fetch

MAX_DOCUMENTS = 4
MAX_TEXT_CHARS = 200_000  # ~50k tokens: every later turn of the session resends it
MAX_TITLE = 200
PDF_MAGIC = b"%PDF-"


class BadDocument(Exception):
    """A document the edge refuses — the message is the caller's 422 detail."""


def clean_documents(raw: Any) -> tuple[dict[str, str], ...]:
    """Validate the body's `documents` SHAPE: a list of `{url, title?}`."""
    if not raw:
        return ()
    if not isinstance(raw, list) or len(raw) > MAX_DOCUMENTS:
        raise BadDocument(f"documents must be a list of at most {MAX_DOCUMENTS}")
    return tuple(_clean_one(i, item) for i, item in enumerate(raw))


def _clean_one(i: int, item: Any) -> dict[str, str]:
    if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not item["url"]:
        raise BadDocument(f"document {i}: needs a url")
    title = item.get("title")
    clean = {"url": item["url"]}
    if isinstance(title, str) and title.strip():
        clean["title"] = title.strip()[:MAX_TITLE]
    return clean


def _text(raw: bytes, i: int) -> str:
    if b"\x00" in raw[:8192]:
        raise BadDocument(f"document {i}: neither a PDF nor text")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    if len(text) > MAX_TEXT_CHARS:
        raise BadDocument(f"document {i}: text over {MAX_TEXT_CHARS} chars; send a shorter file")
    return text


def to_block(raw: bytes, i: int, title: str | None = None) -> dict[str, Any]:
    """The Anthropic `document` block for these bytes, the type detected."""
    if raw.startswith(PDF_MAGIC):
        source = {"type": "base64", "media_type": "application/pdf",
                  "data": base64.b64encode(raw).decode()}
    else:
        source = {"type": "text", "media_type": "text/plain", "data": _text(raw, i)}
    block: dict[str, Any] = {"type": "document", "source": source}
    if title:
        block["title"] = title
    return block


async def prepare_documents(raw: Any) -> tuple[dict[str, Any], ...]:
    """Shape-check and fetch — sequentially, never four downloads at once."""
    blocks = []
    for i, item in enumerate(clean_documents(raw)):
        try:
            data = await fetch(item["url"])
        except FetchRefused as exc:
            raise BadDocument(f"document {i}: {exc}") from exc
        blocks.append(to_block(data, i, item.get("title")))
    return tuple(blocks)
