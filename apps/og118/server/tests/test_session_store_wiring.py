"""og118-session-store wiring — the SDK's native durable memory, env-gated.

Three guarantees:
  * No DSN (today's deploy) → no store anywhere, byte-identical behavior.
  * DSN set → the lifespan builds the store, rebuilds the base runner with it,
    clears the element cache (so lazy element runners inherit it), and closes
    the pool on shutdown.
  * A dead Postgres DEGRADES (chat keeps working on history replay) but never
    kills the app — the memory layer must not take down live turns.

The store is FAKED at the seam the lifespan imports (fi_runner.session_stores.
create_postgres_session_store): no asyncpg, no network, no real Postgres.

No pytest-asyncio in this venv (anyio only) — the lifespan is driven through
TestClient's context manager, which runs startup/shutdown.
"""

from __future__ import annotations

from starlette.testclient import TestClient

import app as app_module
from runner import build_runner


def test_build_runner_default_has_no_store() -> None:
    """The no-DSN contract: nothing wired, the backend behaves exactly as before."""
    runner = build_runner()
    assert runner.backend.session_store is None


def test_build_runner_injects_the_store_with_the_sdk_derived_key() -> None:
    from claude_agent_sdk import project_key_for_directory

    sentinel = object()
    runner = build_runner(session_store=sentinel)
    assert runner.backend.session_store is sentinel
    # The read key must be EXACTLY what the SDK derives when it writes (from
    # the CLI's cwd) — a runner-invented name ("og118") shipped once and every
    # load() missed: writes landed under the deploy's cwd key instead.
    assert (
        runner.backend.session_key("conv-1")["project_key"]
        == project_key_for_directory(None)
    )


class _FakeStore:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def test_lifespan_wires_the_store_and_closes_it_on_shutdown(monkeypatch) -> None:
    import fi_runner.session_stores as stores_module

    fake = _FakeStore()
    seen_dsn: list[str] = []

    async def _fake_create(dsn: str, **_kw):
        seen_dsn.append(dsn)
        return fake

    monkeypatch.setattr(app_module, "_SESSION_STORE_DSN", "postgresql://fake/db")
    monkeypatch.setattr(stores_module, "create_postgres_session_store", _fake_create)
    app_module._element_runners["stale"] = build_runner()

    baseline = app_module._runner
    try:
        with TestClient(app_module.app):
            assert seen_dsn == ["postgresql://fake/db"]
            assert app_module._session_store is fake
            # The base runner was REBUILT with the store — not mutated in place.
            assert app_module._runner.backend.session_store is fake
            # Stale element runners (built storeless) were evicted.
            assert app_module._element_runners == {}
        assert fake.closed, "shutdown must close the pool the factory opened"
        assert app_module._session_store is None
    finally:
        app_module._runner = baseline


def test_lifespan_degrades_loud_when_postgres_is_down(monkeypatch, caplog) -> None:
    import fi_runner.session_stores as stores_module

    async def _boom(dsn: str, **_kw):
        raise ConnectionError("postgres unreachable")

    monkeypatch.setattr(app_module, "_SESSION_STORE_DSN", "postgresql://dead/db")
    monkeypatch.setattr(stores_module, "create_postgres_session_store", _boom)

    baseline = app_module._runner
    with caplog.at_level("ERROR", logger="og118"):
        with TestClient(app_module.app) as client:
            # The app booted and serves — memory is optional, turns are not.
            assert client.get("/health").status_code == 200
            assert app_module._session_store is None
            assert app_module._runner is baseline  # untouched, still storeless
    assert any("session store failed" in r.message for r in caplog.records)


def test_lifespan_without_dsn_never_touches_the_store(monkeypatch) -> None:
    import fi_runner.session_stores as stores_module

    async def _forbidden(dsn: str, **_kw):
        raise AssertionError("create_postgres_session_store must not be called")

    monkeypatch.setattr(app_module, "_SESSION_STORE_DSN", None)
    monkeypatch.setattr(stores_module, "create_postgres_session_store", _forbidden)

    with TestClient(app_module.app):
        assert app_module._session_store is None
