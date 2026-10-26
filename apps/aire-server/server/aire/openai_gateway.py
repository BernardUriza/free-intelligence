"""The OpenAI door (#51): the OpenAI v1 wire format, relayed to AIRE's Azure OpenAI.

A client points its OpenAI SDK at ``https://<aire>/openai/v1`` with an AIRE key
as its API key and changes nothing else. Unlike the Anthropic door there is no
pass-through: every caller is an invited key, AIRE always lends its own Azure
credential, and every turn is priced and banked against that key's ceiling.
That is the whole reason this door exists instead of handing out the Azure key:
Azure has no prepaid balance, so a key without a ceiling is an open tab —
``insult-openai`` ran up USD 81 in eight days that way (2026-10).

Only the two billed generation endpoints are routed. Every other OpenAI path
(embeddings, files, images…) would spend Azure money with no usage this door
knows how to price, so it does not exist here until it can be billed.
"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from . import gateway, gateway_mirror, openai_assemble, pricing, relay, tokens
from .gateway_mirror import ResponseTap

router = APIRouter()


def azure_openai() -> tuple[str, tuple[str, str]] | None:
    """Where the OpenAI door (#51) relays and the header it lends there, or None
    when either half is missing. Its own slot, never the Anthropic one: a key
    revoked on one provider must not silence the other."""
    base = os.environ.get("AIRE_OPENAI_UPSTREAM", "")
    key = os.environ.get("AIRE_LEND_AZURE_OPENAI_KEY", "")
    return (base, ("api-key", key)) if base and key else None


def lend_openai(headers: list[tuple[str, str]], credential: tuple[str, str]) -> list[tuple[str, str]]:
    """Shed whatever the caller presented (its AIRE key rides as the Bearer or as
    `api-key`) and present AIRE's Azure credential instead."""
    kept = [(k, v) for k, v in headers if k.lower() not in ("authorization", "api-key", "x-api-key")]
    return [*kept, credential]


def error(message: str, status: int, kind: str = "api_error") -> JSONResponse:
    """AIRE's own refusals wear OpenAI's error shape — the client's SDK parses
    this body with the code it uses for the real upstream."""
    return JSONResponse({"error": {"message": message, "type": kind, "code": None}},
                        status_code=status)


@router.post("/openai/v1/chat/completions")
async def chat_completions(request: Request) -> Response:
    return await _relay(request, openai_assemble.with_usage(await request.body()))


@router.post("/openai/v1/responses")
async def responses(request: Request) -> Response:
    return await _relay(request, await request.body())


async def _relay(request: Request, body: bytes) -> Response:
    holder = request.state.holder  # the door admits nobody else on this prefix
    base, credential = azure_openai()  # and refused already if there was nothing to lend
    exchange = uuid.uuid4().hex
    await gateway_mirror.log_request(exchange, request.headers, body, holder.nickname)
    headers = lend_openai(gateway.forward_headers(request), credential)

    def tap_for(status: int, content_type: str) -> ResponseTap:
        return ResponseTap(exchange, status, content_type,
                           tokens.biller(holder, pricing.openai_usd), openai_assemble.assemble)

    return await relay.forward(request, body, headers, base, tap_for, holder, error)
