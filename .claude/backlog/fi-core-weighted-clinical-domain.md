# fi-core: ClinicalDomain con señales PESADAS y bilingües — discord-bot consume SOLO el clinical domain

Status: Proposed
Proposed: 2026-08-28 by Bernard (Discord: *"creo que deberíamos mejorar free
intelligence para que discordbot solo use el clinical domain"*, sobre el cierre
del #52 de Alex — mensaje 1542680953602707526 en Khimeras #general)

## What it is

Hoy `fi_core.cognitive.ClinicalDomain` son cinco frozensets PLANOS. El cierre
del #52 de discord-bot (Alex, 2026-08-27) es la lista de lo que esa forma no
puede sostener — y por eso el repo mantiene un corpus clínico paralelo (5
regex + `_SIGNAL_GROUPS` con pesos) unido al PSYCHIATRY de fi-core: dos fuentes
de verdad para la superficie más delicada que existe (crisis).

La mejora: `ClinicalDomain` gana **signal groups pesados**:
`signal_groups: tuple[SignalGroup, ...]` con (name, patterns regex-capaces,
weight, category, language). Los sets planos quedan por compat (CARDIOLOGY
intacta); el clasificador suma pesos → `band_for_gravity` (la tesis de bandas
del #53 de Alex, promovida AL framework). PSYCHIATRY absorbe:

1. Los 5 regex del repo (27 de 29 disparos reales se pierden sin ellos).
2. `_SIGNAL_GROUPS` CON sus pesos ("CPTSD + sertralina" e "internamiento
   psiquiátrico" hoy no cruzarían un umbral booleano).
3. Equivalentes en INGLÉS (PSYCHIATRY trae cero; falta "ya no puedo más" — la
   frase con la que Valentis contestó por primera vez).
4. Listas con peso propio para las 4 categorías que fi-core NOMBRA y nadie
   detecta: abuso, aislamiento social, duelo reciente, uso de sustancias.

Estado final: `vulnerability.py` de discord-bot colapsa a
`PSYCHIATRY.urgency_classifier()` y su corpus local MUERE con grep
([[migrations-end-with-deletion]]); ALICE, og118 y toda persona futura heredan
el mismo motor clínico.

## Canonical path to reuse (Art. 6)

`fi_core/cognitive/domains.py` (ClinicalDomain + PSYCHIATRY) y
`UrgencyClassifier`/`band_for_gravity` ya existen — esto EXTIENDE, no reinventa.
El contenido pesado viene del corpus vivo de discord-bot
(`khimeras_shared/behavior/vulnerability.py`), no se redacta de cero. Es
[[framework-first-canary]]: el canary (discord-bot) empuja la capacidad al
framework.

## The decision that's the owner's

- El reparto con Alex: su trilogía (#52/#53 + el issue que ofreció abrir) es la
  fase de CONSUMO en discord-bot; la fase fi-core es de este repo. Su decisión
  del #52 (unión, no reemplazo) fue correcta bajo el fi-core de hoy — esta card
  es lo que la hace colapsar a un import, no una re-litigación.
- Pesos y umbrales por banda: los valores clínicos los valida Alex (es su
  dominio), no se inventan aquí.

## Status / next step

No construido. Next: diseñar `SignalGroup` + el clasificador pesado en
`fi_core.cognitive`, migrar el corpus de discord-bot con pesos, publicar
fi-core 0.26.x, y abrir la fase de consumo como continuación de la trilogía de
Alex.
