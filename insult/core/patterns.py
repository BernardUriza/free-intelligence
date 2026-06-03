"""Shared pattern primitives reused across detectors.

Today this module exposes only `COMMON_STOPWORDS`, the 15-word ES+EN core
that is currently duplicated across four stopword sets (`_QUOTE_*` in
character, `_QUALITY_*` in quality, `_STANCE_*` in stance_log,
`_RECALL_*` in presets). The full lists differ — each detector layers
its own extras on top — but the core does not, so changes to it should
land here once instead of in four places.

Intentionally NOT a home for compiled regex registries. Each detector's
regex set is highly specific to its domain (character-break detection,
preset classification, anti-pattern monitoring); centralizing those
behind a generic registry would obscure intent without saving lines.
`style.py::LANG_STOPWORDS` is also intentionally excluded — that's a
language-detection lookup, not a content-word filter.
"""

from __future__ import annotations

import re


def count_pattern_hits(text: str, patterns: list[re.Pattern]) -> int:
    """How many patterns in the list produced at least one match in the text.

    The canonical one-liner shared by the preset classifier and the flows
    analyzers (which re-export it as ``count_hits``). Lives here so there's a
    single implementation instead of a copy per detector package.
    """
    return sum(1 for p in patterns if p.search(text))


# Verified by intersection of _QUOTE / _QUALITY / _STANCE / _RECALL stopwords
# (see git history of insult/core/{character,quality,stance_log,presets}.py).
# frozenset because these are read-only and shared across modules.
COMMON_STOPWORDS: frozenset[str] = frozenset(
    {
        "de",
        "la",
        "el",
        "en",
        "que",
        "es",
        "un",
        "una",
        "y",
        "a",
        "no",
        "se",
        "lo",
        "the",
        "is",
    }
)
