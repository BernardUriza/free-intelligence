"""The omnipresent host's message batcher (#6, first slice).

Debounce: a burst of messages from one author in one channel collapses into a
single routed turn. Positive: quiet past the window → one combined batch.
Resistance: still typing (within window) → nothing flushes; different keys never
mix; a whitespace-only burst routes nothing.
"""

from __future__ import annotations

from demux_ai.batch import MessageBatcher


def test_single_message_flushes_after_the_window():
    b = MessageBatcher(window_seconds=3.0)
    b.add("c1:u1", "hola", now=100.0)
    assert b.pop_due(now=101.0) == []  # still within the window
    assert b.pop_due(now=104.0) == [("c1:u1", "hola")]  # quiet past 3s


def test_burst_collapses_into_one_batch_the_debounce_resets():
    """RESISTANCE to per-keystroke turns: three fast messages = ONE turn."""
    b = MessageBatcher(window_seconds=3.0)
    b.add("c1:u1", "oye", now=100.0)
    b.add("c1:u1", "una pregunta", now=101.0)
    b.add("c1:u1", "de las pelis", now=102.0)
    # At 104 only 2s have passed since the LAST message — still batching.
    assert b.pop_due(now=104.0) == []
    assert b.pop_due(now=105.5) == [("c1:u1", "oye\nuna pregunta\nde las pelis")]


def test_different_keys_are_independent():
    b = MessageBatcher(window_seconds=3.0)
    b.add("c1:u1", "de u1", now=100.0)
    b.add("c1:u2", "de u2", now=100.5)
    due = dict(b.pop_due(now=104.0))
    assert due == {"c1:u1": "de u1", "c1:u2": "de u2"}


def test_whitespace_only_burst_routes_nothing():
    """RESISTANCE: a burst that carried no real text has nothing to answer."""
    b = MessageBatcher(window_seconds=3.0)
    b.add("c1:u1", "   ", now=100.0)
    b.add("c1:u1", "\n", now=101.0)
    assert b.pop_due(now=105.0) == []
    assert b.pending_keys() == []  # and it's cleared, not leaked


def test_flushed_batch_is_removed_not_repeated():
    b = MessageBatcher(window_seconds=3.0)
    b.add("c1:u1", "hola", now=100.0)
    assert b.pop_due(now=104.0) == [("c1:u1", "hola")]
    assert b.pop_due(now=110.0) == []  # not re-delivered
    assert b.pending_keys() == []


def test_pending_keys_tracks_unflushed_work():
    b = MessageBatcher(window_seconds=3.0)
    assert b.pending_keys() == []
    b.add("c1:u1", "x", now=100.0)
    assert b.pending_keys() == ["c1:u1"]
