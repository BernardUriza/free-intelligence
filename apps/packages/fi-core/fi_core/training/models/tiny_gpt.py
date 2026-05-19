"""Compact GPT class for fi-core training experiments.

Architecture follows the standard decoder-only Transformer (Vaswani 2017
+ Radford 2018) with the conventional simplifications used in karpathy's
minGPT / nanoGPT: pre-LayerNorm blocks, tied embedding ↔ unembedding
weights, GELU activations, causal self-attention via
``torch.nn.functional.scaled_dot_product_attention`` (PyTorch ≥2.0).

The class is config-driven so a caller can dial vocab_size, hidden dim,
depth, head count, and context length to fit any param budget. Two
presets live in ``presets.py``: ``tiny_gpt_5m`` (custom BPE, ~5M params)
and ``tiny_gpt_30m`` (tiktoken cl100k_base, ~30M params).

Generation logic (temperature, top-k, top-p, repetition penalty) is
adapted from Robo-Poet's ``src/legacy/robo-poet-pytorch/src/generation/generate.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError as e:  # pragma: no cover - import-time error path
    raise ImportError(
        "fi_core.training.models.tiny_gpt requires PyTorch. "
        "Install with: pip install 'fi-core[training]'"
    ) from e


@dataclass
class GPTConfig:
    """Architectural hyperparameters for ``TinyGPT``.

    Defaults are the 5M-param preset (custom BPE, 8K vocab). For the
    30M-param tiktoken preset, see ``presets.tiny_gpt_30m``.
    """

    vocab_size: int = 8000
    block_size: int = 256
    n_layer: int = 6
    n_head: int = 8
    n_embd: int = 256
    dropout: float = 0.1
    bias: bool = True
    tie_weights: bool = True


class _CausalSelfAttention(nn.Module):
    """Multi-head self-attention with causal masking.

    Uses PyTorch ≥2.0's fused ``scaled_dot_product_attention`` which
    automatically picks flash-attention on supported GPUs. Falls back to
    the standard math impl on CPU/MPS (gpu-only doctrine for the trainer
    blocks the CPU path in production, but the layer itself remains
    portable for unit tests).
    """

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        if config.n_embd % config.n_head != 0:
            raise ValueError(
                f"n_embd ({config.n_embd}) must be divisible by n_head ({config.n_head})"
            )
        self.n_head = config.n_head
        self.n_embd = config.n_embd
        self.head_dim = config.n_embd // config.n_head
        self.dropout = config.dropout

        self.c_attn = nn.Linear(config.n_embd, 3 * config.n_embd, bias=config.bias)
        self.c_proj = nn.Linear(config.n_embd, config.n_embd, bias=config.bias)
        self.resid_dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.size()
        q, k, v = self.c_attn(x).split(self.n_embd, dim=2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        y = F.scaled_dot_product_attention(
            q,
            k,
            v,
            attn_mask=None,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=True,
        )
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_dropout(self.c_proj(y))


class _MLP(nn.Module):
    """Two-layer feed-forward with 4x expansion and GELU."""

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.c_fc = nn.Linear(config.n_embd, 4 * config.n_embd, bias=config.bias)
        self.c_proj = nn.Linear(4 * config.n_embd, config.n_embd, bias=config.bias)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.c_proj(F.gelu(self.c_fc(x))))


class _Block(nn.Module):
    """One pre-LN Transformer block (attention + MLP, with residual streams)."""

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.ln_1 = nn.LayerNorm(config.n_embd, bias=config.bias)
        self.attn = _CausalSelfAttention(config)
        self.ln_2 = nn.LayerNorm(config.n_embd, bias=config.bias)
        self.mlp = _MLP(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


class TinyGPT(nn.Module):
    """Compact decoder-only Transformer for character / subword LM.

    Forward signature accepts an optional ``targets`` tensor; when present
    it returns ``(logits, loss)``, when absent it returns ``(logits, None)``.
    Loss is causal next-token cross-entropy via ``F.cross_entropy``.

    The class satisfies ``fi_core.training.protocols.GenerationModel``
    via the :meth:`generate` method.
    """

    def __init__(self, config: GPTConfig) -> None:
        super().__init__()
        self.config = config

        self.token_embedding = nn.Embedding(config.vocab_size, config.n_embd)
        self.position_embedding = nn.Embedding(config.block_size, config.n_embd)
        self.drop = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList([_Block(config) for _ in range(config.n_layer)])
        self.ln_f = nn.LayerNorm(config.n_embd, bias=config.bias)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)

        if config.tie_weights:
            self.lm_head.weight = self.token_embedding.weight

        self.apply(self._init_weights)
        for pn, p in self.named_parameters():
            if pn.endswith("c_proj.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * config.n_layer))

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def get_num_params(self, non_embedding: bool = True) -> int:
        n = sum(p.numel() for p in self.parameters())
        if non_embedding:
            n -= self.position_embedding.weight.numel()
            if self.config.tie_weights:
                # token_embedding and lm_head share weights; count once.
                n -= self.lm_head.weight.numel()
        return n

    def forward(
        self,
        idx: torch.Tensor,
        targets: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        T = idx.size(1)
        if T > self.config.block_size:
            raise ValueError(
                f"sequence length {T} exceeds block_size {self.config.block_size}"
            )
        pos = torch.arange(0, T, dtype=torch.long, device=idx.device).unsqueeze(0)
        x = self.drop(self.token_embedding(idx) + self.position_embedding(pos))
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        logits = self.lm_head(x)
        loss: torch.Tensor | None = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
                ignore_index=-1,
            )
        return logits, loss

    def configure_optimizers(
        self,
        weight_decay: float = 0.1,
        learning_rate: float = 6e-4,
        betas: tuple[float, float] = (0.9, 0.95),
    ) -> torch.optim.Optimizer:
        """Build AdamW with the karpathy-style decay/nodecay split.

        Parameters that are 2D or higher (weights of Linear / Embedding)
        get weight_decay; biases and LayerNorm parameters do not. This
        is the default the trainer uses if the caller does not supply
        their own optimizer_cls.
        """
        decay, nodecay = [], []
        for n, p in self.named_parameters():
            if not p.requires_grad:
                continue
            (decay if p.dim() >= 2 else nodecay).append(p)
        groups = [
            {"params": decay, "weight_decay": weight_decay},
            {"params": nodecay, "weight_decay": 0.0},
        ]
        return torch.optim.AdamW(groups, lr=learning_rate, betas=betas)

    @torch.no_grad()
    def generate(
        self,
        prompt_ids: list[int],
        *,
        max_new_tokens: int = 200,
        temperature: float = 0.8,
        top_k: int | None = 40,
        top_p: float | None = 0.95,
        repetition_penalty: float = 1.0,
    ) -> list[int]:
        """Autoregressive sampling with temp / top-k / top-p / rep penalty.

        Logic adapted from Robo-Poet's ``generate.py``. Returns the full
        sequence (prompt + new tokens). Crops context to ``block_size``
        on each step, which is correct for fixed-context Transformers.
        """
        device = next(self.parameters()).device
        idx = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        self.eval()
        for _ in range(max_new_tokens):
            idx_cond = idx if idx.size(1) <= self.config.block_size else idx[:, -self.config.block_size :]
            logits, _ = self(idx_cond)
            next_logits = logits[0, -1, :]
            if repetition_penalty != 1.0:
                for token_id in set(idx[0].tolist()):
                    if next_logits[token_id] < 0:
                        next_logits[token_id] *= repetition_penalty
                    else:
                        next_logits[token_id] /= repetition_penalty
            if temperature != 1.0:
                next_logits = next_logits / max(temperature, 1e-6)
            if top_k is not None and top_k > 0:
                kth_val = torch.topk(next_logits, top_k).values[-1]
                next_logits = torch.where(
                    next_logits < kth_val,
                    torch.full_like(next_logits, float("-inf")),
                    next_logits,
                )
            if top_p is not None and top_p < 1.0:
                sorted_logits, sorted_idx = torch.sort(next_logits, descending=True)
                cumulative = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                mask = cumulative > top_p
                mask[..., 1:] = mask[..., :-1].clone()
                mask[..., 0] = False
                sorted_logits[mask] = float("-inf")
                next_logits = torch.empty_like(next_logits).scatter_(
                    0, sorted_idx, sorted_logits
                )
            probs = F.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_token.unsqueeze(0)], dim=1)
        return idx[0].tolist()
