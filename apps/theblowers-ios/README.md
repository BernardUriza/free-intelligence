# theblowers-ios — la app nativa personal (shell web)

`theblowers.com` no tiene app de iPhone y no la va a tener: su producto es
contenido sexual generado por usuarios, y la regla 1.1.4 del App Store lo
prohíbe explícitamente. Ésta no pretende serlo — es un **shell nativo privado**
que envuelve el sitio en un `WKWebView`, firmado con la cuenta de Bernard e
instalado por cable. No pasa por App Review porque no se distribuye.

## Qué hace (y qué no)

| Sí | Cómo |
|---|---|
| conserva la sesión al cerrar la app | `WKWebsiteDataStore.default()` — el único store persistente |
| vuelve a la última página que veías | `UltimaPagina` en `UserDefaults`, filtrada por dominio |
| subir fotos y usar la cámara | los `<input type="file">` del sitio invocan el selector de iOS |
| swipe para regresar, pull-to-refresh | `allowsBackForwardNavigationGestures` + `UIRefreshControl` |
| los enlaces externos salen a iOS | `decidePolicyFor` compara el host contra `Sitio.dominios` |
| icono de marca, no la letra genérica de Safari | `TB_favicon2026.png` del propio sitio, aplanado a 1024 sin alfa |
| **login incrustado** | la credencial entra por `Config.xcconfig` -> Info.plist; si el sitio tira la sesion, la app se reautentica sola |
| cortina al mandarla al fondo | el app switcher fotografía la pantalla; `scenePhase != .active` la tapa |

**No** hay push. Que llegue *"tienes un mensaje"* con la app cerrada exige que el
SITIO implemente Push API + Service Worker y empuje desde su backend; envolver la
web no lo inventa. El experimento pendiente es abrir el sitio con Web Inspector y
ver si expone WebSocket/SSE o algún `/messages/unread` que una capa nativa pueda
poller para pintar el badge.

## El login va DENTRO de la app

Bernard no escribe nada en el telefono. La app trae su correo y su password y se
reautentica sola:

1. Al terminar cualquier carga, `AutoLogin.asegurarSesion` pregunta a la pagina
   si hay sesion (busca un enlace `disconnect`/log out). El sitio sirve la
   portada con contenido publico aunque no haya sesion, asi que "cargo bien" NO
   significa "esta autenticado" - hay que preguntarlo.
2. Si contesta `anonimo`, navega a `/en/login`.
3. En la pantalla de login, `AutoLogin.intentar` llena `#connection_form` con el
   setter nativo de `value` (el sitio ignora una asignacion directa) y hace click
   en el submit.
4. Tope de **2 intentos por sesion de app**: un password rechazado no puede
   convertirse en un bucle de reintentos contra su servidor.

La credencial NO esta en el repo, y no depende de que alguien se acuerde de
ignorarla: **`Config.xcconfig` es un symlink**.

```
apps/theblowers-ios/Config.xcconfig -> ~/.secrets/theblowers-ios.xcconfig
```

Git versiona el enlace, y el contenido de un enlace es su RUTA — nunca el archivo
apuntado. Lo que se publica es el mapa; el valor vive en `~/.secrets` (`chmod
600`), fuera de todo repo. Es el mismo principio con el que `og118-ios` inyecta su
client id de Auth0, un paso mas duro: alli un descuido con `git add -f` publicaba
el secreto, aqui no hay secreto que publicar.

**Si `git status` reporta un `typechange` en `Config.xcconfig`**, alguien lo
convirtio en archivo regular con el password adentro. No se commitea: se restaura
el enlace con `ln -sf ~/.secrets/theblowers-ios.xcconfig Config.xcconfig`.

**Lo que esto implica:** cualquiera que abra el telefono desbloqueado entra a la
cuenta sin friccion. Es exactamente lo que pidio; el candado de Face ID sobre la
app es la contramedida obvia y todavia no esta construida.

## Anatomía

| Archivo | Responsabilidad |
|---|---|
| `Sitio.swift` | qué dominios son "adentro" y dónde arranca; `UltimaPagina` |
| `NavegadorDelSitio.swift` | el `WKWebView`, sus delegates y el ruteo interno/externo |
| `TheBlowersApp.swift` | la escena, el fondo negro y la cortina de privacidad |

## Construir e instalar

```bash
export DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer
cd apps/theblowers-ios
ln -sf ~/.secrets/theblowers-ios.xcconfig Config.xcconfig
xcodegen generate
xcodebuild -project TheBlowers.xcodeproj -scheme TheBlowers -sdk iphoneos \
  -destination 'generic/platform=iOS' -derivedDataPath /tmp/tb-dd \
  -allowProvisioningUpdates build
xcrun devicectl device install app --device <UDID> /tmp/tb-dd/Build/Products/Debug-iphoneos/theblowers.app
xcrun devicectl device process launch --device <UDID> com.bernard.theblowers
```

`Config.xcconfig` está en `.gitignore`: el repo guarda el **mapa** al Team ID que
ya usa `og118-ios`, no el valor.

## La maldición de los 7 días

Con el Personal Team gratuito, el perfil de aprovisionamiento **vence a los 7
días** y iOS deja de abrir la app — que es exactamente por lo que og118 había
desaparecido del teléfono el 2026-08-24. También hay un tope de **3 apps** así
por dispositivo; con og118 y ésta van dos. La membresía de $99/año quita las dos
fricciones. Mientras no exista, reinstalar es correr los comandos de arriba.

## Lo que viene después (no construido)

Bernard lo quiere como base para "inteligencia sólo para mí" encima del sitio.
Eso NO existe todavía y no se presume que exista. Cuando se construya, el camino
canónico es el servidor que ya sirve producción (`apps/og118/server`) y el
runtime de agente (`apps/packages/fi-runner`) — no un backend nuevo.
