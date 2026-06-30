/**
 * resonanceEffects — the pure state-to-effect mapping that bridges the
 * resonanceCallMachine reducer to real TTS/STT/mic adapters.
 *
 * useResonanceCallLoop drives the reducer, then on every state ENTERED asks
 * effectForState which single imperative effect to run, and dispatches it to the
 * injected driver (open the mic, cut TTS on barge-in, invoke the agent, etc.).
 * Keeping the mapping pure means the orchestration contract is verifiable without
 * mocking audio I/O — the driver is the only thing the React hook has to wire.
 */

import type { ResonanceCallState } from './resonanceCallMachine';

export type ResonanceEffect =
  | { type: 'open_mic' }
  | { type: 'begin_transcribe' }
  | { type: 'invoke_agent' }
  | { type: 'speak' }
  | { type: 'stop_speaking' }
  | { type: 'hold_silence' }
  | { type: 'fade_and_hangup' }
  | { type: 'end_call' };

const STATE_EFFECT: Record<ResonanceCallState, ResonanceEffect | null> = {
  idle: null,
  listening: { type: 'open_mic' },
  transcribing: { type: 'begin_transcribe' },
  thinking: { type: 'invoke_agent' },
  speaking: { type: 'speak' },
  interrupted: { type: 'stop_speaking' },
  silence_hold: { type: 'hold_silence' },
  sleep_decay: { type: 'fade_and_hangup' },
  ended: { type: 'end_call' },
};

/**
 * The single effect to run on entering `state`, or null when the state needs no
 * adapter action (idle). Only fire when the state actually CHANGED — re-entering
 * the same state must not re-dispatch (the hook guards on prev !== next).
 */
export function effectForState(state: ResonanceCallState): ResonanceEffect | null {
  return STATE_EFFECT[state];
}

export interface ResonanceDriver {
  openMic: () => void;
  beginTranscribe: () => void;
  invokeAgent: () => void;
  speak: () => void;
  stopSpeaking: () => void;
  holdSilence: () => void;
  fadeAndHangup: () => void;
  endCall: () => void;
}

/** Dispatch one effect to the driver. Returns true when an effect ran. */
export function dispatchEffect(effect: ResonanceEffect | null, driver: ResonanceDriver): boolean {
  switch (effect?.type) {
    case 'open_mic': driver.openMic(); return true;
    case 'begin_transcribe': driver.beginTranscribe(); return true;
    case 'invoke_agent': driver.invokeAgent(); return true;
    case 'speak': driver.speak(); return true;
    case 'stop_speaking': driver.stopSpeaking(); return true;
    case 'hold_silence': driver.holdSilence(); return true;
    case 'fade_and_hangup': driver.fadeAndHangup(); return true;
    case 'end_call': driver.endCall(); return true;
    default: return false;
  }
}
