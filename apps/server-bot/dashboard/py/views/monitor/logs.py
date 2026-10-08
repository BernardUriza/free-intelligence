"""Live logs panel — filtered, most recent first, auto-scrolled."""

from browser import document, html

from py.state import store
from py.views.shared import fmt_time

_SKIP_KEYS = ("ts", "event", "level", "timestamp")


def render_logs():
    container = document["log-entries"]
    container.clear()

    filtered = store.logs if store.log_filter == "all" else [
        e for e in store.logs if store.log_filter in e.get("event", "")
    ]

    for entry in reversed(filtered[-100:]):
        row = html.DIV(Class=f"log-row log-{entry.get('level', 'info')}")
        row <= html.SPAN(fmt_time(entry.get("ts", 0)), Class="log-time")
        row <= html.SPAN(entry.get("event", "unknown"), Class="log-event")

        extras = {k: v for k, v in entry.items() if k not in _SKIP_KEYS}
        if extras:
            extra_str = " ".join(f"{k}={v}" for k, v in list(extras.items())[:4])
            row <= html.SPAN(extra_str, Class="log-extra")

        container <= row

    container.scrollTop = container.scrollHeight
