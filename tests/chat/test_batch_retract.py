"""BatchManager.retract_if_pending — the Insult half of the edited-in-address
fix (P0 2026-07-06): a message that enters the batch clean and is edited to
address a sibling must leave Insult's pending batch (the sibling's gateway
picks the edit up via ``edit_summons``). Once flushed, there is nothing to
retract — the False return is the honest signal.
"""

from __future__ import annotations

from types import SimpleNamespace

from personas.insult.cogs.chat.batch import BatchManager, _MessageBatch


def _msg(message_id: int, channel_id: int = 10, author_id: int = 20):
    return SimpleNamespace(
        id=message_id,
        channel=SimpleNamespace(id=channel_id),
        author=SimpleNamespace(id=author_id),
    )


class _Timer:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def _seed(manager: BatchManager, *messages, timer: _Timer | None = None) -> str:
    key = f"{messages[0].channel.id}:{messages[0].author.id}"
    batch = _MessageBatch(
        messages=list(messages),
        texts=[f"text-{m.id}" for m in messages],
        timer=timer,
    )
    manager._pending[key] = batch
    return key


def test_retract_pending_message_removes_it_and_cancels_empty_batch():
    manager = BatchManager()
    timer = _Timer()
    key = _seed(manager, _msg(111), timer=timer)
    assert manager.retract_if_pending(_msg(111)) is True
    assert key not in manager._pending
    assert timer.cancelled is True


def test_retract_keeps_other_messages_in_the_batch():
    """Only the edited message leaves — the rest of the burst still flushes."""
    manager = BatchManager()
    timer = _Timer()
    key = _seed(manager, _msg(111), _msg(222), timer=timer)
    assert manager.retract_if_pending(_msg(222)) is True
    batch = manager._pending[key]
    assert [m.id for m in batch.messages] == [111]
    assert batch.texts == ["text-111"]
    assert timer.cancelled is False


def test_retract_after_flush_returns_false():
    """RESISTANCE: once Insult responded (batch flushed) there is nothing to
    un-send — retract reports False and the caller just logs it."""
    manager = BatchManager()
    assert manager.retract_if_pending(_msg(111)) is False


def test_retract_unknown_message_in_live_batch_returns_false():
    manager = BatchManager()
    _seed(manager, _msg(111))
    assert manager.retract_if_pending(_msg(999)) is False
