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
import {
  createResonanceVadGate,
  DEFAULT_VAD_CONFIG,
  type ResonanceVadConfig,
  type ResonanceVadMode,
} from './resonanceVadGate';
import { createResonanceCueController } from './resonanceCueController';
import { createAudioCuePlayer, type AudioCueAssets } from './createAudioCuePlayer';

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
  /**
   * Read the CURRENT input level (0-255 analyser average). Polled on a stable
   * 50ms timer by the robust VAD gate — not a re-render-driven boolean, which
   * was the source of the frozen-loop flakiness.
   */
  getAudioLevel: () => number;
  /** Hysteresis + timing thresholds for the VAD gate. */
  vadConfig?: ResonanceVadConfig;
  silencePolicy?: ResonanceSilencePolicy;
  sleepPolicy?: ResonanceSleepPolicy;
  bargeInPolicy?: ResonanceBargeInPolicy;
  /** Audio cues (thinking loop / crystalline / ready). Off unless enabled + assets given. */
  audioCues?: { enabled: boolean; assets: AudioCueAssets; volume?: number };
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
    getAudioLevel,
    vadConfig = DEFAULT_VAD_CONFIG,
    silencePolicy = DEFAULT_SILENCE,
    sleepPolicy = DEFAULT_SLEEP,
    bargeInPolicy = DEFAULT_BARGE_IN,
    audioCues,
    debug = false,
    onEvent,
  } = params;

  const getAudioLevelRef = useRef(getAudioLevel);
  getAudioLevelRef.current = getAudioLevel;

  // Audio cues: a Web Audio player behind the pure cue controller. The wrapper is
  // the lifecycle owner — it preloads, applies the policy per transition, and
  // tears down on unmount so a cue can never outlive the call.
  const cueEnabled = audioCues?.enabled ?? false;
  const cuePlayer = useMemo(
    () => (cueEnabled && audioCues ? createAudioCuePlayer(audioCues.assets, { volume: audioCues.volume }) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cueEnabled, audioCues?.assets.thinking, audioCues?.assets.crystalline, audioCues?.assets.ready, audioCues?.volume],
  );
  const cueController = useMemo(() => (cuePlayer ? createResonanceCueController(cuePlayer) : null), [cuePlayer]);
  const cueApplyRef = useRef<typeof cueController extends null ? never : ((i: { previousState: ResonanceCallState; nextState: ResonanceCallState; event: ResonanceCallEvent }, id: string) => void) | undefined>(undefined);
  cueApplyRef.current = cueController?.applyTransition;
  const cueSeqRef = useRef(0);

  useEffect(() => { void cuePlayer?.preload(); }, [cuePlayer]);
  useEffect(() => () => { cuePlayer?.dispose(); }, [cuePlayer]);

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
    // Every async effect ends in success OR recovery — a rejected adapter promise
    // must never leave the loop frozen (the old bug: void p.then() with no catch).
    const recover = (phase: string, e: unknown) => {
      pushDebug({ type: `error.${phase}` as ResonanceCallEvent, state: 'idle', timestamp: Date.now() });
      console.warn(`[resonance] ${phase} failed, recovering`, e);
      ctrl.failRecoverable();
    };
    const driver: ResonanceDriver = {
      openMic: () => {
        void Promise.resolve(adaptersRef.current.openMic()).catch((e) => {
          console.warn('[resonance] mic failed, hanging up', e);
          ctrl.failFatal();
        });
      },
      beginTranscribe: () => {
        void Promise.resolve(adaptersRef.current.beginTranscribe()).then((transcript) => {
          if (!transcript) { ctrl.failRecoverable(); return; }
          setLastTranscript(transcript);
          adaptersRef.current.appendUserMessage(transcript);
          pushDebug({ type: 'stt.completed', state: 'transcribing', transcript, timestamp: Date.now() });
          ctrl.sttCompleted(transcript);
        }).catch((e) => recover('stt', e));
      },
      invokeAgent: () => {
        void Promise.resolve(adaptersRef.current.invokeAgent()).then((text) => {
          if (!text) { ctrl.failRecoverable(); return; }
          setLastAssistantText(text);
          pushDebug({ type: 'assistant.text', state: 'thinking', text, timestamp: Date.now() });
          ctrl.assistantTurnReady(text);
        }).catch((e) => recover('agent', e));
      },
      speak: () => {
        const text = ctrl.lastAssistantText() ?? '';
        // speak() resolves when playback ENDS -> advance to silence_hold. The
        // state guard makes a barge-in (which already left 'speaking') a no-op,
        // so an interrupted clip never double-advances the turn.
        void Promise.resolve(adaptersRef.current.speak(text)).then(() => {
          if (ctrl.state() === 'speaking') ctrl.ttsCompleted();
        }).catch((e) => recover('tts', e));
      },
      stopSpeaking: () => { try { adaptersRef.current.stopSpeaking(); } catch { /* best-effort */ } },
      holdSilence: () => {},
      fadeAndHangup: () => { void adaptersRef.current.closeMic(); },
      endCall: () => { void adaptersRef.current.closeMic(); },
    };
    const ctrl = createResonanceCallController(driver, {
      onState: (s) => setState(s),
      onEvent: (event, s) => {
        // ctrl.state() is still the PRE-transition state here (the controller
        // updates after onEvent), so this is the exact (prev,next,event) the cue
        // policy needs. Cues apply BEFORE the speak effect dispatch, so the
        // thinking loop stops before TTS starts.
        cueApplyRef.current?.({ previousState: ctrl.state(), nextState: s, event }, String(cueSeqRef.current++));
        pushDebug({ type: event, state: s, timestamp: Date.now() });
        onEvent?.(event, s);
      },
    });
    return ctrl;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pushDebug]);

  // --- Robust VAD gate (stable 50ms timer, ref-driven) ---------------------
  const stateRef = useRef(state);
  stateRef.current = state;
  const gate = useMemo(() => createResonanceVadGate(vadConfig), [vadConfig]);

  useEffect(() => {
    if (!enabled) return undefined;
    const id = setInterval(() => {
      const s = stateRef.current;
      const mode: ResonanceVadMode =
        s === 'listening' || s === 'silence_hold' ? 'detect'
        : s === 'speaking' && bargeInPolicy.enabled ? 'barge'
        : 'idle';
      const ev = gate.tick(getAudioLevelRef.current(), performance.now(), mode);
      if (ev === 'speech_start') controller.userSpeechStarted();
      else if (ev === 'speech_end') controller.userSpeechEnded();
      else if (ev === 'barge_in') controller.interrupt();
    }, 50);
    return () => { clearInterval(id); gate.reset(); };
  }, [enabled, gate, controller, bargeInPolicy]);

  // --- Auto-resume + sleep timers ------------------------------------------
  const autoResumeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const sleepTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const clearTimer = (t: React.MutableRefObject<ReturnType<typeof setTimeout> | undefined>) => {
    if (t.current) { clearTimeout(t.current); t.current = undefined; }
  };

  useEffect(() => {
    if (!enabled) return undefined;
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
      clearTimer(autoResumeTimer);
      clearTimer(sleepTimer);
    }
    return undefined;
  }, [enabled, state, controller, silencePolicy, sleepPolicy]);

  useEffect(() => () => {
    clearTimer(autoResumeTimer);
    clearTimer(sleepTimer);
  }, []);

  const startCall = useCallback(async () => {
    if (!enabled) return;
    if (debug && typeof window !== 'undefined') window.__RESONANCE_EVENTS__ = [];
    gate.reset();
    cueController?.reset();
    controller.startCall();
  }, [enabled, debug, controller, gate, cueController]);

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
