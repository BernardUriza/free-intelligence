"""The file door: /files upload, list, download, delete, keyed by the auth principal."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

import app as app_module
from files import clean_name

H5_MAGIC = b"\x89HDF\r\n\x1a\n" + bytes(range(256))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


def _upload(client: TestClient, body: bytes, name: str = "datos.h5", **params) -> dict:
    res = client.post(
        "/files",
        params={"name": name, **params},
        content=body,
        headers={"content-type": "application/x-hdf5"},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_binary_round_trip_is_byte_identical(client, as_account):
    meta = _upload(client, H5_MAGIC)
    assert meta["size"] == len(H5_MAGIC)
    assert meta["sha256"] == hashlib.sha256(H5_MAGIC).hexdigest()

    got = client.get(f"/files/{meta['id']}")
    assert got.status_code == 200
    assert got.content == H5_MAGIC
    assert got.headers["content-type"] == "application/x-hdf5"
    assert got.headers["content-disposition"].startswith("attachment;")
    assert got.headers["x-content-type-options"] == "nosniff"


def test_list_reports_files_and_usage(client, as_account):
    first = _upload(client, b"a" * 10, name="uno.pdf")
    _upload(client, b"b" * 20, name="dos.pdf", conversationId="conv-1")

    listing = client.get("/files").json()
    assert {f["name"] for f in listing["files"]} == {"uno.pdf", "dos.pdf"}
    assert listing["usedBytes"] == 30
    assert listing["quotaBytes"] == 2048

    scoped = client.get("/files", params={"conversationId": "conv-1"}).json()
    assert [f["name"] for f in scoped["files"]] == ["dos.pdf"]
    assert first["id"] not in {f["id"] for f in scoped["files"]}


def test_another_account_sees_nothing(client, as_account):
    meta = _upload(client, b"secreto")
    as_account("acct-B")
    assert client.get(f"/files/{meta['id']}").status_code == 404
    assert client.get("/files").json()["files"] == []
    assert client.delete(f"/files/{meta['id']}").status_code == 404
    as_account("acct-A")
    assert client.get(f"/files/{meta['id']}").content == b"secreto"


def test_delete_removes_bytes_and_metadata(client, as_account, file_store):
    meta = _upload(client, b"x" * 50)
    assert client.delete(f"/files/{meta['id']}").json() == {"deleted": meta["id"]}
    assert client.get(f"/files/{meta['id']}").status_code == 404
    assert client.get("/files").json()["usedBytes"] == 0
    assert list(file_store._root.rglob("*.bin")) == []


def test_file_over_the_cap_is_refused_and_leaves_nothing(client, as_account, file_store):
    res = client.post("/files", params={"name": "gordo.h5"}, content=b"x" * 1025)
    assert res.status_code == 413
    assert res.json()["detail"]["code"] == "FILE_TOO_LARGE"
    assert [p for p in file_store._root.rglob("*") if p.is_file()] == []


def test_account_quota_is_enforced(client, as_account, file_store):
    _upload(client, b"x" * 1024)
    _upload(client, b"x" * 1000)
    res = client.post("/files", params={"name": "tercero.h5"}, content=b"x" * 100)
    assert res.status_code == 413
    assert res.json()["detail"]["code"] == "FILE_QUOTA_EXCEEDED"
    assert client.get("/files").json()["usedBytes"] == 2024
    assert list(file_store._root.rglob("*.part")) == []


def test_ids_that_are_not_ours_are_not_found(client, as_account):
    for bad in ("..%2F..%2Fetc%2Fpasswd", "nope", "A" * 32):
        assert client.get(f"/files/{bad}").status_code == 404


def test_invalid_conversation_id_is_refused(client, as_account):
    res = client.post("/files", params={"name": "a.pdf", "conversationId": "../x"}, content=b"x")
    assert res.status_code == 422


def test_names_lose_paths_and_control_characters(client, as_account):
    meta = _upload(client, b"x", name="../../etc/pass\nwd.pdf")
    assert meta["name"] == "_.._etc_pass_wd.pdf"
    assert clean_name("...") == "file"
    assert len(clean_name("a" * 500)) == 200
