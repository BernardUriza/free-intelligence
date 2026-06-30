/**
 * resonanceCallMachine — the headless turn-taking core of RESONANCE, fi-glass's
 * hands-free continuous voice-call mode.
 *
 * A pure (state, event) -> state reducer with zero adapter, React, or transport
 * dependency. The useResonanceCallLoop hook drives it from real TTS/STT adapters;
 * this module only governs which turn-state is legal next. Keeping the machine
 * pure is what makes the four canonical flows — happy path, barge-in, auto-resume,
 * sleep hangup — verifiable without mocking audio I/O.
 *
 * RESONANCE is the voice CHANNEL through which any elemento (persona) speaks; it is
 * not an elemento itself. See .claude/backlog/og118-resonance-voice-mode.md.
 */

export type ResonanceCallState =
  | 'idle'
  | 'listening'
  | 'transcribing'
  | 'thinking'
  | 'speaking'
  | 'interrupted'
  | 'silence_hold'
  | 'sleep_decay'
  | 'ended';

export type ResonanceCallEvent =
  | 'call.started'
  | 'mic.opened'
  | 'user.speech.started'
  | 'user.speech.ended'
  | 'stt.completed'
  | 'assistant.speech.started'
  | 'assistant.speech.interrupted'
  | 'assistant.speech.completed'
  | 'silence.detected'
  | 'silence.resume'
  | 'sleep.decay.started'
  | 'error.recoverable'
  | 'error.fatal'
  | 'call.ended';

export const RESONANCE_INITIAL_STATE: ResonanceCallState = 'idle';

const TRANSITIONS: Record<
  ResonanceCallState,
  Partial<Record<ResonanceCallEvent, ResonanceCallState>>
> = {
  idle: {
    'call.started': 'listening',
  },
  listening: {
    'mic.opened': 'listening',
    'user.speech.started': 'listening',
    'user.speech.ended': 'transcribing',
    'silence.detected': 'silence_hold',
  },
  transcribing: {
    'stt.completed': 'thinking',
  },
  thinking: {
    'assistant.speech.started': 'speaking',
  },
  speaking: {
    'user.speech.started': 'interrupted',
    'assistant.speech.completed': 'silence_hold',
  },
  interrupted: {
    'assistant.speech.interrupted': 'listening',
  },
  silence_hold: {
    'silence.resume': 'listening',
    'sleep.decay.started': 'sleep_decay',
  },
  sleep_decay: {
    'silence.resume': 'listening',
  },
  ended: {},
};

export function isTerminal(state: ResonanceCallState): boolean {
  return state === 'ended';
}

export function resonanceCallReducer(
  state: ResonanceCallState,
  event: ResonanceCallEvent,
): ResonanceCallState {
  if (isTerminal(state)) return state;
  if (event === 'call.ended') return 'ended';
  // Recovery is global: a failed effect in any active phase either drops the call
  // back to listening (recoverable: STT/agent/TTS hiccup) or hangs up (fatal: mic
  // lost). Without this the loop froze in transcribing/thinking/speaking on a
  // rejected adapter promise.
  if (event === 'error.fatal') return 'ended';
  if (event === 'error.recoverable') return state === 'idle' ? 'idle' : 'listening';
  return TRANSITIONS[state][event] ?? state;
}
