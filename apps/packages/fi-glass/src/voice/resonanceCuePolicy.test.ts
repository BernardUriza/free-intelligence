import { describe, it, expect } from 'vitest';

import { resonanceCuePolicy, type ResonanceCueAction } from './resonanceCuePolicy';
import type { ResonanceCallState, ResonanceCallEvent } from './resonanceCallMachine';

const p = (
  previousState: ResonanceCallState,
  nextState: ResonanceCallState,
  event: ResonanceCallEvent,
): ResonanceCueAction[] => resonanceCuePolicy({ previousState, nextState, event });

describe('resonanceCuePolicy — invariant 1: no cue fires when it should not', () => {
  it('plays nothing on call.started / mic.opened / silence events', () => {
    expect(p('idle', 'listening', 'call.started')).toEqual([]);
    expect(p('listening', 'listening', 'mic.opened')).toEqual([]);
    expect(p('listening', 'silence_hold', 'silence.detected')).toEqual([]);
    expect(p('silence_hold', 'listening', 'silence.resume')).toEqual([]);
  });

  it('does NOT play crystalline on user.speech.started (only on ended)', () => {
    expect(p('listening', 'listening', 'user.speech.started')).toEqual([]);
  });

  it('plays crystalline exactly once on user.speech.ended', () => {
    expect(p('listening', 'transcribing', 'user.speech.ended')).toEqual([
      { type: 'playOnce', cue: 'crystalline' },
    ]);
  });

  it('does NOT play ready on assistant.speech.started (only on completed)', () => {
    expect(p('thinking', 'speaking', 'assistant.speech.started')).toEqual([
      { type: 'stopLoop', cue: 'thinking' },
    ]);
  });

  it('plays ready exactly once on assistant.speech.completed', () => {
    expect(p('speaking', 'silence_hold', 'assistant.speech.completed')).toEqual([
      { type: 'playOnce', cue: 'ready' },
    ]);
  });
});

describe('resonanceCuePolicy — invariant 2: thinking loop can never hang', () => {
  it('starts the loop only on ENTERING thinking', () => {
    expect(p('transcribing', 'thinking', 'stt.completed')).toEqual([
      { type: 'playLoop', cue: 'thinking' },
    ]);
  });

  it('does NOT restart the loop while staying in thinking', () => {
    expect(p('thinking', 'thinking', 'mic.opened')).toEqual([]);
  });

  it('stops the loop on EVERY exit from thinking (event-agnostic)', () => {
    const exits: Array<[ResonanceCallState, ResonanceCallEvent]> = [
      ['speaking', 'assistant.speech.started'],
      ['listening', 'error.recoverable'],
      ['interrupted', 'assistant.speech.interrupted'],
    ];
    for (const [next, event] of exits) {
      expect(p('thinking', next, event)).toContainEqual({ type: 'stopLoop', cue: 'thinking' });
    }
  });

  it('thinking -> ended emits stopAll (which silences the loop)', () => {
    expect(p('thinking', 'ended', 'call.ended')).toEqual([{ type: 'stopAll' }]);
  });
});

describe('resonanceCuePolicy — invariant 3: everything stops on call exit', () => {
  it('stopAll on call.ended, error.fatal, and any transition to ended', () => {
    expect(p('speaking', 'ended', 'call.ended')).toEqual([{ type: 'stopAll' }]);
    expect(p('transcribing', 'ended', 'error.fatal')).toEqual([{ type: 'stopAll' }]);
    expect(p('listening', 'ended', 'error.fatal')).toEqual([{ type: 'stopAll' }]);
  });

  it('teardown short-circuits — no one-shot leaks alongside stopAll', () => {
    // even if an end-of-speech somehow coincided with teardown, only stopAll runs
    expect(p('thinking', 'ended', 'call.ended')).toEqual([{ type: 'stopAll' }]);
  });
});
