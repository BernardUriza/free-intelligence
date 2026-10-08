"""Preset distribution bars + the operational counters list."""

from browser import document, html

PRESETS = [
    ("default_abrasive", "#e74c3c", "Abrasive"),
    ("playful_roast", "#f39c12", "Roast"),
    ("intellectual_pressure", "#3498db", "Intellectual"),
    ("relational_probe", "#9b59b6", "Relational"),
    ("respectful_serious", "#2ecc71", "Serious"),
    ("meta_deflection", "#95a5a6", "Meta"),
]

COUNTER_ITEMS = [
    ("Whisper Transcriptions", "whisper_transcriptions"),
    ("Reminders Created", "reminders_created"),
    ("Facts Extracted", "facts_extracted"),
    ("Facts Failed", "facts_failed"),
    ("Remember Facts Added", "remember_facts_added"),
    ("ALICE Failovers", "alice_failovers"),
    ("Gateway Restarts", "gateway_zombie_restarts"),
]


def render_presets(counters):
    container = document["preset-bars"]
    container.clear()

    total = sum(counters.get(f"preset_{key}", 0) for key, _, _ in PRESETS) or 1

    for key, color, label in PRESETS:
        count = counters.get(f"preset_{key}", 0)
        pct = round(count / total * 100)

        row = html.DIV(Class="preset-row")
        row <= html.SPAN(label, Class="preset-label")
        bar_bg = html.DIV(Class="preset-bar-bg")
        bar_bg <= html.DIV(Class="preset-bar-fill", style={"width": f"{pct}%", "background": color})
        row <= bar_bg
        row <= html.SPAN(f"{count} ({pct}%)", Class="preset-count")
        container <= row


def render_counters(counters):
    container = document["counter-list"]
    container.clear()

    for label, key in COUNTER_ITEMS:
        row = html.DIV(Class="counter-row")
        row <= html.SPAN(label, Class="counter-label")
        row <= html.SPAN(str(counters.get(key, 0)), Class="counter-value")
        container <= row
