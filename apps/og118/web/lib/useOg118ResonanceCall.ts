'use client';

/**
 * useOg118ResonanceCall — og118's consumer glue for RESONANCE (hands-free voice
 * call). Composes the live browser audio surface — one shared getUserMedia
 * stream, useAudioAnalysis for VAD, a MediaRecorder for turn segments, the
 * og118VoiceAdapter for STT/TTS, and the streaming agent — into the
 * ResonanceCallAdapters that drive fi-glass's verified useResonanceCallLoop.
 *
 * All turn-taking lives in the framework (resonanceCallController, vitest-green);
 * this hook only owns the og118-specific I/O wiring. RESONANCE is the channel an
 * elemento speaks through. Mounted behind the RESONANCE_CALL_LOOP flag with the
 * one-shot composer as the fallback. See .claude/backlog/og118-resonance-voice-mode.md.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAudioAnalysis, useResonanceCallLoop, type ResonanceCallAdapters } from 'fi-glass/voice';

import { og118VoiceAdapter, OG118_DEFAULT_VOICE } from './og118VoiceAdapter';

export interface Og118ResonanceCallParams {
  enabled: boolean;
  /** Append the recognized user turn to the client-sent history before the agent runs. */
  appendUserMessage: (text: string) => void;
  /** Send a turn through the streaming agent and resolve with the final assistant text. */
  requestAssistantTurn: (userText: string) => Promise<string>;
  debug?: boolean;
}

function audioSourceToUrl(src: Blob | { url: string }): string {
  return src instanceof Blob ? URL.createObjectURL(src) : src.url;
}

export function useOg118ResonanceCall(params: Og118ResonanceCallParams) {
  const { enabled, appendUserMessage, requestAssistantTurn, debug = false } = params;

  const [streamActive, setStreamActive] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const lastTranscriptRef = useRef<string>('');

  const analysis = useAudioAnalysis(streamRef.current, {
    isActive: streamActive,
  });
  // Feed the robust VAD gate the CURRENT 0-255 level via a ref (the gate polls it
  // on a stable 50ms timer). The earlier `audioLevel > 0.08` was a scale bug, and
  // even isSilent-as-a-render-prop flaked; ref + gate is the fix.
  const audioLevelRef = useRef(0);
  audioLevelRef.current = analysis.audioLevel;

  const startSegment = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;
    if (recorderRef.current && recorderRef.current.state === 'recording') return;
    chunksRef.current = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    rec.start();
    recorderRef.current = rec;
  }, []);

  const finishSegment = useCallback((): Promise<Blob> => {
    const rec = recorderRef.current;
    if (!rec || rec.state !== 'recording') return Promise.resolve(new Blob(chunksRef.current));
    return new Promise<Blob>((resolve) => {
      rec.onstop = () => resolve(new Blob(chunksRef.current, { type: rec.mimeType || 'audio/webm' }));
      rec.stop();
    });
  }, []);

  const adapters: ResonanceCallAdapters = {
    openMic: async () => {
      if (!streamRef.current) {
        streamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true });
        setStreamActive(true);
      }
      startSegment();
    },
    closeMic: () => {
      recorderRef.current?.state === 'recording' && recorderRef.current.stop();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setStreamActive(false);
    },
    beginTranscribe: async () => {
      const blob = await finishSegment();
      if (!og118VoiceAdapter.transcribe) return '';
      const result = await og118VoiceAdapter.transcribe(blob);
      const text = (result?.text ?? '').trim();
      lastTranscriptRef.current = text;
      return text;
    },
    invokeAgent: async () => {
      return requestAssistantTurn(lastTranscriptRef.current);
    },
    speak: (text: string) => {
      return new Promise<void>((resolve) => {
        if (!text || !og118VoiceAdapter.synthesize) { resolve(); return; }
        void og118VoiceAdapter.synthesize(text, OG118_DEFAULT_VOICE).then((src) => {
          const audio = new Audio(audioSourceToUrl(src as Blob | { url: string }));
          ttsAudioRef.current = audio;
          audio.onended = () => resolve();
          audio.onerror = () => resolve();
          void audio.play().catch(() => resolve());
        }).catch(() => resolve());
      });
    },
    stopSpeaking: () => {
      const a = ttsAudioRef.current;
      if (a) { a.pause(); a.currentTime = 0; }
    },
    appendUserMessage,
  };

  const loop = useResonanceCallLoop({
    enabled,
    adapters,
    getAudioLevel: () => audioLevelRef.current,
    debug,
  });

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  // Visual feedback shares the SAME analyser the VAD gate reads — one mic, one
  // useAudioAnalysis. The call bar's equalizer is a passive consumer of these
  // bands, so Bernard can see whether Resonance is actually hearing him.
  return {
    ...loop,
    bands: analysis.bands,
    isHearingUser: loop.isListening && !analysis.isSilent,
  };
}
