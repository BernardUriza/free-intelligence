"""Every image leaves the door ≤ 2000 px per side and small (#50).

Why 2000: once a request carries more than 20 images — counting the ones
resent from earlier turns — the API refuses the WHOLE request if any image is
over 2000 px per side, and that image sits in the transcript forever, so every
later turn of the session dies too. The model downsamples past 2576 anyway, so
2000 costs almost nothing. The bundled CLI already shrinks to 2000 today (all 90
stored images measured ≤ 2000 on 2026-09-25); AIRE owns the rule anyway, so it
does not rest on an undocumented CLI internal, and the CLI never has to decode a
12 MP photo on a 512 MB box.

Pillow is imported lazily: only an image turn pays for it. Its bomb guard stays
armed (`MAX_IMAGE_PIXELS` is never cleared) and its WARNING is promoted to an
error, and JPEGs decode through `draft()` at the smallest scale that still
covers 2000 px, so a 12 MP photo never becomes ~36 MB of RGB in RAM."""

import io
import warnings
from typing import Any

MAX_SIDE = 2000
# Only a JPEG decodes at a reduced scale (draft). Every other format decodes its
# FULL raster before thumbnail() can shrink it, and a one-colour PNG a few KB
# long can claim 9459×9459 — ~268 MB of RGB under Pillow's own bomb line, more
# than this box has free. So a non-JPEG is capped at what the box can hold.
MAX_DECODE_PIXELS = 4096 * 4096  # 64 MB as RGBA, the worst mode
PASS_BYTES = 1_000_000  # already small AND ≤ MAX_SIDE → the caller's bytes ride untouched
JPEG_QUALITY = 85  # a 4.7 MB iPhone photo lands near 1 MB at 2000 px
MEDIA = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}


class BadPixels(Exception):
    """Bytes the normalizer refuses — the caller's 422 detail."""


def _open(raw: bytes) -> Any:
    from PIL import Image
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(raw))  # the bomb check fires inside open()
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise BadPixels("image refused: too many pixels (decompression bomb guard)") from exc
    except (OSError, SyntaxError, ValueError) as exc:
        raise BadPixels("image bytes are not a readable image") from exc
    if img.format not in MEDIA:
        raise BadPixels(f"image format {img.format} not accepted; send {sorted(MEDIA)}")
    if img.format != "JPEG" and img.width * img.height > MAX_DECODE_PIXELS:
        raise BadPixels(f"image refused: {img.width}×{img.height} {img.format} is too large to decode here; "
                        "send it as a JPEG or smaller")
    return img


def _has_alpha(img: Any) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)


def _encode(img: Any) -> tuple[bytes, str]:
    """PNG when transparency must survive and it stays small; JPEG otherwise."""
    out = io.BytesIO()
    if _has_alpha(img):
        img.convert("RGBA").save(out, "PNG", optimize=True)
        if out.tell() <= PASS_BYTES:
            return out.getvalue(), "image/png"
        out = io.BytesIO()
    img.convert("RGB").save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue(), "image/jpeg"


def normalize(raw: bytes) -> tuple[bytes, str]:
    """`(bytes, media_type)` — the media type DETECTED, never the caller's claim."""
    from PIL import Image, ImageOps
    img = _open(raw)
    upright = img.getexif().get(0x0112, 1) == 1
    if upright and max(img.size) <= MAX_SIDE and len(raw) <= PASS_BYTES:
        return raw, MEDIA[img.format]
    if img.format == "JPEG":
        img.draft("RGB", (MAX_SIDE, MAX_SIDE))  # decode at 1/2, 1/4 or 1/8 scale
    try:
        img.seek(0)  # an animated GIF/WebP keeps its first frame
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        return _encode(ImageOps.exif_transpose(img))  # re-encoding drops EXIF: bake the rotation in
    except (OSError, ValueError) as exc:
        raise BadPixels("image could not be decoded") from exc
