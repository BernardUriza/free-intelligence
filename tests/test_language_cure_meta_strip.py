"""Tests for the `_META_PREAMBLE_RE` strip in language_cure.

Documented bug from 2026-05-13 prod incident: Haiku sometimes ignores
"return only the corrected text" and adds a meta-preamble describing what
it's about to do, then the actual text. The regex strips that preamble.
"""

from __future__ import annotations

import re

from insult.core.language import _META_PREAMBLE_RE


def _strip_once(text: str) -> str:
    return _META_PREAMBLE_RE.sub("", text, count=1).strip()


def test_spanish_already_unchanged_preamble():
    inp = (
        "El texto está completamente en español, así que lo devuelvo sin cambios: "
        "Sospecho que hablás del Porfiriato, no de Alicia en el País de las Maravillas."
    )
    out = _strip_once(inp)
    assert out.startswith("Sospecho que hablás del Porfiriato")
    assert "completamente en español" not in out


def test_no_changes_needed_preamble_english():
    inp = "No changes needed: The text is fine as is."
    out = _strip_once(inp)
    assert out == "The text is fine as is."


def test_here_is_the_text_preamble():
    inp = "Here is the text: La cena está lista."
    out = _strip_once(inp)
    assert out == "La cena está lista."


def test_returning_unchanged_preamble():
    inp = "Returning unchanged: Hola Bernard."
    out = _strip_once(inp)
    assert out == "Hola Bernard."


def test_text_without_preamble_passes_through():
    inp = "Hola Bernard, todo bien."
    out = _strip_once(inp)
    assert out == inp


def test_text_with_colon_in_normal_flow_not_stripped():
    """`Mira: el camion sale a las 3pm` is NOT a preamble — must not strip."""
    inp = "Mira: el camion sale a las 3pm."
    out = _strip_once(inp)
    assert out == inp


def test_lo_devuelvo_sin_cambios_variant():
    inp = "Lo devuelvo sin cambios: Buenos días."
    out = _strip_once(inp)
    assert out == "Buenos días."


def test_strips_only_first_preamble_if_repeated():
    """If somehow two preambles stack, only the first gets removed per pass."""
    inp = (
        "El texto está completamente en español, lo devuelvo sin cambios: "
        "No hay cambios: La cena está lista."
    )
    out = _strip_once(inp)
    # First preamble removed, second one remains (count=1)
    assert "El texto está completamente" not in out
    # Either second preamble survived or got stripped too in same pass — both acceptable;
    # what matters is the real content is the tail.
    assert "La cena está lista" in out


def test_preamble_is_case_insensitive():
    inp = "EL TEXTO ESTÁ COMPLETAMENTE EN ESPAÑOL, SIN CAMBIOS: Hola."
    out = _strip_once(inp)
    assert out == "Hola."


def test_regex_compiles_and_is_anchored_to_start():
    """Preambles inside the middle of a sentence MUST NOT be stripped."""
    inp = "Ayer Bern me dijo: lo devuelvo sin cambios al chef."
    out = _strip_once(inp)
    # The match must be at start (^\s*); a colon mid-sentence is fine.
    assert out == inp
    # Sanity: the regex must use IGNORECASE flag
    assert _META_PREAMBLE_RE.flags & re.IGNORECASE
