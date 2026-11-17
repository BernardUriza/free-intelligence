"""The MCP-over-HTTP door that lets the agent running in AIRE keep files for its user.

Same shape as ``mcp_background``: the tools live HERE, beside the durable volume,
and the remote agent calls them over HTTPS. The identity (account + conversation)
comes from the signed capsule in the URL, never from the model.

The capsule is the ONLY credential, and that is deliberate: this spec also travels
through the external engine, which persists turn requests, so it must carry nothing
that outlives the turn. A URL whose capsule this runner did not sign is a 404; a
signed but expired one still answers, and its tools say the window is closed.

No delete tool on purpose: removing a file stays a human act (``DELETE /files/{id}``).
"""

from __future__ import annotations

import base64
import binascii
import json
import os
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from background_jobs import verify_capsule
from deps import get_file_store
from files import FileStore, FileTooLarge, QuotaExceeded

router = APIRouter()

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "files"
SAVE, LIST, READ = "save_file", "list_files", "read_file"
MAX_READ_BYTES = 200_000
TEXT_TYPES = ("text/", "application/json", "application/xml", "application/yaml", "application/x-ndjson")
CLOSED = "this turn's file window is closed — tell the user the file was NOT saved"


def _token() -> str:
    return os.environ.get("OG118_MCP_TOKEN", "").strip()


def _signed_by_us(capsule: str) -> bool:
    return verify_capsule(_token(), capsule, now=0) is not None


def _text(text: str, *, error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def _tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": SAVE,
                "description": (
                    "Keep a file for the user in their durable storage, labelled with this conversation. "
                    "It survives the chat and the user can download it from the app. Use encoding 'text' "
                    "for anything you write as characters (markdown, csv, json, code) and 'base64' for bytes."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "File name with its extension, e.g. notas.md"},
                        "content": {"type": "string", "description": "The whole file, as text or base64."},
                        "encoding": {"type": "string", "enum": ["text", "base64"], "default": "text"},
                        "content_type": {"type": "string", "description": "MIME type; defaults by encoding."},
                    },
                    "required": ["name", "content"],
                },
            },
            {
                "name": LIST,
                "description": "List the user's stored files: this conversation's, or every file of the account.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scope": {"type": "string", "enum": ["conversation", "account"], "default": "conversation"}
                    },
                },
            },
            {
                "name": READ,
                "description": (
                    "Read back a stored file by id. Text comes back whole up to 200 KB; "
                    "a binary or larger file comes back as its metadata only."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"id": {"type": "string", "description": "The file id from save_file or list_files."}},
                    "required": ["id"],
                },
            },
        ]
    }


async def _one_chunk(data: bytes) -> AsyncIterator[bytes]:
    yield data


def _describe(meta: dict) -> str:
    return f"{meta['id']}  {meta['name']}  {meta['size']} bytes  {meta['contentType']}  {meta['createdAt']}"


async def _save(store: FileStore, identidad: dict, args: dict[str, Any]) -> dict[str, Any]:
    name = str(args.get("name") or "").strip()
    content = args.get("content")
    if not name or not isinstance(content, str) or not content:
        return _text("name and content are required", error=True)
    encoding = str(args.get("encoding") or "text")
    if encoding == "base64":
        try:
            data = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError):
            return _text("content is not valid base64 — nothing was saved", error=True)
        default_type = "application/octet-stream"
    elif encoding == "text":
        data, default_type = content.encode("utf-8"), "text/plain; charset=utf-8"
    else:
        return _text("encoding must be 'text' or 'base64'", error=True)
    content_type = str(args.get("content_type") or default_type)[:120]
    try:
        meta = await store.save(identidad["sub"], name, content_type, _one_chunk(data), identidad["cid"])
    except FileTooLarge:
        return _text("the file is over the per-file limit — nothing was saved", error=True)
    except QuotaExceeded:
        return _text("the user's file storage is full — nothing was saved", error=True)
    return _text(
        f"Saved as {meta['name']} ({meta['size']} bytes, id {meta['id']}). "
        "The user can download it from the Files panel of the app."
    )


def _list(store: FileStore, identidad: dict, args: dict[str, Any]) -> dict[str, Any]:
    found = store.list_for(identidad["sub"])
    if str(args.get("scope") or "conversation") != "account":
        found = [f for f in found if f.get("conversationId") == identidad["cid"]]
    if not found:
        return _text("no files stored")
    return _text("\n".join(_describe(f) for f in found))


def _read(store: FileStore, identidad: dict, args: dict[str, Any]) -> dict[str, Any]:
    held = store.get(identidad["sub"], str(args.get("id") or ""))
    if held is None:
        return _text("no file with that id", error=True)
    meta, blob = held
    is_text = meta["contentType"].startswith(TEXT_TYPES)
    if not is_text or meta["size"] > MAX_READ_BYTES:
        return _text(f"{_describe(meta)}\n(not shown: binary or over 200 KB)")
    try:
        return _text(blob.read_bytes().decode("utf-8"))
    except UnicodeDecodeError:
        return _text(f"{_describe(meta)}\n(not shown: not valid UTF-8)")


async def _tools_call(capsule: str, params: dict[str, Any], store: FileStore) -> dict[str, Any]:
    name = params.get("name")
    if name not in (SAVE, LIST, READ):
        return _text(f"unknown tool {name!r}", error=True)
    identidad = verify_capsule(_token(), capsule)
    if identidad is None:
        return _text(CLOSED, error=True)
    args = dict(params.get("arguments") or {})
    if name == SAVE:
        return await _save(store, identidad, args)
    if name == LIST:
        return _list(store, identidad, args)
    return _read(store, identidad, args)


@router.post("/mcp/files/{capsule}")
async def mcp_endpoint(capsule: str, request: Request, store: FileStore = Depends(get_file_store)) -> Response:
    if not _signed_by_us(capsule):
        return Response(status_code=404)
    body = await request.json()
    method, id_ = body.get("method"), body.get("id")
    if id_ is None:
        return Response(status_code=202)
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = _tools_list()
    elif method == "tools/call":
        result = await _tools_call(capsule, dict(body.get("params") or {}), store)
    elif method == "ping":
        result = {}
    else:
        return _json({"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": f"method {method!r} not supported"}})
    return _json({"jsonrpc": "2.0", "id": id_, "result": result})


def _json(payload: dict[str, Any]) -> Response:
    return Response(content=json.dumps(payload), media_type="application/json")
