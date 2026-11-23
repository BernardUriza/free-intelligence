"""Dependency-free helpers for what a Postgres driver hands back."""

from __future__ import annotations


def affected_rows(command_tag: str | None) -> int:
    """Row count in a command tag ("DELETE 3", "INSERT 0 1", "UPDATE 0"); 0 when it has none."""
    last = (command_tag or "").rsplit(" ", 1)[-1]
    return int(last) if last.isdigit() else 0
