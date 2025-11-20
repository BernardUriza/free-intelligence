from __future__ import annotations

"""
Free Intelligence - Preset Loader

Loads LLM agent presets from YAML and validates output against JSON Schema.

Philosophy: Configuration as code, validation as policy.

File: backend/preset_loader.py
Created: 2025-10-28
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
import yaml

from backend.constants import DEFAULT_OLLAMA_MODEL, LLMProvider
from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PresetConfig:
    """Preset configuration"""

    preset_id: str
    version: str
    description: str

    # LLM config
    provider: str
    model: str
    temperature: float
    max_tokens: int
    stream: bool

    # Prompts
    system_prompt: str

    # Validation
    output_schema_path: str | None
    validation_enabled: bool
    validation_strict: bool

    # Caching
    cache_enabled: bool
    cache_ttl_seconds: int
    cache_key_fields: List[str]

    # Examples (for few-shot)
    examples: list[dict[str, str]]

    # Metadata
    metadata: Dict[str, Any]


class PresetLoader:
    """
    Load and validate LLM presets from YAML.

    Features:
    - YAML preset loading
    - JSON Schema validation
    - LRU caching (by preset_id)
    - Cache key computation (hash of prompt+config)
    """

    def __init__(self, presets_dir: str | None = None, schemas_dir: str | None = None):
        """
        Initialize preset loader.

        Args:
            presets_dir: Directory with YAML presets (default: backend/prompts)
            schemas_dir: Directory with JSON schemas (default: backend/schemas)
        """
        # Default to backend/prompts and backend/schemas (absolute paths)
        if presets_dir is None:
            presets_dir = str(Path(__file__).parent.parent / "prompts")
        if schemas_dir is None:
            schemas_dir = str(Path(__file__).parent)

        self.presets_dir = Path(presets_dir)
        self.schemas_dir = Path(schemas_dir)
        self.logger = get_logger(__name__)

        self.logger.info(
            "PRESET_LOADER_INITIALIZED",
            presets_dir=str(self.presets_dir),
            schemas_dir=str(self.schemas_dir),
        )

    @lru_cache(maxsize=100)
    def load_preset(self, preset_id: str) -> PresetConfig:
        """
        Load preset from YAML file.

        Args:
            preset_id: Preset identifier (e.g., "intake_coach")

        Returns:
            PresetConfig object

        Raises:
            FileNotFoundError: If preset file not found
            ValueError: If preset YAML is invalid
        """
        preset_path = self.presets_dir / f"{preset_id}.yaml"

        if not preset_path.exists():
            self.logger.error("PRESET_NOT_FOUND", preset_id=preset_id, file_path=str(preset_path))
            raise FileNotFoundError(f"Preset not found: {preset_path}")

        self.logger.info("PRESET_LOADING_STARTED", preset_id=preset_id, file_path=str(preset_path))

        try:
            with open(preset_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Extract config
            llm_config = data.get("llm", {})
            validation_config = data.get("validation", {})
            cache_config = data.get("cache", {})

            preset = PresetConfig(
                preset_id=data["preset_id"],
                version=data["version"],
                description=data["description"],
                # LLM
                provider=llm_config.get("provider", LLMProvider.OLLAMA),
                model=llm_config.get("model", DEFAULT_OLLAMA_MODEL),
                temperature=llm_config.get("temperature", 0.7),
                max_tokens=llm_config.get("max_tokens", 2048),
                stream=llm_config.get("stream", False),
                # Prompts
                system_prompt=data["system_prompt"],
                # Validation
                output_schema_path=data.get("output_schema"),
                validation_enabled=validation_config.get("enabled", True),
                validation_strict=validation_config.get("strict", True),
                # Caching
                cache_enabled=cache_config.get("enabled", True),
                cache_ttl_seconds=cache_config.get("ttl_seconds", 3600),
                cache_key_fields=cache_config.get("key_fields", ["prompt"]),
                # Examples
                examples=data.get("examples", []),
                # Metadata
                metadata=data.get("metadata", {}),
            )

            self.logger.info(
                "PRESET_LOADED_SUCCESSFULLY",
                preset_id=preset_id,
                version=preset.version,
                provider=preset.provider,
                model=preset.model,
            )

            return preset

        except Exception as e:
            self.logger.error("PRESET_LOADING_FAILED", preset_id=preset_id, error=str(e))
            raise ValueError(f"Failed to load preset {preset_id}: {e}")

    @lru_cache(maxsize=50)
    def load_schema(self, schema_path: str) -> dict[str, Any]:
        """
        Load JSON Schema from file.

        Args:
            schema_path: Path to schema (relative to schemas_dir)

        Returns:
            JSON Schema dict

        Raises:
            FileNotFoundError: If schema file not found
            ValueError: If schema JSON is invalid
        """
        full_path = Path(schema_path)

        if not full_path.exists():
            self.logger.error("SCHEMA_NOT_FOUND", schema_path=schema_path)
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        self.logger.info("SCHEMA_LOADING_STARTED", schema_path=schema_path)

        try:
            with open(full_path, encoding="utf-8") as f:
                schema = json.load(f)

            # Validate schema itself
            jsonschema.Draft7Validator.check_schema(schema)

            self.logger.info("SCHEMA_LOADED_SUCCESSFULLY", schema_path=schema_path)

            return schema

        except Exception as e:
            self.logger.error("SCHEMA_LOADING_FAILED", schema_path=schema_path, error=str(e))
            raise ValueError(f"Failed to load schema {schema_path}: {e}")

    def validate_output(self, output: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Validate LLM output against JSON Schema.

        Args:
            output: LLM output (parsed JSON)
            schema: JSON Schema

        Returns:
            True if valid, False if invalid (or raises if strict)

        Raises:
            jsonschema.ValidationError: If validation fails and strict mode
        """
        try:
            jsonschema.validate(instance=output, schema=schema)
            self.logger.info("OUTPUT_VALIDATION_PASSED", schema_id=schema.get("$id", "unknown"))
            return True

        except jsonschema.ValidationError as e:
            self.logger.error(
                "OUTPUT_VALIDATION_FAILED", error=str(e), schema_id=schema.get("$id", "unknown")
            )
            raise

    def compute_cache_key(self, preset: PresetConfig, prompt: str, **kwargs) -> str:
        """
        Compute cache key for preset + prompt combination.

        Args:
            preset: PresetConfig
            prompt: User prompt
            **kwargs: Additional fields to include in key

        Returns:
            SHA256 hash (hex)
        """
        # Build key from configured fields
        key_parts = {"preset_id": preset.preset_id, "prompt": prompt}

        # Add cache_key_fields from preset config
        for field in preset.cache_key_fields:
            if field == "prompt":
                continue  # Already added
            elif field == "temperature":
                key_parts["temperature"] = preset.temperature
            elif field == "model":
                key_parts["model"] = preset.model
            elif field in kwargs:
                key_parts[field] = kwargs[field]

        # Compute hash
        key_string = json.dumps(key_parts, sort_keys=True)
        cache_key = hashlib.sha256(key_string.encode("utf-8")).hexdigest()

        self.logger.info("CACHE_KEY_COMPUTED", preset_id=preset.preset_id, cache_key=cache_key[:16])

        return cache_key

    def list_presets(self) -> list[str]:
        """
        List available preset IDs.

        Returns:
            List of preset IDs (filenames without .yaml)
        """
        if not self.presets_dir.exists():
            return []

        presets = [p.stem for p in self.presets_dir.glob("*.yaml")]

        self.logger.info("PRESETS_LISTED", count=len(presets))

        return presets


