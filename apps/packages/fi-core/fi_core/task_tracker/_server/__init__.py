"""Internal helpers powering :mod:`fi_core.task_tracker.mcp_server`.

These modules are PRIVATE to fi-core (leading underscore in the package
name). The public surface is the MCP tools exposed by ``mcp_server.py``
and the contract in :mod:`fi_core.task_tracker.mcp_contract` — never
import these helpers from outside fi-core."""

from __future__ import annotations

from .errors import EXCEPTION_CODES, tracker_call
from .registry import get_tracker
from .serializers import error_payload, plan_summary_dict, step_dict

__all__ = [
    "EXCEPTION_CODES",
    "tracker_call",
    "get_tracker",
    "error_payload",
    "plan_summary_dict",
    "step_dict",
]
