"""Smoke tests for ALICE — package + bridge imports.

Bar this file used to guard:
1. ALICE package imports cleanly (no ImportError, no missing deps).
2. The Insult→ALICE bridge symbols load.

The retry-helper / chunker / tool-schema tests that used to live here
(``_full_jitter``, ``_parse_retry_after``, ``_chunk_text``,
``INVOKE_ALICE_TOOL``) tested private surface of the pre-fi-runner
``alice.core.llm`` implementation. The v0.1.18 refactor delegated the
agent loop to ``fi_runner.CodexBackend``; those symbols no longer
exist (backoff + chunking + schema are owned by fi-runner now). The
tests came over to the new world as broken imports of dead names —
removed in alice 0.1.19 rather than rewritten, because the behaviors
they covered are now fi-runner's responsibility and are tested there.
"""

from __future__ import annotations


def test_alice_package_imports_cleanly():
    """All ALICE modules load without ImportError."""
    import personas.alice as alice
    from personas.alice import bot, config  # noqa: F401
    from personas.alice.api import server  # noqa: F401
    from personas.alice.cogs import chat  # noqa: F401
    from personas.alice.core import clinical_reflection, llm, memory, persona_loader  # noqa: F401

    # Guard against the 819f909 breakage: app.py imports ClinicalReflector, so the
    # symbol must exist or the whole package fails to load at boot.
    assert clinical_reflection.ClinicalReflector

    # __version__ string is a smoke check that the package metadata loads.
    # Use a shape check instead of a hard-coded value so version bumps in
    # `alice/__init__.py` don't require touching this test.
    assert alice.__version__
    assert alice.__version__.count(".") == 2  # semver shape


def test_insult_to_alice_bridge_imports_cleanly():
    """Insult's side of the bridge loads."""
    from personas.insult.core.alice_tool import execute_invoke_alice  # noqa: F401
