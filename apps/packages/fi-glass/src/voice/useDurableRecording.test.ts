// @vitest-environment jsdom
/**
 * useDurableRecording — state machine + persistence failure contract.
 *
 * Key invariants under test:
 * 1. Successful stop → artifact state = 'queued', store.put called.
 * 2. IndexedDB failure on stop → artifact state = 'failed', NOT 'saved'/'queued'.
 * 3. Mic stream released BEFORE store.put (even when store throws).
 * 4. cancelRecording → artifact cleared, mic released.
 * 5. pauseRecording / resumeRecording → state transitions without losing artifact id.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import type { AudioQueueStore } from './AudioQueueStore';
import { useDurableRecording } from './useDurableRecording';

// ---------------------------------------------------------------------------
// RecordRTC mock (hoisted — must be before any import that triggers the module)
// ---------------------------------------------------------------------------
vi.mock('recordrtc', () => {
  const stopCbs: (() => void)[] = [];
  let shouldCallStop = true;

  class FakeRTC {
    static StereoAudioRecorder = class {};
    private blob: Blob;

    constructor(_stream: MediaStream, _opts: unknown) {
      this.blob = new Blob(['wav-data'], { type: 'audio/wav' });
    }
    startRecording() {}
    pauseRecording() {}
    resumeRecording() {}
    stopRecording(cb: () => void) {
      stopCbs.push(cb);
      if (shouldCallStop) cb();
    }
    getBlob() {
      return this.blob;
    }
    getState() {
      return 'stopped';
    }
  }

  return { default: FakeRTC };
});

// ---------------------------------------------------------------------------
// Fake store
// ---------------------------------------------------------------------------
function makeFakeStore(putShouldThrow = false): AudioQueueStore {
  return {
    list: vi.fn(async () => []),
    get: vi.fn(async () => null),
    put: vi.fn(async () => {
      if (putShouldThrow) throw new Error('QuotaExceededError: disk full');
    }),
    updateMeta: vi.fn(async () => {}),
    delete: vi.fn(async () => {}),
    clear: vi.fn(async () => {}),
  } as unknown as AudioQueueStore;
}

// ---------------------------------------------------------------------------
// MediaStream mock
// ---------------------------------------------------------------------------
let trackStopCalls = 0;
function makeFakeStream(): MediaStream {
  return {
    getTracks: () => [
      {
        stop: () => {
          trackStopCalls++;
        },
      },
    ],
  } as unknown as MediaStream;
}

// Minimal Web Audio stub — jsdom has no AudioContext.
// Must be a class (not arrow fn) because useAudioAnalysis calls `new AudioContext()`.
class FakeAudioContext {
  createAnalyser() {
    return {
      fftSize: 0,
      frequencyBinCount: 128,
      getByteFrequencyData: vi.fn(),
      connect: vi.fn(),
    };
  }
  createGain() {
    return { gain: { value: 1 }, connect: vi.fn() };
  }
  createMediaStreamSource() {
    return { connect: vi.fn() };
  }
  close = vi.fn();
  state = 'running';
}

beforeEach(() => {
  trackStopCalls = 0;
  vi.stubGlobal('AudioContext', FakeAudioContext);
  vi.stubGlobal('navigator', {
    mediaDevices: {
      getUserMedia: vi.fn(async () => makeFakeStream()),
    },
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useDurableRecording — successful stop', () => {
  it('artifact ends in queued state when store.put succeeds', async () => {
    const store = makeFakeStore(false);
    const onSaved = vi.fn();
    const { result } = renderHook(() =>
      useDurableRecording({ store, onSaved }),
    );

    await act(async () => { await result.current.startRecording(); });
    expect(result.current.artifact?.state).toBe('recording');

    let returnedArtifact: unknown;
    await act(async () => {
      returnedArtifact = await result.current.stopRecording();
    });

    expect(result.current.artifact?.state).toBe('queued');
    expect(store.put).toHaveBeenCalledOnce();
    expect(onSaved).toHaveBeenCalledOnce();
    expect(returnedArtifact).not.toBeNull();
  });
});

describe('useDurableRecording — IndexedDB failure', () => {
  it('artifact state = failed (not saved/queued) when store.put throws', async () => {
    const store = makeFakeStore(true); // put throws QuotaExceededError
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useDurableRecording({ store, onError }),
    );

    await act(async () => { await result.current.startRecording(); });
    expect(result.current.artifact?.state).toBe('recording');

    let returnedArtifact: unknown;
    await act(async () => {
      returnedArtifact = await result.current.stopRecording();
    });

    // Must NOT appear as saved/queued — that would be a false positive
    expect(result.current.artifact?.state).toBe('failed');
    expect(result.current.artifact?.state).not.toBe('saved');
    expect(result.current.artifact?.state).not.toBe('queued');
    expect(returnedArtifact).toBeNull();
    expect(onError).toHaveBeenCalledWith(expect.stringContaining('QuotaExceededError'));
  });

  it('mic stream is released BEFORE store.put is called (even on failure)', async () => {
    let micReleasedBeforePut = false;
    const store: AudioQueueStore = {
      list: vi.fn(async () => []),
      get: vi.fn(async () => null),
      put: vi.fn(async () => {
        // At the moment put is called, the mic track should already be stopped
        micReleasedBeforePut = trackStopCalls > 0;
        throw new Error('storage error');
      }),
      updateMeta: vi.fn(async () => {}),
      delete: vi.fn(async () => {}),
      clear: vi.fn(async () => {}),
    } as unknown as AudioQueueStore;

    const { result } = renderHook(() => useDurableRecording({ store }));

    await act(async () => { await result.current.startRecording(); });
    await act(async () => { await result.current.stopRecording(); });

    expect(micReleasedBeforePut).toBe(true);
    expect(trackStopCalls).toBeGreaterThan(0);
  });
});

describe('useDurableRecording — pause / resume', () => {
  it('pause changes state to paused without losing artifact id', async () => {
    const store = makeFakeStore(false);
    const { result } = renderHook(() => useDurableRecording({ store }));

    await act(async () => { await result.current.startRecording(); });
    const id = result.current.artifact?.id;

    act(() => { result.current.pauseRecording(); });
    expect(result.current.artifact?.state).toBe('paused');
    expect(result.current.artifact?.id).toBe(id);
  });

  it('resume restores recording state', async () => {
    const store = makeFakeStore(false);
    const { result } = renderHook(() => useDurableRecording({ store }));

    await act(async () => { await result.current.startRecording(); });
    act(() => { result.current.pauseRecording(); });
    act(() => { result.current.resumeRecording(); });

    expect(result.current.artifact?.state).toBe('recording');
  });
});

describe('useDurableRecording — cancel', () => {
  it('cancelRecording clears artifact and releases mic', async () => {
    const store = makeFakeStore(false);
    const { result } = renderHook(() => useDurableRecording({ store }));

    await act(async () => { await result.current.startRecording(); });
    expect(result.current.artifact).not.toBeNull();

    act(() => { result.current.cancelRecording(); });

    expect(result.current.artifact).toBeNull();
    expect(trackStopCalls).toBeGreaterThan(0);
  });
});
