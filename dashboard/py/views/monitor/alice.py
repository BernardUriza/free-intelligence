"""ALICE sibling-bot status card. Tolerates missing fields gracefully."""

from browser import document, html

from py.state import store
from py.views.shared import fmt_uptime


def render_alice_card():
    el = document.select_one("#alice-card-body")
    if el is None:
        return
    if not store.alice_metrics:
        el.clear()
        msg = (
            "Sin datos: el blob alice-bot/metrics.json no existe (404). "
            "El container alice-bot fue eliminado; nadie va a escribirlo."
            if store.alice_missing
            else "ALICE no ha reportado todavía"
        )
        el <= html.DIV(msg, Class="alice-empty")
        return

    counters = store.alice_metrics.get("counters", {}) or {}
    gateway = store.alice_metrics.get("gateway", {}) or {}

    el.clear()
    grid = html.DIV(Class="alice-grid")

    def kv(label, value, *, accent=None):
        cls = "alice-stat"
        if accent:
            cls += f" alice-stat-{accent}"
        cell = html.DIV(Class=cls)
        cell <= html.DIV(label, Class="alice-stat-label")
        cell <= html.DIV(str(value), Class="alice-stat-value")
        return cell

    def alert_if(count):
        return "alert" if count > 0 else None

    grid <= kv("uptime", fmt_uptime(store.alice_metrics.get("uptime_seconds", 0)))
    grid <= kv("latency", f"{gateway.get('latency_ms', '--')}ms")
    grid <= kv("guilds", gateway.get("guilds", "--"))
    grid <= kv("turns", counters.get("turns_total", 0))
    failover = counters.get("failover_received", 0)
    grid <= kv("failover", failover, accent=alert_if(failover))
    grid <= kv("invites", counters.get("invite_received", 0))
    errors = counters.get("llm_errors", 0)
    grid <= kv("llm err", errors, accent=alert_if(errors))
    restarts = counters.get("watchdog_restarts", 0)
    grid <= kv("restarts", restarts, accent=alert_if(restarts))

    el <= grid
