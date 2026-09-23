# Criterio de promoción a `khimeras_shared/`

`khimeras_shared/` es el lado *shared* del demux. Hoy está hueco (solo
`__init__.py`). Este documento es el **gate**: nada se mueve aquí sin cumplir la
regla. Sin él, `khimeras_shared/` degenera en "lo que alguien creyó reusable" —
exactamente lo que el demux buscaba evitar.

Origen: acordado con el coagent orquestador (2026-06-14) como primer PR del
cierre del demux, antes de migrar `postgres.py`, `memory`, `corpus` o contratos.

## La regla (TODAS obligatorias)

Un módulo solo se promueve a `khimeras_shared/` cuando cumple las **seis**:

1. **Estable** — su API no está en flujo; no se reescribe sprint a sprint.
2. **Reusable fuera del monorepo** — tendría sentido como dependencia
   independiente, no solo dentro de server-bot.
3. **Contrato maduro** — la interfaz pública está cerrada y documentada, no es
   un detalle de implementación expuesto por accidente.
4. **Mínimo 2 consumers reales** — lo usan ≥2 personas/hosts HOY (no "lo usará
   alguien"). Demostrable con `grep`, no con intención.
5. **Ownership claro** — hay un dueño nombrado del contrato; los cambios pasan
   por él, no por quien tenga prisa.
6. **Tests compartidos** — el módulo trae su propia suite que corre
   independiente del consumidor; no hereda cobertura prestada.

## Anti-reglas (si aplica una, NO se mueve)

- **No mover por estética** — "se vería más limpio en shared" no es razón.
- **No mover por "futuro uso"** — un solo consumer + una promesa = se queda
  donde está hasta que el segundo consumer exista de verdad.
- **No mover lógica específica de persona** — la voz de Insult, los presets, el
  overlay de vulnerabilidad, etc. NO son shared aunque el código se parezca.
- **No mover APIs inestables** — si la interfaz aún cambia, promoverla obliga a
  romper a todos los consumers en cada iteración.

## Tabla de candidatos

| Módulo | Veredicto | Acción |
|---|---|---|
| `shared/corpus/` (animal_liberation, film_criticism) | **Candidato más claro** — 2 consumers reales verificados (`personas/insult/{composition,deep_memory,stages}` + `personas/alice/cogs/chat`) | **Primer move** tras este criterio. El menos peligroso. |
| `reactions` ([REACT:] parse/strip/harvest/add_reactions) | **PROMOVIDO** (2026-07-07) — 3 consumers reales: `personas/insult/cogs/chat/stages` + `personas/alice/cogs/chat` + `persona_gateway/gateway` | Vive en `khimeras_shared/reactions.py` con suite propia en `tests/shared/test_reactions*.py`. `harvest_orphan_emojis` es opt-in por persona (solo Insult lo aplica). |
| `attachments` (Discord attachment → Anthropic vision/document blocks: classify, 5MB cap + compresión de imagen, base64) | **PROMOVIDO** (2026-07-07) — 2 consumers reales: `personas/insult/cogs/chat/stages` + `persona_gateway/gateway` (P0: los siblings no veían imágenes) | Vive en `khimeras_shared/attachments.py` con suite propia en `tests/shared/test_attachments.py`. Puro Discord-ingest → bloques Anthropic; cero persona/memory/LLM. |
| `postgres.py` | Probable shared-infra | Requiere **audit** antes de mover (¿contrato estable? ¿la conexión es genérica o tiene supuestos de Insult?). |
| `memory` | Split requerido | **NO** move directo — store genérico → shared + adapters persona-specific en cada persona. Es el más arriesgado; va al final. |
| Contratos cross-persona (`/invite`, tokens, mensajería entre bots) | Candidato | Solo si ya hay consumers reales (Insult ↔ Alice). Verificar antes de prometer. |

## Secuencia acordada

1. Este documento (el gate). ← **PR actual**
2. `shared/corpus/` → `khimeras_shared/` (candidato más claro, 2 consumers).
3. `postgres.py` → `khimeras_shared/infra/` (tras audit).
4. Contratos cross-persona → `khimeras_shared/contracts/` (si hay consumers reales).
5. Split de `memory` (último — el más peligroso).

`memory` **no** se toca hasta el final, por orden explícito del coagent: es split,
no move, y un error ahí pega a la memoria longitudinal de ambas personas.