# Global preset loader instance
_preset_loader: PresetLoader | None = None


def get_preset_loader() -> PresetLoader:
    """Get or create global preset loader"""
    global _preset_loader

    if _preset_loader is None:
        _preset_loader = PresetLoader()

    return _preset_loader


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI interface for preset loader"""
    import argparse

    parser = argparse.ArgumentParser(description="Free Intelligence Preset Loader CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # List command
    _list_parser = subparsers.add_parser("list", help="List available presets")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load and display preset")
    load_parser.add_argument("preset_id", help="Preset ID")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate JSON against schema")
    validate_parser.add_argument("preset_id", help="Preset ID")
    validate_parser.add_argument("json_file", help="JSON file to validate")

    args = parser.parse_args()

    loader = get_preset_loader()

    if args.command == "list":
        presets = loader.list_presets()
        print("\n" + "=" * 70)
        print("📋 Available Presets")
        print("=" * 70)
        for preset_id in presets:
            preset = loader.load_preset(preset_id)
            print(f"\n  {preset_id}")
            print(f"    Version: {preset.version}")
            print(f"    Description: {preset.description}")
            print(f"    Provider: {preset.provider} ({preset.model})")
        print("\n" + "=" * 70)

    elif args.command == "load":
        preset = loader.load_preset(args.preset_id)
        print("\n" + "=" * 70)
        print(f"📋 Preset: {preset.preset_id}")
        print("=" * 70)
        print(f"\nVersion: {preset.version}")
        print(f"Description: {preset.description}")
        print("\nLLM:")
        print(f"  Provider: {preset.provider}")
        print(f"  Model: {preset.model}")
        print(f"  Temperature: {preset.temperature}")
        print(f"  Max Tokens: {preset.max_tokens}")
        print("\nValidation:")
        print(f"  Enabled: {preset.validation_enabled}")
        print(f"  Strict: {preset.validation_strict}")
        print(f"  Schema: {preset.output_schema_path}")
        print("\nCache:")
        print(f"  Enabled: {preset.cache_enabled}")
        print(f"  TTL: {preset.cache_ttl_seconds}s")
        print(f"  Key Fields: {', '.join(preset.cache_key_fields)}")
        print(f"\nExamples: {len(preset.examples)}")
        print("\n" + "=" * 70)

    elif args.command == "validate":
        preset = loader.load_preset(args.preset_id)

        if not preset.output_schema_path:
            print(f"❌ Preset {args.preset_id} has no output schema")
            return

        schema = loader.load_schema(preset.output_schema_path)

        with open(args.json_file) as f:
            output = json.load(f)

        try:
            loader.validate_output(output, schema)
            print("✅ Validation PASSED")
        except jsonschema.ValidationError as e:
            print(f"❌ Validation FAILED: {e.message}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
