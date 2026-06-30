import { describe, it, expect } from 'vitest';

import {
  createResonanceVadGate,
  DEFAULT_VAD_CONFIG,
  type ResonanceVadEvent,
  type ResonanceVadMode,
} from './resonanceVadGate';

const TICK = 50;

/** Drive the gate for `durationMs` at 50ms ticks with a level(t) function. */
function run(
  gate: ReturnType<typeof createResonanceVadGate>,
  durationMs: number,
  level: (tMs: number) => number,
  mode: ResonanceVadMode = 'detect',
  startMs = 1000,
) {
  const events: Array<{ t: number; e: ResonanceVadEvent }> = [];
  for (let t = 0; t <= durationMs; t += TICK) {
    const e = gate.tick(level(t), startMs + t, mode);
    if (e) events.push({ t, e });
  }
  return events.map((x) => x.e);
}

describe('resonanceVadGate', () => {
  it('low ambient noise (below speechOnThreshold) never starts speech', () => {
    const gate = createResonanceVadGate();
    const events = run(gate, 3000, () => 8); // below on(18) and off(10)
    expect(events).toEqual([]);
  });

  it('sustained speech above threshold for minSpeechMs emits exactly one speech_start', () => {
    const gate = createResonanceVadGate();
    const events = run(gate, 1000, () => 40); // loud the whole time
    expect(events).toEqual(['speech_start']);
  });

  it('a brief blip shorter than minSpeechMs does NOT start speech', () => {
    const gate = createResonanceVadGate();
    // 100ms of loud (< minSpeechMs 180), then quiet
    const events = run(gate, 2000, (t) => (t < 100 ? 40 : 5));
    expect(events).toEqual([]);
  });

  it('speech then a short pause does NOT end the turn (hysteresis/hangover)', () => {
    const gate = createResonanceVadGate();
    // loud 0-500, quiet 500-1000 (500ms < endSilenceMs 850), loud again
    const events = run(gate, 2000, (t) => (t < 500 || t >= 1000 ? 40 : 5));
    expect(events).toEqual(['speech_start']); // started, never ended
  });

  it('speech then sustained silence (>= endSilenceMs) emits speech_end', () => {
    const gate = createResonanceVadGate();
    // loud 0-500, then quiet for >850ms
    const events = run(gate, 2500, (t) => (t < 500 ? 40 : 5));
    expect(events).toEqual(['speech_start', 'speech_end']);
  });

  it('barge mode emits barge_in on sustained speech, not speech_start', () => {
    const gate = createResonanceVadGate();
    const events = run(gate, 1000, () => 40, 'barge');
    expect(events).toEqual(['barge_in']);
  });

  it('idle mode emits nothing and resets a partial turn', () => {
    const gate = createResonanceVadGate();
    // Start speech in detect mode...
    expect(gate.tick(40, 1000, 'detect')).toBeNull();
    expect(gate.tick(40, 1200, 'detect')).toBe('speech_start');
    // ...then idle should reset; coming back to detect needs a fresh onset.
    expect(gate.tick(40, 1250, 'idle')).toBeNull();
    expect(gate.tick(5, 3000, 'detect')).toBeNull();
  });

  it('maxTurnMs forces speech_end even if the user never stops', () => {
    const cfg = { ...DEFAULT_VAD_CONFIG, maxTurnMs: 1000 };
    const gate = createResonanceVadGate(cfg);
    const events = run(gate, 2000, () => 40); // loud forever
    expect(events).toContain('speech_start');
    expect(events).toContain('speech_end');
  });
});
