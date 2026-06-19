# LLM shadow router (gpt-4.1) — token bloat: agentic CLI is the wrong transport for routing

Status: In progress (fix IMPLEMENTED + measured; upstream-vs-local decision pending)
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

## Status / next step

NO bloqueante: A.2 quedó **probado y desplegado pero gated OFF**
(`LLM_SHADOW_ROUTER_ENABLED=false`, rev `discord-bot--0000163`), así que el bloat
solo cuesta cuando se re-encienda para acumular muestras de divergencia antes de
slice B. Hacer este fix ANTES de re-encender = acumulación económica. Relacionado:
el mismo `host_degrader` (gpt-4.1, también gated) heredaría la mejora.
