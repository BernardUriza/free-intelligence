"""The invite server is built with the REAL uvicorn — no mock.

v4.38.32 passed ``install_signal_handlers=`` to ``uvicorn.Config``, a kwarg that
does not exist: every gateway revision crash-looped at boot while CI stayed green,
because the boot tests replace ``_serve_invite_api`` wholesale.
"""

from __future__ import annotations

import signal

import pytest

from persona_gateway import app as app_mod
from persona_gateway.boot import GatewayBootState


@pytest.mark.parametrize("capture", [True, False])
def test_invite_server_builds_with_real_uvicorn(capture):
    server, coro = app_mod._serve_invite_api({}, "", GatewayBootState(), capture_signals=capture)
    coro.close()
    assert server.config.port == 8788


def test_signalless_server_leaves_the_process_sigterm_handler_alone():
    def ours(*_):
        return None

    previous = signal.signal(signal.SIGTERM, ours)
    try:
        server, coro = app_mod._serve_invite_api({}, "", GatewayBootState(), capture_signals=False)
        coro.close()
        with server.capture_signals():
            assert signal.getsignal(signal.SIGTERM) is ours
        assert signal.getsignal(signal.SIGTERM) is ours
    finally:
        signal.signal(signal.SIGTERM, previous)


def test_default_server_still_captures_sigterm():
    server, coro = app_mod._serve_invite_api({}, "", GatewayBootState(), capture_signals=True)
    coro.close()
    with server.capture_signals():
        assert signal.getsignal(signal.SIGTERM) == server.handle_exit
