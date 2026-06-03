"""Background-task wiring for the Discord bot.

`bot._build()` used to be a ~1100-line god-function: every `@tasks.loop`,
every event handler, and all the shared `nonlocal` state lived in one
closure. This package splits the loops out by domain. Each module exposes
a small factory (`build_*`) or a runtime class that takes the deps it needs
and returns the `discord.ext.tasks.Loop` object(s); `bot._build()` stays a
thin orchestrator that creates the loops, registers events, and owns
start/cancel lifecycle.
"""
