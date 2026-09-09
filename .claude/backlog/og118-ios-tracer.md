# OG118-IOS-1 — cliente nativo de iPhone (tracer bullet)

Status: **In progress** (re-verificado EN VIVO 2026-09-09) — compila, instala, arranca y pinta el login en un simulador recién creado. Sigue faltando la vuelta completa del tracer; el átomo es la contraseña de Auth0
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

## Verificación en vivo — 2026-09-09

No una relectura del archivo: se corrió. `xcodegen generate` → `xcodebuild
-scheme OG118 -destination "id=<sim>" build` → **BUILD SUCCEEDED** → `simctl
install` → `simctl launch` → screenshot: la pantalla de login de og118.ai con su
botón "Iniciar sesión". Xcode 26.6 en `/Applications/Xcode-26.6.0.app`.

**La trampa de entorno, que es el hallazgo de hoy y no estaba escrita en ningún
lado:** esta Mac tiene el runtime de iOS 26.5 instalado pero **cero dispositivos
de simulador creados** — `xcrun simctl list devices available | grep iPhone` no
devuelve NADA. Un `xcodebuild -destination 'platform=iOS Simulator,name=iPhone
15'` falla ahí con un error de destino que se lee como toolchain rota, y no lo
es. Se crea uno y ya:

```bash
export DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer
xcrun simctl create "og118-verify" \
  com.apple.CoreSimulator.SimDeviceType.iPhone-17 \
  com.apple.CoreSimulator.SimRuntime.iOS-26-5
xcrun simctl boot <UDID>
```

`xcode-select` apunta a las CommandLineTools, así que **`DEVELOPER_DIR` no es
opcional** en ninguno de los comandos de arriba.

**Dónde se detuvo, y por qué ahí:** la app está corriendo en el simulador con el
login en pantalla. Tocar "Iniciar sesión" abre la hoja de Auth0 y pide la
contraseña de Bernard — ése es el átomo, y es suyo. Todo lo anterior se manejó
desde la sesión.
