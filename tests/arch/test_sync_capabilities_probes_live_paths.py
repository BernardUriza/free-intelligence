"""The DNA generator must probe paths that EXIST, and must never amputate.

`scripts/sync_capabilities.py` rewrites Insult's Self-Awareness block on every
commit, from file-existence probes. That design has one failure mode and it
fired for six weeks: when the probed paths die, every probe answers False, the
capability bullets vanish, and NOTHING goes red — an absent module is
indistinguishable from a removed capability.

It happened. The purga (2f8d9ad, 2026-07-14) deleted `personas/insult/`, which
was where all nine probes pointed. The first commit after it silently stripped
TTS, web search, transcription, reminders, deep memory and HTML artifacts from
Insult's DNA, and it stayed stripped until 2026-08-25. Alex found the sibling
half on Windows: without `fi-core` importable the script also deleted the
fi-core detector block and the hook `git add`ed the amputation.

These tests are what makes the next rot loud.
"""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "sync_capabilities.py"


def _load():
    spec = importlib.util.spec_from_file_location("sync_capabilities", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SYNC = _load()


@pytest.mark.parametrize("capability", sorted(SYNC.CAPABILITY_PATHS))
def test_every_probed_path_still_exists(capability: str) -> None:
    """A probe pointing at a deleted module reads as 'capability removed'."""
    path = SYNC.CAPABILITY_PATHS[capability]
    assert path.exists(), (
        f"sync_capabilities probes {path.relative_to(ROOT)} for '{capability}', "
        "and it is gone. Repoint the probe at the live module or delete the "
        "capability on purpose — leaving it is how Insult's DNA loses a "
        "capability with nothing turning red."
    )


def test_the_committed_dna_matches_what_the_generator_produces() -> None:
    """Otherwise the drift lands on whoever commits next, unreviewed."""
    content = SYNC.PERSONA.read_text(encoding="utf-8")
    block = SYNC.build_capabilities_block(previous=content)
    start = content.index(SYNC.START_MARKER)
    end = content.index(SYNC.END_MARKER) + len(SYNC.END_MARKER)
    assert content[start:end] == block, (
        "shared/personas/insult.md is out of sync with sync_capabilities.py. "
        "Run `python scripts/sync_capabilities.py` and commit the result."
    )


def test_a_missing_fi_core_preserves_the_detector_block_instead_of_deleting_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact amputation Alex hit on a laptop without the conda env."""
    real_import = builtins.__import__

    def no_fi_core(name, *args, **kwargs):
        if name.startswith("fi_core"):
            raise ImportError("simulated: machine without fi-core")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_fi_core)
    assert SYNC.extract_fi_core_mcp_tools() == []

    content = SYNC.PERSONA.read_text(encoding="utf-8")
    block = SYNC.build_capabilities_block(previous=content)
    detectors = [line for line in block.splitlines() if line.startswith("- `mcp__fi-core-persona__")]
    assert detectors, (
        "fi-core is declared in environment.yml but not importable here, and the "
        "generator dropped the detector block instead of preserving it. That "
        "deletion is what the pre-commit hook stages for you."
    )
