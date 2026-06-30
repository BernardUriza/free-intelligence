// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import type { VoiceAdapter } from '@free-intelligence/core';
import type { StoredAudioArtifact } from './audioArtifact';
import type { AudioQueueStore } from './AudioQueueStore';
import { useAudioQueue } from './useAudioQueue';

// ---------------------------------------------------------------------------
// Fake store — in-memory Map, no IndexedDB
// ---------------------------------------------------------------------------
function makeFakeStore(): AudioQueueStore {
  const mem = new Map<string, StoredAudioArtifact>();
  return {
    list: vi.fn(async () => [...mem.values()]),
    get: vi.fn(async (id: string) => mem.get(id) ?? null),
    put: vi.fn(async (a: StoredAudioArtifact) => { mem.set(a.id, a); }),
    updateMeta: vi.fn(async (id: string, patch: Partial<StoredAudioArtifact>) => {
      const existing = mem.get(id);
      if (existing) mem.set(id, { ...existing, ...patch });
    }),
    delete: vi.fn(async (id: string) => { mem.delete(id); }),
    clear: vi.fn(async () => { mem.clear(); }),
  } as unknown as AudioQueueStore;
}

const wavBlob = new Blob(['wav'], { type: 'audio/wav' });

function seedArtifact(
  store: AudioQueueStore,
  id: string,
  state: StoredAudioArtifact['state'] = 'queued',
) {
  const a: StoredAudioArtifact = {
    id,
    mime: 'audio/wav',
    size: 512,
    createdAt: '2026-06-11T00:00:00.000Z',
    updatedAt: '2026-06-11T00:00:00.000Z',
    state,
    blob: wavBlob,
  };
  (store.put as ReturnType<typeof vi.fn>).mockImplementationOnce(() => {
    (store.list as ReturnType<typeof vi.fn>).mockResolvedValue(
      [a, ...((store as any)._items ?? [])],
    );
  });
  // Easier: just push to the underlying store directly
  (store as any).list = vi.fn(async () => [a]);
  return a;
}

