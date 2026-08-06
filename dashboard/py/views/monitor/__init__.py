"""Monitor tab — stat cards, preset bars, counters, ALICE card and live logs."""

from py.state import store
from py.views.monitor.alice import render_alice_card
from py.views.monitor.counters import render_counters, render_presets
from py.views.monitor.logs import render_logs
from py.views.monitor.stats import (
    render_freshness,
    render_stats,
    report_data,
    report_unreachable,
)

__all__ = [
    "render_alice_card",
    "render_freshness",
    "render_logs",
    "render_metrics",
    "report_data",
    "report_unreachable",
]


def render_metrics():
    if not store.metrics:
        return
    counters = store.metrics.get("counters", {})
    render_stats()
    render_presets(counters)
    render_counters(counters)
