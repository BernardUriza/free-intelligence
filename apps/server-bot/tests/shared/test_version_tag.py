"""One deploy tag, every persona's mouth — the version affordance is SHARED.

Before 2026-07-08 Insult wore a hand-bumped literal, legacy-ALICE built a
divergent tag from her own dead 0.1.x semver, and the gateway siblings wore
nothing: 'which build answered?' was only answerable for 1 of 4 personas.
"""

from __future__ import annotations

import re

from persona_core.version import VERSION_TAG


def test_tag_is_superscript_version_shape():
    assert VERSION_TAG.startswith("ᵛ")
    assert "·" in VERSION_TAG


def test_tag_tracks_the_monorepo_version():
    import tomllib
    from pathlib import Path

    raw = (Path(__file__).parents[2] / "pyproject.toml").read_text()
    version = tomllib.loads(raw)["project"]["version"]
    superscript = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    assert "ᵛ" + version.translate(superscript).replace(".", "·") == VERSION_TAG


def test_gateway_appends_tag_within_discord_limit():
    from persona_gateway.gateway import DISCORD_LIMIT

    assert DISCORD_LIMIT + len(f"\n-# {VERSION_TAG}") <= 2000 + len(f"\n-# {VERSION_TAG}")
    assert re.fullmatch(r"ᵛ[⁰¹²³⁴⁵⁶⁷⁸⁹·]+", VERSION_TAG)
