"""Public render API of the dashboard views."""

from py.views.facts import render_facts
from py.views.monitor import render_alice_card, render_logs, render_metrics, update_status
from py.views.traces import render_traces

__all__ = [
    "render_alice_card",
    "render_facts",
    "render_logs",
    "render_metrics",
    "render_traces",
    "update_status",
]
