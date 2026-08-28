"""Wire contracts of the runner — every request/response shape in one place.

Each `Field` here carries the incident that shaped it. They are the runner's
public API: `khimeras_shared.runner.agent_client` (the gateway's turn client)
and the judge clients speak exactly these shapes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TurnRequest(BaseModel):
    channel_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    # v3.9.58: raised from 8000 -> 256000 chars. Bernard 2026-05-19 07:06
    # pasted `message.txt` (21KB) and the runner rejected with 422, falling
    # over to ALICE who never saw the attachment content. The Claude Agent
    # SDK handles long inputs fine; the previous cap was an arbitrary Pydantic
    # constraint with no upstream justification.
    user_text: str = Field(..., min_length=1, max_length=256000)
    # Kept in the schema for caller backward-compat but ignored — the
    # per-channel client owns continuity now.
    session_uuid: str | None = None
    # v3.9.43 (REWRITE-B1): Anthropic-shape content blocks for non-text
    # attachments (image, document). Caller extracts them from the
    # `messages[-1].content` list and forwards them raw. When present the agent
    # receives a multimodal user message instead of text-only. Bug origin:
    # 2026-05-18 Alex sent text+2 images, runner only saw text → bot ignored
    # the images entirely.
    attachments: list[dict] | None = None
    # v3.9.94: per-turn behavioral guidance (preset + vulnerability overlay)
    # computed by the caller's classifier. The runner-extracted architecture had
    # dropped it (agent_client discards `system_prompt`), so the persona answered
    # with its raw base tone regardless of what the classifier decided. Symptom
    # 2026-05-22: classifier picked relational_probe + vulnerability overlay
    # (score 11) for a user hours after suicidal ideation, but Insult stayed
    # abrasive. Injected into the USER message (not the system prompt) so the
    # persona stays cache-stable while the guidance varies per turn.
    behavioral_guidance: str | None = Field(default=None, max_length=16000)
    # Khimeras multi-persona: which sibling persona answers this turn. None ⇒
    # the default persona, fully backward-compatible. A valid id loads
    # PERSONAS_DIR/<id>.md; an unknown/invalid id falls back + logs.
    persona_id: str | None = Field(default=None, max_length=32)
    # OG118-CONTINUITY: prior turns of THIS conversation, replayed by a
    # local-first caller (og118) whose transcript lives client-side. Folded into
    # the user message ONLY when this turn opens a FRESH pool slot — a live SDK
    # session already holds the thread internally, so re-inlining would duplicate
    # context every turn. Untrusted conversational context, never authorization;
    # role-allowlisted + capped by `fold_history`. Discord callers never send it.
    history: list[dict] | None = None


class TurnResponse(BaseModel):
    text: str
    session_uuid: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = ""
    tool_calls: list[dict] = Field(default_factory=list)


class JudgeRequest(BaseModel):
    """One-shot utility request — an SDK call with an arbitrary system prompt,
    no session pool, no persona. Used by fact extraction, the consolidator job,
    image transcription and any future utility caller, so OAuth Max stays
    centralized in the runner. Memory: [[mcp-shape-b-canonical]].
    """

    system_prompt: str = Field(..., min_length=1, max_length=256000)
    user_text: str = Field(..., min_length=1, max_length=256000)
    max_tokens: int = Field(default=4096, ge=1, le=64000)
    model: str | None = Field(
        default=None,
        description="Override AGENT_RUNNER_JUDGE_MODEL. Defaults to Haiku.",
    )
    # v4.21.117: same attachment contract as TurnRequest. Lets utility callers
    # use the judge's vision (image transcription for longitudinal memory) — the
    # judge was text-only before, which is why image content never survived past
    # its live turn.
    attachments: list[dict] | None = None
    # AIRE stage 2: which persona's utility casita (`{persona_id}-judge`) hosts
    # this call on the AIRE route. None ⇒ the default persona's casita —
    # existing callers unchanged. Ignored entirely on the local backend.
    persona_id: str | None = Field(default=None, max_length=32)


class JudgeResponse(BaseModel):
    text: str
    model: str = ""
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class RuleRequest(BaseModel):
    """A house rule Bernard appends to the agents' CLAUDE.md, live."""

    rule: str
