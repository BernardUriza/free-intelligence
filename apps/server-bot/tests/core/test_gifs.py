"""`[GIF: tag]` — a persona posts from its own curated catalog, never a URL it invented.

Discord's picker just pastes a plain URL and the client unfurls it (verified
2026-07-23 by posting as the bot over REST: both a tenor.com/view and a
media.giphy.com URL rendered). So posting is trivial; FINDING is the problem —
Tenor's API died 2026-06-30, and a model asked for "a party GIF" would
hallucinate an opaque id and post a dead link.

Mutator rule: positive (a known tag resolves to its URL and the marker leaves
the visible text) + resistance (an unknown tag posts NOTHING, a non-allowlisted
host is rejected, a persona with no catalog is unaffected, and a failed send
never costs the reply).
"""

from __future__ import annotations

from unittest.mock import patch

from persona_core.gifs import (
    MAX_GIFS_PER_TURN,
    catalog_block,
    load_catalog,
    parse_gif_tags,
    resolve_gifs,
    strip_gif_markers,
)

CATALOG = "fiesta: https://tenor.com/view/dance-gif-813685\ninocente: https://media.giphy.com/media/1TOS/giphy.gif\n"


def _with_catalog(raw: str):
    return patch("persona_core.gifs.load_guidance", return_value=raw)


def test_parses_and_strips_the_marker():
    text = "Eso amerita [GIF: fiesta] y nada más."
    assert parse_gif_tags(text) == ["fiesta"]
    assert strip_gif_markers(text) == "Eso amerita  y nada más."


def test_tag_matching_is_case_and_space_insensitive():
    assert parse_gif_tags("[GIF:  FiEsTa ]") == ["fiesta"]


def test_catalog_parses_entries_and_ignores_comments():
    with _with_catalog("# comentario\n\n" + CATALOG):
        catalog = load_catalog("insult")
    assert catalog["fiesta"].startswith("https://tenor.com/view/")
    assert len(catalog) == 2


def test_known_tag_resolves_to_its_url():
    with _with_catalog(CATALOG):
        assert resolve_gifs("insult", "toma [GIF: fiesta]") == ["https://tenor.com/view/dance-gif-813685"]


def test_unknown_tag_posts_nothing():
    """RESISTANCE: the anti-hallucination guard — a miss is silence, not a
    broken link."""
    with _with_catalog(CATALOG):
        assert resolve_gifs("insult", "toma [GIF: inventado_por_el_modelo]") == []


def test_non_allowlisted_host_is_rejected():
    """RESISTANCE: the catalog is an allowlist too — an arbitrary URL in the
    content file must not become a link-injection surface."""
    with _with_catalog("malo: https://evil.example.com/tracker.gif\n"):
        assert load_catalog("insult") == {}


def test_malformed_line_is_skipped_not_crashed():
    with _with_catalog("sin_url\nbueno: https://tenor.com/view/x-gif-1\n"):
        assert list(load_catalog("insult")) == ["bueno"]


def test_persona_without_catalog_has_the_feature_off():
    """RESISTANCE: no content → no block, no resolution, nothing changes."""
    with _with_catalog(""):
        assert resolve_gifs("frugivoro", "[GIF: fiesta]") == []
        assert catalog_block("frugivoro") is None


def test_catalog_block_lists_the_tags_for_the_model():
    with _with_catalog(CATALOG):
        block = catalog_block("insult")
    assert "fiesta" in block and "inocente" in block
    assert "[GIF: tag]" in block


def test_only_one_gif_per_turn():
    """RESISTANCE: the marker is a punchline, not a mood board."""
    with _with_catalog(CATALOG):
        urls = resolve_gifs("insult", "[GIF: fiesta] y [GIF: inocente]")
    assert len(urls) == MAX_GIFS_PER_TURN
