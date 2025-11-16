"""Base repository pattern for HDF5 operations.

Abstract base class that provides common HDF5 operations with proper
error handling, logging, and type safety.

Clean Code Principles:
- Template Method Pattern: Define algorithm structure, let subclasses implement steps
- DRY: Common operations (open file, read, write, close) are centralized
- Explicit Error Handling: All I/O errors are caught and logged properly
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generic, Optional, TypeVar, Union

import h5py

from backend.logger import get_logger

logger = get_logger(__name__)

# Generic type for any entity stored in HDF5
T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for HDF5 data access.

    Provides:
    - File management (open, close, ensure existence)
    - Error handling and logging
    - Context managers for safe operations
    - Consistent interface for all repositories
    """

    def __init__(self, h5_file_path: Union[str, Path]) -> None:
        """Initialize repository with HDF5 file path.

        Args:
            h5_file_path: Path to HDF5 database file

        Raises:
            ValueError: If path is not a valid file or directory
        """
        self.h5_file_path = Path(h5_file_path)
        self._ensure_parent_dir_exists()

    def _ensure_parent_dir_exists(self) -> None:
        """Ensure parent directory exists, create if needed."""
        self.h5_file_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _open_file(self, mode: str = "r+") -> Generator[h5py.File, None, None]:
        """Context manager for safe HDF5 file operations.

        Args:
            mode: File open mode ('r', 'r+', 'w', 'w-', 'x', 'a')

        Yields:
            h5py.File object

        Raises:
            IOError: If file cannot be opened
            h5py.OSError: If HDF5 operation fails
        """
        file_obj = None
        try:
            file_obj = h5py.File(self.h5_file_path, mode)
            yield file_obj
        except OSError as e:
            logger.error(
                "HDF5_FILE_ERROR",
                path=str(self.h5_file_path),
                mode=mode,
                error=str(e),
            )
            raise OSError(f"Failed to open HDF5 file: {e}") from e
        finally:
            if file_obj:
                file_obj.close()

    @abstractmethod
    def create(self, entity: T, **kwargs: Any) -> str:
        """Create new entity in repository.

        Args:
            entity: Entity to store
            **kwargs: Additional parameters for the operation

        Returns:
            ID of created entity

        Raises:
            ValueError: If entity is invalid
            IOError: If storage operation fails
        """
        pass

    @abstractmethod
    def read(self, entity_id: str) -> Optional[T]:
        """Read entity from repository.

        Args:
            entity_id: ID of entity to retrieve

        Returns:
            Entity if found, None otherwise

        Raises:
            IOError: If read operation fails
        """
        pass

    @abstractmethod
    def update(self, entity_id: str, entity: T) -> bool:
        """Update existing entity in repository.

        Args:
            entity_id: ID of entity to update
            entity: Updated entity data

        Returns:
            True if update successful, False if entity not found

        Raises:
            ValueError: If entity is invalid
            IOError: If update operation fails
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity from repository.

        Args:
            entity_id: ID of entity to delete

        Returns:
            True if deletion successful, False if entity not found

        Raises:
            IOError: If delete operation fails
        """
        pass

    @abstractmethod
    def list_all(self, limit: Optional[int] = None) -> list[T]:
        """List all entities in repository.

        Args:
            limit: Maximum number of entities to return, None for all

        Returns:
            List of entities

        Raises:
            IOError: If list operation fails
        """
        pass

    def _log_operation(
        self,
        operation: str,
        entity_id: Optional[str] = None,
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """Log repository operation for audit trail.

        Args:
            operation: Name of operation (create, read, update, delete)
            entity_id: ID of affected entity
            status: Operation status (success, failed)
            error: Error message if operation failed
        """
        logger.info(
            f"REPOSITORY_{operation.upper()}",
            entity_id=entity_id,
            status=status,
            error=error,
        )
