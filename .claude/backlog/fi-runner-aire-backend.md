# AIREBackend — el backend propio de Bernard, siempre-arriba y observable

Status: Proposed
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

No construido. Siguiente paso cuando Bernard dé el go: auditar el AIRE local
existente (:8099) y mapear su superficie actual contra el contrato AgentBackend.
