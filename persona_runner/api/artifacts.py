"""Artifact serving — the read side of `publish_html_artifact`.

The runner already PERSISTS an HTML artifact (`khimeras_shared.html_artifacts`)
and mints a shareable URL `{base}/a/{id}` — but nothing ever SERVED that path.
The URL pointed at the old `discord-bot` container's FQDN, which is now NXDOMAIN
(nicecliff) / scaled-to-zero (greendune), so every published link was dead on
arrival (verified 2026-07-14: curl 000 / 404).

Root fix (Art. 6, reuse the canonical): the runner is already a live FastAPI
service with the artifact's Postgres and its `get_artifact` reader — so IT serves
`/a/{id}`. `ARTIFACT_BASE_URL` points at the runner's own public FQDN; the URL the
tool mints is now real.

Access model: PUBLIC by id. The id is `secrets.token_urlsafe(8)` — an unguessable
11-char capability token, so the link itself is the credential (like a Google Doc
"anyone with the link"). The storage layer's own contract forbids publishing
secrets into artifacts, so no auth gate is added here on purpose — a shareable
link a human can just open is the whole point.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from khimeras_shared.html_artifacts import get_artifact

log = structlog.get_logger()

router = APIRouter()


@router.get("/a/{artifact_id}", response_class=HTMLResponse)
async def serve_artifact(artifact_id: str) -> HTMLResponse:
    """Serve a published HTML artifact by its capability id, or 404.

    Reads from Postgres via `get_artifact` (which also best-effort increments
    the view counter). Returns the raw stored HTML as `text/html` so a browser
    renders it. A missing/unknown id is a plain 404 — never leak whether an id
    ever existed beyond that.
    """
    artifact = await get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    log.info("artifact_served", id=artifact_id, title=artifact.get("title", "")[:80])
    return HTMLResponse(content=artifact["html_content"])
