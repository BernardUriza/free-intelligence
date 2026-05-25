"""Typed representations of cognitive prompt presets.

Zero-dep core: importing this module pulls no third-party deps. The common
fields shared by every preset are typed; everything preset-specific
(``validation``, ``cache``, ``examples``, ``metadata``, ``urgency_rules``,
``required_fields``, ``phi_redaction`` …) is preserved verbatim in ``raw``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMConfig:
    """The ``llm:`` block of a preset (provider/model/sampling)."""

    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "LLMConfig":
        d = d or {}
        known = {"provider", "model", "temperature", "max_tokens", "stream"}
        return cls(
            provider=d.get("provider"),
            model=d.get("model"),
            temperature=d.get("temperature"),
            max_tokens=d.get("max_tokens"),
            stream=d.get("stream"),
            raw={k: v for k, v in d.items() if k not in known},
        )


@dataclass(frozen=True)
class CognitivePreset:
    """A cognitive-flow prompt preset (one step of the clinical loop).

    Common fields are typed; the full source dict is kept in ``raw`` so
    nothing is lost — use :meth:`get` for preset-specific keys.
    """

    preset_id: str
    system_prompt: str
    llm: LLMConfig
    name: str | None = None
    version: str | None = None
    description: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: Any) -> "CognitivePreset":
        # ``d`` comes straight from yaml.safe_load — could be None/list/scalar.
        if not isinstance(d, dict):
            raise ValueError("preset source must be a mapping")
        preset_id = d.get("preset_id")
        if not preset_id:
            raise ValueError("preset is missing required 'preset_id'")
        return cls(
            preset_id=preset_id,
            system_prompt=d.get("system_prompt", ""),
            llm=LLMConfig.from_dict(d.get("llm")),
            name=d.get("name"),
            version=d.get("version"),
            description=d.get("description"),
            raw=dict(d),
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Read any field from the underlying preset source.

        Use this for preset-specific keys not promoted to attributes, e.g.
        ``preset.get("urgency_rules")`` or ``preset.get("validation")``.
        """
        return self.raw.get(key, default)
