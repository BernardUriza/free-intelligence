"""Reference ``Tokenizer`` implementations for ``fi_core.training``.

Submodules:
- ``fi_core.training.tokenizers.tiktoken_adapter`` — wraps OpenAI's
  ``tiktoken`` library. Use this for the ``tiny_gpt_30m`` preset
  (``cl100k_base`` = GPT-4 vocab, 100,277 tokens).
- ``fi_core.training.tokenizers.bpe``               — train + save +
  load a corpus-specific BPE via HuggingFace's ``tokenizers`` library.
  Use this for the ``tiny_gpt_5m`` preset (8K-16K vocab).

Both require ``pip install fi-core[training]``.
"""
