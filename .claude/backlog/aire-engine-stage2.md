# AIRE engine — etapa 2: el runner deja de hostear el SDK y las personas viven en casitas

Status: Proposed (2026-08-22, orden de Bernard: "etapa 2, NO hoy")

## Qué es

La migración real: `persona-runner` deja de ser un host propio del Claude Agent
SDK y cada turno se vuelve un
`POST /projects/{p}/sessions/{s}/messages` contra la puerta ENGINE de AIRE. El
precedente es og118 (free-intelligence), migrado 2026-08-21 — pero og118 era un
runner delgado; éste no.

El mapeo natural:

- **Canal de Discord = casita de AIRE.** `project_key` por canal (o por
  persona+canal — fork abierto), sesión = el hilo vivo. La memoria del turno
  vive en `claude_session_store` de AIRE en vez del pool en RAM del runner.
- **`shared/personas/<id>.md` = el CLAUDE.md vivo de la casita**, vía el
  `@base` de AIRE (aire-server #36: la casita nace THIN y dereferencia la
  persona compartida) + el persona tool del registry. El DNA deja de viajar
  como `system_prompt` en cada spawn.
- **Los MCP tools custom → tenants del registry de AIRE.** Hoy el runner mete
  tres servers por sesión: `persona_memory` (in-process, tools de facts sobre
  el Postgres de Khimeras), el persona server de fi-core, y Playwright stdio.

## Los huecos, con honestidad (lo que og118 NO tenía)

1. **Playwright no cabe en el droplet.** `@playwright/mcp --headless` =
   Node + Chromium por sesión; el droplet de AIRE es `s-1vcpu-512mb` con
   presupuesto duro de $20/mes ([[do-budget]] de aire-server). O el scraping
   social se pierde, o Playwright se queda como servicio aparte (¿en Azure,
   llamado remoto?), o el droplet crece — gasto que sólo Bernard autoriza.
2. **`persona_memory` es in-process CONTRA el Postgres de Khimeras.** Como
   tenant del registry de AIRE tendría que hablar con una base ajena al
   droplet: o se le da a AIRE la credencial de Khimeras (mezcla de dominios,
   huele mal), o los facts se consultan gateway-side antes del turno (más
   latencia, menos agencia), o el tool se vuelve un MCP HTTP hosteado por este
   repo y AIRE sólo lo cablea. Fork real de arquitectura.
3. **WebSearch es load-bearing y hoy tiene guard de boot**
   (`persona_runner/engine/options.py::verify_required_tools`): su ausencia
   falla SILENCIOSA. La casita de AIRE tendría que garantizar el mismo
   invariante (tools requeridos Y prohibidos — Bash/Write/Edit fuera, el
   contenedor del runner guarda `POSTGRES_URL` y el OAuth de la flota; en AIRE
   el cage es `can_use_tool` / deny rules, no `SandboxSettings`).
4. **Model routing por turno** (`routing/`): Haiku/Sonnet/Opus según preset +
   severidad + presupuesto Opus 24h. La puerta de AIRE fija el modelo por
   sesión/turno — hay que verificar que el parámetro viaja por el door y que
   cambiar de modelo no mata el cache de sesión (la razón de F3 para el pool
   vivo).
5. **`behavioral_guidance` por turno** (el guardián + overlay clínico) hoy
   viaja como campo propio de `/v1/turn`. Por la puerta AIRE tendría que ir
   prefijado en el mensaje o entrar al protocolo de AIRE — decidir sin diluir
   el overlay de usuarios vulnerables (es la parte que protege a Alex).
6. **El presupuesto envenena al cliente, no al query** (aire-server #23:
   `max_budget_usd` agota al pool y los turnos mueren en silencio) y **el pool
   semanal quemado devuelve un éxito mentiroso** (#31). El gateway de Discord
   necesita distinguir "AIRE cortó por presupuesto" de un turno normal para
   que el error hacia el usuario siga siendo neutral y en personaje.
7. **Latencia**: Discord → Azure (gateway) → droplet DO (AIRE) → Anthropic,
   contra el actual Azure → Anthropic. Medir antes de decidir; los turnos de
   voz/TTS son los sensibles.
8. **`/v1/judge`** (extracción de facts, one-shot barato) también tendría que
   mapear a algo en AIRE — ¿mode=complete en una casita utilitaria? — o
   quedarse en el runner, dejando el runner medio vivo (peor de los mundos:
   dos hosts del SDK).

## Camino canónico a reusar (Art. 6)

- og118 como plantilla del cliente del engine door (free-intelligence,
  migrado 2026-08-21).
- aire-server #36 (`@base` / casita THIN) para el persona.md como CLAUDE.md
  vivo.
- El registry de tools de AIRE (#29/#36) para los tenants MCP.

## La decisión que es de Bernard

Todo el item. Los forks nombrados: dónde vive Playwright, cómo entra
`persona_memory` sin mezclar credenciales, casita por canal vs por
persona+canal, y si la etapa 2 vale la latencia extra. La etapa 1
([[aire-gateway-stage1]]) ya da el espejo/observabilidad sin tocar nada de
esto — no hay prisa técnica; la etapa 2 es tesis de producto, no fix.
