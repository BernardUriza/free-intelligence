"""Canary probe runner — success criterion is verified by ID + nonce, never content.

The runner accepts a CANARY_OK reply ONLY when all three hold: author is the
Insult bot user id, channel is the canary channel, and the nonce echoes the one
the probe posted. An impostor bot, the wrong channel, or a stale nonce all fail.
"""

from __future__ import annotations

from scripts.canary_probe import reply_matches

INSULT_ID = "1490000000000000009"
CANARY_CHANNEL = "1490000000000000001"


def _matches(*, author_id, channel_id, content, expected_nonce="n1"):
    return reply_matches(
        author_id=author_id,
        channel_id=channel_id,
        content=content,
        expected_nonce=expected_nonce,
        insult_bot_user_id=INSULT_ID,
        canary_channel_id=CANARY_CHANNEL,
    )


def test_accepts_insult_reply_with_matching_nonce():
    assert _matches(author_id=int(INSULT_ID), channel_id=int(CANARY_CHANNEL), content="CANARY_OK n1") is True


def test_rejects_wrong_author_even_with_right_content():
    assert _matches(author_id=999, channel_id=int(CANARY_CHANNEL), content="CANARY_OK n1") is False


def test_rejects_wrong_channel():
    assert _matches(author_id=int(INSULT_ID), channel_id=999, content="CANARY_OK n1") is False


def test_rejects_stale_nonce():
    assert _matches(author_id=int(INSULT_ID), channel_id=int(CANARY_CHANNEL), content="CANARY_OK other") is False


def test_rejects_non_canary_content():
    assert _matches(author_id=int(INSULT_ID), channel_id=int(CANARY_CHANNEL), content="hello") is False
