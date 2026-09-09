# fi-core: el veredicto de banda carga sus grupos disparados — una llamada, un veredicto, una explicación

Status: Done — fi-core 0.30.0 (free-intelligence PR #465, 2026-09-08); discord-bot collapses to `assess()` pending
Proposed: 2026-09-08 by Bernard (revisión del PR #68 de discord-bot, issue #54)

## What it is

Hoy el consumidor que quiere **la banda** y **por qué** hace dos lecturas
distintas del mismo mensaje:

1. `PSYCHIATRY.urgency_classifier().classify(PatientContext(symptoms=match(msg).symptoms, ...))`
   → la banda (`GravityScore`).
2. `PSYCHIATRY.acute_signals.matched([msg])` → los nombres de grupo que explican.

discord-bot lo dice con todas sus letras en `matched_acute_groups()`
(`khimeras_shared/behavior/vulnerability.py`, PR #68):

> ⚠️ Lectura PARALELA, no el insumo literal de la banda. […] estos grupos leen
> el mismo mensaje con el mismo vocabulario de PSYCHIATRY, así que explican el
> veredicto sin SER el veredicto. **Si algún día divergen, el que manda es el de
> `crisis_band`.**

Y ya divergieron una vez: 0.29.1 (2026-09-07) cerró *"same sentence, two
verdicts"* — `match()` negaba `"me quiero suicidar"` mientras el regex agudo
disparaba `explicit_ideation` sobre la misma frase. Se arregló alineando las dos
ventanas de negación, pero la arquitectura que permite que se separen sigue ahí:
son dos motores (`WeightedSignals` regex-pesado y `UrgencyClassifier`
vocabulario-plegado) leyendo el mismo texto por caminos distintos, y el
consumidor pega los resultados con la esperanza de que coincidan. Una auditoría
(#54) que explica un CRITICAL con grupos que otro motor calculó no es una
explicación del veredicto: es una explicación *cercana* al veredicto.

La mejora: `GravityScore` (o un `ClinicalVerdict` que lo envuelva en
`ClinicalDomain`) sale de **una** llamada de dominio —
`PSYCHIATRY.assess(message, history_texts)` — y trae adentro lo que hoy se
recolecta a mano:

```python
@dataclass(frozen=True)
class ClinicalVerdict:
    score: GravityScore              # banda, gravedad, override, reasons tipados (ver la tarjeta hermana)
    acute: ScoredSignals             # matched / denied / excluded del eje agudo
    chronic: ScoredSignals           # ídem del eje crónico (los facts)
```

Así `signals` del evento de auditoría son, por construcción, los del mismo
cómputo que produjo la banda; `denied` y `excluded` — que hoy discord-bot no
loguea porque tendría que hacer una TERCERA lectura — viajan gratis (Alex los
pidió como "señal débil que vale la pena registrar algún día", #55 H2).

## Canonical path to reuse (Art. 6)

Todo existe: `PSYCHIATRY.match()` (0.27.0), `WeightedSignals.score()` (0.26.0),
`urgency_classifier()`, `_GROUP_TO_CONDITION` vive hoy en discord-bot y es la
pieza que sube al dominio (Alex ya avisó en #55 que un grupo crónico que no
esté ahí "suma al score pero no llega a la banda" — ése es el tell de que el
mapa pertenece al framework, no al consumidor). La tarjeta
[[fi-core-weighted-clinical-domain]] planteó `vulnerability.py` colapsando a un
import; ésta es el último tramo de ese colapso.

## The decision that's the owner's

- Si `assess()` vive en `ClinicalDomain` (PSYCHIATRY, CARDIOLOGY…) o si sólo
  PSYCHIATRY lo necesita hoy. Cardiology no tiene ejes de señales.
- Si `_GROUP_TO_CONDITION` sube tal cual (nombre de grupo crónico → condición
  de `high_risk_conditions`) o si `SignalGroup` gana un campo `condition`.

## Status / next step

**Hecho en fi-core 0.30.0** (free-intelligence PR #465, commit `40cd322a`,
2026-09-08). `ClinicalDomain.assess(message, history=()) → ClinicalVerdict(score,
hits, acute, chronic, conditions)` — una lectura, un veredicto, una explicación.
Las dos decisiones que la tarjeta dejaba al dueño, resueltas:

- **Vive en `ClinicalDomain`**, no sólo en PSYCHIATRY: un dominio sin ejes
  (CARDIOLOGY) devuelve `acute=None` / `chronic=None`, honesto en vez de un
  `ScoredSignals` vacío cuyo `crosses` mentiría.
- **`_GROUP_TO_CONDITION` no subió como dict: ya estaba en fi-core como
  `SignalGroup.category`.** Los 8 grupos crónicos con contraparte llevan como
  `category` exactamente la entrada de `high_risk_conditions`; los 4 sin
  contraparte (`named_diagnosis`, `psychiatric_medication`,
  `mental_health_clinician`, `chronic_comorbidity`) llevan una etiqueta que no
  lo es. `ClinicalDomain.chronic_conditions` lo lee de ahí y
  `tests/test_domain_assess.py` lo pinea igual al dict de discord-bot
  v4.38.15, entrada por entrada.

Paridad con el canary, deliberada: el mensaje alimenta síntomas + eje agudo;
la historia alimenta el eje crónico y, vía el mapa, `medical_history`. Una
condición que el mensaje mismo nombra se reporta en `hits.high_risk_conditions`
y no suma. `denied` y `excluded` viajan en los dos ejes sin tercera lectura
(H2 de Alex, #55). 9 tests nuevos.

**Lo que falta:** discord-bot colapsa `crisis_band` + `matched_acute_groups` +
`history_conditions` + `_GROUP_TO_CONDITION` a `PSYCHIATRY.assess()`, con
[[migrations-end-with-deletion]] como definición de hecho (grep → 0).
