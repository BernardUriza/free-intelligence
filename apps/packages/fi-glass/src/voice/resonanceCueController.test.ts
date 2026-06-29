import { describe, it, expect, vi } from 'vitest';

import { createResonanceCueController, type ResonanceCuePlayer } from './resonanceCueController';

function mockPlayer(): ResonanceCuePlayer {
  return {
    playOnce: vi.fn(),
    playLoop: vi.fn(),
    stopLoop: vi.fn(),
    stopAll: vi.fn(),
  };
}

describe('resonanceCueController', () => {
  it('starts the thinking loop once on entering thinking', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    c.applyTransition({ previousState: 'transcribing', nextState: 'thinking', event: 'stt.completed' });
    expect(player.playLoop).toHaveBeenCalledExactlyOnceWith('thinking');
  });

  it('playLoop is idempotent — a repeated enter-thinking does not stack sources', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    c.applyTransition({ previousState: 'transcribing', nextState: 'thinking', event: 'stt.completed' });
    c.applyTransition({ previousState: 'transcribing', nextState: 'thinking', event: 'stt.completed' });
    expect(player.playLoop).toHaveBeenCalledTimes(1);
  });

  it('stops the loop on exit and clears it from active loops', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    c.applyTransition({ previousState: 'transcribing', nextState: 'thinking', event: 'stt.completed' });
    c.applyTransition({ previousState: 'thinking', nextState: 'speaking', event: 'assistant.speech.started' });
    expect(player.stopLoop).toHaveBeenCalledExactlyOnceWith('thinking');
    // stopLoop again with no active loop is a no-op (best-effort)
    c.applyTransition({ previousState: 'speaking', nextState: 'listening', event: 'assistant.speech.interrupted' });
    expect(player.stopLoop).toHaveBeenCalledTimes(1);
  });

  it('plays crystalline on user.speech.ended and ready on assistant.speech.completed', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    c.applyTransition({ previousState: 'listening', nextState: 'transcribing', event: 'user.speech.ended' });
    c.applyTransition({ previousState: 'speaking', nextState: 'silence_hold', event: 'assistant.speech.completed' });
    expect(player.playOnce).toHaveBeenNthCalledWith(1, 'crystalline');
    expect(player.playOnce).toHaveBeenNthCalledWith(2, 'ready');
  });

  it('dedupes a one-shot replayed with the SAME eventId', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    const t = { previousState: 'listening', nextState: 'transcribing', event: 'user.speech.ended' } as const;
    c.applyTransition(t, 'evt-1');
    c.applyTransition(t, 'evt-1');
    expect(player.playOnce).toHaveBeenCalledTimes(1);
  });

  it('plays again for a DIFFERENT eventId (two real turns)', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    const t = { previousState: 'listening', nextState: 'transcribing', event: 'user.speech.ended' } as const;
    c.applyTransition(t, 'evt-1');
    c.applyTransition(t, 'evt-2');
    expect(player.playOnce).toHaveBeenCalledTimes(2);
  });

  it('stopAll on call.ended clears active loops; calling stopAll again is safe', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    c.applyTransition({ previousState: 'transcribing', nextState: 'thinking', event: 'stt.completed' });
    c.applyTransition({ previousState: 'thinking', nextState: 'ended', event: 'call.ended' });
    expect(player.stopAll).toHaveBeenCalledTimes(1);
    c.stopAll();
    expect(player.stopAll).toHaveBeenCalledTimes(2); // idempotent, no throw
    // after teardown a fresh enter-thinking still works (loop was cleared)
    c.applyTransition({ previousState: 'transcribing', nextState: 'thinking', event: 'stt.completed' });
    expect(player.playLoop).toHaveBeenCalledTimes(2);
  });

  it('reset clears one-shot dedupe so a new session can replay cues', () => {
    const player = mockPlayer();
    const c = createResonanceCueController(player);
    const t = { previousState: 'listening', nextState: 'transcribing', event: 'user.speech.ended' } as const;
    c.applyTransition(t, 'evt-1');
    c.reset();
    c.applyTransition(t, 'evt-1');
    expect(player.playOnce).toHaveBeenCalledTimes(2);
  });
});
