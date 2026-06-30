/**
 * resonanceVadGate — a pure, time-driven voice-activity detector for RESONANCE.
 *
 * The first VAD attempt closed end-of-speech off a React effect watching a
 * derived `isSilent` boolean — it flaked, because re-renders are not a reliable
 * clock and a single threshold has no hysteresis. This gate instead takes the
 * CURRENT audio level + a monotonic timestamp on every tick (the React layer
 * drives it from a setInterval reading an audioLevel ref) and decides with
 * two-threshold hysteresis + minimum durations. No React, no audio I/O — so the
 * timing contract is verifiable with an injected clock + level. audioLevel is the
 * 0-255 analyser average (see useAudioAnalysis).
 */

export interface ResonanceVadConfig {
  /** Level (0-255) to DECLARE speech onset — high, to reject noise. */
  speechOnThreshold: number;
  /** Level (0-255) below which counts as silence — low, the hysteresis floor. */
  speechOffThreshold: number;
  /** Sustained-above-on time before emitting speech_start (debounce). */
  minSpeechMs: number;
  /** Sustained-below-off time after last voice before emitting speech_end. */
  endSilenceMs: number;
  /** Hard cap on a single user turn; forces speech_end. */
  maxTurnMs: number;
}

export const DEFAULT_VAD_CONFIG: ResonanceVadConfig = {
  speechOnThreshold: 24,
  speechOffThreshold: 13,
  minSpeechMs: 180,
  endSilenceMs: 850,
  maxTurnMs: 20_000,
};

/** What the gate is allowed to detect this tick, derived from the call state. */
export type ResonanceVadMode = 'detect' | 'barge' | 'idle';

export type ResonanceVadEvent = 'speech_start' | 'speech_end' | 'barge_in' | null;

export interface ResonanceVadGate {
  /** Feed the current level + monotonic now (ms). Returns one event or null. */
  tick: (level: number, nowMs: number, mode: ResonanceVadMode) => ResonanceVadEvent;
  reset: () => void;
}

export function createResonanceVadGate(
  config: ResonanceVadConfig = DEFAULT_VAD_CONFIG,
): ResonanceVadGate {
  const { speechOnThreshold, speechOffThreshold, minSpeechMs, endSilenceMs, maxTurnMs } = config;

  let inSpeech = false;
  let candidateStartedAt: number | null = null; // sustained-onset tracker
  let speechStartedAt = 0;
  let lastVoiceAt = 0;
  let bargeLatched = false; // emit barge_in once per sustained interruption

  function reset() {
    inSpeech = false;
    candidateStartedAt = null;
    speechStartedAt = 0;
    lastVoiceAt = 0;
    bargeLatched = false;
  }

  function tick(level: number, nowMs: number, mode: ResonanceVadMode): ResonanceVadEvent {
    if (mode === 'idle') {
      // Not listening this tick (transcribing/thinking/ended) — drop any partial.
      reset();
      return null;
    }

    const aboveOn = level >= speechOnThreshold;

    if (mode === 'barge') {
      // In 'speaking': only care about a sustained onset to interrupt the TTS.
      // Latch so one continuous interruption emits barge_in exactly once.
      if (level <= speechOffThreshold) {
        bargeLatched = false;
        candidateStartedAt = null;
        return null;
      }
      if (bargeLatched) return null;
      if (aboveOn) {
        candidateStartedAt ??= nowMs;
        if (nowMs - candidateStartedAt >= minSpeechMs) {
          candidateStartedAt = null;
          bargeLatched = true;
          return 'barge_in';
        }
      }
      return null;
    }

    // mode === 'detect' (listening / silence_hold)
    const belowOff = level <= speechOffThreshold;

    if (!inSpeech) {
      if (aboveOn) {
        candidateStartedAt ??= nowMs;
        if (nowMs - candidateStartedAt >= minSpeechMs) {
          inSpeech = true;
          speechStartedAt = nowMs;
          lastVoiceAt = nowMs;
          candidateStartedAt = null;
          return 'speech_start';
        }
      } else {
        candidateStartedAt = null;
      }
      return null;
    }

    // inSpeech: track last voice, then test sustained silence / max turn.
    if (level > speechOffThreshold) lastVoiceAt = nowMs;

    if (nowMs - speechStartedAt >= maxTurnMs) {
      inSpeech = false;
      candidateStartedAt = null;
      return 'speech_end';
    }
    if (belowOff && nowMs - lastVoiceAt >= endSilenceMs) {
      inSpeech = false;
      candidateStartedAt = null;
      return 'speech_end';
    }
    return null;
  }

  return { tick, reset };
}
