"""Builder for Ollama prompt templates.

Handles loading and managing system prompts for medical SOAP extraction.
Supports loading from external files for better testability and maintainability.

Updated: 2026-02-01 (Phase 2.3 Venus - DI migration for IPresetLoader)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from backend.schemas.llm.interfaces.ipreset_loader import IPresetLoader

from backend.utils.common.logging.logger import get_logger
from pathlib import Path

__all__ = ["OllamaPromptBuilder"]

logger = get_logger(__name__)


class OllamaPromptBuilder:
    """Builds and manages prompts for Ollama LLM queries.

    Loads system prompts from external template files or PresetLoader.
    Supports preset-based configuration for better prompt engineering.
    """

    def __init__(
        self,
        prompt_dir: Union[Path, str] | None = None,
        use_preset: bool = True,
        preset_loader: "IPresetLoader | None" = None,
    ):
        """Initialize prompt builder.

        Args:
            prompt_dir: Directory containing prompt template files.
                       Defaults to prompts/ subdirectory in current module.
            use_preset: If True, load from soap_generator preset (REQUIRES preset_loader).
                       If False, use file-based prompts only.
            preset_loader: IPresetLoader instance (REQUIRED if use_preset=True).

        Raises:
            ValueError: If use_preset=True but preset_loader is None.

        Note:
            Phase 2.3 Critical Fix: No more fallbacks to service locator.
            For DI compliance, pass preset_loader from dependencies.py.
        """
        self.prompt_dir = (
            Path(__file__).parent / "prompts" if prompt_dir is None else Path(prompt_dir)
        )
        self._prompt_cache: dict[str, str] = {}
        self.use_preset = use_preset
        self.preset = None

        # Load SOAP generator preset if enabled
        if self.use_preset:
            if preset_loader is None:
                raise ValueError(
                    "OllamaPromptBuilder with use_preset=True requires preset_loader. "
                    "Use get_preset_loader_dep() from backend.services.workflow.dependencies, "
                    "or set use_preset=False for file-based prompts only."
                )
            try:
                self.preset = preset_loader.load_preset("soap_generator")
                logger.info(
                    "SOAP_PRESET_LOADED",
                    preset_id=self.preset.preset_id,
                    version=self.preset.version,
                    temperature=self.preset.temperature,
                )
            except Exception as e:
                logger.warning(
                    "SOAP_PRESET_LOAD_FAILED",
                    error=str(e),
                    hint="Falling back to file-based prompts",
                )
                self.preset = None

        logger.info(
            "OllamaPromptBuilder initialized",
            prompt_dir=str(self.prompt_dir),
            using_preset=self.preset is not None,
        )

    def load_system_prompt(self, filename: str = "medical_soap_extraction.txt") -> str:
        """Load system prompt from preset or external file.

        Priority: Preset > File cache > File load

        Args:
            filename: Name of the prompt file (default: medical_soap_extraction.txt)
                     Only used if preset unavailable.

        Returns:
            System prompt content

        Raises:
            FileNotFoundError: If prompt file not found and preset unavailable
            IOError: If prompt file cannot be read
        """
        # Priority 1: Use preset if available
        if self.preset:
            logger.debug(
                "PROMPT_LOADED_FROM_PRESET",
                preset_id=self.preset.preset_id,
                length=len(self.preset.system_prompt),
            )
            return self.preset.system_prompt

        # Priority 2: Check cache
        if filename in self._prompt_cache:
            return self._prompt_cache[filename]

        # Priority 3: Load from file
        prompt_path = self.prompt_dir / filename
        if not prompt_path.exists():
            logger.error(
                "PROMPT_FILE_NOT_FOUND",
                filename=filename,
                path=str(prompt_path),
            )
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        try:
            content = prompt_path.read_text(encoding="utf-8").strip()
            self._prompt_cache[filename] = content

            logger.debug(
                "PROMPT_LOADED_FROM_FILE",
                filename=filename,
                length=len(content),
            )

            return content

        except OSError as e:
            logger.error(
                "PROMPT_FILE_READ_ERROR",
                filename=filename,
                error=str(e),
            )
            raise

    def get_temperature(self) -> float:
        """Get temperature from preset or return default.

        Returns:
            Temperature value (0.0-1.0)
        """
        if self.preset:
            return self.preset.temperature
        return 0.3  # Default for SOAP generation

    def get_max_tokens(self) -> int:
        """Get max_tokens from preset or return default.

        Returns:
            Max tokens for LLM response
        """
        if self.preset:
            return self.preset.max_tokens
        return 4096  # Default for SOAP notes

    def build_user_prompt(self, transcription: str) -> str:
        """Format user prompt with transcription content.

        Args:
            transcription: Medical consultation transcription

        Returns:
            Formatted user prompt
        """
        return f"Medical consultation transcription:\n\n{transcription}"

    def clear_cache(self) -> None:
        """Clear the prompt cache.

        Useful for testing or reloading prompts after file changes.
        """
        self._prompt_cache.clear()
        logger.debug("PROMPT_CACHE_CLEARED")
