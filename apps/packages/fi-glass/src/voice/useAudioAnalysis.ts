/**
 * useAudioAnalysis Hook
 *
 * Analiza el nivel de audio en tiempo real usando Web Audio API.
 * Incluye detección de silencio y control de ganancia.
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { audioLevel, isSilent } = useAudioAnalysis(stream, {
 *   silenceThreshold: 5,
 *   gain: 2.5,
 *   isActive: isRecording
 * });
 */

import { useState, useRef, useEffect } from 'react';
const AUDIO_CONFIG = { SILENCE_THRESHOLD: 2, AUDIO_GAIN: 2.5 };

interface AudioAnalysisConfig {
  silenceThreshold?: number;
  gain?: number;
  isActive: boolean;
  /** How many frequency bands to expose for a bar visualizer. Default 24. */
  bandCount?: number;
}

interface UseAudioAnalysisReturn {
  audioLevel: number;
  isSilent: boolean;
  /**
   * Normalized (0..1) frequency bands, downsampled from the analyser's spectrum
   * to `bandCount` entries. Empty + zeroed while inactive. Feed straight to
   * AudioVisualizer `levels` for a live equalizer that reacts to the voice's
   * pitch, not just its volume.
   */
  bands: number[];
}

/**
 * Downsample raw byte frequency data (0-255 per bin, e.g. from
 * `AnalyserNode.getByteFrequencyData`) into `bandCount` normalized (0..1) bands.
 * Each band averages its slice of bins; the top ~25% of bins (mostly empty
 * hiss) is dropped for a livelier low/mid response; `gain` lifts quiet mics and
 * the result is clamped to [0,1]. Pure + exported so the band math is unit-
 * tested without Web Audio.
 */
export function frequencyDataToBands(
  data: ArrayLike<number>,
  bandCount: number,
  gain: number
): number[] {
  if (bandCount <= 0 || data.length === 0) return new Array(Math.max(0, bandCount)).fill(0);
  const usable = Math.floor(data.length * 0.75) || data.length;
  const sliceSize = Math.max(1, Math.floor(usable / bandCount));
  const bands = new Array<number>(bandCount);
  for (let b = 0; b < bandCount; b++) {
    const start = b * sliceSize;
    let sum = 0;
    let n = 0;
    for (let i = start; i < start + sliceSize && i < usable; i++) {
      sum += data[i];
      n++;
    }
    const avg = n ? sum / n : 0;
    const scaled = (avg / 255) * gain;
    bands[b] = scaled > 1 ? 1 : scaled < 0 ? 0 : scaled;
  }
  return bands;
}

export function useAudioAnalysis(
  stream: MediaStream | null,
  config: AudioAnalysisConfig
): UseAudioAnalysisReturn {
  const {
    silenceThreshold = AUDIO_CONFIG.SILENCE_THRESHOLD,
    gain = AUDIO_CONFIG.AUDIO_GAIN,
    isActive,
    bandCount = 24,
  } = config;

  const [audioLevel, setAudioLevel] = useState(0);
  const [bands, setBands] = useState<number[]>([]);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Calculate if audio is below silence threshold
  const isSilent = audioLevel < silenceThreshold;

  // Real-time audio level analysis using Web Audio API
  useEffect(() => {
    if (!stream || !isActive) {
      setAudioLevel(0);
      setBands([]);
      return;
    }

    // Create AudioContext and Analyser
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const gainNode = audioContext.createGain();
    const source = audioContext.createMediaStreamSource(stream);

    // Configure gain for low-volume microphones
    gainNode.gain.value = gain;

    // Configure analyser for real-time response
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;

    // Audio routing: source → gain → analyser
    source.connect(gainNode);
    gainNode.connect(analyser);

    audioContextRef.current = audioContext;
    analyserRef.current = analyser;

    // Audio analysis configured — gain and threshold set via props

    // Audio analysis loop
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateLevel = () => {
      if (!analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);

      // Calculate average level (0-255 range)
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average);

      // Downsample the spectrum to normalized (0..1) bands so a bar visualizer
      // shows pitch, not just one volume blob. (Pure helper above, unit-tested.)
      setBands(frequencyDataToBands(dataArray, bandCount, gain));

      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };

    updateLevel();

    // Cleanup function
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, isActive, gain, silenceThreshold, bandCount]);

  return { audioLevel, isSilent, bands };
}
