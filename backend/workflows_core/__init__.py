from __future__ import annotations

__all__ = [
    "WorkflowId",
]

from typing import NewType

WorkflowId = NewType("WorkflowId", str)
