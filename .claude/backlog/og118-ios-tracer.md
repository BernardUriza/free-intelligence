# OG118-IOS-1 — cliente nativo de iPhone (tracer bullet)

Status: **In progress** (EN VIVO 2026-10-10) — ya está INSTALADA EN EL iPHONE 15 físico, firmada con el Apple ID gratis. El launch lo niega iOS hasta que Bernard confíe en el desarrollador en el teléfono; luego el átomo es la contraseña de Auth0
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
