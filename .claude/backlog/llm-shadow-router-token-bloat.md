# LLM shadow router (gpt-4.1) — token bloat: agentic CLI is the wrong transport for routing

Status: **Done (token bloat)** — fix LOCAL desplegado + medido en prod. La opción upstream (fi_runner chat backend) queda como mejora canónica SEPARADA, sin urgencia (ver "Decisión del dueño").
Proposed: 2026-06-18 by Claude (vía /exchange-coagent + /ultra-lord, autorizado por Bernard)
Measured: 2026-06-19 — direct transport DESPLEGADO (v4.21.82, commit 716e1cd) y medido en prod (rev 0167): 9509 → **115 input tokens (−98.8%)**, misma divergencia genuina. `DirectAzureLLMRouter` + flag `llm_shadow_transport=direct`.

## What it is

El `HostRouterLLM` (`demux_ai/host_llm.py`) — el cerebro gpt-4.1 del demux host,
usado por el `llm_shadow_router` (HOST 5/6 slice A.2) Y por el `host_degrader` —
corre a través de `fi_runner.CodexBackend`, que invoca el CLI agéntico
`codex exec --json`. En prod (2026-06-18) una clasificación de routing que
devuelve UNA palabra costó **9507 tokens de input / 4 de output**.

## Causa raíz (verificada en source, no asumida — Art. 2)

El `_ROUTING_INSTRUCTION` es ~106 tokens y el input del usuario ~22. El delta de
~9.4k NO es el prompt: `codex exec` envía su **harness agéntico interno**
(system prompt de coding agent + schemas de tools builtin) al modelo en CADA
llamada. `fi_runner/backends/codex.py` solo manda `instruction + user_message`
como prompt (línea ~157) y mapea `ToolPolicy` a `--sandbox` (qué puede HACER el
agente), NO a qué schema se envía. **No hay lever** (`builtin_allowed=[]`,
`-c` overrides, ni `--sandbox`) que recorte ese harness — es intrínseco a que
`codex exec` es un CLI de coding agéntico, no un endpoint de chat liviano.

Por eso el "fix de ToolPolicy" que parecía un one-liner es un **no-op**
confirmado; no se shippeó (hubiera sido fake-green).

## Canonical path to reuse (Art. 6)

El fix real: para una clasificación one-shot, NO usar el CLI agéntico. Usar una
completion directa de Azure OpenAI (`openai.AsyncAzureOpenAI`, mismo endpoint
`insult-openai` / deployment `gpt-4.1` / `AZURE_OPENAI_KEY` que ya consume el
host) → manda solo instruction + input (~130 tokens, ~95% menos). Opciones:

1. **Upstream (preferido, canary-driven):** un backend NO-agéntico de Azure chat
   en `fi_runner` (hoy solo expone `ClaudeCodeBackend` / `CodexBackend` /
   `SubprocessCLIBackend`, todos agénticos). Sería un nuevo "nivel configurable"
   del framework (ver `framework-canary-consumer.md`) que el host consume.
2. **Local (más rápido, menos canónico):** `HostRouterLLM` hace la llamada
   directa con `AsyncAzureOpenAI` para el path de routing/degradación (que nunca
   ejecuta tools), saltándose `CodexBackend`.

## The decision that's the owner's

¿Upstream (fi_runner backend nuevo) vs local (AsyncAzureOpenAI directo en
host_llm)? Es la misma tensión consumer-vs-framework de
`framework-canary-consumer.md`. La decisión es de Bernard cuando esto se priorice.

## Update 2026-06-19 (vía /exchange-coagent — relay con insult-gpt)

El fix LOCAL (opción 2) se shippeó y el shadow ya corre encendido y barato:

- **Estado vivo en prod** (rev `discord-bot--0000169`, Healthy): `LLM_SHADOW_ROUTER_ENABLED=true`,
  `LLM_SHADOW_TRANSPORT=direct`, `HOST_ROUTER_CUTOVER_ENABLED=true` (cutover
  DETERMINISTA flipeado ON — no-op estructural; el cutover gpt-4.1 sigue OFF).
- **A.2.2 — reporte agregado de divergencias (#general, KQL):** 16 calls en la ventana
  2026-06-18T22:52 → 06-19T13:56. Buckets: **4 missing_vultur, 0 false_vultur**,
  12 agree_insult. Token split por transporte: direct (rev167+) avg **130** / p95 155;
  agentic legacy (rev162-166) avg 9530 — el avg único miente, hay que partir por transporte.
  Señal prometedora pero **N chico** (solo 6 calls en direct) → keep measuring.
- **Autopsia de 4 `llm_shadow_router_failed` (todos rev161, 0 desde rev162):** 3 =
  `BackendError: codex CLI not on PATH` (arreglado por v4.21.79) + 1 = gap distinto:
  `ValueError: user_message must be non-empty` en un turn solo-adjunto.
- **Gap empty-input ARREGLADO:** v4.21.84 (commit `2077243`) — `_stage_bind_identity`
  skipea el LLM shadow cuando `raw_text.strip()` está vacío + loguea
  `llm_shadow_router_skipped reason=empty_input` (no-error). TDD red→green, suite shadow 34 passed.

## Next step

**A.2.3 — direct-only measurement window** (gated, decisión de Bernard cuándo cerrar):
rev post-empty-input-fix, #general only, direct only, target ≥50 calls o varios días,
`router_error/parse_error/timeout` = 0 recurrente. Solo tras ese reporte + OK explícito
de Bernard se propone el **cutover gpt-4.1** (hoy NO-GO).

Relacionado: el mismo `host_degrader` (gpt-4.1, también gated) heredaría el transporte
direct si se prioriza — hoy sin urgencia.
