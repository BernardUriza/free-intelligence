"""PyTorch trainer for ``fi_core.training``.

Adapted from Robo-Poet's
``src/legacy/robo-poet-pytorch/src/training/train.py`` (the
``GPTTrainer`` class). Key changes from the source:

- **GPU-only.** Fails fast with a clear ``RuntimeError`` if
  ``torch.cuda.is_available()`` is False. Per Bernard's doctrine:
  ``fi_core.training`` is for rented GPU sessions (Lambda / RunPod /
  vast.ai), not for CPU smoke tests. The mps backend is also rejected
  because flash-attention + bf16 paths have intermittent issues on it
  as of PyTorch 2.5.
- **Config-driven optimizer.** Caller passes ``optimizer_cls`` +
  ``optimizer_kwargs`` (default: AdamW from
  ``model.configure_optimizers``). Loss is fixed at the model's
  forward-time CE; caller does not need to plumb it.
- **TensorBoard stripped.** The Robo-Poet original wrote
  per-step metrics to ``SummaryWriter``; fi-core's trainer instead
  returns a structured metrics dict from ``fit`` and logs via
  ``structlog`` if available (graceful no-op otherwise). Consumers that
  want TensorBoard can subclass and add it.
- **Checkpoint format simplified.** The Robo-Poet original stored
  optimizer + scheduler + scaler state; we keep that, but drop the
  TensorBoard-specific log_dir and the "academic compliance" prints.

The trainer does NOT manage the DataLoader — caller passes them. This
keeps the trainer testable with mock loaders and decouples it from any
specific dataset shape.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

try:
    import torch
    from torch.utils.data import DataLoader
except ImportError as e:  # pragma: no cover - import-time error path
    raise ImportError(
        "fi_core.training.trainers.pytorch_trainer requires PyTorch. "
        "Install with: pip install 'fi-core[training]'"
    ) from e

try:
    import structlog

    _log: Any = structlog.get_logger("fi_core.training")
except ImportError:  # pragma: no cover
    import logging

    _log = logging.getLogger("fi_core.training")


def _require_cuda() -> torch.device:
    """Raise unless a CUDA GPU is available.

    The doctrine for ``fi_core.training`` is GPU-only: training on
    a real model with non-trivial corpus on CPU or MPS is either
    impractically slow (CPU) or unreliable (MPS in 2026). Fail fast
    rather than letting a trainer silently take 50× longer.
    """
    if not torch.cuda.is_available():
        raise RuntimeError(
            "fi_core.training.trainers.pytorch_trainer requires CUDA. "
            "Rent a GPU on Lambda Labs / RunPod / vast.ai, or run "
            "torch.cuda.is_available() to confirm setup. "
            "CPU and MPS are not supported paths."
        )
    return torch.device("cuda")


class PyTorchTrainer:
    """Config-driven PyTorch trainer for GPT-style language models.

    Adapted from Robo-Poet's ``GPTTrainer`` class. Features:

    - Mixed precision (autocast + GradScaler) when running on CUDA
    - Gradient accumulation for larger effective batch sizes
    - Learning-rate schedule: linear warmup → cosine decay to ``min_lr``
    - Gradient clipping (``max_grad_norm``, default 1.0)
    - Best-loss checkpoint tracking (``best.pth`` + per-epoch files)
    - Early stopping on no-improvement patience
    """

    def __init__(
        self,
        *,
        model: torch.nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        checkpoint_dir: str | Path,
        learning_rate: float = 6e-4,
        min_lr: float = 1e-6,
        weight_decay: float = 0.1,
        mixed_precision: bool = True,
        gradient_accumulation_steps: int = 1,
        max_grad_norm: float = 1.0,
        log_interval: int = 50,
        optimizer_cls: type[torch.optim.Optimizer] | None = None,
        optimizer_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.device = _require_cuda()
        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.learning_rate = learning_rate
        self.min_lr = min_lr
        self.weight_decay = weight_decay
        self.mixed_precision = mixed_precision
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.max_grad_norm = max_grad_norm
        self.log_interval = log_interval

        # Optimizer: either the model's own configure_optimizers
        # (default karpathy-style AdamW with decay/nodecay split), or
        # the caller's optimizer_cls + kwargs.
        if optimizer_cls is None:
            if hasattr(model, "configure_optimizers"):
                self.optimizer = model.configure_optimizers(
                    weight_decay=weight_decay, learning_rate=learning_rate
                )
            else:
                self.optimizer = torch.optim.AdamW(
                    model.parameters(),
                    lr=learning_rate,
                    weight_decay=weight_decay,
                )
        else:
            kwargs = {"lr": learning_rate, **(optimizer_kwargs or {})}
            self.optimizer = optimizer_cls(model.parameters(), **kwargs)

        self.scaler = torch.amp.GradScaler("cuda", enabled=mixed_precision)

        # Scheduler is constructed lazily in fit() once we know epochs.
        self.scheduler: torch.optim.lr_scheduler.CosineAnnealingLR | None = None
        self.warmup_steps = 0

        self.epoch = 0
        self.global_step = 0
        self.best_val_loss = float("inf")
        self.patience_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(
        self,
        *,
        epochs: int,
        save_every: int = 5,
        patience: int = 10,
    ) -> dict[str, Any]:
        """Run the training loop. Returns a metrics summary."""
        total_steps = len(self.train_loader) * epochs
        self.warmup_steps = max(1, int(0.1 * total_steps))
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=total_steps - self.warmup_steps,
            eta_min=self.min_lr,
        )

        _log.info(
            "training_started",
            epochs=epochs,
            total_steps=total_steps,
            warmup_steps=self.warmup_steps,
            mixed_precision=self.mixed_precision,
        )

        for epoch in range(epochs):
            self.epoch = epoch
            train_metrics = self._train_epoch()
            val_metrics = self._validate()
            _log.info(
                "epoch_complete",
                epoch=epoch + 1,
                train_loss=train_metrics["train_loss"],
                val_loss=val_metrics["val_loss"],
                perplexity=val_metrics["perplexity"],
                tokens_per_sec=train_metrics["tokens_per_sec"],
            )

            is_best = val_metrics["val_loss"] < self.best_val_loss
            if is_best:
                self.best_val_loss = val_metrics["val_loss"]
                self.patience_counter = 0
            else:
                self.patience_counter += 1

            if (epoch + 1) % save_every == 0 or is_best:
                self.save_checkpoint(
                    self.checkpoint_dir / f"checkpoint_epoch_{epoch + 1}.pth",
                    is_best=is_best,
                )

            if self.patience_counter >= patience:
                _log.info("early_stopping", epoch=epoch + 1, patience=patience)
                break

        return {
            "best_val_loss": self.best_val_loss,
            "global_step": self.global_step,
            "epochs_run": self.epoch + 1,
        }

    def save_checkpoint(self, path: Path, *, is_best: bool = False) -> None:
        """Persist model + optimizer + scheduler + scaler state to ``path``."""
        checkpoint: dict[str, Any] = {
            "epoch": self.epoch,
            "global_step": self.global_step,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scaler_state_dict": self.scaler.state_dict(),
            "best_val_loss": self.best_val_loss,
        }
        if self.scheduler is not None:
            checkpoint["scheduler_state_dict"] = self.scheduler.state_dict()
        torch.save(checkpoint, path)
        if is_best:
            torch.save(checkpoint, self.checkpoint_dir / "best.pth")

    def load_checkpoint(self, path: Path) -> None:
        """Restore state previously written by :meth:`save_checkpoint`."""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scaler.load_state_dict(checkpoint["scaler_state_dict"])
        if self.scheduler is not None and "scheduler_state_dict" in checkpoint:
            self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        self.epoch = checkpoint["epoch"]
        self.global_step = checkpoint["global_step"]
        self.best_val_loss = checkpoint["best_val_loss"]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _train_epoch(self) -> dict[str, float]:
        self.model.train()
        total_loss = 0.0
        total_tokens = 0
        start = time.time()
        self.optimizer.zero_grad()

        for batch_idx, (inputs, targets) in enumerate(self.train_loader):
            inputs = inputs.to(self.device, non_blocking=True)
            targets = targets.to(self.device, non_blocking=True)

            with torch.amp.autocast("cuda", enabled=self.mixed_precision):
                _, loss = self.model(inputs, targets)
                loss = loss / self.gradient_accumulation_steps

            self.scaler.scale(loss).backward()

            if (batch_idx + 1) % self.gradient_accumulation_steps == 0:
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.max_grad_norm
                )
                self.scaler.step(self.optimizer)
                self.scaler.update()
                self.optimizer.zero_grad()

                if self.global_step < self.warmup_steps:
                    warmup_lr = self.learning_rate * (self.global_step + 1) / self.warmup_steps
                    for pg in self.optimizer.param_groups:
                        pg["lr"] = warmup_lr
                elif self.scheduler is not None:
                    self.scheduler.step()

                self.global_step += 1

            total_loss += loss.item() * self.gradient_accumulation_steps
            total_tokens += inputs.numel()

            if batch_idx % self.log_interval == 0:
                elapsed = max(time.time() - start, 1e-9)
                _log.info(
                    "train_step",
                    batch=batch_idx,
                    loss=loss.item() * self.gradient_accumulation_steps,
                    lr=self.optimizer.param_groups[0]["lr"],
                    tokens_per_sec=total_tokens / elapsed,
                )

        elapsed = max(time.time() - start, 1e-9)
        return {
            "train_loss": total_loss / max(len(self.train_loader), 1),
            "tokens_per_sec": total_tokens / elapsed,
            "elapsed_time": elapsed,
        }

    @torch.no_grad()
    def _validate(self) -> dict[str, float]:
        self.model.eval()
        total_loss = 0.0
        total_tokens = 0
        for inputs, targets in self.val_loader:
            inputs = inputs.to(self.device, non_blocking=True)
            targets = targets.to(self.device, non_blocking=True)
            with torch.amp.autocast("cuda", enabled=self.mixed_precision):
                _, loss = self.model(inputs, targets)
            total_loss += loss.item()
            total_tokens += inputs.numel()
        avg_loss = total_loss / max(len(self.val_loader), 1)
        return {
            "val_loss": avg_loss,
            "perplexity": math.exp(avg_loss),
            "total_tokens": float(total_tokens),
        }
