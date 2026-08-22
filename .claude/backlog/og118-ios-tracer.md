# OG118-IOS-1 — cliente nativo de iPhone (tracer bullet)

Status: In progress — Apple gate LEVANTADO 2026-08-22; falta la primera vuelta de chat real
Proposed: 2026-08-12 by Bernard ("me harta el multiplatform no nativo")

## Qué es

Una app nativa de iPhone para og118, en SwiftUI, contra el mismo servidor que ya
sirve producción. Nace de que el PWA no le funciona en el teléfono.

Vive en `apps/og118-ios/`. El README de esa carpeta tiene la anatomía y el estado
verificado; esto es el breadcrumb del bloqueo externo.

## Camino canónico a reusar (Art. 6)

El **servidor se reusa entero** — `POST /chat/stream` (SSE), `/conversations`,
`/projects`, `/elements`, `/stt`, `/tts`. El parser de frames replica la
semántica de `apps/og118/web/lib/useOg118Agent.ts`, que es la SSOT del contrato.

**fi-glass NO cruza a Swift.** Toda la anatomía del chat es TypeScript, así que
la UI se reimplementa y queda como segunda superficie a mantener en sync. Ese es
el costo real y es una decisión tomada por el dueño, no un descuido.

## Estado / siguiente paso

**El bloqueo de Apple ya no existe** (verificado 2026-08-22): Xcode vive en
`/Applications/Xcode-26.6.0.app` y la app **compila para iOS**
(`** BUILD SUCCEEDED **`), **arranca en el simulador** iPhone 16 Pro / iOS 26.5 y
**pinta el login con la identidad de og118**. El README de `apps/og118-ios/` es la
tabla de estado viva — este archivo sólo la referencia, no la duplica.

Una arista de la máquina, no del proyecto: `xcode-select` sigue apuntando a
`/Library/Developer/CommandLineTools`, así que un `xcodebuild` pelado falla. Todo
comando de iOS va prefijado con
`export DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer`.

**Lo único que falta es la vuelta completa del tracer bullet**, y sigue
presumiéndose rota hasta que ocurra (Loop Law): login de Auth0 contra el tenant →
`POST /chat/stream` → SSE → respuesta pintada en la pantalla. El átomo humano es
la contraseña de Auth0 en el simulador; todo lo demás —build, install, launch,
screenshot— se maneja desde aquí.

El teléfono físico (cable + Modo desarrollador + los $99) sigue siendo un paso
posterior y aparte: el simulador **no necesita cuenta de desarrollador ni firma**.

### Lo que ya no aplica (histórico)

El bloqueo de la cuenta `bernarduriza@icloud.com` y la solicitud de recuperación
del 2026-08-09 se resolvieron en plazo. El cliente Native de Auth0 ya existía
desde el 2026-07-10 (config en `~/.secrets/og118-ios-auth0.txt`, `302` verificado).
La corrupción del registro local de la App Store
(`Data decryption failed. status = -4308`) es **deuda independiente** y no bloquea
nada: Xcode se instaló con `xcodes`, sin la Store.

## La decisión que es del dueño

Si la app pasa de tracer bullet a algo que se usa, hay que decidir la cuenta de
Apple Developer ($99/año): sin ella la app recaduca cada 7 días en el teléfono.
No bloquea nada para empezar.
