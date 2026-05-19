"""Factory functions for the two architectural presets fi-core ships.

- ``tiny_gpt_5m``  — paired with a custom BPE tokenizer (8K vocab).
  Total ~5M params, embedding table = 8K × 256 = 2M. Trains in ~30 min
  on a single A100.
- ``tiny_gpt_30m`` — paired with ``tiktoken cl100k_base`` (100K vocab).
  Total ~30M params, embedding table = 100K × 256 = 25.6M. Trains in
  ~2-4h on a single A100.

Callers can also instantiate ``TinyGPT(GPTConfig(...))`` directly for
custom architectures; the presets are conveniences, not constraints.
"""

from __future__ import annotations

from fi_core.training.models.tiny_gpt import GPTConfig, TinyGPT


def tiny_gpt_5m(
    *,
    vocab_size: int = 8000,
    block_size: int = 256,
    dropout: float = 0.1,
) -> TinyGPT:
    """5M-param preset for use with a custom BPE tokenizer.

    Architecture: 6 layers × 8 heads × 256 hidden. Embedding table
    dominates the param count when vocab_size is in the 8K-16K range
    typical of corpus-specific BPE. Bump ``vocab_size`` if you train a
    larger BPE (each +8K vocab adds ~2M params via the embedding table).
    """
    config = GPTConfig(
        vocab_size=vocab_size,
        block_size=block_size,
        n_layer=6,
        n_head=8,
        n_embd=256,
        dropout=dropout,
        bias=True,
        tie_weights=True,
    )
    return TinyGPT(config)


def tiny_gpt_30m(
    *,
    vocab_size: int = 100_277,  # tiktoken cl100k_base
    block_size: int = 256,
    dropout: float = 0.1,
) -> TinyGPT:
    """30M-param preset for use with ``tiktoken cl100k_base``.

    Architecture: 6 layers × 8 heads × 256 hidden, paired with the GPT-4
    tokenizer (100,277 vocab). The model is still ``tiny`` by 2026
    standards (modern small models are 100M-1B params), but the vocab
    size pushes total params to ~30M, mostly in the embedding table.

    Tied weights: lm_head shares the token_embedding matrix, so the
    100K × 256 cost is paid once, not twice.
    """
    config = GPTConfig(
        vocab_size=vocab_size,
        block_size=block_size,
        n_layer=6,
        n_head=8,
        n_embd=256,
        dropout=dropout,
        bias=True,
        tie_weights=True,
    )
    return TinyGPT(config)
