# AIREBackend — el backend propio de Bernard, siempre-arriba y observable

Status: In progress — first cut shipped 2026-07-27 (the companion/complete turn)
Proposed: 2026-07-13 by Bernard (dictado en sesión; visión, palabras suyas)

## What it is

Un nuevo `AgentBackend` de fi-runner que compite contra `ClaudeCodeBackend` y
`CodexBackend` a nivel backend, respaldado por AIRE: un servidor propio de
Bernard, **siempre arriba escuchando**, con su **propia versión de la API de
Claude**, y cuyos **procesos se pueden ver en tiempo real** conectándose por
**SSH o por API**.

Lo que lo distingue de los backends existentes (ambos envuelven un CLI de
terceros en subprocess): AIRE es un servidor persistente — sin spawn por turno,
con estado y procesos inspeccionables en vivo. La observabilidad no es un stream
que el runner emite, sino una propiedad del servidor mismo.

## La doctrina de las dos capas de storage (Bernard, dictado 2026-07-13)

> "Vamos a tener dos tipos de storage: uno que sucede aquí — o sea, que haces tú
> como aplicación — y otro totalmente crudo, totalmente agnóstico, al que no le
> importas nada, pero que guarda sus propias transcripciones completas dentro de
> sí mismo. Y ese es AIRE."

- **Capa de aplicación:** curada, con identidad y producto — el ConversationStore
  de og118, IndexedDB, lo que la UI enseña. Vive en el consumidor.
- **Capa cruda (AIRE):** el motor guarda sus transcripciones íntegras DENTRO de
  sí mismo, agnóstico al consumidor — no sabe quién eres ni le importa. No es un
  espejo hacia una base externa: es propiedad del motor, como los JSONL locales
  de Claude Code pero en un servidor persistente y consultable.

