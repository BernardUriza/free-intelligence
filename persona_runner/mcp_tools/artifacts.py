"""MCP tool for publishing standalone HTML artifacts served at `GET /a/{id}`."""

from __future__ import annotations

import os

from persona_runner.mcp_tools import shared
from persona_runner.mcp_tools.tooldef import tool


@tool(
    "publish_html_artifact",
    (
        "Publish a standalone HTML page (report, mini-app, snapshot, "
        "visualization) and return a shareable URL. Use when the response "
        "would be too long for chat, when the user asks for a visualization "
        "or interactive widget, when you want to share a structured document. "
        "Includes everything inline (CSS, JS) — no external assets fetched. "
        "URL is permanent; anyone with the link can view. "
        "Do NOT publish anything containing secrets, tokens, or private content "
        "the user wouldn't share publicly."
    ),
    {"title": str, "html_content": str},
)
async def publish_html_artifact(args: dict) -> dict:
    from khimeras_shared.html_artifacts import insert_artifact
    from persona_runner.mcp_tools.turn_context import current_principal

    title = (args.get("title") or "").strip()
    html_content = args.get("html_content") or ""
    # La autoría la pone el servidor, igual que en las tools de memoria. Antes la
    # escribía el modelo, así que un artefacto público podía quedar firmado a
    # nombre de quien no lo pidió — la misma clase de confusión de principal que
    # el 2026-08-10 le atribuyó a Bernard un fact de Alex.
    user_id = current_principal().user_id
    if not title:
        return shared._error("title is required")
    if not html_content:
        return shared._error("html_content is required")
    if len(html_content) > 1_000_000:
        return shared._error("html_content too large (max 1MB)")
    artifact_id = await insert_artifact(title=title, html_content=html_content, created_by_user_id=user_id)
    if artifact_id is None:
        return shared._error("Failed to persist artifact (Postgres unreachable or insert failed)")
    # The URL must point at a host that actually serves `/a/{id}` — the runner
    # itself does (persona_runner.api.artifacts). NO hardcoded default: the old
    # one was `discord-bot.nicecliff…`, a host that is now NXDOMAIN (and the
    # greendune discord-bot is scaled to zero), so an unconfigured base minted a
    # dead link and reported it as "Published" — a fake-green. Fail loud instead;
    # the artifact IS saved, so the id is returned for recovery.
    base = (os.environ.get("ARTIFACT_BASE_URL") or "").rstrip("/")
    if not base:
        shared.log.error("artifact_base_url_unconfigured", artifact_id=artifact_id)
        return shared._error(
            f"Artifact saved (id={artifact_id}) but ARTIFACT_BASE_URL is not configured, "
            f"so I can't give you a live link. Set it to the runner's public URL."
        )
    url = f"{base}/a/{artifact_id}"
    return shared._text(f"Published. URL: {url}\nTitle: {title}\nSize: {len(html_content)} bytes")
