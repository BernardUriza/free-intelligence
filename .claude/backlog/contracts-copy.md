# CONTRACTS-COPY-1 — las frases que el substrato posee se declaran UNA vez

Status: **Done 2026-10-17** — `contracts/copy.json` → `copy.generated.ts` + `Copy.generated.swift`, con `check:` en el PR gate
Proposed: 2026-10-17 by Claude (candidato surgido en CONTRACTS-BEHAVIOR-1; ejecutado bajo /ultra-lord)

## Qué es

Seis frases que core dice en sus reducers y derivaciones y que cada superficie
repetía a mano: el título por default (`New chat`), el aviso de `deferred`, el
aviso de su tope, y las tres fallas (transporte, timeout, turno vacío). El aviso
de `deferred` se transcribió a mano a Swift el mismo día que nació en core — la
prueba de que una frase que vive dos veces diverge en cuanto alguien la retoca.

Ahora viven en `apps/packages/free-intelligence-core/contracts/copy.json` y los
dos lenguajes derivan: `COPY` en TS (exportado de core, consumido por
`helpers.ts` y `conversation-state.ts`) y `enum Copy` en Swift (consumido por
`ConversationRecord` y `ChatModel`). Un `{param}` es un hueco que la superficie
rellena (`turnDeferredNotice(author)`); el generador valida que cada param
declarado aparezca en el texto y viceversa.

## Camino canónico (Art. 6)

El mismo riel que tokens y schemas: contrato a mano → generadores
(`gen:copy`, `gen:swift-copy`) → `check:copy` + `check:swift-copy` en el paso
"Contracts" del PR gate (son diez checks ya).

**Fuera de alcance a propósito:** el copy de botones y chrome de fi-glass
(`newChatLabel`, "Reintentar", etc.) es de la anatomía, no del substrato; vive
como props con default en fi-glass.

## Lo que cambió de paso

iOS declaraba el turno vacío con un mensaje técnico ("Llegaron N frames pero
ninguno traía texto"). Ahora el usuario ve la frase del contrato (`turnEmpty`)
y el conteo de frames va a la bitácora del turno, que es donde un diagnóstico
pertenece.

## Estado / siguiente paso

Entregado (rama `bernarduriza/contracts-copy`, core 1.10.0). Nada abierto.
