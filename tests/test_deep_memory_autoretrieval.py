"""deep_memory auto-retrieval — runner-bound injection (v4.3.0).

The runner exposed deep_memory as an opt-in MCP tool the agent called on ~1.2%
of turns, so the longitudinal-history safety net was effectively dead. v4.3.0
PRE-FETCHES the most relevant raw-history chunks in discord-bot and injects
them into the turn payload so the agent always sees them.

Each behavior gets a positive case AND a resistance case (the near-miss that
must NOT trigger the path) per .claude/rules/robustness.md.
"""

from __future__ import annotations

import types

import httpx
import pytest

from insult.core.llm.agent_client import AgentRunnerClient

# --- AgentRunnerClient.chat: relevant_memory prepended to user_text --------


class _FakeResp:
    status_code = 200
    text = '{"text":"ok"}'

    def json(self):
        return {"text": "ok", "model": "agent-runner", "stop_reason": "end_turn"}


class _CapturingClient:
    last_payload: dict | None = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _CapturingClient.last_payload = json
        return _FakeResp()


@pytest.fixture
def _patch_httpx(monkeypatch):
    _CapturingClient.last_payload = None
    monkeypatch.setattr(httpx, "AsyncClient", _CapturingClient)


async def test_chat_prepends_relevant_memory_block(_patch_httpx):
    """Positive: relevant_memory is wrapped in a labeled block and placed
    BEFORE the user's actual text (context before message)."""
    client = AgentRunnerClient(runner_url="http://runner", runner_token="t")
    await client.chat(
        "ignored",
        [{"role": "user", "content": "quién es Larisa?"}],
        channel_id="C1",
        user_id="U1",
        relevant_memory="- Larisa es la terapeuta de Alex",
    )
    payload = _CapturingClient.last_payload
    assert payload is not None
    ut = payload["user_text"]
    assert ut == ("<relevant_memory>\n- Larisa es la terapeuta de Alex\n</relevant_memory>\n\nquién es Larisa?")
    assert ut.index("relevant_memory") < ut.index("quién es Larisa?")


async def test_chat_no_memory_leaves_user_text_untouched(_patch_httpx):
    """Resistance: no relevant_memory → user_text is exactly the message, no
    stray <relevant_memory> tag (byte-identical to pre-v4.3.0)."""
    client = AgentRunnerClient(runner_url="http://runner", runner_token="t")
    await client.chat(
        "ignored",
        [{"role": "user", "content": "quién es Larisa?"}],
        channel_id="C1",
        user_id="U1",
    )
    payload = _CapturingClient.last_payload
    assert payload is not None
    assert payload["user_text"] == "quién es Larisa?"
    assert "relevant_memory" not in payload["user_text"]


# --- _build_relevant_memory: the stages-side pre-fetch ----------------------


def _ctx(text: str, user_id: str = "U1"):
    return types.SimpleNamespace(text=text, user_id=user_id)


def _patch_query(monkeypatch, hits=None, raises=False):
    async def _fake(*, user_id, query, top_k):
        if raises:
            raise RuntimeError("pgvector down")
        return hits or []

    monkeypatch.setattr("insult.core.deep_memory.query_user_memory", _fake)


async def test_prefetch_returns_block_for_relevant_hits(monkeypatch):
    """Positive: hits above the similarity floor become a labeled, bulleted
    block."""
    from insult.cogs.chat.stages import _build_relevant_memory

    _patch_query(
        monkeypatch,
        hits=[
            {"chunk_text": "Larisa es la terapeuta de Alex", "similarity": 0.82},
            {"chunk_text": "Voces neurodivergentes es su libro", "similarity": 0.61},
        ],
    )
    out = await _build_relevant_memory(_ctx("cuéntame de Larisa Guerrero"))
    assert out is not None
    assert "- Larisa es la terapeuta de Alex" in out
    assert "- Voces neurodivergentes es su libro" in out
    assert "contexto recuperado" in out  # framed as context, not instruction


async def test_prefetch_skips_trivial_message(monkeypatch):
    """Resistance: a too-short message is skipped WITHOUT even hitting the
    embedder/query (no wasted Azure call on 'okok')."""
    from insult.cogs.chat.stages import _build_relevant_memory

    called = {"n": 0}

    async def _fake(*, user_id, query, top_k):
        called["n"] += 1
        return [{"chunk_text": "x", "similarity": 0.9}]

    monkeypatch.setattr("insult.core.deep_memory.query_user_memory", _fake)
    out = await _build_relevant_memory(_ctx("okok"))
    assert out is None
    assert called["n"] == 0, "trivial message must not trigger a query/embed"


async def test_prefetch_drops_below_threshold_hits(monkeypatch):
    """Resistance: weak (low-similarity) hits are noise — dropped, returns
    None rather than injecting irrelevant history every turn."""
    from insult.cogs.chat.stages import _build_relevant_memory

    _patch_query(monkeypatch, hits=[{"chunk_text": "unrelated", "similarity": 0.10}])
    out = await _build_relevant_memory(_ctx("una pregunta cualquiera larga"))
    assert out is None


async def test_prefetch_none_on_retrieval_failure(monkeypatch):
    """Resistance: a retrieval error never breaks the turn — returns None."""
    from insult.cogs.chat.stages import _build_relevant_memory

    _patch_query(monkeypatch, raises=True)
    out = await _build_relevant_memory(_ctx("mensaje suficientemente largo aquí"))
    assert out is None
