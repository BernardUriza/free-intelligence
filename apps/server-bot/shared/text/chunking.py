"""Discord-safe text chunking.

Discord rejects messages over 2000 characters. We leave a small buffer
for trailing markers (version tag, footnote, etc.) by defaulting to 1990.

Two strategies live here, both shared between bots:

- `chunk_hard`: deterministic slicing on a fixed boundary. Used by Insult
  for its `[SEND]`-delimited multi-message responses where each part is
  already a paragraph and we just need to fit Discord's hard cap.
- `chunk_paragraph_aware`: prefer breaking on `\\n\\n` or `\\n` to avoid
  cutting sentences. Used by ALICE for monolithic LLM responses where
  the bot wrote one long block and the chunker has to find readable seams.

Both functions guarantee no chunk exceeds the cap. Both fall back to a
hard slice if no break exists below the cap.
"""

DISCORD_MAX_CHARS = 1990


def chunk_hard(text: str, max_chars: int = DISCORD_MAX_CHARS) -> list[str]:
    """Slice text into fixed-size chunks. No semantic awareness."""
    return [text[j : j + max_chars] for j in range(0, len(text), max_chars)]


def chunk_paragraph_aware(text: str, max_chars: int = DISCORD_MAX_CHARS) -> list[str]:
    """Prefer `\\n\\n` then `\\n` boundaries; fall back to a hard slice."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        split = remaining.rfind("\n\n", 0, max_chars)
        if split == -1:
            split = remaining.rfind("\n", 0, max_chars)
        if split == -1:
            split = max_chars
        chunks.append(remaining[:split].rstrip())
        remaining = remaining[split:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks
