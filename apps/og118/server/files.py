"""FileStore: an account's binary files (a PDF, an ``.h5``, anything) on the durable volume.

Layout: ``<root>/<sha256(owner)[:32]>/<file_id>.bin`` beside ``<file_id>.json`` (its
metadata), next to the conversations on the Azure Files share. Ownership is structural,
as in ``ConversationStore``: another account's id resolves to "missing". The bytes are
streamed to a temp file and renamed, so a cut upload never leaves a half file behind.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import threading
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

from conversations import utc_now_iso
from fi_core.text import digest

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f/\\]")
MAX_NAME_CHARS = 200
_CONTENT_TYPE = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+(; ?charset=[A-Za-z0-9_-]+)?$")
FALLBACK_CONTENT_TYPE = "application/octet-stream"


class FileTooLarge(Exception):
    """One upload went past the per-file cap."""


class QuotaExceeded(Exception):
    """The upload would take the account past its total."""


def valid_file_id(file_id: str) -> bool:
    return bool(_ID_RE.match(file_id))


def clean_content_type(content_type: str) -> str:
    """A media type safe to send back as a header; anything else is opaque bytes."""
    return content_type if _CONTENT_TYPE.match(content_type) else FALLBACK_CONTENT_TYPE


def clean_name(name: str) -> str:
    """A display name with no path and no control characters; never empty."""
    cleaned = _UNSAFE_NAME.sub("_", name).strip().strip(".")[:MAX_NAME_CHARS]
    return cleaned or "file"


class FileStore:
    def __init__(self, root: str | os.PathLike, max_file_bytes: int, quota_bytes: int) -> None:
        self._root = Path(root)
        self._max_file_bytes = max_file_bytes
        self._quota_bytes = quota_bytes
        self._lock = threading.Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    def _owner_dir(self, owner: str) -> Path:
        return self._root / digest(owner)

    def list_for(self, owner: str) -> list[dict]:
        """The owner's files as metadata, newest first."""
        owner_dir = self._owner_dir(owner)
        if not owner_dir.is_dir():
            return []
        found = [meta for path in owner_dir.glob("*.json") if (meta := self._read_meta(path))]
        found.sort(key=lambda m: m.get("createdAt") or "", reverse=True)
        return found

    def usage(self, owner: str) -> dict:
        return {
            "usedBytes": sum(m.get("size", 0) for m in self.list_for(owner)),
            "quotaBytes": self._quota_bytes,
            "maxFileBytes": self._max_file_bytes,
        }

    def get(self, owner: str, file_id: str) -> tuple[dict, Path] | None:
        """The metadata and the path of the bytes, or None when it is not the owner's."""
        if not valid_file_id(file_id):
            return None
        owner_dir = self._owner_dir(owner)
        meta = self._read_meta(owner_dir / f"{file_id}.json")
        blob = owner_dir / f"{file_id}.bin"
        if meta is None or not blob.is_file():
            return None
        return meta, blob

    async def save(
        self,
        owner: str,
        name: str,
        content_type: str,
        chunks: AsyncIterator[bytes],
        conversation_id: str | None = None,
    ) -> dict:
        """Stream one upload to disk and return its metadata."""
        owner_dir = self._owner_dir(owner)
        owner_dir.mkdir(parents=True, exist_ok=True)
        file_id = uuid.uuid4().hex
        tmp = owner_dir / f"{file_id}.part"
        room = self._quota_bytes - self.usage(owner)["usedBytes"]
        try:
            size, digest = await self._drain(chunks, tmp, room)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        meta = {
            "id": file_id,
            "name": clean_name(name),
            "contentType": clean_content_type(content_type),
            "size": size,
            "sha256": digest,
            "createdAt": utc_now_iso(),
        }
        if conversation_id:
            meta["conversationId"] = conversation_id
        with self._lock:
            os.replace(tmp, owner_dir / f"{file_id}.bin")
            self._write_meta(owner_dir / f"{file_id}.json", meta)
        return meta

    async def _drain(self, chunks: AsyncIterator[bytes], tmp: Path, room: int) -> tuple[int, str]:
        size, digest = 0, hashlib.sha256()
        with tmp.open("wb") as out:
            async for chunk in chunks:
                size += len(chunk)
                if size > self._max_file_bytes:
                    raise FileTooLarge
                if size > room:
                    raise QuotaExceeded
                digest.update(chunk)
                await asyncio.to_thread(out.write, chunk)
        return size, digest.hexdigest()

    def delete(self, owner: str, file_id: str) -> bool:
        if not valid_file_id(file_id):
            return False
        owner_dir = self._owner_dir(owner)
        with self._lock:
            existed = (owner_dir / f"{file_id}.json").is_file()
            (owner_dir / f"{file_id}.json").unlink(missing_ok=True)
            (owner_dir / f"{file_id}.bin").unlink(missing_ok=True)
        return existed

    @staticmethod
    def _read_meta(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _write_meta(path: Path, meta: dict) -> None:
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta), "utf-8")
        os.replace(tmp, path)
