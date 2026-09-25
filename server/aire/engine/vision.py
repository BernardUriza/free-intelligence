"""The turn's image attachments (#29 gap 4, #50) — validated at the edge,
fetched and shrunk at the door, folded into the SDK's streaming-input mode.
Ported from fi-runner's ClaudeCodeBackend (`build_query_input` / `_query`).

An image arrives two ways: inline `{media_type, data}` (base64, no `data:`
prefix) or by reference `{url}` — a signed Discord CDN URL AIRE fetches itself
(`fetch.py`), so the bytes never ride the consumer's pipeline. Either way it
leaves through `shrink.normalize` (≤ 2000 px, media type detected), one image at
a time on a 512 MB box. Blocks ride image-before-text. Current-turn only: a
caller re-attaches an image when it wants the model to see it again."""

import asyncio
import base64
import binascii
from typing import Any

from .fetch import FetchRefused, fetch
from .shrink import BadPixels, normalize

MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGES = 4  # the whole body sits in RAM on a 512MB box — a cap, not a vibe
MAX_IMAGE_B64 = 14_000_000  # ~10 MB decoded, the API's real per-image cap; shrink cuts it down


class BadImage(Exception):
    """An attachment the edge refuses — the message is the caller's 422 detail."""


def clean_images(raw: Any) -> tuple[dict[str, str], ...]:
    """Validate the body's `images` SHAPE: a list of `{media_type, data}` or `{url}`."""
    if not raw:
        return ()
    if not isinstance(raw, list) or len(raw) > MAX_IMAGES:
        raise BadImage(f"images must be a list of at most {MAX_IMAGES}")
    return tuple(_clean_one(i, item) for i, item in enumerate(raw))


def _clean_one(i: int, item: Any) -> dict[str, str]:
    if isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"]:
        return {"url": item["url"]}
    if not isinstance(item, dict) or item.get("media_type") not in MEDIA_TYPES:
        raise BadImage(f"image {i}: needs a url, or a media_type in {sorted(MEDIA_TYPES)}")
    data = item.get("data")
    if not isinstance(data, str) or not data or len(data) > MAX_IMAGE_B64:
        raise BadImage(f"image {i}: data must be base64 of at most {MAX_IMAGE_B64} chars")
    try:
        base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BadImage(f"image {i}: data is not valid base64") from exc
    return {"media_type": item["media_type"], "data": data}


Block = dict[str, Any]  # a ready Anthropic content block: image or document


async def _ready_one(i: int, item: dict[str, str]) -> Block:
    try:
        raw = await fetch(item["url"]) if "url" in item else base64.b64decode(item["data"])
        small, media_type = await asyncio.to_thread(normalize, raw)
    except (FetchRefused, BadPixels) as exc:
        raise BadImage(f"image {i}: {exc}") from exc
    return {"type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(small).decode()}}


async def prepare_images(raw: Any) -> tuple[Block, ...]:
    """Shape-check, fetch and shrink — sequentially, never four decodes at once."""
    return tuple([await _ready_one(i, item) for i, item in enumerate(clean_images(raw))])


def query_input(message: str, attachments: tuple[Block, ...]) -> str | list[Block]:
    """The `client.query()` payload — SDK-free and unit-testable. A text-only
    turn stays a plain string (byte-identical to before); a turn with
    attachments (images from here, documents from `documents.py`) becomes a
    block list, attachments first, the text block last — skipped when the
    message is empty, because an attachment-only send is valid."""
    if not attachments:
        return message
    content: list[Block] = list(attachments)
    if message.strip():
        content.append({"type": "text", "text": message})
    return content


def attached_counts(attachments: tuple[Block, ...]) -> dict[str, int]:
    """What the `result` event reports (#50), so a consumer can compare it
    against what it sent and fail loud instead of answering blind."""
    return {"images_attached": sum(1 for b in attachments if b["type"] == "image"),
            "documents_attached": sum(1 for b in attachments if b["type"] == "document")}


async def send_turn(client: Any, message: str, attachments: tuple[Block, ...]) -> None:
    """Send the turn's user message: a plain string for text-only turns; with
    attachments, the SDK's streaming-input mode (an async iterable yielding one
    user message dict) — the string mode carries no attachments."""
    payload = query_input(message, attachments)
    if isinstance(payload, str):
        await client.query(payload)
        return

    async def _messages() -> Any:
        yield {"type": "user", "message": {"role": "user", "content": payload},
               "parent_tool_use_id": None}

    await client.query(_messages())
