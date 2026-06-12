"""Chat cog — responds to all messages, no prefix needed.

Refactored from a single 1.1k-line `chat.py` into a package of focused
modules. The public surface is unchanged — `from personas.insult.cogs.chat import
ChatCog` still works. Internal structure:

  cog.py      — the ChatCog class (Discord Cog subclass, listener, command)
  batch.py    — BatchManager: dedup, cooldown, rapid-fire batching
  turn.py     — run_turn(): the full single-turn pipeline
  context.py  — conversation-history + user-facts loaders
  voice.py    — Whisper transcription for voice messages
  tasks.py    — tracked-spawn wrapper + background fact extraction
  tools.py    — tool-call execution (reminders, channels, inauguration)
"""

from personas.insult.cogs.chat.batch import BATCH_WAIT_SECONDS, MAX_MESSAGE_LENGTH, MIN_RESPONSE_GAP
from personas.insult.cogs.chat.cog import ChatCog

__all__ = ["BATCH_WAIT_SECONDS", "MAX_MESSAGE_LENGTH", "MIN_RESPONSE_GAP", "ChatCog"]
