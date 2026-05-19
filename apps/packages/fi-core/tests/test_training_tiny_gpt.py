"""Tests for `fi_core.training.models.tiny_gpt`.

Forward / backward / generate on CPU with tiny dimensions (verifies
correctness, not throughput). Preset factories return models with the
documented param counts.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from fi_core.training import GenerationModel
from fi_core.training.models.presets import tiny_gpt_5m, tiny_gpt_30m
from fi_core.training.models.tiny_gpt import GPTConfig, TinyGPT


@pytest.fixture
def tiny_config():
    """Minimal config for fast CPU smoke tests."""
    return GPTConfig(
        vocab_size=64,
        block_size=16,
        n_layer=2,
        n_head=2,
        n_embd=32,
        dropout=0.0,
        bias=True,
        tie_weights=True,
    )


class TestTinyGPTConstruction:
    def test_constructs_with_default_config(self):
        model = TinyGPT(GPTConfig())
        assert model.config.vocab_size == 8000
        assert model.config.n_layer == 6

    def test_n_embd_must_divide_n_head(self, tiny_config):
        bad = GPTConfig(n_embd=33, n_head=2)
        with pytest.raises(ValueError, match="must be divisible"):
            TinyGPT(bad)


class TestTinyGPTForward:
    def test_forward_returns_logits_only_without_targets(self, tiny_config):
        model = TinyGPT(tiny_config)
        x = torch.randint(0, tiny_config.vocab_size, (2, 8))
        logits, loss = model(x)
        assert logits.shape == (2, 8, tiny_config.vocab_size)
        assert loss is None

    def test_forward_returns_logits_and_loss_with_targets(self, tiny_config):
        model = TinyGPT(tiny_config)
        x = torch.randint(0, tiny_config.vocab_size, (2, 8))
        y = torch.randint(0, tiny_config.vocab_size, (2, 8))
        logits, loss = model(x, y)
        assert logits.shape == (2, 8, tiny_config.vocab_size)
        assert loss is not None
        assert loss.dim() == 0  # scalar

    def test_forward_rejects_sequence_too_long(self, tiny_config):
        model = TinyGPT(tiny_config)
        x = torch.randint(
            0, tiny_config.vocab_size, (1, tiny_config.block_size + 1)
        )
        with pytest.raises(ValueError, match="exceeds block_size"):
            model(x)


class TestTinyGPTBackward:
    def test_loss_backprops_through_all_params(self, tiny_config):
        model = TinyGPT(tiny_config)
        x = torch.randint(0, tiny_config.vocab_size, (2, 8))
        y = torch.randint(0, tiny_config.vocab_size, (2, 8))
        _, loss = model(x, y)
        loss.backward()
        # Every leaf with requires_grad must have a gradient now.
        for n, p in model.named_parameters():
            if p.requires_grad:
                assert p.grad is not None, f"{n} has no grad"


class TestTinyGPTGenerate:
    def test_generate_satisfies_protocol(self, tiny_config):
        model = TinyGPT(tiny_config)
        assert isinstance(model, GenerationModel)

    def test_generate_returns_prompt_plus_new_tokens(self, tiny_config):
        model = TinyGPT(tiny_config)
        prompt = [1, 2, 3]
        out = model.generate(prompt, max_new_tokens=5, top_k=4)
        assert out[:3] == prompt
        assert len(out) == len(prompt) + 5

    def test_generated_ids_are_in_vocab(self, tiny_config):
        model = TinyGPT(tiny_config)
        out = model.generate([0], max_new_tokens=20, top_k=8)
        for tid in out:
            assert 0 <= tid < tiny_config.vocab_size

    def test_generate_crops_when_prompt_exceeds_block_size(self, tiny_config):
        model = TinyGPT(tiny_config)
        prompt = list(range(tiny_config.block_size + 5))
        # Should not raise even though prompt > block_size
        out = model.generate(prompt[: tiny_config.vocab_size], max_new_tokens=2, top_k=4)
        assert len(out) > len(prompt[: tiny_config.vocab_size])


class TestPresets:
    def test_tiny_gpt_5m_param_count(self):
        model = tiny_gpt_5m()
        n = model.get_num_params(non_embedding=False)
        # Roughly 5M ±25% for the 8K vocab default
        assert 3_000_000 <= n <= 8_000_000, f"got {n:,} params"

    def test_tiny_gpt_30m_param_count(self):
        model = tiny_gpt_30m()
        n = model.get_num_params(non_embedding=False)
        # Roughly 30M ±25% for cl100k vocab
        assert 20_000_000 <= n <= 40_000_000, f"got {n:,} params"

    def test_both_presets_satisfy_generation_model(self):
        assert isinstance(tiny_gpt_5m(), GenerationModel)
        assert isinstance(tiny_gpt_30m(), GenerationModel)


class TestOptimizerConfiguration:
    def test_configure_optimizers_returns_adamw_with_2_groups(self, tiny_config):
        model = TinyGPT(tiny_config)
        opt = model.configure_optimizers()
        assert isinstance(opt, torch.optim.AdamW)
        # Two param groups: decay + nodecay
        assert len(opt.param_groups) == 2
        assert opt.param_groups[0]["weight_decay"] == 0.1
        assert opt.param_groups[1]["weight_decay"] == 0.0

    def test_decay_group_holds_2d_params_only(self, tiny_config):
        model = TinyGPT(tiny_config)
        opt = model.configure_optimizers()
        decay_params = opt.param_groups[0]["params"]
        nodecay_params = opt.param_groups[1]["params"]
        for p in decay_params:
            assert p.dim() >= 2
        for p in nodecay_params:
            assert p.dim() < 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