Esto explica por qué el session_store (#358/#359) se desactivó: era Anthropic
espejeando SU capa cruda hacia nuestra base — un puente. AIRE elimina el puente
porque el motor propio ES el dueño de su capa cruda.

Contexto del mismo día: el session_store de og118 (PR #358/#359) se DESACTIVÓ
tras verificarse E2E — duplicaba la conversación y Bernard decidió que la
persistencia/continuidad vivirá en AIRE, no en el espejo del SDK de Anthropic.
La capacidad queda en fi-runner, env-gated e inerte (reactivable con un secret).
Existe ya un AIRE corriendo local (visto en `127.0.0.1:8099/projects/aire/...`)
— punto de partida a auditar antes de escribir nada nuevo.

## Canonical path to reuse (Art. 6)

- El contrato es `AgentBackend` (run_turn / run_turn_stream) — AIREBackend lo
  implementa; el Runner, los guards, el glass-box stream y los consumidores no
  cambian. Ésa es la prueba de que el sustrato es portable.
- [[codex-is-the-api-motor]]: CodexBackend es el motor API universal existente —
  AIREBackend no debe duplicar su modo ProviderConfig, debe superarlo donde
  compite (persistencia, observabilidad en vivo, siempre-arriba).
- La continuidad ya tiene dos precedentes en fi-runner (history replay y
  session_store con precedencia resume>replay, PR #358) — AIRE define la tercera
  y decide cuál subsume.

## The decision that's the owner's

- Dónde corre AIRE (el server local :8099 ya existente, un VPS, ACA) y qué
  modelo(s) sirve por debajo de su API estilo Claude.
- El alcance de "verse en tiempo real por SSH": ¿tmux/procesos reales, un TUI,
  o una API de introspección que el SSH sólo consume?
- Cuándo arranca la construcción — esto es captura de visión, NO greenlight.

## Status / next step

**First cut SHIPPED 2026-07-27.** `AIREBackend` vive en
`apps/packages/fi-runner/fi_runner/backends/aire.py` — tercer `AgentBackend`,
cliente HTTP de la puerta de AIRE (`gate.bernarduriza.com`, Bearer). `run_turn` +
`run_turn_stream` implementados, registrado en `backends/__init__.py` y el
top-level, extra `aire = ["httpx"]`, unit test `tests/test_aire_backend.py` (9
pass), y **verificado E2E contra la puerta viva** (turno `complete` real, memoria
en Postgres, $0.02/turno). Nada se borró: ClaudeCode/Codex conservan su
continuidad; AIRE es el tercer sustrato que subsume SU propio path.

El :8099 del texto original quedó **stale**: la puerta real hoy es
`https://gate.bernarduriza.com` (el commit `8d65b83` movió la puerta ahí; `aire.*`
es el front). Auditar el server actual = ya hecho al construir.

**Alcance del corte:** el turno companion/texto (`mode=complete`), justo donde se
desactivó el espejo `session_store` (#358/#359). Lo que la puerta NO recibía por
turno (tools/model/images) se rechazaba en voz alta — archivado como
**aire-server backlog #29** ("grow the door").

**SECOND CUT — forward clauses (2026-08-20).** La puerta creció (aire-server
commits `a40f389` + `6d8bd9a`: el body acepta `{message, mode, tools, model,
images, background}`) y los tres reject clauses se convirtieron en forwards:

- `model` → viaja en el body; el result event trae PROVENANCE real (leído de los
  AssistantMessage). E2E: pedir `"haiku"` respondió `claude-haiku-4-5-20251001`.
- `images` → `TurnImage` mapea 1:1 a `{media_type, data}`. E2E: un PNG azul
  respondió "Blue." ($0.0072/turno).
- `mcp_servers` → traducidos a NOMBRES del registry (sólo `spec.name` cruza el
  wire, `tools` + `mode=agent`); un nombre fuera del registry sigue rechazado
  FUERTE por el 422 de la puerta (`unknown tool 'not_in_registry'; available:
  ['memory']` → `BackendError`). Specs arbitrarios de MCP siguen siendo RCE por
  diseño y no cruzan.

Ese turno E2E (haiku + imagen + memory) es el **primer consumidor real** de los
tres gaps — el caso end-to-end del producto llave-en-mano (aire-server #34,
canónico en `discord-bot/.claude/backlog/servidor-llave-en-mano-personas-alex.md`).
El único input que sigue sin forwardearse es `tool_policy` (AIRE es dueño de la
config de tools server-side; se avisa con warning). 

**Corrección (2026-08-22): el "gap" de `llm_router_policy.py` NO EXISTE.** Lo
escribió una sesión anterior sin abrir el archivo. Los hechos:

1. Ese `Anthropic()` está **dentro del docstring** del módulo
   (`backend/policy/llm_router_policy.py:10`), como el EJEMPLO de lo que el
   archivo prohíbe — el módulo es el *scanner* que veta `anthropic` (`:98`) y
   `messages.create` (`:114`). Reruteárlo sería reescribir el ejemplo del pecado.
2. La única llamada cruda real a Anthropic en todo el repo está en otro lado:
   `backend/infrastructure/model_catalog/api/public/llm_models_admin.py:338`
   (`_test_anthropic_model`, POST a `api.anthropic.com/v1/messages`) — y es una
   sonda de superadmin para probar la config de un modelo, no un turno.
3. **`backend/` no se despliega ni se importa.** og118 y fenix se sirven de
   `og118-backend.yml` / `fenix-backend.yml`, ambos con path filter a
   `apps/**`; los dos Dockerfiles copian sólo `apps/`; `grep "from backend\."`
   sobre `apps/` no da un solo hit. Lo único que lo toca es `pr-gate.yml:39`
   con un `py_compile`. Su último cambio fue el 2026-05-22.

O sea que no hay nada que rerutear a AIRE ahí. Si algo queda es una tarjeta
aparte de higiene (*"borrar o poner en cuarentena el `backend/` legacy"*), no
trabajo de AIRE.
