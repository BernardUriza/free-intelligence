'use client';

// B3-VOICE-FIGLASS-9 — Audio queue management hook.
// Reads artifacts from IndexedDB, exposes transcribe/retry/delete/clear actions.
// Transcription is always explicit — never auto-triggered.

import { useState, useEffect, useCallback } from 'react';
import type { VoiceAdapter } from '@free-intelligence/core';
import type { AudioQueueStore } from './AudioQueueStore';
import type { AudioArtifact } from './audioArtifact';
import { isPending } from './audioArtifact';

export interface UseAudioQueueOptions {
  store: AudioQueueStore;
  adapter?: VoiceAdapter;
  onTranscribed?: (id: string, text: string) => void;
  onError?: (id: string, message: string) => void;
}

export interface UseAudioQueueReturn {
  artifacts: AudioArtifact[];
  totalBytes: number;
  isLoading: boolean;
  // Transcribe one queued/failed artifact
  transcribeArtifact: (id: string) => Promise<void>;
  // Retry a failed transcription
  retryTranscription: (id: string) => Promise<void>;
  // Create a playback object URL for an artifact (caller must revoke when done)
  getPlaybackUrl: (id: string) => Promise<string | null>;
  // Remove an artifact from the queue and IndexedDB
  deleteArtifact: (id: string) => Promise<void>;
  // Remove all transcribed artifacts from IndexedDB
  clearTranscribed: () => Promise<void>;
  // Reload from IndexedDB (call after useDurableRecording saves a new artifact)
  reload: () => Promise<void>;
}

export function useAudioQueue(opts: UseAudioQueueOptions): UseAudioQueueReturn {
  const { store, adapter, onTranscribed, onError } = opts;
  const [artifacts, setArtifacts] = useState<AudioArtifact[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadFromStore = useCallback(async () => {
    try {
      const stored = await store.list();
      // Strip blob from in-memory state — blobs stay in IndexedDB only
      const metas: AudioArtifact[] = stored
        .filter((a) => a.state !== 'deleted')
        .map(({ blob: _blob, ...meta }) => meta)
        .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
      setArtifacts(metas);
    } catch {}
    setIsLoading(false);
  }, [store]);

  useEffect(() => {
    loadFromStore();
  }, [loadFromStore]);

  const patchLocal = useCallback(
    (id: string, patch: Partial<AudioArtifact>) => {
      setArtifacts((prev) =>
        prev.map((a) =>
          a.id === id
            ? { ...a, ...patch, updatedAt: new Date().toISOString() }
            : a,
        ),
      );
    },
    [],
  );

  const doTranscribe = useCallback(
    async (id: string) => {
      if (!adapter?.transcribe) {
        onError?.(id, 'Adaptador de voz sin capacidad de transcripción.');
        return;
      }

      patchLocal(id, { state: 'transcribing', errorMessage: undefined });
      await store.updateMeta(id, { state: 'transcribing', errorMessage: undefined });

      const stored = await store.get(id);
      if (!stored) {
        patchLocal(id, { state: 'failed', errorMessage: 'Artefacto no encontrado.' });
        onError?.(id, 'Artefacto no encontrado.');
        return;
      }

      patchLocal(id, { state: 'uploading' });
      await store.updateMeta(id, { state: 'uploading' });

      try {
        const { text } = await adapter.transcribe(stored.blob);
        patchLocal(id, { state: 'transcribed', transcript: text });
        await store.updateMeta(id, { state: 'transcribed', transcript: text });
        onTranscribed?.(id, text);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Transcripción fallida.';
        patchLocal(id, { state: 'failed', errorMessage: msg });
        await store.updateMeta(id, { state: 'failed', errorMessage: msg });
        onError?.(id, msg);
      }
    },
    [adapter, store, patchLocal, onTranscribed, onError],
  );

  const transcribeArtifact = useCallback(
    async (id: string) => {
      const a = artifacts.find((x) => x.id === id);
      if (!a || (a.state !== 'queued' && a.state !== 'saved')) return;
      await doTranscribe(id);
    },
    [artifacts, doTranscribe],
  );

  const retryTranscription = useCallback(
    async (id: string) => {
      const a = artifacts.find((x) => x.id === id);
      if (!a || a.state !== 'failed') return;
      await doTranscribe(id);
    },
    [artifacts, doTranscribe],
  );

  const getPlaybackUrl = useCallback(
    async (id: string): Promise<string | null> => {
      const stored = await store.get(id);
      if (!stored?.blob || stored.blob.size === 0) return null;
      return URL.createObjectURL(stored.blob);
    },
    [store],
  );

  const deleteArtifact = useCallback(
    async (id: string) => {
      await store.delete(id);
      setArtifacts((prev) => prev.filter((a) => a.id !== id));
    },
    [store],
  );

  const clearTranscribed = useCallback(async () => {
    const toDelete = artifacts.filter((a) => a.state === 'transcribed');
    await Promise.all(toDelete.map((a) => store.delete(a.id)));
    setArtifacts((prev) => prev.filter((a) => a.state !== 'transcribed'));
  }, [artifacts, store]);

  const reload = useCallback(async () => {
    setIsLoading(true);
    await loadFromStore();
  }, [loadFromStore]);

  const totalBytes = artifacts
    .filter(isPending)
    .reduce((s, a) => s + a.size, 0);

  return {
    artifacts,
    totalBytes,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    getPlaybackUrl,
    deleteArtifact,
    clearTranscribed,
    reload,
  };
}
