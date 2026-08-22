"""The customs desk — what the door accepts from the wire, and what it refuses.

Split from `messages.py` (which owns the endpoint and the event stream) because
validating a request body is its own concept: every function here turns an
untrusted field into a typed value or an HTTPException, and none of them knows a
thing about SSE. The daemon is internet-open and runs as root, so this is where
"the wire may NAME a capability, never DEFINE one" is actually enforced.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from .engine import DEFAULT_MODE, MODES
from .engine.contract import Guard
from .engine.guard_registry import UnknownGuard, clean_guards, resolve
from .engine.tools import UnknownTool, clean_tools
from .engine.vision import BadImage, clean_images
from .names import InvalidName, clean

MODEL_SHAPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def safe_names(project: str, session: str) -> tuple[str, str]:
    try:
        return clean("project", project), clean("session", session)
    except InvalidName as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def safe_mode(mode: str | None) -> str:
    return mode if mode in MODES else DEFAULT_MODE


def safe_tools(raw: Any, _mode: str) -> tuple[str, ...]:
    """Validate the `tools` field against the vetted registry (#29). The mode
    dial governs the BUILTIN surface only: registry tools are in-process and
    vetted, so a complete-mode turn may carry them (#36 — og118 edits its
    living persona without ever gaining Write or WebSearch)."""
    try:
        names = clean_tools(raw)
    except UnknownTool as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return tuple(names)


def safe_model(raw: Any) -> str | None:
    """The `model` field (#29 gap 3) rides verbatim to the CLI as `--model`; the
    edge guards only the argv's shape — the API curates the catalog. Absent →
    the engine decides. Binds when the session's pooled client is (re)born."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, str) and MODEL_SHAPE.match(raw):
        return raw
    raise HTTPException(status_code=422, detail="invalid model")


def safe_images(raw: Any) -> tuple[dict[str, str], ...]:
    """Attachments for THIS turn (#29 gap 4), validated in `engine/vision.py`."""
    try:
        return clean_images(raw)
    except BadImage as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def safe_guards(raw: Any) -> list[Guard]:
    """Validate AND BUILD the `guards` field here, at the edge, before a dollar is
    spent. Building early is deliberate: a guard imports its backing lazily, so a
    missing one would otherwise surface mid-turn as findings that never arrive —
    a request accepted and quietly unserved. The caller learns now, for free."""
    try:
        names = clean_guards(raw)
    except UnknownGuard as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return resolve(names)
    except Exception as exc:  # noqa: BLE001 — the backing is absent; not the caller's fault
        raise HTTPException(status_code=503,
                            detail=f"guard backing unavailable: {type(exc).__name__}") from exc
