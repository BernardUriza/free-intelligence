'use client';

/**
 * useResonanceCallLoop — the thin React wrapper that turns the verified, headless
 * resonanceCallController into a live hands-free voice call by binding the real
 * adapters (mic + VAD + STT + composer + TTS) and the silence/auto-resume/sleep
 * timers to it.
 *
 * All turn-taking logic lives in resonanceCallController (vitest-verified). This
 * hook only owns the side of the contract that needs the browser: edge-detecting
 * speech/silence from the live VAD levels, debouncing end-of-speech, arming the
 * auto-resume and sleep timers, and exposing window.__RESONANCE_EVENTS__ for the
 * screenless E2E harness. RESONANCE is the voice channel an elemento speaks
 * through; og118 mounts this behind the RESONANCE_CALL_LOOP flag with a one-shot
 * composer fallback. See .claude/backlog/og118-resonance-voice-mode.md.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { createResonanceCallController } from './resonanceCallController';
import type { ResonanceDriver } from './resonanceEffects';
import type { ResonanceCallEvent, ResonanceCallState } from './resonanceCallMachine';

export interface ResonanceCallAdapters {
  /** Open the mic stream (useDurableRecording.startRecording). */
  openMic: () => void | Promise<void>;
  /** Close the mic stream (useDurableRecording.stopRecording). */
  closeMic: () => void | Promise<void>;
  /** Stop the current segment and push it to STT; resolve with transcript text. */
  beginTranscribe: () => Promise<string>;
  /** Run the agent over the (already-appended) client-sent history; resolve with assistant text. */
  invokeAgent: () => Promise<string>;
  /** Synthesize + play the assistant text (useVoice.generateAudio + playback). */
  speak: (text: string) => void | Promise<void>;
  /** Cut TTS playback immediately (useVoice.close) — barge-in. */
  stopSpeaking: () => void;
  /** Append the user transcript to the client-sent history before invokeAgent. */
  appendUserMessage: (text: string) => void;
}

export interface ResonanceSilencePolicy {
  endOfSpeechMs: number;
  autoResumeMs: number;
}

export interface ResonanceSleepPolicy {
  enabled: boolean;
  idleHangupMs: number;
}

export interface ResonanceBargeInPolicy {
  enabled: boolean;
}

export interface UseResonanceCallLoopParams {
  enabled: boolean;
  adapters: ResonanceCallAdapters;
  /** Live VAD: true while input energy is below the silence threshold (useAudioAnalysis.isSilent). */
  isSilent: boolean;
  /** Live VAD: true while input energy indicates the user is speaking. */
  hasSpeech: boolean;
  silencePolicy?: ResonanceSilencePolicy;
  sleepPolicy?: ResonanceSleepPolicy;
  bargeInPolicy?: ResonanceBargeInPolicy;
  /** Expose window.__RESONANCE_EVENTS__ for the screenless E2E harness. */
  debug?: boolean;
  onEvent?: (event: ResonanceCallEvent, state: ResonanceCallState) => void;
}

export interface UseResonanceCallLoopReturn {
  state: ResonanceCallState;
  isActive: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  isThinking: boolean;
  lastTranscript?: string;
  lastAssistantText?: string;
  startCall: () => Promise<void>;
  endCall: () => void;
  interrupt: () => void;
}

const DEFAULT_SILENCE: ResonanceSilencePolicy = { endOfSpeechMs: 900, autoResumeMs: 1200 };
const DEFAULT_SLEEP: ResonanceSleepPolicy = { enabled: true, idleHangupMs: 300_000 };
const DEFAULT_BARGE_IN: ResonanceBargeInPolicy = { enabled: true };

interface ResonanceEventRecord {
  type: ResonanceCallEvent | 'stt.completed' | 'assistant.text';
  state: ResonanceCallState;
  transcript?: string;
  text?: string;
  timestamp: number;
}

declare global {
  interface Window {
    __RESONANCE_EVENTS__?: ResonanceEventRecord[];
  }
}

