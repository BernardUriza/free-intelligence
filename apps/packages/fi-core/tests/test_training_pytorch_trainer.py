"""Tests for `fi_core.training.trainers.pytorch_trainer`.

The trainer is GPU-only by design — all functional tests (forward pass,
checkpoint round-trip, fit loop) are gated on ``torch.cuda.is_available()``
and skipped on the CI Mac runner that has no CUDA. The CPU-runnable
tests verify the early-fail behavior and Protocol satisfaction.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from fi_core.training import Trainer
from fi_core.training.trainers.pytorch_trainer import (
    PyTorchTrainer,
    _require_cuda,
)


REQUIRES_CUDA = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="fi_core.training.trainers requires CUDA",
)


class TestCUDAGate:
    def test_require_cuda_raises_on_no_cuda(self, monkeypatch):
        # Force no-CUDA path regardless of host
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        with pytest.raises(RuntimeError, match="requires CUDA"):
            _require_cuda()

    def test_require_cuda_passes_on_cuda(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
        device = _require_cuda()
        assert device.type == "cuda"

    def test_trainer_constructor_fails_fast_without_cuda(
        self, monkeypatch, tmp_path
    ):
        """The constructor calls _require_cuda; absent CUDA it must raise."""
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        from fi_core.training.models.tiny_gpt import GPTConfig, TinyGPT

        model = TinyGPT(GPTConfig(vocab_size=32, block_size=8, n_layer=1, n_head=1, n_embd=8))
        # Empty DataLoader is fine; we never get past the CUDA check
        loader = torch.utils.data.DataLoader([], batch_size=1)
        with pytest.raises(RuntimeError, match="requires CUDA"):
            PyTorchTrainer(
                model=model,
                train_loader=loader,
                val_loader=loader,
                checkpoint_dir=tmp_path,
            )


@REQUIRES_CUDA
class TestPyTorchTrainerCUDA:
    """End-to-end CUDA path. Only runs on a machine with a CUDA GPU.

    These are smoke tests, not benchmarks — they verify the trainer
    glues the model + optimizer + loop without crashing, not that it
    converges.
    """

    def _make_loader(self, vocab_size: int, block_size: int, batches: int = 2):
        """Tiny synthetic loader yielding ``(input, target)`` pairs."""

        class _DS(torch.utils.data.Dataset):
            def __len__(self):
                return batches * 4

            def __getitem__(self, _):
                x = torch.randint(0, vocab_size, (block_size,))
                y = torch.randint(0, vocab_size, (block_size,))
                return x, y

        return torch.utils.data.DataLoader(_DS(), batch_size=4)

    def test_trainer_satisfies_protocol(self, tmp_path):
        from fi_core.training.models.tiny_gpt import GPTConfig, TinyGPT

        cfg = GPTConfig(vocab_size=64, block_size=8, n_layer=2, n_head=2, n_embd=16)
        model = TinyGPT(cfg)
        loader = self._make_loader(cfg.vocab_size, cfg.block_size)
        trainer = PyTorchTrainer(
            model=model,
            train_loader=loader,
            val_loader=loader,
            checkpoint_dir=tmp_path,
        )
        assert isinstance(trainer, Trainer)

    def test_fit_runs_one_epoch_on_toy_data(self, tmp_path):
        from fi_core.training.models.tiny_gpt import GPTConfig, TinyGPT

        cfg = GPTConfig(vocab_size=64, block_size=8, n_layer=2, n_head=2, n_embd=16)
        model = TinyGPT(cfg)
        loader = self._make_loader(cfg.vocab_size, cfg.block_size)
        trainer = PyTorchTrainer(
            model=model,
            train_loader=loader,
            val_loader=loader,
            checkpoint_dir=tmp_path,
            log_interval=1000,  # silence
        )
        result = trainer.fit(epochs=1, save_every=1, patience=10)
        assert "best_val_loss" in result
        assert result["epochs_run"] == 1

    def test_checkpoint_round_trip(self, tmp_path):
        from fi_core.training.models.tiny_gpt import GPTConfig, TinyGPT

        cfg = GPTConfig(vocab_size=64, block_size=8, n_layer=2, n_head=2, n_embd=16)
        model = TinyGPT(cfg)
        loader = self._make_loader(cfg.vocab_size, cfg.block_size)
        trainer = PyTorchTrainer(
            model=model,
            train_loader=loader,
            val_loader=loader,
            checkpoint_dir=tmp_path,
        )
        trainer.fit(epochs=1, save_every=1, patience=10)
        ckpt_path = tmp_path / "best.pth"
        assert ckpt_path.exists()
        # Build a fresh trainer + model and load
        model2 = TinyGPT(cfg)
        trainer2 = PyTorchTrainer(
            model=model2,
            train_loader=loader,
            val_loader=loader,
            checkpoint_dir=tmp_path,
        )
        trainer2.load_checkpoint(ckpt_path)
        # Param values should match (within bf16/fp32 conversion noise)
        for p1, p2 in zip(model.parameters(), model2.parameters(), strict=False):
            assert torch.allclose(p1.detach().cpu(), p2.detach().cpu(), atol=1e-5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
