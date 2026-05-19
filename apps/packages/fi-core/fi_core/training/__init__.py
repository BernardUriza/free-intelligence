"""Training utilities for fi-core.

Sub-modules:
- ``fi_core.training.protocols``        — DatasetReader / Tokenizer / Trainer / GenerationModel Protocols
- ``fi_core.training.datasets``         — DatasetReader impls (HDF5, pgvector)
- ``fi_core.training.tokenizers``       — Tokenizer impls (tiktoken adapter, BPE)
- ``fi_core.training.models``           — TinyGPT class + presets (tiny_gpt_5m, tiny_gpt_30m)
- ``fi_core.training.trainers``         — PyTorchTrainer (config-driven optimizer + checkpoints)

V2 narrative: training is a utility surface, not a closed loop. The
patterns shipped by ``fi_core.persona`` are NOT trained on any corpus
a consumer feeds into this module — they are human-distilled from
production failure modes. This module ships the pipes (read chunks
written by ``fi_core.stores``, tokenize, embed, run a small GPT loop);
the closed loop, if a consumer wants one, is their assembly.

Optional dependencies are pulled by ``pip install fi-core[training]``
(``torch``, ``tiktoken``, ``tokenizers``). The base ``fi-core`` install
does NOT pull them — importing any sub-module without the extras raises
``ImportError``.
"""

from fi_core.training.protocols import (
    DatasetReader,
    GenerationModel,
    Tokenizer,
    Trainer,
)

__all__ = [
    "DatasetReader",
    "GenerationModel",
    "Tokenizer",
    "Trainer",
]
