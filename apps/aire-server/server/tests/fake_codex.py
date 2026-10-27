"""A tiny `codex exec --json` for the backend's tests — the argv and the JSON
lines are real (copied from codex-cli 0.164.0, 2026-10-26), the model is not.
It echoes `pong: <prompt>`, keeps each thread's history in FAKE_CODEX_STORE so
`exec resume <id>` can continue it, refuses an unknown thread the way codex
does (stderr `no rollout found`, exit 1), runs a "tool" whose outcome follows
the sandbox, fails a turn on "fail", dies silently on "crash", and records the
argv it was given in `last_argv.json` so a test can read the dial."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

STORE = Path(os.environ.get("FAKE_CODEX_STORE", "/nonexistent"))
USAGE = {"input_tokens": 10, "cached_input_tokens": 7, "cache_write_input_tokens": 1,
         "output_tokens": 2, "reasoning_output_tokens": 0}


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def parse(argv: list[str]) -> tuple[str | None, list[str], str]:
    thread = argv[argv.index("resume") + 1] if "resume" in argv else None
    images = [argv[i + 1] for i, a in enumerate(argv) if a == "-i"]
    return thread, images, argv[-1]


def main() -> int:
    STORE.mkdir(parents=True, exist_ok=True)
    (STORE / "last_argv.json").write_text(json.dumps(sys.argv[1:]))
    thread, images, prompt = parse(sys.argv[1:])
    if thread and not (STORE / f"{thread}.json").exists():
        print(f"Error: thread/resume: thread/resume failed: no rollout found for thread id {thread}"
              " (code -32600)", file=sys.stderr)
        return 1
    thread = thread or str(uuid.uuid4())
    path = STORE / f"{thread}.json"
    history = json.loads(path.read_text()) if path.exists() else []
    emit({"type": "thread.started", "thread_id": thread})
    if "crash" in prompt:
        print("segfault", file=sys.stderr)
        return 3
    emit({"type": "turn.started"})
    if "fail" in prompt:
        emit({"type": "turn.failed", "error": {"message": "boom"}})
        return 0
    if "tool" in prompt:
        status = "completed" if 'sandbox_mode="workspace-write"' in sys.argv else "failed"
        emit({"type": "item.started", "item": {"id": "item_0", "type": "command_execution",
                                                "command": "ls", "aggregated_output": "", "status": "in_progress"}})
        emit({"type": "item.completed", "item": {"id": "item_0", "type": "command_execution",
                                                  "command": "ls", "aggregated_output": "", "status": status}})
    text = f"pong: {prompt}" + (f" after {len(history)}" if history else "") + (f" images: {len(images)}" if images else "")
    emit({"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": text}})
    emit({"type": "turn.completed", "usage": USAGE})
    path.write_text(json.dumps([*history, prompt]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
