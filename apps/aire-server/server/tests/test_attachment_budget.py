"""The per-session attachment budget (#50): history is resent every turn."""

import pytest

from aire.engine import attachment_budget as b


def test_room_left_passes():
    b.check(3, 2_000_000, 1, [400_000])


@pytest.mark.parametrize("held,held_bytes,images,adding", [
    (b.MAX_SESSION_IMAGES, 0, 1, [1]),
    (0, b.MAX_SESSION_BYTES - 10, 0, [11]),
    (b.MAX_SESSION_IMAGES - 1, 0, 2, [1, 1]),
])
def test_either_cap_refuses(held, held_bytes, images, adding):
    with pytest.raises(b.OverBudget, match="new session"):
        b.check(held, held_bytes, images, adding)


@pytest.mark.asyncio
async def test_a_document_weighs_but_does_not_count_as_an_image(monkeypatch):
    async def held(*_):
        return b.MAX_SESSION_IMAGES, 0
    monkeypatch.setattr(b, "held", held)
    doc = {"type": "document", "source": {"type": "text", "data": "x" * 10}}
    await b.enforce("pk", "sid", (doc,))
    with pytest.raises(b.OverBudget):
        await b.enforce("pk", "sid", ({"type": "image", "source": {"data": "x"}},))


@pytest.mark.asyncio
async def test_a_text_only_turn_never_reads_the_store(monkeypatch):
    async def boom(*_):
        raise AssertionError("read the store for a text-only turn")
    monkeypatch.setattr(b, "held", boom)
    await b.enforce("pk", "sid", ())
