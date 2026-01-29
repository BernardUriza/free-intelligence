"""Shared fixtures for RAG Service tests."""

from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import torch


# ==============================================================================
# MOCK FIXTURES - GPU/Torch
# ==============================================================================

@pytest.fixture
def mock_torch_cuda():
    """Mock torch.cuda module for CUDA tests."""
    with patch("torch.cuda.is_available", return_value=True), \
         patch("torch.cuda.get_device_name", return_value="NVIDIA GeForce RTX 3090"), \
         patch("torch.cuda.get_device_properties") as mock_props, \
         patch("torch.cuda.memory_allocated", return_value=512 * 1024 * 1024), \
         patch("torch.cuda.memory_reserved", return_value=1024 * 1024 * 1024), \
         patch("torch.cuda.empty_cache"):

        # Mock device properties (VRAM)
        mock_device = MagicMock()
        mock_device.total_memory = 24 * 1024**3  # 24 GB VRAM
        mock_props.return_value = mock_device

        yield


@pytest.fixture
def mock_torch_mps():
    """Mock torch.backends.mps for Apple Silicon tests."""
    with patch("torch.cuda.is_available", return_value=False), \
         patch("torch.backends.mps.is_available", return_value=True):
        yield


@pytest.fixture
def mock_torch_cpu():
    """Mock no GPU available (CPU mode)."""
    with patch("torch.cuda.is_available", return_value=False), \
         patch("torch.backends.mps.is_available", return_value=False):
        yield


# ==============================================================================
# MOCK FIXTURES - SentenceTransformer
# ==============================================================================

@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer to avoid model download."""
    mock_model = MagicMock()

    # Mock encode() to return fake embeddings
    def mock_encode(texts, batch_size=32, convert_to_numpy=True, **kwargs):
        import numpy as np
        num_texts = len(texts)
        # Return 384-dim embeddings (all-MiniLM-L6-v2 dimension)
        return np.random.rand(num_texts, 384).astype(np.float32)

    mock_model.encode = MagicMock(side_effect=mock_encode)

    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        yield mock_model


# ==============================================================================
# FASTAPI CLIENT FIXTURE
# ==============================================================================

@pytest.fixture
def test_client(mock_sentence_transformer, mock_torch_mps):
    """FastAPI TestClient with mocked GPU/model."""
    from fastapi.testclient import TestClient

    # Import AFTER mocking (so app uses mocks)
    from rag_service.main import app

    with TestClient(app) as client:
        yield client


# ==============================================================================
# ENVIRONMENT VARIABLE FIXTURES
# ==============================================================================

@pytest.fixture
def mock_env_require_gpu_true(monkeypatch):
    """Mock RAG_REQUIRE_GPU=true."""
    monkeypatch.setenv("RAG_REQUIRE_GPU", "true")


@pytest.fixture
def mock_env_require_gpu_false(monkeypatch):
    """Mock RAG_REQUIRE_GPU=false."""
    monkeypatch.setenv("RAG_REQUIRE_GPU", "false")


@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Mock RAG_API_KEY."""
    monkeypatch.setenv("RAG_API_KEY", "test-api-key-12345")
