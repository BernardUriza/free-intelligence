# RESONANCE — hands-free, screenless voice-call mode for og118

Status: **Done — default-on desde 2026-09-12** — resonanceCallMachine/Controller/VadGate/CuePolicy + useResonanceCallLoop en fi-glass, consumidos por og118 vía useOg118ResonanceCall. El flag `?resonance=1` se borró el 2026-09-12, el día que Azure concedió la cuota (whisper/tts 3 → 30 RPM) — ver la última sección
Proposed: 2026-06-29 by Bernard

> Naming taxonomy locked: the **elementos** are the 118 named personas (atoms,
> the customGPTs — see [[og118-elementos-118-gpt-personas]]). **Resonance** is a
> different layer of chemistry on purpose: it is NOT an element, it is the
> *channel* through which any elemento speaks by voice. Atoms (personas) speak
> through Resonance. Chemical resonance (the delocalized hybrid that holds a
> molecule together) doubles as acoustic resonance (the voice that envelops you).
> Public/feature name is the English **Resonance**.

## What it is

A **voice-call mode** for og118 (`staging.og118.ai`): screenless, hands-free,
continuous spoken conversation with whichever elemento is bound. The seed use
case Bernard validated against ChatGPT Advanced Voice Mode is talking in bed,
no screen, until you drift off — but the scope is deliberately the **medium
(voice), not the use (sleep)**. Naming it "sleep helper" would close the scope;
Resonance covers arrullo, manos-libres, brainstorm a oscuras, accessibility —
anything that lives on voice.

The market gap this fills (from `/histerical-search`, 2026-06-29): the existing
named products split into two camps that nobody has merged —
- **screenless hardware** (Naptick AI, Somnox) that is NOT a general LLM, and
- **LLM apps** (character.ai sleep helper, Sleep.app) that chain you to a screen.

A general conversational LLM + voice + zero screen is exactly what people hack
out of ChatGPT voice (the OpenAI forum has open requests for a "sleep timer for
voice mode" because they use it as a bedtime companion). og118 already owns every
piece to ship the real thing.

## Canonical path to reuse (Art. 6) — this is composition, not new plumbing

The voice round-trip already exists end-to-end in og118. Resonance is a **mode**
on top, not new transport.

- **Voice round-trip already ships in og118:** `web/lib/og118VoiceAdapter.ts`
  (TTS/STT VoiceAdapter), `web/lib/useOg118VoiceComposer.tsx` (composer hook),
  `web/components/Og118VoiceErrorBanner.tsx`, `web/components/Og118MessageActions.tsx`
  (SpeakButton), backend `server/tts.py` + `server/stt.py`. Don't rebuild voice.
- **Voice gateway is live and JWT-verified** — TTS/STT route to the susurro
  gateway `sus.bernarduriza.com`, confirmed live with a real Auth0 JWT
  ([[og118-voice-susurro-gateway]]). Resonance reuses this, no new endpoint.
- **fi-glass already has the voice + persona primitives** — Americio closed the
  composer+voice; Californio closed the persona selector + SpeakButton
  ([[fi-glass-framework]]). The persona being spoken is an **elemento**
  ([[og118-elementos-118-gpt-personas]]); Resonance is the channel, not a new GPT.
- **Stateless continuity already solved** — client-sent history + stateless
  backend ([[og118-continuity-canary]]) means a long hands-free session keeps the
  thread without server session state.
- **Canary discipline** ([[framework-first-canary]]): "continuous voice-call
  session loop" (mic-open turn-taking, barge-in, auto-resume after silence, a
  sleep/idle timer that fades energy/volume) is **reusable fi-glass framework**,
  not og118-local. If built, the call-session loop primitive belongs in
  fi-glass/core; og118 is its first consumer. App-specific stays in og118:
  branding/copy "Resonance", which elemento is default, the nighttime tone curve.

## What is genuinely NEW (the only real build)

