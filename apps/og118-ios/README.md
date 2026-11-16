# og118-ios — cliente nativo (tracer bullet)

App de iPhone nativa en SwiftUI que habla el **mismo contrato que ya sirve
producción**: Auth0 PKCE → `POST /chat/stream` (SSE) contra
`og118-api.thankfulmoss-53b8b5c9.eastus2.azurecontainerapps.io`.

Nace porque el PWA en el teléfono no da la experiencia que Bernard quiere
(2026-08-12). El servidor se reusa entero; lo único que se reimplementa es la
capa de UI, porque fi-glass es TypeScript y no cruza a Swift.

## Estado verificado (Art. 2)

| Qué | Cómo se comprobó | Resultado |
|---|---|---|
| Los fuentes compilan | `swiftc -typecheck` contra el SDK de macOS | 0 errores, 0 warnings |
| La lógica del turno **se ejecuta** y hace lo que dice | arnés de `Tests/`, corrido de verdad | 40/40 verde |
| El arnés detecta el bug si vuelve | mutación: quitar la guarda de `fold()` | rojo, "hubo 2" burbujas, exit 1 |
| El JSON que emite Swift **lo acepta el servidor** | `ConversationRecordRequest.model_validate` sobre el JSON real | acepta; id válido; `author` preservado |
| `project.yml` es válido | `xcodegen generate` | genera `OG118.xcodeproj` |
| La API de producción responde | `curl /health` (tras cold start) | `200` |
| El cliente Auth0 existe y acepta el callback | `GET /authorize` con el `client_id` y el `redirect_uri` reales | `302` al login, sin *Unknown client* ni *Callback URL mismatch* |
| **Compila para iOS** | `xcodebuild -sdk iphonesimulator` con Xcode 26.6 | `** BUILD SUCCEEDED **` |
| **Arranca y se ve** | instalada y lanzada en un simulador iPhone 16 Pro / iOS 26.5 | login renderiza con la identidad de og118 |
| **Corre en el iPhone físico** | instalada el 2026-10-10 y el 2026-11-01 | hoy NO está instalada: el perfil gratis caducó el 2026-11-07 |
| **La app real y sus unit tests** | `xcodebuild test -only-testing:OG118UnitTests` en simulador, también en CI (`pr-gate.yml`) | 13 pasan (2026-11-15) |

El estado vivo, incidente por incidente, está en `.claude/backlog/og118-ios-tracer.md`. Lo que este README
no puede afirmar: la vuelta completa en el teléfono con el código del 2026-11-15 está sin verificar.

## Correrla en el simulador

```bash
export DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer
cd apps/og118-ios && xcodegen generate
xcodebuild -project OG118.xcodeproj -scheme OG118 -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/og118-dd build
SIM=$(xcrun simctl create og118-test com.apple.CoreSimulator.SimDeviceType.iPhone-16-Pro \
  com.apple.CoreSimulator.SimRuntime.iOS-26-5)
xcrun simctl boot "$SIM"
xcrun simctl install "$SIM" /tmp/og118-dd/Build/Products/Debug-iphonesimulator/og118.app
xcrun simctl launch "$SIM" com.bernard.og118
xcrun simctl io "$SIM" screenshot /tmp/og118.png
```

El simulador **no necesita cuenta de desarrollador ni firma** (`Sign to Run
Locally`). Los $99 y el Modo desarrollador sólo hacen falta para el teléfono
físico.

## Correr el arnés sin Xcode

`ChatModel` recibe su stream inyectado, así que la lógica del turno —fold,
autoría, cancelación, historial— se ejecuta sin red, sin UI y sin Xcode:

```bash
cd apps/og118-ios
SDK=$(xcrun --show-sdk-path --sdk macosx)
# -DDEBUG porque la sonda de desarrollo vive tras esa bandera: no viaja en el
# binario que se instala, pero el arnés sí la cubre.
swiftc -DDEBUG -sdk "$SDK" -target arm64-apple-macos14.0 -o /tmp/og118-harness \
  Sources/Models/*.swift Sources/Services/*.swift Sources/Services/Generated/*.swift \
  Sources/Services/Voice/*.swift Tests/ChatModelHarness.swift
/tmp/og118-harness
```

No es XCTest a propósito: XCTest necesita Xcode, y el punto del arnés es
verificar **mientras Xcode no está**. Cuando Xcode entre, se convierte en un
test target sin reescribir los asserts.

### Cruzar la frontera de lenguaje

Los asserts de Swift no prueban que el **servidor** acepte lo que Swift emite —
ese borde es donde estas cosas truenan. El JSON del record se valida contra el
Pydantic real:

```bash
cd apps/og118/server
.venv/bin/python -c "
import json, sys; sys.path.insert(0, '.')
from app import ConversationRecordRequest
ConversationRecordRequest.model_validate(json.load(open('/tmp/record.json')))
print('el servidor acepta el JSON de Swift')"
```

## Persistencia

La fuente de verdad es el servidor: `PUT /conversations/{id}` al cerrar cada turno y `GET` al arrancar. El id
de conversación se guarda en `UserDefaults` y **es también el `session_id`** que viaja en `/chat/stream`.