describe('useAudioQueue', () => {
  let store: AudioQueueStore;

  beforeEach(() => {
    store = makeFakeStore();
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:fake-url'),
      revokeObjectURL: vi.fn(),
    });
  });

  it('loads artifacts from store on mount', async () => {
    const a: StoredAudioArtifact = {
      id: 'a1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([a]);

    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});
    expect(result.current.artifacts).toHaveLength(1);
    expect(result.current.artifacts[0].id).toBe('a1');
  });

  it('strips deleted artifacts from memory state', async () => {
    const deleted: StoredAudioArtifact = {
      id: 'd1',
      mime: 'audio/wav',
      size: 0,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'deleted',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([deleted]);

    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});
    expect(result.current.artifacts).toHaveLength(0);
  });

  it('deleteArtifact removes from store and local state', async () => {
    const a: StoredAudioArtifact = {
      id: 'a1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([a]);

    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});
    expect(result.current.artifacts).toHaveLength(1);

    await act(async () => {
      await result.current.deleteArtifact('a1');
    });
    expect(store.delete).toHaveBeenCalledWith('a1');
    expect(result.current.artifacts).toHaveLength(0);
  });

  it('transcribeArtifact calls adapter.transcribe and updates state to transcribed', async () => {
    const a: StoredAudioArtifact = {
      id: 'a1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([a]);
    vi.mocked(store.get).mockResolvedValue(a);

    const transcribe = vi.fn(async () => ({ text: 'hola mundo' }));
    const adapter: VoiceAdapter = {
      defaultVoice: 'nova',
      availableVoices: [],
      transcribe,
    };
    const onTranscribed = vi.fn();

    const { result } = renderHook(() =>
      useAudioQueue({ store, adapter, onTranscribed }),
    );
    await act(async () => {});

    await act(async () => {
      await result.current.transcribeArtifact('a1');
    });

    expect(transcribe).toHaveBeenCalledWith(wavBlob);
    expect(onTranscribed).toHaveBeenCalledWith('a1', 'hola mundo');
    const updated = result.current.artifacts.find((x) => x.id === 'a1');
    expect(updated?.state).toBe('transcribed');
    expect(updated?.transcript).toBe('hola mundo');
  });

  it('transcribeArtifact marks failed on adapter error', async () => {
    const a: StoredAudioArtifact = {
      id: 'a1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([a]);
    vi.mocked(store.get).mockResolvedValue(a);

    const adapter: VoiceAdapter = {
      defaultVoice: 'nova',
      availableVoices: [],
      transcribe: vi.fn(async () => { throw new Error('network timeout'); }),
    };
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useAudioQueue({ store, adapter, onError }),
    );
    await act(async () => {});

    await act(async () => {
      await result.current.transcribeArtifact('a1');
    });

    const updated = result.current.artifacts.find((x) => x.id === 'a1');
    expect(updated?.state).toBe('failed');
    expect(updated?.errorMessage).toContain('network timeout');
    expect(onError).toHaveBeenCalledWith('a1', 'network timeout');
  });

  it('transcribeArtifact is no-op when adapter has no transcribe', async () => {
    const a: StoredAudioArtifact = {
      id: 'a1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([a]);

    const onError = vi.fn();
    const { result } = renderHook(() => useAudioQueue({ store, onError }));
    await act(async () => {});

    await act(async () => {
      await result.current.transcribeArtifact('a1');
    });
    expect(onError).toHaveBeenCalledWith('a1', expect.stringContaining('transcripción'));
  });

  it('clearTranscribed removes only transcribed artifacts from store', async () => {
    const q: StoredAudioArtifact = {
      id: 'q1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    const t: StoredAudioArtifact = {
      id: 't1',
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:01:00.000Z',
      updatedAt: '2026-06-11T00:01:00.000Z',
      state: 'transcribed',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([q, t]);

    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});
    expect(result.current.artifacts).toHaveLength(2);

    await act(async () => {
      await result.current.clearTranscribed();
    });
    expect(store.delete).toHaveBeenCalledWith('t1');
    expect(store.delete).not.toHaveBeenCalledWith('q1');
    expect(result.current.artifacts.find((x) => x.id === 't1')).toBeUndefined();
    expect(result.current.artifacts.find((x) => x.id === 'q1')).toBeDefined();
  });

  it('totalBytes sums only pending artifacts', async () => {
    const pending: StoredAudioArtifact = {
      id: 'p1',
      mime: 'audio/wav',
      size: 1024,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'queued',
      blob: wavBlob,
    };
    const done: StoredAudioArtifact = {
      id: 'd1',
      mime: 'audio/wav',
      size: 2048,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state: 'transcribed',
      blob: wavBlob,
    };
    vi.mocked(store.list).mockResolvedValue([pending, done]);

    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});
    // Only pending item's bytes
    expect(result.current.totalBytes).toBe(1024);
  });

  // B3-VOICE-FIGLASS-19 — archive ("mark as sent to chat")
  function makeStored(
    id: string,
    state: StoredAudioArtifact['state'],
  ): StoredAudioArtifact {
    return {
      id,
      mime: 'audio/wav',
      size: 512,
      createdAt: '2026-06-11T00:00:00.000Z',
      updatedAt: '2026-06-11T00:00:00.000Z',
      state,
      blob: wavBlob,
    };
  }

  it('archiveArtifact moves a transcribed artifact to archived and persists it', async () => {
    vi.mocked(store.list).mockResolvedValue([makeStored('t1', 'transcribed')]);
    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});

    await act(async () => { await result.current.archiveArtifact('t1'); });

    expect(result.current.artifacts[0].state).toBe('archived');
    expect(store.updateMeta).toHaveBeenCalledWith('t1', { state: 'archived' });
  });

  it('archiveArtifact refuses non-transcribed artifacts', async () => {
    vi.mocked(store.list).mockResolvedValue([makeStored('q1', 'queued')]);
    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});

    await act(async () => { await result.current.archiveArtifact('q1'); });

    expect(result.current.artifacts[0].state).toBe('queued');
    expect(store.updateMeta).not.toHaveBeenCalled();
  });

  it('clearTranscribed also purges archived artifacts', async () => {
    vi.mocked(store.list).mockResolvedValue([
      makeStored('t1', 'transcribed'),
      makeStored('ar1', 'archived'),
      makeStored('q1', 'queued'),
    ]);
    const { result } = renderHook(() => useAudioQueue({ store }));
    await act(async () => {});

    await act(async () => { await result.current.clearTranscribed(); });

    expect(store.delete).toHaveBeenCalledWith('t1');
    expect(store.delete).toHaveBeenCalledWith('ar1');
    expect(store.delete).not.toHaveBeenCalledWith('q1');
    expect(result.current.artifacts.map((a) => a.id)).toEqual(['q1']);
  });
});
