"""LLM client subpackage — runner-backed, no direct-Anthropic client.

The legacy direct-Anthropic Messages-API client (and its parsing/pricing/
retry satellites) was deleted once the agent runner became the sole LLM
backend. The conversational turn client ``AgentRunnerClient`` lives in
``khimeras_shared.runner.agent_client`` (persona-neutral transport).

What remains here:

- ``runner_judge_client``: ``RunnerJudgeClient`` → POST /v1/judge (one-shot
  text-only utility calls: facts, summaries, moltbook, proactive, reminders).
- a re-export of the shared ``LLMResponse`` contract so existing imports
  (``from personas.insult.core.llm import LLMResponse``) keep working.
"""

from khimeras_shared.llm.types import LLMResponse

__all__ = [
    "LLMResponse",
]
