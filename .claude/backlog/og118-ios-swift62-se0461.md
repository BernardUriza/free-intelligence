# OG118-IOS-SWIFT62-1 — SE-0461 invierte el aislamiento por default y el decode se sube al main actor

Status: Proposed
Proposed: 2026-08-13 by Claude (investigación con /histerical-search)

## Qué es

`apps/og118-ios` corre en `SWIFT_VERSION 5.9`. Hoy, por SE-0338, una función
`nonisolated async` SALE del actor del llamador: `Og118Client.loadConversation`
decodifica el JSON fuera del main actor y la UI no se bloquea.

**Swift 6.2 / SE-0461 invierte ese default.** Una función `nonisolated async`
deja de salirse y se queda en el actor del llamador; el opt-out explícito pasa a
ser `@concurrent`. Consecuencia concreta: al subir de versión de lenguaje, el
decode del record empieza a correr EN EL MAIN ACTOR sin que nadie toque una sola
línea de este repo.

No es urgente —el decode ronda los 3 ms, medido— pero es exactamente el tipo de
regresión silenciosa que no se ve venir: no hay error de compilación, no hay
warning, sólo hitches que aparecen el día del upgrade.

## Lo que YA está pagado

La migración típica a Swift 6 es sobre todo anotaciones `@MainActor` en clases
`ObservableObject` y conformidad `Sendable`. Este repo ya tiene **10 `@MainActor`**
en sus modelos y servicios, y **cero Combine**. El grueso del trabajo está hecho.

## Qué hacer cuando se toque

1. `SWIFT_STRICT_CONCURRENCY = complete` en `project.yml` y limpiar warnings
   ANTES de cambiar de versión de lenguaje.
2. Marcar `@concurrent` lo que hoy depende de salirse del actor —empezando por
   el decode de `loadConversation`— o mover el decode a un método explícito
   fuera del main actor.
3. Medir antes y después: el arnés no ve hitches de UI, así que esto se verifica
   con Instruments sobre una conversación grande (la de 32 mensajes / 19 812
   caracteres sirve de caso).

## La decisión que es de Bernard

Cuándo subir de versión de lenguaje. No hay razón de producto para hacerlo hoy;
la razón para NO dejarlo indefinido es que el costo crece con cada archivo nuevo.

## Estado / siguiente paso

Sin empezar. El disparador natural es el día que se toque `SWIFT_VERSION`, y este
documento existe para que ese día nadie descubra el problema en producción.

Ver también [[verify-before-assuming]] Rule 20 (una recomendación investigada no
está validada hasta probarla) — aquí la prueba pendiente es medir con Instruments,
no leer la propuesta de evolution.
