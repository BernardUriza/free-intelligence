# Backlog — discord-bot

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook. Items Done se retiran del folder (limpiezas
2026-07-05 y 2026-08-06); su historia vive en git.

**Última auditoría contra el repo y prod: 2026-09-09** (`git log --since=2026-09-07`,
`grep -rn`, `az containerapp list|show|acr list|job list`, `gh issue list`,
`curl -I` al blob del dashboard y al FQDN del runner, y **`psql` de sólo lectura
contra la Postgres de prod**). Las anteriores: 2026-09-07 y 2026-08-06. Cada fila
se re-verificó hoy y los items que cambiaron llevan su bloque *Re-chequeo
2026-09-09*; los que no se pudieron verificar lo dicen.

**Los dos huecos que el 09-07 declaró, cerrados hoy:**
- *Postgres (sin acceso)* → **sí hubo acceso** (credencial de `~/.secrets/`,
  consumida a variable, nunca impresa; sólo `SELECT`/`COUNT`). Cerró la deuda más
  vieja del folder: la ingesta del corpus de Frugívoro, sin verificar desde el
  2026-08-06.
- *`khimeras_shared/corpus/` (otro agente lo estaba podando)* → ese agente era
  `6ba7a61` (v4.38.6, issue #62), del mismo 09-07: borró 1,017 líneas de corpus.
  Dejó **tres items rancios** que el 09-07 no pudo recoger porque el borrado
  ocurría mientras se auditaba.

**Y dos contradicciones internas del 09-07, corregidas aquí** — las dos son la
misma forma: el commit de esa auditoría ARREGLÓ algo y su propio índice lo dejó
escrito como pendiente. Ver las filas de AIRE etapa 1 y de Frugívoro.

**No verificado hoy:** que Valentis conteste en vivo en #general (misma deuda que
el 09-07), y la re-auditoría de alcanzabilidad CVE por CVE — se verificó la lista
de `--ignore-vuln` y los pisos de versión, no el análisis de cada CVE.

