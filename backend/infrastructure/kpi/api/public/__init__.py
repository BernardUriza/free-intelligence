"""KPI Public API.

Public endpoints for KPI metrics (requires authentication).
"""

from .kpis import router

__all__ = ["router"]
