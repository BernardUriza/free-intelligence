'use client';

// B3-VOICE-FIGLASS-9 — Durable local audio capture hook.
// Separates capture from transcription: record → pause/resume → stop → save to
// IndexedDB queue. Transcription is a separate action (useAudioQueue).
// Never auto-transcribes on stop. Never persists blob as object URL.
//
// B3-VOICE-FIGLASS-18 — Segmented pause. RecordRTC cannot yield a partial blob
// mid-recording, so "pause" actually STOPS the live recorder (which yields a
// complete WAV segment) while keeping the mic stream alive; "resume" starts a
// fresh recorder on the same stream. Segments are spliced (mergeWavBlobs) into
// the final WAV on stop — and, while paused, into `pausedPreviewBlob`, so the
// UI can play back everything recorded so far before deciding to resume,
// discard, or save.

import { useState, useRef, useCallback, useEffect } from 'react';
import type { AudioQueueStore } from './AudioQueueStore';
import type { AudioArtifact, AudioQueuePolicy } from './audioArtifact';
import {
  makeArtifactId,
  isPending,
  AUDIO_QUEUE_DEFAULTS,
} from './audioArtifact';
import { useAudioAnalysis } from './useAudioAnalysis';
import { mergeWavBlobs } from './wav';

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
  /** Everything recorded so far, available while state === 'paused' (null
   * otherwise). A complete playable WAV — feed it to a player as a preview. */
  pausedPreviewBlob: Blob | null;
  // Visualizer data (0..1 normalized bands)
  bands: number[];
  audioLevel: number;
  isSilent: boolean;
  // True while getUserMedia is in-flight (pressed mic, waiting for permission)
  isStarting: boolean;
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
  const [isStarting, setIsStarting] = useState(false);
  const [pausedPreviewBlob, setPausedPreviewBlob] = useState<Blob | null>(null);

  const recorderRef = useRef<RTCInstance | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);
  const pausedElapsedRef = useRef<number>(0);
  const artifactRef = useRef<AudioArtifact | null>(null);
  // Segmented pause (B3-VOICE-FIGLASS-18): completed WAV segments, the ctor
  // cached for mid-session recorder restarts, and the in-flight pause stop —
  // resume/stop await it so a segment is never lost to the async RecordRTC
  // callback racing the next action.
  const segmentsRef = useRef<Blob[]>([]);
  const rtcCtorRef = useRef<Awaited<ReturnType<typeof loadRecordRTC>> | null>(null);
  const pauseOpRef = useRef<Promise<void>>(Promise.resolve());

  // Keep ref in sync with state for callbacks
  useEffect(() => {
    artifactRef.current = artifact;
  }, [artifact]);

  // Check capacity against store on mount and when policy changes
  useEffect(() => {
    store.list().then((stored) => {
      const pending = stored.filter(isPending);
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
      // The ref must advance SYNCHRONOUSLY: the segmented-pause microtasks
      // (segment collection, preview splice, resume's recorder restart) read
      // it before React flushes the state update — a render-time ref would
      // still show the previous state and make them bail.
      const prev = artifactRef.current;
      if (!prev) return;
      const updated = { ...prev, ...patch, updatedAt: new Date().toISOString() };
      artifactRef.current = updated;
      setArtifact(updated);
    },
    [],
  );

  // Build and start a recorder on the live stream. Used at start and again on
  // every resume (segmented pause stops the previous instance for its blob).
  const startNewRecorderSegment = useCallback((stream: MediaStream): RTCInstance => {
    const RecordRTC = rtcCtorRef.current;
    if (!RecordRTC) throw new Error('[useDurableRecording] RecordRTC not loaded');
    const recorder = new RecordRTC(stream, {
      type: 'audio',
      recorderType: (RecordRTC as unknown as { StereoAudioRecorder: unknown }).StereoAudioRecorder,
      mimeType: 'audio/wav',
      numberOfAudioChannels: 1,
      desiredSampRate: 16000,
      disableLogs: true,
    });
    recorder.startRecording();
    return recorder;
  }, []);

  const startRecording = useCallback(async () => {
    if (artifact?.state === 'recording' || artifact?.state === 'paused') return;

    setIsStarting(true);
    try {
      // Check capacity before requesting mic
      const stored = await store.list();
      const pending = stored.filter(isPending);
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

      rtcCtorRef.current = await loadRecordRTC();
      segmentsRef.current = [];
      pauseOpRef.current = Promise.resolve();
      setPausedPreviewBlob(null);
      recorderRef.current = startNewRecorderSegment(stream);

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
    } finally {
      setIsStarting(false);
    }
  }, [artifact, store, policy, deviceId, onError, releaseStream, startNewRecorderSegment]);

  const pauseRecording = useCallback(() => {
    if (artifactRef.current?.state !== 'recording') return;
    stopTimer();
    pausedElapsedRef.current = Date.now() - startTimeRef.current;
    // B3-VOICE-FIGLASS-17: persist the elapsed time on the artifact so the
    // paused draft shows the real recorded duration instead of "--:--"
    // (durationMs used to be written only on stop).
    updateArtifact({ state: 'paused', durationMs: pausedElapsedRef.current });

    // B3-VOICE-FIGLASS-18: a real stop (not RecordRTC pause) — the only way to
    // get the audio out — yields this stretch as a complete WAV segment. The
    // mic stream stays alive so resume can start a fresh recorder instantly.
    const recorder = recorderRef.current;
    recorderRef.current = null;
    pauseOpRef.current = new Promise<void>((resolve) => {
      if (!recorder) {
        resolve();
        return;
      }
      recorder.stopRecording(() => {
        const segment = recorder.getBlob();
        if (segment && segment.size > 0) segmentsRef.current.push(segment);
        // Long recordings: the splice doubles the bytes in memory. Past the
        // per-item cap the final stop will reject the audio anyway, so skip
        // the preview (honest fallback) instead of building a doomed blob.
        const totalBytes = segmentsRef.current.reduce((s, b) => s + b.size, 0);
        if (totalBytes > policy.maxBytesPerItem) {
          resolve();
          return;
        }
        void mergeWavBlobs(segmentsRef.current)
          .then((preview) => {
            // Only surface the preview if we are still paused — the user may
            // have already resumed/stopped while the blob was being spliced.
            if (artifactRef.current?.state === 'paused') {
              setPausedPreviewBlob(preview);
            }
          })
          .catch(() => {
            // No preview is a degraded UI, not an error — the segments are
            // intact and the final stop will surface a real failure if any.
          })
          .finally(resolve);
      });
    });
  }, [stopTimer, updateArtifact, policy]);

  const resumeRecording = useCallback(() => {
    if (artifactRef.current?.state !== 'paused') return;
    setPausedPreviewBlob(null);
    // Resume the timer from where we paused
    startTimeRef.current = Date.now() - pausedElapsedRef.current;
    timerRef.current = setInterval(() => {
      setRecordingTime(
        Math.floor((Date.now() - startTimeRef.current) / 1000),
      );
    }, 1000);
    updateArtifact({ state: 'recording' });
    // Wait for the pause's segment collection, then start the next segment on
    // the still-live stream. Bail if the user stopped/cancelled meanwhile.
    void pauseOpRef.current.then(() => {
      if (artifactRef.current?.state !== 'recording') return;
      const stream = streamRef.current;
      if (!stream) return;
      try {
        recorderRef.current = startNewRecorderSegment(stream);
      } catch (err) {
        updateArtifact({
          state: 'failed',
          errorMessage:
            err instanceof Error ? err.message : 'No se pudo reanudar la grabación.',
        });
      }
    });
  }, [updateArtifact, startNewRecorderSegment]);

  const stopRecording = useCallback(async (): Promise<AudioArtifact | null> => {
    const current = artifactRef.current;
    if (current?.state !== 'recording' && current?.state !== 'paused') {
      return null;
    }

    stopTimer();
    // While recording, startTimeRef is rebased on resume so now-start IS the
    // recorded total. While paused, the wall clock kept running — use the
    // elapsed time captured at pause instead.
    const durationMs =
      current.state === 'paused'
        ? pausedElapsedRef.current
        : Date.now() - startTimeRef.current;

    // Signal to the UI that stop is in-flight before the async RecordRTC callback.
    // Without this the artifact stays in 'recording' during the ~500ms blob + IDB
    // save, and the user sees no feedback after pressing Stop.
    updateArtifact({ state: 'stopping' });
    setPausedPreviewBlob(null);

    // Collect any in-flight pause segment first, then the live recorder's.
    await pauseOpRef.current;

    // NOTE: releaseStream() must NOT be called before stopRecording() — stopping
    // the MediaStream tracks puts the recorder in an invalid state and RecordRTC
    // throws InvalidStateError, leaving the artifact stuck in 'stopping'. We
    // release the stream right AFTER the blob is obtained so the mic indicator
    // still clears promptly (before the merge + IndexedDB save).
    const recorder = recorderRef.current;
    recorderRef.current = null;
    if (recorder) {
      await new Promise<void>((resolve) => recorder.stopRecording(resolve));
      const segment = recorder.getBlob();
      if (segment && segment.size > 0) segmentsRef.current.push(segment);
    }
    releaseStream();

    const segments = segmentsRef.current;
    segmentsRef.current = [];

    let blob: Blob | null = null;
    if (segments.length > 0) {
      try {
        blob = await mergeWavBlobs(segments);
      } catch {
        blob = null; // mismatched/corrupt segments — surfaced as empty below
      }
    }

    if (!blob || blob.size === 0) {
      updateArtifact({ state: 'failed', errorMessage: 'Grabación vacía.' });
      return null;
    }

    if (blob.size > policy.maxBytesPerItem) {
      updateArtifact({
        state: 'failed',
        errorMessage: `Audio demasiado grande (${Math.round(blob.size / 1024 / 1024)} MB, máximo ${Math.round(policy.maxBytesPerItem / 1024 / 1024)} MB).`,
      });
      return null;
    }

    const finalArtifact: AudioArtifact = {
      ...current,
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
      return finalArtifact;
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : 'Error al guardar audio.';
      updateArtifact({ state: 'failed', errorMessage: msg });
      onError?.(msg);
      return null;
    }
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
    segmentsRef.current = [];
    setPausedPreviewBlob(null);
    setArtifact(null);
    artifactRef.current = null;
    setRecordingTime(0);
  }, [stopTimer, releaseStream]);

  return {
    artifact,
    recordingTime,
    pausedPreviewBlob,
    bands,
    audioLevel,
    isSilent,
    isStarting,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    cancelRecording,
    isAtCapacity,
  };
}
