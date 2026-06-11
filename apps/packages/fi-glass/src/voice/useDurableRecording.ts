'use client';

// B3-VOICE-FIGLASS-9 — Durable local audio capture hook.
// Separates capture from transcription: record → pause/resume → stop → save to
// IndexedDB queue. Transcription is a separate action (useAudioQueue).
// Never auto-transcribes on stop. Never persists blob as object URL.

import { useState, useRef, useCallback, useEffect } from 'react';
import type { AudioQueueStore } from './AudioQueueStore';
import type { AudioArtifact, AudioQueuePolicy } from './audioArtifact';
import {
  makeArtifactId,
  AUDIO_QUEUE_DEFAULTS,
} from './audioArtifact';
import { useAudioAnalysis } from './useAudioAnalysis';

export interface UseDurableRecordingOptions {
  store: AudioQueueStore;
  policy?: AudioQueuePolicy;
  deviceId?: string | null;
  onSaved?: (artifact: AudioArtifact) => void;
  onError?: (message: string) => void;
}

export interface UseDurableRecordingReturn {
  // Active artifact being recorded (null when idle)
  artifact: AudioArtifact | null;
  recordingTime: number;
  // Visualizer data (0..1 normalized bands)
  bands: number[];
  audioLevel: number;
  isSilent: boolean;
  // Actions
  startRecording: () => Promise<void>;
  pauseRecording: () => void;
  resumeRecording: () => void;
  stopRecording: () => Promise<AudioArtifact | null>;
  cancelRecording: () => void;
  isAtCapacity: boolean;
}

const MIC_TIMEOUT_MS = 15000;

// RecordRTC instance type (lib has no TS declarations — kept minimal).
interface RTCInstance {
  startRecording(): void;
  pauseRecording(): void;
  resumeRecording(): void;
  stopRecording(cb: () => void): void;
  getBlob(): Blob;
  getState(): string;
}

// RecordRTC is loaded lazily (optional peer dep) only when actually recording.
async function loadRecordRTC(): Promise<{ new(stream: MediaStream, opts: Record<string, unknown>): RTCInstance; StereoAudioRecorder: unknown }> {
  const mod: any = await import('recordrtc');
  const RTC = mod.default ?? mod.RecordRTC ?? mod;
  if (!RTC || typeof RTC !== 'function') {
    throw new Error('[useDurableRecording] RecordRTC not available');
  }
  return RTC;
}

