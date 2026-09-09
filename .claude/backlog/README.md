# Backlog — discord-bot

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook. Items Done se retiran del folder (limpiezas
2026-07-05 y 2026-08-06); su historia vive en git.

**Última auditoría contra el repo y prod: 2026-09-07** (`git log --since=2026-08-06`,
`grep -rn`, `az containerapp list|show|job list`, `az acr list`, `gh issue list`,
`curl -I` al blob del dashboard). La anterior fue el 2026-08-06. Cada status de
abajo se re-verificó hoy y cada item lleva su bloque *Re-chequeo 2026-09-07* con
los comandos; los que no se pudieron verificar lo dicen. Lo que NO se auditó hoy:
`khimeras_shared/corpus/` (otro agente lo estaba podando en el mismo momento) y
Postgres (sin acceso desde esta sesión).

| Item | Status | Hook |
|---|---|---|
| [AIRE gateway etapa 1: relay Anthropic](aire-gateway-stage1.md) | **Superseded por la etapa 2** (2026-08-28) — el relay ya no existe; queda limpiar `docs/runbook_dr.md` paso 4 | el runner ya no spawnea un CLI que herede `ANTHROPIC_BASE_URL`: la única ruta Anthropic es la puerta engine (`AIRE_GATE_URL`, único env AIRE vivo en `persona-runner` al 2026-09-07). `ANTHROPIC_BASE_URL`/`ANTHROPIC_CUSTOM_HEADERS` salieron de la Container App en la revisión 195 (v4.35.2). El "espejo pendiente" nunca se verificó y hoy es moot. `docs/runbook_dr.md:60-62` sigue listando los dos env vars muertos — fuera del alcance de esta auditoría, pendiente |
| [Servidor llave en mano con personas de Alex](servidor-llave-en-mano-personas-alex.md) | 🔒 **Congelado hasta 2027** (candado de Bernard 2026-08-17, `84cfe15`) — este índice decía "Proposed" | nada se ejecuta ante un tercero antes de 2027 ni se vuelve a proponer; permitido documentar/investigar/construir activos internos. Sin commits al item desde el candado (`git log --since=2026-08-18 -- <item>` → vacío) |
| [Persona de acompañamiento psicológico](persona-acompanamiento-issues-alex.md) | **Fase 1 SHIPPED** (2026-08-25, v4.32.75–80) — fase 2 sin abrir | Valentis existe: #41 ADN (`15e1fcc`), #42 guidance grave (`5545d1d`), #43 registro (`fe221f3`), #44 piso de seguridad para toda la casa (`9d39b81`); los 4 issues CERRADOS 2026-08-25; `VALENTIS_DISCORD_TOKEN` en el env vivo de `persona-gateway`. Derivados que Alex siguió: #52 y #53 (crisis → fi-core, cerrados 09-01/09-04). Fase 2 (facetas por tema, presets propios, overlay propio, corpus) no tiene issue |
| [Cadenas cortadas post-purga + código muerto](cadenas-cortadas-post-purga.md) | Triaged (2026-07-15) · **#5 RESUELTO** 2026-08-06 · re-verificado 2026-09-07 | el job `fact-consolidation` y `khimeras_shared/consolidation/` MURIERON el 2026-08-06 (`de941f5`; hoy `az containerapp job list` → vacío, `git ls-files` → 0) — este índice seguía diciendo "cron 31-feb". De los 3 cero-callers queda **uno**: `RouterBudget` revivió el mismo 08-06 como cap del router vivo (`72d5175`); sólo `class LLMShadowRouter` sigue construida únicamente en tests. #4 (corpus) no auditado hoy |
| [Dashboard: data plane fósil](dashboard-data-plane-fossil.md) | **In progress** — fake-green eliminado 2026-08-06 (`34bf41c`, v2.4.0); fork de Bernard sigue abierto — este índice decía "Proposed" | el pill ya se deriva del `timestamp` del productor; el blob sigue con `Last-Modified: 25 Jun 2026` (curl 2026-09-07). La superficie NO está congelada: desde 08-06 ganó el portal de nómina de Alex (`dbccf0d` + 5 commits `docs(nomina)`). Fork: recablear el emisor en `persona_gateway` o congelar |
| [La proactividad murió en la purga](proactividad-muerta-restaurar-en-el-host.md) | Accepted · **slice 1 HECHO** el mismo 2026-08-06 (`aae8e2c`, v4.32.33); slices 2–5 sin arrancar | `khimeras_shared/proactive.py` + `tests/core/test_proactive.py` viven; cero callers fuera del test, ningún `ProactiveWorker` en `demux_ai/`, `world_scans` sigue sin escritores. Sin commits al tema desde 08-06 |
| [Graceful turn drain en deploys](graceful-turn-drain-on-deploy.md) | **In progress** — paso 1 AMPLIADO 2026-09-09 (v4.38.22); pasos 2 y 3 **re-escritos**: el item estaba mal | dos correcciones con recibo (2026-09-09): **el runner YA drena** — uvicorn instala el handler y espera indefinidamente (`timeout_graceful_shutdown=None`), lo que mata el turno es el SIGKILL al vencer el grace period, así que el paso 2 no era construir un drain sino darle tiempo al que hay; y **subir el grace period en el gateway sin gate de recepción da respuestas DOBLES** (dos réplicas sosteniendo el mismo token de Discord), así que el gate es prerequisito, no el "complemento opcional" que decía el item. El paso 1 se amplió donde más dolía: el presupuesto de reconexión pasó de 0.75s a un reloj de 45s, porque un turno nuevo durante el swap moría contra el socket cerrado |
| [Builder de turno unificado](turn-builder-unificado.md) | **In progress** — slice 2 (arnés de paridad) HECHO; slice 1 (`TurnSpec`/`TurnBuilder`) no | `tests/arch/test_mention_invite_parity.py` existe desde `d4fefb9` (2026-08-06, v4.32.37; AST + comportamiento, asimetrías reales como `xfail(strict)`), reforzado en `5319ec2` (#40). `grep TurnSpec\|TurnBuilder` → sólo un docstring en `aire_route.py`; `_handle` y `respond_to_invite` siguen siendo dos entry points |
| [Frugívoro persona](frugivoro-persona.md) | In progress — corpus RAG vivo en repo; falta el benchmark; re-verificado 2026-09-07 | 3 de 4 pasos siguen verificados en repo (`corpus_namespace="__corpus_vegan__"` en `registry.py:139`, `scripts/ingest_corpus.py`, `data/corpus/frugivoro/` + MANIFEST); el 4º (ingesta en Postgres) **sigue sin verificar** — sin acceso a Postgres hoy. Único movimiento: `4ed8825` (#39, 2026-08-11) — deducción de origen de la comida en el ADN. Benchmark §1–§3 sin arrancar |
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | In progress — **ACR: `serverbotacr` BORRADO, todo en GHCR** (2026-08-12); RG + repo pendientes — este índice decía "3 apps en serverbotacr" | `az acr list` → sólo `insultacr`; `persona-gateway`/`persona-runner`/`khimeras-host` y `susurro-gateway` pullean de `ghcr.io/bernarduriza/…`. `insultacr` sobrevive por dos inquilinos: la app retirada `discord-bot` (min 0, `insult-bot:d6fa36c`) y `rancho-studio`. El job `fact-consolidation` ya no bloquea (borrado 08-06). RG→`server-rg` sigue agendado |
| [Renombrar Frugi → Fruggy](rename-frugi-to-fruggy.md) | **Slice 1 DONE** (alias `fruggy`, `40a4fea` v4.32.45, 2026-08-10; #36 cerrado 2026-08-14) — resto en decisión de Bernard | `registry.py:135` → `aliases=["frugivoro", "frugi", "frugívoro", "fruggy"]`. Siguen fuera: `display_name="Frugívoro"`, el username del bot en Discord, el `persona_id`/DNA/`token_env`, y 146 hits de "frugi" (`grep -rni frugi --include=*.py --include=*.md`) |
| [CVE exploitability review](cve-exploitability-review.md) | Proposed — **1 de 9 acciones ejecutada** (el ignore de `CVE-2026-3219` cayó hoy, `fde7584` v4.38.7); cero bumps | `environment.yml` sin pisos nuevos (sólo `pydantic-settings>=2.1.0` y el cap `starlette<1.0`; los únicos movimientos desde 08-06 son fi-core/fi-runner y la salida de `claude-agent-sdk`). Colateral vigente: `persona-runner` `ingress.external: true` (az, 2026-09-07) |
| [ML-stack CVE tax](ml-stack-cve-audit.md) | Proposed · re-verificado 2026-09-07 sin cambios | `environment.yml:146` sigue `sentence-transformers>=3.0.0`; consumidores vivos siguen siendo 2 (`memory/connection.py:147`, `memory/minilm_embedder.py:49` → `khimeras_shared/vectors.py`). El bloque ML de `--ignore-vuln` en `ci.yml` intacto |

## Retirados (Done verificado, 2026-09-07 — historia en git)

- **runner-base: Node + Claude CLI + credencial OAuth muertos** — Done 2026-08-28,
  v4.35.2 (`c972579`), cerrado el mismo día que se propuso (`373eeb1` → `a81379e`).
  `runner-base.Dockerfile` borrado (`ls` 2026-09-07 → no existe; el runner monta
  `khimeras-base`), `CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_BASE_URL`/
  `ANTHROPIC_CUSTOM_HEADERS`/`TURN_BACKEND` fuera de la Container App (revisión
  195; hoy el env de `persona-runner` sólo lleva `AIRE_GATE_URL`+`AIRE_AUTH_TOKEN`
  como vars de LLM), rotador + regla del playbook actualizados; recibo vivo de
  Insult en #general con ᵛ⁴·³⁵·².
- **AIRE engine etapa 2: personas en casitas** — TERMINADA 2026-08-28, v4.35.0
  (`fc0944a`), hallazgos 1 y 2 cerrados con recibo vivo (`4cf04dd`, `e8e1e07`).
  La puerta engine es la única ruta: casita `{persona}-{canal}`, topic durable
  que rueda tras 1 h, judge en casita, las 10 tools de memoria por
  `/mcp/{casita}`. Verificado 2026-09-07: `grep -rn "claude_agent_sdk\|TURN_BACKEND"
  --include=*.py --include=*.yml .` → 4 hits, todos docstrings/comentarios de
  procedencia (`tooldef.py`, `test_tooldef.py`, `environment.yml`); las tres apps
  corren `798ba77` desde GHCR; `persona-runner` con `AIRE_GATE_URL=https://gate.bernarduriza.com`.
  Matiz del host: `2150ca0` (v4.36.0, 2026-08-29) migró la clase `HostRouterLLM`
  a `AIREBackend`, pero el host VIVO sigue arrancando `DirectAzureLLMRouter`
  (Azure OpenAI directo, `demux_ai/__main__.py:25`; el env de `khimeras-host` no
  lleva `AIRE_GATE_URL`) — `HostRouterLLM` sólo la construye `LLMShadowRouter`,
  que sólo construyen los tests.

## Retirados (Done verificado, 2026-08-06 — historia en git)

- **LLM shadow router / token bloat** — Done por partida doble. El token bloat se
  arregló en v4.21.82 (`716e1cd`, 9509→115 tokens con `DirectAzureLLMRouter`) y
  **el cutover a gpt-4.1 lleva LIVE desde el 2026-07-08** (`88481c9` v4.22.19:
  *"el cutover gpt-4.1 está LIVE"*), que además borró el shadow determinista
  (`demux_ai/shadow_router.py`) y su harness (`scripts/shadow_divergence_report.py`).
  Hoy el router ES el host: `demux_ai/__main__.py:25` → `run_host(DirectAzureLLMRouter())`
  en el Container App `khimeras-host` (Running, min=1). **El "26% de divergencia,
  falsos positivos peli/Netflix→vultur" que este índice citaba como NO-GO nunca
  existió: `diverged` era `target != "insult"`, o sea el NOMBRE del campo contando
  cada ruteo correcto a un hermano como divergencia.** La ventana A.2.3 quedó
  superada por la instrumentación de hoy: `host_dispatched` con
  `has_context`/`prev_target`/`switched` (v4.32.28-30) + `scripts/router_health.py`
  + `scripts/router_eval.py --no-context`, doctrinado en
  `.claude/rules/router-observability.md`.
- **Cross-turn durable research jobs** — Done v4.22.34 (`82ac0ff`, 2026-07-10),
  no "Proposed" como decía este índice: tabla `research_jobs`
  (`postgres_schema.sql:178`), marcador `[RESEARCH:]` → `save_research_job`
  (`persona_gateway/markers.py:135`) y `ResearchWorker.drain` que corre el job en
  el runner y postea el reporte de vuelta (`persona_gateway/workers/research.py`),
  con recuperación de jobs colgados.
- **ADN nivelado: bio + estilo + gustos propios** — Done 2026-07-16. Verificado:
  alice/vultur/frugivoro/unborn_being tienen `## Biografía` + estilo + "lo que sé
  sobre mí"; `persona_gateway/workers/reflection.py:78` escribe a `agent_facts`
  con `provenance="self_declared"`.
- **Dedup `persona.md` vs `insult.md`** — Done 2026-07-16. Verificado: `persona.md`
  raíz no existe y el tombstone `test_root_persona_md_stays_dead`
  (`tests/shared/test_registry_insult.py:32`) lo mantiene muerto.
- **Renombrar `vultur-gateway` → `persona-gateway`** — Done 2026-07-05 (v4.21.119
  `17fc427`). Verificado: `az containerapp list -g insult-rg` muestra
  `persona-gateway` (Running, min=1) y ningún `vultur-gateway`.

## Retirados (Done, 2026-07-05 — historia en git)

- addressed_to_sibling over-suppression — Done v4.21.113 `783b00d`; cross-talk @frugi E2E-verificado (`7a1f6d2`).
- runner no dispara invoke_alice → marcador `[INVITE:]` — Done v4.21.114 `3f871a5`, E2E verificado.
- mover runner a `persona_runner/` top-level — Done v4.21.118 `19db105`.
