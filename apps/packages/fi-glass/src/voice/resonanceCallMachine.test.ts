import { describe, it, expect } from 'vitest';

import {
  RESONANCE_INITIAL_STATE,
  resonanceCallReducer,
  isTerminal,
  type ResonanceCallEvent,
  type ResonanceCallState,
} from './resonanceCallMachine';

function run(events: ResonanceCallEvent[], from: ResonanceCallState = RESONANCE_INITIAL_STATE) {
  return events.reduce((state, event) => resonanceCallReducer(state, event), from);
}

function trace(events: ResonanceCallEvent[], from: ResonanceCallState = RESONANCE_INITIAL_STATE) {
  const states: ResonanceCallState[] = [from];
  events.reduce((state, event) => {
    const next = resonanceCallReducer(state, event);
    states.push(next);
    return next;
  }, from);
  return states;
}

describe('resonanceCallMachine', () => {
  it('starts idle', () => {
    expect(RESONANCE_INITIAL_STATE).toBe('idle');
  });

  it('happy path: idle -> listening -> transcribing -> thinking -> speaking -> listening', () => {
    const states = trace([
      'call.started',
      'user.speech.ended',
      'stt.completed',
      'assistant.speech.started',
      'assistant.speech.completed',
      'silence.resume',
    ]);
    expect(states).toEqual([
      'idle',
      'listening',
      'transcribing',
      'thinking',
      'speaking',
      'silence_hold',
      'listening',
    ]);
  });

  it('barge-in: speaking + user.speech.started -> interrupted -> listening', () => {
    const states = trace(
      ['user.speech.started', 'assistant.speech.interrupted'],
      'speaking',
    );
    expect(states).toEqual(['speaking', 'interrupted', 'listening']);
  });

  it('auto-resume: speaking.completed -> silence_hold -> listening', () => {
    expect(run(['assistant.speech.completed', 'silence.resume'], 'speaking')).toBe('listening');
  });

  it('sleep hangup: silence_hold + sleep.decay.started -> sleep_decay -> ended', () => {
    const states = trace(['sleep.decay.started', 'call.ended'], 'silence_hold');
    expect(states).toEqual(['silence_hold', 'sleep_decay', 'ended']);
    expect(isTerminal('ended')).toBe(true);
  });

  it('call.ended from any active state hangs up to ended', () => {
    for (const s of [
      'listening',
      'transcribing',
      'thinking',
      'speaking',
      'interrupted',
      'silence_hold',
      'sleep_decay',
    ] as ResonanceCallState[]) {
      expect(resonanceCallReducer(s, 'call.ended')).toBe('ended');
    }
  });

  it('ignores events with no transition for the current state (no-op stays put)', () => {
    expect(resonanceCallReducer('listening', 'stt.completed')).toBe('listening');
    expect(resonanceCallReducer('idle', 'user.speech.started')).toBe('idle');
  });

  it('error.recoverable from any active phase drops back to listening', () => {
    for (const s of [
      'transcribing',
      'thinking',
      'speaking',
      'interrupted',
      'silence_hold',
    ] as ResonanceCallState[]) {
      expect(resonanceCallReducer(s, 'error.recoverable')).toBe('listening');
    }
    // idle has no call to recover into — stays idle
    expect(resonanceCallReducer('idle', 'error.recoverable')).toBe('idle');
  });

  it('error.fatal hangs up to ended from any active phase', () => {
    for (const s of [
      'listening',
      'transcribing',
      'thinking',
      'speaking',
      'silence_hold',
    ] as ResonanceCallState[]) {
      expect(resonanceCallReducer(s, 'error.fatal')).toBe('ended');
    }
  });

  it('ended is terminal — no event revives the call', () => {
    for (const e of [
      'call.started',
      'user.speech.started',
      'assistant.speech.started',
      'silence.resume',
    ] as ResonanceCallEvent[]) {
      expect(resonanceCallReducer('ended', e)).toBe('ended');
    }
  });
});
