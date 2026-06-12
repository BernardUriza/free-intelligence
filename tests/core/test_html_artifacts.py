"""Tests for the html_artifacts module (v3.9.57).

These exercise the SQL contract against the CI Postgres service. Skip
locally when POSTGRES_URL is unset, same pattern as test_siesta_pg_state.
"""

from __future__ import annotations

import os

import pytest

from personas.insult.core import html_artifacts

pytestmark = pytest.mark.skipif(
    not os.environ.get("POSTGRES_URL"),
    reason="POSTGRES_URL not configured — html_artifacts tests need a live PG",
)


@pytest.fixture(autouse=True)
async def _clean_table():
    """Wipe html_artifacts between tests."""
    conn = await html_artifacts._connect()
    if conn is None:
        pytest.skip("PG unreachable from this test runner")
    try:
        await conn.execute("DELETE FROM html_artifacts")
    finally:
        await conn.close()
    yield
    conn = await html_artifacts._connect()
    if conn is None:
        return
    try:
        await conn.execute("DELETE FROM html_artifacts")
    finally:
        await conn.close()


async def test_insert_returns_short_id():
    aid = await html_artifacts.insert_artifact(title="hello", html_content="<h1>hi</h1>")
    assert aid is not None
    # 11 chars from token_urlsafe(8); URL-safe alphabet only.
    assert 8 <= len(aid) <= 22
    assert all(c.isalnum() or c in "-_" for c in aid)


async def test_get_returns_inserted_artifact():
    aid = await html_artifacts.insert_artifact(title="hello", html_content="<h1>hi</h1>", created_by_user_id="u1")
    assert aid is not None
    got = await html_artifacts.get_artifact(aid)
    assert got is not None
    assert got["title"] == "hello"
    assert got["html_content"] == "<h1>hi</h1>"
    assert got["view_count"] == 1  # incremented on this read


async def test_get_increments_view_count():
    aid = await html_artifacts.insert_artifact(title="t", html_content="<p>x</p>")
    assert aid is not None
    for expected in (1, 2, 3):
        got = await html_artifacts.get_artifact(aid)
        assert got is not None
        assert got["view_count"] == expected


async def test_get_unknown_id_returns_none():
    assert await html_artifacts.get_artifact("doesnotexist") is None


async def test_insert_rejects_empty_title():
    aid = await html_artifacts.insert_artifact(title="", html_content="<p>x</p>")
    assert aid is None


async def test_insert_rejects_empty_html():
    aid = await html_artifacts.insert_artifact(title="t", html_content="")
    assert aid is None


async def test_ids_are_unique_across_inserts():
    """Sanity: token_urlsafe(8) collision probability is astronomically low,
    but pin the invariant so a future change to _new_id is caught."""
    ids = set()
    for i in range(20):
        aid = await html_artifacts.insert_artifact(title=f"t{i}", html_content=f"<p>{i}</p>")
        assert aid is not None
        assert aid not in ids
        ids.add(aid)
