"""ConversationStore — the server-authoritative, per-account conversation store.

Cloud counterpart of fi-glass's IndexedDBConversationLibrary: the same
ConversationRecord shape (id/title/createdAt/updatedAt/messages/preview/
schemaVersion), persisted server-side so an account's conversations follow it
across browsers/devices. Layout: ONE JSON file per conversation under a
per-owner directory (``<root>/<sha256(owner)[:32]>/<conversation_id>.json``) on
the same Azure Files volume as the corpus — a per-turn ``put`` rewrites only
that conversation, never a monolithic index (unlike ProjectRegistry, whose
single JSON is fine because project churn is rare; conversation churn is every
turn). Ownership is structural: a caller can only ever read its own directory,
so cross-account ids resolve to "missing" (404, never 403 — no existence
probing, same invariant as projects). Writes are atomic (temp + os.replace)
under an in-process lock; single replica = single writer.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from pathlib import Path

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

SUMMARY_FIELDS = (
    "id",
    "title",
    "createdAt",
    "updatedAt",
    "preview",
    "pinnedAt",
    "archivedAt",
    # The project this conversation belongs to. In the SUMMARY because the
    # project detail page's "Recents" filters the light list — pulling every full
    # record just to read one field would make that page cost the whole account's
    # transcripts.
    "projectId",
)


def valid_conversation_id(conversation_id: str) -> bool:
    """True for filesystem-safe ids (UUIDs qualify). Anything else — path
    separators, dots, empty — is rejected before it ever touches a Path."""
    return bool(_ID_RE.match(conversation_id))


class ConversationStore:
    def __init__(self, root: str | os.PathLike) -> None:
        self._root = Path(root)
        self._lock = threading.Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    def _owner_dir(self, owner: str) -> Path:
        return self._root / hashlib.sha256(owner.encode("utf-8")).hexdigest()[:32]

    def _record_path(self, owner: str, conversation_id: str) -> Path:
        if not valid_conversation_id(conversation_id):
            raise ValueError(f"invalid conversation id: {conversation_id!r}")
        return self._owner_dir(owner) / f"{conversation_id}.json"

    def list_for(self, owner: str) -> list[dict]:
        """The owner's conversations as light summaries (no messages), newest
        ``updatedAt`` first."""
        owner_dir = self._owner_dir(owner)
        if not owner_dir.is_dir():
            return []
        summaries: list[dict] = []
        for path in owner_dir.glob("*.json"):
            try:
                record = json.loads(path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            summaries.append(
                {k: record[k] for k in SUMMARY_FIELDS if record.get(k) is not None}
            )
        summaries.sort(key=lambda s: s.get("updatedAt") or "", reverse=True)
        return summaries

    def get(self, owner: str, conversation_id: str) -> dict | None:
        try:
            path = self._record_path(owner, conversation_id)
        except ValueError:
            return None
        return self._read(path)

    @staticmethod
    def _read(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    @staticmethod
    def _write(path: Path, record: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(record), "utf-8")
        os.replace(tmp, path)

    def put(self, owner: str, record: dict) -> None:
        """Blind upsert. Used by tests and seeding; the HTTP surface goes through
        ``put_content`` so a stale device cannot clobber organization flags."""
        path = self._record_path(owner, record["id"])
        with self._lock:
            self._write(path, record)

    # The fields the OWNER moves deliberately (rename / pin / archive) and the
    # resource a conversation was born in. Everything else in a record is
    # CONTENT, produced by whichever device is holding the turn.
    ORGANIZATION_FIELDS = ("pinnedAt", "archivedAt", "projectId")

    def put_content(self, owner: str, record: dict) -> dict:
        """Upsert a record, but the STORED organization flags win.

        Every mutation used to travel as a whole-record put, so the last writer
        won the whole record: pin on the phone, then send a message from the
        desktop whose in-memory copy predates the pin, and the pin is gone —
        never reported, because nothing failed. Read-modify-write under the same
        lock as the write, so two concurrent puts cannot interleave.

        The fix is not a version check. It is that a put no longer CARRIES an
        opinion about the flags: a stale device cannot lose a pin it is not
        allowed to speak about. The only way to move them is ``patch_metadata``,
        which sends the delta rather than the world.

        ``updatedAt`` deliberately still comes from the body — that IS content
        recency, and the device holding the turn is its rightful author.
        """
        path = self._record_path(owner, record["id"])
        with self._lock:
            stored = self._read(path)
            merged = dict(record)
            if stored is not None:
                for field in self.ORGANIZATION_FIELDS:
                    merged.pop(field, None)
                    if stored.get(field) is not None:
                        merged[field] = stored[field]
                # A custom title is a rename — an organization act. Letting the
                # auto-derived title of a later message overwrite it is the same
                # bug wearing a different field's name.
                if stored.get("titleCustom"):
                    merged["title"] = stored["title"]
                    merged["titleCustom"] = True
            self._write(path, merged)
        return merged

    def patch_metadata(self, owner: str, conversation_id: str, patch: dict) -> dict | None:
        """Merge a metadata delta into a stored record. ``None`` if absent.

        Mirrors core's ``applyConversationMetadataPatch``: an explicit ``None``
        CLEARS the field, an omitted key leaves it alone. That distinction is the
        whole point — a whole-record put cannot tell "unpinned" from "this device
        never knew about the pin".
        """
        try:
            path = self._record_path(owner, conversation_id)
        except ValueError:
            return None
        with self._lock:
            stored = self._read(path)
            if stored is None:
                return None
            merged = dict(stored)
            for field in ("title", "titleCustom", "updatedAt"):
                if field in patch:
                    merged[field] = patch[field]
            for field in ("pinnedAt", "archivedAt"):
                if field not in patch:
                    continue
                if patch[field] is None:
                    merged.pop(field, None)
                else:
                    merged[field] = patch[field]
            self._write(path, merged)
            return merged

    def delete(self, owner: str, conversation_id: str) -> None:
        """Remove the record (no-op if absent — mirrors the client contract)."""
        try:
            path = self._record_path(owner, conversation_id)
        except ValueError:
            return
        with self._lock:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def clear_for(self, owner: str) -> int:
        """Remove every conversation the owner has. Returns how many."""
        owner_dir = self._owner_dir(owner)
        if not owner_dir.is_dir():
            return 0
        removed = 0
        with self._lock:
            for path in owner_dir.glob("*.json"):
                try:
                    path.unlink()
                    removed += 1
                except FileNotFoundError:
                    pass
        return removed
