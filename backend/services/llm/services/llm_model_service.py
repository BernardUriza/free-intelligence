"""LLM Model Service - Manages AI model configurations.

Handles CRUD operations for LLM models stored in YAML config.
Provides caching and validation for model management.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

import os
import yaml
from backend.models.llm_model import (
    CostTier,
    LLMModel,
    LLMModelCreate,
    LLMModelUpdate,
    LLMProvider,
)
from pathlib import Path

# Config file path
CONFIG_DIR = Path(__file__).parent.parent / "config"
LLM_MODELS_FILE = CONFIG_DIR / "llm_models.yaml"


class LLMModelService:
    """Service for managing LLM model configurations."""

    _instance: ClassVar[LLMModelService | None] = None
    _models_cache: ClassVar[dict[str, LLMModel]] = {}
    _cache_timestamp: ClassVar[float | None] = None

    def __new__(cls) -> LLMModelService:
        """Singleton pattern for service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _parse_datetime(self, value: str | datetime | None) -> datetime:
        """Parse datetime from various formats (robust to YAML serialization quirks)."""
        if value is None:
            return datetime.utcnow()
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return datetime.utcnow()

        # Normalize: remove trailing Z if there's already a timezone offset
        # e.g., "2025-01-01T00:00:00+00:00Z" -> "2025-01-01T00:00:00+00:00"
        normalized = value.rstrip("Z")

        # If no timezone info, add UTC
        if "+" not in normalized and "-" not in normalized[10:]:
            normalized += "+00:00"

        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            # Fallback: try replacing Z with +00:00 for simple ISO format
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.utcnow()

    def _load_from_yaml(self) -> dict[str, LLMModel]:
        """Load models from YAML file."""
        if not LLM_MODELS_FILE.exists():
            return {}

        with open(LLM_MODELS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "models" not in data:
            return {}

        models = {}
        for item in data["models"]:
            try:
                model = LLMModel(
                    id=item["id"],
                    label=item["label"],
                    provider=LLMProvider(item["provider"]),
                    cost_tier=CostTier(item["cost_tier"]),
                    max_tokens=item.get("max_tokens", 4096),
                    context_window=item.get("context_window", 128000),
                    is_active=item.get("is_active", True),
                    description=item.get("description"),
                    size_bytes=item.get("size_bytes"),
                    ram_required_gb=item.get("ram_required_gb"),
                    created_at=self._parse_datetime(item.get("created_at")),
                    updated_at=self._parse_datetime(item.get("updated_at")),
                )
                models[model.id] = model
            except (KeyError, ValueError) as e:
                print(f"Warning: Failed to load model {item.get('id', 'unknown')}: {e}")
                continue

        return models

    def _save_to_yaml(self, models: dict[str, LLMModel]) -> None:
        """Save models to YAML file."""
        data = {
            "models": [
                {
                    "id": m.id,
                    "label": m.label,
                    "provider": m.provider if isinstance(m.provider, str) else m.provider.value,
                    "cost_tier": m.cost_tier if isinstance(m.cost_tier, str) else m.cost_tier.value,
                    "max_tokens": m.max_tokens,
                    "context_window": m.context_window,
                    "is_active": m.is_active,
                    "description": m.description,
                    "size_bytes": m.size_bytes,
                    "ram_required_gb": m.ram_required_gb,
                    "created_at": m.created_at.isoformat() + "Z",
                    "updated_at": m.updated_at.isoformat() + "Z",
                }
                for m in models.values()
            ]
        }

        # Ensure config directory exists
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Write with atomic rename for safety
        temp_file = LLM_MODELS_FILE.with_suffix(".yaml.tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        temp_file.rename(LLM_MODELS_FILE)

    def _get_cache(self) -> dict[str, LLMModel]:
        """Get models from cache, reloading if file changed."""
        if not LLM_MODELS_FILE.exists():
            self._models_cache = {}
            self._cache_timestamp = None
            return self._models_cache

        file_mtime = os.path.getmtime(LLM_MODELS_FILE)

        if self._cache_timestamp is None or file_mtime > self._cache_timestamp:
            self._models_cache = self._load_from_yaml()
            self._cache_timestamp = file_mtime

        return self._models_cache

    def _invalidate_cache(self) -> None:
        """Force cache reload on next access."""
        self._cache_timestamp = None

    def list_models(self, include_inactive: bool = False) -> list[LLMModel]:
        """List all LLM models.

        Args:
            include_inactive: Include inactive models in results

        Returns:
            List of LLMModel objects
        """
        models = self._get_cache()
        if include_inactive:
            return list(models.values())
        return [m for m in models.values() if m.is_active]

    def get_model(self, model_id: str) -> LLMModel | None:
        """Get a specific model by ID.

        Args:
            model_id: Model identifier

        Returns:
            LLMModel or None if not found
        """
        models = self._get_cache()
        return models.get(model_id)

    def create_model(self, data: LLMModelCreate) -> LLMModel:
        """Create a new LLM model.

        Args:
            data: Model creation data

        Returns:
            Created LLMModel

        Raises:
            ValueError: If model ID already exists
        """
        models = self._get_cache()

        if data.id in models:
            raise ValueError(f"Model with ID '{data.id}' already exists")

        now = datetime.utcnow()
        model = LLMModel(
            id=data.id,
            label=data.label,
            provider=data.provider,
            cost_tier=data.cost_tier,
            max_tokens=data.max_tokens,
            context_window=data.context_window,
            is_active=data.is_active,
            description=data.description,
            size_bytes=data.size_bytes,
            ram_required_gb=data.ram_required_gb,
            created_at=now,
            updated_at=now,
        )

        models[model.id] = model
        self._save_to_yaml(models)
        self._invalidate_cache()

        return model

    def update_model(self, model_id: str, data: LLMModelUpdate) -> LLMModel | None:
        """Update an existing LLM model.

        Args:
            model_id: Model identifier
            data: Update data

        Returns:
            Updated LLMModel or None if not found
        """
        models = self._get_cache()

        if model_id not in models:
            return None

        model = models[model_id]
        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if value is not None:
                setattr(model, key, value)

        model.updated_at = datetime.utcnow()
        models[model_id] = model

        self._save_to_yaml(models)
        self._invalidate_cache()

        return model

    def delete_model(self, model_id: str, hard_delete: bool = False) -> bool:
        """Delete or deactivate an LLM model.

        Args:
            model_id: Model identifier
            hard_delete: If True, permanently remove; otherwise soft delete

        Returns:
            True if operation succeeded
        """
        models = self._get_cache()

        if model_id not in models:
            return False

        if hard_delete:
            del models[model_id]
        else:
            models[model_id].is_active = False
            models[model_id].updated_at = datetime.utcnow()

        self._save_to_yaml(models)
        self._invalidate_cache()

        return True

    def get_models_by_provider(self, provider: LLMProvider) -> list[LLMModel]:
        """Get all models from a specific provider.

        Args:
            provider: LLM provider

        Returns:
            List of models from that provider
        """
        models = self._get_cache()
        provider_value = provider if isinstance(provider, str) else provider.value
        return [m for m in models.values() if m.provider == provider_value and m.is_active]


# Global service instance
llm_model_service = LLMModelService()
