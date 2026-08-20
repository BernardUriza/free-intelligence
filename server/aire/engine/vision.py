"""The turn's image attachments (#29 gap 4) — validated at the edge, folded
into the SDK's streaming-input mode. Ported from fi-runner's ClaudeCodeBackend
(`build_query_input` / `_query`, the canonical vision fold).

`data` is base64-encoded bytes, no `data:` URL prefix. Blocks ride
image-before-text (Anthropic's recommended ordering). Current-turn only: the
mirrored transcript keeps whatever the SDK writes, and a caller re-attaches an
image when it wants the model to see it again."""

import base64
import binascii
from typing import Any

MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGES = 4  # the whole body sits in RAM on a 512MB box — a cap, not a vibe
MAX_IMAGE_B64 = 5_000_000  # ~3.7MB decoded, inside the API's 5MB-per-image cap


class BadImage(Exception):
    """An attachment the edge refuses — the message is the caller's 422 detail."""


def clean_images(raw: Any) -> tuple[dict[str, str], ...]:
    """Validate the body's `images`: a list of `{media_type, data}` dicts."""
    if not raw:
        return ()
    if not isinstance(raw, list) or len(raw) > MAX_IMAGES:
        raise BadImage(f"images must be a list of at most {MAX_IMAGES}")
    return tuple(_clean_one(item) for item in raw)


def _clean_one(item: Any) -> dict[str, str]:
    if not isinstance(item, dict) or item.get("media_type") not in MEDIA_TYPES:
        raise BadImage(f"each image needs a media_type in {sorted(MEDIA_TYPES)}")
    data = item.get("data")
    if not isinstance(data, str) or not data or len(data) > MAX_IMAGE_B64:
        raise BadImage(f"image data must be base64 of at most {MAX_IMAGE_B64} chars")
    try:
        base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BadImage("image data is not valid base64") from exc
    return {"media_type": item["media_type"], "data": data}


def query_input(message: str, images: tuple[dict[str, str], ...]) -> str | list[dict[str, Any]]:
    """The `client.query()` payload — SDK-free and unit-testable. A text-only
    turn stays a plain string (byte-identical to before); an image turn becomes
    a block list, images first, the text block last — skipped when the message
    is empty, because an image-only send is valid: the picture IS the message."""
    if not images:
        return message
    content: list[dict[str, Any]] = [
        {"type": "image",
         "source": {"type": "base64", "media_type": img["media_type"], "data": img["data"]}}
        for img in images
    ]
    if message.strip():
        content.append({"type": "text", "text": message})
    return content


async def send_turn(client: Any, message: str, images: tuple[dict[str, str], ...]) -> None:
    """Send the turn's user message: a plain string for text-only turns; for
    image turns, the SDK's streaming-input mode (an async iterable yielding one
    user message dict) — the string mode carries no attachments."""
    payload = query_input(message, images)
    if isinstance(payload, str):
        await client.query(payload)
        return

    async def _messages() -> Any:
        yield {"type": "user", "message": {"role": "user", "content": payload},
               "parent_tool_use_id": None}

    await client.query(_messages())
