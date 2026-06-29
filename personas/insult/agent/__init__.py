"""Insult Agent SDK runner.

Lives in the `persona-runner` Container App (separate from `insult-bot`).
Two long-running services share the container:

- `workspace_renderer` — mirrors Postgres state to /data/insult-workspace
  as markdown files. The Agent SDK reads from these files selectively via
  Read/Grep/Glob tools instead of receiving them inline.
- `runner` (Fase 2b) — FastAPI service exposing POST /v1/turn that
  Insult's `AgentRunnerClient` calls behind a feature flag. Wraps the
  Claude Agent SDK loop.

Both processes have their own systemd-style entrypoints so we can swap
or restart one without the other.
"""
