"""Custom Byte-Pair Encoding (BPE) tokenizer trained on a target corpus.

Use this for the ``tiny_gpt_5m`` preset when you want a vocab tightly
fit to your corpus (typical: 8K-16K merges; embedding table = vocab ×
hidden_dim stays under 4M params at hidden_dim=256).

Implementation defers to HuggingFace's ``tokenizers`` library — it
ships a fast Rust BPE trainer (``BpeTrainer``) that is orders of
magnitude faster than a pure-Python implementation. The wrapper here
exposes train / save / load + the standard ``Tokenizer`` Protocol
surface.

Special tokens shipped by default: ``<pad>``, ``<unk>``, ``<bos>``,
``<eos>``. Override via ``special_tokens=`` if your downstream needs
something different.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

try:
    from tokenizers import Tokenizer as HFTokenizer
    from tokenizers import decoders, models, pre_tokenizers, trainers
except ImportError as e:  # pragma: no cover - import-time error path
    raise ImportError(
        "fi_core.training.tokenizers.bpe requires the 'tokenizers' library. "
        "Install with: pip install 'fi-core[training]'"
    ) from e


DEFAULT_SPECIAL_TOKENS = ("<pad>", "<unk>", "<bos>", "<eos>")


class BPETokenizer:
    """Byte-Pair Encoding tokenizer with corpus-specific vocabulary.

    Lifecycle:

        tok = BPETokenizer.train(corpus_iter, vocab_size=8000)
        tok.save("tokenizer.json")
        ...
        tok = BPETokenizer.load("tokenizer.json")
        ids = tok.encode("hello world")
    """

    def __init__(self, hf_tokenizer: HFTokenizer) -> None:
        self._tok = hf_tokenizer

    @property
    def vocab_size(self) -> int:
        return self._tok.get_vocab_size()

    def encode(self, text: str) -> list[int]:
        return self._tok.encode(text).ids

    def decode(self, ids: list[int]) -> str:
        return self._tok.decode(ids)

    def save(self, path: str | Path) -> None:
        """Persist the tokenizer state to a JSON file (HuggingFace format)."""
        self._tok.save(str(path))

    @classmethod
    def load(cls, path: str | Path) -> BPETokenizer:
        """Load a tokenizer previously persisted by :meth:`save`."""
        return cls(HFTokenizer.from_file(str(path)))

    @classmethod
    def train(
        cls,
        corpus: Iterable[str],
        *,
        vocab_size: int = 8000,
        min_frequency: int = 2,
        special_tokens: tuple[str, ...] = DEFAULT_SPECIAL_TOKENS,
    ) -> BPETokenizer:
        """Train a fresh BPE tokenizer on the given corpus.

        ``corpus`` may be any iterable of strings (a list, a generator,
        a streaming source). The tokenizer pre-tokenizes on whitespace
        + punctuation (the GPT-2 style ``ByteLevel`` pre-tokenizer with
        whitespace pre-split), then runs BPE merges up to ``vocab_size``.

        ``min_frequency`` controls the minimum number of times a pair
        must co-occur to be considered for a merge; the default of 2
        is the HuggingFace standard.

        Special tokens are added to the vocabulary up-front so their
        ids are stable across training runs (assuming the same
        ``special_tokens`` tuple).
        """
        hf = HFTokenizer(models.BPE(unk_token="<unk>"))
        hf.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        hf.decoder = decoders.ByteLevel()
        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            special_tokens=list(special_tokens),
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
            show_progress=False,
        )
        hf.train_from_iterator(corpus, trainer=trainer)
        return cls(hf)
