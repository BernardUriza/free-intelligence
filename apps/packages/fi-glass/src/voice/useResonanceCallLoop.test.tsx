// @vitest-environment jsdom
/**
 * useResonanceCallLoop — the error OUTPUT contract.
 *
 * Before `onError` existed, the loop's only reaction to a failed phase was a
 * `console.warn` plus a debug event: a consumer had no way to learn that STT or
 * TTS was unreachable, so an outage looked exactly like a silent model. These
 * tests pin the reporting, not the turn-taking (the state machine has its own
 * suites in resonanceCallController / resonanceEffects).
 */

import { describe, it, expect, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useResonanceCallLoop, type ResonanceCallAdapters } from './useResonanceCallLoop';

function adapters(over: Partial<ResonanceCallAdapters> = {}): ResonanceCallAdapters {
  return {
    openMic: vi.fn(),
    closeMic: vi.fn(),
    beginTranscribe: vi.fn().mockResolvedValue('hola'),
    invokeAgent: vi.fn().mockResolvedValue('respuesta'),
    speak: vi.fn(),
    stopSpeaking: vi.fn(),
    appendUserMessage: vi.fn(),
    ...over,
  };
}

async function startWith(a: ResonanceCallAdapters) {
  const hook = renderHook(() => useResonanceCallLoop({ enabled: true, adapters: a }));
  await act(async () => { await hook.result.current.startCall(); });
  return hook;
}

describe('onError', () => {
  it('reports a mic failure as FATAL — the call hung up, nothing is retried', async () => {
    const onError = vi.fn();
    const boom = new Error('NotAllowedError: permiso denegado');
    await startWith(adapters({ openMic: vi.fn().mockRejectedValue(boom), onError }));

    expect(onError).toHaveBeenCalledWith('mic', boom, true);
  });

  it('stays silent while every phase succeeds', async () => {
    const onError = vi.fn();
    await startWith(adapters({ onError }));

    expect(onError).not.toHaveBeenCalled();
  });

  it('is optional — a consumer that never passes it does not crash', async () => {
    const a = adapters({ openMic: vi.fn().mockRejectedValue(new Error('x')) });
    await expect(startWith(a)).resolves.toBeDefined();
  });
});
