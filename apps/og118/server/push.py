"""OG118-PUSH-1 — tell the phone when an answer landed while nobody was looking.

A turn that outlives its connection (detached_turn) writes its answer to the record, and the
person who asked had to come back and look. Each device registers its APNs token per account;
when a late answer lands, every device of that account gets one alert. Unconfigured (no key)
it does nothing; a failed push never fails the delivery it rides on."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx
import jwt

log = logging.getLogger("uvicorn.error").getChild("og118.push")

HOSTS = {"production": "https://api.push.apple.com", "development": "https://api.sandbox.push.apple.com"}
TOKEN_TTL_S = 40 * 60
BODY_CHARS = 160
Sender = Callable[[str, str, dict], Awaitable[tuple[int, str]]]


class DeviceStore:
    def __init__(self, root: str | os.PathLike) -> None:
        self._root = Path(root)
        self._lock = threading.Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, owner: str) -> Path:
        return self._root / (hashlib.sha256(owner.encode("utf-8")).hexdigest()[:32] + ".json")

    def _read(self, owner: str) -> dict:
        try:
            return json.loads(self._path(owner).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def register(self, owner: str, token: str, environment: str) -> None:
        with self._lock:
            devices = self._read(owner)
            devices[token] = {"environment": environment, "updatedAt": int(time.time())}
            self._path(owner).write_text(json.dumps(devices), encoding="utf-8")

    def remove(self, owner: str, token: str) -> None:
        with self._lock:
            devices = self._read(owner)
            if devices.pop(token, None) is not None:
                self._path(owner).write_text(json.dumps(devices), encoding="utf-8")

    def for_owner(self, owner: str) -> dict:
        return self._read(owner)


_cached: tuple[float, str] | None = None


def is_configured() -> bool:
    return all(os.getenv(k) for k in ("OG118_APNS_KEY", "OG118_APNS_KEY_ID", "OG118_APNS_TEAM_ID"))


def _provider_token() -> str:
    global _cached
    now = time.time()
    if _cached and now - _cached[0] < TOKEN_TTL_S:
        return _cached[1]
    token = jwt.encode(
        {"iss": os.environ["OG118_APNS_TEAM_ID"], "iat": int(now)},
        os.environ["OG118_APNS_KEY"].replace("\\n", "\n"),
        algorithm="ES256",
        headers={"kid": os.environ["OG118_APNS_KEY_ID"]},
    )
    _cached = (now, token)
    return token


async def _send(token: str, environment: str, payload: dict) -> tuple[int, str]:
    headers = {
        "authorization": "bearer " + _provider_token(),
        "apns-topic": os.getenv("OG118_APNS_TOPIC", "com.bernard.og118"),
        "apns-push-type": "alert",
        "apns-priority": "10",
    }
    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        response = await client.post(f"{HOSTS[environment]}/3/device/{token}", headers=headers, json=payload)
    reason = ""
    if response.status_code != 200:
        try:
            reason = response.json().get("reason", "")
        except ValueError:
            reason = response.text[:80]
    return response.status_code, reason


def payload_for(title: str, body: str, conversation_id: str) -> dict:
    text = " ".join((body or "").split())
    if len(text) > BODY_CHARS:
        text = text[: BODY_CHARS - 1].rstrip() + "…"
    return {
        "aps": {"alert": {"title": title, "body": text}, "sound": "default", "thread-id": conversation_id},
        "conversation_id": conversation_id,
    }


async def notify(
    store: DeviceStore, owner: str, title: str, body: str, conversation_id: str, send: Sender | None = None
) -> int:
    """How many devices accepted the alert. A token Apple no longer knows is forgotten."""
    if send is None and not is_configured():
        return 0
    send = send or _send
    delivered = 0
    for token, device in store.for_owner(owner).items():
        try:
            status, reason = await send(token, device.get("environment", "production"), payload_for(title, body, conversation_id))
        except Exception as exc:
            log.warning("push not sent: %s", type(exc).__name__)
            continue
        if status == 200:
            delivered += 1
        elif status == 410 or reason in ("BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"):
            store.remove(owner, token)
            log.info("push token forgotten: %s", reason or status)
        else:
            log.warning("push refused: %s %s", status, reason)
    return delivered
