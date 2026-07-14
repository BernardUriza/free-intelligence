"""strip_delivery_markers — a deferred research/agenda post must never leak a raw
marker as visible text (the 2026-07-11 bug: `[REACT:🌸,🤍]` showed in Alice's report
because the drain loop stripped only its own marker, not [REACT:])."""

from __future__ import annotations

from khimeras_shared.markers import strip_delivery_markers


def test_strips_leaked_react_marker():
    # the exact shape Bernard caught in Alice's delivered report
    text = "demasiado bonito para que no lo notes.\n\n[REACT:🌸,🤍]\n\n---\n\nFue un gusto."
    out = strip_delivery_markers(text)
    assert "[REACT:" not in out
    assert "🌸" not in out
    assert "demasiado bonito" in out
    assert "Fue un gusto." in out


def test_strips_research_and_agenda_markers_too():
    text = "aquí va[RESEARCH: algo] y [AGENDA: vigilar x] el reporte"
    out = strip_delivery_markers(text)
    assert "[RESEARCH:" not in out
    assert "[AGENDA:" not in out
    assert "aquí va" in out and "el reporte" in out


def test_strips_remind_and_remember_markers_too():
    """A deferred report has no live turn to schedule from or learn for — its
    [REMIND:]/[REMEMBER:] must be stripped, never leaked (they'd also re-arm the
    intent from a post the user never asked for)."""
    text = "el hallazgo[REMIND: +1h | revisar] y [REMEMBER: le interesa x] fin"
    out = strip_delivery_markers(text)
    assert "[REMIND:" not in out
    assert "[REMEMBER:" not in out
    assert "el hallazgo" in out and "fin" in out


def test_strips_all_markers_at_once():
    text = "hola [REACT:👀] mundo [RESEARCH: x] fin [AGENDA: y] ya [REMIND: +1h | z] va [REMEMBER: w]"
    out = strip_delivery_markers(text)
    for marker in ("[REACT:", "[RESEARCH:", "[AGENDA:", "[REMIND:", "[REMEMBER:"):
        assert marker not in out
    assert "hola" in out and "mundo" in out and "fin" in out


def test_leaves_clean_text_untouched():
    assert strip_delivery_markers("un reporte normal sin marcadores") == "un reporte normal sin marcadores"


def test_handles_empty():
    assert strip_delivery_markers("") == ""
