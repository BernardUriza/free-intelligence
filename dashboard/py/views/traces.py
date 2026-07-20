"""Recent Messages panel — trace cards in a carousel + the reasoning modal."""

from browser import document, html

from py.state import store
from py.views.shared import CardCarousel, fmt_time


def _render_trace_card(trace):
    card = html.DIV()

    time_str = fmt_time(trace.get("ts", 0), "%H:%M", "??:??")
    card <= html.DIV(f"{trace.get('user', '?')} · {time_str}", Class="trace-user")

    inp = trace.get("input", "")
    card <= html.DIV(f'"{inp}"' if inp else "(empty)", Class="trace-input")

    resp = trace.get("response", "")
    card <= html.DIV(resp if resp else "(no text)", Class="trace-response")

    meta = html.DIV(Class="trace-meta")
    meta <= html.SPAN(trace.get("preset", "?"), Class="trace-tag preset")
    pressure = trace.get("pressure", 0)
    if pressure:
        meta <= html.SPAN(f"P{pressure}", Class="trace-tag pressure")
    shape = trace.get("expression_shape", "")
    if shape:
        meta <= html.SPAN(shape, Class="trace-tag shape")
    for tool in trace.get("tools", []):
        meta <= html.SPAN(tool, Class="trace-tag tool")
    if trace.get("character_break"):
        meta <= html.SPAN("BREAK!", Class="trace-tag break")
    if trace.get("anti_pattern"):
        meta <= html.SPAN("DRIFT", Class="trace-tag break")
    if trace.get("reactions"):
        meta <= html.SPAN(" ".join(trace["reactions"][:3]), Class="trace-tag")

    detail_btn = html.SPAN("↗", Class="trace-detail-btn")
    detail_btn.bind("click", lambda ev, t=trace: _show_trace_modal(t))
    meta <= detail_btn
    card <= meta

    return card


def _show_trace_modal(trace):
    for e in document.select(".trace-modal-overlay"):
        e.remove()

    overlay = html.DIV(Class="trace-modal-overlay")
    modal = html.DIV(Class="trace-modal")

    close_btn = html.BUTTON("×", Class="trace-modal-close")
    close_btn.bind("click", lambda ev: overlay.remove())
    modal <= close_btn

    time_str = fmt_time(trace.get("ts", 0))
    modal <= html.H2(f"{trace.get('user', '?')} · {time_str}", Class="trace-modal-title")

    modal <= html.DIV("INPUT", Class="trace-modal-label")
    modal <= html.DIV(trace.get("input", "(empty)"), Class="trace-modal-text input")

    modal <= html.DIV("RESPONSE", Class="trace-modal-label")
    modal <= html.DIV(trace.get("response", "(no text)"), Class="trace-modal-text response")

    modal <= html.DIV("REASONING", Class="trace-modal-label")
    grid = html.DIV(Class="trace-modal-grid")

    rows = [
        ("Preset", trace.get("preset", "?"), "preset"),
        ("Modifiers", ", ".join(trace.get("preset_modifiers", [])) or "none", ""),
        ("Pressure", f"Level {trace.get('pressure', 0)}", "pressure"),
        ("Expression Shape", trace.get("expression_shape", "?"), "shape"),
        ("Expression Flavor", trace.get("expression_flavor", "?"), ""),
        ("Epistemic Move", trace.get("epistemic_move", "none"), ""),
        ("Awareness Pattern", trace.get("awareness_pattern", "none"), ""),
        ("Tools Used", ", ".join(trace.get("tools", [])) or "none", "tool"),
        ("Reactions", " ".join(trace.get("reactions", [])) or "none", ""),
        ("Channel", trace.get("channel", "?"), ""),
        ("User ID", trace.get("user_id", "?"), ""),
    ]

    for label, value, tag_class in rows:
        row = html.DIV(Class="trace-modal-row")
        row <= html.SPAN(label, Class="trace-modal-key")
        row <= html.SPAN(str(value), Class=f"trace-modal-val {tag_class}")
        grid <= row

    modal <= grid
    overlay <= modal

    overlay.bind("click", lambda ev: overlay.remove() if ev.target == overlay else None)

    document.body <= overlay


_carousel = CardCarousel(
    container_id="traces-carousel",
    render_card=_render_trace_card,
    get_id=lambda t: str(t.get("ts", 0)),
    empty_msg="No messages yet.",
)


def render_traces():
    _carousel.render(list(reversed(store.traces[-30:])))
