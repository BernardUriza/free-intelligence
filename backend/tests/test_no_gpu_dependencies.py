"""CI/CD test: Ensure backend has NO GPU dependencies.

Verifies that production backend can run without PyTorch.
This saves ~3GB in deployment size.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-02-02
Card: Vector Math CPU/GPU Separation
"""

import sys

import pytest


def test_torch_not_importable():
    """PyTorch should NOT be installed in production backend."""
    with pytest.raises(ImportError):
        import torch  # noqa: F401


def test_sentence_transformers_not_importable():
    """sentence-transformers should NOT be installed in production."""
    with pytest.raises(ImportError):
        import sentence_transformers  # noqa: F401


def test_cpu_math_importable():
    """CPU math utils should be importable without GPU libs."""
    from backend.utils.math.cpu import cosine_similarity, cosine_similarity_batch

    assert callable(cosine_similarity)
    assert callable(cosine_similarity_batch)


def test_top_level_math_importable():
    """Top-level math module should work without GPU."""
    from backend.utils.math import cosine_similarity

    assert callable(cosine_similarity)


def test_no_torch_in_modules_after_import():
    """Importing math utils should NOT load torch."""
    # Clear torch if previously loaded
    if "torch" in sys.modules:
        del sys.modules["torch"]

    from backend.utils.math import cosine_similarity  # noqa: F401

    assert "torch" not in sys.modules


def test_cpu_math_functional():
    """CPU math should work correctly without GPU."""
    from backend.utils.math import cosine_similarity

    # Test identical vectors
    score = cosine_similarity([1, 0, 0], [1, 0, 0])
    assert abs(score - 1.0) < 1e-6

    # Test orthogonal vectors
    score = cosine_similarity([1, 0, 0], [0, 1, 0])
    assert abs(score - 0.0) < 1e-6
