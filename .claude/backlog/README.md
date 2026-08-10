# Backlog — discord-bot

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook. Items Done se retiran del folder (limpiezas
2026-07-05 y 2026-08-06); su historia vive en git.

**Última auditoría contra el repo y prod: 2026-08-06** (`git log`/`git show`,
`grep -rn`, `az containerapp list|show|job list`, `az acr list`). Cada status de
abajo se re-verificó ese día; los que no se pudieron verificar lo dicen.

| Item | Status | Hook |
|---|---|---|
| [Cadenas cortadas post-purga + código muerto](cadenas-cortadas-post-purga.md) | Triaged (2026-07-15) · re-verificado 2026-08-06 sin cambios | los 4 congelados siguen congelados y los 3 cero-callers (consolidation, `RouterBudget`, `class LLMShadowRouter`) siguen sin dueño ni fecha. El job `fact-consolidation` sigue en cron 31-feb con la imagen pre-purga; su hermano zombie `insult-canary` sí murió hoy (v4.32.27) |
| [Dashboard: data plane fósil](dashboard-data-plane-fossil.md) | Proposed (2026-07-20) | cero uploaders de los blobs desde el retiro del plumbing; pill "connected" verde sobre datos muertos. Fork de Bernard: recablear upload desde persona-gateway o congelar la superficie (KQL/Postgres ya son la observabilidad real) |
| [La proactividad murió en la purga](proactividad-muerta-restaurar-en-el-host.md) | Accepted (2026-08-06, dirección de Bernard) | `2f8d9ad` borró 1,184 líneas de sistema proactivo y nunca se replantaron; restaurarlo en el host como banda de agentes. *(Item creado hoy por una sesión paralela — su contenido no se auditó aquí)* |
| [Graceful turn drain en deploys](graceful-turn-drain-on-deploy.md) | **In progress** (era "Proposed", mentía a la baja) | paso 1 HECHO (retry 502/503, v4.32.1); el drenaje real NO: sin gate SIGTERM en runner/gateway y `terminationGracePeriodSeconds: null` en `persona-runner` |
| [Builder de turno unificado](turn-builder-unificado.md) | Proposed — parcialmente adelantado | `TurnContextBuilder` ya unificó contexto/guidance/corpus, pero `TurnSpec`/`TurnBuilder` no existen, `_handle` y `respond_to_invite` siguen artesanales y NO hay arnés de paridad en `tests/arch/` |
| [Frugívoro persona](frugivoro-persona.md) | In progress — **corpus RAG ya vivo**; falta el benchmark | el item pedía 4 pasos para "activar" el corpus: 3 verificados en repo (namespace `__corpus_vegan__` en el registry, `scripts/ingest_corpus.py`, `data/corpus/frugivoro/` + MANIFEST, RAG generalizado v4.24.0/4.24.4) y el 4º (ingesta corrida contra prod) **sin verificar** — no se consultó Postgres. Vivo sólo el benchmark ético §1–§3 |
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | In progress (ACR parcial) | las 3 apps del repo pullean de `serverbotacr`, pero **`susurro-gateway` volvió a `insultacr`** (su CD vive en otro repo). `insultacr` no se puede borrar: 3 proyectos ajenos + el job `fact-consolidation` + la app retirada. RG→`server-rg` = reconstrucción con downtime, agendada por Bernard |
| [Renombrar Frugi → Fruggy](rename-frugi-to-fruggy.md) | **In progress** (2026-08-10) — slice 1 abierto como issue #36 | el registry sigue con `display_name="Frugívoro"` y `aliases=[frugivoro, frugi, frugívoro]`. Slice 1 = solo el alias `fruggy` (primer issue de Alex); `display_name`, username de Discord y los ~129 hits de "frugi" quedan fuera, pendientes de decisión de Bernard |
| [CVE exploitability review](cve-exploitability-review.md) | Proposed — **cero bumps ejecutados** (faltaba en este índice) | análisis entregado 2026-07-19 con 8 bumps disponibles y un ignore a soltar (`CVE-2026-3219`, "MITIGADO"); a 2026-08-06 `environment.yml` y `ci.yml` siguen igual. Colateral vigente: `persona-runner` tiene `ingress.external: true` |
| [ML-stack CVE tax](ml-stack-cve-audit.md) | Proposed | `sentence-transformers`→torch/transformers sigue EN USO, pero sólo por 2 consumidores vivos (`memory/connection.py`, `memory/minilm_embedder.py`) — las rutas `personas/insult/core/*` que citaba murieron en la purga. El RAG de corpus YA embebe con Azure ada-002: el precedente existe y hoy hay dos motores de embeddings conviviendo |

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
