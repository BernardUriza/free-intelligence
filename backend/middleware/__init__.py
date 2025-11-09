"""Middleware modules for Free Intelligence backend."""

from __future__ import annotations

from .internal_only import InternalOnlyMiddleware

__all__ = ["InternalOnlyMiddleware"]
