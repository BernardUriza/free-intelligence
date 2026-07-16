# ADN nivelado: biografía + estilo de escritura + gustos auto-seleccionados por persona

Status: Done (2026-07-16 — los 5 slices en un día: plantilla, 5 personas niveladas, exoesqueleto Unborn, reflection worker)
Proposed: 2026-07-16 by Bernard (vía /histerical-search — investigación completa en ese turno)

## What it is
Que cada robot tenga ADN distinto y se le NOTE: estilo de escritura propio,
biografía ficticia-pero-aterrizada (el mundo = Khimeras, donde robots viven con
humanos), y gustos propios adquiridos y seleccionados por ellos de manera
PERMANENTE. Hoy solo Insult tiene el kit completo (979 líneas de DNA, self-facts,
guidance content); los hermanos andan en 92-122 líneas sin bio, sin ejemplos de
estilo y sin acceso documentado a `agent_facts`.

Receta validada (15+ fuentes, ver conversación 2026-07-16):
1. **Biografía** = eventos formativos + relaciones + qué quiere, anclada al mundo
   (Character-LLM: un personaje son sus recuerdos; Generative Agents: seed
   memories; spec chara_card_v2/v3: description/scenario/first_mes).
2. **Estilo** = 2-3 diálogos de ejemplo few-shot + tics/hábitos lingüísticos +
   prohibiciones explícitas (PersonaGym: "linguistic habits" es métrica de
   primera clase; las cards usan mes_example como ancla de estilo).
3. **Gustos permanentes auto-seleccionados** = reflection loop periódico
   (Generative Agents) que escribe a `agent_facts` con
   `provenance=self_declared` (patrón persona-block de Letta — el nuestro YA
   existe y tiene mejor semántica de provenance).
Fine-tuning (Character-LLM) DESCARTADO: runner = Claude OAuth, sin FT, e
innecesario a nivel prompt.

## Canonical path to reuse (Art. 6)
- Plantilla: la estructura de `shared/personas/insult.md` (secciones Identity
  DNA / Lo que yo sé sobre mí) — nivelar hermanos hacia ella, NO inventar formato.
- Self-facts: tubería `agent_facts` + `get/add/update_agent_fact` ya en prod,
  keyed por `agent_id`. Solo falta documentarla en el DNA de cada hermano.
- Reflection loop: clonar el molde de los workers existentes
  (`AgendaWorker`/`memory_consolidation` cron) — pregunta periódica "¿qué
  aprendiste de ti / qué gusto confirmaste?" → `add_agent_fact(self_declared)`.
- Frugívoro ya tiene proto-bio ("## Origen"); Vultur ya tiene hábito lingüístico
  duro (cierre IFA) — extender, no reescribir.

## Slices
1. Plantilla de secciones `## Biografía` + `## Estilo de escritura` (con
   ejemplos) definida y aplicada a UN hermano (Vultur, el más maduro) como canary.
2. Nivelar ALICE + Frugívoro con la plantilla.
3. Sección "Lo que yo sé sobre mí" (agent_facts) en los 3 hermanos.
4. Reflection worker (cron bajo, p.ej. semanal) con provenance=self_declared.
5. `unborn_being.md`: convertir los 3 prompts crudos estilo-assistant en un
   persona Khimeras nacido con la plantilla (bio atea/antinatalista incluida) —
   hoy violaría el character guard tal cual está.

## The decision that's the owner's
- El CONTENIDO de cada biografía y estilo (identidad creativa de sus robots) —
  Claude propone drafts, Bernard aprueba.
- Cadencia del reflection loop y si los self-facts de gustos entran al system
  prompt en cada turno (costo de contexto) o vía get_agent_facts on-demand.
- GO del slice 1.

## Status / next step
DONE COMPLETO (2026-07-16). Slices 1-2-3-5: plantilla + 5 personas con
bio/estilo/self-facts. Slice 4: ReflectionWorker en persona_gateway/workers/
reflection.py — loop 6h con gate durable semanal (agents.last_reflected_at),
juez vía /v1/judge (prompt en prompts_md/self_reflection.md), escribe a
agent_facts con provenance=self_declared, ADD-only, fail-safe total.
Cadencia y knobs en GatewayConfig (reflection_*).
