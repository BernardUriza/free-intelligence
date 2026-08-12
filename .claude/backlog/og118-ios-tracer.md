# OG118-IOS-1 — cliente nativo de iPhone (tracer bullet)

Status: In progress
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

Verificado hoy: `swiftc -typecheck` limpio (0 errores), `xcodegen generate` crea
el proyecto, y la API de producción responde `200` en `/health`.
**Nunca se ha ejecutado en un teléfono** — hasta entonces se presume roto.

Bloqueado por dos cosas, ninguna de código:

### 1. Xcode no instalado — cuenta de Apple en recuperación

- La cuenta `bernarduriza@icloud.com` está **bloqueada por Apple** desde antes
  del 2026-08-12. Mensaje literal de `xcodes`: *"This Apple Account has been
  locked for security reasons."*
- Hay una **solicitud de recuperación abierta desde el 2026-08-09 17:10:15 CDT**;
  Apple la libera el **2026-08-12 17:10:15 CDT**. Correo de Apple confirmándolo:
  foto en el Discord `#general` de Bernard, 12:27 del 2026-08-12.
- **Nadie debe tocar el link "cancelar la recuperación"** de ese correo ni abrir
  una solicitud nueva: reinicia el plazo de tres días.
- Apple avisa por SMS o llamada al `+52 33 2477 6734`. **Los SMS de Apple no
  entran en esa línea** (comprobado dos veces); **la llamada sí funciona** — en
  `iforgot.apple.com`, "Did not get a verification code?" → "Get a phone call".
- Instalar sin App Store: `xcodes install 26.6` (binario ya en
  `/opt/homebrew/bin/xcodes`). La Store en sí sigue rota aparte, ver abajo.

### 2. Falta un cliente Native en Auth0

El `client_id` del web es SPA y no acepta callbacks de esquema propio. Registrar
una app **Native** en `dev-1r4daup7ofj7q6gn.us.auth0.com`, callback
`og118://dev-1r4daup7ofj7q6gn.us.auth0.com/ios/ai.og118.app/callback`, y pasar el
id por la build setting `OG118_AUTH0_CLIENT_ID`.

## Deuda aparte: el registro local de la App Store está corrupto

Independiente del bloqueo de la cuenta. El App Store no puede descifrar su propio
registro de cuenta (`_NSInlineData: Data decryption failed. status = -4308`,
`ACAccount: Failed to decrypt account property. key = accountFlags`, ~105 veces
por interacción), y por eso sus diálogos de verificación **no hacen nada al dar
clic, sin mostrar error alguno**. Limpiar cachés y cookies **no lo arregla**
(probado 2026-08-12; respaldo en `~/.appstore-backup-20260812-115402`). La
reparación pendiente es Sign Out → Sign In desde el menú **Store**, cuando la
cuenta esté desbloqueada.

## La decisión que es del dueño

Si la app pasa de tracer bullet a algo que se usa, hay que decidir la cuenta de
Apple Developer ($99/año): sin ella la app recaduca cada 7 días en el teléfono.
No bloquea nada para empezar.
