"""Token-level text from the SDK's partial messages (OG118-EXTERNAL-TURN-2).

With `include_partial_messages=True` the SDK yields `StreamEvent`s wrapping the
raw API events (`content_block_start`, `content_block_delta`, ...) and STILL
yields the complete `TextBlock` afterwards, before that block's `content_block_stop`
(the documented order). So a consumer that appends every `text` event would see
each block twice. Here the deltas stream as they arrive and, when the block
completes, only the tail the deltas did not cover is emitted — normally nothing.

Deltas never touch the result: `drain` keeps building `text`/`answer` from the
complete blocks exactly as before. Stream events are emitted for the main
session only; a subagent's block (`parent_tool_use_id` set) never had deltas and
keeps the legacy whole-block emission.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class LiveText:
    """The text already streamed for the main session's block in progress."""

    block: str = ""

    def on_stream_event(self, event: dict[str, Any]) -> str | None:
        """The text delta to emit for one raw API event, or None."""
        kind = event.get("type")
        if kind == "content_block_start":
            self.block = ""
            return None
        if kind != "content_block_delta":
            return None
        delta = event.get("delta") or {}
        text = delta.get("text") if delta.get("type") == "text_delta" else None
        if not text:
            return None
        self.block += text
        return text

    def settle(self, text: str, *, main: bool) -> str:
        """What is still unsaid when a complete `TextBlock` arrives: the whole
        block when no deltas streamed it (legacy engines, subagents), the uncovered
        tail when they did, nothing when a mismatch would otherwise double it."""
        if not main:
            return text
        live, self.block = self.block, ""
        if not live:
            return text
        return text[len(live):] if text.startswith(live) else ""
