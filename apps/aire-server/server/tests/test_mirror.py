"""The mirror's mtime cache (#26), offline: unchanged files are skipped, a
changed file is re-offered, a deleted file's stamp is pruned — no Postgres."""

import json

import pytest

from aire import mirror


class FakeStore:
    def __init__(self):
        self.appended = []

    async def append(self, key, entries):
        self.appended.append((key["session_id"], len(entries)))

    async def close(self):
        pass


def _transcript(root, name, uuids):
    d = root / "proj"
    d.mkdir(exist_ok=True)
    lines = [json.dumps({"cwd": str(root), "uuid": u}) for u in uuids]
    (d / f"{name}.jsonl").write_text("\n".join(lines))
    return d / f"{name}.jsonl"


@pytest.fixture
def patched(tmp_path, monkeypatch):
    monkeypatch.setattr(mirror, "PROJECTS", tmp_path)
    monkeypatch.setattr(mirror, "CACHE", tmp_path / "cache.json")
    return tmp_path


async def _run(store):
    cache = mirror.load_cache()
    try:
        return await mirror._offer_changed(store, cache)
    finally:
        mirror.save_cache(cache)


@pytest.mark.asyncio
async def test_second_run_skips_the_unchanged_file(patched):
    _transcript(patched, "sess-a", ["u1", "u2"])
    store = FakeStore()
    assert await _run(store) == (2, 1)
    assert await _run(store) == (0, 0)
    assert store.appended == [("sess-a", 2)]


@pytest.mark.asyncio
async def test_a_grown_file_is_offered_again_in_full(patched):
    path = _transcript(patched, "sess-a", ["u1"])
    store = FakeStore()
    await _run(store)
    _transcript(patched, "sess-a", ["u1", "u2", "u3"])
    assert path.stat().st_size != json.loads((patched / "cache.json").read_text())[str(path)][1]
    assert await _run(store) == (3, 1)


@pytest.mark.asyncio
async def test_a_deleted_file_leaves_the_cache(patched):
    path = _transcript(patched, "sess-a", ["u1"])
    await _run(FakeStore())
    path.unlink()
    await _run(FakeStore())
    assert json.loads((patched / "cache.json").read_text()) == {}


def test_a_lost_cache_is_just_an_empty_one(patched):
    assert mirror.load_cache() == {}
