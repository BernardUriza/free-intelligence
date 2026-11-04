"""`MarkerFilter` — el texto en vivo nunca enseña un marcador, ni partido.

Misma tabla que la del filtro de razonamiento del AI SDK: publica lo que ya no
puede ser marcador, retiene el sufijo que aún podría serlo, descarta el marcador
cuando cierra, y suelta un corchete de prosa en cuanto se sabe que no era uno.
"""

from __future__ import annotations

from persona_runner.engine.live_text import MAX_OPEN_MARKER, MarkerFilter


def _run(chunks: list[str]) -> tuple[list[str], str]:
    f = MarkerFilter()
    out = [f.feed(c) for c in chunks]
    return out, f.flush()


def test_plain_text_passes_through_untouched():
    out, tail = _run(["hola ", "Bern"])
    assert out == ["hola ", "Bern"] and tail == ""


def test_a_marker_split_across_chunks_is_held_then_dropped():
    out, tail = _run(["qué coraje [REA", "CT:🔥", "] eso"])
    assert out == ["qué coraje ", "", " eso"] and tail == ""


def test_the_gif_marker_is_a_marker_too_whatever_its_case():
    out, tail = _run(["mira [gif: face", "palm] jaja"])
    assert "".join(out) + tail == "mira  jaja"


def test_a_bracket_that_is_not_a_marker_is_published_as_soon_as_that_is_known():
    out, tail = _run(["ver [1] y [REACTOR] y [", "nota]"])
    assert "".join(out) + tail == "ver [1] y [REACTOR] y [nota]"


def test_a_lone_open_bracket_at_the_end_is_published_at_flush():
    out, tail = _run(["precio ["])
    assert out == ["precio "] and tail == "["


def test_an_open_marker_that_never_closes_is_dropped_at_flush():
    out, tail = _run(["adiós [REACT:🔥"])
    assert out == ["adiós "] and tail == ""


def test_an_open_marker_longer_than_the_cap_is_released_as_text():
    body = "x" * (MAX_OPEN_MARKER + 5)
    out, tail = _run(["[REACT:" + body])
    assert "".join(out) + tail == "[REACT:" + body


def test_two_markers_back_to_back_leave_only_the_prose():
    out, tail = _run(["[REACT:👀][GIF: shrug]listo"])
    assert "".join(out) + tail == "listo"
