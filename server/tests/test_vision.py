"""The vision fold (#29 gap 4), offline: the edge validation and the query
payload shape — no SDK, no network."""

import base64

import pytest

from aire.engine.vision import MAX_IMAGES, BadImage, attached_counts, clean_images, query_input

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


BLOCK = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG_B64}}
DOC = {"type": "document", "source": {"type": "text", "media_type": "text/plain", "data": "hola"}}


def test_query_input_folds_attachments_first_then_the_text_block():
    blocks = query_input("what is this?", (BLOCK, DOC))
    assert [b["type"] for b in blocks] == ["image", "document", "text"]
    assert blocks[0] == BLOCK and blocks[1] == DOC
    assert blocks[2]["text"] == "what is this?"


def test_query_input_attachment_only_send_has_no_text_block():
    blocks = query_input("", (BLOCK,))
    assert [b["type"] for b in blocks] == ["image"]


def test_attached_counts_reports_each_kind():
    assert attached_counts((BLOCK, DOC, DOC)) == {"images_attached": 1, "documents_attached": 2}
