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
| `project.yml` es válido | `xcodegen generate` | genera `OG118.xcodeproj` |
| La API de producción responde | `curl /health` (tras cold start) | `200` |
| El cliente Auth0 existe y acepta el callback | `GET /authorize` con el `client_id` y el `redirect_uri` reales | `302` al login, sin *Unknown client* ni *Callback URL mismatch* |
| **Corre en un iPhone** | **no probado** | **requiere Xcode, que no está instalado** |

La última fila es la que importa: **esto no se ha ejecutado nunca**. Hasta que
arranque en el teléfono y complete una vuelta de chat, se presume roto.

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

1. **Xcode instalado.** Bloqueado el 2026-08-12 por la cuenta de Apple en
   recuperación — ver `.claude/backlog/og118-ios-tracer.md`.
2. **Firma con Apple ID gratis.** La app dura 7 días en el teléfono antes de
   recaducar; reinstalar es darle Run otra vez. El año completo son los $99.

## Anatomía

| Archivo | Responsabilidad |
|---|---|
| `Config.swift` | hosts, audience, scheme del callback |
| `Auth.swift` | Auth0 PKCE con `ASWebAuthenticationSession` + refresh |
| `Og118Client.swift` | `POST /chat/stream` y el parser de frames SSE |
| `StreamEvent.swift` | frames nativos de fi-runner → eventos tipados |
| `ChatModel.swift` | un turno vivo + el fold a transcript |
| `ContentView.swift` | login, transcript y composer |

El parser corta por línea en blanco y toma las líneas `data:`, igual que
`useOg118Agent.ts`. El `session_id` lo manda el cliente y es estable por sesión
— el backend corre sin estado y la continuidad la da el `history` que se
reenvía, tal como en el web.
