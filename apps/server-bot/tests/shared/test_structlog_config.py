"""shared.logging_setup — the canonical structlog wiring.

Positive: LOG_FORMAT=json renders one JSON object per line (the contract KQL
parsing depends on — see the 2026-07-08 ANSI-logs P0). Resistance: console
mode never emits JSON, and processors_extra hooks run before the renderer.
"""

from __future__ import annotations

import json

import structlog

from shared.logging_setup import configure_structlog


def _capture_line(capsys) -> str:
    log = structlog.get_logger()
    log.info("probe_event", campo="valor")
    return capsys.readouterr().out.strip()


def test_json_mode_emits_parseable_json(monkeypatch, capsys):
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_structlog()
    line = _capture_line(capsys)
    parsed = json.loads(line)
    assert parsed["event"] == "probe_event"
    assert parsed["campo"] == "valor"
    assert parsed["level"] == "info"
    assert "timestamp" in parsed


def test_console_mode_is_not_json(monkeypatch, capsys):
    monkeypatch.setenv("LOG_FORMAT", "console")
    configure_structlog()
    line = _capture_line(capsys)
    try:
        json.loads(line)
        emitted_json = True
    except json.JSONDecodeError:
        emitted_json = False
    assert not emitted_json
    assert "probe_event" in line


def test_processors_extra_run_before_renderer(monkeypatch, capsys):
    monkeypatch.setenv("LOG_FORMAT", "json")

    def stamp(logger, method_name, event_dict):
        event_dict["stamped"] = True
        return event_dict

    configure_structlog(processors_extra=[stamp])
    line = _capture_line(capsys)
    assert json.loads(line)["stamped"] is True


def test_json_mode_keeps_the_traceback(monkeypatch, capsys):
    """2026-11-04: every `log.exception` in prod read `exc_info: true`, so the runner's
    dead embeddings logged an error for three weeks without ever saying why."""
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_structlog()
    try:
        raise RuntimeError("la causa real")
    except RuntimeError:
        structlog.get_logger().exception("probe_failed")
    parsed = json.loads(capsys.readouterr().out.strip())
    assert "la causa real" in parsed["exception"]
