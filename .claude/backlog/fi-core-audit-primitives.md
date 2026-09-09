# fi-core: primitivas de auditoría — seudónimo con llave que rota y evento con hash, para que el segundo consumidor no las reescriba

Status: Done — fi-core 0.30.0 (free-intelligence PR #465, 2026-09-08); el repoint de discord-bot `audit.py` es de Alex (issue #54)
Proposed: 2026-09-08 by Bernard (merge del PR #68 de discord-bot, issue #54)

## What it is

discord-bot #54 pidió portar **la forma** del patrón `DomainEvent` de
`fi_core.cognitive.events` — nombre estable, campos tipados, `audit_hash` con
`sha256_payload` — a structlog + Log Analytics, sin construir un event store. El
PR #68 lo hizo bien, y al hacerlo escribió en `khimeras_shared/audit.py`
(256 líneas) dos primitivas que **no tienen nada de discord-bot**:

1. **`pseudonymous_user(user_id, *, now)`** — HMAC-SHA256 con llave de entorno,
   **`None` sin llave** (nunca cae a un sha256 pelón: el espacio de IDs de
   Discord es chico y conocido, un hash sin llave es reversible), **rota cada
   mes** con el periodo visible al frente (`2026-09:a3f91c…`) para que no se
   pueda agrupar entre meses ni queriendo. Dos condiciones que Alex hizo parte
   de la decisión, con el test que reprueba un sha256 pelón
   (`test_dos_llaves_distintas_dan_codigos_distintos`).
2. **`_emit(event, **fields)`** — el payload con el nombre del evento adentro
   (si no, un `absent` se reetiqueta como `classified` sin mover el hash),
   `audit_hash = sha256_payload(payload)`, y **se traga cualquier falla**: el
   registro nunca cuesta el turno.

El segundo consumidor ya existe: og118 y AIRE corren personas con la misma
`ClinicalDomain`, y el día que registren un veredicto sobre una persona real
van a necesitar exactamente estas dos cosas — y si no están en el framework,
las van a reescribir con una diferencia chica (una llave eterna, un hash sin el
nombre del evento) que nadie va a notar hasta que un log se filtre. Es
[[framework-canary-consumer]] al pie de la letra: el canary (discord-bot) ya
probó la forma; sube al framework.

`DomainEvent` tal cual no sirve para esto: está pensado para un event store
(`consultation_id`, `EventMetadata` con `user_id` en claro) — justo el campo que
la primitiva 1 existe para no guardar.

## Canonical path to reuse (Art. 6)

`fi_core.cognitive.events.sha256_payload` ya existe; `hmac`/`hashlib` son
stdlib. Propuesta de superficie, en `fi_core/cognitive/audit.py`:

```python
def pseudonym(subject: str, *, key: str | None, period: str) -> str | None
def audit_period(now: datetime | None = None) -> str          # "2026-09", UTC
def audited(event: str, **fields) -> dict[str, Any]           # fields + event + audit_hash
```

Sin structlog adentro (fi-core no impone logger): el consumidor hace
`log.info(**audited("crisis_band_classified", band=..., user_id=pseudonym(...)))`.
La lectura de la llave del entorno y el "trágate todo" quedan del lado del
consumidor, que es quien sabe qué es fail-safe en su camino de turno.

## The decision that's the owner's

- Si vive en `fi_core.cognitive` (junto a `events.py`, de donde viene la
  disciplina) o en un `fi_core.audit` sin dependencia del dominio clínico —
  la primitiva no sabe de medicina.
- El largo del digest (discord-bot recorta a 16 hex = 64 bits: suficiente para
  que dos personas de un servidor no choquen; la protección la da la llave).
  Parámetro con ese default.

## Status / next step

**Hecho en fi-core 0.30.0** (free-intelligence PR #465, commit `40cd322a`,
2026-09-08). `fi_core/audit.py`, stdlib puro: `pseudonym(subject, *, key,
period, digest_chars=16)`, `audit_period(now=None)`, `audited(event,
**fields)`. Las dos decisiones que la tarjeta dejaba al dueño:

- **Vive en `fi_core.audit`, no en `fi_core.cognitive`**: la primitiva no sabe
  de medicina. `sha256_payload` se mudó ahí (una sola definición);
  `fi_core.cognitive.events` lo importa y `fi_core.cognitive.sha256_payload`
  sigue resolviendo a la misma función.
- **El largo del digest es parámetro con default 16** (el del canary).

Sin structlog y sin leer el entorno: el consumidor lee la llave, decide el
fail-safe y hace `log.info(**audited("crisis_band_classified", ...))`.
`audited` rechaza un `audit_hash` pasado desde afuera. **Byte-compatible con
`pseudonymous_user` de discord-bot**: el vector `2026-09:df068944ec77436d`
(llave de prueba, sujeto de prueba, septiembre) se calculó con la
implementación de discord-bot v4.38.15 y está pineado, así los códigos de
septiembre que ya están en Log Analytics siguen siendo comparables tras el
cambio. 17 tests en `tests/test_audit.py`, incluido el que un sha256 pelón
reprueba.

**Lo que falta:** discord-bot `khimeras_shared/audit.py` se queda con los dos
emisores, la lectura de `CRISIS_AUDIT_KEY` y el trágate-todo; `pseudonymous_user`,
`audit_period` y `_audit_hash` mueren con grep.

**Estado del consumidor (2026-09-08):** discord-bot subió el pin a 0.30.0
(`1078ea1`) sin tocar `khimeras_shared/audit.py` — Bernard se lo dejó a Alex
en el issue #54 ("yo no toco `audit.py`"). El repoint a `fi_core.audit` queda
como su decisión; mientras, las dos implementaciones son byte-compatibles.
