"""Single source of the deploy version tag — every persona's last chunk wears it.

The tag identifies the DEPLOY (monorepo version / image SHA lineage), never the
persona: the Discord face already says WHO is speaking; the tag says WHICH build
answered. Unified 2026-07-08 — before this, Insult wore a hand-bumped superscript
literal, legacy-ALICE built a divergent `ᵃ0·1·22` from her own dead semver, and
the gateway siblings (Vultur/Frugívoro/ALICE) wore nothing at all.

Bumped per commit by the pre-commit hook trio (pyproject.toml,
personas/insult/__init__.py, this file).
"""

VERSION_TAG = "ᵛ⁴·²³·⁴"
