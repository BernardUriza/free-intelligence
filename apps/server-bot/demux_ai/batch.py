"""Message batching for the omnipresent host (#6).

The host sees EVERY message in the server (unlike the mention-gated gateway), so a
fast typist firing "oye" / "una pregunta" / "de las pelis" in three keystrokes must
become ONE routed turn, not three. This is the debounce: messages accumulate per
key (channel:author) and flush as one combined text once the burst goes quiet for
`window_seconds`.

The window is 15s (was 3s until 2026-08-06). Three seconds only catches a burst
of keystrokes; it splits a person THINKING between messages — the pause to recall
a title, to find the link, to write the second half of the idea — into separate
routed turns, each classified blind to the other (the host router gets no channel
context, so a fragment that lands alone routes alone). Fifteen seconds buys the
whole thought at the cost of up to 15s before the turn even starts dispatching.

Pure and clock-injected on purpose. The old Insult batcher (now deleted) wired an
`asyncio` timer per batch, which is a pain to test deterministically. Here the core
is a plain accumulator with a `pop_due(now)` the host's loop polls — so the batching
rule is unit-testable with a fake clock, and the asyncio wiring is a thin shell over
it (see the host receiver, later slice of #6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WINDOW_SECONDS = 15.0


@dataclass
class _Batch:
    parts: list[str] = field(default_factory=list)
    last_activity: float = 0.0
    # The id of the most recent message that contributed real text. The routed
    # turn's [REACT:] markers target THIS message (the last thing the user said),
    # so it must ride through pop_due → dispatch → the gateway /invite. Without it
    # every host-routed turn drops its reactions (the post-cutover regression).
    last_message_id: str | None = None
    # The most recent attachment-bearing message of the burst. When present it
    # WINS as the burst's trigger: the invite path harvests images/documents from
    # the trigger message, so anchoring on the text tail loses the image the user
    # actually wants discussed (2026-07-16, la imagen pelona sin respuesta).
    attachment_message_id: str | None = None
    # The transcript of the burst's most recent voice note. The host is the ONLY
    # component that talks to susurro (2026-07-23 decision), so this text is the
    # persona's single source for what was SAID — it rides pop_due → dispatch →
    # /invite instead of being re-transcribed downstream.
    voice_transcript: str = ""


@dataclass
class MessageBatcher:
    """Debounce per-key message bursts into one combined text.

    `window_seconds` is the quiet gap after the LAST message before a batch is
    considered done — each new message RESETS it, so a continuous burst collapses
    into a single batch no matter how many messages it spans.
    """

    window_seconds: float = DEFAULT_WINDOW_SECONDS
    _batches: dict[str, _Batch] = field(default_factory=dict)

    def add(
        self,
        key: str,
        text: str,
        now: float,
        message_id: str | None = None,
        *,
        has_attachments: bool = False,
        voice_transcript: str = "",
    ) -> None:
        """Accumulate one message under `key`, resetting its debounce to `now`.

        Empty/whitespace text still resets the window (the user is active) but adds
        no line to the combined text — and does NOT become the reaction target
        (`message_id` is only adopted when the message contributes real text, so a
        trailing "ok"/whitespace never steals the [REACT:] anchor). An
        attachment-bearing message additionally records itself as the burst's
        preferred trigger (see `_Batch.attachment_message_id`)."""
        batch = self._batches.get(key)
        if batch is None:
            batch = _Batch()
            self._batches[key] = batch
        stripped = text.strip()
        if stripped:
            batch.parts.append(stripped)
            if message_id:
                batch.last_message_id = message_id
        if has_attachments and message_id:
            batch.attachment_message_id = message_id
        if voice_transcript.strip():
            batch.voice_transcript = voice_transcript.strip()
        batch.last_activity = now

    def pop_due(self, now: float) -> list[tuple[str, str, str | None, str]]:
        """Return and REMOVE every batch quiet for at least `window_seconds`.

        Result is `(key, combined_text, trigger_message_id, voice_transcript)`
        in insertion order. A batch that went quiet but accumulated no real text
        (only whitespace) is dropped, not routed — there is nothing to answer.
        The trigger is the attachment-bearing message when the burst had one
        (the invite path harvests images from the trigger — anchoring on the
        text tail loses them), else the last real-text message (the [REACT:]
        anchor). `voice_transcript` is "" for a burst with no audio.
        """
        due: list[tuple[str, str, str | None, str]] = []
        for key in list(self._batches):
            batch = self._batches[key]
            if now - batch.last_activity < self.window_seconds:
                continue
            del self._batches[key]
            combined = "\n".join(batch.parts).strip()
            if combined:
                due.append(
                    (
                        key,
                        combined,
                        batch.attachment_message_id or batch.last_message_id,
                        batch.voice_transcript,
                    )
                )
        return due

    def pending_keys(self) -> list[str]:
        """Keys with an un-flushed batch — for the host to know if it should keep
        polling (idle when empty)."""
        return list(self._batches)
