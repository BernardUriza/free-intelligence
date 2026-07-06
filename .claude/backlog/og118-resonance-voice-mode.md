# RESONANCE — hands-free, screenless voice-call mode for og118

Status: Proposed (name ratified by Bernard 2026-06-29)
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
