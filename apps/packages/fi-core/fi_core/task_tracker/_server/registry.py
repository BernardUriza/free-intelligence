"""Process-wide TaskTracker singleton + test-friendly accessor.

The MCP server holds ONE :class:`TaskTracker` for the lifetime of the
process. Scoping is by ``session_id`` on the tracker itself (different
agent sessions never see each other's plans — see
:class:`fi_core.task_tracker.tracker.SessionMismatch`).

The :func:`get_tracker` indirection lets tests swap the global for a
per-test instance via ``monkeypatch.setattr(registry, "_TRACKER", fresh)``.
Without it every test would share state with the rest of the suite — the
1h TTL won't save you from a flaky test ordering."""

from __future__ import annotations

from ..tracker import TaskTracker


# Process-wide singleton: every MCP tool call lands here. Cheap (in-memory
# dict with TTL eviction) and intentionally non-persistent — plans live
# for a turn. If a session truly needs cross-process state, swap the
# tracker for a Redis-backed variant; the public surface is unchanged.
_TRACKER: TaskTracker = TaskTracker()


def get_tracker() -> TaskTracker:
    """Return the live singleton — read by every MCP handler.

    Indirected so tests can swap the global; never inline the
    ``_TRACKER`` reference at a tool handler, always go through this."""
    return _TRACKER
