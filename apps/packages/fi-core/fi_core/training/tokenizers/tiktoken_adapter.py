"""Adapter wrapping OpenAI's ``tiktoken`` as the ``Tokenizer`` Protocol.

``tiktoken`` ships GPT-4's ``cl100k_base`` BPE (100,277 tokens) plus a
handful of older encodings. We expose only ``cl100k_base`` by default
because (a) it's the modern baseline and (b) it pairs cleanly with the
``tiny_gpt_30m`` preset (which assumes that vocab size).

The wrapper is intentionally thin — tiktoken's own ``encode`` /
``decode`` are fast and feature-complete; we just constrain the public
surface to the four methods the ``Tokenizer`` Protocol requires
(``vocab_size``, ``encode``, ``decode``).
"""

from __future__ import annotations

try:
    import tiktoken
except ImportError as e:  # pragma: no cover - import-time error path
    raise ImportError(
        "fi_core.training.tokenizers.tiktoken_adapter requires tiktoken. "
        "Install with: pip install 'fi-core[training]'"
    ) from e


class TiktokenTokenizer:
    """``Tokenizer`` Protocol impl backed by ``tiktoken``.

    Default encoding is ``cl100k_base`` (the GPT-4 / GPT-4o tokenizer).
    Pass ``encoding_name="o200k_base"`` for the GPT-4o / GPT-4.1 vocab
    (~200K tokens) if your model can pay the embedding cost.
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoding = tiktoken.get_encoding(encoding_name)
        self._encoding_name = encoding_name

    @property
    def vocab_size(self) -> int:
        return self._encoding.n_vocab

    @property
    def encoding_name(self) -> str:
        return self._encoding_name

    def encode(self, text: str) -> list[int]:
        return self._encoding.encode(text)

    def decode(self, ids: list[int]) -> str:
        return self._encoding.decode(ids)
