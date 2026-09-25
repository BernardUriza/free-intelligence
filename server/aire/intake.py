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

from .agent_sdk import DEFAULT_PROVIDER, providers
from .engine import DEFAULT_MODE, MODES
from .engine.contract import Guard, RemoteTool
from .engine.remote_tools import BadRemoteTool, clean_remote_tools
from .engine.guards import UnknownGuard, clean_guards, resolve
from .engine.tools import UnknownTool, clean_tools
from .engine import attachment_budget
from .engine.documents import BadDocument, prepare_documents
from .engine.vision import BadImage, prepare_images
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


def safe_provider(raw: Any) -> str:
    """The `provider` field (#49): the native backend by default, or an ACP
    agent the OPERATOR named in `AIRE_ACP_AGENTS`. The wire picks from the
    roster; it never defines what runs."""
    if raw is None or raw == "":
        return DEFAULT_PROVIDER
    if isinstance(raw, str) and raw in providers():
        return raw
    raise HTTPException(status_code=422,
                        detail=f"unknown provider; available: {list(providers())}")


def safe_model(raw: Any) -> str | None:
    """The `model` field (#29 gap 3) rides verbatim to the CLI as `--model`; the
    edge guards only the argv's shape — the API curates the catalog. Absent →
    the engine decides. Binds when the session's pooled client is (re)born."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, str) and MODEL_SHAPE.match(raw):
        return raw
    raise HTTPException(status_code=422, detail="invalid model")


async def _prepare(images: Any, documents: Any, provider: str) -> tuple[dict[str, Any], ...]:
    try:
        blocks = await prepare_images(images) + await prepare_documents(documents)
    except (BadImage, BadDocument) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if provider != DEFAULT_PROVIDER and any(b["source"]["type"] == "base64" and b["type"] == "document"
                                            for b in blocks):
        raise HTTPException(status_code=422, detail=f"PDF documents need the {DEFAULT_PROVIDER} provider")
    return blocks


async def safe_attachments(images: Any, documents: Any, key: dict[str, str],
                           provider: str = DEFAULT_PROVIDER) -> tuple[dict[str, Any], ...]:
    """Attachments for THIS turn (#29 gap 4, #50) as ready content blocks: images
    fetched and shrunk (`engine/vision.py`), documents fetched and typed
    (`engine/documents.py`), then weighed against what the session already
    resends every turn (`engine/attachment_budget.py`). All before a dollar is spent."""
    blocks = await _prepare(images, documents, provider)
    try:
        await attachment_budget.enforce(key["project_key"], key["session_id"], blocks)
    except attachment_budget.OverBudget as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # the store is unreachable: refuse loud, never guess the weight
        raise HTTPException(status_code=503,
                            detail=f"session attachment budget unreadable: {type(exc).__name__}") from exc
    return blocks


def safe_guard_names(raw: Any) -> list[str]:
    """The `guards` field as validated NAMES — the cheap, deterministic half.

    Separate from building on purpose: a request whose SHAPE is wrong (a spec
    instead of a name, guards on a detached turn) must be refused before anything
    environmental is consulted. Otherwise a caller on a box without the backing
    gets told the backing is missing when the real problem is their request, and
    the same call would answer differently on another box."""
    try:
        return clean_guards(raw)
    except UnknownGuard as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def safe_remote_tools(raw: Any) -> tuple[RemoteTool, ...]:
    """Validate `remote_tools` (#48): HTTP MCP servers the caller hosts. The
    wire names a url; the environment defines the trust (the origin allowlist
    lives in AIRE_REMOTE_TOOL_ORIGINS). Full law: engine/remote_tools.py."""
    try:
        return clean_remote_tools(raw)
    except BadRemoteTool as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def build_guards(names: list[str]) -> list[Guard]:
    """The vetted guards, built HERE at the edge before a dollar is spent. A guard
    imports its backing lazily, so a missing one would otherwise surface mid-turn
    as findings that never arrive — a request accepted and quietly unserved."""
    try:
        return resolve(names)
    except Exception as exc:  # noqa: BLE001 — the backing is absent; not the caller's fault
        raise HTTPException(status_code=503,
                            detail=f"guard backing unavailable: {type(exc).__name__}") from exc
