"""Tests for `fi_core.training.tokenizers`.

Covers ``TiktokenTokenizer`` (wraps OpenAI tiktoken) and ``BPETokenizer``
(wraps HuggingFace tokenizers). Encode/decode round-trip, vocab_size
sanity, Protocol satisfaction.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from fi_core.training import Tokenizer


class TestTiktokenTokenizer:
    def setup_method(self):
        from fi_core.training.tokenizers.tiktoken_adapter import (
            TiktokenTokenizer,
        )

        self.tok = TiktokenTokenizer()  # cl100k_base default

    def test_satisfies_protocol(self):
        assert isinstance(self.tok, Tokenizer)

    def test_default_encoding_is_cl100k(self):
        assert self.tok.encoding_name == "cl100k_base"

    def test_vocab_size_is_cl100k_count(self):
        # cl100k_base has 100,277 tokens (incl. special)
        assert self.tok.vocab_size == 100_277

    def test_encode_returns_list_of_ints(self):
        ids = self.tok.encode("hello world")
        assert isinstance(ids, list)
        assert all(isinstance(i, int) for i in ids)
        assert all(0 <= i < self.tok.vocab_size for i in ids)

    def test_round_trip(self):
        for text in ["hello", "the quick brown fox", "¿qué hubo?", ""]:
            ids = self.tok.encode(text)
            assert self.tok.decode(ids) == text

    def test_o200k_encoding_works(self):
        from fi_core.training.tokenizers.tiktoken_adapter import (
            TiktokenTokenizer,
        )

        tok = TiktokenTokenizer(encoding_name="o200k_base")
        # o200k_base has ~200K tokens
        assert tok.vocab_size > 150_000
        assert tok.decode(tok.encode("hi")) == "hi"


class TestBPETokenizer:
    def setup_method(self):
        from fi_core.training.tokenizers.bpe import BPETokenizer

        # Train on a small synthetic corpus
        corpus = [
            "the quick brown fox jumps over the lazy dog",
            "she sells seashells by the seashore",
            "hello world goodbye world",
        ] * 50  # repeat for enough freq counts
        self.tok = BPETokenizer.train(corpus, vocab_size=200, min_frequency=1)

    def test_satisfies_protocol(self):
        assert isinstance(self.tok, Tokenizer)

    def test_vocab_size_is_reasonable(self):
        # ByteLevel adds 256-byte alphabet + 4 special tokens + learned merges.
        # With vocab_size=200 target and tiny corpus the trainer caps near
        # the alphabet floor (~260). Just verify it's > 0 and bounded.
        assert 0 < self.tok.vocab_size < 1000

    def test_encode_returns_list_of_ints(self):
        ids = self.tok.encode("hello world")
        assert isinstance(ids, list)
        assert all(isinstance(i, int) for i in ids)
        assert all(0 <= i < self.tok.vocab_size for i in ids)

    def test_round_trip_known_corpus_word(self):
        # Words seen many times in training should round-trip cleanly
        for text in ["the quick brown fox", "hello world"]:
            ids = self.tok.encode(text)
            assert self.tok.decode(ids) == text

    def test_save_and_load(self):
        from fi_core.training.tokenizers.bpe import BPETokenizer

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tok.json"
            self.tok.save(path)
            assert path.exists()
            loaded = BPETokenizer.load(path)
            assert loaded.vocab_size == self.tok.vocab_size
            assert loaded.encode("hello world") == self.tok.encode("hello world")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
