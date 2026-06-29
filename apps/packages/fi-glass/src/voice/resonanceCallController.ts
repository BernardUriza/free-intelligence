/**
 * resonanceCallController — the framework-agnostic heart of useResonanceCallLoop.
 *
 * Holds the resonanceCallMachine state, and on every CHANGED state dispatches the
 * single effectForState to the injected ResonanceDriver. External signals (mic
 * opened, end-of-speech silence, STT transcript, assistant text, TTS completed,
 * barge-in) enter through named methods that map to FSM events. No React, no
 * audio I/O — so the full turn-taking contract is verifiable with vitest + a mock
 * driver, exactly as the coagent's contract requires. useResonanceCallLoop is a
 * thin React wrapper that binds the real adapters to this controller.
 */

import {
  RESONANCE_INITIAL_STATE,
  resonanceCallReducer,
  isTerminal,
  type ResonanceCallEvent,
  type ResonanceCallState,
} from './resonanceCallMachine';
import { effectForState, dispatchEffect, type ResonanceDriver } from './resonanceEffects';

export interface ResonanceControllerHooks {
  onState?: (state: ResonanceCallState) => void;
  onEvent?: (event: ResonanceCallEvent, state: ResonanceCallState) => void;
}

export interface ResonanceCallController {
  state: () => ResonanceCallState;
  lastTranscript: () => string | undefined;
  lastAssistantText: () => string | undefined;
  events: () => ResonanceCallEvent[];
  send: (event: ResonanceCallEvent) => ResonanceCallState;
  // Named signal entrypoints (the React layer / tests call these):
  startCall: () => void;
  micOpened: () => void;
  userSpeechStarted: () => void;
  userSpeechEnded: () => void;
  sttCompleted: (transcript: string) => void;
  assistantTurnReady: (text: string) => void;
  ttsCompleted: () => void;
  ttsInterrupted: () => void;
  silenceDetected: () => void;
  silenceResume: () => void;
  sleepDecay: () => void;
  /** Barge-in helper: cut TTS, then re-open for the user's new turn. */
  interrupt: () => void;
  /** A recoverable adapter failure (STT/agent/TTS) — drop back to listening. */
  failRecoverable: () => void;
  /** A fatal adapter failure (mic lost) — hang up the call. */
  failFatal: () => void;
  endCall: () => void;
}

export function createResonanceCallController(
  driver: ResonanceDriver,
  hooks: ResonanceControllerHooks = {},
): ResonanceCallController {
  let state: ResonanceCallState = RESONANCE_INITIAL_STATE;
  let transcript: string | undefined;
  let assistantText: string | undefined;
  const log: ResonanceCallEvent[] = [];

  function send(event: ResonanceCallEvent): ResonanceCallState {
    const next = resonanceCallReducer(state, event);
    log.push(event);
    hooks.onEvent?.(event, next);
    if (next !== state) {
      state = next;
      hooks.onState?.(state);
      dispatchEffect(effectForState(state), driver);
    }
    return state;
  }

  return {
    state: () => state,
    lastTranscript: () => transcript,
    lastAssistantText: () => assistantText,
    events: () => [...log],
    send,
    startCall: () => { send('call.started'); },
    micOpened: () => { send('mic.opened'); },
    userSpeechStarted: () => { send('user.speech.started'); },
    userSpeechEnded: () => { send('user.speech.ended'); },
    sttCompleted: (t: string) => { transcript = t; send('stt.completed'); },
    assistantTurnReady: (text: string) => { assistantText = text; send('assistant.speech.started'); },
    ttsCompleted: () => { send('assistant.speech.completed'); },
    ttsInterrupted: () => { send('assistant.speech.interrupted'); },
    silenceDetected: () => { send('silence.detected'); },
    silenceResume: () => { send('silence.resume'); },
    sleepDecay: () => { send('sleep.decay.started'); },
    interrupt: () => {
      if (state !== 'speaking') return;
      send('user.speech.started');        // speaking -> interrupted (fires stop_speaking)
      send('assistant.speech.interrupted'); // interrupted -> listening (fires open_mic)
    },
    failRecoverable: () => { if (!isTerminal(state) && state !== 'idle') send('error.recoverable'); },
    failFatal: () => { if (!isTerminal(state)) send('error.fatal'); },
    endCall: () => { if (!isTerminal(state)) send('call.ended'); },
  };
}
