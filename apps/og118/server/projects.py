"""ProjectRegistry — the server-authoritative project↔owner↔corpus map.

PROJ-ACCOUNT-1 completion: a project's ``corpus_id`` is minted server-side and
OWNED by the account that created it (``ownerId`` = the auth principal's sub), so
a caller can only reach corpora it owns. Persisted as JSON on the SAME Azure Files
volume as the HDF5 corpus it indexes (``OG118_PROJECT_REGISTRY_PATH``, default
next to ``FI_RAG_STORE_PATH`` at /opt/fi/data) — survives every redeploy, single
replica = single writer (chosen over SQLite to avoid a 2nd SMB file-lock surface;
Postgres is the documented post-Gate-3-SCALE path, over-provisioned now). Writes
are atomic (temp file + os.replace) under an in-process lock.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import uuid
from pathlib import Path



def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _clean(value: str | None) -> str:
    """Normalize an optional free-text field to a plain string.

    Empty and absent are the SAME state here — a description someone cleared is
    not meaningfully different from one never written — so both store ``""`` and
    the consumer never has to branch on ``None`` vs ``""``."""
    return (value or "").strip()


def _hydrate(project: dict) -> dict:
    """Fill the fields a record predating this contract never had.

    Projects minted before the index page existed carry only
    ``{id, name, createdAt, ownerId}``. Returning those raw would hand the grid a
    missing sort key and an undefined subtitle, so the read path backfills:
    ``updatedAt`` falls back to ``createdAt`` (the only honest answer — nothing
    has touched it since) and the text fields to ``""``. Backfill on READ, not a
    migration pass: the store is a single JSON rewritten under a lock, and a
    rewrite-everything-on-boot is a far bigger blast radius than a dict merge.
    """
    return {
        "description": "",
        "instructions": "",
        **project,
        "updatedAt": project.get("updatedAt") or project.get("createdAt"),
    }


class ProjectRegistry:
    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict]:
        try:
            return json.loads(self._path.read_text("utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def _save(self, data: dict[str, dict]) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data), "utf-8")
        os.replace(tmp, self._path)  # atomic on POSIX

    def create(
        self,
        owner: str,
        name: str | None,
        *,
        description: str | None = None,
        instructions: str | None = None,
    ) -> dict:
        """Mint a project owned by ``owner``. The id (= corpus_id) is a server
        UUIDv4 — unguessable, never client-supplied.

        ``description`` is the card's subtitle; ``instructions`` is the
        per-project system prompt. Both start empty and are set later via
        :meth:`update` — a project is created from a name alone."""
        now = _now()
        project = {
            "id": f"project-{uuid.uuid4()}",
            "name": (name or "Proyecto").strip() or "Proyecto",
            "description": _clean(description),
            "instructions": _clean(instructions),
            "createdAt": now,
            "updatedAt": now,
            "ownerId": owner,
        }
        with self._lock:
            data = self._load()
            data[project["id"]] = project
            self._save(data)
        return project

    def update(
        self,
        project_id: str,
        owner: str,
        *,
        name: str | None = None,
        description: str | None = None,
        instructions: str | None = None,
    ) -> dict | None:
        """Patch the fields the owner supplied; ``None`` means "leave alone".

        Returns the hydrated record, or ``None`` if it is missing or not owned —
        the caller turns both into the same 404, so a non-owner cannot probe for
        existence (ADR invariant 7, same as :meth:`owns`).

        Touches ``updatedAt`` on every accepted patch: it is the sort key of the
        index page, so a field edit that did not move it would leave the grid
        claiming the project is older than it is.
        """
        with self._lock:
            data = self._load()
            proj = data.get(project_id)
            if proj is None or proj.get("ownerId") != owner:
                return None
            if name is not None:
                cleaned = name.strip()
                if cleaned:
                    proj["name"] = cleaned
            if description is not None:
                proj["description"] = _clean(description)
            if instructions is not None:
                proj["instructions"] = _clean(instructions)
            proj["updatedAt"] = _now()
            data[project_id] = proj
            self._save(data)
        return _hydrate(proj)

    def touch(self, project_id: str, owner: str) -> None:
        """Move ``updatedAt`` without changing content — what an upload or a new
        conversation in the project means for the index's "Updated X ago"."""
        with self._lock:
            data = self._load()
            proj = data.get(project_id)
            if proj is None or proj.get("ownerId") != owner:
                return
            proj["updatedAt"] = _now()
            data[project_id] = proj
            self._save(data)

    def get(self, project_id: str) -> dict | None:
        proj = self._load().get(project_id)
        return None if proj is None else _hydrate(proj)

    def list_for(self, owner: str) -> list[dict]:
        return [_hydrate(p) for p in self._load().values() if p.get("ownerId") == owner]

    def delete(self, project_id: str, owner: str) -> bool:
        """Remove the project from the registry IF owned by ``owner``. Returns
        True if it existed and was owned (the caller also drops the corpus)."""
        with self._lock:
            data = self._load()
            proj = data.get(project_id)
            if proj is None or proj.get("ownerId") != owner:
                return False
            del data[project_id]
            self._save(data)
        return True

    def owns(self, project_id: str, owner: str) -> bool:
        """True only if ``project_id`` exists AND is owned by ``owner``. Used to
        gate upload / corpus-bind; a non-owner gets the same answer as 'missing'
        (the route returns 404, never 403 — no existence probing, ADR invariant 7)."""
        proj = self._load().get(project_id)
        return proj is not None and proj.get("ownerId") == owner
