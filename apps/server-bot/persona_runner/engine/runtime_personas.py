"""Personas created at runtime — durable in Postgres, materialized as DNA files.

The runner resolves a persona by FILE (`persona_files.resolve_persona_path`) and by
registry entry (`persona_for`). A runtime persona gets both without a deploy: its
newest row is written to ``RUNTIME_PERSONAS_DIR/<id>.md`` and kept in an in-process
map, at boot (`hydrate`) and on every write (`save`). Postgres is the truth; the
directory and the map are a cache any replica rebuilds from it.

The image's own personas are never shadowed: an id the static registry or
``PERSONAS_DIR`` already owns is refused, so a runtime write can never rewrite
Insult or Astra.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol

import structlog

from persona_core.memory.repositories.runtime_personas import RuntimePersonaRow
from persona_runner.core import config
from shared.personas import Persona, get_persona

log = structlog.get_logger()

PROVIDERS = frozenset({"claude", "codex"})
MAX_DNA_CHARS = 200_000
_RUNTIME: dict[str, Persona] = {}


class RuntimePersonaError(ValueError):
    """The write is refused: bad id, an id the image owns, or an invalid body."""


class _Repo(Protocol):
    async def append(self, **kwargs) -> int: ...

    async def latest(self) -> list[RuntimePersonaRow]: ...


def lookup(persona_id: str) -> Persona | None:
    return _RUNTIME.get(persona_id)


def path_for(persona_id: str) -> Path | None:
    candidate = config.RUNTIME_PERSONAS_DIR / f"{persona_id}.md"
    return candidate if persona_id in _RUNTIME and candidate.exists() else None


def persona_for(persona_id: str) -> Persona | None:
    """The registry entry for an id: the image's first, then a runtime one."""
    return get_persona(persona_id) or lookup(persona_id)


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _materialize(row: RuntimePersonaRow) -> None:
    _write_atomic(config.RUNTIME_PERSONAS_DIR / f"{row.persona_id}.md", row.dna)
    _RUNTIME[row.persona_id] = Persona(
        persona_id=row.persona_id,
        display_name=row.display_name,
        persona_file=f"{row.persona_id}.md",
        token_env="",  # nosec B106 — env-var NAME (none: no Discord door), not a secret
        gateway_enabled=False,
        provider=row.provider,
        model=row.model,
    )


def validate(persona_id: str, display_name: str, provider: str, model: str | None, dna: str) -> None:
    if not config.PERSONA_ID_RE.match(persona_id):
        raise RuntimePersonaError(f"persona_id {persona_id!r} must match {config.PERSONA_ID_RE.pattern}")
    if get_persona(persona_id) is not None or (config.PERSONAS_DIR / f"{persona_id}.md").exists():
        raise RuntimePersonaError(f"persona_id {persona_id!r} belongs to the image and cannot be rewritten")
    if provider not in PROVIDERS:
        raise RuntimePersonaError(f"provider {provider!r} not one of {sorted(PROVIDERS)}")
    if provider != "claude" and not model:
        raise RuntimePersonaError(f"provider {provider!r} needs a model")
    if not display_name.strip():
        raise RuntimePersonaError("display_name is empty")
    if not dna.strip() or len(dna) > MAX_DNA_CHARS:
        raise RuntimePersonaError(f"dna must be 1..{MAX_DNA_CHARS} characters")


async def save(
    repo: _Repo,
    *,
    persona_id: str,
    display_name: str,
    provider: str,
    model: str | None,
    dna: str,
    created_by: str | None,
) -> int:
    """Append a version and serve it from the next turn on. Returns the version."""
    model = None if provider == "claude" else (model or None)
    validate(persona_id, display_name, provider, model, dna)
    version = await repo.append(
        persona_id=persona_id, display_name=display_name, provider=provider, model=model, dna=dna, created_by=created_by
    )
    _materialize(RuntimePersonaRow(persona_id, display_name, provider, model, dna, version))
    log.info(
        "runtime_persona_saved", persona_id=persona_id, provider=provider, model=model, version=version, chars=len(dna)
    )
    return version


async def hydrate(repo: _Repo) -> int:
    """Materialize the newest version of every runtime persona. Never raises."""
    try:
        rows = await repo.latest()
    except Exception:
        log.exception("runtime_personas_hydrate_failed")
        return 0
    for row in rows:
        if get_persona(row.persona_id) is None:
            _materialize(row)
    log.info("runtime_personas_hydrated", count=len(_RUNTIME))
    return len(_RUNTIME)
