"""An in-process fake of api.anthropic.com for the gateway tests: a realistic
Messages SSE stream with deliberate delays (so buffering is detectable), the
received request recorded for header assertions, and an error mode that returns
a byte-exact 400 body."""

from __future__ import annotations

import asyncio
from typing import Any

STREAM_CHUNKS = [
    b'event: message_start\n'
    b'data: {"type":"message_start","message":{"id":"msg_test01","type":"message",'
    b'"role":"assistant","model":"claude-haiku-4-5","content":[],"stop_reason":null,'
    b'"usage":{"input_tokens":10,"output_tokens":1}}}\n\n',
    b'event: ping\ndata: {"type": "ping"}\n\n',
    b': this comment line must survive the relay\n\n',
    b'event: content_block_start\n'
    b'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n',
    b'event: content_block_delta\n'
    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hel"}}\n\n',
    b'event: content_block_delta\n'
    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"lo"}}\n\n',
    b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n',
    b'event: message_delta\n'
    b'data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},'
    b'"usage":{"output_tokens":7}}\n\n',
    b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
]

ERROR_BODY = (b'{"type":"error","error":{"type":"invalid_request_error",'
              b'"message":"max_tokens: fake upstream says no"}}')

OPENAI_CHAT_CHUNKS = [
    b'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"gpt-4.1-2025-04-14",'
    b'"choices":[{"index":0,"delta":{"role":"assistant","content":"po"},"finish_reason":null}]}\n\n',
    b'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"gpt-4.1-2025-04-14",'
    b'"choices":[{"index":0,"delta":{"content":"ng"},"finish_reason":"stop"}]}\n\n',
    b'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"gpt-4.1-2025-04-14",'
    b'"choices":[],"usage":{"prompt_tokens":1000,"completion_tokens":100,'
    b'"prompt_tokens_details":{"cached_tokens":200}}}\n\n',
    b'data: [DONE]\n\n',
]

OPENAI_RESPONSE = (b'{"id":"resp_1","object":"response","model":"gpt-4.1-2025-04-14",'
                   b'"output":[],"usage":{"input_tokens":500,"output_tokens":50,'
                   b'"input_tokens_details":{"cached_tokens":0}}}')

state: dict[str, Any] = {"headers": None, "path": None, "body": b"", "finished": None}


async def _read_body(receive: Any) -> bytes:
    body = b""
    while True:
        msg = await receive()
        body += msg.get("body", b"")
        if not msg.get("more_body"):
            return body


async def _start(send: Any, status: int, content_type: bytes) -> None:
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", content_type)]})


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] != "http":
        return
    state["headers"] = {k.decode(): v.decode() for k, v in scope["headers"]}
    state["path"] = scope["path"]
    state["body"] = await _read_body(receive)
    if scope["path"].startswith("/openai/"):
        await _openai(send)
        return
    if state["headers"].get("x-fake") == "error":
        await _start(send, 400, b"application/json")
        await send({"type": "http.response.body", "body": ERROR_BODY, "more_body": False})
        return
    state["finished"] = False
    await _start(send, 200, b"text/event-stream")
    for chunk in STREAM_CHUNKS:
        await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await asyncio.sleep(0.12)
    state["finished"] = True
    await send({"type": "http.response.body", "body": b"", "more_body": False})


async def _openai(send: Any) -> None:
    """Azure OpenAI's v1 surface: a streamed chat completion, or a plain Responses object."""
    if state["path"].endswith("/responses"):
        await _start(send, 200, b"application/json")
        await send({"type": "http.response.body", "body": OPENAI_RESPONSE, "more_body": False})
        return
    await _start(send, 200, b"text/event-stream")
    for chunk in OPENAI_CHAT_CHUNKS:
        await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await asyncio.sleep(0.05)
    await send({"type": "http.response.body", "body": b"", "more_body": False})
