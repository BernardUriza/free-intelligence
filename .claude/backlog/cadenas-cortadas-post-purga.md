# Cadenas cortadas por la purga de `personas/` — triage revivir/congelar

Status: Triaged (2026-07-15)
Proposed: 2026-07-14 by la autopsia 10-agentes; decidido 2026-07-15 by Bernard+Claude

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
