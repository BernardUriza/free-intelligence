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
 * elemento speaks through; the one-shot composer stays the fallback.
 * See .claude/backlog/og118-resonance-voice-mode.md.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  useAudioAnalysis,
  useResonanceCallLoop,
  type ResonanceCallAdapters,
  type ResonanceErrorPhase,
} from 'fi-glass/voice';

import { og118VoiceAdapter, OG118_DEFAULT_VOICE } from './og118VoiceAdapter';

export interface Og118ResonanceCallParams {
  /** Append the recognized user turn to the client-sent history before the agent runs. */
  appendUserMessage: (text: string) => void;
  /** Send a turn through the streaming agent and resolve with the final assistant text. */
  requestAssistantTurn: (userText: string) => Promise<string>;
  /** Un fallo de voz que el usuario debe ver — se pinta en `Og118VoiceErrorBanner`. */
  onVoiceError?: (message: string) => void;
}

function audioSourceToUrl(src: Blob | { url: string }): string {
  return src instanceof Blob ? URL.createObjectURL(src) : src.url;
}

const FALLO_POR_FASE: Record<ResonanceErrorPhase, string> = {
  mic: 'No se pudo abrir el micrófono — la llamada se colgó.',
  duration: 'La llamada alcanzó su límite de duración.',
  stt: 'No se pudo transcribir tu voz.',
  agent: 'El agente no pudo responder este turno.',
  tts: 'No se pudo sintetizar la respuesta en voz.',
};

/**
 * El texto que el usuario lee cuando un turno de llamada falla. `Og118STTError`
 * y `Og118TTSError` ya cargan un mensaje en español por status (401 sin token,
 * 503 sin configurar), así que ése gana; el resto cae a la fase para que ningún
 * fallo llegue mudo. Un fallo recuperable dice que se reintenta — un fatal no,
 * porque la llamada ya se colgó.
 */
export function mensajeDeFalloDeVoz(
  phase: ResonanceErrorPhase,
  error: unknown,
  fatal: boolean,
): string {
  const conocido = error instanceof Error ? error.message.trim() : '';
  if (conocido) return conocido;
  return fatal ? FALLO_POR_FASE[phase] : `${FALLO_POR_FASE[phase]} Reintentando.`;
}

export function useOg118ResonanceCall(params: Og118ResonanceCallParams) {
  const { appendUserMessage, requestAssistantTurn, onVoiceError } = params;

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
      // Una SÍNTESIS que falla se propaga: el loop la enruta a `recover('tts')`,
      // que ahora sí llega al usuario. Tragársela hacía que un /tts 503 se viera
      // idéntico a un modelo callado. La falla de REPRODUCCIÓN sí resuelve —
      // el audio existió y cortarlo es semántica de barge-in, no un error.
      return new Promise<void>((resolve, reject) => {
        if (!text || !og118VoiceAdapter.synthesize) { resolve(); return; }
        void og118VoiceAdapter.synthesize(text, OG118_DEFAULT_VOICE).then((src) => {
          const audio = new Audio(audioSourceToUrl(src as Blob | { url: string }));
          ttsAudioRef.current = audio;
          audio.onended = () => resolve();
          audio.onerror = () => resolve();
          void audio.play().catch(() => resolve());
        }).catch(reject);
      });
    },
    stopSpeaking: () => {
      const a = ttsAudioRef.current;
      if (a) { a.pause(); a.currentTime = 0; }
    },
    appendUserMessage,
    onError: (phase, error, fatal) => onVoiceError?.(mensajeDeFalloDeVoz(phase, error, fatal)),
  };

  const loop = useResonanceCallLoop({
    enabled: true,
    adapters,
    getAudioLevel: () => audioLevelRef.current,
    audioCues: {
      enabled: true,
      assets: {
        thinking: '/sounds/thinking.mp3',
        crystalline: '/sounds/crystalline.mp3',
        ready: '/sounds/ready.mp3',
      },
    },
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
