"""Unit tests for HDF5 SOAP module.

Tests cover SOAP note generation data storage.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# GET SOAP DATA TESTS
# ==============================================================================


class TestGetSoapData:
    """Tests for get_soap_data function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.CORPUS_PATH")
    def test_raises_when_no_corpus(
        self,
        mock_corpus_path: MagicMock,
    ) -> None:
        """Test get_soap_data raises when corpus doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.soap import (
            get_soap_data,
        )

        mock_corpus_path.exists.return_value = False

        with pytest.raises(ValueError, match="Corpus file not found"):
            get_soap_data("session-123")

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.CORPUS_PATH")
    def test_raises_when_no_task(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_soap_data raises when task doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.soap import (
            get_soap_data,
        )

        mock_corpus_path.exists.return_value = True

        # Mock file without task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="Task.*not found"):
            get_soap_data("session-123")

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.CORPUS_PATH")
    def test_raises_when_no_soap_data(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_soap_data raises when no SOAP data."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.soap import (
            get_soap_data,
        )

        mock_corpus_path.exists.return_value = True

        # Mock task without soap_data
        mock_task = MagicMock()
        mock_task.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No SOAP data found"):
            get_soap_data("session-123")

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.CORPUS_PATH")
    def test_returns_soap_data_from_new_format(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_soap_data returns SOAP data from new format."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.soap import (
            get_soap_data,
        )

        mock_corpus_path.exists.return_value = True

        # Mock dataset with [()] access
        class MockDataset:
            def __getitem__(self, key):
                if key == ():
                    return b'{"subjective": "Patient reports pain"}'
                raise KeyError(key)

        # Mock task with soap_data
        mock_task = MagicMock()
        mock_task.__contains__ = MagicMock(side_effect=lambda k: k == "soap_data")
        mock_task.__getitem__ = MagicMock(return_value=MockDataset())

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        result = get_soap_data("session-123")

        assert result == {"subjective": "Patient reports pain"}

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.CORPUS_PATH")
    def test_returns_soap_data_from_legacy_format(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_soap_data returns SOAP data from legacy format."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.soap import (
            get_soap_data,
        )

        mock_corpus_path.exists.return_value = True

        # Mock dataset with [()] access
        class MockDataset:
            def __getitem__(self, key):
                if key == ():
                    return b'{"assessment": "Diagnosis"}'
                raise KeyError(key)

        # Mock task with soap_note (legacy)
        mock_task = MagicMock()

        def contains_check(k):
            if k == "soap_data":
                return False
            if k == "soap_note":
                return True
            return False

        mock_task.__contains__ = MagicMock(side_effect=contains_check)
        mock_task.__getitem__ = MagicMock(return_value=MockDataset())

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        result = get_soap_data("session-123")

        assert result == {"assessment": "Diagnosis"}
