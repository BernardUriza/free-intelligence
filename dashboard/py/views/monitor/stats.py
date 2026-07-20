"""Stat cards (uptime / messages / latency / errors) + the status pill."""

from browser import document

from py.state import store
from py.views.shared import fmt_uptime


def render_stats():
    counters = store.metrics.get("counters", {})
    bot = store.metrics.get("bot", {})
    db = store.metrics.get("db", {})

    document["val-uptime"].text = fmt_uptime(store.metrics.get("uptime_seconds", 0))
    document["val-messages"].text = str(db.get("total_messages", counters.get("messages_total", 0)))
    document["val-latency"].text = f"{bot.get('latency_ms', 0)}ms"
    # `llm_errors` died with its emitter (the legacy LLMClient); these three DO fire.
    document["val-errors"].text = str(
        counters.get("facts_failed", 0)
        + counters.get("alice_failovers", 0)
        + counters.get("gateway_zombie_restarts", 0)
    )


def update_status(state, text):
    el = document["status-indicator"]
    el.text = text
    el.className = f"status status-{state}"
