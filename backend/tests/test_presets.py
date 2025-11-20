"""Tests for preset loading and validation.

Verifies that all presets load correctly and schemas are valid.
"""

from __future__ import annotations

import pytest

from backend.schemas.preset_loader import PresetLoader, get_preset_loader


class TestPresetLoader:
    """Test suite for PresetLoader"""

    def test_preset_loader_singleton(self):
        """Test that get_preset_loader returns the same instance"""
        loader1 = get_preset_loader()
        loader2 = get_preset_loader()
        assert loader1 is loader2, "PresetLoader should be a singleton"

    def test_list_presets(self):
        """Test listing all available presets"""
        loader = get_preset_loader()
        presets = loader.list_presets()

        # Should have at least our 5 presets
        assert isinstance(presets, list)
        assert len(presets) >= 5, f"Expected at least 5 presets, got {len(presets)}"

        # Check for expected presets
        expected_presets = [
            "intake_coach",
            "diarization_analyst",
            "soap_generator",
            "corpus_search",
            "emotion_analyzer",
        ]
        for preset_id in expected_presets:
            assert (
                preset_id in presets
            ), f"Expected preset '{preset_id}' not found in {presets}"

    def test_load_diarization_analyst(self):
        """Test loading diarization_analyst preset"""
        loader = get_preset_loader()
        preset = loader.load_preset("diarization_analyst")

        assert preset.preset_id == "diarization_analyst"
        assert preset.version == "1.0.0"
        assert preset.temperature == 0.2, "Diarization should use low temperature"
        assert preset.max_tokens == 2048
        assert preset.provider == "azure"
        assert "speaker classification" in preset.description.lower()
        assert len(preset.system_prompt) > 100, "System prompt should be detailed"
        assert len(preset.examples) > 0, "Should have few-shot examples"

    def test_load_soap_generator(self):
        """Test loading soap_generator preset"""
        loader = get_preset_loader()
        preset = loader.load_preset("soap_generator")

        assert preset.preset_id == "soap_generator"
        assert preset.version == "1.0.0"
        assert preset.temperature == 0.3, "SOAP should use precise temperature"
        assert preset.max_tokens == 3072, "SOAP notes can be detailed"
        assert "SOAP" in preset.description
        assert len(preset.system_prompt) > 100
        assert preset.cache_enabled is True

    def test_load_emotion_analyzer(self):
        """Test loading emotion_analyzer preset"""
        loader = get_preset_loader()
        preset = loader.load_preset("emotion_analyzer")

        assert preset.preset_id == "emotion_analyzer"
        assert preset.version == "1.0.0"
        assert preset.temperature == 0.4, "Emotion needs balanced temperature"
        assert "emotional state" in preset.description.lower()
        assert len(preset.examples) > 0, "Should have emotion examples"

    def test_load_corpus_search(self):
        """Test loading corpus_search preset"""
        loader = get_preset_loader()
        preset = loader.load_preset("corpus_search")

        assert preset.preset_id == "corpus_search"
        assert preset.version == "1.0.0"
        assert preset.temperature == 0.4
        assert "HDF5" in preset.description or "corpus" in preset.description.lower()

    def test_load_nonexistent_preset(self):
        """Test loading a preset that doesn't exist"""
        loader = get_preset_loader()

        with pytest.raises(FileNotFoundError):
            loader.load_preset("nonexistent_preset")

    def test_preset_caching(self):
        """Test that presets are cached (LRU)"""
        loader = get_preset_loader()

        # Load twice
        preset1 = loader.load_preset("diarization_analyst")
        preset2 = loader.load_preset("diarization_analyst")

        # Should be the exact same object (cached)
        assert preset1 is preset2, "Presets should be cached"

    def test_all_presets_have_required_fields(self):
        """Test that all presets have required configuration fields"""
        loader = get_preset_loader()
        presets = loader.list_presets()

        for preset_id in presets:
            preset = loader.load_preset(preset_id)

            # Required fields
            assert preset.preset_id
            assert preset.version
            assert preset.description
            assert preset.system_prompt
            assert preset.provider
            assert preset.model
            assert preset.temperature >= 0.0 and preset.temperature <= 1.0
            assert preset.max_tokens > 0
            assert isinstance(preset.cache_enabled, bool)
            assert isinstance(preset.validation_enabled, bool)

    def test_schema_loading(self):
        """Test loading JSON schemas"""
        loader = get_preset_loader()

        # These schemas should exist
        schema_paths = [
            "backend/schemas/diarization.schema.json",
            "backend/schemas/soap.schema.json",
            "backend/schemas/emotion.schema.json",
            "backend/schemas/corpus_search.schema.json",
        ]

        for schema_path in schema_paths:
            schema = loader.load_schema(schema_path)
            assert isinstance(schema, dict)
            assert "$schema" in schema or "type" in schema
            assert "properties" in schema or "type" in schema


class TestPresetIntegration:
    """Test integration with actual workflows"""

    def test_diarization_preset_in_provider(self):
        """Test that AzureGPT4Provider loads diarization preset"""
        from backend.providers.diarization import AzureGPT4Provider

        # This will fail if AZURE env vars not set, but we can test the preset loading logic
        try:
            provider = AzureGPT4Provider()
            assert provider.preset is not None, "Provider should load preset"
            assert provider.preset.preset_id == "diarization_analyst"
        except ValueError as e:
            # Expected if AZURE_OPENAI_ENDPOINT not set
            if "AZURE_OPENAI_ENDPOINT" not in str(e):
                raise

    def test_soap_preset_in_prompt_builder(self):
        """Test that OllamaPromptBuilder loads SOAP preset"""
        from backend.services.soap_generation.prompt_builder import OllamaPromptBuilder

        builder = OllamaPromptBuilder(use_preset=True)
        assert builder.preset is not None, "Builder should load preset"
        assert builder.preset.preset_id == "soap_generator"

        # Test temperature/max_tokens helpers
        assert builder.get_temperature() == 0.3
        assert builder.get_max_tokens() == 3072

    def test_emotion_preset_in_worker(self):
        """Test that emotion worker can load preset"""
        from backend.schemas.preset_loader import get_preset_loader

        loader = get_preset_loader()
        preset = loader.load_preset("emotion_analyzer")

        # Verify emotion-specific config
        assert preset.temperature == 0.4
        assert "ANXIETY" in preset.system_prompt or "emotion" in preset.system_prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
