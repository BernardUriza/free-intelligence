"""Builder for Ollama prompt templates.

Handles loading and managing system prompts for medical SOAP extraction.
Supports loading from external files for better testability and maintainability.
"""

from __future__ import annotations

from pathlib import Path

from backend.logger import get_logger

__all__ = ["OllamaPromptBuilder"]

logger = get_logger(__name__)


class OllamaPromptBuilder:
    """Builds and manages prompts for Ollama LLM queries.

    Loads system prompts from external template files and formats user prompts.
    """

    def __init__(self, prompt_dir: Path | Optional[str] = None):
        """Initialize prompt builder.

        Args:
            prompt_dir: Directory containing prompt template files.
                       Defaults to prompts/ subdirectory in current module.
        """
        self.prompt_dir = (
            Path(__file__).parent / "prompts" if prompt_dir is None else Path(prompt_dir)
        )
        self._prompt_cache: dict[str, str] = {}

        logger.info(
            "OllamaPromptBuilder initialized",
            prompt_dir=str(self.prompt_dir),
        )

    def load_system_prompt(self, filename: str = "medical_soap_extraction.txt") -> str:
        """Load system prompt from external file.

        Caches loaded prompts in memory to avoid repeated file I/O.

        Args:
            filename: Name of the prompt file (default: medical_soap_extraction.txt)

        Returns:
            System prompt content

        Raises:
            FileNotFoundError: If prompt file not found
            IOError: If prompt file cannot be read
        """
        # Check cache first
        if filename in self._prompt_cache:
            return self._prompt_cache[filename]

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
                "PROMPT_LOADED",
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
