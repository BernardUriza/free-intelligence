"""Unit tests for HDF5 orders module.

Tests cover CRUD operations for medical orders.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# CREATE ORDER TESTS
# ==============================================================================


class TestCreateOrder:
    """Tests for create_order function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.CORPUS_PATH")
    def test_create_order_returns_order_id(
        self,
        mock_corpus_path: MagicMock,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test create_order returns order ID."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import create_order

        # Mock CORPUS_PATH
        mock_corpus_path.parent.mkdir = MagicMock()

        # Mock HDF5 file
        mock_orders_group = MagicMock()
        mock_orders_group.create_dataset = MagicMock()

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)
        mock_task_group.create_group = MagicMock(return_value=mock_orders_group)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_orders_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)  # task doesn't exist
        mock_file.create_group = MagicMock(return_value=mock_task_group)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        order_id = create_order(
            session_id="session-123",
            order={"type": "prescription", "description": "Test order"},
        )

        assert order_id.startswith("order_")


# ==============================================================================
# GET ORDERS TESTS
# ==============================================================================


class TestGetOrders:
    """Tests for get_orders function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.CORPUS_PATH")
    def test_get_orders_raises_when_no_corpus(
        self,
        mock_corpus_path: MagicMock,
    ) -> None:
        """Test get_orders raises when corpus file doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import get_orders

        mock_corpus_path.exists.return_value = False

        with pytest.raises(ValueError, match="Corpus file not found"):
            get_orders("session-123")

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.CORPUS_PATH")
    def test_get_orders_returns_empty_when_no_task(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_orders returns empty list when no orders task."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import get_orders

        mock_corpus_path.exists.return_value = True

        # Mock HDF5 file with no task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        result = get_orders("session-123")

        assert result == []

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.CORPUS_PATH")
    def test_get_orders_returns_empty_when_no_orders_group(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_orders returns empty when no orders group."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import get_orders

        mock_corpus_path.exists.return_value = True

        # Mock task group without orders
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        result = get_orders("session-123")

        assert result == []

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.CORPUS_PATH")
    def test_get_orders_returns_orders_list(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_orders returns list of orders."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import get_orders

        mock_corpus_path.exists.return_value = True

        # Mock order data - need dataset that supports [()] access
        order_json = b'{"id": "order_123", "type": "prescription"}'

        class MockOrderDataset:
            def __getitem__(self, key):
                if key == ():
                    return order_json
                raise KeyError(key)

        mock_orders_group = MagicMock()
        mock_orders_group.__iter__ = MagicMock(return_value=iter(["order_123"]))
        mock_orders_group.__getitem__ = MagicMock(return_value=MockOrderDataset())

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_orders_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        result = get_orders("session-123")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "order_123"


# ==============================================================================
# UPDATE ORDER TESTS
# ==============================================================================


class TestUpdateOrder:
    """Tests for update_order function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders._h5_lock")
    def test_update_order_raises_when_no_task(
        self,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_order raises when task doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import update_order

        # Mock HDF5 file without task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No orders found"):
            update_order(
                session_id="session-123",
                order_id="order_123",
                order={"description": "Updated"},
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders._h5_lock")
    def test_update_order_raises_when_no_orders_group(
        self,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_order raises when orders group doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import update_order

        # Mock task group without orders
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No orders found"):
            update_order(
                session_id="session-123",
                order_id="order_123",
                order={"description": "Updated"},
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders._h5_lock")
    def test_update_order_raises_when_order_not_found(
        self,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_order raises when order doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import update_order

        # Mock orders group without the specific order
        mock_orders_group = MagicMock()
        mock_orders_group.__contains__ = MagicMock(return_value=False)

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_orders_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="Order order_123 not found"):
            update_order(
                session_id="session-123",
                order_id="order_123",
                order={"description": "Updated"},
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders._h5_lock")
    def test_update_order_success(
        self,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_order successfully updates order."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import update_order

        # Mock orders group with existing order
        mock_orders_group = MagicMock()
        mock_orders_group.__contains__ = MagicMock(return_value=True)
        mock_orders_group.__delitem__ = MagicMock()
        mock_orders_group.create_dataset = MagicMock()

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_orders_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise
        update_order(
            session_id="session-123",
            order_id="order_123",
            order={"description": "Updated"},
        )


# ==============================================================================
# DELETE ORDER TESTS
# ==============================================================================


class TestDeleteOrder:
    """Tests for delete_order function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    def test_delete_order_raises_when_no_task(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test delete_order raises when task doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import delete_order

        # Mock HDF5 file without task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No orders found"):
            delete_order(
                session_id="session-123",
                order_id="order_123",
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    def test_delete_order_raises_when_no_orders_group(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test delete_order raises when orders group doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import delete_order

        # Mock task group without orders
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No orders found"):
            delete_order(
                session_id="session-123",
                order_id="order_123",
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    def test_delete_order_raises_when_order_not_found(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test delete_order raises when order doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import delete_order

        # Mock orders group without the specific order
        mock_orders_group = MagicMock()
        mock_orders_group.__contains__ = MagicMock(return_value=False)

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_orders_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="Order order_123 not found"):
            delete_order(
                session_id="session-123",
                order_id="order_123",
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.orders.locked_session_h5")
    def test_delete_order_success(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test delete_order successfully deletes order."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import delete_order

        # Mock orders group with existing order
        mock_orders_group = MagicMock()
        mock_orders_group.__contains__ = MagicMock(return_value=True)
        mock_orders_group.__delitem__ = MagicMock()

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_orders_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise
        delete_order(
            session_id="session-123",
            order_id="order_123",
        )
