"""Append-only ([[log-is-the-truth]]): the file is the truth; mirrors get a copy."""

from datetime import datetime, timezone
from typing import Callable

from .config import LOG

MIRRORS: list[Callable[[str], None]] = []


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def append_file(line: str) -> None:
    with LOG.open("a") as f:
        f.write(line + "\n")
        f.flush()


def append(line: str) -> None:
    append_file(line)
    for mirror in MIRRORS:
        mirror(line)
