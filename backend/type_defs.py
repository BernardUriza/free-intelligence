"""Type definitions for Free Intelligence backend.

Re-exports types from backend.src.fi_common.types for backward compatibility.
"""

from __future__ import annotations

from backend.src.fi_common.types.type_defs import AuditLogDict, DiarizationChunkDict

__all__ = ["AuditLogDict", "DiarizationChunkDict"]