| Item | Status | Hook |
|---|---|---|
| [Servidor llave en mano con personas de Alex](servidor-llave-en-mano-personas-alex.md) | 🔒 **Congelado hasta 2027** (candado de Bernard 2026-08-17, `84cfe15`) | re-confirmado 2026-09-09: el ÚNICO commit al item desde el candado es `1af6718`, la auditoría del 09-07, y su diff son 4 líneas de status. Cero ejecución ante terceros. Nada que proponer aquí |
| [Persona de acompañamiento psicológico](persona-acompanamiento-issues-alex.md) | **Fase 1 SHIPPED** (2026-08-25, v4.32.75–80) — fase 2 sin issue propio | re-verificado 2026-09-09: `VALENTIS_DISCORD_TOKEN` sigue en el env vivo de `persona-gateway` (secretRef `valentis-discord-token`), `shared/personas/valentis.md` y su preset `respectful_serious` existen; #41–#44 CLOSED. **Matiz nuevo:** el issue **#61 (OPEN, 09-07)** cubre UNA de las cuatro piezas de la fase 2 — el corpus — y ahí Valentis aparece con `corpus_namespace=None` y **0 chunks**. Las otras tres (facetas por tema, presets propios, overlay propio) siguen sin issue. **No verificado:** que Valentis conteste en vivo (misma deuda que el 09-07) |
| [Cadenas cortadas post-purga + código muerto](cadenas-cortadas-post-purga.md) | **Casi agotado** — le queda UNA acción: borrar `LLMShadowRouter`. Re-verificado 2026-09-09 | de las cinco entradas, tres murieron y la cuarta se resolvió río arriba. **El #4 (corpus) quedó rancio el mismo 09-07 y esta auditoría no lo pudo recoger:** `6ba7a61` (#62) borró `khimeras_shared/corpus/{animal_liberation,film_criticism,vegan_gastronomy}.md` + `rag.py` + su test — 1,017 líneas; hoy el folder sólo tiene `__init__.py`, `pg_rag.py`, `references.py`. Otro dato rancio más viejo: el item da por muertos los `ingest_*`, pero `scripts/ingest_corpus.py` vive y está trackeado desde `d6b1297`. Queda vivo: `class LLMShadowRouter` (`demux_ai/llm_shadow_router.py:129`) con **9 construcciones, todas en `tests/test_llm_shadow_router.py`** y cero en producción. Borrarla cierra el item entero |
| [Dashboard: data plane fósil](dashboard-data-plane-fossil.md) | **In progress** — fake-green eliminado 2026-08-06 (`34bf41c`, v2.4.0); fork de Bernard sigue abierto | re-verificado 2026-09-09, sin cambios: `dashboard/py/freshness.py:5` deriva el pill del timestamp del productor; el blob sigue con `Last-Modified: 25 Jun 2026` — **76 días de fósil** — y el de `alice-bot` da 404. `git log --since=2026-09-07 -- dashboard/` → vacío. Fork: recablear el emisor en `persona_gateway` o congelar |
| [La proactividad murió en la purga](proactividad-muerta-restaurar-en-el-host.md) | Accepted · **slice 1 HECHO** 2026-08-06 (`aae8e2c`, v4.32.33); slices 2–5 sin arrancar | re-verificado 2026-09-09, las cuatro afirmaciones intactas: `khimeras_shared/proactive.py` y su test viven, el ÚNICO import es el propio test, cero `ProactiveWorker` en `demux_ai/`, y `store_world_scan` sólo lo llama `tests/core/test_world_scans.py` — cero escritores en producción. **Cuidado con el falso positivo:** `khimeras_shared/proactive_agenda.py` SÍ tiene consumidor vivo (`persona_gateway/workers/agenda.py:11`), pero ése es el worker reactivo de `[AGENDA:]`, no este núcleo. **No verificado:** el contenido de la tabla `world_scans` en Postgres |
| [Graceful turn drain en deploys](graceful-turn-drain-on-deploy.md) | **In progress** — paso 3 desplegado; **2026-09-19 (v4.39.0)**: el gate no corrió porque un SIGTERM DUPLICADO se leía como "mátalo" — corregido; y el incidente destapó que el ingress corta a los 240 s → turnos con boleto (`robustness.md`) | dos correcciones con recibo (2026-09-09): **el runner YA drena** — uvicorn instala el handler y espera indefinidamente (`timeout_graceful_shutdown=None`), lo que mata el turno es el SIGKILL al vencer el grace period, así que el paso 2 no era construir un drain sino darle tiempo al que hay; y **subir el grace period en el gateway sin gate de recepción da respuestas DOBLES** (dos réplicas sosteniendo el mismo token de Discord), así que el gate es prerequisito, no el "complemento opcional" que decía el item. El paso 1 se amplió donde más dolía: el presupuesto de reconexión pasó de 0.75s a un reloj de 45s, porque un turno nuevo durante el swap moría contra el socket cerrado |
| [Builder de turno unificado](turn-builder-unificado.md) | **In progress** — 4 de los 5 defectos CERRADOS 2026-09-09 (v4.38.26); quedan 2 asimetrías, ambas por decisión, no por trabajo | re-verificado 2026-09-09: `TurnSpec`/`TurnBuilder` siguen sin existir (el único hit es un docstring de `aire_route.py:659`, que además nombra otro concepto) y `_handle`/`respond_to_invite` siguen siendo dos entry points. Pero el CI ya impone paridad, así que el refactor rinde poco; **lo que rendía eran los 5 `xfail(strict)` del arnés, y hoy quedan 2** (de 48 passed/5 xfailed a **52 passed/2 xfailed**). Cerradas: el `memory.store` y `attachment_blocks` desnudos de `_handle` (los dos que perdían la respuesta delante del humano), el `corpus_query` que iba keyed por el resumen del router, y la mitad del cuarto que escribía facts bajo el id del propio bot. Las cuatro verificadas en rojo revirtiendo cada fix. **De paso destapó una contradicción entre dos arneses del repo:** `test_gateway_corpus_wiring.py` fijaba el defecto del corpus como correcto mientras el de paridad lo marcaba xfail. Lo que queda son las dos que no son trabajo sino decisión — qué `user_id` recibe el runner cuando no hay humano, y si el host va a escuchar ediciones. Detalle: (1) ✅ el `memory.store` de `_handle` ya va guardado — un parpadeo de Postgres degrada en vez de matar el turno; (2) ✅ igual con `attachment_blocks` — un adjunto corrupto ya no se come la respuesta; (3) ✅ `corpus_query=subject_ask or reason`; (4) 🟡 media — los facts bajo el id del bot ya se descartan, pero el runner sigue recibiendo ese id como sujeto del turno; (5) 🔴 el summon-por-edición sigue muerto desde el cutover, y es capacidad nueva en el host, no un fix |
| [Frugívoro persona](frugivoro-persona.md) | **Los 4 pasos verificados** por primera vez (2026-09-09) — falta sólo el benchmark | la deuda más vieja del folder, cerrada: `psql` de sólo lectura contra prod da **858 chunks** bajo `user_id='__corpus_vegan__'` (la columna es `user_id`, no `namespace`), en 3 `source_ref` — Williams *Ethics of Diet* 749, y dos revisiones PMC de 60 y 49 — ingeridos el 2026-07-16, exactamente las 3 fuentes del MANIFEST. **Contradicción del 09-07 corregida aquí:** ese índice decía "sin acceso a Postgres" y sí lo había. **Y el item quedó rancio el mismo día:** cita `khimeras_shared/corpus/vegan_gastronomy.md` como vivo dos veces y `6ba7a61` lo borró (recuperable en `git show 798ba77:khimeras_shared/corpus/vegan_gastronomy.md`). Benchmark §1–§3 sin arrancar, sin issue |
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | In progress — ACR consolidado en GHCR (2026-08-12); RG + repo pendientes | re-verificado 2026-09-09, sin cambios: `az acr list` → sólo `insultacr`, con los mismos dos inquilinos — la app retirada `discord-bot` (Running, min=0, `insult-bot:d6fa36c`) y `rancho-studio`. Las tres del repo, más `susurro-gateway` y `aire-front`, pullean de GHCR. `az containerapp job list` → vacío. RG→`server-rg` sigue agendado |
| [Renombrar Frugi → Fruggy](rename-frugi-to-fruggy.md) | **Slice 1 DONE** (alias `fruggy`, `40a4fea` v4.32.45; #36 cerrado 2026-08-14) — resto en decisión de Bernard | re-verificado 2026-09-09. Registry intacto: `aliases=["frugivoro","frugi","frugívoro","fruggy"]`, `display_name="Frugívoro"`. **Ojo con el conteo: bajó de 146 a 125 hits y NO es progreso** — `6ba7a61` borró `vegan_gastronomy.md`, que traía 21 de esos hits (146 − 21 = 125, cuadra exacto). Siguen fuera el `display_name`, el username del bot en Discord y el `persona_id`/DNA/`token_env` |
| [CVE exploitability review](cve-exploitability-review.md) | Proposed — 1 de 9 acciones ejecutada (`fde7584`, v4.38.7); cero bumps | re-verificado 2026-09-09: `ci.yml` sin un solo cambio desde el 09-07, **34 `--ignore-vuln` en pie** (líneas 225-258); `CVE-2026-3219` sobrevive sólo como comentario de historia, o sea que el drop aguantó. En `environment.yml` el único diff son fi-core 0.27.0→0.30.0 y fi-runner 0.21.2→0.21.5, ajenos a la lista: **cero pisos nuevos**. Colateral: `persona-runner` sigue con `ingress.external: true`, `ipSecurityRestrictions: null` — pero hoy su superficie pública se estrechó, `6aebcbb` (v4.38.23) dejó `/docs` y `/openapi.json` en **404** desde internet. **No verificado:** la alcanzabilidad CVE por CVE |
| [Arranque en frío del runner: `min=0` cuesta un turno mudo al día](runner-cold-start-min-replicas.md) | **Proposed** 2026-09-23 — el gateway YA sobrevive el frío (v4.39.6: alta idempotente + reintento); queda la decisión de Bernard: `min=1` (gasto) y/o startup probe (gratis) | recibo: probe de v4.39.5 en #general 13:32 UTC → `host_turn_gave_up` a los 135 s, alta aceptada por el runner a los 169 s, dos turnos huérfanos. 7 días: 105 arranques, 5 give-ups |
| [ML-stack CVE tax](ml-stack-cve-audit.md) | Proposed · re-verificado 2026-09-09 sin cambios | `sentence-transformers>=3.0.0` sigue, ahora en **`environment.yml:176`** (el item dice `:146`; la línea corrió por los comentarios de fi-core, no por un cambio de contenido). Consumidores vivos siguen siendo dos más el test: `memory/minilm_embedder.py:49`, `memory/connection.py:147`, `tests/core/test_vectors.py:14`. El bloque `--- ML stack advisories (2026-05-20) ---` intacto en `ci.yml:141` |

## Retirados (Done verificado, 2026-09-09 — historia en git)

- **AIRE gateway etapa 1: relay Anthropic** — Superseded por la etapa 2
  (2026-08-28) y **sin ninguna acción abierta**, contra lo que este índice decía.
  La fila afirmaba que *"`docs/runbook_dr.md:60-62` sigue listando los dos env
  vars muertos — pendiente"*. Falso: `grep -rn
  "ANTHROPIC_BASE_URL\|ANTHROPIC_CUSTOM_HEADERS" . --exclude-dir=.git` deja UN
  hit fuera del backlog, `docs/runbook_dr.md:58`, y esa línea dice justamente lo
  contrario — que las dos env vars *"ya no existen en la app: salieron en la
  revisión 195"*. `git show 1af6718 -- docs/runbook_dr.md` lo explica: **el mismo
  commit de la auditoría del 09-07 hizo la limpieza y su propio índice la dejó
  escrita como pendiente.** Env vivo de `persona-runner` confirmado hoy sin
  ningún `ANTHROPIC_*`: `POSTGRES_URL`, `PERSONA_RUNNER_TOKEN`,
  `ARTIFACT_BASE_URL`, `AIRE_GATE_URL`, `AIRE_AUTH_TOKEN`, `RUNNER_MCP_TOKEN`,
  `RUNNER_MCP_BASE`.

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
- [cd-gateway-health-fake-green](cd-gateway-health-fake-green.md) — Proposed — el CD da success con la revisión nueva del gateway en crash loop
