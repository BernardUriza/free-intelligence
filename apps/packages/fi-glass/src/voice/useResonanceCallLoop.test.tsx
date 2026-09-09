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

import { describe, it, expect, vi, afterEach } from 'vitest';
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
  const hook = renderHook(() =>
    useResonanceCallLoop({ enabled: true, adapters: a, getAudioLevel: () => 0 }),
  );
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

// --- El techo de duración -----------------------------------------------------
//
// `idleHangupMs` NO es un techo: sólo se arma en `silence_hold`, así que a quien
// no deja de hablar nunca se le cuelga. Los upstreams de voz se aprovisionan por
// requests-por-minuto (susurro: 3 RPM, techo duro de la suscripción), de modo que
// una llamada sin tope puede dejar sin servicio a los demás consumidores.

describe('maxCallMs', () => {
  afterEach(() => { vi.useRealTimers(); });

  it('cuelga por RELOJ aunque el estado nunca pase por silence_hold', async () => {
    vi.useFakeTimers();
    const onError = vi.fn();
    const a = adapters({ onError });
    const hook = renderHook(() =>
      useResonanceCallLoop({
        enabled: true,
        adapters: a,
        getAudioLevel: () => 200, // hablando: el idle hangup jamás se arma
        sleepPolicy: { enabled: true, idleHangupMs: 300_000, maxCallMs: 60_000 },
      }),
    );
    await act(async () => { await hook.result.current.startCall(); });

    expect(onError).not.toHaveBeenCalled();
    await act(async () => { vi.advanceTimersByTime(60_000); });

    expect(onError).toHaveBeenCalledWith('duration', expect.any(Error), true);
    expect(onError.mock.calls[0][1].message).toContain('1 minuto');
    expect(hook.result.current.isActive).toBe(false);
  });

  it('maxCallMs 0 desactiva el techo', async () => {
    vi.useFakeTimers();
    const onError = vi.fn();
    const hook = renderHook(() =>
      useResonanceCallLoop({
        enabled: true,
        adapters: adapters({ onError }),
        getAudioLevel: () => 200,
        sleepPolicy: { enabled: true, idleHangupMs: 300_000, maxCallMs: 0 },
      }),
    );
    await act(async () => { await hook.result.current.startCall(); });
    await act(async () => { vi.advanceTimersByTime(3_600_000); });

    expect(onError).not.toHaveBeenCalled();
  });
});

