"""Assistant workflow router wrapper.

This module delegates to `backend.api.public.workflows.assistant` package,
which contains split endpoints for introduction, chat, diagnostics, and streaming.
"""

from __future__ import annotations

from .assistant import router  # re-export aggregated router
