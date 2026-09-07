# Renombrar Frugi → Fruggy

Status: **Slice 1 DONE** (alias `fruggy` shipped en `40a4fea`, v4.32.45,
2026-08-10; issue #36 CERRADO 2026-08-14) — el resto del rename sigue siendo
decisión de Bernard. Re-verificado 2026-09-07.
Proposed: 2026-07-05 by Bernard

## Re-chequeo 2026-09-07 (auditoría del backlog)

- `gh issue list --state all` → `#36 CLOSED 2026-08-14T22:54:31Z Enséñale a
  Frugívoro su apodo: alias "fruggy"`.
- `shared/personas/registry.py:135` → `aliases=["frugivoro", "frugi",
  "frugívoro", "fruggy"]`, con el comentario del propio commit (*"fruggy" es el
  apodo real de cariño en #general (issue #36)*). `display_name="Frugívoro"`
  sigue (`:129`).
- Lo que sigue FUERA, tal como se decidió al abrir el slice: `display_name`, el
  username del bot en el Discord Developer Portal, `persona_id`/DNA/`token_env`,
  y **146** hits de "frugi" (`grep -rni frugi --include='*.py' --include='*.md'
  . | grep -v .claude/backlog | wc -l`; eran ~129 el 08-10 — creció con la
  documentación nueva, no con código).
- `frugi` sigue vivo como alias legacy. No hay issue abierto para el slice 2.

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

**Slice 1 en curso — issue #36** (`gh issue view 36`), el primer issue de Alex.
Scope decidido el 2026-08-10 al abrirlo, para que sea tamaño-de-arranque:

- **SÍ**: agregar `fruggy` a `aliases` en `registry.py:133` + test positivo +
  test de resistencia. `test_no_two_personas_share_a_role_candidate`
  (`tests/shared/test_registry_insult.py:104`) ya guarda la colisión.
- **NO** (queda para un slice posterior, decisión de Bernard): `display_name`,
  el username del bot en el Discord Developer Portal, el `persona_id`, el DNA,
  el `token_env`, y los ~129 hits de "frugi" en docs/corpus/tests.
- **`frugi` sobrevive** como alias legacy en este slice — matarlo es parte de la
  decisión de rename completo, no del arranque de alguien que no conoce el repo.

Relacionado: [[frugivoro-persona]] (el item padre de la persona).