export function useDurableRecording(
  opts: UseDurableRecordingOptions,
): UseDurableRecordingReturn {
  const {
    store,
    policy = AUDIO_QUEUE_DEFAULTS,
    deviceId = null,
    onSaved,
    onError,
  } = opts;

  const [artifact, setArtifact] = useState<AudioArtifact | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [currentStream, setCurrentStream] = useState<MediaStream | null>(null);
  const [isAtCapacity, setIsAtCapacity] = useState(false);

  const recorderRef = useRef<RTCInstance | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);
  const pausedElapsedRef = useRef<number>(0);
  const artifactRef = useRef<AudioArtifact | null>(null);

  // Keep ref in sync with state for callbacks
  useEffect(() => {
    artifactRef.current = artifact;
  }, [artifact]);

  // Check capacity against store on mount and when policy changes
  useEffect(() => {
    store.list().then((stored) => {
      const pending = stored.filter(
        (a) => a.state !== 'transcribed' && a.state !== 'deleted',
      );
      const totalBytes = pending.reduce((s, a) => s + a.size, 0);
      setIsAtCapacity(
        pending.length >= policy.maxItems || totalBytes >= policy.maxBytes,
      );
    }).catch(() => {});
  }, [store, policy]);

  const { audioLevel, isSilent, bands } = useAudioAnalysis(currentStream, {
    isActive: artifact?.state === 'recording',
  });

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const releaseStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setCurrentStream(null);
    }
  }, []);

  const updateArtifact = useCallback(
    (patch: Partial<AudioArtifact>) => {
      setArtifact((prev) => {
        if (!prev) return prev;
        const updated = { ...prev, ...patch, updatedAt: new Date().toISOString() };
        artifactRef.current = updated;
        return updated;
      });
    },
    [],
  );

  const startRecording = useCallback(async () => {
    if (artifact?.state === 'recording' || artifact?.state === 'paused') return;

    try {
      // Check capacity before requesting mic
      const stored = await store.list();
      const pending = stored.filter(
        (a) => a.state !== 'transcribed' && a.state !== 'deleted',
      );
      const totalBytes = pending.reduce((s, a) => s + a.size, 0);
      if (pending.length >= policy.maxItems || totalBytes >= policy.maxBytes) {
        setIsAtCapacity(true);
        onError?.(
          `Cola llena (máximo ${policy.maxItems} audios o ${Math.round(policy.maxBytes / 1024 / 1024)} MB). Transcribe o elimina audios antes de grabar.`,
        );
        return;
      }

      // Request microphone with timeout guard
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(
          () => reject(new Error('Permiso de micrófono expirado (15s).')),
          MIC_TIMEOUT_MS,
        ),
      );
      const audioConstraints: MediaTrackConstraints | boolean = deviceId
        ? { deviceId: { exact: deviceId } }
        : true;
      const stream = await Promise.race([
        navigator.mediaDevices.getUserMedia({ audio: audioConstraints }),
        timeoutPromise,
      ]);

      streamRef.current = stream;
      setCurrentStream(stream);

      const RecordRTC = await loadRecordRTC();
      const recorder = new RecordRTC(stream, {
        type: 'audio',
        recorderType: (RecordRTC as unknown as { StereoAudioRecorder: unknown }).StereoAudioRecorder,
        mimeType: 'audio/wav',
        numberOfAudioChannels: 1,
        desiredSampRate: 16000,
        disableLogs: true,
      });

      recorderRef.current = recorder;
      recorder.startRecording();

      const now = Date.now();
      startTimeRef.current = now;
      pausedElapsedRef.current = 0;
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime(
          Math.floor((Date.now() - startTimeRef.current) / 1000),
        );
      }, 1000);

      const newArtifact: AudioArtifact = {
        id: makeArtifactId(),
        mime: 'audio/wav',
        size: 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        state: 'recording',
      };
      setArtifact(newArtifact);
      artifactRef.current = newArtifact;
    } catch (err) {
      releaseStream();
      onError?.(err instanceof Error ? err.message : 'No se pudo iniciar la grabación.');
    }
  }, [artifact, store, policy, deviceId, onError, releaseStream]);

  const pauseRecording = useCallback(() => {
    if (artifactRef.current?.state !== 'recording') return;
    recorderRef.current?.pauseRecording();
    stopTimer();
    pausedElapsedRef.current = Date.now() - startTimeRef.current;
    updateArtifact({ state: 'paused' });
  }, [stopTimer, updateArtifact]);

  const resumeRecording = useCallback(() => {
    if (artifactRef.current?.state !== 'paused') return;
    recorderRef.current?.resumeRecording();
    // Resume the timer from where we paused
    startTimeRef.current = Date.now() - pausedElapsedRef.current;
    timerRef.current = setInterval(() => {
      setRecordingTime(
        Math.floor((Date.now() - startTimeRef.current) / 1000),
      );
    }, 1000);
    updateArtifact({ state: 'recording' });
  }, [updateArtifact]);

  const stopRecording = useCallback(async (): Promise<AudioArtifact | null> => {
    const current = artifactRef.current;
    if (current?.state !== 'recording' && current?.state !== 'paused') {
      return null;
    }

    stopTimer();
    const durationMs = Date.now() - startTimeRef.current + pausedElapsedRef.current;

    // Release mic immediately (before await — keeps browser mic indicator clean)
    releaseStream();

    return new Promise<AudioArtifact | null>((resolve) => {
      if (!recorderRef.current) {
        resolve(null);
        return;
      }

      recorderRef.current.stopRecording(async () => {
        const blob = recorderRef.current?.getBlob() ?? null;
        recorderRef.current = null;

        if (!blob || blob.size === 0) {
          updateArtifact({ state: 'failed', errorMessage: 'Grabación vacía.' });
          resolve(null);
          return;
        }

        if (blob.size > policy.maxBytesPerItem) {
          updateArtifact({
            state: 'failed',
            errorMessage: `Audio demasiado grande (${Math.round(blob.size / 1024 / 1024)} MB, máximo ${Math.round(policy.maxBytesPerItem / 1024 / 1024)} MB).`,
          });
          resolve(null);
          return;
        }

        const finalArtifact: AudioArtifact = {
          ...current!,
          size: blob.size,
          durationMs,
          state: 'queued',
          updatedAt: new Date().toISOString(),
        };

        updateArtifact({
          size: blob.size,
          durationMs,
          state: 'queued',
        });

        try {
          await store.put({ ...finalArtifact, blob });
          onSaved?.(finalArtifact);
          setIsAtCapacity(false); // will be rechecked next start
          resolve(finalArtifact);
        } catch (err) {
          const msg =
            err instanceof Error ? err.message : 'Error al guardar audio.';
          updateArtifact({ state: 'failed', errorMessage: msg });
          onError?.(msg);
          resolve(null);
        }
      });
    });
  }, [store, policy, releaseStream, stopTimer, updateArtifact, onSaved, onError]);

  const cancelRecording = useCallback(() => {
    stopTimer();
    releaseStream();
    if (recorderRef.current) {
      try {
        recorderRef.current.stopRecording(() => {});
      } catch {}
      recorderRef.current = null;
    }
    setArtifact(null);
    artifactRef.current = null;
    setRecordingTime(0);
  }, [stopTimer, releaseStream]);

  return {
    artifact,
    recordingTime,
    bands,
    audioLevel,
    isSilent,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    cancelRecording,
    isAtCapacity,
  };
}
