"""Infrastructure layer - Concrete implementations."""

from backend.core.infrastructure.events.infrastructure.hdf5_store import HDF5EventStore

__all__ = ["HDF5EventStore"]
