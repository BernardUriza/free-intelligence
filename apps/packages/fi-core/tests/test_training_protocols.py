"""Tests for `fi_core.training.protocols`.

Pure-Python tests — verify that the Protocols are runtime_checkable
and that the canonical concrete implementations satisfy them.
"""

from __future__ import annotations

import pytest

from fi_core.training import (
    DatasetReader,
    GenerationModel,
    Tokenizer,
    Trainer,
)


class TestProtocolsRuntimeCheckable:
    def test_dataset_reader_is_runtime_checkable(self):
        """Anything with read_chunks + count satisfies the Protocol."""

        class _Reader:
            async def read_chunks(self, namespace, *, limit=None):  # noqa: ARG002
                yield

            async def count(self, namespace):  # noqa: ARG002
                return 0

        assert isinstance(_Reader(), DatasetReader)

    def test_tokenizer_is_runtime_checkable(self):
        class _Tok:
            @property
            def vocab_size(self):
                return 100

            def encode(self, text):  # noqa: ARG002
                return [0]

            def decode(self, ids):  # noqa: ARG002
                return ""

        assert isinstance(_Tok(), Tokenizer)

    def test_generation_model_is_runtime_checkable(self):
        class _Gen:
            def generate(
                self,
                prompt_ids,  # noqa: ARG002
                *,
                max_new_tokens=200,  # noqa: ARG002
                temperature=0.8,  # noqa: ARG002
                top_k=40,  # noqa: ARG002
                top_p=0.95,  # noqa: ARG002
                repetition_penalty=1.0,  # noqa: ARG002
            ):
                return []

        assert isinstance(_Gen(), GenerationModel)

    def test_trainer_is_runtime_checkable(self):
        class _Tr:
            def fit(self, *, epochs, save_every=5, patience=10):  # noqa: ARG002
                return {"best_val_loss": 0.0, "global_step": 0}

            def save_checkpoint(self, path, *, is_best=False):  # noqa: ARG002
                pass

            def load_checkpoint(self, path):  # noqa: ARG002
                pass

        assert isinstance(_Tr(), Trainer)

    def test_non_conforming_class_is_rejected(self):
        class _NotAReader:
            pass

        assert not isinstance(_NotAReader(), DatasetReader)


class TestPublicAPI:
    def test_top_level_reexports(self):
        """``from fi_core.training import X`` works for all 4 Protocols."""
        import fi_core.training as training

        assert hasattr(training, "DatasetReader")
        assert hasattr(training, "Tokenizer")
        assert hasattr(training, "GenerationModel")
        assert hasattr(training, "Trainer")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
