# OG118-IOS-1 — cliente nativo de iPhone (tracer bullet)

Status: **In progress** (2026-11-16) — og118 0.1.0 está INSTALADA en el iPhone 15 desde TestFlight, sin cable, abre con la sesión iniciada y mandó un turno real. La subida ya es automática (`og118-ios-testflight.yml`, primera corrida verde 12:32) y un vigilante semanal la renueva antes de caducar. Sin verificar en el teléfono: que la respuesta aparezca tras volver de segundo plano, foto, dictado y llamada.
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

**Decidido 2026-10-31 por Bernard: «pagamos 99».** Motivo: la app desapareció del iPhone al caducar el perfil gratis de 7 días. Inscripción con `bernarduriza@icloud.com` en developer.apple.com (Chrome de debug); login y pago son átomos suyos. Al quedar activa: `DEVELOPMENT_TEAM` en `apps/og118-ios/Config.xcconfig` → el Team ID pagado, `xcodegen generate`, rebuild, `devicectl install`. Build con perfil gratis (vence 2026-11-07) lista en `/tmp/og118-dd` mientras tanto.

**Avance 2026-10-31 ~11:40:** login OK (2FA por la notificación en la Mac; llamada y SMS nunca llegaron). Datos personales tomados del archivo de identidad privado. Tipo Individual, contrato aceptado, costo Mex$1749/año. Auto-renovación SÍ y tarjeta guardada ••0749 sin CFDI (decisiones de Bernard). **PAGADO 2026-10-31 12:11** con la Chime virtual (1.er intento rechazado 11:53; Bernard aprobó la alerta SMS de Chime y el reintento pasó; la ••0749 de INVEX y la DiDi estaban bloqueadas). Pedido Apple Store `W1672029496`, Mex$1,749, auto-renovación. Siguiente: esperar el correo de activación a la cuenta iCloud, leer el Team ID nuevo en developer.apple.com/account → `DEVELOPMENT_TEAM` en `Config.xcconfig` → `xcodegen generate` → build → `devicectl install` (iPhone por cable, desbloqueado).

**2026-11-01 14:30 — «sigue sin abrir».** Medido: el iPhone ya trae **iOS 27.0.1** y la Mac Xcode 26.6 (SDK 26.5); compila e instala igual. El perfil gratis local sigue vigente hasta 2026-11-07 e incluye el iPhone (`00008120-000E3D4C0E100032`). La build de `/tmp/og118-dd` se perdió con el reinicio de las 07:50; se rehízo en `generic/platform=iOS` (BUILD SUCCEEDED). Xcode todavía sólo conoce el Personal Team `7L36T9PTFN`: el equipo pagado aún no aparece, y developer.apple.com pide login (átomo de Bernard). El install exige teléfono **desbloqueado** (`kAMDMobileImageMounterDeviceLocked`); compilar contra el id del teléfono también.

**2026-11-01 16:08 — ABRE en el iPhone.** Install OK por red local (el primer intento dio `Connection reset by peer`; el segundo pasó). El launch lo negó iOS: al borrarse la app el 31-oct se borró también la confianza del desarrollador. Se otorgó desde la Mac con **Duplicación del iPhone** + desktop-control (Bluetooth de la Mac encendido con `blueutil -p 1`; el iPhone debe estar BLOQUEADO para que conecte): Ajustes → buscar «VPN» → VPN & Device Management → bernarduriza@icloud.com → Trust → Allow. Launch → pantalla de inicio con el composer. **Sigue el perfil gratis: vence 2026-11-07 14:48 UTC**; antes de esa fecha hay que firmar con el Team ID pagado.

