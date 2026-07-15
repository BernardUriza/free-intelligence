"""The runner serves `/a/{id}` — published artifacts stop being dead links.

Root fix for the dead-artifact-host chain (2026-07-14): `publish_html_artifact`
persisted an artifact and minted `{base}/a/{id}`, but no host served that path —
the URL pointed at the scaled-to-zero / NXDOMAIN discord-bot FQDN. The runner
(alive, has the artifact's Postgres + `get_artifact`) now serves it itself.

Positive: a known id → 200 with the stored HTML as text/html. Resistance: an
unknown id → 404, never a 500 and never leaking prior existence.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import persona_runner.api.artifacts as artifacts
from persona_runner.runner import app


def test_known_artifact_is_served_as_html():
    stored = {
        "id": "abc123token",
        "title": "Reporte",
        "html_content": "<!doctype html><h1>hola mundo</h1>",
        "created_at": "2026-07-14",
        "view_count": 0,
    }
    with (
        patch.object(artifacts, "get_artifact", new=AsyncMock(return_value=stored)),
        TestClient(app) as client,
    ):
        r = client.get("/a/abc123token")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<h1>hola mundo</h1>" in r.text


def test_unknown_artifact_is_404_not_500():
    """RESISTANCE: a missing id is a clean 404, never a crash."""
    with (
        patch.object(artifacts, "get_artifact", new=AsyncMock(return_value=None)),
        TestClient(app) as client,
    ):
        r = client.get("/a/nope-does-not-exist")
    assert r.status_code == 404


def test_serve_route_is_mounted_on_the_app():
    """The router is actually included — the read side isn't dead code."""
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/a/{artifact_id}" in paths


# --- publish side: no more dead-link fake-green ---

import khimeras_shared.html_artifacts as html_store  # noqa: E402
from persona_runner import mcp_tools  # noqa: E402

_publish = mcp_tools.publish_html_artifact.handler


async def test_publish_fails_loud_when_base_url_unconfigured(monkeypatch):
    """The old default minted a URL to a dead FQDN and called it 'Published'.
    With no ARTIFACT_BASE_URL, publish must return an HONEST error (the artifact
    is still saved, id returned) — never a link to a corpse."""
    monkeypatch.delenv("ARTIFACT_BASE_URL", raising=False)
    monkeypatch.setattr(html_store, "insert_artifact", AsyncMock(return_value="tok123"))
    out = await _publish({"title": "Reporte", "html_content": "<h1>hi</h1>"})
    text = repr(out).lower()
    assert "tok123" in text  # id surfaced for recovery
    assert "nicecliff" not in text  # the dead FQDN never appears
    assert "not configured" in text or "no configurado" in text


async def test_publish_uses_the_configured_base(monkeypatch):
    """With ARTIFACT_BASE_URL set (the runner's own FQDN), the URL points there."""
    monkeypatch.setenv("ARTIFACT_BASE_URL", "https://persona-runner.example.net/")
    monkeypatch.setattr(html_store, "insert_artifact", AsyncMock(return_value="tok999"))
    out = await _publish({"title": "R", "html_content": "<p>x</p>"})
    text = repr(out)
    assert "https://persona-runner.example.net/a/tok999" in text  # trailing slash trimmed, id appended
