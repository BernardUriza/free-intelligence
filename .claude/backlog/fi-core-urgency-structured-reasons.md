# fi-core: `GravityScore.reasons` estructurados — el veredicto explica con NOMBRES de grupo, nunca con la frase

Status: Proposed
Proposed: 2026-09-08 by Bernard (sesión discord-bot, verificando el deploy del
PR #68 de Alex — el registro auditable del veredicto de banda, issue #54)

## What it is

`UrgencyClassifier` explica su veredicto con **strings de prosa que llevan la
frase emparejada adentro**. Salida real de fi-core 0.29.x
(`fi_core/cognitive/urgency.py`, `base_gravity` / `modifiers` / `classify`):

```
symptom 'me quiero morir' → gravity 9
critical pattern 'quiero morir' detected → override CRITICAL
comorbidity 'intento de suicidio previo' (+0.5)
```

Ese formato era correcto para el flujo clínico de origen (FLOW.md: un médico
lee el porqué en pantalla). En un **log que se guarda años**, no: discord-bot
#54 decidió — decisión 1 de Alex, explícita — que el evento de auditoría
`crisis_band_classified` explica el veredicto con los **nombres de los grupos**
(`explicit_ideation`, `at_the_limit`) y NUNCA con las frases canónicas, porque
*"ésas se parecen demasiado al texto original para un log que se guarda años"*.
El PR #68 lo cumplió en `signals` (vía `ScoredSignals.matched`)… y lo rompió sin
querer en `reasons`, porque `reasons` viene de fi-core y trae la frase. El primer
evento real en producción (2026-09-09 00:11 UTC, persona-gateway rev 201) salió
así:

```
"reasons": ["comorbidity 'abuso' (+0.5)", "comorbidity 'duelo reciente' (+0.5)",
            "comorbidity 'intento de suicidio previo' (+0.5)"]
```

Etiquetas clínicas de una persona en Log Analytics, y en un turno grave irían
las frases del vocabulario (`critical pattern 'quiero morir'`). El consumidor no
puede arreglarlo sin parsear prosa — que es exactamente lo que
[[alex-issues-fi-core-via-discord-bot]] prohíbe: un bug de fi-core se arregla
río arriba.

La mejora: `reasons` deja de ser `tuple[str, ...]` y pasa a ser una tupla de
**razones tipadas**:

```python
@dataclass(frozen=True)
class UrgencyReason:
    kind: Literal["symptom", "critical_pattern", "comorbidity", "age", "pregnancy"]
    key: str          # NOMBRE estable: el grupo de señal / la condición canónica, no la frase del mensaje
    weight: float     # +0.5, 9, 10…
    def render(self) -> str: ...   # la prosa de hoy, para UIs y tests que la leen
```

Con `key` = el nombre del `SignalGroup` (o la clave de condición) el consumidor
loguea `kind`+`key`+`weight` y nunca una frase. La prosa sobrevive como
`render()` para quien la muestre en pantalla.

## Canonical path to reuse (Art. 6)

`ScoredSignals.matched` ya devuelve nombres de grupo (0.26.0) — es el mismo
principio, aplicado al otro objeto que explica un veredicto. `GravityScore` es
`frozen` y se construye en un solo lugar (`classify`), así que el cambio es
local a `urgency.py` + los tests que leen `reasons` como string.

## The decision that's the owner's

- **Compat:** `reasons` es API pública de 0.x (discord-bot la lee en
  `crisis_band(...).reasons`, y sus tests centinela comparan strings). Pre-1.0
  no hay shim obligatorio, pero el bump es MINOR con nota de migración, y
  discord-bot sube el pin en el mismo día (patrón #52/#53).
- **Mientras no exista:** Alex decide si `crisis_band_classified` deja de
  loguear `reasons` y se queda sólo con `signals` + `gravity` (hoy `reasons`
  recortado a 3 es su decisión 2). Está planteado en discord-bot #54.

## Status / next step

No construido. Next: `UrgencyReason` en `fi_core.cognitive.urgency`, `classify`
lo emite, `render()` conserva la prosa; CHANGELOG MINOR; discord-bot #54 sube el
pin y `audit.py` loguea `key`/`weight`. Recibo de cierre: el evento en KQL sin
una sola frase del vocabulario.