**2026-11-15 20:45 — «otra vez se murió og118 en mi cel».** Medido: el servidor está sano (`/health` 200, réplica viva, suscripción `Enabled`) y su último request real es del 4-nov. La causa es la app nativa: el perfil gratis venció el 2026-11-07 14:48 UTC y nadie firmó con el equipo pagado. **La membresía NO está activa:** developer.apple.com/account (leído 20:44, sesión de `bernarduriza@icloud.com`) dice `Bernard Uriza Orozco (Pending)` y «Purchase your membership. To continue your enrollment, complete your purchase now», quince días después del pedido `W1672029496`. Xcode sólo conoce el Personal Team `7L36T9PTFN`. **El «PAGADO 2026-10-31» de arriba quedó falso al día siguiente:** el pedido `W1672029496`, leído el 15-nov 20:50 en la vista de invitado de la Apple Store, dice «Cancelado. Se canceló este artículo el 01 noviembre 2026 y no se facturó». No hay cargo que reclamar; hay que comprar de nuevo. `developer.apple.com/enroll/purchase` está en «Complete your purchase» (Mex$1749, botón «Continue to payment»), con la inscripción intacta. Parche: build nueva con perfil gratis (creado 2026-11-16 02:36 UTC, **vence 2026-11-23 02:36 UTC**), sin instalar porque el iPhone salía `unavailable` en `devicectl`. Siguiente: iPhone desbloqueado en la misma red → `devicectl install` → confianza por Duplicación del iPhone; y cerrar la inscripción (pagar de nuevo o reclamar el pedido, decisión de Bernard).

**2026-11-15 20:55 — pedido nuevo `W1947292357`.** Bernard autorizó volver a comprar (Mex$1,749, auto-renovación, sin CFDI). Colocado con la Chime virtual como tarjeta nueva (la guardada ••0749 no se usó); al formulario de facturación le faltaba la colonia. Pantalla final: «Gracias: Confirmación del pedido». **Autorizado en la tarjeta, leído en app.chime.com a las 21:02:** «Aos Mexico, Nov 15 2026 8:55 PM, −$94.49», sin alerta SMS. Autorizado todavía no es membresía activa: el del 31-oct también dio número y Apple lo canceló al día siguiente. El iPhone no anuncia Bonjour ni responde ping desde la Mac (última conexión de CoreDevice: 1-nov), así que el install espera a que esté desbloqueado en la misma red o por cable. Verificar el estado en la vista de invitado de la Apple Store y que `(Pending)` desaparezca de developer.apple.com/account (hasta 48 h). Al activarse: Team ID pagado → `DEVELOPMENT_TEAM` en `Config.xcconfig` → `xcodegen generate` → build → `devicectl install`.

## Robustecimiento — 2026-11-15 (plan aprobado por Bernard)

Bernard, tras la tercera muerte por perfil caducado: *«busquen qué más mejorar en la arquitectura, en el
robustecimiento, que sean serios… para que no vuelva a pasar y para que realmente tenga una funcionalidad
real»*. **La meta es el paso 6**: abre og118 en el iPhone cualquier día, sin Mac, sin cable y sin volver a dar
confianza; manda un turno, cambia de app, regresa y la respuesta está ahí; y si algo va a caducar, se entera antes.

