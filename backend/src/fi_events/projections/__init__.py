"""Projections module - Materialized views from event streams.

Exports:
- Projection: Base class for all projections
- ProjectionRegistry: Central registry
- Concrete projections: SessionIndex, TranscriptionTimeline, etc.
"""

from backend.src.fi_events.projections.consumers import (
    AssistantTurnsProjection,
    MetricsByTypeProjection,
    SessionIndexProjection,
    TranscriptionTimelineProjection,
    register_default_projections,
)
from backend.src.fi_events.projections.registry import (
    Projection,
    ProjectionRegistry,
    ProjectionState,
    ProjectionStatus,
    get_registry,
    reset_registry,
)

__all__ = [
    # Registry
    "Projection",
    "ProjectionRegistry",
    "ProjectionState",
    "ProjectionStatus",
    "get_registry",
    "reset_registry",
    # Consumers
    "SessionIndexProjection",
    "TranscriptionTimelineProjection",
    "AssistantTurnsProjection",
    "MetricsByTypeProjection",
    "register_default_projections",
]
