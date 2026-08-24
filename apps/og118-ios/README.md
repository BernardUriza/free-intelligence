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
| **Corre en el iPhone físico** | **no probado** | falta conectar el teléfono por cable |

Ya arranca y se ve como og118, pero **nadie ha completado todavía una vuelta de
chat real** — login de Auth0 contra el tenant, SSE del servidor, respuesta
pintada. Eso sigue presumiéndose roto hasta que ocurra.

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

El transcript vive en el servidor, no en el teléfono: `PUT /conversations/{id}`
al cerrar cada turno y `GET` al arrancar. El id de conversación se guarda en
`UserDefaults` y **es también el `session_id`** que viaja en `/chat/stream` —
así lo manda el contrato de core (*"Stable id. Doubles as the backend session_id
for the same thread"*), y por eso no se genera un uuid aparte por lanzamiento.

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

## Lo que falta para la primera corrida

Xcode ya no bloquea nada (`/Applications/Xcode-26.6.0.app`, verificado
2026-08-22): la app compila para iOS, se instala y arranca en el simulador.

1. **La vuelta completa del tracer bullet en el simulador**: login de Auth0 →
   `POST /chat/stream` → SSE → respuesta pintada. El único átomo humano es la
   contraseña de Auth0; build, install, launch y screenshot se manejan desde
   aquí. Hasta que ocurra, se presume rota (Loop Law).
2. **El teléfono físico** es un paso posterior y aparte: cable, Modo
   desarrollador y firma con Apple ID gratis (la app recaduca a los 7 días; el
   año completo son los $99). El simulador no necesita nada de eso.

## Anatomía

| Archivo | Responsabilidad |
|---|---|
| `Config.swift` | hosts, audience, scheme del callback |
| `Auth.swift` | Auth0 PKCE con `ASWebAuthenticationSession` + refresh |
| `Og118Client.swift` | `POST /chat/stream` y el parser de frames SSE |
| `StreamEvent.swift` | frames nativos de fi-runner → eventos tipados |
| `ChatModel.swift` | un turno vivo, el fold a transcript y la persistencia |
| `ConversationRecord.swift` | el record de `/conversations` + las derivaciones de core |
| `ContentView.swift` | login, transcript, composer y hoja de conversaciones |
| `Theme.swift` | los tokens de og118 (`--og-bg-deep`, `--og-accent`) traducidos a SwiftUI |

El parser corta por línea en blanco y toma las líneas `data:`, igual que
`useOg118Agent.ts`. El `session_id` lo manda el cliente y es estable por sesión
— el backend corre sin estado y la continuidad la da el `history` que se
reenvía, tal como en el web.
