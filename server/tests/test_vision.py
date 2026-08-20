"""The vision fold (#29 gap 4), offline: the edge validation and the query
payload shape — no SDK, no network."""

import base64

import pytest

from aire.engine.vision import MAX_IMAGES, BadImage, clean_images, query_input

PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfakebytes").decode()
IMG = {"media_type": "image/png", "data": PNG_B64}


def test_clean_images_accepts_the_valid_and_defaults_to_empty():
    assert clean_images(None) == ()
    assert clean_images([]) == ()
    assert clean_images([IMG]) == (IMG,)


@pytest.mark.parametrize("bad", [
    "not-a-list",
    [{"media_type": "image/tiff", "data": PNG_B64}],
    [{"media_type": "image/png", "data": "not base64!!"}],
    [{"media_type": "image/png", "data": ""}],
    [{"media_type": "image/png"}],
    [IMG] * (MAX_IMAGES + 1),
])
def test_clean_images_refuses_the_malformed(bad):
    with pytest.raises(BadImage):
        clean_images(bad)


def test_query_input_text_only_stays_a_plain_string():
    assert query_input("hola", ()) == "hola"


def test_query_input_folds_images_first_then_the_text_block():
    blocks = query_input("what is this?", (IMG,))
    assert [b["type"] for b in blocks] == ["image", "text"]
    assert blocks[0]["source"] == {"type": "base64", "media_type": "image/png",
                                   "data": PNG_B64}
    assert blocks[1]["text"] == "what is this?"


def test_query_input_image_only_send_has_no_text_block():
    blocks = query_input("", (IMG,))
    assert [b["type"] for b in blocks] == ["image"]
