"""Insult + ALICE Dashboard — entry point. Wires fetching, views, tabs and refresh."""

import json

from browser import document, timer

from py import views
from py.config import (
    ALICE_METRICS_URL,
    FACTS_URL,
    LOGS_URL,
    METRICS_URL,
    REFRESH_INTERVAL,
    TRACES_URL,
    VERSION,
)
from py.net import fetch_json
from py.state import store

document.select_one(".logo").innerHTML = (
    f'<span>INSULT</span> Dashboard <em>v{VERSION}</em> <div class="logo-dot"></div>'
)


# ── Data fetching ────────────────────────────────────────────────

def fetch_data():
    fetch_json(METRICS_URL, _on_metrics)
    fetch_json(LOGS_URL, _on_logs)
    fetch_json(TRACES_URL, _on_traces)
    fetch_json(FACTS_URL, _on_facts)
    # ALICE blob is separate; failure is non-fatal (card just stays empty).
    fetch_json(ALICE_METRICS_URL, _on_alice_metrics)


def _on_metrics(req):
    if req.status == 200:
        store.metrics = json.loads(req.text)
        views.render_metrics()
        views.update_status("live", "connected")
    else:
        views.update_status("error", f"HTTP {req.status}")


def _on_logs(req):
    if req.status == 200:
        store.logs = json.loads(req.text)
        views.render_logs()


def _on_traces(req):
    if req.status == 200:
        store.traces = json.loads(req.text)
        views.render_traces()


def _on_facts(req):
    if req.status == 200:
        store.facts = json.loads(req.text)


def _on_alice_metrics(req):
    if req.status == 200:
        try:
            store.alice_metrics = json.loads(req.text)
            views.render_alice_card()
        except Exception:
            store.alice_metrics = {}


def _on_facts_and_render(req):
    if req.status == 200:
        store.facts = json.loads(req.text)
    views.render_facts()


# ── Tab switching ────────────────────────────────────────────────

def _switch_tab(ev):
    tab = ev.target.attrs.get("data-tab", "monitor")
    store.current_tab = tab

    for t in document.select(".tab"):
        t.classList.remove("active")
    ev.target.classList.add("active")

    if tab == "monitor":
        document.select_one(".bento").style.display = "grid"
        document["facts-view"].style.display = "none"
    elif tab == "facts":
        document.select_one(".bento").style.display = "none"
        document["facts-view"].style.display = ""
        fetch_json(FACTS_URL, _on_facts_and_render)


def _on_filter_change(ev):
    store.log_filter = document["log-filter"].value
    views.render_logs()


# ── Bindings + auto-refresh ──────────────────────────────────────

document["log-filter"].bind("change", _on_filter_change)
document["tab-monitor"].bind("click", _switch_tab)
document["tab-facts"].bind("click", _switch_tab)
document["facts-user-filter"].bind("change", lambda ev: views.render_facts())
document["facts-category-filter"].bind("change", lambda ev: views.render_facts())

fetch_data()
timer.set_interval(fetch_data, REFRESH_INTERVAL)
