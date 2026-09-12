"""Background jobs — la mitad DURABLE de "te aviso cuando termine" (OG118-BACKGROUND-1).

Tres piezas, ninguna con estado en memoria:

- ``JobStore``: un JSON por job en el mismo Azure Files que las conversaciones,
  bajo ``<root>/<estado>/<job_id>.json``. El estado ES el directorio, así que
  reclamar un job es un ``os.replace`` de ``pending/`` a ``running/``: atómico
  en el share, y dos ejecuciones concurrentes no pueden reclamar el mismo.
- ``Capsule``: la identidad del turno (sub + conversación + corpus) firmada con
  HMAC y con vencimiento. Viaja en la URL del MCP remoto que este runner le
  entrega a AIRE; el modelo nunca la elige ni puede forjarla. Es el equivalente
  sin Postgres de la fila ``aire_turn_principals`` de discord-bot.
- ``start_execution``: arranca el ACA Job con el token de la identidad
  administrada del contenedor (IMDS de Container Apps, sin SDK). Si no hay
  identidad o no hay rol, falla ruidoso y la tool le dice al modelo la verdad.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import httpx

PENDING, RUNNING, DONE, FAILED = "pending", "running", "done", "failed"
ESTADOS = (PENDING, RUNNING, DONE, FAILED)
MAX_GOAL_CHARS = 4000


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class JobStore:
    def __init__(self, root: str | os.PathLike) -> None:
        self._root = Path(root)
        for estado in ESTADOS:
            (self._root / estado).mkdir(parents=True, exist_ok=True)

    def _path(self, estado: str, job_id: str) -> Path:
        return self._root / estado / f"{job_id}.json"

    @staticmethod
    def _write(path: Path, job: dict) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(job), "utf-8")
        os.replace(tmp, path)

    def create(self, *, owner: str, conversation_id: str, goal: str, corpus_id: str | None) -> dict:
        goal = goal.strip()
        if not goal:
            raise ValueError("goal vacío")
        job = {
            "id": uuid.uuid4().hex,
            "owner": owner,
            "conversationId": conversation_id,
            "corpusId": corpus_id,
            "goal": goal[:MAX_GOAL_CHARS],
            "status": PENDING,
            "createdAt": _now(),
        }
        self._write(self._path(PENDING, job["id"]), job)
        return job

    def claim_next(self) -> dict | None:
        """El job pendiente más viejo, ya movido a ``running/``. ``None`` si no hay."""
        pendientes = sorted(self._root.joinpath(PENDING).glob("*.json"), key=lambda p: p.stat().st_mtime)
        for path in pendientes:
            destino = self._path(RUNNING, path.stem)
            try:
                os.replace(path, destino)
            except FileNotFoundError:
                continue
            job = json.loads(destino.read_text("utf-8"))
            job["status"], job["startedAt"] = RUNNING, _now()
            self._write(destino, job)
            return job
        return None

    def _settle(self, job: dict, estado: str, **campos: Any) -> dict:
        job = {**job, "status": estado, "finishedAt": _now(), **campos}
        self._write(self._path(estado, job["id"]), job)
        try:
            self._path(RUNNING, job["id"]).unlink()
        except FileNotFoundError:
            pass
        return job

    def finish(self, job: dict, result: str) -> dict:
        return self._settle(job, DONE, result=result)

    def fail(self, job: dict, error: str) -> dict:
        return self._settle(job, FAILED, error=error[:2000])

    def get(self, job_id: str) -> dict | None:
        for estado in ESTADOS:
            path = self._path(estado, job_id)
            if path.exists():
                return json.loads(path.read_text("utf-8"))
        return None

    def pending_for(self, owner: str, conversation_id: str) -> list[dict]:
        out = []
        for estado in (PENDING, RUNNING):
            for path in self._root.joinpath(estado).glob("*.json"):
                job = json.loads(path.read_text("utf-8"))
                if job.get("owner") == owner and job.get("conversationId") == conversation_id:
                    out.append(job)
        return out


CAPSULE_TTL_SECONDS = 30 * 60


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_capsule(secret: str, *, sub: str, conversation_id: str, corpus_id: str | None,
                 ttl: int = CAPSULE_TTL_SECONDS, now: float | None = None) -> str:
    payload = {"sub": sub, "cid": conversation_id, "corpus": corpus_id,
               "exp": int((now if now is not None else time.time()) + ttl)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    mac = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{mac}"


def verify_capsule(secret: str, capsule: str, *, now: float | None = None) -> dict | None:
    """El payload si la firma cuadra y no venció; ``None`` en cualquier otro caso."""
    if not secret or "." not in capsule:
        return None
    body, mac = capsule.rsplit(".", 1)
    esperado = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, esperado):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < (now if now is not None else time.time()):
        return None
    return payload


ARM_API_VERSION = "2024-03-01"
ARM = "https://management.azure.com"


def _managed_identity_token(resource: str = f"{ARM}/") -> str:
    """El token de la identidad del contenedor, por el IMDS de Container Apps."""
    endpoint = os.environ.get("IDENTITY_ENDPOINT", "").strip()
    header = os.environ.get("IDENTITY_HEADER", "").strip()
    if not endpoint or not header:
        raise RuntimeError("sin identidad administrada: IDENTITY_ENDPOINT/IDENTITY_HEADER ausentes")
    r = httpx.get(endpoint, params={"resource": resource, "api-version": "2019-08-01"},
                  headers={"X-IDENTITY-HEADER": header}, timeout=10.0)
    r.raise_for_status()
    return r.json()["access_token"]


def start_execution(job_resource_id: str) -> str:
    """Arranca una ejecución del ACA Job; devuelve el nombre de la ejecución."""
    token = _managed_identity_token()
    r = httpx.post(f"{ARM}{job_resource_id}/start", params={"api-version": ARM_API_VERSION},
                   headers={"Authorization": f"Bearer {token}"}, json={}, timeout=30.0)
    r.raise_for_status()
    return str(r.json().get("name") or r.headers.get("Location") or "")


Starter = Callable[[str], str]
