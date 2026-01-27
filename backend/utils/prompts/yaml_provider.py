"""Prompt provider extension to handle legacy YAML presets.

This module provides compatibility with the existing YAML prompt presets
while allowing them to be integrated into the new fi_prompts system.
"""

from __future__ import annotations

from string import Template
from typing import Any

import os
import yaml
from backend.utils.common.logging.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)


class YAMLPromptProvider:
    """Handles legacy YAML prompt presets for integration with the new prompt system."""

    def __init__(self, yaml_dir: str | None = None):
        """Initialize the YAML prompt provider."""
        self.yaml_dir = Path(yaml_dir or os.getenv("YAML_PROMPTS_DIR", "backend/prompts"))

        if not self.yaml_dir.exists():
            logger.warning(f"YAML prompts directory does not exist: {self.yaml_dir}")
            self._yaml_presets = {}
        else:
            self._yaml_presets = self._load_yaml_presets()

    def _load_yaml_presets(self) -> dict[str, dict[str, Any]]:
        """Load all YAML prompt presets from the directory."""
        presets = {}

        for yaml_file in self.yaml_dir.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    preset_data = yaml.safe_load(f)

                preset_id = preset_data.get("preset_id", yaml_file.stem)
                presets[preset_id] = preset_data
            except Exception as e:
                logger.warning(f"Failed to load YAML preset {yaml_file}: {e}")

        logger.info(f"Loaded {len(presets)} YAML prompt presets from {self.yaml_dir}")
        return presets

    def get_yaml_preset(self, preset_id: str) -> dict[str, Any] | None:
        """Get a specific YAML preset by ID."""
        return self._yaml_presets.get(preset_id)

    def get_yaml_system_prompt(self, preset_id: str) -> str | None:
        """Extract the system prompt from a YAML preset."""
        preset = self._yaml_presets.get(preset_id)
        if not preset:
            return None
        return preset.get("system_prompt", "")

    def get_yaml_llm_config(self, preset_id: str) -> dict[str, Any] | None:
        """Extract the LLM configuration from a YAML preset."""
        preset = self._yaml_presets.get(preset_id)
        if not preset:
            return None
        return preset.get("llm", {})

    def convert_yaml_to_template(self, preset_id: str, **kwargs: Any) -> str | None:
        """Convert a YAML preset to a filled template using provided parameters."""
        system_prompt = self.get_yaml_system_prompt(preset_id)
        if not system_prompt:
            return None

        try:
            # Use Template to fill the system prompt with provided parameters
            template = Template(system_prompt)
            return template.safe_substitute(**kwargs)
        except Exception as e:
            logger.error(f"Failed to convert YAML preset {preset_id} to template: {e}")
            return None


# Integration function to combine both systems
def get_enhanced_prompt(prompt_type: str, **kwargs: Any) -> str:
    """Get a prompt from either the new template system or the legacy YAML presets.

    Args:
        prompt_type: The type of prompt to retrieve
        **kwargs: Parameters to fill into the prompt template

    Returns:
        Formatted prompt string with all placeholders filled
    """
    from backend.utils.prompts.prompt_provider import get_prompt as get_new_prompt

    # First try the new template system
    try:
        return get_new_prompt(prompt_type, **kwargs)
    except ValueError:
        # If not found, try the YAML preset system
        yaml_provider = YAMLPromptProvider()
        yaml_result = yaml_provider.convert_yaml_to_template(prompt_type, **kwargs)

        if yaml_result is not None:
            logger.info(f"Retrieved prompt from YAML preset: {prompt_type}")
            return yaml_result
        else:
            # If not found in either system, raise the original error
            available_new = get_new_prompt.__globals__[
                "get_prompt_provider"
            ]().list_available_prompts()
            available_yaml = list(yaml_provider._yaml_presets.keys())
            all_available = available_new + available_yaml

            raise ValueError(f"Prompt type '{prompt_type}' not found. Available: {all_available}")
