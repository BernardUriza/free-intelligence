"""Message batching for the omnipresent host (#6).

The host sees EVERY message in the server (unlike the mention-gated gateway), so a
fast typist firing "oye" / "una pregunta" / "de las pelis" in three keystrokes must
become ONE routed turn, not three. This is the debounce: messages accumulate per
key (channel:author) and flush as one combined text once the burst goes quiet for
`window_seconds`.

Pure and clock-injected on purpose. The old Insult batcher (now deleted) wired an
`asyncio` timer per batch, which is a pain to test deterministically. Here the core
is a plain accumulator with a `pop_due(now)` the host's loop polls — so the batching
rule is unit-testable with a fake clock, and the asyncio wiring is a thin shell over
it (see the host receiver, later slice of #6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WINDOW_SECONDS = 3.0


@dataclass
class _Batch:
    parts: list[str] = field(default_factory=list)
    last_activity: float = 0.0
    # The id of the most recent message that contributed real text. The routed
    # turn's [REACT:] markers target THIS message (the last thing the user said),
    # so it must ride through pop_due → dispatch → the gateway /invite. Without it
    # every host-routed turn drops its reactions (the post-cutover regression).
    last_message_id: str | None = None


@dataclass
class MessageBatcher:
    """Debounce per-key message bursts into one combined text.

    `window_seconds` is the quiet gap after the LAST message before a batch is
    considered done — each new message RESETS it, so a continuous burst collapses
    into a single batch no matter how many messages it spans.
    """

    window_seconds: float = DEFAULT_WINDOW_SECONDS
    _batches: dict[str, _Batch] = field(default_factory=dict)

    def add(self, key: str, text: str, now: float, message_id: str | None = None) -> None:
        """Accumulate one message under `key`, resetting its debounce to `now`.

        Empty/whitespace text still resets the window (the user is active) but adds
        no line to the combined text — and does NOT become the reaction target
        (`message_id` is only adopted when the message contributes real text, so a
        trailing "ok"/whitespace never steals the [REACT:] anchor)."""
        batch = self._batches.get(key)
        if batch is None:
            batch = _Batch()
            self._batches[key] = batch
        stripped = text.strip()
        if stripped:
            batch.parts.append(stripped)
            if message_id:
                batch.last_message_id = message_id
        batch.last_activity = now

    def pop_due(self, now: float) -> list[tuple[str, str, str | None]]:
        """Return and REMOVE every batch quiet for at least `window_seconds`.

        Result is `(key, combined_text, last_message_id)` triples in insertion
        order. A batch that went quiet but accumulated no real text (only
        whitespace) is dropped, not routed — there is nothing to answer. The
        `last_message_id` is the reaction anchor for the routed turn (None when the
        caller never supplied ids).
        """
        due: list[tuple[str, str, str | None]] = []
        for key in list(self._batches):
            batch = self._batches[key]
            if now - batch.last_activity < self.window_seconds:
                continue
            del self._batches[key]
            combined = "\n".join(batch.parts).strip()
            if combined:
                due.append((key, combined, batch.last_message_id))
        return due

    def pending_keys(self) -> list[str]:
        """Keys with an un-flushed batch — for the host to know if it should keep
        polling (idle when empty)."""
        return list(self._batches)
