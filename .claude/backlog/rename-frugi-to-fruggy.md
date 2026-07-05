# Renombrar Frugi → Fruggy

Status: Proposed
Proposed: 2026-07-05 by Bernard

## What it is

Renombrar la persona Frugívoro de su apodo actual "frugi" a **Fruggy** — el
nombre corto con el que se le habla en Discord. Alcance a decidir al ejecutar:
como mínimo el alias (`aliases` en el registry) y probablemente el
`display_name`/username del bot en Discord; el `persona_id` interno
(`frugivoro`), el archivo DNA (`shared/personas/frugivoro.md`) y el
`token_env` pueden quedarse o migrar según el costo.

## Canonical path to reuse (Art. 6)

El registry es la única fuente de identidad: `shared/personas/registry.py`
entrada `"frugivoro"` (aliases `["frugivoro", "frugi", "frugívoro"]`,
`display_name="Frugívoro"`, bot_user_id `1521273256236023989`). Slice mínimo:

1. Agregar/reemplazar alias `fruggy` en el registry (y decidir si `frugi` se
   queda como alias legacy o muere — dos aliases activos duplican la
   superficie de addressing).
2. `display_name` → "Fruggy" si el rename es de cara al usuario, + username
   del bot en el Discord Developer Portal (atom de Bernard si pide login).
3. Grep total: `grep -rin "frugi"` — persona DNA, docs, backlog items
   (`addressed-to-sibling-over-suppression.md` menciona "cross-talk @frugi"),
   tests. Un rename a medias deja dos nombres vivos (Art. 6: one source of
   truth per surface).

## The decision that's the owner's

- ¿Rename completo (display_name + username Discord + DNA) o solo el alias
  hablado? El username del bot en Discord es visible para Alex — timing es
  llamada de Bernard.
- ¿`frugi` sobrevive como alias legacy o se mata el mismo día? (Art. 6
  sugiere matarlo; la fricción de que Alex se acostumbre sugiere gracia
  temporal.)

## Status / next step

No arrancado. Desbloquea con un GO de Bernard; el slice del registry es
trivial (una línea + tests de aliases si existen). Relacionado:
[[frugivoro-persona]] (el item padre de la persona).
