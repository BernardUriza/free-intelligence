"""Where the engine's own prompts live; `fi_core.prompts.load_prompt` reads them."""

from __future__ import annotations

from pathlib import Path

SHARED_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts_md"
