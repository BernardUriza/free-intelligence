# Cadenas cortadas por la purga de `personas/` — triage revivir/congelar

Status: Triaged (2026-07-15) · auditoría de código muerto 2026-07-20 ·
**#5 RESUELTO 2026-08-06** (consolidador + job borrados) ·
**re-verificado 2026-09-07**: de los 3 cero-callers queda UNO
(`class LLMShadowRouter`); `RouterBudget` revivió como cap del router vivo.
Ver el bloque final.
Proposed: 2026-07-14 by la autopsia 10-agentes; decidido 2026-07-15 by Bernard+Claude

## Re-chequeo 2026-09-09 — al item le queda UNA acción

**El #4 (corpus) quedó rancio el mismo 09-07, y esa auditoría no lo pudo
recoger porque el borrado ocurría mientras se auditaba** (su índice lo declara:
*"otro agente lo estaba podando en el mismo momento"*). Ese agente fue
`6ba7a61` (v4.38.6, issue #62, 2026-09-07 11:09):

    khimeras_shared/corpus/__init__.py   217 --   corpus/rag.py            235 --
    animal_liberation.md 82 --  animal_liberation_tactics.md 54 --
    film_criticism.md   104 --  vegan_gastronomy.md         251 --
    tests/core/test_animal_tactics.py 87 --        → 1,017 líneas borradas

Hoy `ls khimeras_shared/corpus/` → `__init__.py`, `pg_rag.py`, `references.py`.
Así que la entrada #4 describe un repo que ya no existe.

**Segundo dato rancio, más viejo:** este item da por muertos los `ingest_*`,
pero `scripts/ingest_corpus.py` vive y está trackeado desde `d6b1297`
(2026-07-16). El camino vivo del corpus es RAG por namespace (`registry.py`
declara cinco `corpus_namespace`, y `turn_context.py:220` los inyecta con
`append_corpus_block`); el re-poblado migró al **issue #61, abierto**.

**Lo único que le queda a este item:** `class LLMShadowRouter`
(`demux_ai/llm_shadow_router.py:129`) — 9 construcciones, **todas** en
`tests/test_llm_shadow_router.py`, cero en producción desde el cutover a
gpt-4.1. Borrarla y borrar su test cierra el item entero; hasta entonces es un
módulo que sólo existe para que su propia prueba lo construya
([[migrations-end-with-deletion]]: la definición de done es el grep vacío).

La purga de `personas/` (2f8d9ad) mató el `debug_server` y varios scripts de tooling
que eran el DISPARADOR de superficies auxiliares. En cada caso la capa de DATOS
sobrevivió en `khimeras_shared`; lo que murió fue el trigger/HTTP/tooling. Decisión
por superficie, calibrada al blast radius real (bot de ~1 usuario, Art. proportional-rigor).

## 1. html_artifacts — ✅ REVIVIDO (2026-07-15, 3fea06b + e3ddbbf)

El bot minteaba URLs `/a/{id}` a un FQDN muerto (nicecliff NXDOMAIN, greendune
escalado a 0). Ahora el **runner sirve `/a/{id}`** él mismo (`persona_runner/api/
artifacts.py` → `get_artifact` → HTMLResponse), `ARTIFACT_BASE_URL` apunta a su
propio FQDN, y `publish_html_artifact` falla en voz alta si no está configurado en
vez de mintear un cadáver. Cerrado.

## 2. dashboard SWA — ❄️ CONGELADO

`dashboard/` (Brython + HTML estático, su propio Azure Static Web App) leía su feed
del `debug_server` que vivía en `personas/insult` — muerto. La capa de datos (Postgres)
vive; el endpoint que el dashboard consumía, no. Para 1 usuario, un dashboard de ops
no vale re-cablear ahora. **Congelado**: si se revive, su feed debe apuntar a un
endpoint nuevo en el runner o el gateway (no al `debug_server` muerto).

## 3. sync SerenityOps — ❄️ CONGELADO

El repo `khimeras_shared/memory/repositories/serenityops.py` (snapshots + sync tokens)
SOBREVIVIÓ, pero el endpoint HTTP que creaba/resolvía los tokens vivía en el
`debug_server` muerto. Sin superficie para disparar el sync. **Congelado**: revivir =
exponer las operaciones de sync token como rutas del runner. Bajo valor a 1 usuario.

## 4. RAG re-poblado — ❄️ CONGELADO (el corpus está VIVO)

`khimeras_shared/corpus/` (animal_liberation, film_criticism, vegan_gastronomy) + `pg_rag.py`
+ `rag.py` están VIVOS — el corpus se consulta bien. Lo que murió son los `ingest_*`
scripts (re-poblado del `deep_memory_chunks`). El corpus es contenido estático que no
necesita re-poblado frecuente. **Congelado**: los ingest scripts viven en git
(`2f8d9ad^:scripts/ingest_*`); resucitar solo si se agrega corpus nuevo.

## Cómo descongelar

Cada "❄️" es reversible: la capa de datos existe, solo falta re-cablear el disparador
a una ruta viva (runner/gateway). Ninguna es urgente a la escala actual.

## 5. Job `fact-consolidation` — ❄️ CONGELADO POR SEGURIDAD (2026-07-15)

**Era un riesgo real para Alex, no infra de bajo valor.** El ACA Job corría cada
2 días (`0 7 */2 * *`) con la imagen PRE-PURGA `insult-bot:d6fa36c` y el comando
`python -m personas.insult consolidate-facts` — o sea, el consolidador VIEJO, SIN
el guard clínico (`filter_clinical_destruction` + prompt conservador) que se agregó
hoy. Estaba podando los facts de Alex cada 48h con capacidad de borrar salud/trauma.

**Congelado**: cron cambiado a `0 0 31 2 *` (31-feb, nunca se dispara). Reversible.
**Re-hogar (follow-up)**: construir un entrypoint de consolidación en el sistema
vivo (`khimeras_shared.consolidation.orchestrator` — el módulo existe, 688 LOC con
el guard clínico ya integrado; la ruta vieja `khimeras_shared.memory_consolidation`
fue renombrada en b3c8894) + una imagen que lo corra, y recién entonces re-activar
el cron. NUNCA re-activar apuntando a la imagen vieja.

## Auditoría de código muerto post-purga (2026-07-20)

Una pregunta casual ("cuál .py tiene más LOC") destapó que `khimeras_shared/behavior/
flows/` (~2,700 líneas: pipeline + test + 30 .md) llevaba desde la purga **sin un
solo caller vivo, aparentando conexión** — se borró por la raíz en v4.29.0/29.1
(commits df0acbd, 5437e92). Eso disparó un barrido completo del repo (Agent Explore,
grep de callers vivos por módulo). Resultado: **NO hay más muertos-invisibles tipo
flows.** Los 3 candidatos con cero callers son todos **congelados/dormantes por
diseño y documentados** — se registran aquí con dueño y decisión pendiente para NO
re-descubrirlos en la próxima auditoría:

| Ruta | LOC | Cero-callers verificado | Por qué NO se borró |
|---|---|---|---|
| `khimeras_shared/consolidation/` | 688 | grep del paquete = 0 importadores vivos (solo strings de provenance + `apply_consolidation_plan` que es método del *repository*, no del paquete) | **Salvaguarda clínica de Alex** — es el item #5 de arriba, congelado a propósito con el guard `filter_clinical_destruction`. Borrarlo destruye la maquinaria que se va a re-homear. |
| `demux_ai/router_budget.py` (`RouterBudget`) | 112 | `RouterBudget(` no se construye fuera del propio archivo; el `_BUDGET.record()` de `router_runtime` es OTRA clase (rate-limiter per-user) | Hoja huérfana **dentro del host #6 (`demux_ai/`), deployado-pero-dormante por diseño**. Perdió su consumidor en la purga del shadow stage; su re-cableado depende de cuándo el host owné la recepción. |
| `class LLMShadowRouter` en `demux_ai/llm_shadow_router.py` | ~32 | solo construido en tests; el vivo es `DirectAzureLLMRouter` (`demux_ai/__main__.py:25`, `scripts/router_eval.py`) | **NO borrar el archivo** — comparte módulo con `DirectAzureLLMRouter` y helpers vivos. Solo la clase agéntica cara está muerta, también dentro del host #6 dormante. |

**Decisión de Bernard pendiente** (sin fecha forzada): descongelar-y-re-cablear vs.
borrar. Los tres son reversibles vía git. El peso va hacia **mantener** en los tres
— consolidation por Alex, los dos del host por ser infra en construcción, no basura.

## Re-verificación 2026-08-06 (auditoría del backlog)

Los cuatro congelados y los tres cero-callers siguen EXACTAMENTE igual; nadie
descongeló nada en 17 días. Receipts:

| Cosa | Estado hoy | Cómo se verificó |
|---|---|---|
| #1 html_artifacts (revivido) | sigue vivo | `az containerapp show -n persona-runner ... env` → `ARTIFACT_BASE_URL=https://persona-runner.greendune-53f1f4af.eastus2.azurecontainerapps.io` |
| #5 job `fact-consolidation` | congelado, intacto | `az containerapp job list -g insult-rg` → único job, cron `0 0 31 2 *`, imagen PRE-PURGA `insultacr.azurecr.io/insult-bot:d6fa36c7` |
| `khimeras_shared/consolidation/` | 0 importadores vivos (sólo sus propios módulos + tests) | `grep -rn "khimeras_shared.consolidation" --include='*.py' .` |
| `demux_ai/router_budget.py` | `RouterBudget` sólo se construye en `tests/core/test_router_budget.py` | `grep -rn "RouterBudget" --include='*.py' .` |
| `class LLMShadowRouter` | sigue muerta-pero-presente; el vivo es `DirectAzureLLMRouter` (`demux_ai/__main__.py:25`, `scripts/router_eval.py:140`) | mismo grep |

Nota de cruce: el job `insult-canary` —el OTRO job huérfano que este repo daba
por borrado desde el 21-jun— resultó ser un zombie real y **se borró hoy**
(v4.32.27, `ccea31e`). Es la misma clase de mentira que esta auditoría persigue:
un doc afirmando una deleción que nunca ocurrió. `fact-consolidation` es el que
queda, y su borrado está subordinado al re-hogar del #5.

El item #2 (dashboard SWA) tiene su propio archivo desde 2026-07-20:
[[dashboard-data-plane-fossil]] — la decisión de recablear-vs-congelar vive ahí.


## RESUELTO 2026-08-06 — el consolidador se borró entero, código y job

Bernard, ante la disyuntiva descongelar-vs-borrar: **"lo que sea más radical"**.

La auditoría forense de ese día reveló que "congelado por diseño" era un
eufemismo. El job **estaba fallando en producción** antes de congelarse:

    fact-consolidation-29732100  Failed  2026-07-13
    fact-consolidation-29729220  Failed  2026-07-11
    fact-consolidation-29726340  Failed  2026-07-09

con causa concreta en los logs — `consolidator_run_started {"users": 2}` seguido
de `POST /v1/judge → 422 Unprocessable Content`: la imagen congelada hablaba un
esquema que el runner ya no acepta. El "congelamiento" del 07-15 fue moverle el
cron al **31 de febrero**, una fecha que no existe. Un cron imposible no frena
una falla: la esconde.

Y el job muerto seguía montando **cuatro secretos vivos** (`postgres-url`,
`discord-token`, `insult-agent-runner-token`, `acr-password`) sobre la imagen
`insult-bot:d6fa36c` — pre-purga, sin parches, sin supervisión.

Borrado ejecutado:
  - ACA Job `fact-consolidation` (backup fuera de todo repo en
    `~/.secrets/azure-job-backups/`, chmod 600). `az containerapp job list -g
    insult-rg` ahora devuelve VACÍO.
  - `khimeras_shared/consolidation/` — 5 archivos
  - sus 3 suites + `prompts_md/memory_consolidator_judge.md` — 1,226 líneas
  - referencias huérfanas en `scripts/dr_inventory.sh`, `docs/runbook_dr.md`,
    `.github/workflows/cd.yml`, `CLAUDE.md`, `.claude/rules/architecture.md`

**El costo, asumido y escrito, no escondido:** se fue con él
`filter_clinical_destruction`, la guarda que impedía borrar un fact clínico de
Alex sin importar lo que pidiera el juez. Era irrelevante sin consolidador —nada
podaba— pero es cara de reconstruir. Vive en git. Si el consolidador vuelve,
vuelve CON su guarda y CON su consumidor en el mismo PR, nunca antes.

**Consecuencia que queda abierta:** los facts son ADD-only y ahora nada los poda
jamás. Está escrito en `CLAUDE.md` § Memory & facts para que no sorprenda a nadie
dentro de tres meses.

Bonus del barrido: `scripts/dr_inventory.sh` listaba `discord-bot` (retirado a
cero) y **omitía `khimeras-host`** (la app viva). Un runbook de recuperación ante
desastres que enumera mal las apps es peligroso justo cuando se necesita.
Corregido a `(persona-gateway persona-runner khimeras-host)`.

## Re-chequeo 2026-09-07 (auditoría del backlog)

El índice `README.md` seguía diciendo *"el job `fact-consolidation` sigue en
cron 31-feb"* un mes después del bloque de arriba — la fila se quedó rancia
aunque este archivo ya decía RESUELTO. Estado real hoy:

| Cosa | Estado 2026-09-07 | Cómo se verificó |
|---|---|---|
| #5 job `fact-consolidation` | **no existe** | `az containerapp job list -g insult-rg` → vacío |
| `khimeras_shared/consolidation/` | **no existe en git** (queda un `__pycache__` huérfano en disco) | `git ls-files khimeras_shared/consolidation \| wc -l` → `0` |
| `demux_ai/router_budget.py` (`RouterBudget`) | **YA NO es cero-callers**: `72d5175` (2026-08-06, v4.32.36, *"el cap de $5/semana que autorizaste llevaba un mes sin cumplirse"*) lo instancia en `DirectAzureLLMRouter.__init__` (`llm_shadow_router.py:186`) y `route()` consulta `can_spend()` antes de gastar | `grep -rn "RouterBudget" --include='*.py' demux_ai` → import en `llm_shadow_router.py:33`, uso en `:186`/`:229` |
| `class LLMShadowRouter` | sigue construida SÓLO en `tests/test_llm_shadow_router.py`; ahora envuelve `HostRouterLLM` (AIRE, `2150ca0`), pero el host vivo arranca `DirectAzureLLMRouter` (`demux_ai/__main__.py:25`) | `grep -rn "LLMShadowRouter(" --include='*.py' .` → sólo tests |
| #1 html_artifacts | sigue vivo | env de `persona-runner`: `ARTIFACT_BASE_URL=https://persona-runner.greendune-53f1f4af.eastus2.azurecontainerapps.io` |
| #2 dashboard | tiene su propio item ([[dashboard-data-plane-fossil]]) | — |
| #3 sync SerenityOps | sin movimiento | `git log --since=2026-08-06 -- khimeras_shared/memory/repositories/serenityops.py` → vacío |
| #4 RAG re-poblado / `khimeras_shared/corpus/` | **NO auditado hoy** — otro agente estaba borrando código muerto en ese paquete durante esta auditoría | — |

Queda un solo cero-caller documentado (`class LLMShadowRouter`, ~32 líneas
dentro de un módulo vivo). La decisión de borrar la clase sigue siendo de
Bernard; el peso sigue en mantener porque comparte archivo con el router vivo.