1. **Continuous call loop** — open-mic turn-taking instead of one-shot
   record→send→speak. Barge-in (interrupt the AI's speech), auto-resume after a
   pause, VAD/silence detection. This is the missing primitive vs. the existing
   one-shot composer.
2. **Idle / sleep timer** — the explicit thing ChatGPT voice users beg OpenAI
   for: after N minutes of one-sided silence, fade volume/energy and end the
   call gracefully instead of talking to a sleeping person forever.
3. **Energy/tone curve** — optional: a delivery that ramps down (slower, softer)
   as the session ages, the "empujoncito verbal" Bernard described — but this is
   a persona/prompt + TTS-param concern, not architecture.

## The decision that's the owner's

1. **Where the call-loop lives** — fi-glass primitive (canary-correct) vs. og118
   prototype first. Per [[framework-first-canary]] the loop is reusable; the
   default is fi-glass with og118 as first consumer, but the prototype-in-consumer
   exception is allowed WITH an explicit extraction gate.
2. **Default elemento for Resonance** — which persona answers when you just
   "call" with no element picked (Oxígeno/vultur as the seed?).
3. **Sleep-timer semantics** — does Resonance ship a nighttime affordance at all
   in v1, or is it pure call-mode and the sleep tone comes later as a persona?
   (Bernard: scope is voice, not sleep — so timer = generic idle hangup, the
   sleep framing stays a persona concern.)
4. **TTS provider headroom for continuous duration** — a long hands-free call is
   far more TTS/STT volume than one-shot turns; confirm susurro gateway cost/rate
   limits before opening it to long sessions (Art. 7 stress-test).

## Status / next step

Not built — vision + name captured the day Bernard decided it (Art. 5). The
value, per Bernard, is integrating it into `staging.og118.ai` where the voice
round-trip already runs. Next step when greenlit: classify the call-loop
(fi-glass vs og118 prototype), then build the continuous-call session on top of
the existing `og118VoiceAdapter` + susurro gateway, with Oxígeno as the first
elemento on the other end of the line.

Related: [[og118-elementos-118-gpt-personas]] (the atoms Resonance carries),
[[fi-glass-framework]], [[framework-first-canary]],
[[og118-voice-susurro-gateway]], [[b3-tts-stt-cycle]], [[og118-continuity-canary]].

## El estudio del default-on — 2026-09-09

Bernard pidió resolver el residual. Se mapeó la superficie entera antes de tocar
nada, y **el flag no era el problema: era la venda sobre el problema.**

### Lo que se verificó (con recibos)

- **El flag vive en UN solo sitio**, cliente puro:
  `web/components/Og118AgentChat.tsx:59-66` (`?resonance=1`, `?RESONANCE_CALL_LOOP=1`
  o `localStorage`). No pasa por `lib/og118Flags.ts`, así que prenderlo por
  default es una edición de código, no un flip de variable de deploy.
- **La infra SÍ está configurada.** El trío de STT y el de TTS están completos —
  llaves como secretos (`OG118_STT_API_KEY`, `OG118_TTS_API_KEY`) y
  endpoint/deployment como variables de repo, los cuatro apuntando a
  `https://sus.bernarduriza.com`. El workflow las cablea en cada deploy
  (`og118-backend.yml:200-245`) y el último corrió verde hoy (`37d098b4`,
  14:23Z). La hipótesis de "prenderlo lo rompe porque falta config" se probó y
  **es falsa**.
- **El defecto real: el fallo era MUDO, y en dos capas.**
  1. `useResonanceCallLoop` no exponía NINGÚN error a su consumidor — su única
     salida era un `console.warn` (`:171-175`). Un STT/TTS caído se veía idéntico
     a un modelo callado.
  2. og118 se tragaba además el fallo de síntesis: `speak` hacía
     `.catch(() => resolve())`, o sea reportaba "ya hablé" tras un 503.
  El agravante: `Og118VoiceErrorBanner` existe y el composer de un tiro YA
  enruta sus fallos ahí (`useOg118VoiceComposer.tsx:64`). **RESONANCE era la
  única superficie de voz sin banner.**
- **Cero tests del flag**, en cualquiera de sus dos posiciones.

### Lo que se hizo

El hueco es del FRAMEWORK y og118 fue el canario que lo destapó
([[framework-first-canary]]), así que subió:

- fi-glass: `ResonanceCallAdapters.onError(phase, error, fatal)` +
  `ResonanceErrorPhase`, disparado en `recover()` y en el camino fatal del
  micrófono. 3 tests nuevos (`useResonanceCallLoop.test.tsx` — el archivo no
  tenía ninguno). `dist/` reconstruido y commiteado ([[committed-dist-artifacts]]).
- og118: `speak` deja de tragarse la síntesis (el loop la enruta a
  `recover('tts')`); `mensajeDeFalloDeVoz()` como función pura y testeada decide
  qué lee el usuario, y `Og118AgentChat` la cablea a `composer.setVoiceError`.
  4 tests nuevos. Suites: fi-glass 614 verdes, og118-web 116 verdes.

### Por qué el flag NO se quitó, y qué falta para quitarlo

Prenderlo hoy habría sido cambiar un flag por un riesgo sin medir. Queda **una**
cosa, y es la decisión #4 de arriba, todavía intacta: **no hay tope de duración
ni de gasto en una llamada.** El único techo es un idle hangup de cliente a 5
minutos (`useResonanceCallLoop.ts:98`); el servidor no tiene rate limit ni cuota
por usuario (sólo caps de tamaño: 25 MB por audio de STT, 4096 chars por TTS).
Una llamada manos libres es órdenes de magnitud más volumen que un turno suelto,
y el costo por minuto continuo del gateway susurro **nunca se midió**. Eso es el
stress-test del Art. 7 que la tarjeta se pidió a sí misma y sigue sin correrse.

**Condición para el default-on, en una línea:** medir el costo de un minuto de
llamada contra el gateway y poner un tope explícito (duración o gasto). Con eso,
quitar el flag es borrar `readResonanceFlag` y sus dos usos.

> Esa medición se corrió el mismo día y **contestó otra cosa**. Ver la sección
> siguiente: el bloqueo no es el costo, es la capacidad upstream.

Segundo detalle menor para ese día: `debug: resonanceEnabled`
(`Og118AgentChat.tsx:157`) expondría `window.__RESONANCE_EVENTS__` a todo el
mundo — hoy sólo lo ve quien opta por el flag.

## El stress-test del Art. 7, corrido — y salió ROJO (2026-09-09)

La decisión #4 llevaba desde junio pidiendo *"confirmar cost/rate limits del
gateway susurro antes de abrirlo a sesiones largas"*. Se corrió contra el gateway
y contra Azure. **No se pudo quitar el flag, y la razón es mejor que un costo.**

### Medido contra el gateway real (`sus.bernarduriza.com`)

| | |
|---|---|
| TTS, 129 chars | **2.8 / 3.1 s** en caliente → **8.0 s** de audio (≈16 chars/s) |
| TTS, primera llamada tras reposo | **34 s** — cold start; es el primer turno de toda llamada |
| STT, 8.0 s de audio | **1.4 / 1.5 s** |
| Turno modelado (habla 6s + 0.9 endOfSpeech + 1.5 STT + ~4 agente + 2.9 TTS + 18.6 playback + 1.2 autoResume) | **≈35 s → ~1.7 turnos/min** |

### El techo, verificado contra Azure (no contra el doc)

```
whisper: capacity 3 → 3 RPM        OpenAI.Standard.whisper  used 3.0 / limit 3.0
tts:     capacity 3 → 3 RPM        OpenAI.Standard.tts      used 3.0 / limit 3.0
```

La cuota de la suscripción en northcentralus está **agotada**: subirla exige una
solicitud a Azure (https://aka.ms/oai/quotaincrease). Y el gateway es
**compartido** — discord-bot, inkbook, picturelock, visalaw-videopipe y el
dictado de un tiro de og118 beben del mismo techo.

**Un solo llamante a 1.7 turnos/min consume ~57% del RPM de whisper y de tts.**
Dos llamadas concurrentes, o una de turnos cortos, lo revientan — y se llevan por
delante el dictado de todos los demás consumidores. **Prender RESONANCE por
default hoy no es caro: es una negación de servicio a la flota.**

### Lo que sí se shipeó, porque el daño ya existe con el flag puesto

Cualquiera con `?resonance=1` puede hoy abrir una llamada sin tope alguno:

- **fi-glass `ResonanceSleepPolicy.maxCallMs`** (default 10 min) — techo de RELOJ
  para la llamada entera, armado en `startCall` e independiente del estado.
  `idleHangupMs` **no era un techo**: sólo se arma en `silence_hold`, así que a
  quien no deja de hablar nunca se le colgaba. Se reporta por `onError` con fase
  `'duration'`, o sea llega al banner: una llamada que se corta sin explicación se
  lee como un crash. 2 tests (ambas ramas, incluido `maxCallMs: 0`).
- **`server/voice_quota.py`** — ventana deslizante por principal sobre
  `/stt/transcribe` y `/tts/synthesize`, 429 con `Retry-After`. El default
  (`OG118_VOICE_RPM=3`) **iguala el techo upstream a propósito**: no inventa una
  restricción que Azure no impondría ya —eso habría roto el dictado de un tiro,
  que funciona hoy— pero convierte un 429 remoto y caro en uno local y honesto.
  6 tests + aislamiento del contador en `conftest.py` (es estado de proceso: sin
  reset, un test hereda el 429 del anterior y acusa al código equivocado).

### Lo que falta ahora para el default-on, y ya no es de og118

**Una solicitud de aumento de cuota a Azure** para `whisper`/`tts` en
northcentralus. Sin más RPM no hay tope del lado de og118 que haga viable una
llamada manos libres abierta a todos.

### Las dos solicitudes YA SE ENVIARON — 2026-09-09

Se llenó y envió el formulario de Microsoft (`aka.ms/oai/quotaincrease` →
*Microsoft Foundry Service: Request for Quota Increase*, Dynamics 365 Customer
Voice, anónimo, sin login). **Una solicitud por modelo**, porque el formulario
sólo acepta un modelo por envío:

| Campo | whisper | tts |
|---|---|---|
| Suscripción | `d61ba6bc-eda9-4327-a264-5cfddef30bc8` | igual |
| Quota Type | Model Deployment (PTU/RPM/TPM) | igual |
| Model Type / Deployment | Azure OpenAI · Standard | igual |
| Región preferida | North Central US | igual |
| Si no hay cupo ahí | *Grant me quota in an alternate region* → **Anywhere in the USA** | igual |
| Total pedido | **30 RPM** (de 3) | **30 RPM** (de 3) |

Las dos confirmaron con *"Thanks! You've completed the request! / Your response
was submitted."*

**No hay número de caso: el formulario no emite folio.** El único acuse es esa
pantalla. Microsoft dice que se procesa *"the next business day after
submission, sometimes up to two business days"* y advierte explícitamente que
**enviar la solicitud no garantiza que se cumpla**.

La justificación que se mandó apoya el criterio que el propio formulario dice
priorizar —*"customers who generate traffic that consumes the existing quota
allocation"*—: se citó el 3.0/3.0 de la suscripción, los tiempos medidos contra
el gateway, el ~57% que consume un solo llamante, y que el flag existe
únicamente por el techo de RPM.

**Cómo verificar si la concedieron** (no hay correo de aviso garantizado):

```bash
az cognitiveservices usage list -l northcentralus \
  --query "[?contains(name.value,'whisper')||contains(name.value,'tts')].{n:name.value,used:currentValue,limit:limit}" -o table
```

Un `limit` mayor a 3.0 es la concesión. Si a los tres días hábiles sigue en 3.0,
la vía es `csgate@microsoft.com`, que es el contacto que el formulario publica.

Segundo detalle para ese día, ya anotado arriba: `debug: resonanceEnabled`
expondría `window.__RESONANCE_EVENTS__` a todo el mundo.

## La cuota se concedió y el flag se borró — 2026-09-12

Tres días después de las solicitudes, sin correo de aviso, el poll dio verde:

```
OpenAI.Standard.whisper  3.0 / 30.0
OpenAI.Standard.tts      3.0 / 30.0
```

El `limit` subió; el `used` seguía en 3.0 porque la cuota de la suscripción no
escala los deployments sola. Se escalaron los dos (`susurro-openai`, susurro-rg,
`capacity: 3 → 30`, `Succeeded`) y el poll quedó en **30.0 / 30.0** para ambos.

Con el techo diez veces más alto, se cumplió la condición de la sección anterior:

- **og118 web:** `readResonanceFlag` y sus dos usos borrados; el botón de
  llamada se monta siempre. `useOg118ResonanceCall` perdió `enabled` y `debug`
  (el segundo era el que habría expuesto `window.__RESONANCE_EVENTS__` a todos).
  grep de `RESONANCE_CALL_LOOP|readResonanceFlag|resonanceEnabled` en fuentes → 0.
- **og118 server:** `OG118_VOICE_RPM` pasa de 3 a **10** por default. Ya no
  iguala el upstream —eso dejó de tener sentido con 30— sino que cabe una llamada
  de turnos cortos (~2 RPM por endpoint al ritmo medido) y le deja dos tercios
  del techo al resto de la flota aunque un sujeto lo agote. Test renombrado con
  la nueva razón.
- **fi-glass:** sólo el header de `useResonanceCallLoop.ts`, que decía que og118
  lo montaba tras el flag; el `dist/` rebuild cambió únicamente source maps.

Lo que NO cambió: `maxCallMs` (10 min) sigue armado. Y el arnés de un render
completo de `Og118AgentChat` no existe (jsdom sin IndexedDB), así que el
"siempre montado" se verifica en la superficie real, no con un test unitario.