| Paso | Qué | Estado (2026-11-15) |
|---|---|---|
| 1a | El equipo de firma vive sólo en `Config.xcconfig`; `Info.plist` reporta versión y build reales | Hecho, PR #651. `project.yml` fijaba `DEVELOPMENT_TEAM` a nivel de target y le ganaba al xcconfig: cambiar el xcconfig no habría cambiado la firma |
| 1b | TestFlight por CI + vigilante semanal de caducidad + evento de renovación | **Hecho, 16-nov** (PR #659). Cuenta activa leída 11:08; Team ID de pago = el mismo `7L36T9PTFN`. Bernard aceptó tres cosas ese día: términos de App Store Connect, términos de TestFlight y términos de la API. App `og118`, id `6835548280`; grupo interno «Bernard». Primera subida a mano desde la Mac (build `2026111601`). La primera corrida del CI falló con «Cloud signing permission error»: firmar en la nube exige una llave de API con rol ADMIN, y la primera era APP_MANAGER. Bernard autorizó la llave ADMIN; la anterior quedó revocada. Segunda corrida verde a las 12:32 (build `202611161830`, `VALID`, expira 2027-02-14). `og118-ios-caducidad.yml` corrió en CI y leyó 89 días; con el umbral forzado a 120 el lector devuelve «renovar» (probado local). Llave en `~/.secrets/appstoreconnect-og118-ci*` y en los secrets `ASC_*` del repo. Evento de renovación anual creado en su calendario para el 16-oct-2027 |
| 2 | Un solo camino de red (`Transporte`): 401 → refresco → reintento → login con motivo; arranque en frío en cargar/guardar/borrar; errores callados a la vista; modelos construidos una vez | Hecho, PR #651 |
| 3 | El turno sobrevive a cambiar de app: `survive_disconnect` + `POST /chat/cancel` en el servidor; el teléfono espera la respuesta del record en vez de revertir y cobrar otra vez; watchdog de 45 s; resincroniza al volver; `UIBackgroundModes: audio` | Hecho, PR #652, desplegado: a las 23:10 del 15-nov `POST /chat/cancel` sin credencial pasó de 404 a 401 en producción. Probado con pruebas (servidor, arnés, simulador); **sin probar** una desconexión real contra producción ni en el teléfono |
| 4 | Caché en disco de hilos y lista, borrador persistente, guardado con reintento y marca de pendiente, cierre de sesión limpio | Hecho, PR #653; con pruebas, sin probar en el teléfono |
| 5 | CI compila la app y corre `OG118UnitTests`; el deploy fija `OG118_AUTH_MODE` y `AUTH0_*`; `/health` da la versión del contrato; el servidor registra `X-OG118-Client` | Hecho en parte, PR #653: el gate compiló la app en CI (Xcode 26.3, 13 pruebas) y producción contestó `/health` con `"schema":"1.2.0"` y `OG118_AUTH_MODE=auth0` a las 23:16 del 15-nov. **Falta**: que la app compare la versión del contrato, y el dominio propio de la API (`api.og118.ai` no resuelve; `Config.swift` sigue apuntando al hostname crudo de Azure) |
| 6 | Prueba en el iPhone real (login, texto, foto, dictado, llamada, cambiar de app >30 s) | **En parte, 16-nov 12:01–12:03**, manejando el teléfono por Duplicación del iPhone: instalada desde TestFlight (Bernard aceptó los términos de TestFlight), abrió sin pedir login, turno de texto mandado (en pantalla `HTTP 200` y el frame `open`; en logs `POST /chat/stream 200` a las 12:02:14). Sacada a segundo plano 50 s: a las 12:02:32 el teléfono hizo `GET 404` + `PUT 200` del hilo, o sea guardó la pregunta al caerse el stream en vez de revertirla. **Sin verificar:** que la respuesta haya aterrizado y se vea al volver; foto, dictado, llamada |

Build de dispositivo con este código: compilado el 15-nov a las 23:17 (`BUILD SUCCEEDED`, perfil gratis, vence
2026-11-23 02:36 UTC), **sin instalar**: `devicectl list devices` daba el iPhone como `unavailable`. Vive en el
scratchpad de la sesión; si se pierde, se recompila con los comandos de «En el teléfono físico».

**16-nov, madrugada.** El puente por cable se intentó y no se instaló nada: primero la Mac no veía el teléfono (el
cable era solo de carga), y con un cable de datos los intentos de las 00:18 a 00:28 fallaron con «The device is
locked». Bernard ordenó parar y que no se instale nada en su teléfono hasta tener la membresía activa y la entrega
por aire. El paso 6 se hace entonces, con el build de TestFlight.

Quién vigila: `~/.local/bin/apple-membresia-vigia`, por el Chrome de trabajo, lee la CUENTA (la verdad) y el
pedido (para cazar una cancelación). Corre con launchd (`com.bernard.apple-membresia-vigia`) a las 9:07, 14:07 y
20:07, avisa en pantalla solo cuando el estado cambia y se da de baja solo al ver la cuenta activa o el pedido
cancelado. Bitácora en `~/Library/Application Support/apple-membresia-vigia/`.

## Aviso de respuesta lista — 2026-11-16 (PR #661)

La primera mejora que Bernard escogió para la app: mandar la pregunta, guardar el teléfono y enterarse solo.

- **Servidor** (`apps/og118/server/push.py`): cada teléfono registra su token por cuenta (`POST /push/devices`);
  al entregar un turno tardío (el local que se quedó sin cliente o el externo que llegó tarde) manda un aviso
  por APNs con el id del hilo. Sin llave no hace nada; un push que falla no pierde la respuesta.
- **App** (`Sources/Services/Avisos.swift`): pide permiso al mandar el primer mensaje; si el turno termina con
  la app en segundo plano pero viva, el aviso es local; tocar cualquiera de los dos abre ese hilo.
- **Llave APNs**: «og118 push», Sandbox & Production, en `~/.secrets/apns-og118*` y en los secrets
  `OG118_APNS_KEY` / `OG118_APNS_KEY_ID`; el deploy la conecta en su propio paso.
- **CI**: el archivo ahora se firma (uno sin firmar pierde los entitlements), el job falla si falta
  `aps-environment` y revoca el certificado de desarrollo que cada corrida obliga a crear.

Verificado el 16-nov: suite del servidor 308 en verde; build `202611161905` subido por CI con «push entitlement
present in the archive» y «development certificates revoked after the run: 1»; el Container App tiene las tres
`OG118_APNS_*`; `POST /push/devices` sin credencial contesta 401; Apple contesta `400 BadDeviceToken` a un token
falso con esta llave, o sea que la llave sí autentica. El primer deploy falló en el paso del worker por un 429 de
Azure y pasó al reintentarlo.

**Prueba en el iPhone, 16-nov 13:31–13:36** (Duplicación del iPhone, build `202611161905` actualizado desde
TestFlight):

- La respuesta del turno de mediodía SÍ estaba en el hilo al reabrir (cuenta hasta 40 y cierre): el turno que
  sobrevive a la desconexión funciona en el teléfono real.
- Al mandar el primer mensaje iOS pidió el permiso de notificaciones; aceptado.
- Logs: `chat turn client=ios/0.1.0(202611161905)` (el arreglo del logger sirve) y `POST /push/devices 200` a las
  13:32:58 (el teléfono registró su token).
- **El aviso NO se vio.** Dos turnos terminaron con la app en segundo plano (13:33:18 y 13:35:02, por el `PUT`
  del guardado) y en la captura continua de pantalla (13:34:51–13:35:35, un cuadro cada ~1.5 s) no apareció
  ningún banner, ni en el teléfono duplicado ni en la Mac.
- Causa probable, corregida: el aviso local se disparaba en un `onChange` de la vista, y SwiftUI no actualiza
  vistas con la escena en segundo plano. Ahora lo dispara el modelo (`ChatModel.alRecibirRespuesta`), también
  para la respuesta que aterriza tarde. **Sin verificar** que con eso ya aparezca; tampoco está descartado que la
  Duplicación del iPhone no muestre banners.
- El camino del push del servidor no se ejercitó: los dos turnos terminaron dentro de la app, no abandonados.

**Lo que la prueba del 16-nov destapó:** la línea `chat turn client=…` no salía en los logs de producción. El
logger `og118` no tenía handler y todo su INFO (también las auditorías de elementos) se perdía; ahora cuelga de
`uvicorn.error`. Y la Duplicación del iPhone se corta cuando Bernard toma el teléfono o regresa a la Mac: solo
sirve mientras él no usa ninguno de los dos.

**Cómo se sube una versión mientras no haya CI** (desde `apps/og118-ios`, con la sesión de Xcode de la Mac):

```bash
xcodebuild archive -project OG118.xcodeproj -scheme OG118 -configuration Release \
  -destination 'generic/platform=iOS' -archivePath "$TMPDIR/OG118.xcarchive" \
  CURRENT_PROJECT_VERSION=<AAAAMMDDNN> -allowProvisioningUpdates
xcodebuild -exportArchive -archivePath "$TMPDIR/OG118.xcarchive" \
  -exportOptionsPlist ExportOptions.plist -exportPath "$TMPDIR/og118-export" -allowProvisioningUpdates
```

El número de build (`CURRENT_PROJECT_VERSION`) tiene que ser mayor que el del build anterior; si no, App Store
Connect rechaza la subida.

Lo que quedó fuera de estos pasos y sigue abierto: un solo dueño del `AVAudioSession` (dictado, llamada y
reproducción lo configuran cada uno por su lado), las imágenes del borrador (sólo el texto sobrevive al cierre)
y el aviso «despertando el servidor» en el POST del chat (el API está prendido 24/7 desde el 28-oct).

Hallazgos de la auditoría que cambiaron el plan: nada vigilaba la caducidad (ni workflow, ni script, ni launchd,
ni cron); el CI sólo compilaba un arnés de macOS; un 401 dejaba al usuario atorado en «Tu sesión expiró» sin
refrescar ni sacar al login; cualquier corte de red borraba la burbuja y «Reintentar» cobraba el turno dos veces;
`RootView` reconstruía todos los modelos en cada cambio de `Auth`; `GET /projects` daba 404 en cada arranque
(bandera apagada) y ese error nunca se mostraba.

## La UI calca la web — 2026-10-10

Por orden de Bernard ("que sea el mismo UI de web"): medido en vivo con
`getComputedStyle` sobre app.og118.ai a 390px y comparado contra screenshots del
simulador. Lo que falta para paridad completa son FUNCIONES, no estilo: adjuntar
(el «+» del riel) y la llamada Resonance. El "Powered by" exigió arreglar un
camino de datos: el teléfono no escribía `trace.model` en sus turnos.

## Adjuntar imágenes en iPhone — 2026-10-10

Paridad con `useComposerImages` de fi-glass: jpeg/png/webp/gif, máximo 4, lo
chico viaja tal cual y lo demás (HEIC de la cámara incluido) se reduce a JPEG
0.85 con lado de 2048 vía ImageIO; techo de 4 MiB de base64. Entradas: Fotos,
Cámara y Archivos (las tres de Safari). Viaja como `images[{media_type,data}]`
en `/chat/stream`, se guarda en el record como `images[{mediaType,data}]`, no se
re-sube en `history`, y el reintento la vuelve a mandar. Probado: arnés (con
fotos reales generadas y un control de que la grande sí rebasa el umbral), el
Pydantic real de `app.py` aceptando el JSON de Swift, y el flujo con clics en el
simulador. Falta: un turno con foto contra el servidor vivo (requiere login).

## Resonance en iPhone — 2026-10-10

**Revisión del hilo principal (mismo día), antes de mergear:** al tocar Llamar en
el simulador la app se CONGELABA. `sample` mostró el hilo principal atorado en
`AVAudioSession.setActive` (el `ResonanceCallModel` es `@MainActor`, así que el
`Task` que abre el micrófono corría ahí). El dictado y la lectura tenían la misma
llamada en el mismo hilo. Arreglo de raíz: `ColaDeAudio` — toda activación de
sesión y `engine.start` en una cola serial, con límite de 8 s que falla con
nombre («El audio del teléfono no respondió…») y cuelga. Los errores de voz
pasaron al aviso sobre el composer: dentro del hilo, la tarjeta de inicio los
tapaba y la falla era muda. El TTS ahora pide `voice: "nova"` como la web.
El HAL del simulador de esta Mac no responde a `setActive`; la vuelta de audio
real sólo se puede probar en el iPhone.

Puerto 1:1 del modo llamada de la web. Lo que se construyó:

| Pieza iOS | Puerto de (web) |
|---|---|
| `Models/ResonanceCall.swift` — máquina, efectos, política de cues, compuerta VAD, analizador, controlador (puro, en el arnés) | fi-glass `resonanceCallMachine.ts`, `resonanceEffects.ts`, `resonanceCuePolicy.ts`, `resonanceVadGate.ts`, `resonanceCallController.ts`, `useAudioAnalysis.ts` |
| `Models/ResonanceCallModel.swift` — adaptadores: micrófono, STT, el turno del chat, TTS, temporizadores | `useResonanceCallLoop.ts` + og118 `useOg118ResonanceCall.ts` |
| `Services/Voice/ResonanceAudio.swift` — AVAudioEngine (voiceChat = cancelación de eco) + segmento WAV + cues | `getUserMedia` + `MediaRecorder` + `createAudioCuePlayer.ts` |
| `Views/Chat/ResonanceCallViews.swift` — `ResonanceCallButton`, `ResonanceCallBar` | `.og-resonance-call-btn*`, `.og-resonance-live`, `AudioVisualizer` en `Og118AgentChat.tsx` |

**Valores tomados de la web, no inventados:** umbrales del VAD 24 / 13, 180 ms de
arranque, 850 ms de silencio de fin de turno, 20 s por turno
(`resonanceVadGate.ts:27-33`); tick de 50 ms (`useResonanceCallLoop.ts:272`);
auto-resume 1200 ms, colgar por inactividad a 300 s, tope de llamada 600 s
(`useResonanceCallLoop.ts:116-121`); ganancia 2.5 y umbral de «Te oigo» 2
(`useAudioAnalysis.ts`, AUDIO_CONFIG); analizador fftSize 256, suavizado 0.8 y
ventana dB por defecto de Web Audio (-100/-30); 24 bandas; volumen de cues 0.6
(`createAudioCuePlayer.ts:36`); etiquetas de estado (`Og118AgentChat.tsx:73-81`);
mensajes de fallo por fase (`useOg118ResonanceCall.ts:39-45`).

**Paridad del nivel, medida, no supuesta:** el VAD compara contra el promedio de
`getByteFrequencyData`, una escala propia de Web Audio. `ResonanceSpectrum` la
replica (Blackman, FFT /N, suavizado, dB→byte) y el arnés la compara contra un
`AnalyserNode` REAL de Chrome (OfflineAudioContext, seno 1 kHz): los 128 bins
coinciden con diferencia 0. Un tono puro promedia ~15 en ambos (no cruza 24); una
señal de banda ancha a 0.05 da 163 aquí y 166 en Chrome.

**Lo que NO se verificó:** el micrófono real (simulador sin voz humana probada),
la cancelación de eco del iPhone frente al barge-in, y la vuelta completa
STT → turno → TTS contra el servidor (necesita sesión de Auth0). La UI se vio en el
simulador con una maqueta efímera de los cuatro estados (no commiteada).

**Diferencia conocida con la web:** la web manda `voice: "nova"` al TTS
(`og118VoiceAdapter.ts:45`); `VoiceService` del iPhone no manda voz y usa el
default del servidor. No se tocó aquí.

**Integración:** el riel del composer es «+ · selector · llamar», como la web; en
llamada el botón queda visible aunque el riel esté cerrado (`keepWhenRailCollapses`)
y `ResonanceCallBar` ocupa el encabezado de la caja. Los fallos de la llamada caen
al mismo banner de voz que el dictado (`voz.errorMessage`).

## El dictado — 2026-10-15

Bernard: *"el mic no se activaba automáticamente, le daba click y se quedaba
pensando como si no hubiera internet"*. Dos causas, las dos con recibo:

1. **El mic SÍ grababa, pero la pantalla no se enteraba.** `VoiceModel.grabando`
   era una propiedad calculada que leía `AudioRecorder.grabando`, otro
   `ObservableObject` anidado; la vista observa a `VoiceModel`, y un cambio en el
   objeto anidado no se publica. Resultado: toque → graba en silencio con el
   icono apagado → segundo toque → detiene y sube → spinner. El estado del
   dictado ahora vive en `VoiceModel` (`preparando` / `grabando` /
   `transcribiendo`), con micrófono y red inyectados (`DictadoDependencias`) y
   tres tests en `UnitTests/DictadoTests.swift` que recorren los estados sin
   micrófono. Mutación: quitar `grabando = true` tumba el test en la aserción
   exacta. Mientras el micrófono se prepara, los toques se ignoran: antes, dos
   toques rápidos abrían dos grabadoras y la primera quedaba en disco.
2. **La transcripción pasa por DOS servidores dormidos.** `og118-api` se apaga a
   los ~5 min sin tráfico (Log Analytics: arranque 00:14:17Z, última petición
   00:14:25Z, apagado 00:19:48Z; `/health` tardó 32 s dormido) y el gateway
   `sus.bernarduriza.com` (`susurro-gateway`, `insult-rg`, también
   `minReplicas: 0`) tardó 11.6 s en contestar su raíz y 30 s+ en `/health`.
   En 14 días **ni una petición a `/stt/transcribe` llegó a `og118-api`**: las
   que Bernard intentó murieron en el teléfono o esperando el arranque. Ahora el
   tap del mic dispara `GET /health` al API mientras él habla, para que el audio
   no pague ese arranque. El gateway sigue frío: despertarlo necesita un
   endpoint del servidor (`/stt/warm`) o `minReplicas: 1`, y eso es decisión de
   gasto de Bernard (og118-api 1 vCPU/2 GiB ≈ USD 21/mes prendido).

Verificado en el simulador: `TEST SUCCEEDED` (5/5) y `BUILD SUCCEEDED` para el
iPhone. **No verificado en el teléfono**: estaba bloqueado y sin cable al
compilar; la build con el arreglo está lista para `devicectl device install`.

## Revisión de sistema (`/cruel-critic`) — 2026-10-15

Lectura completa de `apps/og118-ios` + `app.py` + contratos generados, trazando
flujos (arranque → restore, turno → fold → PUT, Auth0, dictado, Resonance, drawer).
Arreglado en el mismo PR #544, con tests que la mutación tumba:

| # | Era | Arreglo |
|---|---|---|
| 1 | **CRITICAL** — un restore fallido (cold start, red) dejaba `messages` vacío con el error INVISIBLE (StartCard tapa `TranscriptView`); escribir ahí hacía `PUT` de reemplazo total con `baseRecord == nil` → **la conversación del servidor se borraba**. | `ChatModel.hiloListo` / `cargaFallida`: `send` y `save` no corren hasta que el restore terminó; el error se pinta aunque el hilo esté vacío, con «Reintentar carga»; «Cargando la conversación…» y el aviso de servidor dormido a los 4 s. |
| 5 | **GRAVE** — tras una carga fallida, tocar el mismo chat en el drawer no hacía nada (`guard id != conversationID`). | `open()` del mismo id reintenta el restore. |
| 2 | **GRAVE** — `Auth.token()` no coalescía: al arrancar, restore + catálogo + drawer disparaban N refreshes concurrentes con el mismo refresh (con rotación + reuse-detection en Auth0 eso revoca la familia → deslogueo). | Un solo `Task` de refresh compartido; los callers esperan el mismo resultado. Test con tres callers concurrentes → un intercambio. **La config de rotación del tenant NO se verificó**; el código ya era incorrecto sin ella. |
| 3 | **GRAVE** — `ResonanceMicrophone` sin observar interrupciones ni cambios de ruta/configuración: una notificación, una llamada o los AirPods mataban el engine y la barra decía «Escuchando…» 300 s. | Observadores de `interruptionNotification`, `routeChangeNotification` y `AVAudioEngineConfigurationChange`: reconecta el motor con el formato nuevo o cuelga con nombre («Otra app tomó el audio…»). |
| 4 | **GRAVE** — colgar mientras `abrir()` esperaba dejaba el engine arrancado sin dueño (mic encendido). | `.openMic` re-checa `controlador.activa` tras el `await` y cierra si ya no hay llamada. |
| 6 | **GRAVE** — PUT de reemplazo total sin relectura: lo que otro cliente (web, drawer) agregó o fijó se perdía; `preservando` alineaba por índice y tiraba los mensajes del servidor más allá del conteo local. | `save()` relee el record vivo antes de escribir y `ConversationRecord.fusionar` suma sólo los turnos nuevos sobre el vivo (título/pin/archivado del vivo mandan); el hilo local adopta lo que llegó de fuera. Ventana residual: dos PUT que se cruzan en los ms entre relectura y escritura. |

Verificación: arnés macOS 239/239; unit tests en simulador 13/13 (8 nuevos:
`HiloTests`, `AuthTests`, `DictadoTests`); mutaciones probadas: quitar el gate de
`send` → ✘ en `HiloTests.swift:60`; quitar el refresh compartido → ✘ «intercambios 3 == 1»;
`BUILD SUCCEEDED` para iPhone. **En el teléfono: sin verificar** (bloqueado, sin cable).

### Deuda que la revisión dejó nombrada (IMPORTANT, no bloquea)

- `Og118Client`: un 401 reusa el access cacheado hasta `expiresAt` y dice «inicia sesión otra vez» sin forzar refresh ni desloguear.
- Cold start: `loadConversation`/`saveConversation`/el POST del stream no pasan por `ArranqueEnFrio`; el stream no tiene copy de «Despertando el servidor».
- `VoiceService.authorize` manda sin `Authorization` si el access viene vacío (el mismo bug que `Og118Client` ya mató).
- `AudioRecorder.empezar` ignora el `Bool` de `record()`.
- `GET /projects` 404 en cada arranque y `catalog.errorMessage` no se pinta; la web lo gatea con `og118Flags`.
- Tres dueños del `AVAudioSession` (dictado `spokenAudio`, llamada `voiceChat`, lectura `playback`) sin arbitraje: dictar en llamada apaga la cancelación de eco.
- El SSE es tarea foreground: cambiar de app >30 s corta el turno y «Reintentar» lo vuelve a cobrar.
- **Decisión de Bernard:** `UIBackgroundModes: audio` para que la llamada sobreviva al bloqueo de pantalla. Hoy no está declarado.

## En el teléfono físico — 2026-10-10

El teléfono ya no es "paso posterior": el iPhone 15 (`iPhone15,4`, CoreDevice id
`C71FE5EA-605B-57B9-BD3B-E385BE80E568`) está **pareado** y la Mac tiene identidad
`Apple Development: bernarduriza@icloud.com`, equipo `7L36T9PTFN` (cuenta GRATIS).
`project.yml` ya declara ese equipo, así que no hay flags a mano:

```bash
export DEVELOPER_DIR=/Applications/Xcode-26.6.0.app/Contents/Developer
cd apps/og118-ios && xcodegen generate
xcodebuild -project OG118.xcodeproj -scheme OG118 -configuration Debug \
  -destination "id=C71FE5EA-605B-57B9-BD3B-E385BE80E568" \
  -derivedDataPath /tmp/og118-dd -allowProvisioningUpdates build
xcrun devicectl device install app --device C71FE5EA-605B-57B9-BD3B-E385BE80E568 \
  /tmp/og118-dd/Build/Products/Debug-iphoneos/og118.app
xcrun devicectl device process launch --device C71FE5EA-605B-57B9-BD3B-E385BE80E568 com.bernard.og118
```

Corrido hoy: **BUILD SUCCEEDED** → install OK → launch **negado** por iOS
(`profile has not been explicitly trusted by the user`). Eso es el átomo de la
primera vez, no un bug: en el teléfono, Ajustes → General → VPN y gestión de
dispositivos → `Apple Development: bernarduriza@icloud.com` → Confiar.

**El perfil gratis caduca a los 7 días** (éste: creado 2026-10-10, vence
2026-10-17 13:32). Al caducar la app deja de abrir; se reinstala corriendo los
tres comandos de arriba. Los $99 lo suben a un año — sigue siendo decisión de
Bernard.

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
