"""/sync/serenityops — append a structured snapshot pushed by SerenityOps.

Per-user bearer auth (resolved in ``keys._auth_middleware``, which stamps
``request["sync_user_id"]``). Body is JSON with optional curriculum /
opportunities payloads; both are JSONB-stored as-is and never interpreted
server-side. Body size is capped so a stolen token can't DoS the prompt path.
"""

from __future__ import annotations

import json

import structlog
from aiohttp import web

from insult.core.debug_server.keys import _MEMORY_KEY, _bad_request, _unauthorized

log = structlog.get_logger()

# Cap on the raw JSON body the sync endpoint accepts. curriculum.yaml + a
# few hundred pipeline rows fit comfortably under 256KB. A larger cap would
# let a stolen token DoS the bot's prompt-build path; smaller would clip
# legit installs once Alex's pipeline has 50+ applications with notes.
_SYNC_MAX_BODY_BYTES = 256 * 1024


async def _handle_sync_serenityops(request: web.Request) -> web.Response:
    """POST /sync/serenityops — append a structured snapshot from SerenityOps.

    Auth is per-user (handled in `_auth_middleware`); `request["sync_user_id"]`
    is the Discord user id resolved from the bearer token. The body is a JSON
    object with optional `curriculum` and `opportunities` payloads plus
    `client_version`; both data fields are JSONB-stored as-is and never
    interpreted server-side. The prompt builder reads only the latest snapshot.
    """
    user_id = request.get("sync_user_id")
    if not user_id:
        # Defense-in-depth — middleware already gated, but if a routing
        # change ever sneaks a path past it, fail closed here too.
        return _unauthorized()

    # Bound the body so a stolen token can't DoS by pushing huge payloads.
    if (request.content_length or 0) > _SYNC_MAX_BODY_BYTES:
        return _bad_request(f"payload too large (>{_SYNC_MAX_BODY_BYTES} bytes)")

    try:
        body = await request.json()
    except (ValueError, json.JSONDecodeError):
        return _bad_request("body must be valid JSON")

    if not isinstance(body, dict):
        return _bad_request("body must be a JSON object")

    curriculum = body.get("curriculum")
    opportunities = body.get("opportunities")
    if curriculum is None and opportunities is None:
        return _bad_request("at least one of curriculum/opportunities is required")

    if curriculum is not None and not isinstance(curriculum, dict):
        return _bad_request("curriculum must be a JSON object")
    if opportunities is not None and not isinstance(opportunities, dict):
        return _bad_request("opportunities must be a JSON object")

    client_version = body.get("client_version")
    if client_version is not None and not isinstance(client_version, str):
        return _bad_request("client_version must be a string")

    memory = request.app[_MEMORY_KEY]
    snapshot_id = await memory.insert_serenityops_snapshot(user_id, curriculum, opportunities, client_version)
    log.info(
        "sync_serenityops_accepted",
        user_id=user_id,
        snapshot_id=snapshot_id,
        client_version=client_version,
        cv_present=curriculum is not None,
        pipeline_present=opportunities is not None,
    )
    return web.json_response(
        {"ok": True, "snapshot_id": snapshot_id, "user_id": user_id},
        status=201,
    )
