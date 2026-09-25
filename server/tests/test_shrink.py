"""The image normalizer (#50): ≤ 2000 px out, bombs refused, media type detected."""

import io

import pytest
from PIL import Image

from aire.engine import shrink


def _img(size, fmt, mode="RGB"):
    out = io.BytesIO()
    Image.new(mode, size, (200, 30, 30, 128) if mode == "RGBA" else (200, 30, 30)).save(out, fmt)
    return out.getvalue()


def _size(raw):
    return Image.open(io.BytesIO(raw)).size


def test_a_big_jpeg_comes_out_at_2000_on_the_long_edge():
    out, media = shrink.normalize(_img((4000, 3000), "JPEG"))
    assert media == "image/jpeg" and _size(out) == (2000, 1500)


def test_a_small_image_rides_byte_identical_with_its_detected_type():
    raw = _img((800, 600), "PNG")
    assert shrink.normalize(raw) == (raw, "image/png")


def test_a_big_transparent_png_keeps_alpha_when_it_stays_small():
    out, media = shrink.normalize(_img((3000, 1000), "PNG", "RGBA"))
    assert media == "image/png" and max(_size(out)) == 2000
    assert Image.open(io.BytesIO(out)).mode == "RGBA"


def test_the_decompression_bomb_warning_is_an_error(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(shrink.BadPixels, match="bomb"):
        shrink.normalize(_img((40, 40), "PNG"))


def test_the_bomb_guard_is_never_cleared_by_the_module():
    import aire.engine.shrink  # noqa: F401
    assert Image.MAX_IMAGE_PIXELS is not None


@pytest.mark.parametrize("raw", [b"not an image at all", _img((10, 10), "BMP")])
def test_garbage_and_unaccepted_formats_are_refused(raw):
    with pytest.raises(shrink.BadPixels):
        shrink.normalize(raw)


def test_a_rotated_phone_photo_keeps_its_orientation_after_the_resize():
    img = Image.new("RGB", (4000, 3000), (10, 10, 10))
    exif = img.getexif()
    exif[0x0112] = 6  # "rotate 90° clockwise to display"
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif)
    small, _ = shrink.normalize(out.getvalue())
    assert _size(small) == (1500, 2000)


def test_a_small_rotated_photo_is_re_encoded_upright_not_passed_through():
    img = Image.new("RGB", (400, 300), (10, 10, 10))
    exif = img.getexif()
    exif[0x0112] = 6
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif)
    small, _ = shrink.normalize(out.getvalue())
    assert _size(small) == (300, 400)
