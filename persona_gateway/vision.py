"""Image transcription — the only trace an image leaves once its turn is over.

An image reaches the model as base64 inside ONE live turn and then evaporates:
the stored row keeps the user's text and nothing else. Ask about that photo two
days later and the persona is blind to it, even though it "saw" it — the memory
is longitudinal for words and amnesic for everything visual.

The sink for this survived the purge fully wired and tested
(`MemoryStore.append_to_message` → `append_content_by_discord_id`, keyed on the
Discord message id so the append lands whichever writer won the deduped insert),
and the runner's `JudgeRequest` grew an `attachments` field in v4.21.117
explicitly for "image transcription for longitudinal memory". Only the PRODUCER
died with `personas/insult` — this module. Same shape as `other_people`: the
plumbing looked load-bearing while nothing called it.

Fire-and-forget after delivery, mirroring `FactExtractor`: the transcription's
LLM round-trip must never sit between the user and their reply.
"""

from __future__ import annotations

import asyncio

import structlog

from persona_core.memory import MemoryStore
from persona_core.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt
from persona_core.runner.judge_client import RunnerJudgeClient

log = structlog.get_logger()

_CACHE: PromptCache = {}

MAX_TRANSCRIPT_CHARS = 600


class ImageTranscriber:
    """Background vision backstop. No-op without a judge client or images."""

    def __init__(self, memory: MemoryStore, bg_tasks: set[asyncio.Task]) -> None:
        self.memory = memory
        self._bg_tasks = bg_tasks

    def spawn(
        self,
        judge_client: RunnerJudgeClient | None,
        discord_message_id: str,
        attachment_blocks: list[dict],
    ) -> None:
        """Fire-and-forget, tracked so the event loop can't GC it mid-flight."""
        images = [b for b in attachment_blocks if isinstance(b, dict) and b.get("type") == "image"]
        if judge_client is None or not discord_message_id or not images:
            return
        task = asyncio.create_task(self._transcribe_and_append(judge_client, discord_message_id, images))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _transcribe_and_append(
        self,
        judge: RunnerJudgeClient,
        discord_message_id: str,
        images: list[dict],
    ) -> None:
        """Describe each image and append it to the stored row. Best-effort.

        A transcription fault costs the trace, never the turn — the reply was
        already delivered before this ran.
        """
        try:
            system_prompt = load_prompt(SHARED_PROMPTS_DIR, "image_transcript", _CACHE)
            for index, image in enumerate(images):
                resp = await judge.utility_call(
                    system_prompt,
                    [{"role": "user", "content": [{"type": "text", "text": "Describe esta imagen."}, image]}],
                )
                description = (resp.text or "").strip().replace("\n", " ")
                if not description:
                    log.warning(
                        "image_transcript_empty",
                        discord_message_id=discord_message_id,
                        image_index=index,
                    )
                    continue
                description = description[:MAX_TRANSCRIPT_CHARS]
                appended = await self.memory.append_to_message(discord_message_id, f"[Imagen adjunta: {description}]")
                log.info(
                    "image_transcript_stored",
                    discord_message_id=discord_message_id,
                    image_index=index,
                    chars=len(description),
                    row_updated=appended,
                )
        except Exception:
            log.exception("image_transcript_failed", discord_message_id=discord_message_id)
