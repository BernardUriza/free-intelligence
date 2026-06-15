"""Verify the runner client extracts text + image attachments correctly.

Regression coverage for v3.9.43 (REWRITE-B1): the previous
`_last_user_text` discarded image blocks silently, so Alex's
text+2-images turns were processed as text-only. These tests pin the
new split (`_last_user_text` vs `_last_user_attachments`).
"""

from __future__ import annotations

from khimeras_shared.runner.agent_client import (
    _last_user_attachments,
    _last_user_text,
)


def _user(content):
    return {"role": "user", "content": content}


def _image_block(media_type: str = "image/png", data: str = "AAAA") -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def test_last_user_text_plain_string():
    assert _last_user_text([_user("hola")]) == "hola"


def test_last_user_text_mixed_blocks_returns_only_text():
    msgs = [_user([_text_block("captura del bug"), _image_block()])]
    assert _last_user_text(msgs) == "captura del bug"


def test_last_user_text_multiple_text_blocks_joined():
    msgs = [_user([_text_block("línea 1"), _text_block("línea 2"), _image_block()])]
    assert _last_user_text(msgs) == "línea 1\nlínea 2"


def test_last_user_text_image_only_returns_empty():
    msgs = [_user([_image_block()])]
    assert _last_user_text(msgs) == ""


def test_last_user_text_empty_messages():
    assert _last_user_text([]) == ""


def test_last_user_attachments_extracts_images():
    msgs = [_user([_text_block("foto:"), _image_block("image/jpeg", "BBBB")])]
    attachments = _last_user_attachments(msgs)
    assert len(attachments) == 1
    assert attachments[0]["type"] == "image"
    assert attachments[0]["source"]["media_type"] == "image/jpeg"


def test_last_user_attachments_extracts_multiple_images():
    msgs = [
        _user(
            [
                _text_block("dos capturas:"),
                _image_block("image/png", "AAA"),
                _image_block("image/jpeg", "BBB"),
            ]
        )
    ]
    assert len(_last_user_attachments(msgs)) == 2


def test_last_user_attachments_includes_documents():
    msgs = [
        _user(
            [
                _text_block("ve el pdf"),
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": "%PDF"},
                },
            ]
        )
    ]
    attachments = _last_user_attachments(msgs)
    assert len(attachments) == 1
    assert attachments[0]["type"] == "document"


def test_last_user_attachments_text_only_returns_empty():
    assert _last_user_attachments([_user("solo texto")]) == []


def test_last_user_attachments_empty_messages_returns_empty():
    assert _last_user_attachments([]) == []


def test_split_preserves_text_and_image_independently():
    """The critical invariant: same input produces both text AND images,
    they don't cannibalize each other. This is the exact case that bit
    us 2026-05-18 — text was preserved, images were dropped."""
    msgs = [
        _user(
            [
                _text_block("ya viste esto?"),
                _image_block("image/png", "AAA"),
                _image_block("image/png", "BBB"),
            ]
        )
    ]
    assert _last_user_text(msgs) == "ya viste esto?"
    assert len(_last_user_attachments(msgs)) == 2
