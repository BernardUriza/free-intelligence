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

    def create(self, owner: str, name: str | None) -> dict:
        """Mint a project owned by ``owner``. The id (= corpus_id) is a server
        UUIDv4 — unguessable, never client-supplied."""
        project = {
            "id": f"project-{uuid.uuid4()}",
            "name": (name or "Proyecto").strip() or "Proyecto",
            "createdAt": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "ownerId": owner,
        }
        with self._lock:
            data = self._load()
            data[project["id"]] = project
            self._save(data)
        return project

    def get(self, project_id: str) -> dict | None:
        return self._load().get(project_id)

    def list_for(self, owner: str) -> list[dict]:
        return [p for p in self._load().values() if p.get("ownerId") == owner]

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
