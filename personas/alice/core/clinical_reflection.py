"""ALICE's Clinical Reflection Layer — the metacognitive "backend clínico".

Counterpart to the Presence Layer (`alice/core/llm.py`). Presence speaks TO the
person and holds them emotionally; this layer speaks ABOUT the person, ONLY to the
clinician. It NEVER reaches the patient. It reads the same conversation the
presence layer is having and produces a structured clinical observation
(lectura clínica, indicadores, recomendaciones, frase sugerida) for therapeutic
continuity. Frontend emocional / backend clínico — both are ALICE.

It is NOT a therapist replacement: it organizes the emotional/cognitive chaos into
something a clinician can act on. Routes through `fi_runner` over the SAME Azure
deployment as presence (no second account, same GPT-4.1). fi_runner is the single
boundary to fi-core — alice imports NO fi-core. Grounding comes two ways at once:

- `capabilities=["cognitive", "rag"]` — OPT-IN MCP tools (SOAP scoring, in-context
  recall) the LLM may reach for while reasoning.
- `guards=[triage_guard("psychiatry")]` — a GUARANTEED in-process safety net
  fi_runner runs every turn, so a suicide-plan mention escalates to CRITICAL
  regardless of the LLM's phrasing (never an optional tool it could skip).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import structlog
from fi_runner import CodexBackend, GravityScore, PermissionMode, Runner, ToolPolicy, triage_guard

from personas.alice.config import settings

log = structlog.get_logger()

_CLINICAL_PERSONA_PATH = Path(__file__).resolve().parent.parent / "persona_clinical.md"


@dataclass(frozen=True)
class ClinicalReflection:
    """A structured clinical observation FOR THE CLINICIAN (never the patient).

    ``triage`` is a deterministic, explainable risk score from fi_runner's PSYCHIATRY
    triage guard — a non-LLM safety net that runs alongside the narrative so a
    suicide-plan mention escalates to CRITICAL regardless of the LLM's phrasing.
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    triage: GravityScore | None = None


class ClinicalReflector:
    """Generates ALICE's clinical reflection over a conversation.

    Mirrors `AliceLLMClient`'s Azure wiring (same endpoint/deployment, key bridged
    into `AZURE_OPENAI_API_KEY` for the codex subprocess) but loads the clinical
    persona and returns a `ClinicalReflection`. Kept separate from the presence
    client so the two voices never bleed into each other.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        persona_path: str | None = None,
    ):
        self.api_key = api_key or settings.azure_openai_key
        self.endpoint = endpoint or settings.azure_openai_endpoint
        self.model = deployment or settings.azure_openai_gpt_deployment
        self._persona = Path(persona_path or _CLINICAL_PERSONA_PATH).read_text(encoding="utf-8")

        self._key_env = "AZURE_OPENAI_API_KEY"
        if self.api_key:
            os.environ.setdefault(self._key_env, self.api_key)

        self._backend = CodexBackend(
            default_model=self.model,
            azure_endpoint=self.endpoint,
            azure_api_key_env=self._key_env,
        )

    @staticmethod
    def _flatten(messages: list[dict[str, str]]) -> str:
        """Render the conversation as a `role: content` transcript for the prompt.

        Roles are kept verbatim so the clinical layer can tell the patient's
        utterances ("user") from the presence layer's replies ("assistant").
        """
        return "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)

    async def reflect(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
    ) -> ClinicalReflection:
        """Produce a clinical observation about the conversation, for the clinician.

        `messages` is the same OpenAI-shaped history the presence layer sees. The
        result is metacognitive — caller MUST route it to a clinician-only channel,
        never back to the patient.
        """
        chosen_model = model or self.model
        runner = Runner(
            backend=self._backend,
            persona=self._persona,
            # cognitive (score_soap, advance_consultation) + rag (lexical/semantic
            # recall over in-context text) as OPTIONAL MCP tools the LLM may call
            # while reasoning.
            capabilities=["cognitive", "rag"],
            # PSYCHIATRY triage as a GUARANTEED in-process guard fi_runner runs every
            # turn — a safety net, not an optional tool. alice imports no fi-core;
            # fi_runner owns the boundary (guard + capabilities).
            guards=[triage_guard("psychiatry")],
            tool_policy=ToolPolicy(permission_mode=PermissionMode.DEFAULT),
            model=chosen_model,
        )
        start = time.monotonic()
        result = await runner.run(self._flatten(messages))
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = result.usage or {}
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))

        # The triage guard ran in-process inside runner.run (guaranteed). Its
        # GravityScore is the deterministic safety net: a "plan suicida" escalates
        # to CRITICAL regardless of the LLM's phrasing.
        triage: GravityScore = result.guard_outcomes["triage"].metadata["score"]

        log.info(
            "alice_clinical_reflection",
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            backend="codex",
            triage_level=triage.level.value,
            triage_gravity=triage.final_gravity,
        )
        return ClinicalReflection(
            text=result.text,
            model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            triage=triage,
        )
