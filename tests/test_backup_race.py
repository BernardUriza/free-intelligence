"""Unit tests for the shutdown-upload race policy (pure function).

The full upload_db path needs azure-storage-blob installed, which isn't a
test-time dependency. The race decision itself is a pure function
(`should_abort_upload`) so we test THAT directly — the caller just wires
it to the blob properties.

Scenario reproduced tonight (2026-04-21 05:05 UTC): operator pushed a new
memory.db to the blob, triggered a container restart. New container
downloaded + uploaded (16 facts). Three seconds later the OLD container's
graceful_shutdown fired and called upload_db(), blindly overwriting the
blob with its stale in-memory DB (3 facts). 13 manual facts lost.

The fix encoded here: upload MUST abort when the current remote mtime is
strictly newer than the mtime we observed at our last download/upload.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from insult.core.backup import (
    count_authoritative_rows,
    should_abort_download,
    should_abort_upload,
    should_force_overwrite,
    should_unstick_baseline,
)

T_DOWNLOAD = datetime(2026, 4, 21, 5, 5, 39, tzinfo=UTC)
T_REMOTE_NEWER = datetime(2026, 4, 21, 5, 5, 40, tzinfo=UTC)
T_REMOTE_SAME = T_DOWNLOAD
T_REMOTE_OLDER = datetime(2026, 4, 21, 5, 5, 30, tzinfo=UTC)
T_REMOTE_EVEN_NEWER = datetime(2026, 4, 21, 5, 6, 0, tzinfo=UTC)


def test_aborts_when_remote_is_strictly_newer():
    # The exact race from 2026-04-21: old container about to overwrite a
    # remote that the new container already wrote.
    assert should_abort_upload(T_REMOTE_NEWER, T_DOWNLOAD) is True


def test_proceeds_when_remote_equals_last_known():
    assert should_abort_upload(T_REMOTE_SAME, T_DOWNLOAD) is False


def test_proceeds_when_remote_is_older():
    # Defensive: clocks or cache weirdness. Err on the side of uploading.
    assert should_abort_upload(T_REMOTE_OLDER, T_DOWNLOAD) is False


def test_proceeds_on_first_ever_upload_no_tracked_mtime():
    assert should_abort_upload(T_REMOTE_NEWER, None) is False


def test_proceeds_when_remote_mtime_is_unknown():
    # If Azure didn't return last_modified for some reason, we don't stall backups.
    assert should_abort_upload(None, T_DOWNLOAD) is False


def test_override_force_overwrite_bypasses_check():
    # Escape hatch for operators: skip_if_remote_newer=False forces through.
    assert should_abort_upload(T_REMOTE_NEWER, T_DOWNLOAD, skip_if_remote_newer=False) is False


# --- should_unstick_baseline -----------------------------------------------
#
# Production incident on 2026-04-27: a replacement container wrote the blob
# 9 minutes after the surviving container started up. From then on, every
# 10-minute backup attempt aborted because the remote was strictly newer
# than what the surviving container had observed at boot. With no recovery
# path, uploads stayed frozen for 13+ hours while the bot DB drifted.
#
# Recovery rule: if the remote mtime is identical to what we saw during
# the previous aborted attempt, the writer is gone. Adopt their mtime as
# our new baseline and proceed.


def test_unstick_when_remote_stable_across_two_checks():
    # Same mtime in two consecutive aborted checks → race over, proceed.
    assert should_unstick_baseline(T_REMOTE_NEWER, T_REMOTE_NEWER) is True


def test_no_unstick_on_first_observation():
    # First abort: we have not yet observed the remote during a prior cycle.
    # We must wait one more interval before unsticking.
    assert should_unstick_baseline(T_REMOTE_NEWER, None) is False


def test_no_unstick_when_remote_is_still_changing():
    # Different mtime than last observation → competing writer is still
    # active. Keep aborting.
    assert should_unstick_baseline(T_REMOTE_EVEN_NEWER, T_REMOTE_NEWER) is False


def test_no_unstick_when_current_mtime_unknown():
    # Azure didn't give us a mtime — cannot prove stability, do not unstick.
    assert should_unstick_baseline(None, T_REMOTE_NEWER) is False


# --- count_authoritative_rows + should_force_overwrite -----------------------
#
# Production incident on 2026-04-27: a long-running container had accumulated
# 92 facts for a vulnerable user (Alex / CPTSD + active treatment). Its
# uploads had been aborting for ~9 hours because of the upload-side race
# (some earlier writer left the blob mtime ahead of our baseline). When the
# container was finally killed by a deploy, the new replica downloaded the
# stale blob (4 facts) and Alex lost his vulnerability overlay.
#
# The 2026-04-21 fix correctly handles operator-pushed-fresh: local stale,
# remote rich → abort. But the 2026-04-27 case is the OPPOSITE: local rich,
# remote stale → we must overwrite. Row counts on `messages` and
# `user_facts` distinguish the two.


def _make_db(path: Path, n_messages: int, n_facts: int) -> None:
    """Create a synthetic SQLite DB with the load-bearing tables."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE messages (id INTEGER PRIMARY KEY, body TEXT);
            CREATE TABLE user_facts (id INTEGER PRIMARY KEY, fact TEXT);
            """
        )
        for i in range(n_messages):
            conn.execute("INSERT INTO messages (body) VALUES (?)", (f"m{i}",))
        for i in range(n_facts):
            conn.execute("INSERT INTO user_facts (fact) VALUES (?)", (f"f{i}",))
        conn.commit()
    finally:
        conn.close()


def test_count_authoritative_rows_returns_zero_for_missing_file(tmp_path: Path):
    counts = count_authoritative_rows(tmp_path / "nope.db")
    assert counts == {"messages": 0, "user_facts": 0}


def test_count_authoritative_rows_reads_real_db(tmp_path: Path):
    db = tmp_path / "test.db"
    _make_db(db, n_messages=42, n_facts=92)
    counts = count_authoritative_rows(db)
    assert counts == {"messages": 42, "user_facts": 92}


def test_count_authoritative_rows_zero_for_missing_table(tmp_path: Path):
    # A partial DB (e.g. mid-migration) should not raise — missing tables are 0.
    db = tmp_path / "partial.db"
    conn = sqlite3.connect(db)
    conn.executescript("CREATE TABLE messages (id INTEGER); INSERT INTO messages VALUES (1);")
    conn.commit()
    conn.close()
    counts = count_authoritative_rows(db)
    assert counts == {"messages": 1, "user_facts": 0}


def test_force_overwrite_when_local_strictly_richer_in_facts():
    # The 2026-04-27 Alex scenario: local has 92 facts, remote has 4.
    assert should_force_overwrite({"messages": 100, "user_facts": 92}, {"messages": 100, "user_facts": 4}) is True


def test_force_overwrite_when_local_strictly_richer_in_messages():
    # Long-running container with more conversation history than blob.
    assert should_force_overwrite({"messages": 5000, "user_facts": 50}, {"messages": 1000, "user_facts": 50}) is True


def test_no_force_overwrite_when_remote_has_more_facts():
    # The 2026-04-21 operator-pushed scenario: local has 3 facts, remote has 16.
    # Even if local has more messages, the operator's facts must not be lost.
    assert should_force_overwrite({"messages": 200, "user_facts": 3}, {"messages": 100, "user_facts": 16}) is False


def test_no_force_overwrite_when_remote_has_more_messages():
    # Mirror case: remote has more messages even if facts are equal.
    assert should_force_overwrite({"messages": 100, "user_facts": 50}, {"messages": 200, "user_facts": 50}) is False


def test_no_force_overwrite_when_counts_equal():
    # No strict gain → don't force. Could be a routine periodic upload that
    # raced; existing abort/unstick policy handles it.
    assert should_force_overwrite({"messages": 100, "user_facts": 50}, {"messages": 100, "user_facts": 50}) is False


def test_no_force_overwrite_when_local_empty():
    # Defensive: brand-new container with no data must NOT clobber a populated remote.
    assert should_force_overwrite({"messages": 0, "user_facts": 0}, {"messages": 100, "user_facts": 50}) is False


def test_force_overwrite_handles_missing_keys():
    # Tolerate truncated dicts — missing key is treated as 0.
    # If local has more in one table and remote is silent on the others,
    # both default to 0 and the gain is genuine.
    assert should_force_overwrite({"messages": 100}, {"messages": 50}) is True
    # If remote has data in a table local is silent on, that counts as
    # local-loses — refuse to clobber even though local is rich elsewhere.
    assert should_force_overwrite({"user_facts": 100}, {"messages": 50}) is False
    # Empty local: no strict gain.
    assert should_force_overwrite({}, {"messages": 50}) is False


# --- should_abort_download ---------------------------------------------------
#
# The 2026-04-27 Alex incident reconstructed: a container swap downloaded a
# stale 4-fact blob over a long-running 92-fact local DB on startup. The
# upload-side fix (force_overwrite) only kicks in AFTER the bot has already
# clobbered its own local state. The download-side guard catches it before
# any data is overwritten.


def test_abort_download_when_local_strictly_richer_in_facts():
    # The exact Alex regression: local 92 facts, remote 4 facts. Don't
    # download — the blob is stale and would erase the cluster.
    assert should_abort_download({"messages": 100, "user_facts": 92}, {"messages": 100, "user_facts": 4}) is True


def test_abort_download_when_local_strictly_richer_in_messages():
    # Long-running rich container, fresh blob has fewer messages.
    assert should_abort_download({"messages": 5000, "user_facts": 50}, {"messages": 1000, "user_facts": 50}) is True


def test_proceed_download_when_remote_has_more_facts():
    # Operator pushed a fresh blob with 16 facts, local has 3 from a
    # newly-spawned container. Download is correct here.
    assert should_abort_download({"messages": 200, "user_facts": 3}, {"messages": 100, "user_facts": 16}) is False


def test_proceed_download_when_remote_has_more_messages():
    # Symmetric case on messages table.
    assert should_abort_download({"messages": 100, "user_facts": 50}, {"messages": 200, "user_facts": 50}) is False


def test_proceed_download_when_counts_equal():
    # No strict gain locally → safe to download (same content / different mtime).
    assert should_abort_download({"messages": 100, "user_facts": 50}, {"messages": 100, "user_facts": 50}) is False


def test_proceed_download_when_local_empty():
    # Brand-new container at first boot: no local data → must download.
    assert should_abort_download({"messages": 0, "user_facts": 0}, {"messages": 100, "user_facts": 50}) is False


def test_abort_download_handles_missing_keys():
    # Mirror of force_overwrite_handles_missing_keys.
    assert should_abort_download({"messages": 100}, {"messages": 50}) is True
    assert should_abort_download({"user_facts": 100}, {"messages": 50}) is False
    assert should_abort_download({}, {"messages": 50}) is False
