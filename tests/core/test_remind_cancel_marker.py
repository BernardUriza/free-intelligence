"""`[REMIND_CANCEL:]` marker contract — parse, strip, and non-collision with
`[REMIND:]`.

Mutator rule (.claude/rules/robustness.md): the positive case each parser exists
for AND the resistance case it must survive — here the sharpest resistance is
cross-contamination: a cancel marker must never read as a create marker (a
double-schedule) and a create marker must never read as a cancel (a lost row).
"""

from __future__ import annotations

from persona_core.markers import (
    MAX_CANCEL_CRITERION_LEN,
    parse_remind_cancels,
    strip_delivery_markers,
    strip_remind_cancels,
)
from persona_core.remind_marker import parse_remind, strip_reminds

# --------------------------------------------------------------------------
# parse_remind_cancels
# --------------------------------------------------------------------------


def test_parse_extracts_criterion():
    assert parse_remind_cancels("Listo, lo quito. [REMIND_CANCEL: sacar la ropa]") == ["sacar la ropa"]


def test_parse_extracts_multiple_distinct_criteria_in_order():
    """Two cancel markers are two targets — unlike [REMIND:], where a second
    marker is a stutter, cancelling twice costs nothing and both are honored."""
    text = "Fuera ambos. [REMIND_CANCEL: la ropa] y [REMIND_CANCEL: tomar el ARV]"
    assert parse_remind_cancels(text) == ["la ropa", "tomar el ARV"]


def test_parse_dedupes_a_stuttered_criterion_case_insensitively():
    text = "[REMIND_CANCEL: la ropa][REMIND_CANCEL: La Ropa]"
    assert parse_remind_cancels(text) == ["la ropa"]


def test_parse_returns_empty_without_marker():
    assert parse_remind_cancels("Nada que cancelar aquí.") == []
    assert parse_remind_cancels("") == []


def test_parse_skips_empty_criterion():
    """RESISTANCE: an empty criterion would substring-match EVERY pending
    reminder — a cancel-all nobody asked for. It parses to nothing."""
    assert parse_remind_cancels("[REMIND_CANCEL: ]") == []
    assert parse_remind_cancels("[REMIND_CANCEL:]") == []


def test_parse_caps_an_oversize_criterion():
    long = "x" * (MAX_CANCEL_CRITERION_LEN + 50)
    [criterion] = parse_remind_cancels(f"[REMIND_CANCEL: {long}]")
    assert len(criterion) == MAX_CANCEL_CRITERION_LEN


# --------------------------------------------------------------------------
# strip_remind_cancels
# --------------------------------------------------------------------------


def test_strip_removes_marker_and_collapses_holes():
    out = strip_remind_cancels("Listo, cancelado. [REMIND_CANCEL: la ropa] ¿Algo más?")
    assert "[REMIND_CANCEL" not in out
    assert "Listo, cancelado." in out
    assert "¿Algo más?" in out
    assert "  " not in out


def test_strip_leaves_clean_text_untouched():
    assert strip_remind_cancels("una respuesta normal") == "una respuesta normal"
    assert strip_remind_cancels("") == ""


# --------------------------------------------------------------------------
# non-collision with [REMIND:] — both directions
# --------------------------------------------------------------------------


def test_cancel_marker_is_not_parsed_as_a_remind():
    """RESISTANCE: a cancel must never double as a create (a phantom row)."""
    assert parse_remind("Va. [REMIND_CANCEL: la ropa | algo]") is None


def test_remind_marker_is_not_parsed_as_a_cancel():
    """RESISTANCE: a create must never double as a cancel (a lost row)."""
    assert parse_remind_cancels("[REMIND: +2h | sacar la ropa]") == []


def test_strip_reminds_leaves_the_cancel_marker_for_its_own_strip():
    text = "Va.[REMIND: +2h | x][REMIND_CANCEL: y]"
    out = strip_reminds(text)
    assert "[REMIND:" not in out.replace("[REMIND_CANCEL:", "")
    assert "[REMIND_CANCEL: y]" in out


def test_strip_remind_cancels_leaves_the_remind_marker_for_its_own_strip():
    out = strip_remind_cancels("Va.[REMIND: +2h | x][REMIND_CANCEL: y]")
    assert "[REMIND: +2h | x]" in out
    assert "[REMIND_CANCEL" not in out


# --------------------------------------------------------------------------
# strip_delivery_markers inherits the strip (deferred paths can't leak it)
# --------------------------------------------------------------------------


def test_deferred_delivery_strips_remind_cancel_too():
    text = "el reporte[REMIND_CANCEL: la ropa] sigue [REMIND: +1h | z] fin"
    out = strip_delivery_markers(text)
    assert "[REMIND_CANCEL:" not in out
    assert "[REMIND:" not in out
    assert "el reporte" in out and "fin" in out
