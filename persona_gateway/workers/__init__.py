"""Background drain workers — durable queues each persona services on a cadence.

Each worker owns the LOGIC of one `@tasks.loop` (research jobs, standing agendas,
reminders); the loop shell in `PersonaClient` stays one line (`await
worker.drain(self)`). Workers take their deps injected (persona, memory,
agent_client) and receive the live client as a `host` per call — for
`get_channel` and the bot user id — so they never import `PersonaClient` and the
dependency graph stays acyclic (workers → khimeras_shared, never back).
"""

from __future__ import annotations

from persona_gateway.workers.agenda import AgendaWorker
from persona_gateway.workers.reminders import ReminderWorker
from persona_gateway.workers.research import ResearchWorker

__all__ = ["AgendaWorker", "ReminderWorker", "ResearchWorker"]
