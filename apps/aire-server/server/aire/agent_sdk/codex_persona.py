"""The casita's persona reaches Codex as `AGENTS.md` in its cwd — the project doc
`codex exec` reads at thread start, the way the Claude backend reads `CLAUDE.md`
into its system prompt (`engine/options.casita_prompt`). Written on every turn so
an edited persona takes effect on the next fresh thread; a resumed thread keeps
the instructions it opened with, exactly like Claude's warm session."""
from __future__ import annotations

from pathlib import Path

AGENTS_MD = "AGENTS.md"
PROJECT_DOC_MAX_BYTES = 1_048_576


def write_agents_md(cwd: str) -> int:
    """Materialize the casita prompt as AGENTS.md; returns the bytes written (0 =
    no persona, and a stale AGENTS.md from an earlier persona is removed)."""
    from ..engine.options import casita_prompt

    text = casita_prompt(cwd)
    path = Path(cwd) / AGENTS_MD
    if not text:
        path.unlink(missing_ok=True)
        return 0
    data = text.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)
    return len(data)