Desde el 2026-11-15 el teléfono guarda una copia (`Services/CacheLocal.swift`, en Application Support): el
último record de cada hilo y la lista se pintan al instante y se leen sin red, pero no se puede mandar sobre un
hilo que el servidor no confirmó. Un guardado que no llega queda marcado como pendiente y se vuelve a subir. El
borrador de texto de cada conversación sobrevive al cierre de la app. Cerrar sesión borra todo eso.

Título, preview y truncado replican `free-intelligence-core` al carácter
(tope 60 y 120, colapso de espacios, elipsis) para que el mismo hilo se lea
igual en la web y en el teléfono.

`GET /conversations` alimenta la hoja para cambiar de hilo; los archivados se
filtran del listado.

## Construir

```bash
brew install xcodegen          # ya instalado en esta máquina
cd apps/og118-ios
grep '^AUTH0_CLIENT_ID=' ~/.secrets/og118-ios-auth0.txt \
  | sed 's/^AUTH0_CLIENT_ID=/OG118_AUTH0_CLIENT_ID = /' > Config.xcconfig
xcodegen generate              # genera OG118.xcodeproj (no se commitea)
open OG118.xcodeproj
```

`Config.xcconfig` está en `.gitignore`: el repo guarda el **mapa** a
`~/.secrets/og118-ios-auth0.txt`, no el valor.

Requiere **Xcode** (no basta con las CommandLineTools). Instalación sin App
Store:

```bash
xcodes install 26.6
```

## Identidad: el cliente Native YA existía

Bernard registró la app nativa en Auth0 el **2026-07-10**, la misma noche del
primer scaffold de SwiftUI. Su config vive en `~/.secrets/og118-ios-auth0.txt`:
bundle id `com.bernard.og118`, callback
`com.bernard.og118://dev-1r4daup7ofj7q6gn.us.auth0.com/ios/com.bernard.og118/callback`.
El código está alineado a **ese** cliente — no se creó uno nuevo (Art. 6).

El `client_id` del web (`9FxTpqyKHP9xw9u4fO6T3Ob7acAarEQj`) es de tipo SPA y no
sirve aquí: Auth0 no acepta callbacks de esquema propio en clientes SPA.

## Red y turno

Toda petición sale por `Services/Transporte.swift`. Un 401 refresca el token una vez y repite; si el servidor
rechaza también el nuevo, la sesión se cierra y el login dice por qué. Cada petición lleva
`X-OG118-Client: ios/<versión>(<build>)`.

El turno pide `survive_disconnect`: si la conexión se cae con el turno ya abierto (cambiar de app, perder
señal), el servidor lo termina y la respuesta llega por el record; el teléfono la espera en vez de revertir.
Parar a mano llama a `POST /chat/cancel`. 45 s sin una sola línea del servidor cortan el stream.

## Firma y distribución

El equipo de firma vive **sólo** en `Config.xcconfig` (ignorado por git). `project.yml` no lo fija: un valor a
nivel de target le gana al xcconfig.

Con el Apple ID gratis el perfil dura 7 días y la app deja de abrir; pasó el 17-oct, el 31-oct y el 7-nov de 2026.
La salida es TestFlight con la membresía de pago (paso 1b del tracker), que todavía no existe. Mientras tanto,
instalar por cable exige el teléfono desbloqueado y volver a confiar en el desarrollador si la app se borró.

## Anatomía

**Paridad con la web móvil (2026-10-10):** la UI calca app.og118.ai a 390pt —
sin barra de encabezado, burbujas de ancho completo con radio 14, píldora
«Powered by» desde `trace.model`, composer de una fila con el riel detrás del
toggle, y el drawer lateral con «+ Nuevo chat» y «Salir · correo». Toda medida
nueva entró al contrato de tokens, no a Swift a mano. El riel es «+ · selector ·
llamar» como la web: adjuntar imágenes y la llamada por voz (Resonance, puerto
1:1 de fi-glass en `ResonanceCall.swift`; ver `.claude/backlog/og118-ios-tracer.md`).

| Archivo | Responsabilidad |
|---|---|
| `Config.swift` | hosts, audience, scheme del callback |
| `Auth.swift` | Auth0 PKCE con `ASWebAuthenticationSession` + refresh |
| `Og118Client.swift` | `POST /chat/stream` y el parser de frames SSE |
| `StreamEvent.swift` | frames nativos de fi-runner → eventos tipados |
| `ChatModel.swift` | un turno vivo, el fold a transcript y la persistencia |
| `ConversationRecord.swift` | el record de `/conversations` + las derivaciones de core |
| `ContentView.swift` | login o conversación: botón flotante (sin barra), marca de agua, hilo, composer y el drawer |
| `ConversationsDrawer.swift` | el sidebar de app.og118.ai como panel lateral de 280pt (swipe desde el borde para abrir) |
| `ShellChrome.swift` | `MenuButton` (`.fi-aws-toggle`) y `Watermark` (`watermark-og118.svg`) |
| `Theme.swift` | helpers y composición; los VALORES vienen de `Generated/Theme.generated.swift`, derivado del contrato `glass-chat-tokens.json` |

El parser corta por línea en blanco y toma las líneas `data:`, igual que
`useOg118Agent.ts`. El `session_id` lo manda el cliente y es estable por sesión
— el backend corre sin estado y la continuidad la da el `history` que se
reenvía, tal como en el web.
