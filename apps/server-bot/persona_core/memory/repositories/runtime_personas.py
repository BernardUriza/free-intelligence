"""Runtime personas — the DNA of a persona created after the image was built.

Append-only (`runtime_personas`): `append` adds a version, `latest` returns the
newest row per persona id. Nothing here decides who may write; the runner's
bearer gate does, and the runner refuses ids that the static registry owns.
"""

from __future__ import annotations

from dataclasses import dataclass

from persona_core.memory.base import BaseRepository


@dataclass(frozen=True)
class RuntimePersonaRow:
    persona_id: str
    display_name: str
    provider: str
    model: str | None
    dna: str
    version: int


_APPEND_SQL = """
INSERT INTO runtime_personas (persona_id, display_name, provider, model, dna, created_by)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id
"""

_LATEST_SQL = """
SELECT DISTINCT ON (persona_id) id, persona_id, display_name, provider, model, dna
FROM runtime_personas
ORDER BY persona_id, id DESC
"""


class RuntimePersonasRepository(BaseRepository):
    async def append(
        self, *, persona_id: str, display_name: str, provider: str, model: str | None, dna: str, created_by: str | None
    ) -> int:
        return await self._fetchval(_APPEND_SQL, persona_id, display_name, provider, model, dna, created_by)

    async def latest(self) -> list[RuntimePersonaRow]:
        rows = await self._fetch(_LATEST_SQL)
        return [
            RuntimePersonaRow(
                persona_id=r["persona_id"],
                display_name=r["display_name"],
                provider=r["provider"],
                model=r["model"],
                dna=r["dna"],
                version=r["id"],
            )
            for r in rows
        ]
