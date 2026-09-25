"""The per-session image budget (#50): history is resent every turn."""

import pytest

from aire.engine import image_budget as b


def test_room_left_passes():
    b.check(3, 2_000_000, [400_000])


@pytest.mark.parametrize("held,held_b64,adding", [
    (b.MAX_SESSION_IMAGES, 0, [1]),
    (0, b.MAX_SESSION_IMAGE_B64 - 10, [11]),
    (b.MAX_SESSION_IMAGES - 1, 0, [1, 1]),
])
def test_either_cap_refuses(held, held_b64, adding):
    with pytest.raises(b.OverBudget, match="new session"):
        b.check(held, held_b64, adding)


@pytest.mark.asyncio
async def test_a_text_only_turn_never_reads_the_store(monkeypatch):
    async def boom(*_):
        raise AssertionError("read the store for a text-only turn")
    monkeypatch.setattr(b, "held", boom)
    await b.enforce("pk", "sid", ())
