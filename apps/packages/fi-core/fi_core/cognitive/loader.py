"""Loader for the bundled cognitive prompt presets (YAML).

The 7 presets are the prompt layer of the Redux-Claude clinical state
machine, distilled from real production medical AI consumers:
``intake_coach``, ``soap_generator``, ``question_generator``,
``medication_extractor``, ``emotion_analyzer``, ``diarization_analyst``,
``corpus_search``.

YAML parsing requires the ``cognitive`` extra::

    pip install 'fi-core[cognitive]'
"""

from __future__ import annotations

import pathlib

from .types import CognitivePreset

_PRESETS_DIR = pathlib.Path(__file__).parent / "presets"


def _require_yaml():
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise ImportError(
            "fi_core.cognitive preset loading requires PyYAML. "
            "Install it with:  pip install 'fi-core[cognitive]'"
        ) from exc
    return yaml


def available_presets() -> list[str]:
    """Return the preset ids bundled with the package (by file stem).

    Works without the ``cognitive`` extra — it only lists files.
    """
    return sorted(p.stem for p in _PRESETS_DIR.glob("*.yaml"))


def load_preset(preset_id: str) -> CognitivePreset:
    """Load a single preset by id (e.g. ``"intake_coach"``)."""
    yaml = _require_yaml()
    path = _PRESETS_DIR / f"{preset_id}.yaml"
    if not path.exists():
        raise KeyError(
            f"No cognitive preset {preset_id!r}. "
            f"Available: {available_presets()}"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CognitivePreset.from_dict(data)


def load_all() -> dict[str, CognitivePreset]:
    """Load every bundled preset, keyed by preset id."""
    return {pid: load_preset(pid) for pid in available_presets()}
