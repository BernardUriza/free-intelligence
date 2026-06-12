"""Tests for `tools/serenityops-sync-client/sync_insult.py`.

The client script lives in the bot repo so it can be shipped to users
inside the serenityops-lite zip. Tests are split into two layers:

1. **End-to-end** — invoke the script's `main()` in-process against a
   live aiohttp TestServer running `build_app`. Exercises the FULL stack:
   middleware auth → handler → JSON parse → memory mock.

2. **Unit / pure-function** — `_load_env`, `_read_yaml` parsed in
   isolation via `importlib.util.spec_from_file_location`. Catches env
   parser edge cases and the YAML→JSON fallback.

We deliberately avoid `subprocess.run` because the script must read from
`.env` not from inherited env vars, AND because subprocess + threading +
asyncio race on socket binding under the full suite. Calling `main()`
directly with a monkeypatched cwd is equivalent for coverage purposes
(the script's only side effect is the HTTP POST + stdout/stderr) and
deterministic.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml
from aiohttp.test_utils import TestServer

from personas.insult.core.debug_server import build_app

CLIENT = Path(__file__).resolve().parent.parent.parent / "tools" / "serenityops-sync-client" / "sync_insult.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_curriculum() -> dict:
    return {
        "personal": {
            "full_name": "Alex Nava",
            "title": "Psicóloga · Coordinadora",
            "location": "CDMX",
            "work_modality_required": "remote",
        },
        "summary": "15+ años en OSCs.",
        "experience": [
            {"company": "Freelance", "role": "Pet Sitter", "current": True},
        ],
    }


@pytest.fixture
def sample_pipeline() -> dict:
    return {
        "pipeline": [
            {"id": "x1", "company": "Fund A", "role": "Coord", "stage": "applied", "outcome": None},
        ],
    }


@pytest.fixture
def project_root(tmp_path: Path, sample_curriculum, sample_pipeline) -> Path:
    """Build a fake serenityops-lite project tree under tmp.

    Mirrors the real layout the script expects:

        root/
          .env
          curriculum/curriculum.yaml
          opportunities/structure.yaml
          scripts/sync_insult.py   (copied from tools/)
    """
    (tmp_path / "curriculum").mkdir()
    (tmp_path / "opportunities").mkdir()
    (tmp_path / "scripts").mkdir()

    (tmp_path / "curriculum" / "curriculum.yaml").write_text(
        yaml.safe_dump(sample_curriculum, allow_unicode=True), encoding="utf-8"
    )
    (tmp_path / "opportunities" / "structure.yaml").write_text(
        yaml.safe_dump(sample_pipeline, allow_unicode=True), encoding="utf-8"
    )

    # Copy the client script so its `PROJECT_ROOT = parent.parent` walks up
    # to the tmp root rather than the bot repo.
    shutil.copy(CLIENT, tmp_path / "scripts" / "sync_insult.py")

    return tmp_path


@pytest.fixture
async def bot_server():
    """Live aiohttp TestServer running the bot's `build_app` with a memory
    mock that accepts the test token and records the snapshot inserts."""
    mem = AsyncMock()
    mem.resolve_sync_token = AsyncMock(side_effect=lambda t: "alex-test-id" if t == "valid-test-token" else None)
    inserted: list[tuple] = []

    async def _record_snapshot(user_id, curriculum, opportunities, client_version=None):
        inserted.append((user_id, curriculum, opportunities, client_version))
        return len(inserted)  # snapshot id

    mem.insert_serenityops_snapshot = AsyncMock(side_effect=_record_snapshot)
    app = build_app(mem, "admin-token")
    server = TestServer(app)
    await server.start_server()
    try:
        yield server, inserted
    finally:
        await server.close()


def _write_env(project_root: Path, url: str, token: str) -> None:
    (project_root / ".env").write_text(
        f"INSULT_SYNC_URL={url}\nINSULT_SYNC_TOKEN={token}\n# leading comment line that the parser should ignore\n\n",
        encoding="utf-8",
    )


def _load_client_module(project_root: Path):
    """Load the client script as a module rooted at `project_root/scripts/sync_insult.py`.

    The script computes `PROJECT_ROOT = Path(__file__).resolve().parent.parent`,
    so placing the file under `<tmp>/scripts/sync_insult.py` makes the script's
    PROJECT_ROOT point at `<tmp>` — exactly what a real serenityops-lite install
    expects. importlib gives us a fresh module per test so module-level state
    can't bleed across cases.
    """
    from importlib import util

    script_path = project_root / "scripts" / "sync_insult.py"
    spec = util.spec_from_file_location(f"sync_insult_{id(project_root)}", str(script_path))
    assert spec is not None and spec.loader is not None
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_client_in_process(project_root: Path, capsys) -> tuple[int, str, str]:
    """Invoke main() in-process and capture stdout/stderr.

    Strip INSULT_* env vars from the test process during the call so the
    script must read from .env (mirroring a clean user environment).
    """
    saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("INSULT_")}
    try:
        mod = _load_client_module(project_root)
        rc = mod.main()
    finally:
        os.environ.update(saved)
    out, err = capsys.readouterr()
    return rc, out, err


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_posts_both_payloads(project_root, bot_server, sample_curriculum, sample_pipeline, capsys):
    """End-to-end: client reads .env + YAMLs, server receives snapshot."""
    server, inserted = bot_server
    url = f"http://127.0.0.1:{server.port}/sync/serenityops"
    _write_env(project_root, url, "valid-test-token")

    # urllib.urlopen is sync but releases the GIL during socket I/O, which
    # lets the aiohttp TestServer (running on this event loop) service the
    # request. asyncio.to_thread keeps the event loop turning during the call.
    import asyncio

    rc = await asyncio.to_thread(lambda: _run_client_in_process(project_root, capsys))
    return_code, out, err = rc

    assert return_code == 0, f"stderr: {err}\nstdout: {out}"
    assert "snapshot #1" in out

    # Server saw exactly one insertion with both payloads intact.
    assert len(inserted) == 1
    user_id, cv, ops, client_ver = inserted[0]
    assert user_id == "alex-test-id"
    assert cv == sample_curriculum
    assert ops == sample_pipeline
    assert client_ver == "lite-1.0.0"


@pytest.mark.asyncio
async def test_rejects_invalid_token(project_root, bot_server, capsys):
    """Server returns 401 → client exits non-zero with readable error."""
    server, inserted = bot_server
    url = f"http://127.0.0.1:{server.port}/sync/serenityops"
    _write_env(project_root, url, "wrong-token")

    import asyncio

    return_code, _out, err = await asyncio.to_thread(lambda: _run_client_in_process(project_root, capsys))

    assert return_code != 0
    assert "401" in err or "unauthorized" in err.lower()
    # Token guidance present so the user knows how to recover.
    assert "!sync-token" in err
    assert len(inserted) == 0


def test_missing_env_vars_exits_nonzero(project_root, capsys):
    """No `.env`, no env vars → bail with readable error."""
    # Ensure no leftover .env
    env_path = project_root / ".env"
    if env_path.exists():
        env_path.unlink()
    return_code, _out, err = _run_client_in_process(project_root, capsys)
    assert return_code != 0
    assert "INSULT_SYNC_URL" in err or "INSULT_SYNC_TOKEN" in err
    # Help text steers user to the Discord command.
    assert "!sync-token" in err


def test_missing_both_yamls_exits_nonzero(project_root, capsys):
    """Neither curriculum.yaml nor opportunities/structure.yaml present →
    bail rather than POST a body with both fields null."""
    (project_root / "curriculum" / "curriculum.yaml").unlink()
    (project_root / "opportunities" / "structure.yaml").unlink()
    _write_env(project_root, "http://127.0.0.1:1/sync", "x")
    return_code, _out, err = _run_client_in_process(project_root, capsys)
    assert return_code != 0
    assert "no encontré" in err or "no encontre" in err or "ERROR" in err


def test_env_parser_ignores_comments_and_blank_lines(tmp_path):
    """`.env` parser is a tiny in-script function — verify it handles
    the common shapes (comments, blank lines, quoted values)."""
    from importlib import util

    spec = util.spec_from_file_location("sync_insult", str(CLIENT))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "# top comment\n"
        "\n"
        'INSULT_SYNC_URL="https://example.com/sync"\n'
        "INSULT_SYNC_TOKEN='single-quoted-token'\n"
        "# inline comment header\n"
        "OTHER_VAR=plain-value\n",
        encoding="utf-8",
    )

    parsed = mod._load_env(env_file)
    assert parsed["INSULT_SYNC_URL"] == "https://example.com/sync"
    assert parsed["INSULT_SYNC_TOKEN"] == "single-quoted-token"  # noqa: S105 — fixture, not a real secret
    assert parsed["OTHER_VAR"] == "plain-value"


def test_env_parser_handles_missing_file(tmp_path):
    """Missing .env returns empty dict, not an exception."""
    from importlib import util

    spec = util.spec_from_file_location("sync_insult", str(CLIENT))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod._load_env(tmp_path / "no-such-file.env") == {}


def test_yaml_reader_falls_back_to_json(tmp_path):
    """If a file is JSON-formatted but named .yaml, the reader still parses
    it. This is the path SerenityOps installs might take on systems where
    PyYAML is hard to install (the script's `_read_yaml` has a JSON fallback)."""
    from importlib import util

    spec = util.spec_from_file_location("sync_insult", str(CLIENT))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    json_as_yaml = tmp_path / "curriculum.yaml"
    json_as_yaml.write_text(json.dumps({"summary": "from-json"}), encoding="utf-8")

    result = mod._read_yaml(json_as_yaml)
    assert result == {"summary": "from-json"}


def test_yaml_reader_missing_file_returns_none(tmp_path):
    from importlib import util

    spec = util.spec_from_file_location("sync_insult", str(CLIENT))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod._read_yaml(tmp_path / "missing.yaml") is None