export function useResonanceCallLoop(
  params: UseResonanceCallLoopParams,
): UseResonanceCallLoopReturn {
  const {
    enabled,
    adapters,
    isSilent,
    hasSpeech,
    silencePolicy = DEFAULT_SILENCE,
    sleepPolicy = DEFAULT_SLEEP,
    bargeInPolicy = DEFAULT_BARGE_IN,
    debug = false,
    onEvent,
  } = params;

  const [state, setState] = useState<ResonanceCallState>('idle');
  const [lastTranscript, setLastTranscript] = useState<string>();
  const [lastAssistantText, setLastAssistantText] = useState<string>();

  // Keep the latest adapters/policies in refs so the controller's driver closures
  // never go stale without re-creating the controller mid-call.
  const adaptersRef = useRef(adapters);
  adaptersRef.current = adapters;

  const pushDebug = useCallback(
    (record: ResonanceEventRecord) => {
      if (!debug || typeof window === 'undefined') return;
      (window.__RESONANCE_EVENTS__ ||= []).push(record);
    },
    [debug],
  );

  const controller = useMemo(() => {
    const driver: ResonanceDriver = {
      openMic: () => { void adaptersRef.current.openMic(); },
      beginTranscribe: () => {
        void Promise.resolve(adaptersRef.current.beginTranscribe()).then((transcript) => {
          if (!transcript) { ctrl.silenceResume(); return; }
          setLastTranscript(transcript);
          adaptersRef.current.appendUserMessage(transcript);
          pushDebug({ type: 'stt.completed', state: 'transcribing', transcript, timestamp: Date.now() });
          ctrl.sttCompleted(transcript);
        });
      },
      invokeAgent: () => {
        void Promise.resolve(adaptersRef.current.invokeAgent()).then((text) => {
          setLastAssistantText(text);
          pushDebug({ type: 'assistant.text', state: 'thinking', text, timestamp: Date.now() });
          ctrl.assistantTurnReady(text);
        });
      },
      speak: () => {
        const text = ctrl.lastAssistantText() ?? '';
        void adaptersRef.current.speak(text);
      },
      stopSpeaking: () => { adaptersRef.current.stopSpeaking(); },
      holdSilence: () => {},
      fadeAndHangup: () => { void adaptersRef.current.closeMic(); },
      endCall: () => { void adaptersRef.current.closeMic(); },
    };
    const ctrl = createResonanceCallController(driver, {
      onState: (s) => setState(s),
      onEvent: (event, s) => {
        pushDebug({ type: event, state: s, timestamp: Date.now() });
        onEvent?.(event, s);
      },
    });
    return ctrl;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pushDebug]);

  // --- VAD edge detection + timers -----------------------------------------
  const spokeRef = useRef(false);
  const endOfSpeechTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const autoResumeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sleepTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const clearTimer = (t: React.MutableRefObject<ReturnType<typeof setTimeout> | undefined>) => {
    if (t.current) { clearTimeout(t.current); t.current = undefined; }
  };

  useEffect(() => {
    if (!enabled) return;

    if (state === 'listening') {
      clearTimer(autoResumeTimer);
      if (hasSpeech) {
        clearTimer(endOfSpeechTimer);
        if (!spokeRef.current) { spokeRef.current = true; controller.userSpeechStarted(); }
      } else if (isSilent && spokeRef.current && !endOfSpeechTimer.current) {
        endOfSpeechTimer.current = setTimeout(() => {
          endOfSpeechTimer.current = undefined;
          spokeRef.current = false;
          controller.userSpeechEnded();
        }, silencePolicy.endOfSpeechMs);
      }
    }

    if (state === 'speaking' && bargeInPolicy.enabled && hasSpeech) {
      controller.interrupt();
    }

    if (state === 'silence_hold') {
      if (!autoResumeTimer.current) {
        autoResumeTimer.current = setTimeout(() => {
          autoResumeTimer.current = undefined;
          controller.silenceResume();
        }, silencePolicy.autoResumeMs);
      }
      if (sleepPolicy.enabled && !sleepTimer.current) {
        sleepTimer.current = setTimeout(() => {
          sleepTimer.current = undefined;
          controller.sleepDecay();
          controller.endCall();
        }, sleepPolicy.idleHangupMs);
      }
    } else {
      clearTimer(sleepTimer);
    }
  }, [enabled, state, isSilent, hasSpeech, controller, silencePolicy, sleepPolicy, bargeInPolicy]);

  useEffect(() => () => {
    clearTimer(endOfSpeechTimer);
    clearTimer(autoResumeTimer);
    clearTimer(sleepTimer);
  }, []);

  const startCall = useCallback(async () => {
    if (!enabled) return;
    if (debug && typeof window !== 'undefined') window.__RESONANCE_EVENTS__ = [];
    spokeRef.current = false;
    controller.startCall();
  }, [enabled, debug, controller]);

  const endCall = useCallback(() => { controller.endCall(); }, [controller]);
  const interrupt = useCallback(() => { controller.interrupt(); }, [controller]);

  return {
    state,
    isActive: state !== 'idle' && state !== 'ended',
    isListening: state === 'listening',
    isSpeaking: state === 'speaking',
    isThinking: state === 'thinking' || state === 'transcribing',
    lastTranscript,
    lastAssistantText,
    startCall,
    endCall,
    interrupt,
  };
}
