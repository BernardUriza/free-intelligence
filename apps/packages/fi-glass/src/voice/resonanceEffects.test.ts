import { describe, it, expect, vi } from 'vitest';

import {
  effectForState,
  dispatchEffect,
  type ResonanceDriver,
  type ResonanceEffect,
} from './resonanceEffects';
import {
  RESONANCE_INITIAL_STATE,
  resonanceCallReducer,
  type ResonanceCallEvent,
} from './resonanceCallMachine';

function mockDriver(): ResonanceDriver {
  return {
    openMic: vi.fn(),
    beginTranscribe: vi.fn(),
    invokeAgent: vi.fn(),
    speak: vi.fn(),
    stopSpeaking: vi.fn(),
    holdSilence: vi.fn(),
    fadeAndHangup: vi.fn(),
    endCall: vi.fn(),
  };
}

describe('effectForState', () => {
  it('idle needs no adapter action', () => {
    expect(effectForState('idle')).toBeNull();
  });

  it('maps each active state to its single effect', () => {
    expect(effectForState('listening')).toEqual({ type: 'open_mic' });
    expect(effectForState('transcribing')).toEqual({ type: 'begin_transcribe' });
    expect(effectForState('thinking')).toEqual({ type: 'invoke_agent' });
    expect(effectForState('speaking')).toEqual({ type: 'speak' });
    expect(effectForState('interrupted')).toEqual({ type: 'stop_speaking' });
    expect(effectForState('silence_hold')).toEqual({ type: 'hold_silence' });
    expect(effectForState('sleep_decay')).toEqual({ type: 'fade_and_hangup' });
    expect(effectForState('ended')).toEqual({ type: 'end_call' });
  });
});

describe('dispatchEffect', () => {
  it('routes each effect to the matching driver method exactly once', () => {
    const cases: Array<[ResonanceEffect, keyof ResonanceDriver]> = [
      [{ type: 'open_mic' }, 'openMic'],
      [{ type: 'begin_transcribe' }, 'beginTranscribe'],
      [{ type: 'invoke_agent' }, 'invokeAgent'],
      [{ type: 'speak' }, 'speak'],
      [{ type: 'stop_speaking' }, 'stopSpeaking'],
      [{ type: 'hold_silence' }, 'holdSilence'],
      [{ type: 'fade_and_hangup' }, 'fadeAndHangup'],
      [{ type: 'end_call' }, 'endCall'],
    ];
    for (const [effect, method] of cases) {
      const driver = mockDriver();
      expect(dispatchEffect(effect, driver)).toBe(true);
      expect(driver[method]).toHaveBeenCalledTimes(1);
    }
  });

  it('null effect dispatches nothing', () => {
    const driver = mockDriver();
    expect(dispatchEffect(null, driver)).toBe(false);
    for (const fn of Object.values(driver)) expect(fn).not.toHaveBeenCalled();
  });
});

describe('reducer + effects integration (barge-in cuts TTS)', () => {
  it('a user barge-in during speaking dispatches stop_speaking then re-opens the mic', () => {
    const driver = mockDriver();
    const drive = (state: Parameters<typeof effectForState>[0]) =>
      dispatchEffect(effectForState(state), driver);

    let state = resonanceCallReducer('speaking', 'user.speech.started');
    drive(state); // interrupted -> stop_speaking
    expect(driver.stopSpeaking).toHaveBeenCalledTimes(1);

    state = resonanceCallReducer(state, 'assistant.speech.interrupted');
    drive(state); // listening -> open_mic
    expect(driver.openMic).toHaveBeenCalledTimes(1);
    expect(driver.speak).not.toHaveBeenCalled();
  });

  it('full happy turn fires transcribe -> agent -> speak in order', () => {
    const driver = mockDriver();
    const order: string[] = [];
    const d: ResonanceDriver = {
      ...mockDriver(),
      beginTranscribe: () => order.push('transcribe'),
      invokeAgent: () => order.push('agent'),
      speak: () => order.push('speak'),
    };
    let state = RESONANCE_INITIAL_STATE;
    const seq: ResonanceCallEvent[] = [
      'call.started',
      'user.speech.ended',
      'stt.completed',
      'assistant.speech.started',
    ];
    for (const e of seq) {
      state = resonanceCallReducer(state, e);
      dispatchEffect(effectForState(state), d);
    }
    expect(order).toEqual(['transcribe', 'agent', 'speak']);
  });
});
